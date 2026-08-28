"""Assessment domain (§21). Question is shared platform content — same
ownership precedent as curriculum (see app/models/curriculum.py) — while
Attempt is tenant- and learner-scoped: it is a specific student's response,
which is exactly the kind of data §50 means by "tenant-owned."

`assessment_type` (diagnostic/formative/retrieval_practice/application/
transfer/delayed_retention, §21) is a different axis from SkillFacetType
(recognition/recall/application/transfer/retention, §28) even though the
vocabularies overlap — one is "why was this posed," the other is "which
dimension of the skill does it target." Do not conflate them.
"""
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._types import uuid_fk, uuid_pk, utcnow
from app.models.curriculum import SkillFacetType


def _enum_column(enum_cls, name: str):
    return Enum(enum_cls, name=name, native_enum=False, values_callable=lambda ec: [e.value for e in ec])


class AssessmentType(str, enum.Enum):
    """§21."""

    DIAGNOSTIC = "diagnostic"
    FORMATIVE = "formative"
    RETRIEVAL_PRACTICE = "retrieval_practice"
    APPLICATION = "application"
    TRANSFER = "transfer"
    DELAYED_RETENTION = "delayed_retention"


class EvaluationMethod(str, enum.Enum):
    """AI is listed for future AI-assisted grading (§46's structured-output
    path) — nothing in this phase's service layer sets it; only AUTOMATIC
    (exact-match against Question.correct_answer) and MANUAL (a teacher
    grading an open-ended response) are actually produced."""

    AUTOMATIC = "automatic"
    MANUAL = "manual"
    AI = "ai"


class Question(Base):
    """Reusable content, not tenant-owned — see module docstring."""

    __tablename__ = "questions"

    id: Mapped[str] = uuid_pk()
    skill_id: Mapped[str] = uuid_fk("skills.id")
    facet_type: Mapped[SkillFacetType] = mapped_column(_enum_column(SkillFacetType, "question_facet_type"), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    # Null for open-ended items that require manual/AI grading; set for
    # items automatic exact-match grading can evaluate deterministically.
    correct_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    # §29/ADR-014: an explicit transfer-variant edge. When set, this item is
    # a deliberately surface-varied sibling of source_question_id — the
    # relationship §29 asks for, not just a shared skill_id + TRANSFER tag.
    source_question_id: Mapped[str | None] = uuid_fk("questions.id", nullable=True)
    surface_variation: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Attempt(Base):
    """"The assessment record" from §21 — what was asked, targeted skill (via
    question.skill_id), difficulty (via question.difficulty), content
    version (snapshotted at submission, §41/§42 provenance), learner
    response, evaluation method, evaluation confidence, and timestamp all
    live on this one row."""

    __tablename__ = "attempts"
    __table_args__ = (UniqueConstraint("tenant_id", "idempotency_key", name="uq_attempts_tenant_idempotency_key"),)

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = uuid_fk("tenants.id")
    student_user_id: Mapped[str] = uuid_fk("users.id")
    question_id: Mapped[str] = uuid_fk("questions.id")
    assessment_type: Mapped[AssessmentType] = mapped_column(_enum_column(AssessmentType, "assessment_type"), nullable=False)
    # Snapshot of Question.content_version at submission time — if the
    # question is edited later, historical attempts still say which version
    # of the content they actually answered (§41).
    question_content_version: Mapped[int] = mapped_column(Integer, nullable=False)
    learner_response: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool | None] = mapped_column(nullable=True)
    evaluation_method: Mapped[EvaluationMethod | None] = mapped_column(
        _enum_column(EvaluationMethod, "evaluation_method"), nullable=True
    )
    evaluation_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Client-supplied, required (§130 idempotent event ingestion): a retried
    # submit-attempt call with the same key returns the existing row instead
    # of creating a duplicate.
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
