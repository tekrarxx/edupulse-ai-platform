"""Curriculum domain (§19, §20): Subject -> Topic -> Concept -> Skill, with a
Skill's facets (§28) and prerequisite graph (§19) as first-class rows.

Deliberately NOT tenant-scoped. Curriculum content (MEB / Türkiye Yüzyılı
Maarif Modeli material) is shared reference data every tenant reads from the
same source, not a tenant-owned entity in the §50 sense — duplicating it per
tenant would mean re-authoring the same Physics content once per school and
letting copies drift out of sync. Write access is restricted to SUPER_ADMIN
at the route layer (`app/api/routes/curriculum.py`); every authenticated
user can read.

No table, column, or enum here may assume the subject is Physics (§2) — a
second subject must be addable as data alone, which the Phase 3 test suite
demonstrates directly (`tests/api/test_curriculum.py`).
"""
import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._types import uuid_fk, uuid_pk, utcnow


class SkillFacetType(str, enum.Enum):
    """§28. A learner's success on one facet must never be read as mastery of
    another — recognizing a formula is not being able to transfer it."""

    RECOGNITION = "recognition"
    RECALL = "recall"
    APPLICATION = "application"
    TRANSFER = "transfer"
    RETENTION = "retention"


def _enum_column(enum_cls, name: str):
    return Enum(enum_cls, name=name, native_enum=False, values_callable=lambda ec: [e.value for e in ec])


class Subject(Base):
    """§2: a row of data, e.g. "Fizik" — never a hardcoded assumption."""

    __tablename__ = "subjects"

    id: Mapped[str] = uuid_pk()
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    content_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Topic(Base):
    __tablename__ = "topics"
    __table_args__ = (UniqueConstraint("subject_id", "slug", name="uq_topics_subject_slug"),)

    id: Mapped[str] = uuid_pk()
    subject_id: Mapped[str] = uuid_fk("subjects.id")
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    content_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Concept(Base):
    __tablename__ = "concepts"
    __table_args__ = (UniqueConstraint("topic_id", "slug", name="uq_concepts_topic_slug"),)

    id: Mapped[str] = uuid_pk()
    topic_id: Mapped[str] = uuid_fk("topics.id")
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    content_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Skill(Base):
    """The unit knowledge state (Phase 4) and PDE (Phase 5) will attach to.
    `grade_level` and `learning_outcome_code` exist so MEB/TYM mapping has
    somewhere to live without inventing a second parallel table (§20)."""

    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("concept_id", "slug", name="uq_skills_concept_slug"),)

    id: Mapped[str] = uuid_pk()
    concept_id: Mapped[str] = uuid_fk("concepts.id")
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    grade_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    learning_outcome_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    content_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    facets: Mapped[list["SkillFacet"]] = relationship(back_populates="skill")
    prerequisites: Mapped[list["Prerequisite"]] = relationship(
        foreign_keys="Prerequisite.skill_id", viewonly=True
    )


class SkillFacet(Base):
    """§28: recognition/recall/application/transfer/retention as distinct,
    independently-evidenced dimensions of one Skill — never collapsed into a
    single mastery column."""

    __tablename__ = "skill_facets"
    __table_args__ = (UniqueConstraint("skill_id", "facet_type", name="uq_skill_facets_skill_type"),)

    id: Mapped[str] = uuid_pk()
    skill_id: Mapped[str] = uuid_fk("skills.id")
    facet_type: Mapped[SkillFacetType] = mapped_column(_enum_column(SkillFacetType, "skill_facet_type"), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    skill: Mapped["Skill"] = relationship(back_populates="facets")


class Prerequisite(Base):
    """A directed edge: `prerequisite_skill_id` must be learned before
    `skill_id`. Cycle detection happens in `curriculum_service.py` at write
    time (§19) — a general-purpose graph-acyclicity check does not express
    as a database CHECK constraint, only the trivial self-loop case does."""

    __tablename__ = "prerequisites"
    __table_args__ = (
        UniqueConstraint("skill_id", "prerequisite_skill_id", name="uq_prerequisites_edge"),
        CheckConstraint("skill_id <> prerequisite_skill_id", name="ck_prerequisites_no_self_loop"),
    )

    id: Mapped[str] = uuid_pk()
    skill_id: Mapped[str] = uuid_fk("skills.id")
    prerequisite_skill_id: Mapped[str] = uuid_fk("skills.id")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
