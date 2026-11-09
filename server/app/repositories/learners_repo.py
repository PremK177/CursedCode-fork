from collections import defaultdict

from app.core.logging import get_logger
from app.services.mistake_detector import CORE_MISTAKE_SLUGS

logger = get_logger(__name__)


class LearnersRepo:
    def __init__(self, db):
        self.db = db

    def get_or_create(self, learner_key: str) -> dict:
        resp = (
            self.db.table("learners")
            .select("*")
            .eq("learner_key", learner_key)
            .execute()
        )
        if resp.data:
            row = resp.data[0]
            try:
                self.db.table("learners").update({"last_active_at": "now()"}).eq("id", row["id"]).execute()
            except Exception:
                pass
            return row

        created = (
            self.db.table("learners")
            .insert({"learner_key": learner_key})
            .execute()
        )
        return created.data[0]

    def get_concept_mastery(self, learner_id: str) -> list[dict]:
        try:
            resp = (
                self.db.table("concept_mastery")
                .select("mastery_score, concept_id, concepts(slug, name)")
                .eq("learner_id", learner_id)
                .order("mastery_score", desc=False)
                .execute()
            )
            return resp.data or []
        except Exception as e:
            logger.warning("Could not fetch concept mastery: %s", e)
            return []

    def get_recurring_mistakes(self, learner_id: str) -> list[dict]:
        """Return core mistake categories seen in >= 2 distinct challenges."""
        subs = (
            self.db.table("submissions")
            .select("id, challenge_id")
            .eq("learner_id", learner_id)
            .execute()
        )
        rows = subs.data or []
        if not rows:
            return []
        sub_ids = [r["id"] for r in rows]
        sub_to_challenge = {r["id"]: r["challenge_id"] for r in rows}

        # Map challenge UUIDs to slugs for human-readable evidence
        chals_resp = self.db.table("challenges").select("id, slug").execute()
        uuid_to_slug = {c["id"]: c["slug"] for c in (chals_resp.data or [])}

        mistakes = (
            self.db.table("submission_mistakes")
            .select("submission_id, mistake_categories(slug)")
            .in_("submission_id", sub_ids)
            .execute()
        )

        cat_challenges: dict[str, set] = defaultdict(set)
        for m in (mistakes.data or []):
            cat = (m.get("mistake_categories") or {}).get("slug")
            if not cat or cat not in CORE_MISTAKE_SLUGS:
                continue
            challenge_id = sub_to_challenge.get(m["submission_id"])
            if challenge_id:
                slug = uuid_to_slug.get(challenge_id, str(challenge_id))
                cat_challenges[cat].add(slug)

        result = [
            {
                "slug": cat,
                "challenge_count": len(chals),
                "challenges": sorted(chals),
            }
            for cat, chals in cat_challenges.items()
            if len(chals) >= 2
        ]
        result.sort(key=lambda x: (-x["challenge_count"], x["slug"]))
        return result
