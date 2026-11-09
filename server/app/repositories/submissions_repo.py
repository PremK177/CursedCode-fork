from typing import Any
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)


class SubmissionsRepo:
    def __init__(self, db: Any):
        self.db = db

    def create(self, learner_id: str, challenge_id: str, source_code: str) -> dict:
        resp = (
            self.db.table("submissions")
            .insert(
                {
                    "learner_id": learner_id,
                    "challenge_id": challenge_id,
                    "source_code": source_code,
                    "status": "queued",
                }
            )
            .execute()
        )
        return resp.data[0]

    def update(self, submission_id: str, data: dict) -> dict:
        resp = (
            self.db.table("submissions")
            .update(data)
            .eq("id", submission_id)
            .execute()
        )
        return resp.data[0]

    def get_by_public_id(self, public_id: str) -> dict:
        resp = (
            self.db.table("submissions")
            .select("*")
            .eq("public_id", public_id)
            .single()
            .execute()
        )
        if not resp.data:
            raise NotFoundError(f"Submission '{public_id}' not found.")
        return resp.data

    def insert_test_results(self, results: list[dict]) -> None:
        if results:
            self.db.table("test_results").insert(results).execute()

    def insert_mistakes(self, mistakes: list[dict]) -> None:
        if mistakes:
            self.db.table("submission_mistakes").insert(mistakes).execute()

    def increment_hints(self, submission_id: str) -> int:
        """Atomically increments hints_requested and returns the new value."""
        resp = (
            self.db.rpc(
                "increment_hints_requested",
                {"sub_id": submission_id},
            ).execute()
        )
        # Fallback: fetch current value if RPC not available
        row = (
            self.db.table("submissions")
            .select("hints_requested")
            .eq("id", submission_id)
            .single()
            .execute()
        )
        return row.data["hints_requested"]
