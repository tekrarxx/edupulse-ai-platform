"""Prometheus Decision Engine orchestration (§32, ADR-013). The only code
path that writes the `decisions` table: pulls knowledge states from Phase 5
(app/services/knowledge_state_service.py), scores candidates
(decision_policy.py), authorizes the selection (authorization_service.py),
and persists the full structured, explainable record — three separate
modules, one orchestrator, per §35/§37.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.curriculum import Skill, SkillFacetType
from app.models.decision import AuthorizationResult, Decision
from app.models.evidence import Evidence
from app.models.relationship import ParentStudentLink
from app.models.user import User
from app.services import decision_policy, knowledge_state_service
from app.services.audit_service import record_audit
from app.services.authorization_service import authorize
from app.services.decision_policy import FacetInput

MODEL_VERSION = knowledge_state_service.MODEL_VERSION
_MAJORITY_AGE_YEARS = 18


class DecisionEngineError(Exception):
    pass


class SkillNotFound(DecisionEngineError):
    pass


def _is_minor(date_of_birth, *, as_of: datetime) -> bool:
    """None (unknown date of birth) is never treated as minor — §105: an
    unrecorded fact is not evidence of anything, so it cannot trigger a
    consent gate that assumes minor status."""
    if date_of_birth is None:
        return False
    today = as_of.date()
    age_years = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
    return age_years < _MAJORITY_AGE_YEARS


def generate_decision(
    db: Session,
    *,
    tenant_id: str,
    student_user_id: str,
    skill_id: str,
    is_shadow: bool,
    as_of: datetime | None = None,
    requesting_user_id: str | None = None,
) -> Decision:
    if db.get(Skill, skill_id) is None:
        raise SkillNotFound()

    as_of = as_of or datetime.now(timezone.utc)

    knowledge_states = knowledge_state_service.get_knowledge_states_for_skill(
        db, tenant_id=tenant_id, student_user_id=student_user_id, skill_id=skill_id, as_of=as_of
    )
    facet_states = {
        ks.facet_type: FacetInput(mastery_probability=ks.mastery_probability, confidence_label=ks.confidence_label)
        for ks in knowledge_states
    }

    ranked = decision_policy.score_candidates(facet_states)
    selected = ranked[0]

    student = db.get(User, student_user_id)
    is_minor = _is_minor(student.date_of_birth if student is not None else None, as_of=as_of)
    has_guardian_consent = (
        is_minor
        and db.query(ParentStudentLink)
        .filter(
            ParentStudentLink.tenant_id == tenant_id,
            ParentStudentLink.student_user_id == student_user_id,
            ParentStudentLink.consent_given_at.isnot(None),
        )
        .first()
        is not None
    )

    authorization_result, authorization_reason = authorize(
        selected_action=selected.action,
        primary_facet_confidence_label=facet_states[SkillFacetType.APPLICATION].confidence_label,
        is_minor=is_minor,
        has_guardian_consent=has_guardian_consent,
    )

    evidence_ids = [
        row.id
        for row in db.query(Evidence.id)
        .filter(Evidence.tenant_id == tenant_id, Evidence.student_user_id == student_user_id, Evidence.skill_id == skill_id)
        .all()
    ]

    knowledge_state_snapshot = [
        {
            "facet_type": ks.facet_type.value,
            "mastery_probability": ks.mastery_probability,
            "confidence_label": ks.confidence_label.value,
            "evidence_count": ks.evidence_count,
            "model_version": ks.model_version,
            "as_of": ks.as_of.isoformat(),
        }
        for ks in knowledge_states
    ]

    decision = Decision(
        tenant_id=tenant_id,
        student_user_id=student_user_id,
        skill_id=skill_id,
        selected_action=selected.action,
        candidate_actions=[
            {"action": entry.action.value, "score": entry.score, "reason_codes": [rc.value for rc in entry.reason_codes]}
            for entry in ranked
        ],
        reason_codes=[rc.value for rc in selected.reason_codes],
        policy_version=decision_policy.POLICY_VERSION,
        model_version=MODEL_VERSION,
        confidence=max(0.0, min(1.0, selected.score - (ranked[1].score if len(ranked) > 1 else 0.0))),
        knowledge_state_snapshot=knowledge_state_snapshot,
        evidence_ids=evidence_ids,
        authorization_result=authorization_result,
        authorization_reason=authorization_reason,
        is_shadow=is_shadow,
    )
    db.add(decision)
    db.flush()

    # §85/§131: an ESCALATED decision is Prometheus saying "a human should
    # look at this" — a real (non-shadow) escalation is exactly the kind of
    # "important decision" §131 asks to be auditable, distinct from
    # AIUsageRecord (AI cost/reliability accounting) and from Decision's own
    # append-only row (the full explainable trace already lives there).
    if not is_shadow and authorization_result == AuthorizationResult.ESCALATED:
        record_audit(
            db,
            tenant_id=tenant_id,
            actor_user_id=requesting_user_id,
            action="decision.escalated",
            target_type="decision",
            target_id=decision.id,
        )

    db.commit()
    db.refresh(decision)
    return decision
