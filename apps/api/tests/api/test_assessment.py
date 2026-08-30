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


@pytest.fixture
def question_id(client: TestClient, admin: tuple[User, str], skill_id: str) -> str:
    _, token = admin
    response = client.post(
        "/assessment/questions",
        json={"skill_id": skill_id, "facet_type": "application", "prompt": "2+2=?", "correct_answer": "4"},
        headers=_headers(token),
    )
    return response.json()["id"]


@pytest.fixture
def open_ended_question_id(client: TestClient, admin: tuple[User, str], skill_id: str) -> str:
    _, token = admin
    response = client.post(
        "/assessment/questions",
        json={"skill_id": skill_id, "facet_type": "transfer", "prompt": "Explain in your own words.", "correct_answer": None},
        headers=_headers(token),
    )
    return response.json()["id"]


def test_question_public_view_hides_correct_answer(client: TestClient, admin: tuple[User, str], question_id: str) -> None:
    _, token = admin
    response = client.get(f"/assessment/questions/{question_id}", headers=_headers(token))
    assert response.status_code == 200
    assert "correct_answer" not in response.json()


def test_student_cannot_create_question(client: TestClient, db: Session, question_id: str) -> None:
    _, student_token = _seed_user(db, role=Role.STUDENT)
    response = client.post(
        "/assessment/questions",
        json={"skill_id": "whatever", "facet_type": "recall", "prompt": "x"},
        headers=_headers(student_token),
    )
    assert response.status_code == 403


