"""§60: Plan -> Entitlement -> Tenant -> feature-access lookups
(app/services/entitlement_service.py). Uses the real `db` fixture (Postgres
or SQLite, per tests/conftest.py) since these functions are DB-facing, not
pure computation.
"""
import uuid

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.ai_usage import AIUsageCapability, AIUsageRecord
from app.models.plan import Entitlement, EntitlementKey, Plan
from app.models.tenant import Tenant, TenantType
from app.models.user import Role, User
from app.services import entitlement_service


def _make_tenant(db: Session, *, plan_id: str | None = None) -> Tenant:
    tenant = Tenant(name=f"Tenant {uuid.uuid4().hex[:8]}", tenant_type=TenantType.INDIVIDUAL, plan_id=plan_id)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def _make_user(db: Session, *, tenant: Tenant) -> User:
    user = User(
        tenant_id=tenant.id,
        email=f"{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("irrelevant-for-this-test"),
        display_name="Test User",
        role=Role.STUDENT,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_get_entitlement_value_returns_none_when_no_entitlement_row_exists(db: Session) -> None:
    plan = Plan(slug=f"bare-{uuid.uuid4().hex[:8]}", name="Bare Plan")
    db.add(plan)
    db.commit()
    tenant = _make_tenant(db, plan_id=plan.id)

    value = entitlement_service.get_entitlement_value(db, tenant_id=tenant.id, key=EntitlementKey.AI_EXPLANATIONS_MONTHLY_LIMIT)
    assert value is None


def test_get_entitlement_value_returns_the_configured_limit(db: Session) -> None:
    plan = Plan(slug=f"limited-{uuid.uuid4().hex[:8]}", name="Limited Plan")
    db.add(plan)
    db.flush()
    db.add(Entitlement(plan_id=plan.id, key=EntitlementKey.AI_EXPLANATIONS_MONTHLY_LIMIT, value=5))
    db.commit()
    tenant = _make_tenant(db, plan_id=plan.id)

    value = entitlement_service.get_entitlement_value(db, tenant_id=tenant.id, key=EntitlementKey.AI_EXPLANATIONS_MONTHLY_LIMIT)
    assert value == 5


def test_tenant_with_no_plan_id_falls_back_to_the_free_plan(db: Session) -> None:
    """§107: never treated as unlimited — the free plan's real limit applies."""
    tenant = _make_tenant(db, plan_id=None)

    value = entitlement_service.get_entitlement_value(db, tenant_id=tenant.id, key=EntitlementKey.AI_EXPLANATIONS_MONTHLY_LIMIT)
    assert value == 10  # migration 0010's seeded free-plan limit


def test_enforce_ai_explanation_quota_allows_under_the_limit(db: Session) -> None:
    plan = Plan(slug=f"small-{uuid.uuid4().hex[:8]}", name="Small Plan")
    db.add(plan)
    db.flush()
    db.add(Entitlement(plan_id=plan.id, key=EntitlementKey.AI_EXPLANATIONS_MONTHLY_LIMIT, value=2))
    db.commit()
    tenant = _make_tenant(db, plan_id=plan.id)

    entitlement_service.enforce_ai_explanation_quota(db, tenant_id=tenant.id)  # 0 used, 2 allowed -> no raise


def test_enforce_ai_explanation_quota_raises_once_the_limit_is_reached(db: Session) -> None:
    plan = Plan(slug=f"small2-{uuid.uuid4().hex[:8]}", name="Small Plan 2")
    db.add(plan)
    db.flush()
    db.add(Entitlement(plan_id=plan.id, key=EntitlementKey.AI_EXPLANATIONS_MONTHLY_LIMIT, value=1))
    db.commit()
    tenant = _make_tenant(db, plan_id=plan.id)
    user = _make_user(db, tenant=tenant)
    db.add(
        AIUsageRecord(
            tenant_id=tenant.id,
            actor_user_id=user.id,
            provider="fake",
            model="fake-model",
            capability=AIUsageCapability.SKILL_EXPLANATION,
            prompt_name="skill_explanation",
            prompt_version="v1",
            latency_ms=1,
            success=True,
        )
    )
    db.commit()

    try:
        entitlement_service.enforce_ai_explanation_quota(db, tenant_id=tenant.id)
        assert False, "expected QuotaExceeded"
    except entitlement_service.QuotaExceeded:
        pass


def test_enforce_ai_explanation_quota_never_raises_when_unlimited(db: Session) -> None:
    plan = Plan(slug=f"unlimited-{uuid.uuid4().hex[:8]}", name="Unlimited Plan")
    db.add(plan)
    db.commit()
    tenant = _make_tenant(db, plan_id=plan.id)

    entitlement_service.enforce_ai_explanation_quota(db, tenant_id=tenant.id)  # no Entitlement row at all -> no raise


# --- max_tenant_users seat limit (Roadmap Stage E, ADR-016 second gated feature) ---


def test_get_tenant_user_seat_usage_falls_back_to_the_free_plan(db: Session) -> None:
    tenant = _make_tenant(db, plan_id=None)
    _make_user(db, tenant=tenant)

    used, limit = entitlement_service.get_tenant_user_seat_usage(db, tenant_id=tenant.id)
    assert used == 1
    assert limit == 5  # migration 0012's seeded free-plan seat limit


def test_enforce_tenant_user_seat_limit_allows_under_the_limit(db: Session) -> None:
    plan = Plan(slug=f"seats-{uuid.uuid4().hex[:8]}", name="Small Seats Plan")
    db.add(plan)
    db.flush()
    db.add(Entitlement(plan_id=plan.id, key=EntitlementKey.MAX_TENANT_USERS, value=2))
    db.commit()
    tenant = _make_tenant(db, plan_id=plan.id)
    _make_user(db, tenant=tenant)  # 1 used, 2 allowed

    entitlement_service.enforce_tenant_user_seat_limit(db, tenant_id=tenant.id)  # no raise


def test_enforce_tenant_user_seat_limit_raises_once_the_limit_is_reached(db: Session) -> None:
    plan = Plan(slug=f"seats2-{uuid.uuid4().hex[:8]}", name="Small Seats Plan 2")
    db.add(plan)
    db.flush()
    db.add(Entitlement(plan_id=plan.id, key=EntitlementKey.MAX_TENANT_USERS, value=1))
    db.commit()
    tenant = _make_tenant(db, plan_id=plan.id)
    _make_user(db, tenant=tenant)  # 1 used, 1 allowed -> at the limit

    try:
        entitlement_service.enforce_tenant_user_seat_limit(db, tenant_id=tenant.id)
        assert False, "expected QuotaExceeded"
    except entitlement_service.QuotaExceeded:
        pass


def test_enforce_tenant_user_seat_limit_never_raises_when_unlimited(db: Session) -> None:
    plan = Plan(slug=f"unlimited-seats-{uuid.uuid4().hex[:8]}", name="Unlimited Seats Plan")
    db.add(plan)
    db.commit()
    tenant = _make_tenant(db, plan_id=plan.id)
    for _ in range(10):
        _make_user(db, tenant=tenant)

    entitlement_service.enforce_tenant_user_seat_limit(db, tenant_id=tenant.id)  # no Entitlement row at all -> no raise
