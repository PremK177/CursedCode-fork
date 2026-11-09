import uuid
import pytest
import httpx
from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_list_challenges_and_four_judge_challenges():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/challenges?learner_id=test_user")
        assert resp.status_code == 200
        challenges = resp.json()
        assert len(challenges) >= 12

        slugs = {c["slug"] for c in challenges}
        # All 4 mandatory judge challenges must exist with exact slugs
        for judge_slug in ("last-k-total", "count-passes", "first-n-squares", "middle-three"):
            assert judge_slug in slugs

        # At least 3 difficulties and at least 4 concepts
        difficulties = {c["difficulty"] for c in challenges}
        concepts = {tag for c in challenges for tag in c.get("tags", [])}
        assert len(difficulties) >= 3
        assert len(concepts) >= 4


@pytest.mark.asyncio
async def test_get_challenge_detail_public_fields_only():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/challenges/last-k-total")
        assert resp.status_code == 200
        data = resp.json()
        assert data["slug"] == "last-k-total"
        assert len(data["visibleTests"]) == 3
        assert data["hiddenTestCount"] == 6

        # Security check: verify no hidden test inputs or expected values are returned
        assert "hiddenTests" not in data
        assert "hidden_tests" not in data
        for vt in data["visibleTests"]:
            assert "test" in vt
            assert "call" in vt
            assert "expected" in vt


@pytest.mark.asyncio
async def test_rohan_example_submission_on_last_k_total():
    """Verifies the exact Rohan story example from debug-dojo.txt Page 4."""
    rohan_code = """def last_k_total(marks, k):
    total = 0
    for i in range(len(marks) - k, len(marks)):
        total += marks[i]
    return total
"""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/submit",
            json={"learner_id": "rohan_example", "challenge_id": "last-k-total", "code": rohan_code},
        )
        assert resp.status_code == 200
        result = resp.json()

        # Visible tests 1..3 all pass
        assert [v["test"] for v in result["visible"]] == [1, 2, 3]
        assert all(v["outcome"] == "passed" for v in result["visible"])

        # Hidden tests numbered 1..6: 3 pass, 1 runtime_error, 2 wrong_output
        assert [h["test"] for h in result["hidden"]] == [1, 2, 3, 4, 5, 6]
        outcomes = [h["outcome"] for h in result["hidden"]]
        assert outcomes == ["passed", "passed", "runtime_error", "wrong_output", "wrong_output", "passed"]

        # Tagged with unhandled_short_input
        assert "unhandled_short_input" in result["mistake_tags"]

        # Hidden results never leak expected, got, or call
        for h in result["hidden"]:
            assert set(h.keys()) == {"test", "outcome"}

        # Plain-language explanation mentions the failure cause without leaking hidden values
        exp_lower = result["explanation"].lower()
        assert "hidden" in exp_lower or "k" in exp_lower or "marks" in exp_lower


