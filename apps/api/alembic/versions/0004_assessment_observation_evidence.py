"""assessment, observation, evidence (Phase 4 / P3)

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-28

Observations are append-only at the database level (§40): a trigger
rejects UPDATE and DELETE on the table outright, so the guarantee holds
even against a raw SQL statement, not just the service layer's own
discipline. This is Postgres-specific (PL/pgSQL) — skipped on SQLite,
which the app only ever uses as a lightweight local-dev fallback, never
for anything this migration's data needs to be durable in.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FACET_TYPES = ("recognition", "recall", "application", "transfer", "retention")
_ASSESSMENT_TYPES = ("diagnostic", "formative", "retrieval_practice", "application", "transfer", "delayed_retention")
_EVALUATION_METHODS = ("automatic", "manual", "ai")
_EVENT_TYPES = (
    "answer_submitted",
    "answer_correct",
    "answer_incorrect",
    "hint_requested",
    "time_spent",
    "task_completed",
    "transfer_failed",
    "retention_assessment_completed",
)
_POLARITIES = ("positive", "negative")
_DIRECTNESS = ("direct", "indirect")


def upgrade() -> None:
    op.create_table(
        "questions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("skill_id", sa.String(length=36), sa.ForeignKey("skills.id"), nullable=False),
        sa.Column("facet_type", sa.Enum(*_FACET_TYPES, name="question_facet_type", native_enum=False), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("correct_answer", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("content_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_questions_skill_id", "questions", ["skill_id"])

    op.create_table(
        "attempts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("student_user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("question_id", sa.String(length=36), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("assessment_type", sa.Enum(*_ASSESSMENT_TYPES, name="assessment_type", native_enum=False), nullable=False),
        sa.Column("question_content_version", sa.Integer(), nullable=False),
        sa.Column("learner_response", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("evaluation_method", sa.Enum(*_EVALUATION_METHODS, name="evaluation_method", native_enum=False), nullable=True),
        sa.Column("evaluation_confidence", sa.Float(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_attempts_tenant_idempotency_key"),
    )
    op.create_index("ix_attempts_tenant_id", "attempts", ["tenant_id"])
    op.create_index("ix_attempts_student_user_id", "attempts", ["student_user_id"])
    op.create_index("ix_attempts_question_id", "attempts", ["question_id"])

    op.create_table(
        "observations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("subject_type", sa.String(length=50), nullable=False),
        sa.Column("subject_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.Enum(*_EVENT_TYPES, name="observation_event_type", native_enum=False), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("correlation_id", sa.String(length=100), nullable=True),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_observations_tenant_idempotency_key"),
    )
    op.create_index("ix_observations_tenant_id", "observations", ["tenant_id"])
    op.create_index("ix_observations_subject", "observations", ["subject_type", "subject_id"])

    op.create_table(
        "evidence",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("student_user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("observation_id", sa.String(length=36), sa.ForeignKey("observations.id"), nullable=False),
        sa.Column("skill_id", sa.String(length=36), sa.ForeignKey("skills.id"), nullable=False),
        sa.Column("facet_type", sa.Enum(*_FACET_TYPES, name="evidence_facet_type", native_enum=False), nullable=False),
        sa.Column("polarity", sa.Enum(*_POLARITIES, name="evidence_polarity", native_enum=False), nullable=False),
        sa.Column("directness", sa.Enum(*_DIRECTNESS, name="evidence_directness", native_enum=False), nullable=False, server_default="direct"),
        sa.Column("reliability", sa.Float(), nullable=False),
        sa.Column("task_validity", sa.Float(), nullable=False),
        sa.Column("transfer_relevance", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("evaluation_confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evidence_tenant_id", "evidence", ["tenant_id"])
    op.create_index("ix_evidence_student_user_id", "evidence", ["student_user_id"])
    op.create_index("ix_evidence_skill_id", "evidence", ["skill_id"])
    op.create_index("ix_evidence_observation_id", "evidence", ["observation_id"])

    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
            CREATE FUNCTION prevent_observation_mutation() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'observations are append-only: % is not permitted', TG_OP;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER observations_append_only
            BEFORE UPDATE OR DELETE ON observations
            FOR EACH ROW EXECUTE FUNCTION prevent_observation_mutation();
            """
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS observations_append_only ON observations;")
        op.execute("DROP FUNCTION IF EXISTS prevent_observation_mutation();")
    op.drop_table("evidence")
    op.drop_table("observations")
    op.drop_table("attempts")
    op.drop_table("questions")
