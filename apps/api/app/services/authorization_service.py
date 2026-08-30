"""Decision authorization (§37, ADR-013): a second, independent pure
function that only inspects the policy's output — it never re-runs
app/services/decision_policy.py's scoring. This separation is mandatory
(§35, §37): decision generation and authorization are different questions
("what should follow" vs "is it allowed") and must be different code paths.

Three rules exist:
  1. TEACHER_INTERVENTION always escalates (the policy already decided a
     human should look at this).
  2. A personalized action is rejected outright when the primary facet's
     confidence is insufficient (not enough evidence to justify adapting
     difficulty/transfer/retention timing for this specific learner yet).
  3. §81: a minor student with no recorded guardian consent has every
     otherwise-ALLOWED action escalated for human review instead of
     auto-executed (Phase 10, closing the gap this module used to document
     as "no consent/age data model exists yet" — ParentStudentLink.consent_
     given_at and User.date_of_birth now exist, see ADR-013 Addendum).

Explicit remaining scope gap: role- and tenant-education-policy-based checks
(e.g. a tenant restricting which action types it allows at all) are still
NOT implemented — no such policy data model exists yet, and a fake check
that always passes would violate §105.
"""
from app.models.decision import AuthorizationResult, CandidateActionType
from app.models.knowledge_state import ConfidenceLabel

_PERSONALIZED_ACTIONS = {
    CandidateActionType.EASIER_TASK,
    CandidateActionType.HARDER_TASK,
    CandidateActionType.TRANSFER_TASK,
    CandidateActionType.DELAYED_RETENTION_ASSESSMENT,
}


def authorize(
    *,
    selected_action: CandidateActionType,
    primary_facet_confidence_label: ConfidenceLabel,
    is_minor: bool = False,
    has_guardian_consent: bool = False,
) -> tuple[AuthorizationResult, str]:
    if selected_action == CandidateActionType.TEACHER_INTERVENTION:
        return AuthorizationResult.ESCALATED, "action_requires_human_review"

    if (
        selected_action in _PERSONALIZED_ACTIONS
        and primary_facet_confidence_label == ConfidenceLabel.INSUFFICIENT_EVIDENCE
    ):
        return AuthorizationResult.REJECTED, "insufficient_confidence_for_personalized_action"

    if is_minor and not has_guardian_consent:
        return AuthorizationResult.ESCALATED, "minor_without_guardian_consent"

    return AuthorizationResult.ALLOWED, "confidence_and_role_checks_passed"
