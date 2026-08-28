"""Prometheus Decision Engine domain (§32–§39, ADR-013). `Decision` is the
structured, append-only output record (§32, §100); the actual scoring and
authorization logic live in app/services/decision_policy.py and
app/services/authorization_service.py, kept deliberately separate (§35,
§37) — this module only defines the closed vocabularies and the storage
shape.
"""
import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._types import uuid_fk, uuid_pk, utcnow


def _enum_column(enum_cls, name: str):
    return Enum(enum_cls, name=name, native_enum=False, values_callable=lambda ec: [e.value for e in ec])


class CandidateActionType(str, enum.Enum):
    """§34's full candidate set. Declaration order is the deterministic
    tie-break used by decision_policy.score_candidates (§99)."""

    INSUFFICIENT_EVIDENCE_ACTION = "insufficient_evidence_action"
    RETRIEVAL_QUESTION = "retrieval_question"
    NEW_CONCEPT_EXPLANATION = "new_concept_explanation"
    EASIER_TASK = "easier_task"
    HARDER_TASK = "harder_task"
    TRANSFER_TASK = "transfer_task"
    REVIEW_TASK = "review_task"
    DELAYED_RETENTION_ASSESSMENT = "delayed_retention_assessment"
    HINT = "hint"
    WORKED_EXAMPLE = "worked_example"
    TEACHER_INTERVENTION = "teacher_intervention"
    DEFER_DECISION = "defer_decision"


class ReasonCode(str, enum.Enum):
    """Closed vocabulary (ADR-013 "Reason codes") — structural, one fixed
    set per CandidateActionType, not free text."""

    INSUFFICIENT_EVIDENCE_OVERALL = "insufficient_evidence_overall"
    LOW_CONFIDENCE_APPLICATION = "low_confidence_application"
    LOW_MASTERY_RECOGNITION = "low_mastery_recognition"
    LOW_MASTERY_RECALL = "low_mastery_recall"
    LOW_MASTERY_APPLICATION = "low_mastery_application"
    HIGH_MASTERY_APPLICATION = "high_mastery_application"
    TRANSFER_NOT_YET_EVIDENCED = "transfer_not_yet_evidenced"
    AMBIGUOUS_APPLICATION_EVIDENCE = "ambiguous_application_evidence"
    RETENTION_EVIDENCE_STALE = "retention_evidence_stale"
    CONTRADICTORY_EVIDENCE = "contradictory_evidence"
    NO_ACTION_STRONGLY_INDICATED = "no_action_strongly_indicated"


class AuthorizationResult(str, enum.Enum):
    ALLOWED = "allowed"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class Decision(Base):
    """Append-only (Postgres trigger, see alembic/versions/0006_decision.py,
    same pattern as Observation). Nothing updates or deletes a Decision row
    from application code — a re-evaluation produces a new row, never an
    edit, so decision history is a faithful, tamper-evident log (§100)."""

    __tablename__ = "decisions"

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = uuid_fk("tenants.id")
    student_user_id: Mapped[str] = uuid_fk("users.id")
    skill_id: Mapped[str] = uuid_fk("skills.id")
    selected_action: Mapped[CandidateActionType] = mapped_column(
        _enum_column(CandidateActionType, "decision_selected_action"), nullable=False
    )
    # Full ranked list: [{"action": str, "score": float, "reason_codes": [str, ...]}, ...]
    # for all 12 evaluated actions (§32 "candidate_actions" + "scores").
    candidate_actions: Mapped[list] = mapped_column(JSON, nullable=False)
    # The selected action's own reason codes, duplicated at the top level
    # for direct access without re-scanning candidate_actions (§32).
    reason_codes: Mapped[list] = mapped_column(JSON, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    # Per-facet knowledge-state summary at decision time (§100 provenance):
    # [{"facet_type": str, "mastery_probability": float, "confidence_label": str,
    #   "evidence_count": int, "model_version": str, "as_of": iso str}, ...]
    knowledge_state_snapshot: Mapped[list] = mapped_column(JSON, nullable=False)
    # Every Evidence id that fed into any of the five facet states (§100).
    evidence_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    authorization_result: Mapped[AuthorizationResult] = mapped_column(
        _enum_column(AuthorizationResult, "decision_authorization_result"), nullable=False
    )
    authorization_reason: Mapped[str] = mapped_column(Text, nullable=False)
    # §38: true if this decision must never be surfaced as the learner's
    # actionable next step — see app/api/routes/decision.py for enforcement.
    is_shadow: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
