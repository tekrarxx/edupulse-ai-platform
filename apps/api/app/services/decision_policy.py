"""Decision policy (ADR-013): pure candidate-action scoring, no DB, no
implicit clock — a pure function of five FacetInput values, so it is
directly property-testable and reproducible (§99). Kept separate from
app/services/authorization_service.py per §37: this module answers "what
should follow," never "is it allowed."
"""
from dataclasses import dataclass

from app.models.curriculum import SkillFacetType
from app.models.decision import CandidateActionType, ReasonCode
from app.models.knowledge_state import ConfidenceLabel

POLICY_VERSION = "pde-policy-v1"

_CONFIDENCE_WEIGHT = {
    ConfidenceLabel.INSUFFICIENT_EVIDENCE: 0.0,
    ConfidenceLabel.LOW_CONFIDENCE: 0.5,
    ConfidenceLabel.HIGH_CONFIDENCE: 1.0,
}

_REASON_CODES: dict[CandidateActionType, tuple[ReasonCode, ...]] = {
    CandidateActionType.INSUFFICIENT_EVIDENCE_ACTION: (ReasonCode.INSUFFICIENT_EVIDENCE_OVERALL,),
    CandidateActionType.RETRIEVAL_QUESTION: (ReasonCode.LOW_CONFIDENCE_APPLICATION,),
    CandidateActionType.NEW_CONCEPT_EXPLANATION: (ReasonCode.LOW_MASTERY_RECOGNITION, ReasonCode.LOW_MASTERY_RECALL),
    CandidateActionType.EASIER_TASK: (ReasonCode.LOW_MASTERY_APPLICATION,),
    CandidateActionType.HARDER_TASK: (ReasonCode.HIGH_MASTERY_APPLICATION,),
    CandidateActionType.TRANSFER_TASK: (ReasonCode.HIGH_MASTERY_APPLICATION, ReasonCode.TRANSFER_NOT_YET_EVIDENCED),
    CandidateActionType.REVIEW_TASK: (ReasonCode.AMBIGUOUS_APPLICATION_EVIDENCE, ReasonCode.RETENTION_EVIDENCE_STALE),
    CandidateActionType.DELAYED_RETENTION_ASSESSMENT: (
        ReasonCode.HIGH_MASTERY_APPLICATION,
        ReasonCode.RETENTION_EVIDENCE_STALE,
    ),
    CandidateActionType.HINT: (ReasonCode.LOW_MASTERY_APPLICATION,),
    CandidateActionType.WORKED_EXAMPLE: (ReasonCode.LOW_MASTERY_RECOGNITION,),
    CandidateActionType.TEACHER_INTERVENTION: (ReasonCode.CONTRADICTORY_EVIDENCE,),
    CandidateActionType.DEFER_DECISION: (ReasonCode.NO_ACTION_STRONGLY_INDICATED,),
}


@dataclass(frozen=True)
class FacetInput:
    mastery_probability: float
    confidence_label: ConfidenceLabel


@dataclass(frozen=True)
class CandidateActionScore:
    action: CandidateActionType
    score: float
    reason_codes: tuple[ReasonCode, ...]


def _w(facet: FacetInput) -> float:
    return _CONFIDENCE_WEIGHT[facet.confidence_label]


def score_candidates(facet_states: dict[SkillFacetType, FacetInput]) -> list[CandidateActionScore]:
    """ADR-013's scoring formulas. `facet_states` must have all five
    SkillFacetType keys. Returns all 12 CandidateActionType entries, sorted
    descending by score, ties broken by CandidateActionType declaration
    order (§99 reproducibility)."""
    app = facet_states[SkillFacetType.APPLICATION]
    rec = facet_states[SkillFacetType.RECOGNITION]
    rcl = facet_states[SkillFacetType.RECALL]
    trf = facet_states[SkillFacetType.TRANSFER]
    ret = facet_states[SkillFacetType.RETENTION]

    w_app, w_rec, w_rcl, w_trf, w_ret = _w(app), _w(rec), _w(rcl), _w(trf), _w(ret)
    p_app, p_rec, p_rcl, p_trf = app.mastery_probability, rec.mastery_probability, rcl.mastery_probability, trf.mastery_probability

    easier_task_score = w_app * max(0.0, 0.5 - p_app) * 2.0
    new_concept_score = 0.6 * w_rec * (1.0 - p_rec) + 0.4 * w_rcl * (1.0 - p_rcl)

    scores: dict[CandidateActionType, float] = {
        CandidateActionType.INSUFFICIENT_EVIDENCE_ACTION: 1.0 - w_app,
        CandidateActionType.RETRIEVAL_QUESTION: 0.85 * (1.0 - w_app) + 0.15 * (1.0 - w_rec),
        CandidateActionType.NEW_CONCEPT_EXPLANATION: new_concept_score,
        CandidateActionType.EASIER_TASK: easier_task_score,
        CandidateActionType.HARDER_TASK: w_app * max(0.0, p_app - 0.5) * 2.0 * (1.0 - w_trf),
        CandidateActionType.TRANSFER_TASK: w_app * p_app * (1.0 - w_trf),
        CandidateActionType.REVIEW_TASK: w_app * (1.0 - abs(2.0 * p_app - 1.0)) * 0.6 + (1.0 - w_ret) * 0.4,
        CandidateActionType.DELAYED_RETENTION_ASSESSMENT: w_app * p_app * w_trf * p_trf * (1.0 - w_ret),
        CandidateActionType.HINT: 0.5 * easier_task_score,
        CandidateActionType.WORKED_EXAMPLE: 0.5 * new_concept_score,
        CandidateActionType.TEACHER_INTERVENTION: (
            1.0 if (app.confidence_label == ConfidenceLabel.LOW_CONFIDENCE and 0.4 <= p_app <= 0.6) else 0.05
        ),
        CandidateActionType.DEFER_DECISION: 0.05,
    }

    ordered_actions = list(CandidateActionType)
    ranked = sorted(
        (
            CandidateActionScore(action=action, score=scores[action], reason_codes=_REASON_CODES[action])
            for action in ordered_actions
        ),
        key=lambda entry: (-entry.score, ordered_actions.index(entry.action)),
    )
    return ranked
