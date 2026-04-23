from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Verdict = Literal["weak", "mixed", "solid", "strong"]


class MetaReportSessionInput(BaseModel):
    session_id: str
    session_created_at: datetime
    config_snapshot: dict
    report_payload: dict


class MetaReportAgentInput(BaseModel):
    sessions: list[MetaReportSessionInput]


class RecurringWeakness(BaseModel):
    aspect: str
    occurrence_count: int = Field(ge=2)
    session_ids: list[str]
    evidence_quotes: list[str]


class ImprovementSignal(BaseModel):
    aspect: str
    from_verdict: Verdict
    to_verdict: Verdict
    earlier_session_id: str
    later_session_id: str


class PassProbabilityPoint(BaseModel):
    session_id: str
    session_created_at: datetime
    pass_probability: int = Field(ge=0, le=100)


class NextFocusArea(BaseModel):
    aspect: str
    reason: str
    suggested_prep: str


class MetaReportOutput(BaseModel):
    overall_trend_summary: str
    recurring_weaknesses: list[RecurringWeakness]
    improvement_signals: list[ImprovementSignal]
    pass_probability_series: list[PassProbabilityPoint]
    next_focus_areas: list[NextFocusArea]
