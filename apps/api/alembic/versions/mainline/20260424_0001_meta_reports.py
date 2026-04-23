"""create meta_reports table

Revision ID: 20260424_0001
Revises: 20260423_0001
Create Date: 2026-04-24 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260424_0001"
down_revision = "20260423_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meta_reports",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column(
            "covered_session_ids",
            sa.JSON(),
            nullable=False,
            comment="Snapshot of session_ids covered at trigger time (ordered).",
        ),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column(
            "payload",
            sa.JSON(),
            nullable=True,
            comment="MetaReportOutput when status=ready; {detail: ...} when status=failed.",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_meta_reports_user_id", "meta_reports", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_meta_reports_user_id", table_name="meta_reports")
    op.drop_table("meta_reports")
