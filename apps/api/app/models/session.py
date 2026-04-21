from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin
from app.models.enums import InterviewDirection, InterviewSessionStatus, InterviewStyle

if TYPE_CHECKING:
    from app.models.asset import CandidateAsset
    from app.models.report import InterviewReport
    from app.models.user import User


class InterviewSession(UUIDv7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "interview_sessions"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_asset_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("candidate_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=InterviewSessionStatus.CREATED,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)
    turn_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    config_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    user: Mapped["User"] = relationship(back_populates="interview_sessions")
    candidate_asset: Mapped["CandidateAsset"] = relationship(back_populates="interview_sessions")
    config: Mapped["InterviewConfig | None"] = relationship(back_populates="interview_session")
    direction_framework: Mapped["DirectionFramework | None"] = relationship(back_populates="interview_session")
    turns: Mapped[list["InterviewTurn"]] = relationship(back_populates="interview_session")
    report: Mapped["InterviewReport | None"] = relationship(back_populates="interview_session")


class InterviewConfig(UUIDv7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "interview_configs"

    interview_session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )
    style: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    direction: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)

    interview_session: Mapped["InterviewSession"] = relationship(back_populates="config")


class DirectionFramework(UUIDv7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "direction_frameworks"

    interview_session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    interview_session: Mapped["InterviewSession"] = relationship(back_populates="direction_framework")


class InterviewTurn(UUIDv7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "interview_turns"

    interview_session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    stage_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    question_tag: Mapped[str] = mapped_column(String(128), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="TODO: encrypt answer transcript at rest before production launch.",
    )
    answer_hint: Mapped[str | None] = mapped_column(Text, nullable=True)

    interview_session: Mapped["InterviewSession"] = relationship(back_populates="turns")
    assessment: Mapped["TurnAssessment | None"] = relationship(back_populates="interview_turn")
    compressed_summary: Mapped["CompressedTurnSummary | None"] = relationship(back_populates="interview_turn")


class TurnAssessment(UUIDv7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "turn_assessments"

    interview_turn_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("interview_turns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )
    strengths: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    weaknesses: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    evidence: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    score_optional: Mapped[float | None] = mapped_column(nullable=True)

    interview_turn: Mapped["InterviewTurn"] = relationship(back_populates="assessment")


class CompressedTurnSummary(UUIDv7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "compressed_turn_summaries"

    interview_turn_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("interview_turns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )
    interview_session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    interview_turn: Mapped["InterviewTurn"] = relationship(back_populates="compressed_summary")
