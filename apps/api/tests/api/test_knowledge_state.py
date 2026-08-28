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


@pytest.fixture
def question_id(client: TestClient, admin: tuple[User, str], skill_id: str) -> str:
    _, token = admin
    response = client.post(
        "/assessment/questions",
        json={"skill_id": skill_id, "facet_type": "application", "prompt": "2+2=?", "correct_answer": "4"},
        headers=_headers(token),
    )
    return response.json()["id"]


def _submit_and_evaluate(client: TestClient, *, token: str, question_id: str, learner_response: str) -> None:
    client.post(
        "/assessment/attempts",
        json={
            "question_id": question_id,
            "assessment_type": "formative",
            "learner_response": learner_response,
            "idempotency_key": str(uuid.uuid4()),
        },
        headers=_headers(token),
    )


def test_zero_evidence_returns_insufficient_evidence(client: TestClient, db: Session, skill_id: str) -> None:
    _, student_token = _seed_user(db, role=Role.STUDENT)
    response = client.get(
        "/knowledge-state", params={"skill_id": skill_id, "facet_type": "application"}, headers=_headers(student_token)
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["mastery_probability"] == 0.5
    assert body[0]["confidence_label"] == "insufficient_evidence"
    assert body[0]["model_version"] == "bayesian-beta-binomial-v1"


def test_correct_attempt_raises_mastery_probability_above_prior(
    client: TestClient, db: Session, question_id: str, skill_id: str
) -> None:
    student, student_token = _seed_user(db, role=Role.STUDENT)
    _submit_and_evaluate(client, token=student_token, question_id=question_id, learner_response="4")

    response = client.get(
        "/knowledge-state", params={"skill_id": skill_id, "facet_type": "application"}, headers=_headers(student_token)
    )
    body = response.json()[0]
    assert body["mastery_probability"] > 0.5
    assert body["evidence_count"] == 1


def test_omitting_facet_type_returns_all_five_facets_independently(
    client: TestClient, db: Session, question_id: str, skill_id: str
) -> None:
    student, student_token = _seed_user(db, role=Role.STUDENT)
    _submit_and_evaluate(client, token=student_token, question_id=question_id, learner_response="4")

    response = client.get("/knowledge-state", params={"skill_id": skill_id}, headers=_headers(student_token))
    body = response.json()
    assert len(body) == 5
    facets = {row["facet_type"]: row for row in body}
    assert facets["application"]["mastery_probability"] > 0.5
    # The correct attempt targeted the "application" facet only — every
    # other facet must remain exactly at the uninformative prior (§28).
    for facet_type in ("recognition", "recall", "transfer", "retention"):
        assert facets[facet_type]["mastery_probability"] == 0.5
        assert facets[facet_type]["confidence_label"] == "insufficient_evidence"


def test_student_cannot_view_another_students_knowledge_state(
    client: TestClient, db: Session, question_id: str, skill_id: str
) -> None:
    tenant = Tenant(name="Shared Tenant", tenant_type=TenantType.SCHOOL)
    db.add(tenant)
    db.flush()
    db.commit()

    student_a, _ = _seed_user(db, role=Role.STUDENT, tenant=tenant)
    _, student_b_token = _seed_user(db, role=Role.STUDENT, tenant=tenant)

    response = client.get(
        "/knowledge-state",
        params={"skill_id": skill_id, "facet_type": "application", "student_id": student_a.id},
        headers=_headers(student_b_token),
    )
    assert response.status_code == 403


def test_cross_tenant_student_id_is_rejected(client: TestClient, db: Session, question_id: str, skill_id: str) -> None:
    """§52: a staff member in tenant A must not be able to read a student's
    knowledge state in tenant B by guessing their user id."""
    student_a, student_a_token = _seed_user(db, role=Role.STUDENT)
    _submit_and_evaluate(client, token=student_a_token, question_id=question_id, learner_response="4")

    _, teacher_b_token = _seed_user(db, role=Role.TEACHER)  # different tenant

    response = client.get(
        "/knowledge-state",
        params={"skill_id": skill_id, "facet_type": "application", "student_id": student_a.id},
        headers=_headers(teacher_b_token),
    )
    assert response.status_code == 200
    body = response.json()
    # tenant_id is always derived from the token (§51) — querying student_a's
    # id from tenant B's session finds nothing, not tenant A's real state.
    assert body[0]["mastery_probability"] == 0.5
    assert body[0]["confidence_label"] == "insufficient_evidence"


def test_teacher_must_specify_student_id(client: TestClient, db: Session, skill_id: str) -> None:
    _, teacher_token = _seed_user(db, role=Role.TEACHER)
    response = client.get(
        "/knowledge-state", params={"skill_id": skill_id, "facet_type": "application"}, headers=_headers(teacher_token)
    )
    assert response.status_code == 400


def test_parent_without_link_cannot_view_child_state(client: TestClient, db: Session, skill_id: str) -> None:
    tenant = Tenant(name="Family Tenant", tenant_type=TenantType.INDIVIDUAL)
    db.add(tenant)
    db.flush()
    db.commit()

    student, _ = _seed_user(db, role=Role.STUDENT, tenant=tenant)
    _, parent_token = _seed_user(db, role=Role.PARENT, tenant=tenant)

    response = client.get(
        "/knowledge-state",
        params={"skill_id": skill_id, "facet_type": "application", "student_id": student.id},
        headers=_headers(parent_token),
    )
    assert response.status_code == 403


def test_parent_with_link_can_view_child_state(client: TestClient, db: Session, skill_id: str) -> None:
    tenant = Tenant(name="Family Tenant 2", tenant_type=TenantType.INDIVIDUAL)
    db.add(tenant)
    db.flush()
    db.commit()

    student, _ = _seed_user(db, role=Role.STUDENT, tenant=tenant)
    parent, parent_token = _seed_user(db, role=Role.PARENT, tenant=tenant)
    db.add(ParentStudentLink(tenant_id=tenant.id, parent_user_id=parent.id, student_user_id=student.id))
    db.commit()

    response = client.get(
        "/knowledge-state",
        params={"skill_id": skill_id, "facet_type": "application", "student_id": student.id},
        headers=_headers(parent_token),
    )
    assert response.status_code == 200


def test_unknown_skill_returns_404(client: TestClient, db: Session) -> None:
    _, student_token = _seed_user(db, role=Role.STUDENT)
    response = client.get(
        "/knowledge-state",
        params={"skill_id": str(uuid.uuid4()), "facet_type": "application"},
        headers=_headers(student_token),
    )
    assert response.status_code == 404
