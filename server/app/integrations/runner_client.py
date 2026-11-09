"""
Code execution runner client.
Executes learner code via Judge0 REST API (primary) with a local sandboxed
subprocess fallback (bwrap + POSIX resource limits + runtime guardrails) when
Judge0 is unreachable or unconfigured.
Never executes learner code outside a sandbox.
Guarantees hidden test inputs, outputs, and runner internals stay strictly
server-side. Classifies outcomes into exactly four states: passed,
wrong_output, runtime_error, timeout.
Also detects when learner code mutates its input lists (mutates_input) and
which resource limit was hit (time, memory, output, disk).
"""
import ast
import asyncio
import json
import os
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.core.exceptions import RunnerUnavailableError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Judge0 language ID for Python 3
PYTHON_LANGUAGE_ID = 71

# Judge0 submission status IDs (RapidAPI hosted tier)
STATUS_IN_QUEUE = 1
STATUS_PROCESSING = 2
STATUS_ACCEPTED = 3
STATUS_WRONG_ANSWER = 4
STATUS_TIME_LIMIT_EXCEEDED = 5
STATUS_RUNTIME_ERROR = 11
STATUS_COMPILATION_ERROR = 7
STATUS_INTERNAL_ERROR = 8
STATUS_EXEC_FORMAT_ERROR = 9

_JUDGE0_TO_OUTCOME = {
    STATUS_ACCEPTED: "passed",
    STATUS_WRONG_ANSWER: "wrong_output",
    STATUS_RUNTIME_ERROR: "runtime_error",
    STATUS_TIME_LIMIT_EXCEEDED: "timeout",
    STATUS_COMPILATION_ERROR: "runtime_error",
    STATUS_EXEC_FORMAT_ERROR: "runtime_error",
}

MAX_OUTPUT_BYTES = 65536  # 64 KB stdout/stderr cap
MAX_FILE_BYTES = 65536    # 64 KB file write cap


def _probe_bwrap() -> str | None:
    """Verify bwrap is installed and functional on this host."""
    path = shutil.which("bwrap")
    if not path:
        return None
    try:
        res = subprocess.run(
            [
                path,
                "--unshare-all",
                "--ro-bind", "/", "/",
                "--proc", "/proc",
                "--dev", "/dev",
                "--tmpfs", "/tmp",
                "--",
                sys.executable, "-c", "pass",
            ],
            capture_output=True,
            timeout=2.0,
        )
        return path if res.returncode == 0 else None
    except Exception:
        return None


_BWRAP = _probe_bwrap()


def _set_resource_limits(timeout_seconds: float, memory_limit_mb: int):
    """Pre-exec callback: apply POSIX resource limits inside the child process."""
    mem_bytes = max(192, int(memory_limit_mb) * 3) * 1024 * 1024
    cpu_secs = max(1, int(timeout_seconds) + 1)
    try:
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
    except Exception:
        pass
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_secs, cpu_secs))
    except Exception:
        pass
    try:
        resource.setrlimit(resource.RLIMIT_NPROC, (16, 16))
    except Exception:
        pass
    try:
        resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_FILE_BYTES, MAX_FILE_BYTES))
    except Exception:
        pass
    try:
        resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    except Exception:
        pass


