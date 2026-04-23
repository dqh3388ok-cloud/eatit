"""create app_settings table

Revision ID: 20260423_0001
Revises: 20260421_0000
Create Date: 2026-04-23 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260423_0001"
down_revision = "20260421_0000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column(
            "key",
            sa.String(length=64),
            primary_key=True,
            nullable=False,
            comment="Whitelisted setting key. See app.domain.settings.service.ALLOWED_KEYS.",
        ),
        sa.Column(
            "value",
            sa.JSON(),
            nullable=False,
            comment="JSON-serializable value. Must never store LLM secrets (keys/tokens).",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
