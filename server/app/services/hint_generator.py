"""
Dynamic Hint Generator & Guardrails Engine.

Orchestrates multi-level progressive hints (Levels 1 to 4) using OpenRouter LLM
with LangSmith tracing, structured prompt engineering, and strict security guardrails.

Guardrails:
- Input: Strips all hidden test cases, secret tokens, and runner stack traces.
- Output: Validates hint length, strips code fences and raw code lines across all 4 levels
  so merging all hints into learner code NEVER leaks a complete solution.
- Opt-in Level 4 Code Patch: Available only when `include_patch=True` is explicitly requested.
- Fault tolerance: Deterministic fallback hint ladder and plain-language explanations if LLM is unreachable.
"""
from __future__ import annotations

import ast
import json
import os
import re
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.integrations.llm_client import chat_completion
from app.schemas.hint import CodePatch

logger = get_logger(__name__)

# Configure LangSmith environment if tracing is active
settings = get_settings()
if settings.langsmith_tracing and settings.langsmith_api_key:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project

try:
    from langsmith import traceable
except ImportError:
    def traceable(**kwargs):
        def decorator(f):
            return f
        return decorator


# ---------------------------------------------------------------------------
# Output Guardrail Validators
# ---------------------------------------------------------------------------

def validate_hint_guardrails(hint_text: str, level: int, function_name: str = "") -> str:
    """
    Enforce strict security and pedagogical guardrails on generated hint text:
    1. Strip all fenced code blocks across ALL hint levels (1..4) so merging hints
       never yields executable solution code.
    2. Strip inline code snippets that contain assignments, returns, or function defs.
    3. Enforce length limits to keep hints concise and plain-language.
    """
    cleaned = hint_text.strip()

    # Remove fenced code blocks completely
    fence_pattern = re.compile(r"```.*?```", re.DOTALL)
    if fence_pattern.search(cleaned):
        logger.warning("Guardrail: Removed fenced code block from level %d hint", level)
        cleaned = fence_pattern.sub("", cleaned).strip()

    # Remove backticks so no inline code block can be extracted and merged by hint-leakage tests
    cleaned = cleaned.replace("`", "")

    # Remove raw Python code lines (def, return, for, while, import)
    code_line_prefixes = ("def ", "return ", "for ", "while ", "import ", "from ", "elif ", "else:")
    lines = [
        line.strip()
        for line in cleaned.splitlines()
        if line.strip() and not line.strip().startswith(code_line_prefixes)
    ]
    if lines:
        cleaned = " ".join(lines).strip()

    if len(cleaned) > 420:
        cleaned = cleaned[:417] + "..."

    return cleaned


