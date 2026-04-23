from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.models.enums import InterviewReportStatus
from app.schemas.common import SchemaModel, TimestampedResponse
from app.schemas.turns import NormalizedAnswer, NormalizedQuestion, NormalizedUserAssessment


class RoundReview(SchemaModel):
    question: NormalizedQuestion
    answer: NormalizedAnswer
    assessment: NormalizedUserAssessment


ReportVerdict = Literal["strong", "solid", "mixed", "weak"]


class ReportReason(SchemaModel):
    aspect: str
    verdict: ReportVerdict
    evidence_turn_index: int = Field(ge=0)
    quote: str


class InterviewReportPayload(SchemaModel):
    overall_summary: str
    round_reviews: list[RoundReview] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    pass_probability: int = Field(default=0, ge=0, le=100)
    reasons: list[ReportReason] = Field(default_factory=list)


class TriggerReportResponse(SchemaModel):
    session_id: UUID
    status: InterviewReportStatus
    requested_at: datetime


class TriggerReportRequest(SchemaModel):
    force_regenerate: bool = False


class InterviewReportResponse(TimestampedResponse):
    interview_session_id: UUID
    status: InterviewReportStatus
    requested_at: datetime | None = None
    generated_at: datetime | None = None
    payload: InterviewReportPayload


class ReportStatusResponse(SchemaModel):
    session_id: UUID
    status: InterviewReportStatus
    has_payload: bool
