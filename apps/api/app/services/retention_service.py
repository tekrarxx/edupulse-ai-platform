"""Delayed retention scheduling, due-listing, and completion (§30, §39,
ADR-014). Reuses knowledge_state_service (Phase 5) and
assessment_service.submit_attempt (Phase 4) rather than duplicating their
logic — this module only adds the scheduling/completion/falsification layer
on top.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.assessment import AssessmentType, Question
from app.models.curriculum import SkillFacetType
from app.models.knowledge_state import ConfidenceLabel
from app.models.retention import (
    Hypothesis,
    HypothesisType,
    HypothesisVerdict,
    RetentionCheckpoint,
    RetentionCheckpointStatus,
)
from app.schemas.assessment import SubmitAttemptRequest
from app.services import assessment_service, knowledge_state_service

CHECKPOINT_DAYS = (14, 28)


class RetentionError(Exception):
    pass


class CheckpointNotFound(RetentionError):
    pass


class CheckpointAlreadyCompleted(RetentionError):
    pass


class WrongSkillForCheckpoint(RetentionError):
    pass


class OpenEndedQuestionNotSupported(RetentionError):
    """ADR-014: v1 requires an auto-gradable question so the falsification
    verdict has a definite is_correct at completion time."""


def maybe_schedule_checkpoints(
    db: Session,
    *,
    tenant_id: str,
    student_user_id: str,
    skill_id: str,
    facet_type: SkillFacetType,
    origin_evidence_id: str,
    as_of: datetime | None = None,
) -> list[RetentionCheckpoint]:
    """Called from assessment_service._apply_evaluation after every graded
    attempt. No-op unless facet_type is APPLICATION and this is the first
    time this (tenant, student, skill) crosses high_confidence — ADR-014's
    scheduling trigger."""
    if facet_type != SkillFacetType.APPLICATION:
        return []

    already_scheduled = (
        db.query(RetentionCheckpoint)
        .filter(
            RetentionCheckpoint.tenant_id == tenant_id,
            RetentionCheckpoint.student_user_id == student_user_id,
            RetentionCheckpoint.skill_id == skill_id,
        )
        .first()
    )
    if already_scheduled is not None:
        return []

    as_of = as_of or datetime.now(timezone.utc)
    knowledge_state = knowledge_state_service.get_or_recompute_knowledge_state(
        db,
        tenant_id=tenant_id,
        student_user_id=student_user_id,
        skill_id=skill_id,
        facet_type=SkillFacetType.APPLICATION,
        as_of=as_of,
    )
    if knowledge_state.confidence_label != ConfidenceLabel.HIGH_CONFIDENCE:
        return []

    checkpoints: list[RetentionCheckpoint] = []
    for days in CHECKPOINT_DAYS:
        checkpoint = RetentionCheckpoint(
            tenant_id=tenant_id,
            student_user_id=student_user_id,
            skill_id=skill_id,
            checkpoint_days=days,
            origin_evidence_id=origin_evidence_id,
            scheduled_for=as_of + timedelta(days=days),
            status=RetentionCheckpointStatus.PENDING,
            model_version=knowledge_state.model_version,
        )
        db.add(checkpoint)
        db.flush()

        db.add(
            Hypothesis(
                tenant_id=tenant_id,
                student_user_id=student_user_id,
                skill_id=skill_id,
                hypothesis_type=HypothesisType.RETENTION_PREDICTION,
                retention_checkpoint_id=checkpoint.id,
                predicted_mastery_probability=knowledge_state.mastery_probability,
                predicted_confidence_label=knowledge_state.confidence_label,
                predicted_at=as_of,
            )
        )
        checkpoints.append(checkpoint)

    return checkpoints


def list_due_checkpoints(db: Session, *, tenant_id: str, as_of: datetime | None = None) -> list[RetentionCheckpoint]:
    as_of = as_of or datetime.now(timezone.utc)
    return (
        db.query(RetentionCheckpoint)
        .filter(
            RetentionCheckpoint.tenant_id == tenant_id,
            RetentionCheckpoint.status == RetentionCheckpointStatus.PENDING,
            RetentionCheckpoint.scheduled_for <= as_of,
        )
        .order_by(RetentionCheckpoint.scheduled_for.asc())
        .all()
    )


def list_checkpoints(db: Session, *, tenant_id: str, student_user_id: str, skill_id: str) -> list[RetentionCheckpoint]:
    return (
        db.query(RetentionCheckpoint)
        .filter(
            RetentionCheckpoint.tenant_id == tenant_id,
            RetentionCheckpoint.student_user_id == student_user_id,
            RetentionCheckpoint.skill_id == skill_id,
        )
        .order_by(RetentionCheckpoint.scheduled_for.desc())
        .all()
    )


def get_hypothesis_for_checkpoint(db: Session, *, checkpoint_id: str) -> Hypothesis | None:
    return db.query(Hypothesis).filter(Hypothesis.retention_checkpoint_id == checkpoint_id).first()


def _evaluate_verdict(
    *, predicted_confidence_label: ConfidenceLabel, predicted_mastery_probability: float, actual_is_correct: bool
) -> HypothesisVerdict:
    """ADR-014's verdict rule."""
    if predicted_confidence_label != ConfidenceLabel.HIGH_CONFIDENCE:
        return HypothesisVerdict.INCONCLUSIVE
    predicted_correct = predicted_mastery_probability > 0.5
    return HypothesisVerdict.SUPPORTED if predicted_correct == actual_is_correct else HypothesisVerdict.NOT_SUPPORTED


