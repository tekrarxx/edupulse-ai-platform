import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.ai.providers.base import AIProvider, GenerationRequest, GenerationResult, ProviderTimeout
from app.api.deps import get_ai_provider
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.ai_usage import AIUsageRecord
from app.models.tenant import Tenant, TenantType
from app.models.user import Role, User


class _FakeProvider(AIProvider):
    def __init__(self, responses: list) -> None:
        self.provider_name = "fake"
        self.model_name = "fake-model-v1"
        self._responses = list(responses)

    def generate(self, request: GenerationRequest) -> GenerationResult:
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return GenerationResult(raw_text=item, input_tokens=10, output_tokens=20, latency_ms=5)


_VALID_JSON = json.dumps({"explanation": "A clear explanation.", "key_points": ["point one"]})


@pytest.fixture
def override_ai_provider():
    def _override(fake_provider: AIProvider) -> None:
        app.dependency_overrides[get_ai_provider] = lambda: fake_provider

    yield _override
    app.dependency_overrides.pop(get_ai_provider, None)


def _seed_user(db: Session, *, role: Role) -> tuple[User, str]:
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
def skill_id(client: TestClient, db: Session) -> str:
    admin, admin_token = _seed_user(db, role=Role.SUPER_ADMIN)
    subject = client.post(
        "/curriculum/subjects", json={"slug": f"s-{uuid.uuid4().hex[:8]}", "name": "Test"}, headers=_headers(admin_token)
    ).json()
    topic = client.post(
        "/curriculum/topics", json={"subject_id": subject["id"], "slug": "t", "name": "T"}, headers=_headers(admin_token)
    ).json()
    concept = client.post(
        "/curriculum/concepts", json={"topic_id": topic["id"], "slug": "c", "name": "C"}, headers=_headers(admin_token)
    ).json()
    skill = client.post(
        "/curriculum/skills",
        json={"concept_id": concept["id"], "slug": "sk", "name": "Newton's Second Law", "description": "F = m*a"},
        headers=_headers(admin_token),
    ).json()
    return skill["id"]


def test_student_can_request_explanation(client: TestClient, db: Session, skill_id: str, override_ai_provider) -> None:
    override_ai_provider(_FakeProvider([_VALID_JSON]))
    _, student_token = _seed_user(db, role=Role.STUDENT)

    response = client.post("/ai/explanations", json={"skill_id": skill_id}, headers=_headers(student_token))

    assert response.status_code == 200
    body = response.json()
    assert body["skill_id"] == skill_id
    assert body["explanation"] == "A clear explanation."
    assert body["key_points"] == ["point one"]
    assert body["provider"] == "fake"
    assert body["prompt_name"] == "skill_explanation"
    assert body["prompt_version"] == "v1"


def test_unknown_skill_returns_404(client: TestClient, db: Session, override_ai_provider) -> None:
    override_ai_provider(_FakeProvider([_VALID_JSON]))
    _, student_token = _seed_user(db, role=Role.STUDENT)

    response = client.post("/ai/explanations", json={"skill_id": str(uuid.uuid4())}, headers=_headers(student_token))
    assert response.status_code == 404


def test_malformed_provider_output_returns_502(client: TestClient, db: Session, skill_id: str, override_ai_provider) -> None:
    override_ai_provider(_FakeProvider(["not json"]))
    _, student_token = _seed_user(db, role=Role.STUDENT)

    response = client.post("/ai/explanations", json={"skill_id": skill_id}, headers=_headers(student_token))
    assert response.status_code == 502


def test_provider_unavailable_returns_503(client: TestClient, db: Session, skill_id: str, override_ai_provider) -> None:
    override_ai_provider(_FakeProvider([ProviderTimeout("simulated")]))
    _, student_token = _seed_user(db, role=Role.STUDENT)

    response = client.post("/ai/explanations", json={"skill_id": skill_id}, headers=_headers(student_token))
    assert response.status_code == 503


def test_successful_call_persists_usage_record(client: TestClient, db: Session, skill_id: str, override_ai_provider) -> None:
    override_ai_provider(_FakeProvider([_VALID_JSON]))
    student, student_token = _seed_user(db, role=Role.STUDENT)

    response = client.post("/ai/explanations", json={"skill_id": skill_id}, headers=_headers(student_token))
    assert response.status_code == 200

    records = db.query(AIUsageRecord).filter(AIUsageRecord.actor_user_id == student.id).all()
    assert len(records) == 1
    assert records[0].success is True
    assert records[0].capability.value == "skill_explanation"
    assert records[0].tenant_id == student.tenant_id
