from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.curriculum import SkillFacetType
from app.models.relationship import ParentStudentLink
from app.models.user import Role, User
from app.schemas.knowledge_state import KnowledgeStateOut
from app.services import knowledge_state_service

router = APIRouter(prefix="/knowledge-state")

_TENANT_STAFF_ROLES = {Role.TEACHER, Role.SCHOOL_ADMIN, Role.TENANT_ADMIN, Role.SUPER_ADMIN}


def _resolve_target_student_id(
    *, current_user: User, student_id: str | None, db: Session
) -> str:
    """§51 enforcement point, mirroring GET /assessment/evidence: tenant_id
    always comes from the token; role further narrows which learner's state
    is visible. A STUDENT never sees anyone else's; a PARENT only their
    linked children's (§81); staff must name a student explicitly — unlike
    the evidence endpoint, there is no "every student in the tenant" mode
    here, since a single skill's state for the whole tenant has no obvious
    caller today and would invite an accidental full-tenant scan."""
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


@router.get("", response_model=list[KnowledgeStateOut])
def get_knowledge_state(
    skill_id: str = Query(...),
    student_id: str | None = Query(default=None),
    facet_type: SkillFacetType | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[KnowledgeStateOut]:
    """Recomputes from the Evidence log at request time (ADR-012) — the
    response reflects `as_of = now`, not a stale cached row. If `facet_type`
    is omitted, all five facets (§28) are returned, each independently."""
    target_student_id = _resolve_target_student_id(current_user=current_user, student_id=student_id, db=db)

    try:
        if facet_type is not None:
            states = [
                knowledge_state_service.get_or_recompute_knowledge_state(
                    db,
                    tenant_id=current_user.tenant_id,
                    student_user_id=target_student_id,
                    skill_id=skill_id,
                    facet_type=facet_type,
                )
            ]
        else:
            states = knowledge_state_service.get_knowledge_states_for_skill(
                db,
                tenant_id=current_user.tenant_id,
                student_user_id=target_student_id,
                skill_id=skill_id,
            )
    except knowledge_state_service.SkillNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="skill_not_found")

    return [KnowledgeStateOut.model_validate(state) for state in states]
