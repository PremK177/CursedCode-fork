from fastapi import APIRouter, Depends
from app.integrations.supabase_client import get_supabase
from app.repositories.learners_repo import LearnersRepo
from app.repositories.challenges_repo import ChallengesRepo
from app.schemas.learner import LearnerResponse, RecurringMistake, ConceptMastery, NextChallenge
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/learner", tags=["learner"])

STANDARD_CONCEPTS = [
    ("Lists", "lists"),
    ("Loops", "loops"),
    ("Strings", "strings"),
    ("Slicing", "slicing"),
    ("Indexing", "indexing"),
    ("Comparison", "comparison"),
]

MISTAKE_TARGET_CHALLENGES = {
    "unhandled_short_input": ["common-start", "middle-three", "last-k-total", "word-boundary", "pair-sum"],
    "boundary_comparison": ["word-boundary", "count-passes", "missing-step", "streak-counter"],
    "off_by_one": ["missing-step", "first-n-squares", "middle-three", "streak-counter", "last-k-total"],
    "print_not_return": ["streak-counter", "count-passes", "first-n-squares", "last-k-total"],
    "mutates_input": ["pair-sum", "middle-three", "last-k-total", "common-start"],
}

MISTAKE_PRACTICE_DESCRIPTIONS = {
    "unhandled_short_input": "handling empty or short inputs without out-of-range indexing",
    "boundary_comparison": "inclusive versus strict boundary comparisons at exact threshold values",
    "off_by_one": "loop and slice stop bounds so the final element is neither missed nor double-counted",
    "print_not_return": "returning the computed result directly from the function instead of printing it",
    "mutates_input": "preserving caller input collections without in-place mutation",
}


def score_to_grade_and_difficulty(score: float) -> tuple[str, str]:
    """Derives grade and difficulty tier from a 0..1 mastery estimate."""
    if score < 0.20:
        return "Grade 4", "Easy"
    elif score < 0.40:
        return "Grade 3", "Medium"
    elif score < 0.60:
        return "Grade 2", "Hard"
    elif score < 0.80:
        return "Semi-Grade 1", "Advanced"
    elif score < 0.93:
        return "Grade 1", "Expert"
    else:
        return "Special Grade", "Supreme"


@router.get("/{learner_id}", response_model=LearnerResponse)
async def get_learner(learner_id: str, db=Depends(get_supabase)):
    repo = LearnersRepo(db)
    challenges_repo = ChallengesRepo(db)

    learner = repo.get_or_create(learner_id)
    learner_uuid = learner["id"]

    # Raw mastery from db
    raw_mastery = repo.get_concept_mastery(learner_uuid)
    mastery_map = {}
    for row in raw_mastery:
        slug = row.get("concepts", {}).get("slug") if isinstance(row.get("concepts"), dict) else None
        if slug:
            mastery_map[slug.lower()] = round(float(row.get("mastery_score", 0)) / 100, 2)

    mastery_list = []
    for display_name, slug in STANDARD_CONCEPTS:
        est = mastery_map.get(slug, 0.0)
        grade, diff = score_to_grade_and_difficulty(est)
        mastery_list.append(
            ConceptMastery(
                concept=display_name,
                estimate=est,
                score=est,
                grade=grade,
                difficulty=diff,
            )
        )

    # Recurring mistakes (seen in >= 2 distinct challenges)
    raw_mistakes = repo.get_recurring_mistakes(learner_uuid)
    recurring = [
        RecurringMistake(
            category=r["slug"],
            tag=r["slug"],
            challenge_count=r["challenge_count"],
            challenges=r.get("challenges", []),
        )
        for r in raw_mistakes
        if r.get("challenge_count", 0) >= 2
    ]

    # Next challenge recommendation targeted to recurring mistakes or lowest mastery concept
    published_challenges = challenges_repo.list_published(learner_id=learner_id)
    by_slug = {c["slug"]: c for c in published_challenges}
    unsolved = [c for c in published_challenges if c.get("status") != "Solved"]

    target = None
    reason = ""

    if recurring and published_challenges:
        top_mistake = recurring[0]
        cat = top_mistake.category
        candidate_slugs = MISTAKE_TARGET_CHALLENGES.get(cat, [])
        # Prefer an unsolved challenge from candidate_slugs that isn't already in the failed challenges list if possible
        for slug in candidate_slugs:
            cand = by_slug.get(slug)
            if cand and cand.get("status") != "Solved" and slug not in top_mistake.challenges:
                target = cand
                break
        if not target:
            for slug in candidate_slugs:
                cand = by_slug.get(slug)
                if cand and cand.get("status") != "Solved":
                    target = cand
                    break
        if not target:
            target = unsolved[0] if unsolved else published_challenges[0]

        practice_desc = MISTAKE_PRACTICE_DESCRIPTIONS.get(cat, cat)
        chals_str = ", ".join(top_mistake.challenges[:3])
        reason = (
            f"Chosen to practise {practice_desc} ({cat}), which recurred across "
            f"{top_mistake.challenge_count} different challenges ({chals_str})."
        )
    elif published_challenges:
        # Target lowest mastery concept
        weakest = min(mastery_list, key=lambda m: m.estimate)
        for c in unsolved:
            if weakest.concept in (c.get("tags") or []):
                target = c
                break
        if not target:
            target = unsolved[0] if unsolved else published_challenges[0]
        reason = (
            f"Recommended to build mastery in {weakest.concept} "
            f"(current score {weakest.estimate:.2f}) with edge-case practice."
        )

    next_challenge = None
    if target:
        next_challenge = NextChallenge(
            challenge_id=target["slug"],
            title=target["title"],
            grade=target.get("grade", "Grade 4"),
            difficulty=target.get("difficulty", "Easy"),
            reason=reason,
        )

    return LearnerResponse(
        learner_id=learner_id,
        recurring_mistakes=recurring,
        mastery=mastery_list,
        next_challenge=next_challenge,
    )
