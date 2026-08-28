from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.relationship import ParentStudentLink
from app.models.user import Role, User
from app.schemas.dashboard import StudentDashboardOut
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard")

_TENANT_STAFF_ROLES = {Role.TEACHER, Role.SCHOOL_ADMIN, Role.TENANT_ADMIN, Role.SUPER_ADMIN}


def _resolve_target_student_id(*, current_user: User, student_id: str | None, db: Session) -> str:
    """Same §51/§81 pattern as /knowledge-state, /decisions, /retention."""
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


@router.get("/student", response_model=StudentDashboardOut)
def get_student_dashboard(
    student_id: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StudentDashboardOut:
    target_student_id = _resolve_target_student_id(current_user=current_user, student_id=student_id, db=db)
    dashboard = dashboard_service.get_student_dashboard(db, tenant_id=current_user.tenant_id, student_user_id=target_student_id)
    return StudentDashboardOut(
        student_user_id=dashboard.student_user_id,
        skills=[
            {
                "skill_id": s.skill_id,
                "skill_name": s.skill_name,
                "mastery_label": s.mastery_label,
                "is_weak": s.is_weak,
                "is_strong": s.is_strong,
                "next_action_label": s.next_action_label,
                "pending_retention_checkpoints": s.pending_retention_checkpoints,
            }
            for s in dashboard.skills
        ],
        weak_skill_count=dashboard.weak_skill_count,
        strong_skill_count=dashboard.strong_skill_count,
        upcoming_retention_count=dashboard.upcoming_retention_count,
    )
