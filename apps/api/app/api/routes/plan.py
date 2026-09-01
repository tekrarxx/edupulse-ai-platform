from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import Role, User
from app.schemas.plan import PlanOut, SwitchPlanRequest
from app.services import entitlement_service

router = APIRouter(prefix="/plans")

_admin_access = Depends(require_role(Role.TENANT_ADMIN, Role.SCHOOL_ADMIN, Role.SUPER_ADMIN))


@router.get("", response_model=list[PlanOut])
def list_plans(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[PlanOut]:
    """Any authenticated tenant member may see the available plans (no
    price field exists yet to make this sensitive, ADR-016) — only
    switching (below) is restricted to tenant staff."""
    return [PlanOut.model_validate(p) for p in entitlement_service.list_plans(db)]


@router.get("/tenant/current", response_model=PlanOut)
def get_tenant_current_plan(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> PlanOut:
    plan = entitlement_service.get_current_plan(db, tenant_id=current_user.tenant_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="plan_not_found")
    return PlanOut.model_validate(plan)


@router.put("/tenant", response_model=PlanOut, dependencies=[_admin_access])
def switch_tenant_plan(
    payload: SwitchPlanRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> PlanOut:
    """Self-service plan switching (ROADMAP.md P2, ADR-016's own trigger).
    Always the caller's own tenant (§51) — never a client-supplied
    tenant_id. Still no payment gate (§116) — see entitlement_service's
    module docstring for what this deliberately does and does not do."""
    try:
        plan = entitlement_service.switch_tenant_plan(
            db, tenant_id=current_user.tenant_id, actor_user_id=current_user.id, plan_slug=payload.plan_slug
        )
    except entitlement_service.PlanNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="plan_not_found")
    return PlanOut.model_validate(plan)