def complete_checkpoint(
    db: Session,
    *,
    tenant_id: str,
    checkpoint_id: str,
    question_id: str,
    learner_response: str,
    idempotency_key: str,
) -> RetentionCheckpoint:
    checkpoint = db.get(RetentionCheckpoint, checkpoint_id)
    if checkpoint is None or checkpoint.tenant_id != tenant_id:
        raise CheckpointNotFound()
    if checkpoint.status == RetentionCheckpointStatus.COMPLETED:
        raise CheckpointAlreadyCompleted()

    question = db.get(Question, question_id)
    if question is None or question.skill_id != checkpoint.skill_id:
        raise WrongSkillForCheckpoint()
    if question.correct_answer is None:
        raise OpenEndedQuestionNotSupported()

    attempt = assessment_service.submit_attempt(
        db,
        tenant_id=tenant_id,
        student_user_id=checkpoint.student_user_id,
        payload=SubmitAttemptRequest(
            question_id=question_id,
            assessment_type=AssessmentType.DELAYED_RETENTION,
            learner_response=learner_response,
            idempotency_key=idempotency_key,
        ),
    )

    as_of = datetime.now(timezone.utc)
    knowledge_state = knowledge_state_service.get_or_recompute_knowledge_state(
        db,
        tenant_id=tenant_id,
        student_user_id=checkpoint.student_user_id,
        skill_id=checkpoint.skill_id,
        facet_type=SkillFacetType.APPLICATION,
        as_of=as_of,
    )

    checkpoint.status = RetentionCheckpointStatus.COMPLETED
    checkpoint.delayed_attempt_id = attempt.id
    checkpoint.retention_estimate = knowledge_state.mastery_probability

    hypothesis = get_hypothesis_for_checkpoint(db, checkpoint_id=checkpoint.id)
    if hypothesis is not None and attempt.is_correct is not None:
        hypothesis.verdict = _evaluate_verdict(
            predicted_confidence_label=hypothesis.predicted_confidence_label,
            predicted_mastery_probability=hypothesis.predicted_mastery_probability,
            actual_is_correct=attempt.is_correct,
        )
        hypothesis.evaluated_at = as_of
        hypothesis.actual_is_correct = attempt.is_correct

    db.commit()
    db.refresh(checkpoint)
    return checkpoint
