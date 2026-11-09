from fastapi import APIRouter, Depends
from app.integrations.supabase_client import get_supabase
from app.repositories.submissions_repo import SubmissionsRepo
from app.repositories.challenges_repo import ChallengesRepo
from app.schemas.hint import HintRequest, HintResponse
from app.services.hint_generator import generate_dynamic_hint
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/hint", tags=["hints"])

MAX_HINTS = 4


@router.post("", response_model=HintResponse)
async def get_hint(body: HintRequest, db=Depends(get_supabase)):
    sub_repo = SubmissionsRepo(db)
    chal_repo = ChallengesRepo(db)

    sub = sub_repo.get_by_public_id(body.submission_id)
    challenge = chal_repo.get_by_slug(sub["challenge_id"])

    current_hints = int(sub.get("hints_requested") or 0)
    if body.level and 1 <= body.level <= min(current_hints + 1, MAX_HINTS):
        next_level = body.level
    else:
        next_level = min(current_hints + 1, MAX_HINTS)

    # Collect mistake tags
    mistake_tags = []
    try:
        mistakes_resp = (
            db.table("submission_mistakes")
            .select("mistake_categories(slug)")
            .eq("submission_id", sub["id"])
            .execute()
        )
        for row in mistakes_resp.data or []:
            mc = row.get("mistake_categories")
            if isinstance(mc, dict) and mc.get("slug"):
                mistake_tags.append(mc["slug"])
    except Exception as exc:
        logger.warning("Could not load submission mistakes: %s", exc)

    # Collect safe visible test failure evidence (never hidden tests)
    visible_evidence = []
    try:
        tr_resp = (
            db.table("test_results")
            .select("test_case_id, outcome, actual_output")
            .eq("submission_id", sub["id"])
            .execute()
        )
        c_uuid = challenge.get("uuid") or challenge.get("id")
        tc_resp = (
            db.table("test_cases")
            .select("id, description, expected_output, visibility")
            .eq("challenge_id", c_uuid)
            .execute()
        )
        tc_map = {tc["id"]: tc for tc in (tc_resp.data or []) if tc.get("visibility") == "visible"}
        for tr in tr_resp.data or []:
            tc = tc_map.get(tr.get("test_case_id"))
            if tc:
                visible_evidence.append({
                    "call": tc.get("description", ""),
                    "expected": str(tc.get("expected_output", "")),
                    "got": str(tr.get("actual_output", "")) if tr.get("actual_output") is not None else None,
                    "outcome": tr.get("outcome", ""),
                })
    except Exception as exc:
        logger.warning("Could not assemble visible test evidence: %s", exc)

    # Collect prior hints up to next_level - 1
    prior_hints = []
    try:
        ph_resp = (
            db.table("challenge_hints")
            .select("hint_level, hint_text")
            .eq("challenge_id", challenge.get("uuid") or challenge.get("id"))
            .order("hint_level")
            .execute()
        )
        prior_hints = [h["hint_text"] for h in (ph_resp.data or []) if h.get("hint_level", 0) < next_level]
    except Exception:
        pass

    # Generate progressive hint (code_patch is only generated if explicitly opted in via include_patch=True)
    source_code = sub.get("source_code", "")
    hint_text, code_patch = await generate_dynamic_hint(
        challenge=challenge,
        source_code=source_code,
        mistake_tags=mistake_tags,
        visible_results=visible_evidence,
        hint_level=next_level,
        prior_hints=prior_hints,
        include_patch=bool(body.include_patch),
    )

    # Record that hint was requested
    if next_level > current_hints:
        sub_repo.update(sub["id"], {"hints_requested": next_level})

    return HintResponse(
        submission_id=body.submission_id,
        hint_index=next_level,
        level=next_level,
        remaining=max(0, MAX_HINTS - next_level),
        hint=hint_text,
        code_patch=code_patch,
    )
