"""knowledge state (Phase 5 / P4)

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-28

Per ADR-012: one row per (tenant, student, skill, facet), upserted on each
recompute. This table is a cache of the Beta-Binomial posterior over the
Evidence log, never a second source of truth — nothing here is written
except through app/services/knowledge_state_service.py, which always
recomputes from Evidence before upserting.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FACET_TYPES = ("recognition", "recall", "application", "transfer", "retention")
_CONFIDENCE_LABELS = ("insufficient_evidence", "low_confidence", "high_confidence")


def upgrade() -> None:
    op.create_table(
        "knowledge_states",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("student_user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("skill_id", sa.String(length=36), sa.ForeignKey("skills.id"), nullable=False),
        sa.Column(
            "facet_type", sa.Enum(*_FACET_TYPES, name="knowledge_state_facet_type", native_enum=False), nullable=False
        ),
        sa.Column("alpha", sa.Float(), nullable=False),
        sa.Column("beta", sa.Float(), nullable=False),
        sa.Column("mastery_probability", sa.Float(), nullable=False),
        sa.Column(
            "confidence_label",
            sa.Enum(*_CONFIDENCE_LABELS, name="knowledge_state_confidence_label", native_enum=False),
            nullable=False,
        ),
        sa.Column("effective_n", sa.Float(), nullable=False),
        sa.Column("variance", sa.Float(), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "student_user_id", "skill_id", "facet_type", name="uq_knowledge_states_student_skill_facet"
        ),
    )
    op.create_index("ix_knowledge_states_tenant_id", "knowledge_states", ["tenant_id"])
    op.create_index("ix_knowledge_states_student_user_id", "knowledge_states", ["student_user_id"])
    op.create_index("ix_knowledge_states_skill_id", "knowledge_states", ["skill_id"])


def downgrade() -> None:
    op.drop_table("knowledge_states")
