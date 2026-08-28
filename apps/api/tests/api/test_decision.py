import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.tenant import Tenant, TenantType
from app.models.user import Role, User


def _seed_user(db: Session, *, role: Role, tenant: Tenant | None = None) -> tuple[User, str]:
    if tenant is None:
        tenant = Tenant(name=f"Tenant {uuid.uuid4().hex[:8]}", tenant_type=TenantType.INDIVIDUAL)
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
    return user, token


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin(db: Session) -> tuple[User, str]:
    return _seed_user(db, role=Role.SUPER_ADMIN)


@pytest.fixture
def skill_id(client: TestClient, admin: tuple[User, str]) -> str:
    _, token = admin
    subject = client.post("/curriculum/subjects", json={"slug": f"s-{uuid.uuid4().hex[:8]}", "name": "Test"}, headers=_headers(token)).json()
    topic = client.post("/curriculum/topics", json={"subject_id": subject["id"], "slug": "t", "name": "T"}, headers=_headers(token)).json()
    concept = client.post("/curriculum/concepts", json={"topic_id": topic["id"], "slug": "c", "name": "C"}, headers=_headers(token)).json()
    skill = client.post(
        "/curriculum/skills", json={"concept_id": concept["id"], "slug": "sk", "name": "Skill"}, headers=_headers(token)
    ).json()
    return skill["id"]


def test_next_action_for_evidence_free_skill_returns_insufficient_evidence_action(
    client: TestClient, db: Session, skill_id: str
) -> None:
    _, student_token = _seed_user(db, role=Role.STUDENT)
    response = client.post("/decisions/next-action", params={"skill_id": skill_id}, headers=_headers(student_token))
    assert response.status_code == 201
    body = response.json()
    assert body["selected_action"] == "insufficient_evidence_action"
    assert body["policy_version"] == "pde-policy-v1"
    assert body["model_version"] == "bayesian-beta-binomial-v1"
    assert body["authorization_result"] == "allowed"
    assert len(body["candidate_actions"]) == 12
    assert len(body["knowledge_state_snapshot"]) == 5
    assert body["is_shadow"] is False


def test_student_cannot_request_decision_for_another_student(client: TestClient, db: Session, skill_id: str) -> None:
    tenant = Tenant(name="Shared", tenant_type=TenantType.SCHOOL)
    db.add(tenant)
    db.flush()
    db.commit()
    student_a, _ = _seed_user(db, role=Role.STUDENT, tenant=tenant)
    _, student_b_token = _seed_user(db, role=Role.STUDENT, tenant=tenant)

    response = client.post(
        "/decisions/next-action",
        params={"skill_id": skill_id, "student_id": student_a.id},
        headers=_headers(student_b_token),
    )
    assert response.status_code == 403


def test_teacher_must_specify_student_id(client: TestClient, db: Session, skill_id: str) -> None:
    _, teacher_token = _seed_user(db, role=Role.TEACHER)
    response = client.post("/decisions/next-action", params={"skill_id": skill_id}, headers=_headers(teacher_token))
    assert response.status_code == 400


def test_student_cannot_request_shadow_mode(client: TestClient, db: Session, skill_id: str) -> None:
    _, student_token = _seed_user(db, role=Role.STUDENT)
    response = client.post(
        "/decisions/next-action", params={"skill_id": skill_id, "mode": "shadow"}, headers=_headers(student_token)
    )
    assert response.status_code == 403


def test_unknown_skill_returns_404(client: TestClient, db: Session) -> None:
    _, student_token = _seed_user(db, role=Role.STUDENT)
    response = client.post(
        "/decisions/next-action", params={"skill_id": str(uuid.uuid4())}, headers=_headers(student_token)
    )
    assert response.status_code == 404


def test_cross_tenant_decision_lookup_is_rejected(client: TestClient, db: Session, skill_id: str) -> None:
    """§52: a decision created in tenant A must not be readable from tenant B."""
    _, student_token = _seed_user(db, role=Role.STUDENT)
    created = client.post(
        "/decisions/next-action", params={"skill_id": skill_id}, headers=_headers(student_token)
    ).json()

    _, other_tenant_token = _seed_user(db, role=Role.SUPER_ADMIN)
    response = client.get(f"/decisions/{created['id']}", headers=_headers(other_tenant_token))
    assert response.status_code == 404


def test_get_decision_returns_full_explanation(client: TestClient, db: Session, skill_id: str) -> None:
    student, student_token = _seed_user(db, role=Role.STUDENT)
    created = client.post(
        "/decisions/next-action", params={"skill_id": skill_id}, headers=_headers(student_token)
    ).json()

    response = client.get(f"/decisions/{created['id']}", headers=_headers(student_token))
    assert response.status_code == 200
    body = response.json()
    for field in (
        "id",
        "student_user_id",
        "skill_id",
        "selected_action",
        "candidate_actions",
        "reason_codes",
        "policy_version",
        "model_version",
        "confidence",
        "knowledge_state_snapshot",
        "evidence_ids",
        "authorization_result",
        "authorization_reason",
        "is_shadow",
        "created_at",
    ):
        assert field in body


def test_staff_forced_shadow_decision_is_excluded_from_default_history(
    client: TestClient, db: Session, skill_id: str
) -> None:
    tenant = Tenant(name="Staff Tenant", tenant_type=TenantType.SCHOOL)
    db.add(tenant)
    db.flush()
    db.commit()
    student, _ = _seed_user(db, role=Role.STUDENT, tenant=tenant)
    _, teacher_token = _seed_user(db, role=Role.TEACHER, tenant=tenant)

    shadow_response = client.post(
        "/decisions/next-action",
        params={"skill_id": skill_id, "student_id": student.id, "mode": "shadow"},
        headers=_headers(teacher_token),
    )
    assert shadow_response.status_code == 201
    assert shadow_response.json()["is_shadow"] is True

    default_history = client.get(
        "/decisions", params={"skill_id": skill_id, "student_id": student.id}, headers=_headers(teacher_token)
    ).json()
    assert default_history == []

    with_shadow = client.get(
        "/decisions",
        params={"skill_id": skill_id, "student_id": student.id, "include_shadow": True},
        headers=_headers(teacher_token),
    ).json()
    assert len(with_shadow) == 1


def test_tenant_shadow_mode_default_forces_all_decisions_shadow(
    client: TestClient, db: Session, skill_id: str
) -> None:
    tenant = Tenant(name="Piloting Tenant", tenant_type=TenantType.SCHOOL, pde_shadow_mode_default=True)
    db.add(tenant)
    db.flush()
    db.commit()
    student, student_token = _seed_user(db, role=Role.STUDENT, tenant=tenant)

    response = client.post("/decisions/next-action", params={"skill_id": skill_id}, headers=_headers(student_token))
    assert response.status_code == 201
    assert response.json()["is_shadow"] is True

    history = client.get(
        "/decisions", params={"skill_id": skill_id}, headers=_headers(student_token)
    ).json()
    assert history == []  # student's own default view also excludes shadow decisions


def test_non_staff_cannot_include_shadow_in_history(client: TestClient, db: Session, skill_id: str) -> None:
    _, student_token = _seed_user(db, role=Role.STUDENT)
    response = client.get(
        "/decisions", params={"skill_id": skill_id, "include_shadow": True}, headers=_headers(student_token)
    )
    assert response.status_code == 403