def _build_mutated_source(
    source_code: str,
    call_str: str,
    run_token: str = "DEFAULT",
    memory_limit_mb: int = 64,
    timeout_seconds: float = 2.0,
    include_guardrails: bool = True,
) -> str:
    """
    Build the isolated Python harness that:
    1. Applies resource limits and blocks dangerous modules/syscalls/filesystem access.
    2. Snapshots arguments before calling the learner function to detect mutates_input.
    3. Emits a randomized token marker so user code cannot spoof the harness result.
    """
    try:
        tree = ast.parse(f"_tmp = {call_str}", mode="exec")
        assign = tree.body[0]
        if not isinstance(assign.value, ast.Call):
            call_node = None
        else:
            call_node = assign.value
    except Exception:
        call_node = None

    mem_bytes = max(192, int(memory_limit_mb) * 3) * 1024 * 1024
    cpu_secs = max(1, int(timeout_seconds) + 1)

    preamble = [
        "import builtins as _builtins, copy as _copy, json as _json, os as _os, sys as _sys",
        "_orig_stdout_write = _sys.stdout.write",
        "_orig_stdout_flush = _sys.stdout.flush",
    ]

    if include_guardrails:
        preamble.extend([
            "try:",
            "    import resource as _resource",
            f"    _resource.setrlimit(_resource.RLIMIT_AS, ({mem_bytes}, {mem_bytes}))",
            f"    _resource.setrlimit(_resource.RLIMIT_CPU, ({cpu_secs}, {cpu_secs}))",
            f"    _resource.setrlimit(_resource.RLIMIT_FSIZE, ({MAX_FILE_BYTES}, {MAX_FILE_BYTES}))",
            "    _resource.setrlimit(_resource.RLIMIT_NPROC, (16, 16))",
            "except Exception:",
            "    pass",
            "_os.environ.clear()",
            f"_written_bytes = [0]",
            "def _guarded_stdout_write(_s):",
            "    _b = len(str(_s))",
            "    _written_bytes[0] += _b",
            f"    if _written_bytes[0] > {MAX_OUTPUT_BYTES}:",
            f"        _orig_stdout_write('\\n___LIMIT_OUTPUT_{run_token}___\\n')",
            "        _orig_stdout_flush()",
            "        _sys.exit(1)",
            "    return _orig_stdout_write(_s)",
            "_sys.stdout.write = _guarded_stdout_write",
            "for _fn in ('fork', 'system', 'popen', 'spawnl', 'spawnle', 'spawnlp', 'spawnlpe', 'spawnv', 'spawnve', 'spawnvp', 'spawnvpe', 'execl', 'execle', 'execlp', 'execlpe', 'execv', 'execve', 'execvp', 'execvpe', 'kill', 'killpg', 'remove', 'unlink', 'rmdir', 'mkdir', 'makedirs', 'rename', 'replace', 'chmod', 'chown', 'listdir', 'scandir', 'walk'):",
            "    if hasattr(_os, _fn):",
            "        setattr(_os, _fn, lambda *a, **kw: (_ for _ in ()).throw(PermissionError('System operation blocked in sandbox')))",
            "_BLOCKED_MODULES = frozenset({'socket', 'urllib', 'http', 'ftplib', 'smtplib', 'telnetlib', 'xmlrpc', 'subprocess', 'multiprocessing', 'concurrent', 'pty', 'ctypes', 'shutil', 'signal', 'resource', 'fcntl', 'mmap', ' pathlib', 'pathlib', 'glob', 'tempfile', 'sqlite3'})",
            "class _SandboxImportBlocker:",
            "    def find_spec(self, fullname, path=None, target=None):",
            "        top = fullname.split('.')[0]",
            "        if top in _BLOCKED_MODULES:",
            "            raise ImportError(f'Module {top!r} is restricted in sandbox')",
            "        return None",
            "_sys.meta_path.insert(0, _SandboxImportBlocker())",
            "def _blocked_open(file, mode='r', *args, **kwargs):",
            "    if any(m in str(mode) for m in ('w', 'a', 'x', '+')):",
            f"        _sys.stdout.write('\\n___LIMIT_DISK_{run_token}___\\n')",
            "        _sys.stdout.flush()",
            "        raise PermissionError('Disk write access is restricted in sandbox')",
            "    raise PermissionError('File read access is restricted in sandbox')",
            "_builtins.open = _blocked_open",
        ])

    preamble.append("# --- Learner Code Start ---")
    preamble.append(source_code)
    preamble.append("# --- Learner Code End ---")

    if call_node is None:
        preamble.extend([
            "try:",
            f"    _result = ({call_str})",
            "    try:",
            "        _dumped = _json.dumps(_result)",
            "    except Exception:",
            "        _dumped = _json.dumps(repr(_result))",
            f'    _sys.stdout.write("\\n___RESULT_{run_token}___" + _dumped + "\\n")',
            "except MemoryError:",
            f'    _sys.stdout.write("\\n___LIMIT_MEMORY_{run_token}___\\n")',
            "    _sys.exit(1)",
            "except Exception as _exc:",
            f'    _sys.stdout.write("\\n___ERROR_{run_token}___" + type(_exc).__name__ + "\\n")',
            "    _sys.exit(1)",
        ])
        return "\n".join(preamble)

    func_name = call_node.func.id if isinstance(call_node.func, ast.Name) else ast.unparse(call_node.func)
    arg_assignments = []
    call_vars = []
    snapshot_checks = []

    for i, arg in enumerate(call_node.args):
        var_name = f"_arg_{i}"
        snap_name = f"_snap_{i}"
        arg_source = ast.unparse(arg)
        arg_assignments.append(f"    {var_name} = {arg_source}")
        arg_assignments.append(f"    {snap_name} = _copy.deepcopy({var_name})")
        call_vars.append(var_name)
        snapshot_checks.append((var_name, snap_name))

    for i, kw in enumerate(call_node.keywords):
        var_name = f"_kwarg_{i}"
        snap_name = f"_kwsnap_{i}"
        arg_source = ast.unparse(kw.value)
        arg_assignments.append(f"    {var_name} = {arg_source}")
        arg_assignments.append(f"    {snap_name} = _copy.deepcopy({var_name})")
        if kw.arg:
            call_vars.append(f"{kw.arg}={var_name}")
        else:
            call_vars.append(f"**{var_name}")
        snapshot_checks.append((var_name, snap_name))

    call_with_vars = f"{func_name}({', '.join(call_vars)})"

    preamble.append("try:")
    preamble.extend(arg_assignments)
    preamble.append(f"    _result = {call_with_vars}")
    for var_name, snap_name in snapshot_checks:
        preamble.append(f"    if {var_name} != {snap_name}:")
        preamble.append(f'        _sys.stdout.write("\\n___MUTATED_{run_token}___\\n")')
    preamble.append("    try:")
    preamble.append("        _dumped = _json.dumps(_result)")
    preamble.append("    except Exception:")
    preamble.append("        _dumped = _json.dumps(repr(_result))")
    preamble.append(f'    _sys.stdout.write("\\n___RESULT_{run_token}___" + _dumped + "\\n")')
    preamble.append("except MemoryError:")
    preamble.append(f'    _sys.stdout.write("\\n___LIMIT_MEMORY_{run_token}___\\n")')
    preamble.append("    _sys.exit(1)")
    preamble.append("except OSError as _os_exc:")
    preamble.append("    if getattr(_os_exc, 'errno', None) in (27, 28, 30):")
    preamble.append(f'        _sys.stdout.write("\\n___LIMIT_DISK_{run_token}___\\n")')
    preamble.append(f'    _sys.stdout.write("\\n___ERROR_{run_token}___" + type(_os_exc).__name__ + "\\n")')
    preamble.append("    _sys.exit(1)")
    preamble.append("except Exception as _exc:")
    preamble.append(f'    _sys.stdout.write("\\n___ERROR_{run_token}___" + type(_exc).__name__ + "\\n")')
    preamble.append("    _sys.exit(1)")

    return "\n".join(preamble)