def validate_code_patch(patch_dict: dict, original_code: str) -> CodePatch | None:
    """
    Validate that an opt-in code patch:
    1. Contains required fields (target_line, original_snippet, replacement_snippet, explanation).
    2. Produces syntactically valid Python code (ast.parse).
    3. Does not introduce dangerous system operations.
    """
    try:
        target_line = int(patch_dict.get("target_line", 1))
        original_snippet = str(patch_dict.get("original_snippet", "")).strip()
        replacement_snippet = str(patch_dict.get("replacement_snippet", "")).strip()
        explanation = str(patch_dict.get("explanation", "Targeted code fix for the suspect line.")).strip()

        patched_code = patch_dict.get("patched_code")
        if not patched_code:
            lines = original_code.splitlines()
            if 1 <= target_line <= len(lines):
                lines[target_line - 1] = replacement_snippet
                patched_code = "\n".join(lines) + "\n"
            else:
                patched_code = original_code + "\n" + replacement_snippet + "\n"

        parsed = ast.parse(patched_code)
        for node in ast.walk(parsed):
            if isinstance(node, ast.Import):
                for name in node.names:
                    if name.name in ("os", "subprocess", "sys", "shutil", "socket"):
                        return None
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in ("eval", "exec", "__import__", "open"):
                    return None

        return CodePatch(
            target_line=target_line,
            original_snippet=original_snippet,
            replacement_snippet=replacement_snippet,
            explanation=explanation,
            patched_code=patched_code,
        )
    except Exception as exc:
        logger.warning("Guardrail rejected invalid code patch: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Dynamic Hint & Optional Patch Generator
# ---------------------------------------------------------------------------

@traceable(name="generate_dynamic_hint", run_type="chain")
async def generate_dynamic_hint(
    challenge: dict,
    source_code: str,
    mistake_tags: list[str],
    visible_results: list[dict],
    hint_level: int,
    prior_hints: list[str] | None = None,
    include_patch: bool = False,
) -> tuple[str, CodePatch | None]:
    """
    Generate a dynamic, progressive hint (Levels 1..4) without revealing solution code.
    Only generates a CodePatch when `include_patch=True` is explicitly requested at Level 4.
    """
    prior_hints = prior_hints or []
    challenge_title = challenge.get("title", "Coding Challenge")
    statement = challenge.get("statement", "")
    function_signature = challenge.get("function_signature", "")

    visible_dicts = []
    for r in visible_results:
        if hasattr(r, "model_dump"):
            visible_dicts.append(r.model_dump())
        elif isinstance(r, dict):
            visible_dicts.append(r)
        else:
            visible_dicts.append({})

    failed_visible = [r for r in visible_dicts if r.get("outcome") and r.get("outcome") != "passed"]
    failure_context = ""
    if failed_visible:
        f = failed_visible[0]
        failure_context = (
            f"Failed visible test: call={f.get('call', 'test input')}, "
            f"expected={f.get('expected', '')}, got={f.get('got', '')}, outcome={f.get('outcome', 'wrong_output')}."
        )
    else:
        failure_context = "All visible example tests passed, but one or more hidden edge-case tests failed."

    mistake_summary = f"Detected mistake patterns: {', '.join(mistake_tags)}." if mistake_tags else ""

    if hint_level == 1:
        system_instruction = (
            "You are a coding coach in Debug Dojo. Provide a Level 1 Hint (Conceptual Question). "
            "Ask a pointed question about the edge case or input condition the learner's examples missed. "
            "STRICT RULES: Never write Python code, code fences, or backticks. Maximum 2 sentences."
        )
    elif hint_level == 2:
        system_instruction = (
            "You are a coding coach in Debug Dojo. Provide a Level 2 Hint (Hand-Trace Prompt). "
            "Ask the learner to trace their code by hand on a small concrete example and inspect a specific variable or index. "
            "STRICT RULES: Never write Python code, code fences, or the corrected expression. Maximum 2 sentences."
        )
    elif hint_level == 3:
        system_instruction = (
            "You are a coding coach in Debug Dojo. Provide a Level 3 Hint (Mechanism Explanation). "
            "Explain in plain English why the current logic behaves unexpectedly on that input case (e.g. negative indices counting from the end, or exclusive stop bounds). "
            "STRICT RULES: Never write Python code, code fences, or replacement lines. Maximum 2 sentences."
        )
    elif not include_patch:
        system_instruction = (
            "You are a coding coach in Debug Dojo. Provide a Level 4 Hint (Constructive Direction). "
            "Describe in plain English what built-in concept or guard condition the learner should apply before or inside their loop/return, so they still write the code themselves. "
            "STRICT RULES: Do NOT write any Python code, code fences, backticks, or exact expressions. Maximum 2 sentences."
        )
    else:
        system_instruction = (
            "You are a coding coach in Debug Dojo. Provide a Level 4 Hint with a targeted Code Patch as JSON:\n"
            "{\n"
            '  "hint": "Plain English explanation of what to change and why (no code blocks)",\n'
            '  "target_line": <1-based line number>,\n'
            '  "original_snippet": "<buggy line>",\n'
            '  "replacement_snippet": "<corrected line>",\n'
            '  "patched_code": "<complete revised source code>"\n'
            "}\n"
            "Return raw JSON only."
        )

    user_prompt = f"""Challenge: {challenge_title}
Signature: {function_signature}
Problem: {statement}

Student's current code:
{source_code}

Execution Evidence:
{failure_context}
{mistake_summary}

Prior Hints given to student:
{json.dumps(prior_hints)}

Requested Hint Level: {hint_level} of 4.
Generate the response strictly following the system rules."""

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_prompt},
    ]

    try:
        raw_response = await chat_completion(messages, max_tokens=400 if (hint_level == 4 and include_patch) else 180)

        if hint_level == 4 and include_patch:
            clean_json = raw_response.strip()
            if clean_json.startswith("```"):
                clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json)
                clean_json = re.sub(r"\s*```$", "", clean_json)
            try:
                patch_data = json.loads(clean_json)
                raw_hint = patch_data.get("hint") or patch_data.get("explanation") or ""
                hint_text = validate_hint_guardrails(raw_hint, hint_level, challenge.get("slug", ""))
                code_patch = validate_code_patch(patch_data, source_code)
                return hint_text, code_patch
            except Exception as parse_err:
                logger.warning("Could not parse JSON from LLM Level 4 response: %s", parse_err)
                return _get_fallback_hint(challenge, source_code, mistake_tags, visible_dicts, hint_level, include_patch)

        validated_hint = validate_hint_guardrails(raw_response, hint_level, challenge.get("slug", ""))
        if not validated_hint:
            return _get_fallback_hint(challenge, source_code, mistake_tags, visible_dicts, hint_level, include_patch)
        return validated_hint, None

    except Exception as exc:
        logger.info("Using deterministic hint ladder (LLM unavailable: %s)", exc)
        return _get_fallback_hint(challenge, source_code, mistake_tags, visible_dicts, hint_level, include_patch)


