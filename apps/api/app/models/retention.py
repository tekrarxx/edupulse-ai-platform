"""Delayed retention and falsification (§30, §39, ADR-014).

`RetentionCheckpoint` and `Hypothesis` are created together, one pair per
checkpoint, by app/services/retention_service.py::maybe_schedule_checkpoints
— the only code path that writes either table. The Hypothesis's prediction
is frozen at scheduling time (before the outcome is known) so its verdict
is a genuine falsification test, not a post-hoc description (§39).
"""
import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._types import uuid_fk, uuid_pk, utcnow
from app.models.knowledge_state import ConfidenceLabel


def _enum_column(enum_cls, name: str):
    return Enum(enum_cls, name=name, native_enum=False, values_callable=lambda ec: [e.value for e in ec])


class RetentionCheckpointStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"


class HypothesisType(str, enum.Enum):
    """Closed vocabulary, extensible — only RETENTION_PREDICTION exists in
    this phase; other falsifiable claim types (e.g. a decision-policy
    prediction) are future work, not fabricated here."""

    RETENTION_PREDICTION = "retention_prediction"


class HypothesisVerdict(str, enum.Enum):
    PENDING = "pending"
    SUPPORTED = "supported"
    NOT_SUPPORTED = "not_supported"
    INCONCLUSIVE = "inconclusive"


class RetentionCheckpoint(Base):
    __tablename__ = "retention_checkpoints"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "student_user_id", "skill_id", "checkpoint_days", name="uq_retention_checkpoint_student_skill_days"
        ),
    )

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = uuid_fk("tenants.id")
    student_user_id: Mapped[str] = uuid_fk("users.id")
    skill_id: Mapped[str] = uuid_fk("skills.id")
    checkpoint_days: Mapped[int] = mapped_column(Integer, nullable=False)  # 14 or 28
    # The APPLICATION-facet Evidence row whose high_confidence crossing
    # triggered scheduling (§100 provenance).
    origin_evidence_id: Mapped[str] = uuid_fk("evidence.id")
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[RetentionCheckpointStatus] = mapped_column(
        _enum_column(RetentionCheckpointStatus, "retention_checkpoint_status"),
        nullable=False,
        default=RetentionCheckpointStatus.PENDING,
    )
    delayed_attempt_id: Mapped[str | None] = uuid_fk("attempts.id", nullable=True)
    # The recomputed APPLICATION mastery_probability at completion time —
    # the *actual* measured retention, distinct from Hypothesis's frozen
    # *predicted* value (§30: never a single unexplained percentage).
    retention_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Hypothesis(Base):
    __tablename__ = "hypotheses"

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = uuid_fk("tenants.id")
    student_user_id: Mapped[str] = uuid_fk("users.id")
    skill_id: Mapped[str] = uuid_fk("skills.id")
    hypothesis_type: Mapped[HypothesisType] = mapped_column(
        _enum_column(HypothesisType, "hypothesis_type"), nullable=False
    )
    retention_checkpoint_id: Mapped[str] = uuid_fk("retention_checkpoints.id")
    # Frozen at scheduling time — never recomputed (§39: a falsifiable
    # prediction must be fixed before the outcome is known).
    predicted_mastery_probability: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_confidence_label: Mapped[ConfidenceLabel] = mapped_column(
        _enum_column(ConfidenceLabel, "hypothesis_predicted_confidence_label"), nullable=False
    )
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    verdict: Mapped[HypothesisVerdict] = mapped_column(
        _enum_column(HypothesisVerdict, "hypothesis_verdict"), nullable=False, default=HypothesisVerdict.PENDING
    )
