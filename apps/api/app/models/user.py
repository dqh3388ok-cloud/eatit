from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDv7PrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.asset import CandidateAsset
    from app.models.session import InterviewSession


class User(UUIDv7PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        index=True,
        nullable=False,
        comment="TODO: encrypt email at rest before production auth rollout.",
    )

    candidate_assets: Mapped[list["CandidateAsset"]] = relationship(back_populates="user")
    interview_sessions: Mapped[list["InterviewSession"]] = relationship(back_populates="user")
