"""Observation (§22) doubles as this project's immutable event log (§40)
rather than building two parallel systems: both require tenant_id, actor,
subject, timestamp, event type, payload, schema version, correlation ID, and
immutability, and Observation's whole purpose — a directly recorded fact,
no inferred conclusion — is a stricter version of the same event-sourcing
idea. This consolidation is a deliberate scope decision for Phase 3/P3, not
an oversight (§106).

Append-only is enforced at the database level (a trigger rejects UPDATE and
DELETE — see alembic/versions/0004_assessment_observation_evidence.py),
not by application convention, so it holds even against a raw SQL statement
or a future bug that bypasses the service layer.
"""
import enum
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._types import uuid_fk, uuid_pk, utcnow


class ObservationEventType(str, enum.Enum):
    """§22's own examples — a fixed, closed vocabulary. A client can never
    invent an event type, which is one half of what keeps an Observation
    from smuggling in an interpreted conclusion (the other half is the
    payload key denylist in app/schemas/assessment.py)."""

    ANSWER_SUBMITTED = "answer_submitted"
    ANSWER_CORRECT = "answer_correct"
    ANSWER_INCORRECT = "answer_incorrect"
    HINT_REQUESTED = "hint_requested"
    TIME_SPENT = "time_spent"
    TASK_COMPLETED = "task_completed"
    TRANSFER_FAILED = "transfer_failed"
    RETENTION_ASSESSMENT_COMPLETED = "retention_assessment_completed"


class Observation(Base):
    __tablename__ = "observations"
    __table_args__ = (UniqueConstraint("tenant_id", "idempotency_key", name="uq_observations_tenant_idempotency_key"),)

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = uuid_fk("tenants.id")
    actor_user_id: Mapped[str | None] = uuid_fk("users.id", nullable=True)
    subject_type: Mapped[str] = mapped_column(String(50), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_type: Mapped[ObservationEventType] = mapped_column(
        Enum(ObservationEventType, name="observation_event_type", native_enum=False, values_callable=lambda ec: [e.value for e in ec]),
        nullable=False,
    )
    # Primitive-scalar-only JSON object — enforced by the Pydantic schema at
    # the API boundary (app/schemas/assessment.py), not by this column type.
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
