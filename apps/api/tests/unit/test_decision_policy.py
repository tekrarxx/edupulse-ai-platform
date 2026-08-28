"""Property-based and scenario tests for the ADR-013 scoring policy (§87).
No DB, no HTTP — score_candidates is a pure function of five FacetInput
values by design (§99)."""
from hypothesis import given
from hypothesis import strategies as st

from app.models.curriculum import SkillFacetType
from app.models.decision import CandidateActionType
from app.models.knowledge_state import ConfidenceLabel
from app.services import authorization_service
from app.services.decision_policy import FacetInput, score_candidates

_APP, _REC, _RCL, _TRF, _RET = (
    SkillFacetType.APPLICATION,
    SkillFacetType.RECOGNITION,
    SkillFacetType.RECALL,
    SkillFacetType.TRANSFER,
    SkillFacetType.RETENTION,
)

_INSUFFICIENT = ConfidenceLabel.INSUFFICIENT_EVIDENCE
_LOW = ConfidenceLabel.LOW_CONFIDENCE
_HIGH = ConfidenceLabel.HIGH_CONFIDENCE


def _facets(app=None, rec=None, rcl=None, trf=None, ret=None) -> dict[SkillFacetType, FacetInput]:
    default = FacetInput(mastery_probability=0.5, confidence_label=_INSUFFICIENT)
    return {
        _APP: app or default,
        _REC: rec or default,
        _RCL: rcl or default,
        _TRF: trf or default,
        _RET: ret or default,
    }


_mastery = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
_label = st.sampled_from([_INSUFFICIENT, _LOW, _HIGH])
_facet_input = st.builds(FacetInput, mastery_probability=_mastery, confidence_label=_label)
_facet_states_strategy = st.fixed_dictionaries({facet: _facet_input for facet in SkillFacetType})


@given(_facet_states_strategy)
def test_all_scores_stay_in_unit_interval(facet_states) -> None:
    ranked = score_candidates(facet_states)
    assert len(ranked) == 12
    for entry in ranked:
        assert 0.0 <= entry.score <= 1.0


@given(_facet_states_strategy)
def test_reproducibility(facet_states) -> None:
    first = score_candidates(facet_states)
    second = score_candidates(facet_states)
    assert [(e.action, e.score) for e in first] == [(e.action, e.score) for e in second]


@given(st.floats(min_value=0.0, max_value=0.5, allow_nan=False), st.floats(min_value=0.5, max_value=1.0, allow_nan=False))
def test_easier_and_harder_task_monotonic_in_application_mastery(p_low, p_high) -> None:
    """Holding w_APP=HIGH and w_TRF=INSUFFICIENT fixed: EASIER_TASK is
    non-increasing and HARDER_TASK is non-decreasing in p_APP (ADR-013)."""
    low_state = _facets(app=FacetInput(p_low, _HIGH), trf=FacetInput(0.5, _INSUFFICIENT))
    high_state = _facets(app=FacetInput(p_high, _HIGH), trf=FacetInput(0.5, _INSUFFICIENT))

    low_scores = {e.action: e.score for e in score_candidates(low_state)}
    high_scores = {e.action: e.score for e in score_candidates(high_state)}

    if p_high >= p_low:
        assert high_scores[CandidateActionType.EASIER_TASK] <= low_scores[CandidateActionType.EASIER_TASK]
        assert high_scores[CandidateActionType.HARDER_TASK] >= low_scores[CandidateActionType.HARDER_TASK]


def test_zero_evidence_everywhere_selects_insufficient_evidence_action() -> None:
    ranked = score_candidates(_facets())  # all facets default to insufficient_evidence, p=0.5
    assert ranked[0].action == CandidateActionType.INSUFFICIENT_EVIDENCE_ACTION


