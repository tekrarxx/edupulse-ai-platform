from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.decision import Decision
from app.models.relationship import ParentStudentLink
from app.models.tenant import Tenant
from app.models.user import Role, User
from app.schemas.decision import DecisionOut
from app.services import decision_engine_service

router = APIRouter(prefix="/decisions")

_TENANT_STAFF_ROLES = {Role.TEACHER, Role.SCHOOL_ADMIN, Role.TENANT_ADMIN, Role.SUPER_ADMIN}


def _resolve_target_student_id(*, current_user: User, student_id: str | None, db: Session) -> str:
    """Same §51/§81 enforcement pattern as GET /knowledge-state: tenant_id
    always comes from the token, role narrows which learner is visible, and
    staff must name a student explicitly (no tenant-wide scan here either)."""
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


def _resolve_is_shadow(*, current_user: User, mode: Literal["live", "shadow"] | None, db: Session) -> bool:
    """ADR-013 Shadow Mode: the tenant flag is a hard floor a per-request
    `mode` cannot lift. Only staff may pass `mode` at all — a student or
    parent has no way to request shadow for themselves."""
    if mode is not None and current_user.role not in _TENANT_STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="mode_requires_staff_role")

    tenant = db.get(Tenant, current_user.tenant_id)
    tenant_default = tenant.pde_shadow_mode_default if tenant is not None else False
    return tenant_default or mode == "shadow"


@router.post("/next-action", response_model=DecisionOut, status_code=status.HTTP_201_CREATED)
def request_next_action(
    skill_id: str = Query(...),
    student_id: str | None = Query(default=None),
    mode: Literal["live", "shadow"] | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DecisionOut:
    target_student_id = _resolve_target_student_id(current_user=current_user, student_id=student_id, db=db)
    is_shadow = _resolve_is_shadow(current_user=current_user, mode=mode, db=db)

    try:
        decision = decision_engine_service.generate_decision(
            db,
            tenant_id=current_user.tenant_id,
            student_user_id=target_student_id,
            skill_id=skill_id,
            is_shadow=is_shadow,
        )
    except decision_engine_service.SkillNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="skill_not_found")

    return DecisionOut.model_validate(decision)


def _get_owned_decision(db: Session, *, tenant_id: str, decision_id: str) -> Decision:
    decision = db.get(Decision, decision_id)
    if decision is None or decision.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="decision_not_found")
    return decision


@router.get("/{decision_id}", response_model=DecisionOut)
def get_decision(
    decision_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> DecisionOut:
    decision = _get_owned_decision(db, tenant_id=current_user.tenant_id, decision_id=decision_id)
    # Reuses the same visibility rule as listing: a caller may only view a
    # decision for a student they are already permitted to view (§51, §81).
    _resolve_target_student_id(current_user=current_user, student_id=decision.student_user_id, db=db)
    return DecisionOut.model_validate(decision)


@router.get("", response_model=list[DecisionOut])
def list_decisions(
    skill_id: str = Query(...),
    student_id: str | None = Query(default=None),
    include_shadow: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DecisionOut]:
    """§38: shadow decisions are excluded by default — only a staff caller
    may opt into seeing them, and even then only for a student they can
    already view."""
    target_student_id = _resolve_target_student_id(current_user=current_user, student_id=student_id, db=db)

    if include_shadow and current_user.role not in _TENANT_STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="include_shadow_requires_staff_role")

    query = db.query(Decision).filter(
        Decision.tenant_id == current_user.tenant_id,
        Decision.student_user_id == target_student_id,
        Decision.skill_id == skill_id,
    )
    if not include_shadow:
        query = query.filter(Decision.is_shadow.is_(False))

    decisions = query.order_by(Decision.created_at.desc()).offset(offset).limit(limit).all()
    return [DecisionOut.model_validate(d) for d in decisions]
