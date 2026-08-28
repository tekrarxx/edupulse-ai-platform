"""prometheus decision engine (Phase 6 / P5)

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-28

Decisions are append-only at the database level (§40, §100), same pattern
as observations (0004): a trigger rejects UPDATE and DELETE outright.
Also adds Tenant.pde_shadow_mode_default (ADR-013 Shadow Mode, §96).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SELECTED_ACTIONS = (
    "insufficient_evidence_action",
    "retrieval_question",
    "new_concept_explanation",
    "easier_task",
    "harder_task",
    "transfer_task",
    "review_task",
    "delayed_retention_assessment",
    "hint",
    "worked_example",
    "teacher_intervention",
    "defer_decision",
)
_AUTHORIZATION_RESULTS = ("allowed", "rejected", "escalated")


def upgrade() -> None:
    op.add_column(
        "tenants", sa.Column("pde_shadow_mode_default", sa.Boolean(), nullable=False, server_default=sa.false())
    )

    op.create_table(
        "decisions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("student_user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("skill_id", sa.String(length=36), sa.ForeignKey("skills.id"), nullable=False),
        sa.Column(
            "selected_action",
            sa.Enum(*_SELECTED_ACTIONS, name="decision_selected_action", native_enum=False),
            nullable=False,
        ),
        sa.Column("candidate_actions", sa.JSON(), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("policy_version", sa.String(length=50), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("knowledge_state_snapshot", sa.JSON(), nullable=False),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column(
            "authorization_result",
            sa.Enum(*_AUTHORIZATION_RESULTS, name="decision_authorization_result", native_enum=False),
            nullable=False,
        ),
        sa.Column("authorization_reason", sa.Text(), nullable=False),
        sa.Column("is_shadow", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_decisions_tenant_id", "decisions", ["tenant_id"])
    op.create_index("ix_decisions_student_user_id", "decisions", ["student_user_id"])
    op.create_index("ix_decisions_skill_id", "decisions", ["skill_id"])

    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
            CREATE FUNCTION prevent_decision_mutation() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'decisions are append-only: % is not permitted', TG_OP;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER decisions_append_only
            BEFORE UPDATE OR DELETE ON decisions
            FOR EACH ROW EXECUTE FUNCTION prevent_decision_mutation();
            """
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS decisions_append_only ON decisions;")
        op.execute("DROP FUNCTION IF EXISTS prevent_decision_mutation();")
    op.drop_table("decisions")
    op.drop_column("tenants", "pde_shadow_mode_default")
