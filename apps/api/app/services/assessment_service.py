"""Assessment/Observation/Evidence application service (§15).

The Observation -> Evidence boundary lives entirely in this module:
`evaluate_attempt` is the ONLY code path that creates Evidence, and it
always does so from an Observation it just wrote in the same call — there
is no way to reach Evidence without going through a raw fact first (§23).
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.assessment import Attempt, EvaluationMethod, Question
from app.models.curriculum import Skill
from app.models.evidence import Evidence, EvidenceDirectness, EvidencePolarity
from app.models.observation import Observation, ObservationEventType
from app.schemas.assessment import ObservationCreate, QuestionCreate, SubmitAttemptRequest


class AssessmentError(Exception):
    pass


class QuestionNotFound(AssessmentError):
    pass


class SkillNotFound(AssessmentError):
    pass


class AttemptNotFound(AssessmentError):
    pass


class AttemptAlreadyEvaluated(AssessmentError):
    pass


class SubjectNotFound(AssessmentError):
    pass


def create_question(db: Session, payload: QuestionCreate) -> Question:
    if db.get(Skill, payload.skill_id) is None:
        raise SkillNotFound()
    question = Question(
        skill_id=payload.skill_id,
        facet_type=payload.facet_type,
        prompt=payload.prompt,
        correct_answer=payload.correct_answer,
        difficulty=payload.difficulty,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def list_questions(db: Session) -> list[Question]:
    return db.query(Question).order_by(Question.created_at).all()


def get_question(db: Session, question_id: str) -> Question:
    question = db.get(Question, question_id)
    if question is None:
        raise QuestionNotFound()
    return question


def _record_observation(
    db: Session,
    *,
    tenant_id: str,
    actor_user_id: str,
    subject_type: str,
    subject_id: str,
    event_type: ObservationEventType,
    payload: dict,
    idempotency_key: str,
) -> Observation:
    existing = (
        db.query(Observation)
        .filter(Observation.tenant_id == tenant_id, Observation.idempotency_key == idempotency_key)
        .first()
    )
    if existing is not None:
        return existing

    observation = Observation(
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        subject_type=subject_type,
        subject_id=subject_id,
        event_type=event_type,
        payload=payload,
        idempotency_key=idempotency_key,
    )
    db.add(observation)
    db.flush()
    return observation


def submit_attempt(db: Session, *, tenant_id: str, student_user_id: str, payload: SubmitAttemptRequest) -> Attempt:
    existing = (
        db.query(Attempt)
        .filter(Attempt.tenant_id == tenant_id, Attempt.idempotency_key == payload.idempotency_key)
        .first()
    )
    if existing is not None:
        return existing  # §130: retried submission, not a new attempt

    question = db.get(Question, payload.question_id)
    if question is None:
        raise QuestionNotFound()

    attempt = Attempt(
        tenant_id=tenant_id,
        student_user_id=student_user_id,
        question_id=question.id,
        assessment_type=payload.assessment_type,
        question_content_version=question.content_version,
        learner_response=payload.learner_response,
        idempotency_key=payload.idempotency_key,
    )
    db.add(attempt)
    db.flush()

    _record_observation(
        db,
        tenant_id=tenant_id,
        actor_user_id=student_user_id,
        subject_type="attempt",
        subject_id=attempt.id,
        event_type=ObservationEventType.ANSWER_SUBMITTED,
        payload={"question_id": question.id, "response_length": len(payload.learner_response)},
        idempotency_key=f"{payload.idempotency_key}:submitted",
    )

    if question.correct_answer is not None:
        is_correct = payload.learner_response.strip().lower() == question.correct_answer.strip().lower()
        _apply_evaluation(
            db,
            attempt=attempt,
            question=question,
            is_correct=is_correct,
            evaluation_method=EvaluationMethod.AUTOMATIC,
            evaluation_confidence=1.0,
        )

    db.commit()
    db.refresh(attempt)
    return attempt


def evaluate_attempt(
    db: Session, *, tenant_id: str, attempt_id: str, is_correct: bool, evaluation_confidence: float
) -> Attempt:
    attempt = db.get(Attempt, attempt_id)
    if attempt is None or attempt.tenant_id != tenant_id:
        raise AttemptNotFound()
    if attempt.evaluated_at is not None:
        raise AttemptAlreadyEvaluated()

    question = db.get(Question, attempt.question_id)
    _apply_evaluation(
        db,
        attempt=attempt,
        question=question,
        is_correct=is_correct,
        evaluation_method=EvaluationMethod.MANUAL,
        evaluation_confidence=evaluation_confidence,
    )
    db.commit()
    db.refresh(attempt)
    return attempt


def _apply_evaluation(
    db: Session,
    *,
    attempt: Attempt,
    question: Question,
    is_correct: bool,
    evaluation_method: EvaluationMethod,
    evaluation_confidence: float,
) -> None:
    now = datetime.now(timezone.utc)
    attempt.is_correct = is_correct
    attempt.evaluation_method = evaluation_method
    attempt.evaluation_confidence = evaluation_confidence
    attempt.evaluated_at = now

    observation = _record_observation(
        db,
        tenant_id=attempt.tenant_id,
        actor_user_id=attempt.student_user_id,
        subject_type="attempt",
        subject_id=attempt.id,
        event_type=ObservationEventType.ANSWER_CORRECT if is_correct else ObservationEventType.ANSWER_INCORRECT,
        payload={"evaluation_method": evaluation_method.value},
        idempotency_key=f"{attempt.idempotency_key}:evaluated",
    )

    db.add(
        Evidence(
            tenant_id=attempt.tenant_id,
            student_user_id=attempt.student_user_id,
            observation_id=observation.id,
            skill_id=question.skill_id,
            facet_type=question.facet_type,
            polarity=EvidencePolarity.POSITIVE if is_correct else EvidencePolarity.NEGATIVE,
            directness=EvidenceDirectness.DIRECT,
            # Manual grading carries a small reliability discount relative to
            # exact-match automatic grading, which cannot be subjectively
            # wrong about whether the strings matched (§27).
            reliability=1.0 if evaluation_method == EvaluationMethod.AUTOMATIC else 0.8,
            task_validity=1.0,
            transfer_relevance=question.facet_type.value == "transfer",
            evaluation_confidence=evaluation_confidence,
        )
    )


def record_observation(
    db: Session, *, tenant_id: str, actor_user_id: str, payload: ObservationCreate
) -> Observation:
    existing = (
        db.query(Observation)
        .filter(Observation.tenant_id == tenant_id, Observation.idempotency_key == payload.idempotency_key)
        .first()
    )
    if existing is not None:
        return existing

    if payload.subject_type == "attempt":
        attempt = db.get(Attempt, payload.subject_id)
        if attempt is None or attempt.tenant_id != tenant_id:
            raise SubjectNotFound()

    observation = _record_observation(
        db,
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        subject_type=payload.subject_type,
        subject_id=payload.subject_id,
        event_type=payload.event_type,
        payload=payload.payload,
        idempotency_key=payload.idempotency_key,
    )
    db.commit()
    db.refresh(observation)
    return observation


def query_evidence(db: Session, *, tenant_id: str, student_user_id: str | None) -> list[Evidence]:
    query = db.query(Evidence).filter(Evidence.tenant_id == tenant_id)
    if student_user_id is not None:
        query = query.filter(Evidence.student_user_id == student_user_id)
    return query.order_by(Evidence.created_at.desc()).all()
