from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from typing import Any

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin
from app.models.enums import CandidateAssetStatus, ParseResultStatus

if TYPE_CHECKING:
    from app.models.session import InterviewSession
    from app.models.user import User


class CandidateAsset(UUIDv7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "candidate_assets"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resume_file_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    resume_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resume_content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    jd_file_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    jd_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    jd_content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[CandidateAssetStatus] = mapped_column(
        Enum(CandidateAssetStatus, name="candidate_asset_status"),
        nullable=False,
        default=CandidateAssetStatus.DRAFT,
    )

    user: Mapped["User"] = relationship(back_populates="candidate_assets")
    parse_result: Mapped["ParseResult | None"] = relationship(back_populates="candidate_asset")
    interview_sessions: Mapped[list["InterviewSession"]] = relationship(back_populates="candidate_asset")


class ParseResult(UUIDv7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "parse_results"

    candidate_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )
    status: Mapped[ParseResultStatus] = mapped_column(
        Enum(ParseResultStatus, name="parse_result_status"),
        nullable=False,
        default=ParseResultStatus.PENDING,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="TODO: encrypt parse payload at rest before production launch.",
    )
    match_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    candidate_asset: Mapped["CandidateAsset"] = relationship(back_populates="parse_result")
