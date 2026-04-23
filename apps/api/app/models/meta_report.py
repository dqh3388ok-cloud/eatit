from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin


class MetaReport(UUIDv7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "meta_reports"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    covered_session_ids: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="Snapshot of session_ids covered at trigger time (ordered).",
    )
    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="generating",
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="MetaReportOutput when status=ready; {detail: ...} when status=failed.",
    )
