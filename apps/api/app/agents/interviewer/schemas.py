from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class TurnAssessmentSnippet(BaseModel):
    summary: str


class TurnRecord(BaseModel):
    question: str
    answer: str
    assessment: TurnAssessmentSnippet | None = None


class InterviewerAgentInput(BaseModel):
    framework_json: str
    recent_turns: list[TurnRecord]
    long_term_summary: str | None = None
    remaining_minutes: int | None = None


class InterviewerAgentOutput(BaseModel):
    question: str
    intent: str
    expected_depth: Literal["surface", "tactical", "strategic"]
    followup_hint: str | None = None
    should_end: bool = False
