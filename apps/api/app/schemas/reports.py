from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.models.enums import InterviewReportStatus
from app.schemas.common import SchemaModel, TimestampedResponse
from app.schemas.turns import NormalizedAnswer, NormalizedQuestion, NormalizedUserAssessment


class RoundReview(SchemaModel):
    question: NormalizedQuestion
    answer: NormalizedAnswer
    assessment: NormalizedUserAssessment


class InterviewReportPayload(SchemaModel):
    overall_summary: str
    round_reviews: list[RoundReview]
    strengths: list[str]
    improvements: list[str]
    next_actions: list[str]


class TriggerReportResponse(SchemaModel):
    session_id: UUID
    status: InterviewReportStatus
    requested_at: datetime


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
