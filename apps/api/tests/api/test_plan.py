"""Self-service plan switching (ROADMAP.md P2, ADR-016's own trigger)."""
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.audit_log import AuditLog
from app.models.plan import Plan
from app.models.tenant import Tenant, TenantType
from app.models.user import Role, User


def _seed_user(db: Session, *, role: Role, tenant: Tenant | None = None) -> tuple[User, str, Tenant]:
    if tenant is None:
        tenant = Tenant(name=f"Tenant {uuid.uuid4().hex[:8]}", tenant_type=TenantType.SCHOOL)
        db.add(tenant)
        db.flush()
    user = User(
        tenant_id=tenant.id,
        email=f"{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("irrelevant-for-this-test"),
        display_name="Test User",
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token, _ = create_access_token(user_id=user.id, tenant_id=user.tenant_id, role=user.role.value)
    return user, token, tenant


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _make_plan(db: Session, *, slug: str, name: str) -> Plan:
    plan = Plan(slug=slug, name=name)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def test_list_plans_returns_every_plan_including_the_seeded_free_plan(client: TestClient, db: Session) -> None:
    _, token, _ = _seed_user(db, role=Role.STUDENT)
    response = client.get("/plans", headers=_headers(token))
    assert response.status_code == 200
    slugs = {p["slug"] for p in response.json()}
    assert "free" in slugs  # migration 0010


def test_tenant_admin_can_self_service_switch_the_tenants_plan(client: TestClient, db: Session) -> None:
    other_plan = _make_plan(db, slug=f"school-{uuid.uuid4().hex[:8]}", name="Okul")
    _, token, tenant = _seed_user(db, role=Role.TENANT_ADMIN)

    response = client.put("/plans/tenant", json={"plan_slug": other_plan.slug}, headers=_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == other_plan.slug

    db.refresh(tenant)
    assert tenant.plan_id == other_plan.id


def test_switch_writes_an_audit_record(client: TestClient, db: Session) -> None:
    other_plan = _make_plan(db, slug=f"school-{uuid.uuid4().hex[:8]}", name="Okul")
    _, token, tenant = _seed_user(db, role=Role.SUPER_ADMIN)

    response = client.put("/plans/tenant", json={"plan_slug": other_plan.slug}, headers=_headers(token))
    assert response.status_code == 200

    audit_row = db.query(AuditLog).filter(AuditLog.tenant_id == tenant.id, AuditLog.action == "tenant.plan_changed").first()
    assert audit_row is not None
    assert audit_row.target_id == tenant.id


def test_switch_to_an_unknown_plan_slug_is_rejected(client: TestClient, db: Session) -> None:
    _, token, _ = _seed_user(db, role=Role.SUPER_ADMIN)
    response = client.put("/plans/tenant", json={"plan_slug": "does-not-exist"}, headers=_headers(token))
    assert response.status_code == 404
    assert response.json()["detail"] == "plan_not_found"


def test_teacher_cannot_switch_the_tenants_plan(client: TestClient, db: Session) -> None:
    other_plan = _make_plan(db, slug=f"school-{uuid.uuid4().hex[:8]}", name="Okul")
    _, token, _ = _seed_user(db, role=Role.TEACHER)

    response = client.put("/plans/tenant", json={"plan_slug": other_plan.slug}, headers=_headers(token))
    assert response.status_code == 403


def test_student_cannot_switch_the_tenants_plan(client: TestClient, db: Session) -> None:
    other_plan = _make_plan(db, slug=f"school-{uuid.uuid4().hex[:8]}", name="Okul")
    _, token, _ = _seed_user(db, role=Role.STUDENT)

    response = client.put("/plans/tenant", json={"plan_slug": other_plan.slug}, headers=_headers(token))
    assert response.status_code == 403


def test_switching_a_tenants_plan_never_affects_another_tenant(client: TestClient, db: Session) -> None:
    """§52 cross-tenant negative test: the endpoint always uses the
    caller's own tenant_id from the token (§51) — there is no tenant_id
    field in the request body to smuggle a different target."""
    plan_a = _make_plan(db, slug=f"plan-a-{uuid.uuid4().hex[:8]}", name="Plan A")
    plan_b = _make_plan(db, slug=f"plan-b-{uuid.uuid4().hex[:8]}", name="Plan B")
    _, token_a, tenant_a = _seed_user(db, role=Role.SUPER_ADMIN)
    _, _, tenant_b = _seed_user(db, role=Role.SUPER_ADMIN)
    tenant_b.plan_id = plan_a.id
    db.commit()

    response = client.put("/plans/tenant", json={"plan_slug": plan_b.slug}, headers=_headers(token_a))
    assert response.status_code == 200

    db.refresh(tenant_a)
    db.refresh(tenant_b)
    assert tenant_a.plan_id == plan_b.id
    assert tenant_b.plan_id == plan_a.id  # untouched
