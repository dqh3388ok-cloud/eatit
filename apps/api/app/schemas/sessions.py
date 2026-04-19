from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.enums import InterviewDirection, InterviewSessionStatus, InterviewStyle
from app.schemas.common import PaginatedResponse, SchemaModel, TimestampedResponse
from app.schemas.frameworks import DirectionFramework


class InterviewConfigRequest(SchemaModel):
    style: InterviewStyle
    direction: InterviewDirection
    duration_minutes: int = Field(ge=1)


class InterviewConfigResponse(TimestampedResponse):
    interview_session_id: UUID
    style: InterviewStyle
    direction: InterviewDirection
    duration_minutes: int


class CreateSessionRequest(SchemaModel):
    asset_bundle_id: UUID
    config: InterviewConfigRequest


class CreateSessionResponse(SchemaModel):
    session_id: UUID
    status: InterviewSessionStatus
    direction_framework: DirectionFramework


class SessionSummary(TimestampedResponse):
    user_id: UUID
    candidate_asset_id: UUID
    status: InterviewSessionStatus
    started_at: datetime | None = None
    ended_at: datetime | None = None
    turn_count: int = Field(ge=0)
    config_snapshot: dict


class SessionDetailResponse(SessionSummary):
    config: InterviewConfigResponse | None = None
    direction_framework: DirectionFramework | None = None


class SessionListResponse(PaginatedResponse[SessionSummary]):
    pass


class EndSessionResponse(SchemaModel):
    session_id: UUID
    status: InterviewSessionStatus
    ended_at: datetime
