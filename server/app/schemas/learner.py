from pydantic import BaseModel


class RecurringMistake(BaseModel):
    category: str
    tag: str = ""
    challenge_count: int
    challenges: list[str] = []


class ConceptMastery(BaseModel):
    concept: str
    estimate: float
    score: float = 0.0
    grade: str = "Grade 4"
    difficulty: str = "Easy"


class NextChallenge(BaseModel):
    challenge_id: str
    title: str = ""
    grade: str = "Grade 4"
    difficulty: str = "Easy"
    reason: str


class LearnerResponse(BaseModel):
    learner_id: str
    recurring_mistakes: list[RecurringMistake] = []
    mastery: list[ConceptMastery] = []
    next_challenge: NextChallenge | None = None
