"""transfer variants, delayed retention, falsification (Phase 7 / P6)

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-28

All additive per ADR-014: two nullable columns on questions, one nullable
column on evidence, two new tables. No existing data is affected.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FAILURE_MODES = (
    "lack_of_knowledge",
    "retrieval_failure",
    "careless_error",
    "misconception",
    "transfer_failure",
    "retention_failure",
)
_CHECKPOINT_STATUSES = ("pending", "completed")
_HYPOTHESIS_TYPES = ("retention_prediction",)
_HYPOTHESIS_VERDICTS = ("pending", "supported", "not_supported", "inconclusive")
_CONFIDENCE_LABELS = ("insufficient_evidence", "low_confidence", "high_confidence")


def upgrade() -> None:
    op.add_column("questions", sa.Column("source_question_id", sa.String(length=36), sa.ForeignKey("questions.id"), nullable=True))
    op.add_column("questions", sa.Column("surface_variation", sa.Text(), nullable=True))

    op.add_column(
        "evidence",
        sa.Column(
            "failure_mode", sa.Enum(*_FAILURE_MODES, name="evidence_failure_mode", native_enum=False), nullable=True
        ),
    )

    op.create_table(
        "retention_checkpoints",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("student_user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("skill_id", sa.String(length=36), sa.ForeignKey("skills.id"), nullable=False),
        sa.Column("checkpoint_days", sa.Integer(), nullable=False),
        sa.Column("origin_evidence_id", sa.String(length=36), sa.ForeignKey("evidence.id"), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum(*_CHECKPOINT_STATUSES, name="retention_checkpoint_status", native_enum=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("delayed_attempt_id", sa.String(length=36), sa.ForeignKey("attempts.id"), nullable=True),
        sa.Column("retention_estimate", sa.Float(), nullable=True),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "student_user_id", "skill_id", "checkpoint_days", name="uq_retention_checkpoint_student_skill_days"
        ),
    )
    op.create_index("ix_retention_checkpoints_tenant_id", "retention_checkpoints", ["tenant_id"])
    op.create_index("ix_retention_checkpoints_student_user_id", "retention_checkpoints", ["student_user_id"])
    op.create_index("ix_retention_checkpoints_skill_id", "retention_checkpoints", ["skill_id"])
    op.create_index("ix_retention_checkpoints_scheduled_for", "retention_checkpoints", ["scheduled_for"])

    op.create_table(
        "hypotheses",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("student_user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("skill_id", sa.String(length=36), sa.ForeignKey("skills.id"), nullable=False),
        sa.Column("hypothesis_type", sa.Enum(*_HYPOTHESIS_TYPES, name="hypothesis_type", native_enum=False), nullable=False),
        sa.Column("retention_checkpoint_id", sa.String(length=36), sa.ForeignKey("retention_checkpoints.id"), nullable=False),
        sa.Column("predicted_mastery_probability", sa.Float(), nullable=False),
        sa.Column(
            "predicted_confidence_label",
            sa.Enum(*_CONFIDENCE_LABELS, name="hypothesis_predicted_confidence_label", native_enum=False),
            nullable=False,
        ),
        sa.Column("predicted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_is_correct", sa.Boolean(), nullable=True),
        sa.Column(
            "verdict",
            sa.Enum(*_HYPOTHESIS_VERDICTS, name="hypothesis_verdict", native_enum=False),
            nullable=False,
            server_default="pending",
        ),
    )
    op.create_index("ix_hypotheses_tenant_id", "hypotheses", ["tenant_id"])
    op.create_index("ix_hypotheses_retention_checkpoint_id", "hypotheses", ["retention_checkpoint_id"])


def downgrade() -> None:
    op.drop_table("hypotheses")
    op.drop_table("retention_checkpoints")
    op.drop_column("evidence", "failure_mode")
    op.drop_column("questions", "surface_variation")
    op.drop_column("questions", "source_question_id")
