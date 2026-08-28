"""Mandatory cross-tenant and role tests (§52, §88).

Users with non-STUDENT roles cannot be created through the public
`/auth/register` endpoint by design (see ADR-011), so this suite seeds them
directly through the ORM — exercising the RBAC/tenant-scoping enforcement
in `app/api/deps.py` and `app/api/routes/auth.py` independently of the
registration flow.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.tenant import Tenant, TenantType
from app.models.user import Role, User


def _seed_user(db: Session, *, tenant_name: str, role: Role) -> tuple[User, str]:
    tenant = Tenant(name=tenant_name, tenant_type=TenantType.SCHOOL)
    db.add(tenant)
    db.flush()

    user = User(
        tenant_id=tenant.id,
        email=f"{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("irrelevant-for-this-test"),
        display_name=tenant_name,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token, _ = create_access_token(user_id=user.id, tenant_id=user.tenant_id, role=user.role.value)
    return user, token


def test_tenant_admin_sees_only_own_tenant_users(client: TestClient, db: Session) -> None:
    tenant_a_admin, token_a = _seed_user(db, tenant_name="Tenant A", role=Role.TENANT_ADMIN)
    tenant_b_admin, _token_b = _seed_user(db, tenant_name="Tenant B", role=Role.TENANT_ADMIN)

    response = client.get("/auth/tenant/users", headers={"Authorization": f"Bearer {token_a}"})

    assert response.status_code == 200
    returned_ids = {u["id"] for u in response.json()}
    assert tenant_a_admin.id in returned_ids
    assert tenant_b_admin.id not in returned_ids  # the mandatory negative assertion (§52)


def test_cross_tenant_admin_cannot_be_tricked_by_a_second_call(client: TestClient, db: Session) -> None:
    """Even calling the endpoint twice from two different tenant admins never
    lets either see the other tenant's roster — there is no client-supplied
    tenant_id anywhere in the request for an attacker to manipulate."""
    _, token_a = _seed_user(db, tenant_name="Tenant C", role=Role.TENANT_ADMIN)
    _, token_b = _seed_user(db, tenant_name="Tenant D", role=Role.TENANT_ADMIN)

    users_seen_by_a = {u["id"] for u in client.get("/auth/tenant/users", headers={"Authorization": f"Bearer {token_a}"}).json()}
    users_seen_by_b = {u["id"] for u in client.get("/auth/tenant/users", headers={"Authorization": f"Bearer {token_b}"}).json()}

    assert users_seen_by_a.isdisjoint(users_seen_by_b)


@pytest.mark.parametrize("role", [Role.STUDENT, Role.TEACHER, Role.PARENT])
def test_non_admin_roles_cannot_list_tenant_users(client: TestClient, db: Session, role: Role) -> None:
    _, token = _seed_user(db, tenant_name="Tenant E", role=role)
    response = client.get("/auth/tenant/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


@pytest.mark.parametrize("role", [Role.TENANT_ADMIN, Role.SCHOOL_ADMIN, Role.SUPER_ADMIN])
def test_admin_roles_can_list_tenant_users(client: TestClient, db: Session, role: Role) -> None:
    _, token = _seed_user(db, tenant_name="Tenant F", role=role)
    response = client.get("/auth/tenant/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_inactive_user_token_is_rejected(client: TestClient, db: Session) -> None:
    user, token = _seed_user(db, tenant_name="Tenant G", role=Role.TENANT_ADMIN)
    user.is_active = False
    db.commit()

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
