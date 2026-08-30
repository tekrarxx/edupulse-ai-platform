"""The §115 MVP loop, automated (§86 "e2e" layer).

Reproduces `docs/audit/MVP-GATE.md`'s §1 manual trace as one real,
CI-repeatable pytest test: real HTTP calls through the FastAPI `TestClient`
against a real Postgres-backed `db` fixture (the same fixtures every other
API test uses — no e2e-specific harness), asserting the exact same
milestones the MVP Gate report verified by hand. Closes the gap that
report's §2 flagged: "this codebase's 'E2E' so far has been the manual HTTP
trace... not an automated suite."

One golden-path journey, deliberately — this is not meant to replace the
targeted unit/API/security tests elsewhere; it is meant to prove the whole
chain still connects end to end after any future change.
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.retention import RetentionCheckpoint
from app.models.tenant import Tenant, TenantType
from app.models.user import Role, User


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_full_mvp_learning_loop_student_to_retention_falsification(client: TestClient, db: Session) -> None:
    # --- Setup: a real school tenant, a real admin (seeded directly — no
    # self-service path creates non-STUDENT accounts, by design, ADR-011),
    # and a real student enrolled through the actual admin-enrollment API
    # (not a DB script) added in this same roadmap stage.
    tenant = Tenant(name=f"MVP Loop School {uuid.uuid4().hex[:8]}", tenant_type=TenantType.SCHOOL)
    db.add(tenant)
    db.flush()
    admin = User(
        tenant_id=tenant.id,
        email=f"mvp-admin-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("irrelevant-for-this-test"),
        display_name="MVP Admin",
        role=Role.SUPER_ADMIN,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    admin_token, _ = create_access_token(user_id=admin.id, tenant_id=admin.tenant_id, role=admin.role.value)

    student_email = f"mvp-student-{uuid.uuid4().hex[:8]}@example.com"
    enroll_response = client.post(
        "/auth/tenant/users",
        json={"email": student_email, "password": "correct-horse-battery", "display_name": "Fizik Öğrencisi", "role": "STUDENT"},
        headers=_headers(admin_token),
    )
    assert enroll_response.status_code == 201, enroll_response.text
    student_id = enroll_response.json()["id"]
    login_response = client.post("/auth/login", json={"email": student_email, "password": "correct-horse-battery"})
    assert login_response.status_code == 200
    student_token = login_response.json()["access_token"]

    # --- Curriculum: Fizik → Mekanik → Kuvvet → Newton'un İkinci Yasası,
    # mirroring the MVP Gate report's real seeded slice.
    subject = client.post(
        "/curriculum/subjects", json={"slug": f"fizik-{uuid.uuid4().hex[:6]}", "name": "Fizik"}, headers=_headers(admin_token)
    ).json()
    topic = client.post(
        "/curriculum/topics",
        json={"subject_id": subject["id"], "slug": "mekanik", "name": "Mekanik"},
        headers=_headers(admin_token),
    ).json()
    concept = client.post(
        "/curriculum/concepts",
        json={"topic_id": topic["id"], "slug": "kuvvet", "name": "Kuvvet"},
        headers=_headers(admin_token),
    ).json()
    skill = client.post(
        "/curriculum/skills",
        json={"concept_id": concept["id"], "slug": "newton-2", "name": "Newton'un İkinci Hareket Yasası"},
        headers=_headers(admin_token),
    ).json()
    skill_id = skill["id"]

    # --- Step 1: Assessment -> Observation -> Evidence (§21-§23). Five real
    # correct APPLICATION attempts, exactly the MVP Gate trace's shape.
    first_application_question_id = None
    for _ in range(5):
        question = client.post(
            "/assessment/questions",
            json={"skill_id": skill_id, "facet_type": "application", "prompt": "F = m*a, m=2kg, a=3m/s^2, F=?", "correct_answer": "6"},
            headers=_headers(admin_token),
        ).json()
        first_application_question_id = first_application_question_id or question["id"]
        attempt_response = client.post(
            "/assessment/attempts",
            json={
                "question_id": question["id"],
                "assessment_type": "formative",
                "learner_response": "6",
                "idempotency_key": str(uuid.uuid4()),
            },
            headers=_headers(student_token),
        )
        assert attempt_response.status_code == 201

    # --- Step 2: Knowledge State (Phase 5, ADR-012) — facet independence:
    # only APPLICATION (the facet with real evidence) should have moved.
    ks_response = client.get("/knowledge-state", params={"skill_id": skill_id}, headers=_headers(student_token))
    assert ks_response.status_code == 200
    states = {row["facet_type"]: row for row in ks_response.json()}
    assert states["application"]["confidence_label"] == "high_confidence"
    assert states["application"]["mastery_probability"] > 0.75
    assert states["application"]["evidence_count"] == 5
    for facet in ("recognition", "recall", "transfer", "retention"):
        assert states[facet]["confidence_label"] == "insufficient_evidence"

    # --- Step 3: Prometheus Decision (Phase 6, ADR-013) — the same
    # deterministic scoring the MVP Gate report observed by hand: high
    # APPLICATION mastery with no TRANSFER evidence yet selects transfer_task.
    decision_response = client.post(
        "/decisions/next-action", params={"skill_id": skill_id}, headers=_headers(student_token)
    )
    assert decision_response.status_code == 201
    decision = decision_response.json()
    assert decision["selected_action"] == "transfer_task"
    assert decision["authorization_result"] == "allowed"
    assert len(decision["candidate_actions"]) == 12
    assert "high_mastery_application" in decision["reason_codes"]

    get_decision = client.get(f"/decisions/{decision['id']}", headers=_headers(student_token))
    assert get_decision.status_code == 200
    assert get_decision.json()["selected_action"] == "transfer_task"

    history = client.get("/decisions", params={"skill_id": skill_id}, headers=_headers(student_token)).json()
    assert any(d["id"] == decision["id"] for d in history)

    # --- Step 4: Retention checkpoints auto-scheduled (Phase 7, ADR-014) —
    # created automatically by the 5th attempt's evaluation, no extra call.
    checkpoints = client.get(
        "/retention/checkpoints", params={"skill_id": skill_id, "student_id": student_id}, headers=_headers(admin_token)
    ).json()
    assert sorted(c["checkpoint_days"] for c in checkpoints) == [14, 28]
    for checkpoint in checkpoints:
        assert checkpoint["status"] == "pending"
        assert checkpoint["hypothesis"]["verdict"] == "pending"
        assert checkpoint["hypothesis"]["predicted_confidence_label"] == "high_confidence"

    # --- Step 5: Transfer task, answered incorrectly — an explicit
    # surface-varied sibling of the first application question (§29:
    # `source_question_id`/`surface_variation`, ADR-014's transfer-variant
    # edge, not just a shared skill_id + TRANSFER tag).
    transfer_question = client.post(
        "/assessment/questions",
        json={
            "skill_id": skill_id,
            "facet_type": "transfer",
            "prompt": "F = m*a, sürtünme dahil, m=2kg, a=3m/s^2, sürtünme kuvveti=1N, F=?",
            "correct_answer": "7",
            "source_question_id": first_application_question_id,
            "surface_variation": "friction_added",
        },
        headers=_headers(admin_token),
    ).json()
    transfer_attempt = client.post(
        "/assessment/attempts",
        json={
            "question_id": transfer_question["id"],
            "assessment_type": "formative",
            "learner_response": "wrong-answer",
            "idempotency_key": str(uuid.uuid4()),
        },
        headers=_headers(student_token),
    )
    assert transfer_attempt.status_code == 201

    evidence_rows = client.get("/assessment/evidence", headers=_headers(student_token)).json()
    transfer_evidence = next(e for e in evidence_rows if e["facet_type"] == "transfer")
    assert transfer_evidence["polarity"] == "negative"
    assert transfer_evidence["failure_mode"] == "transfer_failure"

    # --- Step 6: Delayed retention completion + falsification verdict.
    # No scheduler runs inside a test process (the real one is n8n, Phase
    # 10 — infrastructure/n8n/workflows/retention-checkpoint-scheduler.json;
    # exercising an external cron system from a unit-style test would not
    # be testing this codebase's own logic) — simulate elapsed time exactly
    # as the MVP Gate report's manual trace did, by moving `scheduled_for`
    # into the past directly.
    checkpoint_14d = db.query(RetentionCheckpoint).filter(
        RetentionCheckpoint.student_user_id == student_id, RetentionCheckpoint.checkpoint_days == 14
    ).one()
    checkpoint_14d.scheduled_for = datetime.now(timezone.utc) - timedelta(days=1)
    db.commit()

    due = client.get("/retention/checkpoints/due", headers=_headers(admin_token)).json()
    assert any(c["id"] == checkpoint_14d.id for c in due)

    delayed_question = client.post(
        "/assessment/questions",
        json={"skill_id": skill_id, "facet_type": "application", "prompt": "F = m*a, m=4kg, a=2m/s^2, F=?", "correct_answer": "8"},
        headers=_headers(admin_token),
    ).json()
    complete_response = client.post(
        f"/retention/checkpoints/{checkpoint_14d.id}/complete",
        json={"question_id": delayed_question["id"], "learner_response": "8", "idempotency_key": str(uuid.uuid4())},
        headers=_headers(admin_token),
    )
    assert complete_response.status_code == 200
    completed = complete_response.json()
    assert completed["status"] == "completed"
    assert completed["retention_estimate"] is not None
    assert completed["hypothesis"]["actual_is_correct"] is True
    assert completed["hypothesis"]["verdict"] == "supported"

    # The full §115 loop, on real persistent data, through real HTTP calls:
    # Student -> Skill -> Assessment -> Observation -> Evidence ->
    # Knowledge State -> Prometheus Decision -> Transfer -> Retention ->
    # Falsification verdict.
