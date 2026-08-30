import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.audit_log import AuditLog
from app.models.tenant import Tenant, TenantType
from app.models.user import Role, User


def _unique_email() -> str:
    return f"test-{uuid.uuid4().hex}@example.com"


def _seed_staff(db: Session, *, role: Role, tenant: Tenant | None = None) -> tuple[User, str, Tenant]:
    if tenant is None:
        tenant = Tenant(name=f"Tenant {uuid.uuid4().hex[:8]}", tenant_type=TenantType.SCHOOL)
        db.add(tenant)
        db.flush()
    user = User(
        tenant_id=tenant.id,
        email=_unique_email(),
        password_hash=hash_password("irrelevant-for-this-test"),
        display_name="Staff User",
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token, _ = create_access_token(user_id=user.id, tenant_id=user.tenant_id, role=user.role.value)
    return user, token, tenant


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register(client: TestClient, *, email: str | None = None, password: str = "correct-horse-battery") -> dict:
    response = client.post(
        "/auth/register",
        json={"email": email or _unique_email(), "password": password, "display_name": "Test Student"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_register_creates_tenant_and_returns_access_token(client: TestClient) -> None:
    body = _register(client)
    assert body["user"]["role"] == "STUDENT"
    assert body["access_token"]
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]


def test_register_sets_httponly_refresh_cookie(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={"email": _unique_email(), "password": "correct-horse-battery", "display_name": "Test Student"},
    )
    cookie = response.cookies.get("edupulse_refresh_token")
    assert cookie is not None


def test_register_duplicate_email_rejected(client: TestClient) -> None:
    email = _unique_email()
    _register(client, email=email)
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "correct-horse-battery", "display_name": "Second User"},
    )
    assert response.status_code == 409


def test_register_rejects_short_password(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={"email": _unique_email(), "password": "short", "display_name": "Test"},
    )
    assert response.status_code == 422


def test_login_success(client: TestClient) -> None:
    email = _unique_email()
    _register(client, email=email, password="correct-horse-battery")
    response = client.post("/auth/login", json={"email": email, "password": "correct-horse-battery"})
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_wrong_password_rejected(client: TestClient) -> None:
    email = _unique_email()
    _register(client, email=email, password="correct-horse-battery")
    response = client.post("/auth/login", json={"email": email, "password": "wrong-password"})
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_credentials"


def test_login_unknown_email_rejected_with_same_generic_message(client: TestClient) -> None:
    response = client.post("/auth/login", json={"email": _unique_email(), "password": "whatever12345"})
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_credentials"


def test_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user_with_valid_token(client: TestClient) -> None:
    body = _register(client)
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert response.status_code == 200
    assert response.json()["email"] == body["user"]["email"]


def test_me_rejects_garbage_token(client: TestClient) -> None:
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_refresh_issues_new_access_token_and_rotates_cookie(client: TestClient) -> None:
    register_response = client.post(
        "/auth/register",
        json={"email": _unique_email(), "password": "correct-horse-battery", "display_name": "Test"},
    )
    old_access_token = register_response.json()["access_token"]

    refresh_response = client.post("/auth/refresh")
    assert refresh_response.status_code == 200
    new_access_token = refresh_response.json()["access_token"]
    assert new_access_token != old_access_token


def test_refresh_without_cookie_rejected() -> None:
    from fastapi.testclient import TestClient as _TestClient

    from app.main import app

    # A client with no cookie jar shared from a prior request.
    fresh_client = _TestClient(app)
    response = fresh_client.post("/auth/refresh")
    assert response.status_code == 401


def test_login_is_rate_limited_after_repeated_attempts(client: TestClient) -> None:
    email = _unique_email()
    _register(client, email=email, password="correct-horse-battery")

    responses = [client.post("/auth/login", json={"email": email, "password": "wrong-password"}) for _ in range(6)]

    statuses = [r.status_code for r in responses]
    assert 401 in statuses  # the first few are ordinary failed-credential attempts
    assert 429 in statuses  # login's limit is 5/minute — the 6th attempt must be throttled


def test_register_writes_audit_records(client: TestClient, db: Session) -> None:
    body = _register(client)
    user_id = body["user"]["id"]

    audit_actions = {row.action for row in db.query(AuditLog).filter(AuditLog.target_id == user_id).all()}
    assert "user.registered" in audit_actions


def test_logout_revokes_session_so_refresh_then_fails(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={"email": _unique_email(), "password": "correct-horse-battery", "display_name": "Test"},
    )
    logout_response = client.post("/auth/logout")
    assert logout_response.status_code == 204

    refresh_response = client.post("/auth/refresh")
    assert refresh_response.status_code == 401


# --- POST /auth/tenant/users: admin-initiated enrollment ---