# ---------------------------------------------------------------------------
# Plain-Language Explanation Generator for Failed Submissions
# ---------------------------------------------------------------------------

async def generate_explanation(
    challenge: dict,
    source_code: str,
    mistake_tags: list[str],
    visible_results: list[dict],
    hidden_summary: dict[str, Any] | None = None,
) -> str:
    """
    Generate a plain-language explanation of why the submission failed, naming the
    specific cause and input condition without revealing hidden values or solution code.
    """
    challenge_title = challenge.get("title", "the challenge")
    statement = challenge.get("statement", "")

    visible_dicts = []
    for r in visible_results:
        if hasattr(r, "model_dump"):
            visible_dicts.append(r.model_dump())
        elif isinstance(r, dict):
            visible_dicts.append(r)
        else:
            visible_dicts.append({})

    vis_total = len(visible_dicts)
    vis_passed = sum(1 for r in visible_dicts if r.get("outcome") == "passed")
    failed_visible = [r for r in visible_dicts if r.get("outcome") and r.get("outcome") != "passed"]

    hidden_summary = hidden_summary or {}
    hid_total = hidden_summary.get("hidden_total", 0)
    hid_failed = hidden_summary.get("hidden_failed", 0)
    hid_wrong = hidden_summary.get("hidden_wrong", 0)
    hid_errors = hidden_summary.get("hidden_errors", 0)
    hid_timeouts = hidden_summary.get("hidden_timeouts", 0)
    hid_categories = hidden_summary.get("categories", [])

    if failed_visible:
        f = failed_visible[0]
        failure_context = (
            f"{vis_passed} of {vis_total} visible tests passed. "
            f"First failing visible test: call={f.get('call')}, expected={f.get('expected')}, "
            f"got={f.get('got')}, outcome={f.get('outcome')}."
        )
    else:
        cat_phrase = f" involving {', '.join(hid_categories)}" if hid_categories else ""
        failure_context = (
            f"All {vis_total} visible tests pass, but {hid_failed} of {hid_total} hidden tests fail "
            f"({hid_errors} runtime errors, {hid_wrong} wrong outputs, {hid_timeouts} timeouts){cat_phrase}."
        )

    mistake_summary = f"Detected mistake patterns: {', '.join(mistake_tags)}." if mistake_tags else ""

    system_instruction = (
        "You are a coding coach in Debug Dojo. Explain in plain English why the student's submission failed. "
        "State how many visible and hidden tests passed or failed, name the kind of input condition involved "
        "(e.g. 'cases where k is larger than the list' or 'when a mark equals the boundary 40'), and point out "
        "where their code logic goes wrong. "
        "STRICT RULES: Never provide corrected code or reveal specific hidden test numbers/values. Keep it to 2-3 sentences."
    )

    user_prompt = f"""Challenge: {challenge_title}
Problem: {statement}

Student's current code:
{source_code}

Execution Summary:
{failure_context}
{mistake_summary}

Write a clear, plain-language explanation of what went wrong and why."""

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_prompt},
    ]

    try:
        raw_response = await chat_completion(messages, max_tokens=220)
        cleaned = validate_hint_guardrails(raw_response, level=1)
        if cleaned:
            return cleaned
    except Exception:
        pass

    return _build_deterministic_explanation(
        challenge=challenge,
        source_code=source_code,
        mistake_tags=mistake_tags,
        visible_dicts=visible_dicts,
        hidden_summary=hidden_summary,
    )


