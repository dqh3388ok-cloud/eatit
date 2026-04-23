from __future__ import annotations

from pydantic import BaseModel


class ReferenceAgentInput(BaseModel):
    question: str
    job_context: str | None = None
    candidate_answer: str | None = None


class ReferenceAgentOutput(BaseModel):
    answer_outline: list[str]
    ideal_answer: str
    key_evaluation_points: list[str]
    common_pitfalls: list[str]
