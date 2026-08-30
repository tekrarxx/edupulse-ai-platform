from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import enforce_rate_limit, get_current_user, require_role
from app.db.session import get_db
from app.models.relationship import ParentStudentLink
from app.models.user import Role, User
from app.schemas.assessment import (
    AttemptOut,
    ClassifyFailureModeRequest,
    EvaluateAttemptRequest,
    EvidenceOut,
    ObservationCreate,
    ObservationOut,
    QuestionCreate,
    QuestionOut,
    QuestionPublicOut,
    SubmitAttemptRequest,
)
from app.services import assessment_service

router = APIRouter(prefix="/assessment")

_read_access = Depends(get_current_user)
_write_access = Depends(require_role(Role.SUPER_ADMIN))
_grader_access = Depends(require_role(Role.TEACHER, Role.SCHOOL_ADMIN, Role.TENANT_ADMIN, Role.SUPER_ADMIN))

_TENANT_STAFF_ROLES = {Role.TEACHER, Role.SCHOOL_ADMIN, Role.TENANT_ADMIN, Role.SUPER_ADMIN}


@router.post("/questions", response_model=QuestionOut, status_code=status.HTTP_201_CREATED, dependencies=[_write_access])
def create_question(payload: QuestionCreate, db: Session = Depends(get_db)) -> QuestionOut:
    try:
        question = assessment_service.create_question(db, payload)
    except assessment_service.SkillNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="skill_not_found")
    return QuestionOut.model_validate(question)


@router.get("/questions", response_model=list[QuestionPublicOut], dependencies=[_read_access])
def list_questions(db: Session = Depends(get_db)) -> list[QuestionPublicOut]:
    return [QuestionPublicOut.model_validate(q) for q in assessment_service.list_questions(db)]


@router.get("/questions/{question_id}", response_model=QuestionPublicOut, dependencies=[_read_access])
def get_question(question_id: str, db: Session = Depends(get_db)) -> QuestionPublicOut:
    try:
        question = assessment_service.get_question(db, question_id)
    except assessment_service.QuestionNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="question_not_found")
    return QuestionPublicOut.model_validate(question)


@router.post("/attempts", response_model=AttemptOut, status_code=status.HTTP_201_CREATED)
def submit_attempt(
    request: Request,
    payload: SubmitAttemptRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttemptOut:
    # §78: bounds how fast one account can write attempts/observations —
    # generous enough for genuine retrieval practice, not for a scripted flood.
    enforce_rate_limit(request, key_prefix="assessment_attempts", limit=120, window_seconds=60, identity=current_user.id)
    try:
        attempt = assessment_service.submit_attempt(
            db, tenant_id=current_user.tenant_id, student_user_id=current_user.id, payload=payload
        )
    except assessment_service.QuestionNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="question_not_found")
    return AttemptOut.model_validate(attempt)


@router.post("/attempts/{attempt_id}/evaluate", response_model=AttemptOut, dependencies=[_grader_access])
def evaluate_attempt(
    attempt_id: str,
    payload: EvaluateAttemptRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttemptOut:
    try:
        attempt = assessment_service.evaluate_attempt(
            db,
            tenant_id=current_user.tenant_id,
            attempt_id=attempt_id,
            is_correct=payload.is_correct,
            evaluation_confidence=payload.evaluation_confidence,
        )
    except assessment_service.AttemptNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="attempt_not_found")
    except assessment_service.AttemptAlreadyEvaluated:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="attempt_already_evaluated")
    return AttemptOut.model_validate(attempt)


@router.post("/observations", response_model=ObservationOut, status_code=status.HTTP_201_CREATED)
def record_observation(
    payload: ObservationCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ObservationOut:
    try:
        observation = assessment_service.record_observation(
            db, tenant_id=current_user.tenant_id, actor_user_id=current_user.id, payload=payload
        )
    except assessment_service.SubjectNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="subject_not_found")
    return ObservationOut.model_validate(observation)


@router.get("/evidence", response_model=list[EvidenceOut])
def query_evidence(
    student_id: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EvidenceOut]:
    """§51 enforcement point: tenant_id always comes from the token. Role
    further narrows *which learner's* evidence is visible — a STUDENT never
    sees anyone else's, a PARENT only their linked children's (§81)."""
    if current_user.role == Role.STUDENT:
        target_student_id = current_user.id
    elif current_user.role == Role.PARENT:
        if student_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="student_id_required")
        link = (
            db.query(ParentStudentLink)
            .filter(
                ParentStudentLink.tenant_id == current_user.tenant_id,
                ParentStudentLink.parent_user_id == current_user.id,
                ParentStudentLink.student_user_id == student_id,
            )
            .first()
        )
        if link is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not_a_linked_student")
        target_student_id = student_id
    elif current_user.role in _TENANT_STAFF_ROLES:
        target_student_id = student_id  # None = every student in the tenant
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient_role")

    evidence = assessment_service.query_evidence(db, tenant_id=current_user.tenant_id, student_user_id=target_student_id)
    return [EvidenceOut.model_validate(e) for e in evidence]


@router.post("/evidence/{evidence_id}/failure-mode", response_model=EvidenceOut, dependencies=[_grader_access])
def classify_failure_mode(
    evidence_id: str,
    payload: ClassifyFailureModeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvidenceOut:
    try:
        evidence = assessment_service.classify_failure_mode(
            db, tenant_id=current_user.tenant_id, evidence_id=evidence_id, failure_mode=payload.failure_mode
        )
    except assessment_service.StructuralFailureModeCannotBeManuallyClassified:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="structural_failure_mode_not_manually_classifiable")
    except assessment_service.EvidenceNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="evidence_not_found")
    except assessment_service.FailureModeAlreadyClassified:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="failure_mode_already_classified")
    return EvidenceOut.model_validate(evidence)