def _get_call_from_testcase(tc: dict) -> str:
    """Extract callable python string from testcase dict."""
    payload = tc.get("input_payload") or {}
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            pass
    if isinstance(payload, dict) and "call" in payload:
        return payload["call"]
    if tc.get("call"):
        return tc["call"]
    if tc.get("description") and "(" in str(tc["description"]):
        return tc["description"]
    return str(payload)


def _parse_mutated_output(stdout: str, run_token: str = "DEFAULT") -> tuple:
    """
    Parse runner stdout to extract:
    (has_result, actual_output, mutated_flag, limit_hit, error_type, user_stdout)
    """
    has_result = False
    actual = None
    mutated = False
    limit_hit = None
    error_type = None
    user_lines = []

    res_prefix = f"___RESULT_{run_token}___"
    mut_marker = f"___MUTATED_{run_token}___"
    mem_marker = f"___LIMIT_MEMORY_{run_token}___"
    out_marker = f"___LIMIT_OUTPUT_{run_token}___"
    disk_marker = f"___LIMIT_DISK_{run_token}___"
    err_prefix = f"___ERROR_{run_token}___"

    for line in (stdout or "").splitlines():
        if line.startswith(res_prefix):
            has_result = True
            payload = line[len(res_prefix):]
            try:
                actual = json.loads(payload)
            except Exception:
                actual = payload
        elif line.strip() == mut_marker:
            mutated = True
        elif line.strip() == mem_marker:
            limit_hit = "memory"
            error_type = "MemoryError"
        elif line.strip() == out_marker:
            limit_hit = "output"
            error_type = "OutputLimitExceeded"
        elif line.strip() == disk_marker:
            limit_hit = "disk"
            error_type = "PermissionError"
        elif line.startswith(err_prefix):
            error_type = line[len(err_prefix):].strip()
        elif line.startswith("___RESULT___"):
            # Legacy Judge0 marker support when run_token == "DEFAULT"
            if run_token == "DEFAULT":
                has_result = True
                payload = line[len("___RESULT___"):]
                try:
                    actual = json.loads(payload)
                except Exception:
                    actual = payload
        elif line.strip() == "___MUTATED_INPUT___" and run_token == "DEFAULT":
            mutated = True
        else:
            user_lines.append(line)

    user_stdout = "\n".join(user_lines).strip()
    return has_result, actual, mutated, limit_hit, error_type, user_stdout


