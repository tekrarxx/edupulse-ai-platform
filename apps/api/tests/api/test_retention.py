import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.retention import RetentionCheckpoint
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
        "/curriculum/skills", json={"concept_id": concept["id"], "slug": "sk", "name": "Skill"}, headers=_headers(token)
    ).json()
    return skill["id"]


def _create_application_question(client: TestClient, token: str, skill_id: str) -> str:
    response = client.post(
        "/assessment/questions",
        json={"skill_id": skill_id, "facet_type": "application", "prompt": "2+2=?", "correct_answer": "4"},
        headers=_headers(token),
    )
    return response.json()["id"]


def _answer_correctly(client: TestClient, token: str, question_id: str) -> None:
    client.post(
        "/assessment/attempts",
        json={
            "question_id": question_id,
            "assessment_type": "formative",
            "learner_response": "4",
            "idempotency_key": str(uuid.uuid4()),
        },
        headers=_headers(token),
    )


def _reach_high_confidence_application_mastery(client: TestClient, admin_token: str, student_token: str, skill_id: str) -> None:
    """5 correct application-facet answers cross effective_n >= 4 (ADR-012's
    HIGH_CONFIDENCE threshold), triggering retention-checkpoint scheduling
    (ADR-014) on the last one."""
    for _ in range(5):
        question_id = _create_application_question(client, admin_token, skill_id)
        _answer_correctly(client, student_token, question_id)


def test_reaching_high_confidence_schedules_two_checkpoints(
    client: TestClient, db: Session, admin: tuple[User, str], student: tuple[User, str], skill_id: str
) -> None:
    _, admin_token = admin
    _, student_token = student

    _reach_high_confidence_application_mastery(client, admin_token, student_token, skill_id)

    checkpoints = client.get(
        "/retention/checkpoints", params={"skill_id": skill_id}, headers=_headers(student_token)
    ).json()
    assert len(checkpoints) == 2
    days = sorted(c["checkpoint_days"] for c in checkpoints)
    assert days == [14, 28]
    for checkpoint in checkpoints:
        assert checkpoint["status"] == "pending"
        assert checkpoint["hypothesis"]["predicted_confidence_label"] == "high_confidence"
        assert checkpoint["hypothesis"]["verdict"] == "pending"
        scheduled_for = datetime.fromisoformat(checkpoint["scheduled_for"])
        expected = datetime.now(timezone.utc) + timedelta(days=checkpoint["checkpoint_days"])
        assert abs((scheduled_for - expected).total_seconds()) < 60


def test_scheduling_is_idempotent_per_skill(
    client: TestClient, db: Session, admin: tuple[User, str], student: tuple[User, str], skill_id: str
) -> None:
    _, admin_token = admin
    _, student_token = student
    _reach_high_confidence_application_mastery(client, admin_token, student_token, skill_id)

    # One more correct answer after already at high confidence must not
    # schedule a second pair.
    question_id = _create_application_question(client, admin_token, skill_id)
    _answer_correctly(client, student_token, question_id)

    checkpoints = client.get(
        "/retention/checkpoints", params={"skill_id": skill_id}, headers=_headers(student_token)
    ).json()
    assert len(checkpoints) == 2


def test_due_checkpoints_requires_staff_role(client: TestClient, db: Session, student: tuple[User, str], skill_id: str) -> None:
    _, student_token = student
    response = client.get("/retention/checkpoints/due", headers=_headers(student_token))
    assert response.status_code == 403


def test_due_checkpoint_appears_once_scheduled_for_has_passed(
    client: TestClient, db: Session, admin: tuple[User, str], student: tuple[User, str], skill_id: str
) -> None:
    _, admin_token = admin
    student_user, student_token = student
    _reach_high_confidence_application_mastery(client, admin_token, student_token, skill_id)

    not_yet_due = client.get("/retention/checkpoints/due", headers=_headers(admin_token)).json()
    assert not_yet_due == []

    checkpoint = db.query(RetentionCheckpoint).filter(RetentionCheckpoint.student_user_id == student_user.id).first()
    checkpoint.scheduled_for = datetime.now(timezone.utc) - timedelta(days=1)
    db.commit()

    due = client.get("/retention/checkpoints/due", headers=_headers(admin_token)).json()
    assert len(due) == 1
    assert due[0]["id"] == checkpoint.id