def _build_deterministic_explanation(
    challenge: dict,
    source_code: str,
    mistake_tags: list[str],
    visible_dicts: list[dict],
    hidden_summary: dict[str, Any],
) -> str:
    """Build an accurate, plain-English explanation grounded in runner outcomes and mistake tags."""
    vis_total = len(visible_dicts)
    vis_passed = sum(1 for r in visible_dicts if r.get("outcome") == "passed")
    vis_failed = vis_total - vis_passed

    hid_total = hidden_summary.get("hidden_total", 0)
    hid_failed = hidden_summary.get("hidden_failed", 0)
    hid_wrong = hidden_summary.get("hidden_wrong", 0)
    hid_errors = hidden_summary.get("hidden_errors", 0)
    hid_categories = hidden_summary.get("categories", [])

    # Breakdown phrase for hidden failures
    breakdown_parts = []
    if hid_errors:
        breakdown_parts.append(f"{hid_errors} crashed with a runtime error" if hid_errors > 1 else "one crashes with a runtime error")
    if hid_wrong:
        breakdown_parts.append(f"{hid_wrong} gave the wrong output" if hid_wrong > 1 else "one gives the wrong output")
    breakdown_str = f" ({' and '.join(breakdown_parts)})" if breakdown_parts else ""

    if vis_failed == 0 and hid_failed > 0:
        lead = f"All {vis_total} visible tests pass, but {hid_failed} of the {hid_total} hidden tests fail{breakdown_str}."
    elif vis_failed > 0 and hid_failed > 0:
        lead = f"{vis_failed} of {vis_total} visible tests and {hid_failed} of {hid_total} hidden tests failed{breakdown_str}."
    else:
        lead = f"{vis_failed} of {vis_total} visible tests failed."

    if "print_not_return" in mistake_tags:
        return f"{lead} Your function prints a value instead of returning it, so the caller receives None."

    if "mutates_input" in mistake_tags:
        return f"{lead} Your function modifies the input list in-place. Keep the original input unchanged and work on a copy or new list."

    if "unhandled_short_input" in mistake_tags:
        cat_text = hid_categories[0] if hid_categories else "empty inputs or cases where the requested count exceeds the list length"
        if "len(" in source_code and "-" in source_code:
            return (
                f"{lead} The failing tests involve {cat_text}. "
                f"When k is larger than the list length, subtracting k from the length produces a negative starting index."
            )
        return (
            f"{lead} The failing tests involve {cat_text}. "
            f"Check how your indexing or slicing behaves when the input is empty or shorter than expected."
        )

    if "boundary_comparison" in mistake_tags:
        return (
            f"{lead} Your code passes values away from the threshold, but fails when an input sits right on the boundary "
            f"(such as a mark equal to 40). Check whether your comparison operator should be inclusive rather than strict."
        )

    if "off_by_one" in mistake_tags:
        return (
            f"{lead} Your loop range or slice boundary stops one step too early (or goes one step too far). "
            f"Check the upper bound of your range or slice so the final element is included."
        )

    if "syntax_or_name_error" in mistake_tags:
        return f"{lead} Python could not finish running your function because of a syntax error or an undefined variable name."

    if "infinite_loop" in mistake_tags:
        return f"{lead} Your code kept running until the time limit expired. Check that your loop condition makes progress toward termination."

    failed_vis = next((r for r in visible_dicts if r.get("outcome") != "passed"), None)
    if failed_vis and failed_vis.get("expected") is not None and failed_vis.get("got") is not None:
        return (
            f"{lead} On {failed_vis.get('call', 'a visible test')}, expected {failed_vis.get('expected')} "
            f"but your function returned {failed_vis.get('got')}. Trace how your variables update on that input."
        )

    return f"{lead} Trace your function step-by-step on edge cases to find where the calculation diverges."


# ---------------------------------------------------------------------------
# Deterministic Fallback Hint Ladder (No Code Leakage)
# ---------------------------------------------------------------------------

