"""Unit tests for the ADR-014 falsification verdict rule. Pure function, no
DB — mirrors the ADR-012/ADR-013 pattern of testing the decision math in
isolation."""
from app.models.knowledge_state import ConfidenceLabel
from app.models.retention import HypothesisVerdict
from app.services.retention_service import _evaluate_verdict


def test_low_confidence_prediction_is_always_inconclusive() -> None:
    for actual in (True, False):
        verdict = _evaluate_verdict(
            predicted_confidence_label=ConfidenceLabel.LOW_CONFIDENCE,
            predicted_mastery_probability=0.9,
            actual_is_correct=actual,
        )
        assert verdict == HypothesisVerdict.INCONCLUSIVE


def test_insufficient_evidence_prediction_is_always_inconclusive() -> None:
    verdict = _evaluate_verdict(
        predicted_confidence_label=ConfidenceLabel.INSUFFICIENT_EVIDENCE,
        predicted_mastery_probability=0.5,
        actual_is_correct=True,
    )
    assert verdict == HypothesisVerdict.INCONCLUSIVE


def test_high_confidence_correct_prediction_matching_outcome_is_supported() -> None:
    verdict = _evaluate_verdict(
        predicted_confidence_label=ConfidenceLabel.HIGH_CONFIDENCE,
        predicted_mastery_probability=0.9,
        actual_is_correct=True,
    )
    assert verdict == HypothesisVerdict.SUPPORTED


def test_high_confidence_prediction_mismatching_outcome_is_not_supported() -> None:
    verdict = _evaluate_verdict(
        predicted_confidence_label=ConfidenceLabel.HIGH_CONFIDENCE,
        predicted_mastery_probability=0.9,
        actual_is_correct=False,
    )
    assert verdict == HypothesisVerdict.NOT_SUPPORTED


def test_high_confidence_low_mastery_prediction_matching_incorrect_outcome_is_supported() -> None:
    verdict = _evaluate_verdict(
        predicted_confidence_label=ConfidenceLabel.HIGH_CONFIDENCE,
        predicted_mastery_probability=0.1,
        actual_is_correct=False,
    )
    assert verdict == HypothesisVerdict.SUPPORTED
