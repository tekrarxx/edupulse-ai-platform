"""curriculum domain: subject/topic/concept/skill/facet/prerequisite (Phase 3 / P2)

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-28

Not tenant-scoped by design (see docs/adr — curriculum ownership decision
recorded on the Phase 3 approval): this is shared reference content, not a
tenant-owned entity.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FACET_TYPES = ("recognition", "recall", "application", "transfer", "retention")


def upgrade() -> None:
    op.create_table(
        "subjects",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("content_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("slug", name="uq_subjects_slug"),
    )

    op.create_table(
        "topics",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("subject_id", sa.String(length=36), sa.ForeignKey("subjects.id"), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("content_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("subject_id", "slug", name="uq_topics_subject_slug"),
    )
    op.create_index("ix_topics_subject_id", "topics", ["subject_id"])

    op.create_table(
        "concepts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("topic_id", sa.String(length=36), sa.ForeignKey("topics.id"), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("content_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("topic_id", "slug", name="uq_concepts_topic_slug"),
    )
    op.create_index("ix_concepts_topic_id", "concepts", ["topic_id"])

    op.create_table(
        "skills",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("concept_id", sa.String(length=36), sa.ForeignKey("concepts.id"), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("grade_level", sa.Integer(), nullable=True),
        sa.Column("learning_outcome_code", sa.String(length=50), nullable=True),
        sa.Column("content_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("concept_id", "slug", name="uq_skills_concept_slug"),
    )
    op.create_index("ix_skills_concept_id", "skills", ["concept_id"])

    op.create_table(
        "skill_facets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("skill_id", sa.String(length=36), sa.ForeignKey("skills.id"), nullable=False),
        sa.Column("facet_type", sa.Enum(*_FACET_TYPES, name="skill_facet_type", native_enum=False), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("skill_id", "facet_type", name="uq_skill_facets_skill_type"),
    )
    op.create_index("ix_skill_facets_skill_id", "skill_facets", ["skill_id"])

    op.create_table(
        "prerequisites",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("skill_id", sa.String(length=36), sa.ForeignKey("skills.id"), nullable=False),
        sa.Column("prerequisite_skill_id", sa.String(length=36), sa.ForeignKey("skills.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("skill_id", "prerequisite_skill_id", name="uq_prerequisites_edge"),
        sa.CheckConstraint("skill_id <> prerequisite_skill_id", name="ck_prerequisites_no_self_loop"),
    )
    op.create_index("ix_prerequisites_skill_id", "prerequisites", ["skill_id"])
    op.create_index("ix_prerequisites_prerequisite_skill_id", "prerequisites", ["prerequisite_skill_id"])


def downgrade() -> None:
    op.drop_table("prerequisites")
    op.drop_table("skill_facets")
    op.drop_table("skills")
    op.drop_table("concepts")
    op.drop_table("topics")
    op.drop_table("subjects")