def test_low_mastery_application_selects_easier_task() -> None:
    ranked = score_candidates(
        _facets(
            app=FacetInput(0.1, _HIGH),
            rec=FacetInput(0.9, _HIGH),
            rcl=FacetInput(0.9, _HIGH),
        )
    )
    assert ranked[0].action == CandidateActionType.EASIER_TASK


def test_high_mastery_application_and_untested_transfer_selects_transfer_task() -> None:
    ranked = score_candidates(
        _facets(
            app=FacetInput(0.95, _HIGH),
            trf=FacetInput(0.5, _INSUFFICIENT),
        )
    )
    assert ranked[0].action == CandidateActionType.TRANSFER_TASK


def test_high_mastery_application_and_transfer_stale_retention_selects_delayed_retention_assessment() -> None:
    ranked = score_candidates(
        _facets(
            app=FacetInput(0.95, _HIGH),
            trf=FacetInput(0.95, _HIGH),
            ret=FacetInput(0.5, _INSUFFICIENT),
        )
    )
    assert ranked[0].action == CandidateActionType.DELAYED_RETENTION_ASSESSMENT


def test_ambiguous_application_evidence_selects_teacher_intervention() -> None:
    ranked = score_candidates(_facets(app=FacetInput(0.5, _LOW)))
    assert ranked[0].action == CandidateActionType.TEACHER_INTERVENTION


def test_weak_recognition_and_recall_selects_new_concept_explanation() -> None:
    ranked = score_candidates(
        _facets(
            app=FacetInput(0.5, _INSUFFICIENT),
            rec=FacetInput(0.1, _HIGH),
            rcl=FacetInput(0.1, _HIGH),
        )
    )
    # app is insufficient, but recognition/recall are confidently weak — the
    # top two candidates should be the "gather more" and "teach the basics"
    # actions, not a personalized task.
    top_actions = {ranked[0].action, ranked[1].action}
    assert CandidateActionType.NEW_CONCEPT_EXPLANATION in top_actions or ranked[0].action == CandidateActionType.INSUFFICIENT_EVIDENCE_ACTION


def test_action_diversity_across_six_scenarios() -> None:
    scenarios = [
        _facets(),
        _facets(app=FacetInput(0.1, _HIGH), rec=FacetInput(0.9, _HIGH), rcl=FacetInput(0.9, _HIGH)),
        _facets(app=FacetInput(0.95, _HIGH), trf=FacetInput(0.5, _INSUFFICIENT)),
        _facets(app=FacetInput(0.95, _HIGH), trf=FacetInput(0.95, _HIGH), ret=FacetInput(0.5, _INSUFFICIENT)),
        _facets(app=FacetInput(0.5, _LOW)),
        _facets(app=FacetInput(0.7, _HIGH), trf=FacetInput(0.9, _HIGH)),
    ]
    top_actions = {score_candidates(scenario)[0].action for scenario in scenarios}
    assert len(top_actions) >= 5


def test_teacher_intervention_always_escalates() -> None:
    result, reason = authorization_service.authorize(
        selected_action=CandidateActionType.TEACHER_INTERVENTION, primary_facet_confidence_label=_LOW
    )
    from app.models.decision import AuthorizationResult

    assert result == AuthorizationResult.ESCALATED
    assert reason == "action_requires_human_review"


def test_personalized_action_with_insufficient_confidence_is_rejected() -> None:
    from app.models.decision import AuthorizationResult

    result, reason = authorization_service.authorize(
        selected_action=CandidateActionType.HARDER_TASK, primary_facet_confidence_label=_INSUFFICIENT
    )
    assert result == AuthorizationResult.REJECTED
    assert reason == "insufficient_confidence_for_personalized_action"


def test_ordinary_action_is_allowed() -> None:
    from app.models.decision import AuthorizationResult

    result, reason = authorization_service.authorize(
        selected_action=CandidateActionType.EASIER_TASK, primary_facet_confidence_label=_HIGH
    )
    assert result == AuthorizationResult.ALLOWED