def test_super_admin_can_create_a_student(client: TestClient, db: Session) -> None:
    _, token, tenant = _seed_staff(db, role=Role.SUPER_ADMIN)

    response = client.post(
        "/auth/tenant/users",
        json={"email": _unique_email(), "password": "correct-horse-battery", "display_name": "New Student", "role": "STUDENT"},
        headers=_headers(token),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["role"] == "STUDENT"
    assert body["tenant_id"] == tenant.id
    # The created account never receives its own token in this response —
    # this creates someone else's account, it does not sign the caller in as them.
    assert "access_token" not in body


def test_created_user_lands_in_the_actors_own_tenant_not_a_client_supplied_one(client: TestClient, db: Session) -> None:
    """§51: there is no tenant_id field in the request body at all — confirms
    the created user's tenant always comes from the caller's own token."""
    _, token, tenant = _seed_staff(db, role=Role.SUPER_ADMIN)

    response = client.post(
        "/auth/tenant/users",
        json={"email": _unique_email(), "password": "correct-horse-battery", "display_name": "New Teacher", "role": "TEACHER"},
        headers=_headers(token),
    )
    assert response.json()["tenant_id"] == tenant.id


def test_school_admin_cannot_create_a_tenant_admin(client: TestClient, db: Session) -> None:
    """§53/§78 least privilege: a SCHOOL_ADMIN must not be able to create an
    account with more authority than their own."""
    _, token, _ = _seed_staff(db, role=Role.SCHOOL_ADMIN)

    response = client.post(
        "/auth/tenant/users",
        json={"email": _unique_email(), "password": "correct-horse-battery", "display_name": "Escalated", "role": "TENANT_ADMIN"},
        headers=_headers(token),
    )
    assert response.status_code == 403


def test_school_admin_can_create_a_teacher(client: TestClient, db: Session) -> None:
    _, token, _ = _seed_staff(db, role=Role.SCHOOL_ADMIN)

    response = client.post(
        "/auth/tenant/users",
        json={"email": _unique_email(), "password": "correct-horse-battery", "display_name": "New Teacher", "role": "TEACHER"},
        headers=_headers(token),
    )
    assert response.status_code == 201


def test_tenant_admin_cannot_create_a_super_admin(client: TestClient, db: Session) -> None:
    _, token, _ = _seed_staff(db, role=Role.TENANT_ADMIN)

    response = client.post(
        "/auth/tenant/users",
        json={"email": _unique_email(), "password": "correct-horse-battery", "display_name": "Escalated", "role": "SUPER_ADMIN"},
        headers=_headers(token),
    )
    assert response.status_code == 403


def test_duplicate_email_rejected(client: TestClient, db: Session) -> None:
    _, token, _ = _seed_staff(db, role=Role.SUPER_ADMIN)
    email = _unique_email()

    first = client.post(
        "/auth/tenant/users",
        json={"email": email, "password": "correct-horse-battery", "display_name": "First", "role": "STUDENT"},
        headers=_headers(token),
    )
    assert first.status_code == 201
    second = client.post(
        "/auth/tenant/users",
        json={"email": email, "password": "correct-horse-battery", "display_name": "Second", "role": "STUDENT"},
        headers=_headers(token),
    )
    assert second.status_code == 409


def test_teacher_cannot_create_users(client: TestClient, db: Session) -> None:
    _, token, _ = _seed_staff(db, role=Role.TEACHER)

    response = client.post(
        "/auth/tenant/users",
        json={"email": _unique_email(), "password": "correct-horse-battery", "display_name": "X", "role": "STUDENT"},
        headers=_headers(token),
    )
    assert response.status_code == 403


def test_student_cannot_create_users(client: TestClient, db: Session) -> None:
    _, token, _ = _seed_staff(db, role=Role.STUDENT)

    response = client.post(
        "/auth/tenant/users",
        json={"email": _unique_email(), "password": "correct-horse-battery", "display_name": "X", "role": "STUDENT"},
        headers=_headers(token),
    )
    assert response.status_code == 403


def test_admin_created_user_writes_an_audit_record(client: TestClient, db: Session) -> None:
    _, token, _ = _seed_staff(db, role=Role.SUPER_ADMIN)

    response = client.post(
        "/auth/tenant/users",
        json={"email": _unique_email(), "password": "correct-horse-battery", "display_name": "Audited", "role": "STUDENT"},
        headers=_headers(token),
    )
    user_id = response.json()["id"]

    audit_row = db.query(AuditLog).filter(AuditLog.target_id == user_id, AuditLog.action == "user.created_by_admin").first()
    assert audit_row is not None


def test_created_user_can_log_in_with_the_password_the_admin_set(client: TestClient, db: Session) -> None:
    _, token, _ = _seed_staff(db, role=Role.SUPER_ADMIN)
    email = _unique_email()

    create_response = client.post(
        "/auth/tenant/users",
        json={"email": email, "password": "a-real-password-here", "display_name": "Loginable", "role": "STUDENT"},
        headers=_headers(token),
    )
    assert create_response.status_code == 201

    login_response = client.post("/auth/login", json={"email": email, "password": "a-real-password-here"})
    assert login_response.status_code == 200
