from fastapi import APIRouter, Depends

from app.integrations.supabase_client import get_supabase
from app.repositories.challenges_repo import ChallengesRepo
from app.repositories.submissions_repo import SubmissionsRepo
from app.repositories.learners_repo import LearnersRepo
from app.integrations.runner_client import run_code
from app.schemas.submission import SubmitRequest, SubmitResponse, VisibleResult, HiddenResult
from app.core.logging import get_logger
from app.services.hint_generator import generate_explanation
from app.services.mistake_detector import detect_mistakes, summarize_hidden_failure_patterns

logger = get_logger(__name__)
router = APIRouter(prefix="/submit", tags=["submissions"])


def get_db(db=Depends(get_supabase)):
    return db


@router.post("", response_model=SubmitResponse)
async def submit(body: SubmitRequest, db=Depends(get_db)):
    challenges_repo = ChallengesRepo(db)
    submissions_repo = SubmissionsRepo(db)
    learners_repo = LearnersRepo(db)

    # Resolve learner (get or create)
    learner = learners_repo.get_or_create(body.learner_id)
    learner_uuid = learner["id"]

    # Resolve challenge (supports canonical slug and aliases)
    challenge = challenges_repo.get_by_slug(body.challenge_id)
    challenge_uuid = challenge.get("uuid") or challenge["id"]
    canonical_slug = challenge.get("slug", body.challenge_id)

    # Fetch test cases (kept entirely server-side)
    test_cases = challenges_repo.get_test_cases(challenge_uuid)

    # Create pending submission record
    sub = submissions_repo.create(learner_uuid, challenge_uuid, body.code)
    sub_uuid = sub["id"]
    public_id = sub["public_id"]

    # Run code in hardened sandbox
    raw_results = await run_code(body.code, test_cases)

    # Tally results (visible tests numbered 1..V, hidden tests numbered 1..H per spec)
    visible_results: list[VisibleResult] = []
    hidden_results: list[HiddenResult] = []
    db_results = []
    visible_passed = visible_total = hidden_passed = hidden_total = 0
    limit_hit = None

    for tc, res in zip(test_cases, raw_results):
        outcome = res["outcome"]
        vis = tc["visibility"]
        if res.get("limit_hit") and not limit_hit:
            limit_hit = res["limit_hit"]
        elif outcome == "timeout" and not limit_hit:
            limit_hit = "time"

        db_results.append(
            {
                "submission_id": sub_uuid,
                "test_case_id": tc["id"],
                "outcome": outcome,
                "actual_output": (
                    str(res.get("actual_output"))
                    if (vis == "visible" and res.get("actual_output") is not None)
                    else None
                ),
                "duration_ms": res.get("duration_ms"),
                "resource_limit_hit": res.get("limit_hit"),
            }
        )

        if vis == "visible":
            visible_total += 1
            if outcome == "passed":
                visible_passed += 1
            visible_results.append(
                VisibleResult(
                    test=visible_total,
                    call=tc.get("description"),
                    expected=str(tc["expected_output"]),
                    got=str(res.get("actual_output")) if res.get("actual_output") is not None else None,
                    outcome=outcome,
                )
            )
        else:
            hidden_total += 1
            if outcome == "passed":
                hidden_passed += 1
            hidden_results.append(HiddenResult(test=hidden_total, outcome=outcome))

    overall_passed = (visible_passed == visible_total and hidden_passed == hidden_total)

    # Persist test results
    submissions_repo.insert_test_results(db_results)

    # Detect mistake categories deterministically
    mistake_tags: list[str] = []
    if not overall_passed:
        mistake_tags = detect_mistakes(
            challenge_slug=canonical_slug,
            source_code=body.code,
            test_cases=test_cases,
            raw_results=raw_results,
        )

        # Record mistakes in database
        try:
            mistakes_to_insert = []
            for tag in mistake_tags:
                cat_resp = db.table("mistake_categories").select("id").eq("slug", tag).execute()
                if cat_resp.data:
                    mistakes_to_insert.append({
                        "submission_id": sub_uuid,
                        "mistake_category_id": cat_resp.data[0]["id"],
                        "confidence": 0.92,
                        "evidence_summary": f"Detected pattern: {tag}",
                        "detected_by": "rules",
                    })
            submissions_repo.insert_mistakes(mistakes_to_insert)
        except Exception as e:
            logger.warning("Could not persist submission mistakes: %s", e)

    # Update concept mastery (a pass without hints counts for more than a pass after hints)
    max_hints = 0
    try:
        from app.integrations.seed_challenges import SEED_CHALLENGES
        seed_match = next((c for c in SEED_CHALLENGES if c["id"] == canonical_slug), None)
        tags = seed_match.get("tags", []) if seed_match else challenge.get("tags", [])

        learner_subs = (
            db.table("submissions")
            .select("hints_requested")
            .eq("learner_id", learner_uuid)
            .eq("challenge_id", challenge_uuid)
            .execute()
        )
        max_hints = max(
            (int(s.get("hints_requested") or 0) for s in (learner_subs.data or [])),
            default=0,
        )
        independent_pass = overall_passed and max_hints == 0

        for tag in tags:
            tag_slug = tag.lower()
            conc_resp = db.table("concepts").select("id").eq("slug", tag_slug).execute()
            if conc_resp.data:
                conc_id = conc_resp.data[0]["id"]
                cm_resp = (
                    db.table("concept_mastery")
                    .select("*")
                    .eq("learner_id", learner_uuid)
                    .eq("concept_id", conc_id)
                    .execute()
                )
                if cm_resp.data:
                    cm = cm_resp.data[0]
                    attempts = int(cm.get("attempts") or 0) + 1
                    successes = int(cm.get("successful_attempts") or 0) + (1 if overall_passed else 0)
                    indep = int(cm.get("independent_successes") or 0) + (1 if independent_pass else 0)
                    current_score = float(cm.get("mastery_score") or 0.0) / 100.0
                    if overall_passed:
                        delta = 0.35 if independent_pass else max(0.08, 0.18 - 0.03 * max_hints)
                        updated_ratio = min(1.0, max(current_score + delta, (successes * 0.55 + indep * 0.45) / max(1, attempts)))
                    else:
                        updated_ratio = max(0.0, current_score - 0.05)
                    new_score = round(updated_ratio * 100, 1)
                    db.table("concept_mastery").update({
                        "attempts": attempts,
                        "successful_attempts": successes,
                        "independent_successes": indep,
                        "mastery_score": new_score,
                    }).eq("learner_id", learner_uuid).eq("concept_id", conc_id).execute()
                else:
                    successes = 1 if overall_passed else 0
                    indep = 1 if independent_pass else 0
                    initial_ratio = 0.75 if independent_pass else (0.45 if overall_passed else 0.0)
                    new_score = round(initial_ratio * 100, 1)
                    db.table("concept_mastery").insert({
                        "learner_id": learner_uuid,
                        "concept_id": conc_id,
                        "attempts": 1,
                        "successful_attempts": successes,
                        "independent_successes": indep,
                        "mastery_score": new_score,
                    }).execute()
    except Exception as e:
        logger.warning("Could not update concept mastery: %s", e)

    # Explanation text
    if overall_passed:
        if max_hints == 0:
            explanation = "All tests passed with no hints. Nice work."
        else:
            explanation = "All tests passed. Next time, try with one hint fewer."
    elif limit_hit in ("memory", "output", "disk"):
        explanation = (
            f"Runtime error: {limit_hit} limit exceeded. "
            f"Your program was stopped because it exceeded the sandbox {limit_hit} limit."
        )
    elif limit_hit == "time":
        explanation = (
            "Execution timed out (time limit exceeded). "
            "Check your loop conditions to make sure every iteration progresses toward termination."
        )
    else:
        hidden_summary = summarize_hidden_failure_patterns(test_cases, raw_results)
        challenge_ctx = {
            "title": challenge.get("title", "the challenge"),
            "statement": challenge.get("statement", ""),
            "slug": canonical_slug,
            "function_signature": challenge.get("function_signature", ""),
        }
        explanation = await generate_explanation(
            challenge=challenge_ctx,
            source_code=body.code,
            mistake_tags=mistake_tags,
            visible_results=visible_results,
            hidden_summary=hidden_summary,
        )

    # Update submission record
    submissions_repo.update(
        sub_uuid,
        {
            "status": "completed",
            "visible_passed": visible_passed,
            "visible_total": visible_total,
            "hidden_passed": hidden_passed,
            "hidden_total": hidden_total,
            "overall_passed": 1 if overall_passed else 0,
            "resource_limit_hit": limit_hit,
            "explanation": explanation,
        },
    )

    return SubmitResponse(
        submission_id=public_id,
        learner_id=body.learner_id,
        challenge_id=body.challenge_id,
        visible=visible_results,
        hidden=hidden_results,
        mistake_tags=mistake_tags,
        explanation=explanation,
        limit=limit_hit,
        automatic_hint=None,
    )