def test_correct_answer_is_auto_evaluated_and_produces_positive_evidence(
    client: TestClient, db: Session, question_id: str
) -> None:
    student, student_token = _seed_user(db, role=Role.STUDENT)
    response = client.post(
        "/assessment/attempts",
        json={
            "question_id": question_id,
            "assessment_type": "formative",
            "learner_response": "4",
            "idempotency_key": str(uuid.uuid4()),
        },
        headers=_headers(student_token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["is_correct"] is True
    assert body["evaluation_method"] == "automatic"
    assert body["evaluated_at"] is not None

    evidence_response = client.get("/assessment/evidence", headers=_headers(student_token))
    assert evidence_response.status_code == 200
    evidence = evidence_response.json()
    assert len(evidence) == 1
    assert evidence[0]["polarity"] == "positive"
    assert evidence[0]["student_user_id"] == student.id


def test_incorrect_answer_produces_negative_evidence(client: TestClient, db: Session, question_id: str) -> None:
    _, student_token = _seed_user(db, role=Role.STUDENT)
    client.post(
        "/assessment/attempts",
        json={
            "question_id": question_id,
            "assessment_type": "diagnostic",
            "learner_response": "5",
            "idempotency_key": str(uuid.uuid4()),
        },
        headers=_headers(student_token),
    )
    evidence = client.get("/assessment/evidence", headers=_headers(student_token)).json()
    assert evidence[0]["polarity"] == "negative"


def test_duplicate_attempt_submission_is_idempotent(client: TestClient, db: Session, question_id: str) -> None:
    _, student_token = _seed_user(db, role=Role.STUDENT)
    key = str(uuid.uuid4())
    payload = {"question_id": question_id, "assessment_type": "formative", "learner_response": "4", "idempotency_key": key}

    first = client.post("/assessment/attempts", json=payload, headers=_headers(student_token))
    second = client.post("/assessment/attempts", json=payload, headers=_headers(student_token))

    assert first.json()["id"] == second.json()["id"]
    evidence = client.get("/assessment/evidence", headers=_headers(student_token)).json()
    assert len(evidence) == 1  # not duplicated by the second submission


def test_open_ended_question_requires_manual_evaluation(
    client: TestClient, db: Session, open_ended_question_id: str
) -> None:
    # The grader must be in the same tenant as the student — a teacher in a
    # different tenant grading this attempt is exactly the cross-tenant case
    # that must fail, so seed both in one tenant deliberately.
    tenant = Tenant(name="Grading Tenant", tenant_type=TenantType.SCHOOL)
    db.add(tenant)
    db.flush()
    db.commit()

    _, student_token = _seed_user(db, role=Role.STUDENT, tenant=tenant)
    submit_response = client.post(
        "/assessment/attempts",
        json={
            "question_id": open_ended_question_id,
            "assessment_type": "formative",
            "learner_response": "Some explanation.",
            "idempotency_key": str(uuid.uuid4()),
        },
        headers=_headers(student_token),
    )
    attempt = submit_response.json()
    assert attempt["is_correct"] is None
    assert attempt["evaluated_at"] is None

    _, teacher_token = _seed_user(db, role=Role.TEACHER, tenant=tenant)

    student_cannot_grade = client.post(
        f"/assessment/attempts/{attempt['id']}/evaluate",
        json={"is_correct": True, "evaluation_confidence": 0.9},
        headers=_headers(student_token),
    )
    assert student_cannot_grade.status_code == 403

    graded = client.post(
        f"/assessment/attempts/{attempt['id']}/evaluate",
        json={"is_correct": True, "evaluation_confidence": 0.9},
        headers=_headers(teacher_token),
    )
    assert graded.status_code == 200
    assert graded.json()["evaluation_method"] == "manual"

    re_grade = client.post(
        f"/assessment/attempts/{attempt['id']}/evaluate",
        json={"is_correct": False, "evaluation_confidence": 0.9},
        headers=_headers(teacher_token),
    )
    assert re_grade.status_code == 409


def test_observation_payload_rejects_interpretive_keys(client: TestClient, db: Session) -> None:
    _, student_token = _seed_user(db, role=Role.STUDENT)
    response = client.post(
        "/assessment/observations",
        json={
            "subject_type": "task",
            "subject_id": str(uuid.uuid4()),
            "event_type": "task_completed",
            "payload": {"mastery": True},
            "idempotency_key": str(uuid.uuid4()),
        },
        headers=_headers(student_token),
    )
    assert response.status_code == 422


def test_observation_with_unknown_event_type_rejected(client: TestClient, db: Session) -> None:
    _, student_token = _seed_user(db, role=Role.STUDENT)
    response = client.post(
        "/assessment/observations",
        json={
            "subject_type": "task",
            "subject_id": str(uuid.uuid4()),
            "event_type": "student_understands_newton",
            "payload": {},
            "idempotency_key": str(uuid.uuid4()),
        },
        headers=_headers(student_token),
    )
    assert response.status_code == 422


def test_duplicate_observation_submission_is_idempotent(client: TestClient, db: Session) -> None:
    _, student_token = _seed_user(db, role=Role.STUDENT)
    key = str(uuid.uuid4())
    payload = {
        "subject_type": "task",
        "subject_id": str(uuid.uuid4()),
        "event_type": "hint_requested",
        "payload": {"hint_index": 1},
        "idempotency_key": key,
    }

    first = client.post("/assessment/observations", json=payload, headers=_headers(student_token))
    second = client.post("/assessment/observations", json=payload, headers=_headers(student_token))

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]


def test_observation_for_foreign_tenant_attempt_is_rejected(client: TestClient, db: Session, question_id: str) -> None:
    _, student_a_token = _seed_user(db, role=Role.STUDENT)
    attempt = client.post(
        "/assessment/attempts",
        json={"question_id": question_id, "assessment_type": "formative", "learner_response": "4", "idempotency_key": str(uuid.uuid4())},
        headers=_headers(student_a_token),
    ).json()

    _, student_b_token = _seed_user(db, role=Role.STUDENT)  # different tenant
    response = client.post(
        "/assessment/observations",
        json={
            "subject_type": "attempt",
            "subject_id": attempt["id"],
            "event_type": "hint_requested",
            "payload": {},
            "idempotency_key": str(uuid.uuid4()),
        },
        headers=_headers(student_b_token),
    )
    assert response.status_code == 404


def test_student_cannot_see_another_students_evidence(client: TestClient, db: Session, question_id: str) -> None:
    tenant = Tenant(name="Shared School", tenant_type=TenantType.SCHOOL)
    db.add(tenant)
    db.flush()
    db.commit()

    _student_a, token_a = _seed_user(db, role=Role.STUDENT, tenant=tenant)
    _student_b, token_b = _seed_user(db, role=Role.STUDENT, tenant=tenant)

    client.post(
        "/assessment/attempts",
        json={"question_id": question_id, "assessment_type": "formative", "learner_response": "4", "idempotency_key": str(uuid.uuid4())},
        headers=_headers(token_a),
    )

    evidence_b = client.get("/assessment/evidence", headers=_headers(token_b)).json()
    assert evidence_b == []


def test_parent_can_see_only_linked_childs_evidence(client: TestClient, db: Session, question_id: str) -> None:
    from app.models.relationship import ParentStudentLink

    tenant = Tenant(name="Family School", tenant_type=TenantType.SCHOOL)
    db.add(tenant)
    db.flush()
    db.commit()

    linked_child, _ = _seed_user(db, role=Role.STUDENT, tenant=tenant)
    other_child, other_child_token = _seed_user(db, role=Role.STUDENT, tenant=tenant)
    parent, parent_token = _seed_user(db, role=Role.PARENT, tenant=tenant)

    db.add(ParentStudentLink(tenant_id=tenant.id, parent_user_id=parent.id, student_user_id=linked_child.id))
    db.commit()

    client.post(
        "/assessment/attempts",
        json={"question_id": question_id, "assessment_type": "formative", "learner_response": "4", "idempotency_key": str(uuid.uuid4())},
        headers=_headers(other_child_token),
    )

    denied = client.get(f"/assessment/evidence?student_id={other_child.id}", headers=_headers(parent_token))
    assert denied.status_code == 403

    missing_param = client.get("/assessment/evidence", headers=_headers(parent_token))
    assert missing_param.status_code == 400


def test_teacher_can_see_all_tenant_evidence(client: TestClient, db: Session, question_id: str) -> None:
    tenant = Tenant(name="Another School", tenant_type=TenantType.SCHOOL)
    db.add(tenant)
    db.flush()
    db.commit()

    student, student_token = _seed_user(db, role=Role.STUDENT, tenant=tenant)
    _, teacher_token = _seed_user(db, role=Role.TEACHER, tenant=tenant)

    client.post(
        "/assessment/attempts",
        json={"question_id": question_id, "assessment_type": "formative", "learner_response": "4", "idempotency_key": str(uuid.uuid4())},
        headers=_headers(student_token),
    )

    evidence = client.get("/assessment/evidence", headers=_headers(teacher_token)).json()
    assert len(evidence) == 1
    assert evidence[0]["student_user_id"] == student.id


def test_attempt_submissions_are_rate_limited_per_user(client: TestClient, db: Session, question_id: str) -> None:
    """§78: bounds how fast one account can write attempts."""
    _, student_token = _seed_user(db, role=Role.STUDENT)

    responses = [
        client.post(
            "/assessment/attempts",
            json={
                "question_id": question_id,
                "assessment_type": "formative",
                "learner_response": "4",
                "idempotency_key": str(uuid.uuid4()),
            },
            headers=_headers(student_token),
        )
        for _ in range(121)
    ]

    statuses = [r.status_code for r in responses]
    assert statuses.count(201) == 120  # attempts' limit is 120/minute
    assert 429 in statuses
