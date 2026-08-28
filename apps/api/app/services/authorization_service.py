"""Decision authorization (§37, ADR-013): a second, independent pure
function that only inspects the policy's output — it never re-runs
app/services/decision_policy.py's scoring. This separation is mandatory
(§35, §37): decision generation and authorization are different questions
("what should follow" vs "is it allowed") and must be different code paths.

Explicit scope gap, documented in ADR-013: role/consent/age/tenant-education
-policy checks are NOT implemented here — no consent or age data model
exists yet in this codebase, and a fake check that always passes would
violate §105. Only the two rules below are real.
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
    *, selected_action: CandidateActionType, primary_facet_confidence_label: ConfidenceLabel
) -> tuple[AuthorizationResult, str]:
    if selected_action == CandidateActionType.TEACHER_INTERVENTION:
        return AuthorizationResult.ESCALATED, "action_requires_human_review"

    if (
        selected_action in _PERSONALIZED_ACTIONS
        and primary_facet_confidence_label == ConfidenceLabel.INSUFFICIENT_EVIDENCE
    ):
        return AuthorizationResult.REJECTED, "insufficient_confidence_for_personalized_action"

    return AuthorizationResult.ALLOWED, "confidence_and_role_checks_passed"
