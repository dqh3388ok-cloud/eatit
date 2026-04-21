"""create initial data model

Revision ID: 20260419_1600
Revises:
Create Date: 2026-04-19 16:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260419_1600"
down_revision = None
branch_labels = None
depends_on = None


candidate_asset_status = postgresql.ENUM(
    "draft",
    "ready_for_parse",
    "parse_in_progress",
    "analysis_ready",
    "parse_failed",
    name="candidate_asset_status",
    create_type=False,
)
parse_result_status = postgresql.ENUM(
    "pending",
    "succeeded",
    "failed",
    name="parse_result_status",
    create_type=False,
)
interview_style = postgresql.ENUM(
    "friendly_guided",
    "standard_professional",
    "high_pressure_followup",
    name="interview_style",
    create_type=False,
)
interview_direction = postgresql.ENUM(
    "role_match",
    "project_deep_dive",
    "behavioral_comprehensive",
    name="interview_direction",
    create_type=False,
)
interview_session_status = postgresql.ENUM(
    "created",
    "session_started",
    "turn_recording",
    "turn_transcribing",
    "turn_evaluating",
    "turn_compressing",
    "next_question_ready",
    "paused",
    "ended",
    "exited_early",
    "report_generating",
    "report_ready",
    "failed",
    name="interview_session_status",
    create_type=False,
)
interview_report_status = postgresql.ENUM(
    "pending",
    "generating",
    "ready",
    "failed",
    name="interview_report_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    candidate_asset_status.create(bind, checkfirst=True)
    parse_result_status.create(bind, checkfirst=True)
    interview_style.create(bind, checkfirst=True)
    interview_direction.create(bind, checkfirst=True)
    interview_session_status.create(bind, checkfirst=True)
    interview_report_status.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "email",
            sa.String(length=320),
            nullable=False,
            comment="TODO: encrypt email at rest before production auth rollout.",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "candidate_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resume_file_ref", sa.String(length=512), nullable=True),
        sa.Column("resume_filename", sa.String(length=255), nullable=True),
        sa.Column("resume_content_type", sa.String(length=128), nullable=True),
        sa.Column("jd_file_ref", sa.String(length=512), nullable=True),
        sa.Column("jd_filename", sa.String(length=255), nullable=True),
        sa.Column("jd_content_type", sa.String(length=128), nullable=True),
        sa.Column("status", candidate_asset_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_candidate_assets_user_id", "candidate_assets", ["user_id"])

    op.create_table(
        "parse_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("candidate_asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", parse_result_status, nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="TODO: encrypt parse payload at rest before production launch.",
        ),
        sa.Column("match_summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["candidate_asset_id"], ["candidate_assets.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("candidate_asset_id"),
    )
    op.create_index("ix_parse_results_candidate_asset_id", "parse_results", ["candidate_asset_id"])

    op.create_table(
        "interview_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", interview_session_status, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("turn_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("config_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["candidate_asset_id"], ["candidate_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_interview_sessions_candidate_asset_id", "interview_sessions", ["candidate_asset_id"])
    op.create_index("ix_interview_sessions_status", "interview_sessions", ["status"])
    op.create_index("ix_interview_sessions_user_id", "interview_sessions", ["user_id"])

    op.create_table(
        "interview_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("interview_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("style", interview_style, nullable=False),
        sa.Column("direction", interview_direction, nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["interview_session_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("interview_session_id"),
    )
    op.create_index("ix_interview_configs_interview_session_id", "interview_configs", ["interview_session_id"])

    op.create_table(
        "direction_frameworks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("interview_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["interview_session_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("interview_session_id"),
    )
    op.create_index(
        "ix_direction_frameworks_interview_session_id",
        "direction_frameworks",
        ["interview_session_id"],
    )

    op.create_table(
        "interview_turns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("interview_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("stage_name", sa.String(length=64), nullable=True),
        sa.Column("question_tag", sa.String(length=128), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column(
            "answer_text",
            sa.Text(),
            nullable=True,
            comment="TODO: encrypt answer transcript at rest before production launch.",
        ),
        sa.Column("answer_hint", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["interview_session_id"], ["interview_sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_interview_turns_interview_session_id", "interview_turns", ["interview_session_id"])

    op.create_table(
        "turn_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("interview_turn_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strengths", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("weaknesses", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("score_optional", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["interview_turn_id"], ["interview_turns.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("interview_turn_id"),
    )
    op.create_index("ix_turn_assessments_interview_turn_id", "turn_assessments", ["interview_turn_id"])

    op.create_table(
        "compressed_turn_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("interview_turn_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("interview_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["interview_session_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["interview_turn_id"], ["interview_turns.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("interview_turn_id"),
    )
    op.create_index(
        "ix_compressed_turn_summaries_interview_session_id",
        "compressed_turn_summaries",
        ["interview_session_id"],
    )
    op.create_index(
        "ix_compressed_turn_summaries_interview_turn_id",
        "compressed_turn_summaries",
        ["interview_turn_id"],
    )

    op.create_table(
        "interview_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("interview_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", interview_report_status, nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="TODO: encrypt report payload at rest before production launch.",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["interview_session_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("interview_session_id"),
    )
    op.create_index("ix_interview_reports_interview_session_id", "interview_reports", ["interview_session_id"])


def downgrade() -> None:
    op.drop_index("ix_interview_reports_interview_session_id", table_name="interview_reports")
    op.drop_table("interview_reports")

    op.drop_index("ix_compressed_turn_summaries_interview_turn_id", table_name="compressed_turn_summaries")
    op.drop_index("ix_compressed_turn_summaries_interview_session_id", table_name="compressed_turn_summaries")
    op.drop_table("compressed_turn_summaries")

    op.drop_index("ix_turn_assessments_interview_turn_id", table_name="turn_assessments")
    op.drop_table("turn_assessments")

    op.drop_index("ix_interview_turns_interview_session_id", table_name="interview_turns")
    op.drop_table("interview_turns")

    op.drop_index("ix_direction_frameworks_interview_session_id", table_name="direction_frameworks")
    op.drop_table("direction_frameworks")

    op.drop_index("ix_interview_configs_interview_session_id", table_name="interview_configs")
    op.drop_table("interview_configs")

    op.drop_index("ix_interview_sessions_user_id", table_name="interview_sessions")
    op.drop_index("ix_interview_sessions_status", table_name="interview_sessions")
    op.drop_index("ix_interview_sessions_candidate_asset_id", table_name="interview_sessions")
    op.drop_table("interview_sessions")

    op.drop_index("ix_parse_results_candidate_asset_id", table_name="parse_results")
    op.drop_table("parse_results")

    op.drop_index("ix_candidate_assets_user_id", table_name="candidate_assets")
    op.drop_table("candidate_assets")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    interview_report_status.drop(bind, checkfirst=True)
    interview_session_status.drop(bind, checkfirst=True)
    interview_direction.drop(bind, checkfirst=True)
    interview_style.drop(bind, checkfirst=True)
    parse_result_status.drop(bind, checkfirst=True)
    candidate_asset_status.drop(bind, checkfirst=True)
