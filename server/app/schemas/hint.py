from pydantic import BaseModel, Field


class CodePatch(BaseModel):
    target_line: int
    original_snippet: str
    replacement_snippet: str
    explanation: str
    patched_code: str | None = None


class HintRequest(BaseModel):
    submission_id: str = Field(..., min_length=1, max_length=128)
    level: int | None = Field(default=None, ge=1, le=4)
    include_patch: bool = Field(default=False)


class HintResponse(BaseModel):
    submission_id: str
    hint_index: int
    hint: str
    level: int = 1
    remaining: int = 3
    code_patch: CodePatch | None = None
