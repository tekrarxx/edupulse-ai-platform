from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.relationship import ParentStudentLink
from app.models.user import Role, User
from app.schemas.dashboard import AdminDashboardOut, StudentDashboardOut, StudentSummaryOut, TeacherDashboardOut
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


_teacher_access = Depends(require_role(Role.TEACHER))


@router.get("/teacher", response_model=TeacherDashboardOut, dependencies=[_teacher_access])
def get_teacher_dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> TeacherDashboardOut:
    """§76. Scoped to the requesting teacher's own students only (via
    TeacherStudentLink) — not every student in the tenant (§80). A
    school/tenant-wide view is a separate Admin Dashboard endpoint, not
    this one."""
    dashboard = dashboard_service.get_teacher_dashboard(db, tenant_id=current_user.tenant_id, teacher_user_id=current_user.id)
    return TeacherDashboardOut(
        students=[
            StudentSummaryOut(
                student_user_id=s.student_user_id,
                student_name=s.student_name,
                needs_attention=s.needs_attention,
                attention_reasons=s.attention_reasons,
                weak_skill_names=s.weak_skill_names,
                improving_skill_names=s.improving_skill_names,
                forgetting_skill_names=s.forgetting_skill_names,
                misconception_skill_names=s.misconception_skill_names,
                next_action_label=s.next_action_label,
            )
            for s in dashboard.students
        ],
        students_needing_attention_count=dashboard.students_needing_attention_count,
    )


_admin_access = Depends(require_role(Role.SCHOOL_ADMIN, Role.TENANT_ADMIN, Role.SUPER_ADMIN))


@router.get("/admin", response_model=AdminDashboardOut, dependencies=[_admin_access])
def get_admin_dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AdminDashboardOut:
    """§77. Tenant-wide aggregate view for school/tenant admins — counts
    only, never per-student names (§80)."""
    dashboard = dashboard_service.get_admin_dashboard(db, tenant_id=current_user.tenant_id)
    return AdminDashboardOut(
        tenant_id=dashboard.tenant_id,
        active_student_count=dashboard.active_student_count,
        active_teacher_count=dashboard.active_teacher_count,
        students_needing_attention_count=dashboard.students_needing_attention_count,
        weak_skill_student_count=dashboard.weak_skill_student_count,
        forgetting_student_count=dashboard.forgetting_student_count,
        misconception_student_count=dashboard.misconception_student_count,
        escalated_student_count=dashboard.escalated_student_count,
        retention_pending_count=dashboard.retention_pending_count,
        retention_supported_count=dashboard.retention_supported_count,
        retention_not_supported_count=dashboard.retention_not_supported_count,
        retention_inconclusive_count=dashboard.retention_inconclusive_count,
        decisions_total_count=dashboard.decisions_total_count,
        decisions_allowed_count=dashboard.decisions_allowed_count,
        decisions_escalated_count=dashboard.decisions_escalated_count,
        decisions_rejected_count=dashboard.decisions_rejected_count,
        ai_requests_total_count=dashboard.ai_requests_total_count,
        ai_requests_success_count=dashboard.ai_requests_success_count,
        ai_requests_failed_count=dashboard.ai_requests_failed_count,
    )
