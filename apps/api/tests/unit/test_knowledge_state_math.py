"""Property-based tests for the ADR-012 Beta-Binomial computation (§87).

These exercise `compute_knowledge_state` directly — no DB, no HTTP — since
it is a pure function of `(evidence_rows, as_of)` by design (§99).
"""
from datetime import datetime, timedelta, timezone

from hypothesis import given
from hypothesis import strategies as st

from app.models.curriculum import SkillFacetType
from app.models.evidence import Evidence, EvidenceDirectness, EvidencePolarity
from app.models.knowledge_state import ConfidenceLabel
from app.services.knowledge_state_service import (
    ALPHA_PRIOR,
    BETA_PRIOR,
    compute_knowledge_state,
)

_AS_OF = datetime(2026, 8, 28, tzinfo=timezone.utc)


def _evidence(
    *,
    polarity: EvidencePolarity,
    reliability: float = 1.0,
    task_validity: float = 1.0,
    evaluation_confidence: float = 1.0,
    directness: EvidenceDirectness = EvidenceDirectness.DIRECT,
    age_days: float = 0.0,
) -> tuple[Evidence, datetime]:
    evidence = Evidence(
        tenant_id="tenant",
        student_user_id="student",
        observation_id="observation",
        skill_id="skill",
        facet_type=SkillFacetType.APPLICATION,
        polarity=polarity,
        directness=directness,
        reliability=reliability,
        task_validity=task_validity,
        transfer_relevance=False,
        evaluation_confidence=evaluation_confidence,
    )
    occurred_at = _AS_OF - timedelta(days=age_days)
    return evidence, occurred_at


_quality = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
_polarity = st.sampled_from([EvidencePolarity.POSITIVE, EvidencePolarity.NEGATIVE])
_directness = st.sampled_from([EvidenceDirectness.DIRECT, EvidenceDirectness.INDIRECT])
_age_days = st.floats(min_value=0.0, max_value=3650.0, allow_nan=False)

_evidence_row = st.tuples(_polarity, _quality, _quality, _quality, _directness, _age_days)


def _rows_from_specs(specs) -> list[tuple[Evidence, datetime]]:
    return [
        _evidence(
            polarity=polarity,
            reliability=reliability,
            task_validity=task_validity,
            evaluation_confidence=evaluation_confidence,
            directness=directness,
            age_days=age_days,
        )
        for polarity, reliability, task_validity, evaluation_confidence, directness, age_days in specs
    ]


@given(st.lists(_evidence_row, max_size=25))
def test_mastery_probability_stays_in_unit_interval(specs) -> None:
    result = compute_knowledge_state(_rows_from_specs(specs), as_of=_AS_OF)
    assert 0.0 <= result.mastery_probability <= 1.0


@given(st.lists(_evidence_row, max_size=25))
def test_zero_evidence_is_the_uninformative_prior(specs) -> None:
    result = compute_knowledge_state([], as_of=_AS_OF)
    assert result.mastery_probability == 0.5
    assert result.confidence_label == ConfidenceLabel.INSUFFICIENT_EVIDENCE
    assert result.alpha == ALPHA_PRIOR
    assert result.beta == BETA_PRIOR


@given(st.lists(_evidence_row, max_size=20))
def test_adding_positive_evidence_never_decreases_mastery(specs) -> None:
    baseline = compute_knowledge_state(_rows_from_specs(specs), as_of=_AS_OF)
    extra_rows = _rows_from_specs(specs) + [_evidence(polarity=EvidencePolarity.POSITIVE)]
    with_extra = compute_knowledge_state(extra_rows, as_of=_AS_OF)
    assert with_extra.mastery_probability >= baseline.mastery_probability


@given(st.lists(_evidence_row, max_size=20))
def test_adding_negative_evidence_never_increases_mastery(specs) -> None:
    baseline = compute_knowledge_state(_rows_from_specs(specs), as_of=_AS_OF)
    extra_rows = _rows_from_specs(specs) + [_evidence(polarity=EvidencePolarity.NEGATIVE)]
    with_extra = compute_knowledge_state(extra_rows, as_of=_AS_OF)
    assert with_extra.mastery_probability <= baseline.mastery_probability


@given(st.lists(_evidence_row, min_size=1, max_size=20))
def test_permutation_invariance(specs) -> None:
    rows = _rows_from_specs(specs)
    forward = compute_knowledge_state(rows, as_of=_AS_OF)
    backward = compute_knowledge_state(list(reversed(rows)), as_of=_AS_OF)
    assert forward.alpha == backward.alpha
    assert forward.beta == backward.beta
    assert forward.mastery_probability == backward.mastery_probability


@given(st.lists(_evidence_row, max_size=25))
def test_reproducibility_same_inputs_same_output(specs) -> None:
    rows = _rows_from_specs(specs)
    first = compute_knowledge_state(rows, as_of=_AS_OF)
    second = compute_knowledge_state(rows, as_of=_AS_OF)
    assert first == second


def test_low_quality_positive_cannot_outweigh_high_quality_negative_transfer_failures() -> None:
    """§27's own example: a trivial recognition success must not outweigh
    multiple high-quality transfer failures."""
    trivial_positive = [
        _evidence(polarity=EvidencePolarity.POSITIVE, reliability=1.0, task_validity=0.1, evaluation_confidence=1.0)
    ]
    quality_negatives = [
        _evidence(polarity=EvidencePolarity.NEGATIVE, reliability=1.0, task_validity=1.0, evaluation_confidence=1.0)
        for _ in range(3)
    ]
    result = compute_knowledge_state(trivial_positive + quality_negatives, as_of=_AS_OF)
    assert result.mastery_probability < 0.5


def test_confidence_label_thresholds() -> None:
    assert compute_knowledge_state([], as_of=_AS_OF).confidence_label == ConfidenceLabel.INSUFFICIENT_EVIDENCE

    two_rows = [_evidence(polarity=EvidencePolarity.POSITIVE) for _ in range(2)]
    assert compute_knowledge_state(two_rows, as_of=_AS_OF).confidence_label == ConfidenceLabel.LOW_CONFIDENCE

    five_rows = [_evidence(polarity=EvidencePolarity.POSITIVE) for _ in range(5)]
    assert compute_knowledge_state(five_rows, as_of=_AS_OF).confidence_label == ConfidenceLabel.HIGH_CONFIDENCE


def test_decay_pulls_old_evidence_toward_insufficient_confidence() -> None:
    fresh = [_evidence(polarity=EvidencePolarity.POSITIVE, age_days=0.0) for _ in range(5)]
    stale = [_evidence(polarity=EvidencePolarity.POSITIVE, age_days=3650.0) for _ in range(5)]

    fresh_result = compute_knowledge_state(fresh, as_of=_AS_OF)
    stale_result = compute_knowledge_state(stale, as_of=_AS_OF)

    assert fresh_result.confidence_label == ConfidenceLabel.HIGH_CONFIDENCE
    assert stale_result.confidence_label == ConfidenceLabel.INSUFFICIENT_EVIDENCE
    assert stale_result.mastery_probability < fresh_result.mastery_probability


def test_older_evidence_never_produces_negative_alpha_or_beta() -> None:
    ancient = [_evidence(polarity=EvidencePolarity.NEGATIVE, age_days=10000.0) for _ in range(10)]
    result = compute_knowledge_state(ancient, as_of=_AS_OF)
    assert result.alpha >= 0.0
    assert result.beta >= 0.0