def _normalize_val(val: any) -> any:
    if isinstance(val, (int, float, bool, list, dict, set, tuple)):
        return val
    if isinstance(val, str):
        val_str = val.strip()
        if val_str == "None":
            return None
        try:
            return ast.literal_eval(val_str)
        except Exception:
            return val_str
    return val


def _execute_single_test_sandboxed(
    source_code: str,
    call_expr: str,
    expected_raw: any,
    timeout_seconds: float = 2.0,
    memory_limit_mb: int = 64,
) -> dict:
    """
    Execute learner code in a hardened local sandbox.
    Uses bwrap (namespace isolation: no network, read-only root, isolated /tmp)
    plus POSIX resource limits and Python runtime guardrails.
    Returns dict with outcome, actual_output, duration_ms, limit_hit, mutated,
    printed_stdout, error_type.
    """
    run_token = uuid.uuid4().hex[:12]
    full_source = _build_mutated_source(
        source_code=source_code,
        call_str=call_expr,
        run_token=run_token,
        memory_limit_mb=memory_limit_mb,
        timeout_seconds=timeout_seconds,
        include_guardrails=True,
    )

    python_bin = sys.executable
    clean_env = {
        "PATH": "/usr/bin:/bin",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
    }

    start_time = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="dd_sandbox_") as tmpdir:
        if _BWRAP:
            cmd = [
                _BWRAP,
                "--unshare-all",
                "--die-with-parent",
                "--new-session",
                "--ro-bind", "/", "/",
                "--proc", "/proc",
                "--dev", "/dev",
                "--tmpfs", "/tmp",
                "--chdir", "/tmp",
                "--hostname", "sandbox",
                "--",
                python_bin, "-I", "-B", "-c", full_source,
            ]
            preexec = None
        else:
            cmd = [python_bin, "-I", "-B", "-c", full_source]
            preexec = lambda: _set_resource_limits(timeout_seconds, memory_limit_mb)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=max(1.5, float(timeout_seconds) + 0.5),
                cwd=tmpdir,
                env=clean_env,
                preexec_fn=preexec,
            )
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""

            has_result, actual_output, mutated, limit_hit, error_type, user_stdout = _parse_mutated_output(
                stdout, run_token
            )

            # Check for output flood limit (> 64KB of user stdout or stderr)
            if (
                limit_hit == "output"
                or len(user_stdout.encode("utf-8", errors="ignore")) > MAX_OUTPUT_BYTES
                or len(stderr.encode("utf-8", errors="ignore")) > MAX_OUTPUT_BYTES
            ):
                return {
                    "outcome": "runtime_error",
                    "actual_output": None,
                    "duration_ms": duration_ms,
                    "limit_hit": "output",
                    "mutated": mutated,
                    "printed_stdout": True,
                    "error_type": "OutputLimitExceeded",
                }

            if limit_hit == "memory" or "MemoryError" in stderr:
                return {
                    "outcome": "runtime_error",
                    "actual_output": None,
                    "duration_ms": duration_ms,
                    "limit_hit": "memory",
                    "mutated": mutated,
                    "printed_stdout": bool(user_stdout),
                    "error_type": "MemoryError",
                }

            if limit_hit == "disk":
                return {
                    "outcome": "runtime_error",
                    "actual_output": None,
                    "duration_ms": duration_ms,
                    "limit_hit": "disk",
                    "mutated": mutated,
                    "printed_stdout": bool(user_stdout),
                    "error_type": error_type or "DiskLimitExceeded",
                }

            if proc.returncode != 0:
                if proc.returncode < 0:
                    sig = -proc.returncode
                    if sig == signal.SIGXCPU:
                        return {
                            "outcome": "timeout",
                            "actual_output": None,
                            "duration_ms": duration_ms,
                            "limit_hit": "time",
                            "mutated": False,
                            "printed_stdout": bool(user_stdout),
                            "error_type": "TimeoutError",
                        }
                    if sig == signal.SIGXFSZ:
                        return {
                            "outcome": "runtime_error",
                            "actual_output": None,
                            "duration_ms": duration_ms,
                            "limit_hit": "disk",
                            "mutated": False,
                            "printed_stdout": bool(user_stdout),
                            "error_type": "DiskLimitExceeded",
                        }
                    if sig in (signal.SIGKILL, signal.SIGABRT, signal.SIGSEGV):
                        # Killed by OS RLIMIT_AS or OOM
                        return {
                            "outcome": "runtime_error",
                            "actual_output": None,
                            "duration_ms": duration_ms,
                            "limit_hit": "memory",
                            "mutated": False,
                            "printed_stdout": bool(user_stdout),
                            "error_type": "MemoryError",
                        }
                return {
                    "outcome": "runtime_error",
                    "actual_output": None,
                    "duration_ms": duration_ms,
                    "limit_hit": limit_hit,
                    "mutated": mutated,
                    "printed_stdout": bool(user_stdout),
                    "error_type": error_type or "RuntimeError",
                }

            # If process exited 0 without producing our secret result marker (e.g. sys.exit(0))
            if not has_result:
                return {
                    "outcome": "runtime_error",
                    "actual_output": None,
                    "duration_ms": duration_ms,
                    "limit_hit": None,
                    "mutated": mutated,
                    "printed_stdout": bool(user_stdout),
                    "error_type": "EarlyExitError",
                }

            norm_actual = _normalize_val(actual_output)
            norm_expected = _normalize_val(expected_raw)

            # A test is passed only if the return value matches expected AND input was not mutated
            if norm_actual == norm_expected and not mutated:
                outcome = "passed"
            else:
                outcome = "wrong_output"

            return {
                "outcome": outcome,
                "actual_output": actual_output,
                "duration_ms": duration_ms,
                "limit_hit": None,
                "mutated": mutated,
                "printed_stdout": bool(user_stdout),
                "error_type": None,
            }

        except subprocess.TimeoutExpired:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return {
                "outcome": "timeout",
                "actual_output": None,
                "duration_ms": duration_ms,
                "limit_hit": "time",
                "mutated": False,
                "printed_stdout": False,
                "error_type": "TimeoutError",
            }
        except Exception as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("Sandbox execution exception: %s", exc)
            return {
                "outcome": "runtime_error",
                "actual_output": None,
                "duration_ms": duration_ms,
                "limit_hit": None,
                "mutated": False,
                "printed_stdout": False,
                "error_type": type(exc).__name__,
            }