def test_completing_checkpoint_with_correct_answer_supports_hypothesis(
    client: TestClient, db: Session, admin: tuple[User, str], student: tuple[User, str], skill_id: str
) -> None:
    _, admin_token = admin
    student_user, student_token = student
    _reach_high_confidence_application_mastery(client, admin_token, student_token, skill_id)

    checkpoint = db.query(RetentionCheckpoint).filter(RetentionCheckpoint.student_user_id == student_user.id).first()
    delayed_question_id = _create_application_question(client, admin_token, skill_id)

    response = client.post(
        f"/retention/checkpoints/{checkpoint.id}/complete",
        json={"question_id": delayed_question_id, "learner_response": "4", "idempotency_key": str(uuid.uuid4())},
        headers=_headers(admin_token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["retention_estimate"] is not None
    assert body["hypothesis"]["verdict"] == "supported"
    assert body["hypothesis"]["actual_is_correct"] is True

    second_attempt = client.post(
        f"/retention/checkpoints/{checkpoint.id}/complete",
        json={"question_id": delayed_question_id, "learner_response": "4", "idempotency_key": str(uuid.uuid4())},
        headers=_headers(admin_token),
    )
    assert second_attempt.status_code == 409


def test_completing_checkpoint_with_open_ended_question_is_rejected(
    client: TestClient, db: Session, admin: tuple[User, str], student: tuple[User, str], skill_id: str
) -> None:
    _, admin_token = admin
    student_user, student_token = student
    _reach_high_confidence_application_mastery(client, admin_token, student_token, skill_id)
    checkpoint = db.query(RetentionCheckpoint).filter(RetentionCheckpoint.student_user_id == student_user.id).first()

    open_ended = client.post(
        "/assessment/questions",
        json={"skill_id": skill_id, "facet_type": "application", "prompt": "Explain.", "correct_answer": None},
        headers=_headers(admin_token),
    ).json()

    response = client.post(
        f"/retention/checkpoints/{checkpoint.id}/complete",
        json={"question_id": open_ended["id"], "learner_response": "whatever", "idempotency_key": str(uuid.uuid4())},
        headers=_headers(admin_token),
    )
    assert response.status_code == 400


def test_completing_checkpoint_with_wrong_skill_question_is_rejected(
    client: TestClient, db: Session, admin: tuple[User, str], student: tuple[User, str], skill_id: str
) -> None:
    _, admin_token = admin
    student_user, student_token = student
    _reach_high_confidence_application_mastery(client, admin_token, student_token, skill_id)
    checkpoint = db.query(RetentionCheckpoint).filter(RetentionCheckpoint.student_user_id == student_user.id).first()

    other_subject = client.post("/curriculum/subjects", json={"slug": f"s2-{uuid.uuid4().hex[:8]}", "name": "Other"}, headers=_headers(admin_token)).json()
    other_topic = client.post("/curriculum/topics", json={"subject_id": other_subject["id"], "slug": "t2", "name": "T2"}, headers=_headers(admin_token)).json()
    other_concept = client.post("/curriculum/concepts", json={"topic_id": other_topic["id"], "slug": "c2", "name": "C2"}, headers=_headers(admin_token)).json()
    other_skill = client.post(
        "/curriculum/skills", json={"concept_id": other_concept["id"], "slug": "sk2", "name": "Skill2"}, headers=_headers(admin_token)
    ).json()
    wrong_skill_question = _create_application_question(client, admin_token, other_skill["id"])

    response = client.post(
        f"/retention/checkpoints/{checkpoint.id}/complete",
        json={"question_id": wrong_skill_question, "learner_response": "4", "idempotency_key": str(uuid.uuid4())},
        headers=_headers(admin_token),
    )
    assert response.status_code == 400


def test_cross_tenant_checkpoint_completion_is_rejected(
    client: TestClient, db: Session, admin: tuple[User, str], student: tuple[User, str], skill_id: str
) -> None:
    _, admin_token = admin
    student_user, student_token = student
    _reach_high_confidence_application_mastery(client, admin_token, student_token, skill_id)
    checkpoint = db.query(RetentionCheckpoint).filter(RetentionCheckpoint.student_user_id == student_user.id).first()

    _, other_tenant_admin_token = _seed_user(db, role=Role.SUPER_ADMIN)  # a genuinely different tenant
    response = client.post(
        f"/retention/checkpoints/{checkpoint.id}/complete",
        json={"question_id": str(uuid.uuid4()), "learner_response": "4", "idempotency_key": str(uuid.uuid4())},
        headers=_headers(other_tenant_admin_token),
    )
    assert response.status_code == 404


def test_transfer_facet_negative_evidence_is_structurally_tagged(
    client: TestClient, db: Session, admin: tuple[User, str], student: tuple[User, str], skill_id: str
) -> None:
    _, admin_token = admin
    _, student_token = student
    question = client.post(
        "/assessment/questions",
        json={"skill_id": skill_id, "facet_type": "transfer", "prompt": "Transfer item", "correct_answer": "42"},
        headers=_headers(admin_token),
    ).json()
    client.post(
        "/assessment/attempts",
        json={"question_id": question["id"], "assessment_type": "transfer", "learner_response": "wrong", "idempotency_key": str(uuid.uuid4())},
        headers=_headers(student_token),
    )
    evidence = client.get("/assessment/evidence", headers=_headers(student_token)).json()
    assert evidence[0]["failure_mode"] == "transfer_failure"


def test_structural_failure_mode_cannot_be_manually_classified(
    client: TestClient, db: Session, admin: tuple[User, str], student: tuple[User, str], skill_id: str
) -> None:
    _, admin_token = admin
    _, student_token = student
    question = client.post(
        "/assessment/questions",
        json={"skill_id": skill_id, "facet_type": "application", "prompt": "Q", "correct_answer": "4"},
        headers=_headers(admin_token),
    ).json()
    client.post(
        "/assessment/attempts",
        json={"question_id": question["id"], "assessment_type": "formative", "learner_response": "wrong", "idempotency_key": str(uuid.uuid4())},
        headers=_headers(student_token),
    )
    evidence = client.get("/assessment/evidence", headers=_headers(student_token)).json()[0]
    assert evidence["failure_mode"] is None

    response = client.post(
        f"/assessment/evidence/{evidence['id']}/failure-mode",
        json={"failure_mode": "transfer_failure"},
        headers=_headers(admin_token),
    )
    assert response.status_code == 422


def test_teacher_can_classify_unclassified_failure_mode_once(
    client: TestClient, db: Session, admin: tuple[User, str], student: tuple[User, str], skill_id: str
) -> None:
    _, admin_token = admin
    _, student_token = student
    question = client.post(
        "/assessment/questions",
        json={"skill_id": skill_id, "facet_type": "recall", "prompt": "Q", "correct_answer": "4"},
        headers=_headers(admin_token),
    ).json()
    client.post(
        "/assessment/attempts",
        json={"question_id": question["id"], "assessment_type": "retrieval_practice", "learner_response": "wrong", "idempotency_key": str(uuid.uuid4())},
        headers=_headers(student_token),
    )
    evidence = client.get("/assessment/evidence", headers=_headers(student_token)).json()[0]

    classified = client.post(
        f"/assessment/evidence/{evidence['id']}/failure-mode",
        json={"failure_mode": "misconception"},
        headers=_headers(admin_token),
    )
    assert classified.status_code == 200
    assert classified.json()["failure_mode"] == "misconception"

    duplicate = client.post(
        f"/assessment/evidence/{evidence['id']}/failure-mode",
        json={"failure_mode": "careless_error"},
        headers=_headers(admin_token),
    )
    assert duplicate.status_code == 409


def test_student_cannot_classify_failure_mode(
    client: TestClient, db: Session, admin: tuple[User, str], student: tuple[User, str], skill_id: str
) -> None:
    _, admin_token = admin
    _, student_token = student
    question = client.post(
        "/assessment/questions",
        json={"skill_id": skill_id, "facet_type": "recall", "prompt": "Q", "correct_answer": "4"},
        headers=_headers(admin_token),
    ).json()
    client.post(
        "/assessment/attempts",
        json={"question_id": question["id"], "assessment_type": "retrieval_practice", "learner_response": "wrong", "idempotency_key": str(uuid.uuid4())},
        headers=_headers(student_token),
    )
    evidence = client.get("/assessment/evidence", headers=_headers(student_token)).json()[0]

    response = client.post(
        f"/assessment/evidence/{evidence['id']}/failure-mode",
        json={"failure_mode": "misconception"},
        headers=_headers(student_token),
    )
    assert response.status_code == 403


def test_transfer_variant_relationship_is_stored(client: TestClient, db: Session, admin: tuple[User, str], skill_id: str) -> None:
    _, admin_token = admin
    base = client.post(
        "/assessment/questions",
        json={"skill_id": skill_id, "facet_type": "application", "prompt": "Base item", "correct_answer": "4"},
        headers=_headers(admin_token),
    ).json()
    variant = client.post(
        "/assessment/questions",
        json={
            "skill_id": skill_id,
            "facet_type": "transfer",
            "prompt": "Variant item",
            "correct_answer": "4",
            "source_question_id": base["id"],
            "surface_variation": "different everyday scenario, same relationship",
        },
        headers=_headers(admin_token),
    ).json()
    assert variant["source_question_id"] == base["id"]
    assert variant["surface_variation"] == "different everyday scenario, same relationship"