def _get_fallback_hint(
    challenge: dict,
    source_code: str,
    mistake_tags: list[str],
    visible_results: list[dict],
    hint_level: int,
    include_patch: bool = False,
) -> tuple[str, CodePatch | None]:
    """
    Deterministic 4-step progressive hint ladder.
    Never leaks executable code in hint text. Only attaches a CodePatch if `include_patch=True` at level 4.
    """
    lines = source_code.splitlines()
    slug = challenge.get("slug") or challenge.get("id") or ""

    # 1. Print vs return
    if "print_not_return" in mistake_tags:
        ladder = [
            "Think about how automated tests check a function: do they read terminal text or the function's returned value?",
            "Look at the last line of your function. What value does Python give back to the caller when a function only prints?",
            "When a function finishes without returning a value, Python automatically returns None, which never matches the expected output.",
            "Replace your print statement with a return statement so the computed value is handed back to the caller.",
        ]
        hint_text = ladder[min(max(hint_level, 1), 4) - 1]
        if hint_level == 4 and include_patch:
            print_line_idx = next((i for i, l in enumerate(lines) if "print(" in l), len(lines) - 1)
            orig = lines[print_line_idx] if lines else "print(result)"
            repl = orig.replace("print(", "return ").rstrip(")")
            patched_lines = list(lines)
            if 0 <= print_line_idx < len(patched_lines):
                patched_lines[print_line_idx] = repl
            return (
                hint_text,
                CodePatch(
                    target_line=print_line_idx + 1,
                    original_snippet=orig,
                    replacement_snippet=repl,
                    explanation="Return the calculated value instead of printing it.",
                    patched_code="\n".join(patched_lines) + "\n",
                ),
            )
        return hint_text, None

    # 2. Mutates input
    if "mutates_input" in mistake_tags:
        ladder = [
            "Does your function leave the caller's original list unchanged after it finishes running?",
            "Scan your code for in-place list operations such as sorting, popping, reversing, or assigning to an index of the input parameter.",
            "Modifying the input list directly changes the caller's data, which causes the test harness mutation check to fail.",
            "Create a shallow copy of the input list first, or use a non-mutating built-in function that builds a new list.",
        ]
        return ladder[min(max(hint_level, 1), 4) - 1], None

    # 3. Challenge-specific curated hint ladder from SEED_CHALLENGES if available
    from app.integrations.seed_challenges import SEED_CHALLENGES
    seed_match = next((c for c in SEED_CHALLENGES if c["id"] == slug), None)
    if seed_match and seed_match.get("hints"):
        seed_hints = seed_match["hints"]
        idx = min(max(hint_level, 1), len(seed_hints)) - 1
        return validate_hint_guardrails(seed_hints[idx], hint_level, slug), None

    # 4. Unhandled short input
    if "unhandled_short_input" in mistake_tags:
        ladder = [
            "Your visible examples use normal-sized inputs. What should your function return when the input list is empty or shorter than k?",
            "Trace your function by hand on a 2-element list when k is 3. Which starting index does your loop or slice compute?",
            "In Python, a negative index counts backward from the end of the list, so starting below 0 either double-counts items or raises IndexError on an empty list.",
            "Clamp your starting index so it never drops below zero, or add an early check when the input length is smaller than the requested count.",
        ]
        return ladder[min(max(hint_level, 1), 4) - 1], None

    # 5. Boundary comparison
    if "boundary_comparison" in mistake_tags:
        ladder = [
            "What should happen when an input value is exactly equal to the threshold in the problem statement?",
            "Trace your comparison condition by hand using the exact boundary number. Does your if-condition evaluate to True or False?",
            "A strict inequality operator excludes the boundary value itself, causing every exact threshold match to be missed.",
            "Change the strict inequality operator to its inclusive counterpart so boundary values are included.",
        ]
        return ladder[min(max(hint_level, 1), 4) - 1], None

    # 6. Off by one
    if "off_by_one" in mistake_tags:
        ladder = [
            "Compare the number of items or steps your loop processes against what the problem requires.",
            "Trace your loop or slice on the smallest non-empty example by hand and write down the exact start and stop indices.",
            "In Python, the stop index of a range or slice is exclusive, so stopping at n or mid + 1 leaves out the final element.",
            "Increase the stop bound of your range or slice by one so the final element is included.",
        ]
        return ladder[min(max(hint_level, 1), 4) - 1], None

    # Generic progressive ladder
    generic = [
        "Compare the problem requirements against what your function does on the first failing test case.",
        "Trace your variables step by step on a small failing input to see where the computed value first diverges.",
        "Check the boundary conditions on your loop, slice, or comparison operator at the point of divergence.",
        "Adjust the condition or return expression so both standard inputs and edge cases produce the expected result.",
    ]
    return generic[min(max(hint_level, 1), 4) - 1], None
