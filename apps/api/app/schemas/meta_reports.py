from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.models.enums import MetaReportStatus
from app.schemas.common import SchemaModel


class TriggerMetaReportRequest(SchemaModel):
    session_ids: list[str] | None = None


class TriggerMetaReportResponse(SchemaModel):
    id: UUID
    task_id: str
    status: MetaReportStatus
    covered_session_ids: list[str]
    created_at: datetime


class MetaReportDetailResponse(SchemaModel):
    id: UUID
    user_id: str
    status: MetaReportStatus
    covered_session_ids: list[str]
    payload: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class MetaReportListItem(SchemaModel):
    id: UUID
    status: MetaReportStatus
    covered_session_ids: list[str]
    session_count: int
    created_at: datetime


class MetaReportListRequest(SchemaModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class MetaReportListResponse(SchemaModel):
    items: list[MetaReportListItem]
    page: int
    page_size: int
    total: int
