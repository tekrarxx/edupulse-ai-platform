"""Plan/entitlement lookups and enforcement (§60). Deliberately the only
place in the codebase that reads `Tenant.plan_id` or `Entitlement` — every
other service asks this module a yes/no question, never queries the plan
tables directly, so the entitlement model can grow without every caller
needing to change (§60's whole point).

Prometheus/PDE code must never import this module (§95) — it is consumed
by non-PDE services only, currently just app/services/explanation_service.py.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.ai_usage import AIUsageRecord
from app.models.plan import Entitlement, EntitlementKey, Plan
from app.models.tenant import Tenant
from app.models.user import User
from app.services.audit_service import record_audit as _record_audit

_DEFAULT_PLAN_SLUG = "free"


class EntitlementError(Exception):
    pass


class QuotaExceeded(EntitlementError):
    pass


class PlanNotFound(EntitlementError):
    pass


def _resolve_plan_id(db: Session, *, tenant_id: str) -> str | None:
    tenant = db.get(Tenant, tenant_id)
    if tenant is not None and tenant.plan_id is not None:
        return tenant.plan_id
    # A tenant with no plan_id (should not happen for any tenant created
    # after migration 0010, but defensive rather than assumed — §107) is
    # treated as the default free plan, never as unlimited.
    default_plan = db.query(Plan).filter(Plan.slug == _DEFAULT_PLAN_SLUG).first()
    return default_plan.id if default_plan is not None else None


def get_entitlement_value(db: Session, *, tenant_id: str, key: EntitlementKey) -> int | None:
    """None means unlimited — either no `Entitlement` row exists for this
    plan+key, or the row itself has `value=None` (§60: absence of a
    configured limit is never treated as a fabricated restriction, §105)."""
    plan_id = _resolve_plan_id(db, tenant_id=tenant_id)
    if plan_id is None:
        return None
    entitlement = db.query(Entitlement).filter(Entitlement.plan_id == plan_id, Entitlement.key == key).first()
    return entitlement.value if entitlement is not None else None


def _count_ai_explanations_this_month(db: Session, *, tenant_id: str) -> int:
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return (
        db.query(AIUsageRecord)
        .filter(AIUsageRecord.tenant_id == tenant_id, AIUsageRecord.created_at >= month_start)
        .count()
    )


def get_ai_explanation_usage(db: Session, *, tenant_id: str) -> tuple[int, int | None]:
    """(used_this_month, monthly_limit) — `limit=None` means unlimited.
    Shared by the enforcement check below and the admin dashboard's own
    read-only display (app/services/dashboard_service.py), so both always
    agree on what "usage" and "limit" mean."""
    limit = get_entitlement_value(db, tenant_id=tenant_id, key=EntitlementKey.AI_EXPLANATIONS_MONTHLY_LIMIT)
    used = _count_ai_explanations_this_month(db, tenant_id=tenant_id)
    return used, limit


def enforce_ai_explanation_quota(db: Session, *, tenant_id: str) -> None:
    """Checked before generating (explanation_service.py) so an over-quota
    tenant never pays the cost of a real LLM call for a request that will
    be rejected anyway (§48 AI cost control)."""
    used, limit = get_ai_explanation_usage(db, tenant_id=tenant_id)
    if limit is not None and used >= limit:
        raise QuotaExceeded()


def _count_tenant_users(db: Session, *, tenant_id: str) -> int:
    return db.query(User).filter(User.tenant_id == tenant_id).count()


def get_tenant_user_seat_usage(db: Session, *, tenant_id: str) -> tuple[int, int | None]:
    """(used_seats, seat_limit) — mirrors get_ai_explanation_usage's shape so
    the admin dashboard can display both the same way. `limit=None` means
    unlimited (§60)."""
    limit = get_entitlement_value(db, tenant_id=tenant_id, key=EntitlementKey.MAX_TENANT_USERS)
    used = _count_tenant_users(db, tenant_id=tenant_id)
    return used, limit


def enforce_tenant_user_seat_limit(db: Session, *, tenant_id: str) -> None:
    """Checked before admin-initiated enrollment (auth_service.py) so a
    tenant at its plan's seat limit cannot create another account until it
    upgrades — same "check before the write, not after" discipline as
    enforce_ai_explanation_quota (§48/§60)."""
    used, limit = get_tenant_user_seat_usage(db, tenant_id=tenant_id)
    if limit is not None and used >= limit:
        raise QuotaExceeded()


# --- Self-service plan switching (ROADMAP.md P2, ADR-016's own trigger:
# "worth doing once there is a second real tier a tenant would plausibly
# self-upgrade into" — the "school" plan, scripts/seed_school_plan.py,
# is that second tier). Still no money changes hands (§116, ADR-016's
# "What Is Explicitly Not Built") — this removes the "needs an operator to
# run a script" friction, nothing more. A real payment gate is separate,
# future work (ADR-016's second falsifiability trigger). ---


def list_plans(db: Session) -> list[Plan]:
    return db.query(Plan).order_by(Plan.name).all()


def get_current_plan(db: Session, *, tenant_id: str) -> Plan | None:
    plan_id = _resolve_plan_id(db, tenant_id=tenant_id)
    return db.get(Plan, plan_id) if plan_id is not None else None


def switch_tenant_plan(db: Session, *, tenant_id: str, actor_user_id: str, plan_slug: str) -> Plan:
    """Self-service (§60/§63): any TENANT_ADMIN/SCHOOL_ADMIN/SUPER_ADMIN of
    the tenant may switch to any existing Plan, in either direction — there
    is no payment gate to enforce (§116), so this is honestly symmetric
    rather than fabricating an upgrade-only restriction nothing backs."""
    plan = db.query(Plan).filter(Plan.slug == plan_slug).first()
    if plan is None:
        raise PlanNotFound()

    tenant = db.get(Tenant, tenant_id)
    tenant.plan_id = plan.id
    _record_audit(db, tenant_id=tenant_id, actor_user_id=actor_user_id, action="tenant.plan_changed", target_type="tenant", target_id=tenant_id)
    db.commit()
    db.refresh(plan)
    return plan
