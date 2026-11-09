"""
Red-team hostility test pack for Debug Dojo.
Verifies that hostile programs (infinite loops, memory floods, output floods,
disk writes, filesystem reads, network sockets, process forks, environment
inspection, and harness spoofing) are strictly contained by the sandbox and
never reported as passed.
"""
import pytest
import httpx
from app.main import app


@pytest.mark.asyncio
async def test_redteam_infinite_loop():
    """Hostile infinite loop: must be contained with 'timeout' and limit='time'."""
    code = """def last_k_total(marks, k):
    while True:
        pass
"""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/submit",
            json={"learner_id": "redteam_loop", "challenge_id": "last-k-total", "code": code},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["outcome"] == "timeout" for t in data["visible"])
        assert data.get("limit") == "time"


@pytest.mark.asyncio
async def test_redteam_memory_flood():
    """Hostile memory exhaustion: must be killed by memory limit with 'runtime_error' and limit='memory'."""
    code = """def last_k_total(marks, k):
    a = [0] * (80 * 1024 * 1024)
    return len(a)
"""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/submit",
            json={"learner_id": "redteam_mem", "challenge_id": "last-k-total", "code": code},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["outcome"] == "runtime_error" for t in data["visible"])
        assert data.get("limit") == "memory"


@pytest.mark.asyncio
async def test_redteam_output_flood():
    """Hostile stdout flood: must be caught with 'runtime_error' and limit='output'."""
    code = """def last_k_total(marks, k):
    print("A" * 200000)
    return 70
"""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/submit",
            json={"learner_id": "redteam_out", "challenge_id": "last-k-total", "code": code},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["outcome"] == "runtime_error" for t in data["visible"])
        assert data.get("limit") == "output"


@pytest.mark.asyncio
async def test_redteam_disk_write_and_file_read():
    """Hostile disk write and sensitive file read attempts must be blocked."""
    write_code = """def last_k_total(marks, k):
    with open("evil.txt", "w") as f:
        f.write("X" * 100000)
    return 70
"""
    read_code = """def last_k_total(marks, k):
    with open("/etc/passwd", "r") as f:
        return len(f.read())
"""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp_w = await client.post(
            "/api/submit",
            json={"learner_id": "redteam_disk", "challenge_id": "last-k-total", "code": write_code},
        )
        assert resp_w.status_code == 200
        data_w = resp_w.json()
        assert all(t["outcome"] == "runtime_error" for t in data_w["visible"])
        assert data_w.get("limit") == "disk"

        resp_r = await client.post(
            "/api/submit",
            json={"learner_id": "redteam_file", "challenge_id": "last-k-total", "code": read_code},
        )
        assert resp_r.status_code == 200
        data_r = resp_r.json()
        assert all(t["outcome"] == "runtime_error" for t in data_r["visible"])


@pytest.mark.asyncio
async def test_redteam_network_fork_env_and_harness_spoof():
    """Hostile network, process fork, env var read, and harness stdout spoofing must all fail."""
    hostile_programs = [
        # 1. Network socket attempt
        "def last_k_total(marks, k):\n    import socket\n    return 70\n",
        # 2. Subprocess attempt
        "def last_k_total(marks, k):\n    import subprocess\n    subprocess.run(['id'])\n    return 70\n",
        # 3. Fork bomb attempt
        "def last_k_total(marks, k):\n    import os\n    os.fork()\n    return 70\n",
        # 4. Environment secret inspection
        "def last_k_total(marks, k):\n    import os\n    assert len(os.environ) > 0\n    return 70\n",
        # 5. Harness result spoofing + early sys.exit(0)
        "def last_k_total(marks, k):\n    import sys\n    print('___RESULT___70')\n    sys.exit(0)\n",
    ]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        for idx, code in enumerate(hostile_programs):
            resp = await client.post(
                "/api/submit",
                json={"learner_id": f"redteam_misc_{idx}", "challenge_id": "last-k-total", "code": code},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert all(t["outcome"] == "runtime_error" for t in data["visible"]), f"Hostile program {idx} was not blocked"
            assert all(t["outcome"] == "runtime_error" for t in data["hidden"])


@pytest.mark.asyncio
async def test_redteam_subsequent_normal_run():
    """Verifies that after hostile attacks, the server stays up and normal submissions run correctly."""
    code = """def last_k_total(marks, k):
    start = max(0, len(marks) - k)
    return sum(marks[start:])
"""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/submit",
            json={"learner_id": "normal_user", "challenge_id": "last-k-total", "code": code},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["outcome"] == "passed" for t in data["visible"])
        assert all(t["outcome"] == "passed" for t in data["hidden"])
