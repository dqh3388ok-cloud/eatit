from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.session import InterviewSession


class InterviewReport(UUIDv7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "interview_reports"

    interview_session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )
    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="pending",
    )
    requested_at: Mapped[datetime | None] = mapped_column(nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="TODO: encrypt report payload at rest before production launch.",
    )

    interview_session: Mapped["InterviewSession"] = relationship(back_populates="report")