@pytest.mark.asyncio
async def test_submit_correct_solutions_for_all_four_judge_challenges():
    solutions = {
        "last-k-total": """def last_k_total(marks, k):
    start = max(0, len(marks) - k)
    return sum(marks[start:])
""",
        "count-passes": """def count_passes(marks):
    return sum(1 for m in marks if m >= 40)
""",
        "first-n-squares": """def first_n_squares(n):
    return [i * i for i in range(1, n + 1)]
""",
        "middle-three": """def middle_three(items):
    if len(items) < 3:
        return list(items)
    mid = len(items) // 2
    return items[mid - 1 : mid + 2]
""",
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        for slug, code in solutions.items():
            resp = await client.post(
                "/api/submit",
                json={"learner_id": f"solver_{slug}", "challenge_id": slug, "code": code},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert all(v["outcome"] == "passed" for v in data["visible"]), f"Visible failed on {slug}"
            assert all(h["outcome"] == "passed" for h in data["hidden"]), f"Hidden failed on {slug}"
            assert data["mistake_tags"] == []


@pytest.mark.asyncio
async def test_outcome_labels_and_mistake_taxonomy():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. boundary_comparison on count-passes
        r_bound = await client.post(
            "/api/submit",
            json={
                "learner_id": "tax_tester",
                "challenge_id": "count-passes",
                "code": "def count_passes(marks):\n    return sum(1 for m in marks if m > 40)\n",
            },
        )
        assert "boundary_comparison" in r_bound.json()["mistake_tags"]

        # 2. off_by_one on first-n-squares
        r_obo = await client.post(
            "/api/submit",
            json={
                "learner_id": "tax_tester",
                "challenge_id": "first-n-squares",
                "code": "def first_n_squares(n):\n    return [i * i for i in range(1, n)]\n",
            },
        )
        assert "off_by_one" in r_obo.json()["mistake_tags"]

        # 3. print_not_return on count-passes
        r_print = await client.post(
            "/api/submit",
            json={
                "learner_id": "tax_tester",
                "challenge_id": "count-passes",
                "code": "def count_passes(marks):\n    print(sum(1 for m in marks if m >= 40))\n",
            },
        )
        assert "print_not_return" in r_print.json()["mistake_tags"]

        # 4. mutates_input on last-k-total
        r_mut = await client.post(
            "/api/submit",
            json={
                "learner_id": "tax_tester",
                "challenge_id": "last-k-total",
                "code": "def last_k_total(marks, k):\n    marks.reverse()\n    return sum(marks[:k])\n",
            },
        )
        assert "mutates_input" in r_mut.json()["mistake_tags"]


@pytest.mark.asyncio
async def test_progressive_hints_and_no_hint_leakage():
    code = """def last_k_total(marks, k):
    total = 0
    for i in range(len(marks) - k, len(marks)):
        total += marks[i]
    return total
"""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        sub = await client.post(
            "/api/submit",
            json={"learner_id": "tester_hints_leak", "challenge_id": "last-k-total", "code": code},
        )
        sub_id = sub.json()["submission_id"]

        hints_collected = []
        for expected_level in (1, 2, 3, 4):
            h_resp = await client.post("/api/hint", json={"submission_id": sub_id})
            assert h_resp.status_code == 200
            h_data = h_resp.json()
            assert h_data["hint_index"] == expected_level
            assert h_data["level"] == expected_level
            assert h_data["remaining"] == 4 - expected_level
            assert h_data.get("code_patch") is None
            assert "```" not in h_data["hint"]
            assert "def last_k_total" not in h_data["hint"]
            hints_collected.append(h_data["hint"])


@pytest.mark.asyncio
async def test_scripted_learner_recurring_mistakes_and_mastery():
    """
    Simulates a learner making:
    - unhandled_short_input on 2 challenges (last-k-total, middle-three) -> RECURRING
    - off_by_one on 2 challenges (first-n-squares, middle-three) -> RECURRING
    - print_not_return on 1 challenge only (count-passes) -> NOT recurring
    - syntax_or_name_error on 1 challenge -> NOT recurring
    Then solving count-passes with 0 hints vs first-n-squares after hints.
    """
    learner_id = f"scripted_{uuid.uuid4().hex[:8]}"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. unhandled_short_input on last-k-total
        await client.post(
            "/api/submit",
            json={
                "learner_id": learner_id,
                "challenge_id": "last-k-total",
                "code": "def last_k_total(marks, k):\n    total = 0\n    for i in range(len(marks) - k, len(marks)):\n        total += marks[i]\n    return total\n",
            },
        )
        # 2. unhandled_short_input + off_by_one on middle-three
        await client.post(
            "/api/submit",
            json={
                "learner_id": learner_id,
                "challenge_id": "middle-three",
                "code": "def middle_three(items):\n    mid = len(items) // 2\n    return items[mid - 1 : mid + 1]\n",
            },
        )
        # 3. off_by_one on first-n-squares (and request a hint!)
        sub_sq = await client.post(
            "/api/submit",
            json={
                "learner_id": learner_id,
                "challenge_id": "first-n-squares",
                "code": "def first_n_squares(n):\n    return [i * i for i in range(1, n)]\n",
            },
        )
        await client.post("/api/hint", json={"submission_id": sub_sq.json()["submission_id"]})

        # 4. One-off print_not_return on count-passes (only 1 challenge -> must NOT be recurring)
        await client.post(
            "/api/submit",
            json={
                "learner_id": learner_id,
                "challenge_id": "count-passes",
                "code": "def count_passes(marks):\n    print(0)\n",
            },
        )
        # 5. One-off syntax error on word-boundary (must NOT be recurring)
        await client.post(
            "/api/submit",
            json={
                "learner_id": learner_id,
                "challenge_id": "word-boundary",
                "code": "def is_at_boundary(sentence, keyword)\n    return True\n",
            },
        )

        # 6. Solve count-passes WITHOUT hints (Comparison concept gets unassisted boost)
        await client.post(
            "/api/submit",
            json={
                "learner_id": learner_id,
                "challenge_id": "count-passes",
                "code": "def count_passes(marks):\n    return sum(1 for m in marks if m >= 40)\n",
            },
        )
        # 7. Solve first-n-squares AFTER hints (Lists concept gets assisted boost)
        await client.post(
            "/api/submit",
            json={
                "learner_id": learner_id,
                "challenge_id": "first-n-squares",
                "code": "def first_n_squares(n):\n    return [i * i for i in range(1, n + 1)]\n",
            },
        )

        # Verify learner profile
        prof_resp = await client.get(f"/api/learner/{learner_id}")
        assert prof_resp.status_code == 200
        prof = prof_resp.json()

        rec_cats = {m["category"] for m in prof["recurring_mistakes"]}
        assert rec_cats == {"unhandled_short_input", "off_by_one"}
        assert "print_not_return" not in rec_cats
        assert "syntax_or_name_error" not in rec_cats

        # Verify mastery: Comparison (solved with 0 hints) > Lists (solved after hints)
        mastery_by_concept = {m["concept"]: m["estimate"] for m in prof["mastery"]}
        assert mastery_by_concept["Comparison"] > mastery_by_concept["Lists"]

        # Verify next_challenge targets a recurring mistake with a reason
        assert prof["next_challenge"] is not None
        assert any(k in prof["next_challenge"]["reason"] for k in ("unhandled_short_input", "off_by_one"))
