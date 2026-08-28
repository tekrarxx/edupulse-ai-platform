import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.relationship import ParentStudentLink
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
def tenant(db: Session) -> Tenant:
    tenant = Tenant(name=f"Tenant {uuid.uuid4().hex[:8]}", tenant_type=TenantType.SCHOOL)
    db.add(tenant)
    db.flush()
    db.commit()
    return tenant


@pytest.fixture
def admin(db: Session, tenant: Tenant) -> tuple[User, str]:
    return _seed_user(db, role=Role.SUPER_ADMIN, tenant=tenant)


@pytest.fixture
def student(db: Session, tenant: Tenant) -> tuple[User, str]:
    return _seed_user(db, role=Role.STUDENT, tenant=tenant)


@pytest.fixture
def skill_id(client: TestClient, admin: tuple[User, str]) -> str:
    _, token = admin
    subject = client.post("/curriculum/subjects", json={"slug": f"s-{uuid.uuid4().hex[:8]}", "name": "Test"}, headers=_headers(token)).json()
    topic = client.post("/curriculum/topics", json={"subject_id": subject["id"], "slug": "t", "name": "T"}, headers=_headers(token)).json()
    concept = client.post("/curriculum/concepts", json={"topic_id": topic["id"], "slug": "c", "name": "C"}, headers=_headers(token)).json()
    skill = client.post(
        "/curriculum/skills", json={"concept_id": concept["id"], "slug": "sk", "name": "Newton'un Ikinci Yasasi"}, headers=_headers(token)
    ).json()
    return skill["id"]


def _answer(client: TestClient, token: str, question_id: str, response: str) -> None:
    client.post(
        "/assessment/attempts",
        json={
            "question_id": question_id,
            "assessment_type": "formative",
            "learner_response": response,
            "idempotency_key": str(uuid.uuid4()),
        },
        headers=_headers(token),
    )


def test_dashboard_shows_plain_language_progress_no_raw_floats(
    client: TestClient, db: Session, admin: tuple[User, str], student: tuple[User, str], skill_id: str
) -> None:
    _, admin_token = admin
    student_user, student_token = student

    for _ in range(5):
        q = client.post(
            "/assessment/questions",
            json={"skill_id": skill_id, "facet_type": "application", "prompt": "2+2=?", "correct_answer": "4"},
            headers=_headers(admin_token),
        ).json()
        _answer(client, student_token, q["id"], "4")

    # Trigger a real Prometheus decision so the dashboard has one to surface.
    client.post("/decisions/next-action", params={"skill_id": skill_id}, headers=_headers(student_token))

    response = client.get("/dashboard/student", headers=_headers(student_token))
    assert response.status_code == 200
    body = response.json()

    assert body["strong_skill_count"] == 1
    assert body["weak_skill_count"] == 0
    skill_row = body["skills"][0]
    assert skill_row["skill_name"] == "Newton'un Ikinci Yasasi"
    assert skill_row["mastery_label"] == "İyi öğreniyorsun"
    assert skill_row["is_strong"] is True
    assert skill_row["next_action_label"] is not None

    # §26/§75: no raw posterior float anywhere in the response.
    assert "mastery_probability" not in response.text
    assert "confidence_label" not in response.text


def test_dashboard_marks_low_mastery_skill_as_weak(
    client: TestClient, db: Session, admin: tuple[User, str], student: tuple[User, str], skill_id: str
) -> None:
    _, admin_token = admin
    student_user, student_token = student

    for _ in range(5):
        q = client.post(
            "/assessment/questions",
            json={"skill_id": skill_id, "facet_type": "application", "prompt": "2+2=?", "correct_answer": "4"},
            headers=_headers(admin_token),
        ).json()
        _answer(client, student_token, q["id"], "wrong-answer")

    response = client.get("/dashboard/student", headers=_headers(student_token))
    body = response.json()
    assert body["weak_skill_count"] == 1
    assert body["skills"][0]["mastery_label"] == "Biraz daha çalış"
    assert body["skills"][0]["is_weak"] is True


def test_skill_with_no_evidence_does_not_appear_on_dashboard(
    client: TestClient, db: Session, student: tuple[User, str], skill_id: str
) -> None:
    _, student_token = student
    response = client.get("/dashboard/student", headers=_headers(student_token))
    body = response.json()
    assert body["skills"] == []
    assert body["weak_skill_count"] == 0
    assert body["strong_skill_count"] == 0


def test_student_cannot_view_another_students_dashboard(
    client: TestClient, db: Session, tenant: Tenant, student: tuple[User, str]
) -> None:
    student_a, _ = student
    _, student_b_token = _seed_user(db, role=Role.STUDENT, tenant=tenant)

    response = client.get("/dashboard/student", params={"student_id": student_a.id}, headers=_headers(student_b_token))
    assert response.status_code == 403


def test_teacher_must_specify_student_id(client: TestClient, db: Session, tenant: Tenant) -> None:
    _, teacher_token = _seed_user(db, role=Role.TEACHER, tenant=tenant)
    response = client.get("/dashboard/student", headers=_headers(teacher_token))
    assert response.status_code == 400


def test_cross_tenant_dashboard_access_returns_empty_not_leaked_data(
    client: TestClient, db: Session, admin: tuple[User, str], student: tuple[User, str], skill_id: str
) -> None:
    """§52: a staff member in a different tenant must never see tenant A's
    real dashboard data by guessing a student id."""
    _, admin_token = admin
    student_user, student_token = student
    q = client.post(
        "/assessment/questions",
        json={"skill_id": skill_id, "facet_type": "application", "prompt": "2+2=?", "correct_answer": "4"},
        headers=_headers(admin_token),
    ).json()
    _answer(client, student_token, q["id"], "4")

    _, other_tenant_teacher_token = _seed_user(db, role=Role.TEACHER)  # different tenant
    response = client.get(
        "/dashboard/student", params={"student_id": student_user.id}, headers=_headers(other_tenant_teacher_token)
    )
    assert response.status_code == 200
    assert response.json()["skills"] == []


def test_parent_with_link_can_view_child_dashboard(client: TestClient, db: Session, tenant: Tenant) -> None:
    student_user, _ = _seed_user(db, role=Role.STUDENT, tenant=tenant)
    parent, parent_token = _seed_user(db, role=Role.PARENT, tenant=tenant)
    db.add(ParentStudentLink(tenant_id=tenant.id, parent_user_id=parent.id, student_user_id=student_user.id))
    db.commit()

    response = client.get("/dashboard/student", params={"student_id": student_user.id}, headers=_headers(parent_token))
    assert response.status_code == 200


def test_parent_without_link_cannot_view_dashboard(client: TestClient, db: Session, tenant: Tenant) -> None:
    student_user, _ = _seed_user(db, role=Role.STUDENT, tenant=tenant)
    _, parent_token = _seed_user(db, role=Role.PARENT, tenant=tenant)

    response = client.get("/dashboard/student", params={"student_id": student_user.id}, headers=_headers(parent_token))
    assert response.status_code == 403