async def _run_one_test_judge0(client, base_url, headers, source_code, call, expected, timeout_ms):
    """Run a single test case via Judge0."""
    run_token = uuid.uuid4().hex[:12]
    full_source = _build_mutated_source(source_code, call, run_token=run_token, include_guardrails=False)
    token = await _submit(client, base_url, headers, full_source)
    timeout = float(timeout_ms) / 1000.0 if timeout_ms else 5.0
    result = await _poll(client, base_url, headers, token, timeout, run_token=run_token)
    outcome = result["outcome"]
    actual_output = result.get("actual_output")
    mutated = result.get("mutated", False)
    if outcome == "passed":
        norm_actual = _normalize_val(actual_output)
        norm_expected = _normalize_val(expected)
        if norm_actual != norm_expected or mutated:
            outcome = "wrong_output"
    return {
        "outcome": outcome,
        "actual_output": actual_output,
        "duration_ms": result.get("duration_ms"),
        "limit_hit": result.get("limit_hit"),
        "mutated": mutated,
        "printed_stdout": result.get("printed_stdout", False),
        "error_type": result.get("error_type"),
    }


async def _execute_local_fallback(
    source_code: str,
    test_cases: list[dict],
    default_timeout: float,
    memory_limit_mb: int = 64,
) -> list[dict]:
    # Fast syntax check
    try:
        ast.parse(source_code)
    except SyntaxError:
        return [
            {
                "test_case_id": tc["id"],
                "visibility": tc["visibility"],
                "outcome": "runtime_error",
                "actual_output": None,
                "duration_ms": 0,
                "limit_hit": None,
                "mutated": False,
                "printed_stdout": False,
                "error_type": "SyntaxError",
            }
            for tc in test_cases
        ]

    results = []
    for tc in test_cases:
        call = _get_call_from_testcase(tc)
        expected = tc.get("expected_output", "")
        tc_timeout_ms = tc.get("timeout_ms")
        tc_timeout = float(tc_timeout_ms) / 1000.0 if tc_timeout_ms else min(default_timeout, 2.0)

        res = await asyncio.to_thread(
            _execute_single_test_sandboxed,
            source_code,
            call,
            expected,
            tc_timeout,
            memory_limit_mb,
        )
        results.append({
            "test_case_id": tc["id"],
            "visibility": tc["visibility"],
            "outcome": res["outcome"],
            "actual_output": res["actual_output"] if tc["visibility"] == "visible" else None,
            "duration_ms": res.get("duration_ms"),
            "limit_hit": res.get("limit_hit"),
            "mutated": res.get("mutated", False),
            "printed_stdout": res.get("printed_stdout", False),
            "error_type": res.get("error_type"),
        })
    return results


