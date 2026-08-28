"""ai usage accounting (Phase 8 / P7)

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-29

Additive: one new table. No existing schema changes (ADR-015).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_AI_USAGE_CAPABILITIES = ("skill_explanation",)


def upgrade() -> None:
    op.create_table(
        "ai_usage_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column(
            "capability",
            sa.Enum(*_AI_USAGE_CAPABILITIES, name="ai_usage_capability", native_enum=False),
            nullable=False,
        ),
        sa.Column("prompt_name", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=20), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_reason", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_usage_records_tenant_id", "ai_usage_records", ["tenant_id"])
    op.create_index("ix_ai_usage_records_actor_user_id", "ai_usage_records", ["actor_user_id"])
    op.create_index("ix_ai_usage_records_capability", "ai_usage_records", ["capability"])
    op.create_index("ix_ai_usage_records_created_at", "ai_usage_records", ["created_at"])


def downgrade() -> None:
    op.drop_table("ai_usage_records")
