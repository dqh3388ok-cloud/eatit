from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReportTurnAssessmentSnippet(BaseModel):
    summary: str


class ReportTurnRecord(BaseModel):
    question: str
    answer: str
    assessment: ReportTurnAssessmentSnippet | None = None


class ReportAgentInput(BaseModel):
    parse_payload_json: str
    framework_json: str
    turns: list[ReportTurnRecord]
    long_term_summary: str | None = None


Verdict = Literal["strong", "solid", "mixed", "weak"]


class Reason(BaseModel):
    aspect: str
    verdict: Verdict
    evidence_turn_index: int = Field(ge=0)
    quote: str


class ReportAgentOutput(BaseModel):
    pass_probability: int = Field(ge=0, le=100)
    summary: str
    reasons: list[Reason]
    next_actions: list[str]