async def run_code(source_code: str, test_cases: list[dict]) -> list[dict]:
    """
    Execute source_code against each test_case.
    Uses the hardened local sandbox (bwrap + POSIX resource limits + runtime guardrails)
    for deterministic, low-latency containment and exact limit classification.
    Falls back to Judge0 REST API only if local execution is disabled via env.
    """
    settings = get_settings()
    default_timeout = settings.runner_timeout_seconds
    mem_limit = int(settings.runner_memory_limit_mb)

    if os.environ.get("USE_REMOTE_JUDGE0", "").lower() not in ("1", "true", "yes"):
        return await _execute_local_fallback(source_code, test_cases, default_timeout, mem_limit)

    base_url = settings.runner_base_url.rstrip("/")
    api_key = settings.runner_api_key
    if not api_key:
        return await _execute_local_fallback(source_code, test_cases, default_timeout, mem_limit)

    prepared = []
    for tc in test_cases:
        call = _get_call_from_testcase(tc)
        expected = str(tc.get("expected_output", ""))
        prepared.append((tc, call, expected))

    results = []
    judge0_available = False

    if api_key:
        host = urlparse(base_url).hostname or base_url
        headers = {
            "Content-Type": "application/json",
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": host,
        }
        try:
            async with httpx.AsyncClient(timeout=default_timeout) as client:
                for tc, call, expected in prepared:
                    tc_timeout_ms = tc.get("timeout_ms")
                    result = await _run_one_test_judge0(
                        client, base_url, headers, source_code, call, expected, tc_timeout_ms
                    )
                    results.append({
                        "test_case_id": tc["id"],
                        "visibility": tc["visibility"],
                        "outcome": result["outcome"],
                        "actual_output": result["actual_output"]
                        if tc["visibility"] == "visible"
                        else None,
                        "duration_ms": result.get("duration_ms"),
                        "limit_hit": result.get("limit_hit"),
                        "mutated": result.get("mutated", False),
                        "printed_stdout": result.get("printed_stdout", False),
                        "error_type": result.get("error_type"),
                    })
            judge0_available = True
        except RunnerUnavailableError:
            logger.warning("Judge0 unavailable; falling back to local sandbox.")
        except Exception as exc:
            logger.error("Judge0 execution error: %s; falling back to local sandbox.", exc)

    if not judge0_available:
        return await _execute_local_fallback(source_code, test_cases, default_timeout, mem_limit)

    return results


