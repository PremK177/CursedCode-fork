import json
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.integrations.seed_challenges import SEED_CHALLENGES

logger = get_logger(__name__)

DIFF_TO_FRONTEND = {
    "beginner": ("Grade 4", "Easy"),
    "intermediate": ("Grade 3", "Medium"),
    "advanced": ("Grade 2", "Hard"),
}


SLUG_ALIASES = {
    "countpasses": "count-passes",
    "count_passes": "count-passes",
    "middlethree": "middle-three",
    "middle_three": "middle-three",
    "last_k_total": "last-k-total",
    "lastktotal": "last-k-total",
    "first_n_squares": "first-n-squares",
    "firstnsquares": "first-n-squares",
}


class ChallengesRepo:
    def __init__(self, db):
        self.db = db
        self.seed_map = {c["id"]: c for c in SEED_CHALLENGES}
        for alias, target in SLUG_ALIASES.items():
            if target in self.seed_map:
                self.seed_map[alias] = self.seed_map[target]

    def list_published(self, learner_id: str | None = None) -> list[dict]:
        # Only select columns guaranteed to exist in schema 17-schema.md
        resp = (
            self.db.table("challenges")
            .select("id, slug, title, statement, starter_code, difficulty, sort_order")
            .eq("is_published", True)
            .order("sort_order")
            .execute()
        )
        challenges = resp.data or []

        # Get learner submissions status if learner_id is provided
        submission_status_map = {}
        if learner_id:
            try:
                learner_resp = self.db.table("learners").select("id").eq("learner_key", learner_id).execute()
                if learner_resp.data:
                    l_uuid = learner_resp.data[0]["id"]
                    subs_resp = (
                        self.db.table("submissions")
                        .select("challenge_id, overall_passed")
                        .eq("learner_id", l_uuid)
                        .execute()
                    )
                    for s in subs_resp.data or []:
                        cid = str(s["challenge_id"])
                        if s.get("overall_passed"):
                            submission_status_map[cid] = "Solved"
                        elif cid not in submission_status_map:
                            submission_status_map[cid] = "Attempted"
            except Exception as e:
                logger.warning("Could not calculate submission statuses: %s", e)

        result = []
        for ch in challenges:
            cid = str(ch["id"])
            slug = ch["slug"]
            seed_data = self.seed_map.get(slug, {})

            diff_val = ch.get("difficulty", "beginner")
            default_grade, default_diff = DIFF_TO_FRONTEND.get(diff_val, ("Grade 4", "Easy"))

            grade = seed_data.get("grade", default_grade)
            difficulty = seed_data.get("difficulty", default_diff)
            description = seed_data.get("description", "")
            tags = seed_data.get("tags", ["Lists"])
            estimated_time = seed_data.get("estimatedTime", "10 min")
            status = submission_status_map.get(cid, "New")

            result.append({
                "id": slug,
                "slug": slug,
                "title": ch["title"],
                "description": description,
                "grade": grade,
                "difficulty": difficulty,
                "tags": tags,
                "status": status,
                "estimatedTime": estimated_time,
                "sort_order": ch.get("sort_order", 0),
                "time_limit_ms": seed_data.get("time_limit_ms"),
                "input_constraints": seed_data.get("input_constraints"),
                "time_complexity": seed_data.get("time_complexity"),
            })

        return result

    def get_by_slug(self, slug_or_id: str) -> dict:
        raw_clean = slug_or_id.strip().lower()
        slug_clean = SLUG_ALIASES.get(raw_clean, raw_clean)
        resp = (
            self.db.table("challenges")
            .select("id, slug, title, statement, function_signature, starter_code, difficulty, sort_order")
            .eq("slug", slug_clean)
            .eq("is_published", True)
            .execute()
        )
        data = resp.data or []
        if not data and raw_clean != slug_clean:
            resp_alt = (
                self.db.table("challenges")
                .select("id, slug, title, statement, function_signature, starter_code, difficulty, sort_order")
                .eq("slug", raw_clean)
                .eq("is_published", True)
                .execute()
            )
            data = resp_alt.data or []
        if not data:
            try:
                resp2 = (
                    self.db.table("challenges")
                    .select("id, slug, title, statement, function_signature, starter_code, difficulty, sort_order")
                    .eq("id", slug_or_id)
                    .eq("is_published", True)
                    .execute()
                )
                data = resp2.data or []
            except Exception:
                data = []

        if not data:
            raise NotFoundError(f"Challenge '{slug_or_id}' not found.")

        ch = data[0]
        challenge_id = ch["id"]
        slug = ch["slug"]
        seed_data = self.seed_map.get(slug, {})

        # Fetch visible test cases only
        all_tests = self.get_test_cases(challenge_id)
        visible_tests = []
        hidden_count = 0

        for t in all_tests:
            if t["visibility"] == "visible":
                payload = t.get("input_payload") or {}
                call_str = payload.get("call") if isinstance(payload, dict) else None
                if not call_str:
                    call_str = t.get("call") or t.get("description", "")
                visible_tests.append({
                    "test": t["ordinal"],
                    "call": call_str,
                    "expected": str(t.get("expected_output", ""))
                })
            else:
                hidden_count += 1

        diff_val = ch.get("difficulty", "beginner")
        default_grade, default_diff = DIFF_TO_FRONTEND.get(diff_val, ("Grade 4", "Easy"))

        example = seed_data.get("example")
        if not example and visible_tests:
            example = {
                "call": visible_tests[0]["call"],
                "expected": visible_tests[0]["expected"],
                "explanation": f"Returns {visible_tests[0]['expected']} for {visible_tests[0]['call']}."
            }

        return {
            "id": slug,
            "uuid": challenge_id,
            "slug": slug,
            "title": ch["title"],
            "description": seed_data.get("description") or ch.get("statement", "")[:120] + "...",
            "statement": ch["statement"],
            "function_signature": ch.get("function_signature", ""),
            "starter_code": ch.get("starter_code", ""),
            "starterCode": ch.get("starter_code", ""),
            "grade": seed_data.get("grade", default_grade),
            "difficulty": seed_data.get("difficulty", default_diff),
            "tags": seed_data.get("tags", ["Algorithms"]),
            "status": "New",
            "estimatedTime": seed_data.get("estimatedTime", "15 min"),
            "sort_order": ch.get("sort_order", 0),
            "example": example,
            "visibleTests": visible_tests,
            "hiddenTestCount": hidden_count,
            "constraints": {
                "time_limit_ms": seed_data.get("time_limit_ms"),
                "memory_limit_mb": seed_data.get("memory_limit_mb"),
                "input_constraints": seed_data.get("input_constraints"),
                "time_complexity": seed_data.get("time_complexity"),
            },
        }

    def get_test_cases(self, challenge_id: str) -> list[dict]:
        """Returns ALL test cases (visible + hidden) — never send to frontend."""
        resp = (
            self.db.table("test_cases")
            .select("id, visibility, ordinal, input_payload, expected_output, timeout_ms, description")
            .eq("challenge_id", challenge_id)
            .order("ordinal")
            .execute()
        )
        return resp.data or []
