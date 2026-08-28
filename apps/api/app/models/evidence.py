"""Evidence (§23, §27): an interpreted signal, always derived from — and
foreign-keyed to — exactly one Observation. There is no API path that
creates Evidence directly; it only ever comes out of
assessment_service.evaluate_attempt, which is what guarantees every row
traces back to a raw fact (§23 "never store an inference as if it were a
raw observation").

Failure-mode discrimination (§31, ADR-014): `failure_mode` is nullable and
has two distinct write paths — TRANSFER_FAILURE/RETENTION_FAILURE are set
automatically in assessment_service (structural facts, not inferences),
while LACK_OF_KNOWLEDGE/RETRIEVAL_FAILURE/CARELESS_ERROR/MISCONCEPTION can
only be set via the explicit teacher-only classification endpoint — never
automatically from a single incorrect answer, per §31's own warning.
"""
import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._types import uuid_fk, uuid_pk, utcnow
from app.models.curriculum import SkillFacetType


def _enum_column(enum_cls, name: str):
    return Enum(enum_cls, name=name, native_enum=False, values_callable=lambda ec: [e.value for e in ec])


class EvidencePolarity(str, enum.Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


class EvidenceDirectness(str, enum.Enum):
    """§27. Every Evidence row this phase produces is DIRECT (a graded
    attempt at the skill itself); INDIRECT is modeled for a future source
    (e.g. a teacher's qualitative observation) that does not exist yet."""

    DIRECT = "direct"
    INDIRECT = "indirect"


class FailureMode(str, enum.Enum):
    """§31, ADR-014. LACK_OF_KNOWLEDGE/RETRIEVAL_FAILURE/CARELESS_ERROR/
    MISCONCEPTION require a human classification (see
    app/services/assessment_service.py::classify_failure_mode); only
    TRANSFER_FAILURE and RETENTION_FAILURE are ever set automatically, and
    only for their matching facet_type."""

    LACK_OF_KNOWLEDGE = "lack_of_knowledge"
    RETRIEVAL_FAILURE = "retrieval_failure"
    CARELESS_ERROR = "careless_error"
    MISCONCEPTION = "misconception"
    TRANSFER_FAILURE = "transfer_failure"
    RETENTION_FAILURE = "retention_failure"


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = uuid_fk("tenants.id")
    student_user_id: Mapped[str] = uuid_fk("users.id")
    observation_id: Mapped[str] = uuid_fk("observations.id")
    skill_id: Mapped[str] = uuid_fk("skills.id")
    facet_type: Mapped[SkillFacetType] = mapped_column(_enum_column(SkillFacetType, "evidence_facet_type"), nullable=False)
    polarity: Mapped[EvidencePolarity] = mapped_column(_enum_column(EvidencePolarity, "evidence_polarity"), nullable=False)
    directness: Mapped[EvidenceDirectness] = mapped_column(
        _enum_column(EvidenceDirectness, "evidence_directness"), nullable=False, default=EvidenceDirectness.DIRECT
    )
    # §27 quality attributes. Recency is deliberately NOT a stored column —
    # it is "how long ago was this" relative to *now*, which changes on
    # every read, so it is computed at query time from occurred_at on the
    # linked Observation rather than frozen at write time.
    reliability: Mapped[float] = mapped_column(Float, nullable=False)
    task_validity: Mapped[float] = mapped_column(Float, nullable=False)
    transfer_relevance: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evaluation_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    failure_mode: Mapped[FailureMode | None] = mapped_column(
        _enum_column(FailureMode, "evidence_failure_mode"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