async def _submit(client, base_url, headers, source_code):
    """Submit code to Judge0 and return the submission token."""
    url = f"{base_url}/submissions"
    params = {"base64_encoded": "false"}
    payload = {
        "source_code": source_code,
        "language_id": PYTHON_LANGUAGE_ID,
        "stdin": "",
    }
    resp = await client.post(url, params=params, headers=headers, json=payload)
    if resp.status_code >= 400:
        logger.error("Judge0 submission rejected: %s %s", resp.status_code, resp.text[:200])
        raise RunnerUnavailableError(f"Judge0 rejected submission (HTTP {resp.status_code}).")
    data = resp.json()
    token = data.get("token")
    if not token:
        raise RunnerUnavailableError("Judge0 did not return a submission token.")
    return token


async def _poll(client, base_url, headers, token, timeout, run_token: str = "DEFAULT"):
    """Poll Judge0 until the submission finishes, then return the normalized result."""
    url = f"{base_url}/submissions/{token}"
    params = {"base64_encoded": "false"}
    deadline = asyncio.get_event_loop().time() + (timeout or 5.0)
    while True:
        resp = await client.get(url, params=params, headers=headers)
        if resp.status_code >= 400:
            raise RunnerUnavailableError(f"Judge0 poll failed (HTTP {resp.status_code}).")
        data = resp.json()
        status = data.get("status") or {}
        status_id = status.get("id")

        if status_id in (STATUS_IN_QUEUE, STATUS_PROCESSING):
            if asyncio.get_event_loop().time() > deadline:
                return {
                    "outcome": "timeout",
                    "actual_output": None,
                    "duration_ms": None,
                    "limit_hit": "time",
                    "mutated": False,
                    "printed_stdout": False,
                    "error_type": "TimeoutError",
                }
            await asyncio.sleep(0.5)
            continue

        if status_id == STATUS_INTERNAL_ERROR:
            raise RunnerUnavailableError("Judge0 internal error.")

        outcome = _JUDGE0_TO_OUTCOME.get(status_id, "runtime_error")
        stdout = data.get("stdout") or ""
        has_result, actual_output, mutated, limit_hit, error_type, user_stdout = _parse_mutated_output(
            stdout, run_token=run_token
        )
        if outcome == "passed" and not has_result:
            outcome = "runtime_error"

        duration_ms = None
        try:
            duration_ms = int(float(data.get("time") or 0) * 1000)
        except (TypeError, ValueError):
            duration_ms = None

        return {
            "outcome": outcome,
            "actual_output": actual_output,
            "duration_ms": duration_ms,
            "limit_hit": limit_hit or ("time" if outcome == "timeout" else None),
            "mutated": mutated,
            "printed_stdout": bool(user_stdout),
            "error_type": error_type,
        }
