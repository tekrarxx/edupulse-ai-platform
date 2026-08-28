from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.relationship import ParentStudentLink
from app.models.retention import RetentionCheckpoint
from app.models.user import Role, User
from app.schemas.retention import CompleteCheckpointRequest, HypothesisOut, RetentionCheckpointOut
from app.services import retention_service

router = APIRouter(prefix="/retention")

_TENANT_STAFF_ROLES = {Role.TEACHER, Role.SCHOOL_ADMIN, Role.TENANT_ADMIN, Role.SUPER_ADMIN}
_grader_access = Depends(require_role(Role.TEACHER, Role.SCHOOL_ADMIN, Role.TENANT_ADMIN, Role.SUPER_ADMIN))


def _resolve_target_student_id(*, current_user: User, student_id: str | None, db: Session) -> str:
    """Same §51/§81 pattern used by /knowledge-state and /decisions."""
    if current_user.role == Role.STUDENT:
        if student_id is not None and student_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient_role")
        return current_user.id
    if current_user.role == Role.PARENT:
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
        return student_id
    if current_user.role in _TENANT_STAFF_ROLES:
        if student_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="student_id_required")
        return student_id
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient_role")


def _to_out(db: Session, checkpoint: RetentionCheckpoint) -> RetentionCheckpointOut:
    hypothesis = retention_service.get_hypothesis_for_checkpoint(db, checkpoint_id=checkpoint.id)
    return RetentionCheckpointOut(
        id=checkpoint.id,
        student_user_id=checkpoint.student_user_id,
        skill_id=checkpoint.skill_id,
        checkpoint_days=checkpoint.checkpoint_days,
        origin_evidence_id=checkpoint.origin_evidence_id,
        scheduled_for=checkpoint.scheduled_for,
        status=checkpoint.status,
        delayed_attempt_id=checkpoint.delayed_attempt_id,
        retention_estimate=checkpoint.retention_estimate,
        model_version=checkpoint.model_version,
        created_at=checkpoint.created_at,
        hypothesis=HypothesisOut.model_validate(hypothesis) if hypothesis is not None else None,
    )


@router.get("/checkpoints/due", response_model=list[RetentionCheckpointOut], dependencies=[_grader_access])
def get_due_checkpoints(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[RetentionCheckpointOut]:
    """What a future scheduler (n8n/cron — not yet wired into this repo,
    see ADR-014) would poll. Real application logic; the caller is external."""
    checkpoints = retention_service.list_due_checkpoints(db, tenant_id=current_user.tenant_id)
    return [_to_out(db, c) for c in checkpoints]


@router.get("/checkpoints", response_model=list[RetentionCheckpointOut])
def list_checkpoints(
    skill_id: str = Query(...),
    student_id: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RetentionCheckpointOut]:
    target_student_id = _resolve_target_student_id(current_user=current_user, student_id=student_id, db=db)
    checkpoints = retention_service.list_checkpoints(
        db, tenant_id=current_user.tenant_id, student_user_id=target_student_id, skill_id=skill_id
    )
    return [_to_out(db, c) for c in checkpoints]


@router.post("/checkpoints/{checkpoint_id}/complete", response_model=RetentionCheckpointOut, dependencies=[_grader_access])
def complete_checkpoint(
    checkpoint_id: str,
    payload: CompleteCheckpointRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RetentionCheckpointOut:
    try:
        checkpoint = retention_service.complete_checkpoint(
            db,
            tenant_id=current_user.tenant_id,
            checkpoint_id=checkpoint_id,
            question_id=payload.question_id,
            learner_response=payload.learner_response,
            idempotency_key=payload.idempotency_key,
        )
    except retention_service.CheckpointNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="checkpoint_not_found")
    except retention_service.CheckpointAlreadyCompleted:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="checkpoint_already_completed")
    except retention_service.WrongSkillForCheckpoint:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="question_does_not_target_checkpoint_skill")
    except retention_service.OpenEndedQuestionNotSupported:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="open_ended_question_not_supported")
    return _to_out(db, checkpoint)
