"""§113 P2's Definition-of-Done claim, actually demonstrated: "a second
subject (e.g. Chemistry) with zero code changes." MVP-GATE.md flagged this
as "architecturally supported... but not re-demonstrated" — this test
closes that by running assessment, knowledge-state, and Prometheus decision
generation against a real Chemistry skill (scripts/seed_curriculum_chemistry.py),
through the exact same code paths tests/e2e/test_mvp_learning_loop.py
exercises for Physics. No branch anywhere in app/ checks a subject name —
if this test passes, that claim is real, not asserted.
"""
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.tenant import Tenant, TenantType
from app.models.user import Role, User


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_prometheus_loop_works_unmodified_for_a_non_physics_subject(client: TestClient, db: Session) -> None:
    tenant = Tenant(name=f"Chemistry School {uuid.uuid4().hex[:8]}", tenant_type=TenantType.SCHOOL)
    db.add(tenant)
    db.flush()
    admin = User(
        tenant_id=tenant.id,
        email=f"chem-admin-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("irrelevant-for-this-test"),
        display_name="Chem Admin",
        role=Role.SUPER_ADMIN,
    )
    student = User(
        tenant_id=tenant.id,
        email=f"chem-student-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("irrelevant-for-this-test"),
        display_name="Chem Student",
        role=Role.STUDENT,
    )
    db.add_all([admin, student])
    db.commit()
    db.refresh(admin)
    db.refresh(student)
    admin_token, _ = create_access_token(user_id=admin.id, tenant_id=admin.tenant_id, role=admin.role.value)
    student_token, _ = create_access_token(user_id=student.id, tenant_id=student.tenant_id, role=student.role.value)

    # A Chemistry curriculum slice, created through the same generic
    # curriculum API every subject uses — Kimya, not Fizik.
    subject = client.post(
        "/curriculum/subjects", json={"slug": f"kimya-{uuid.uuid4().hex[:6]}", "name": "Kimya"}, headers=_headers(admin_token)
    ).json()
    topic = client.post(
        "/curriculum/topics",
        json={"subject_id": subject["id"], "slug": "kimyasal-baglar", "name": "Kimyasal Bağlar"},
        headers=_headers(admin_token),
    ).json()
    concept = client.post(
        "/curriculum/concepts",
        json={"topic_id": topic["id"], "slug": "iyonik-bag", "name": "İyonik Bağ"},
        headers=_headers(admin_token),
    ).json()
    skill = client.post(
        "/curriculum/skills",
        json={"concept_id": concept["id"], "slug": "iyonik-bag-olusumu", "name": "İyonik Bağ Oluşumu"},
        headers=_headers(admin_token),
    ).json()
    skill_id = skill["id"]

    for _ in range(5):
        question = client.post(
            "/assessment/questions",
            json={
                "skill_id": skill_id,
                "facet_type": "application",
                "prompt": "Na ve Cl arasında hangi iyon türü oluşur?",
                "correct_answer": "iyonik",
            },
            headers=_headers(admin_token),
        ).json()
        attempt = client.post(
            "/assessment/attempts",
            json={
                "question_id": question["id"],
                "assessment_type": "formative",
                "learner_response": "iyonik",
                "idempotency_key": str(uuid.uuid4()),
            },
            headers=_headers(student_token),
        )
        assert attempt.status_code == 201

    ks_response = client.get("/knowledge-state", params={"skill_id": skill_id}, headers=_headers(student_token))
    assert ks_response.status_code == 200
    application_state = next(row for row in ks_response.json() if row["facet_type"] == "application")
    assert application_state["confidence_label"] == "high_confidence"
    assert application_state["evidence_count"] == 5

    decision_response = client.post("/decisions/next-action", params={"skill_id": skill_id}, headers=_headers(student_token))
    assert decision_response.status_code == 201
    decision = decision_response.json()
    assert decision["authorization_result"] == "allowed"
    assert len(decision["candidate_actions"]) == 12
    assert decision["policy_version"] == "pde-policy-v1"
    assert decision["model_version"] == "bayesian-beta-binomial-v1"
