"""Knowledge State (§24, ADR-012): a cached, re-derivable materialized view
over the Evidence log for one (student, skill, facet) — never a second
source of truth. `app/services/knowledge_state_service.py` is the only code
path that writes this table, and it always recomputes the full posterior
from Evidence before upserting, per ADR-012's "recompute from log, don't
mutate incrementally" decision (reproducibility, §99).

Never read `mastery_probability` alone as a fact — always pair it with
`confidence_label` (§26). There is deliberately no `mastery = true` column.
"""
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._types import uuid_fk, uuid_pk, utcnow
from app.models.curriculum import SkillFacetType


def _enum_column(enum_cls, name: str):
    return Enum(enum_cls, name=name, native_enum=False, values_callable=lambda ec: [e.value for e in ec])


class ConfidenceLabel(str, enum.Enum):
    """§26 language discipline, enforced structurally: the API vocabulary is
    this closed set, never a bare float."""

    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    LOW_CONFIDENCE = "low_confidence"
    HIGH_CONFIDENCE = "high_confidence"


class KnowledgeState(Base):
    __tablename__ = "knowledge_states"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "student_user_id", "skill_id", "facet_type", name="uq_knowledge_states_student_skill_facet"
        ),
    )

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = uuid_fk("tenants.id")
    student_user_id: Mapped[str] = uuid_fk("users.id")
    skill_id: Mapped[str] = uuid_fk("skills.id")
    facet_type: Mapped[SkillFacetType] = mapped_column(
        _enum_column(SkillFacetType, "knowledge_state_facet_type"), nullable=False
    )
    # Beta posterior parameters (ADR-012). Never negative, never both zero —
    # the prior (1.0, 1.0) is the floor.
    alpha: Mapped[float] = mapped_column(Float, nullable=False)
    beta: Mapped[float] = mapped_column(Float, nullable=False)
    mastery_probability: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_label: Mapped[ConfidenceLabel] = mapped_column(
        _enum_column(ConfidenceLabel, "knowledge_state_confidence_label"), nullable=False
    )
    # effective_n and variance are internal/debugging fields (ADR-012's
    # "Confidence" section) — not the vocabulary an API consumer should read
    # mastery through; confidence_label is that vocabulary.
    effective_n: Mapped[float] = mapped_column(Float, nullable=False)
    variance: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    # The instant the posterior was evaluated at — decay is relative to this,
    # not to `computed_at` (§99: reproducibility requires as_of to be an
    # explicit input, never an implicit "now" read inside the computation).
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
