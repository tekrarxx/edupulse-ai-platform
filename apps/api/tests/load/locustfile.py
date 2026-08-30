"""Load test for the MVP learning loop (§109/§138 — measurement-driven
performance work, run before any cloud deployment). Not a pytest test —
run directly with Locust, never collected by the pytest suite.

Each simulated user is a genuinely distinct student: `on_start` calls the
real `POST /auth/register` (its own fresh individual tenant, exactly like
a real B2C signup), so this measures the system under many real concurrent
accounts, not one token replayed in a loop — and naturally exercises the
per-user rate limits added in Phase 10 slice 1 exactly as a real traffic
spike would.

Setup (once, before running):
    docker compose exec api python3 scripts/seed_load_test_curriculum.py
    # copy the two printed LOAD_TEST_* values into your shell environment

Run (from the host, against the container's published port):
    pip install locust
    LOAD_TEST_SKILL_ID=... LOAD_TEST_QUESTION_IDS=... \
        locust -f tests/load/locustfile.py --host http://localhost:8000
"""
import os
import random
import uuid

from locust import HttpUser, between, task

_SKILL_ID = os.environ["LOAD_TEST_SKILL_ID"]
_QUESTION_IDS = os.environ["LOAD_TEST_QUESTION_IDS"].split(",")


class StudentUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self) -> None:
        email = f"loadtest-{uuid.uuid4().hex}@example.com"
        response = self.client.post(
            "/auth/register",
            json={"email": email, "password": "correct-horse-battery", "display_name": "Load Test Student"},
            name="/auth/register",
        )
        if response.status_code != 201:
            # A real, expected outcome under a registration burst from one
            # IP (Phase 10 slice 1's per-IP limit on /auth/register) — not
            # a bug in this locustfile. Leave access_token unset; every
            # task below no-ops without one rather than crashing the run.
            self.access_token = None
            return
        self.access_token = response.json()["access_token"]

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    @task(5)
    def submit_attempt(self) -> None:
        if not self.access_token:
            return
        question_id = random.choice(_QUESTION_IDS)
        is_correct_attempt = random.random() < 0.7  # a realistic mixed mastery signal, not uniformly right or wrong
        self.client.post(
            "/assessment/attempts",
            json={
                "question_id": question_id,
                "assessment_type": "formative",
                "learner_response": "4" if is_correct_attempt else "wrong-answer",
                "idempotency_key": str(uuid.uuid4()),
            },
            headers=self._auth_headers(),
            name="/assessment/attempts",
        )

    @task(2)
    def request_decision(self) -> None:
        if not self.access_token:
            return
        self.client.post(
            f"/decisions/next-action?skill_id={_SKILL_ID}",
            headers=self._auth_headers(),
            name="/decisions/next-action",
        )

    @task(3)
    def view_dashboard(self) -> None:
        if not self.access_token:
            return
        self.client.get("/dashboard/student", headers=self._auth_headers(), name="/dashboard/student")
