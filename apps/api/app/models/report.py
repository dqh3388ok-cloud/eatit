from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin
from app.models.enums import InterviewReportStatus

if TYPE_CHECKING:
    from app.models.session import InterviewSession


class InterviewReport(UUIDv7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "interview_reports"

    interview_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )
    status: Mapped[InterviewReportStatus] = mapped_column(
        Enum(InterviewReportStatus, name="interview_report_status"),
        nullable=False,
        default=InterviewReportStatus.PENDING,
    )
    requested_at: Mapped[datetime | None] = mapped_column(nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="TODO: encrypt report payload at rest before production launch.",
    )

    interview_session: Mapped["InterviewSession"] = relationship(back_populates="report")
