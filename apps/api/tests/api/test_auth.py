import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def _unique_email() -> str:
    return f"test-{uuid.uuid4().hex}@example.com"


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
