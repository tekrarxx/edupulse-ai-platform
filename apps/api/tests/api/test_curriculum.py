import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.tenant import Tenant, TenantType
from app.models.user import Role, User


def _seed_user_token(db: Session, *, role: Role) -> str:
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
    return token


@pytest.fixture
def admin_headers(db: Session) -> dict:
    return {"Authorization": f"Bearer {_seed_user_token(db, role=Role.SUPER_ADMIN)}"}


@pytest.fixture
def student_headers(db: Session) -> dict:
    return {"Authorization": f"Bearer {_seed_user_token(db, role=Role.STUDENT)}"}


def _unique_slug(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def test_unauthenticated_read_is_rejected(client: TestClient) -> None:
    response = client.get("/curriculum/subjects")
    assert response.status_code == 401


def test_student_can_read_but_not_write(client: TestClient, admin_headers: dict, student_headers: dict) -> None:
    create_response = client.post("/curriculum/subjects", json={"slug": _unique_slug("fizik"), "name": "Fizik"}, headers=admin_headers)
    assert create_response.status_code == 201

    read_response = client.get("/curriculum/subjects", headers=student_headers)
    assert read_response.status_code == 200

    write_response = client.post("/curriculum/subjects", json={"slug": _unique_slug("kimya"), "name": "Kimya"}, headers=student_headers)
    assert write_response.status_code == 403


def test_duplicate_subject_slug_rejected(client: TestClient, admin_headers: dict) -> None:
    slug = _unique_slug("fizik")
    first = client.post("/curriculum/subjects", json={"slug": slug, "name": "Fizik"}, headers=admin_headers)
    assert first.status_code == 201
    second = client.post("/curriculum/subjects", json={"slug": slug, "name": "Fizik Tekrar"}, headers=admin_headers)
    assert second.status_code == 409


def test_topic_requires_existing_subject(client: TestClient, admin_headers: dict) -> None:
    response = client.post(
        "/curriculum/topics",
        json={"subject_id": "does-not-exist", "slug": "mekanik", "name": "Mekanik"},
        headers=admin_headers,
    )
    assert response.status_code == 404


def _build_skill(client: TestClient, admin_headers: dict, *, subject_name: str) -> str:
    """Walks Subject -> Topic -> Concept -> Skill using only the generic
    curriculum endpoints — the same call sequence works for any subject."""
    subject = client.post(
        "/curriculum/subjects", json={"slug": _unique_slug(subject_name.lower()), "name": subject_name}, headers=admin_headers
    ).json()
    topic = client.post(
        "/curriculum/topics",
        json={"subject_id": subject["id"], "slug": _unique_slug("topic"), "name": "Test Topic"},
        headers=admin_headers,
    ).json()
    concept = client.post(
        "/curriculum/concepts",
        json={"topic_id": topic["id"], "slug": _unique_slug("concept"), "name": "Test Concept"},
        headers=admin_headers,
    ).json()
    skill = client.post(
        "/curriculum/skills",
        json={"concept_id": concept["id"], "slug": _unique_slug("skill"), "name": "Test Skill", "grade_level": 9},
        headers=admin_headers,
    ).json()
    return skill["id"]


def test_full_hierarchy_round_trips_for_physics(client: TestClient, admin_headers: dict) -> None:
    skill_id = _build_skill(client, admin_headers, subject_name="Fizik")

    facet_response = client.post(
        "/curriculum/skills/{}/facets".format(skill_id),
        json={"facet_type": "application", "description": "Verilen değerlerle ivmeyi hesaplar."},
        headers=admin_headers,
    )
    assert facet_response.status_code == 201

    detail = client.get(f"/curriculum/skills/{skill_id}", headers=admin_headers).json()
    assert detail["facets"][0]["facet_type"] == "application"


def test_second_subject_requires_no_code_change(client: TestClient, admin_headers: dict) -> None:
    """§2 / Phase 3 DoD: adding Chemistry uses the exact same generic
    endpoints as Physics — nothing here is Physics-specific."""
    physics_skill_id = _build_skill(client, admin_headers, subject_name="Fizik")
    chemistry_skill_id = _build_skill(client, admin_headers, subject_name="Kimya")

    assert physics_skill_id != chemistry_skill_id
    for skill_id in (physics_skill_id, chemistry_skill_id):
        response = client.get(f"/curriculum/skills/{skill_id}", headers=admin_headers)
        assert response.status_code == 200


def test_prerequisite_between_two_skills_via_api(client: TestClient, admin_headers: dict) -> None:
    skill_a = _build_skill(client, admin_headers, subject_name="Fizik")
    skill_b = _build_skill(client, admin_headers, subject_name="Fizik")

    response = client.post(
        f"/curriculum/skills/{skill_a}/prerequisites",
        json={"prerequisite_skill_id": skill_b},
        headers=admin_headers,
    )
    assert response.status_code == 201

    cycle_response = client.post(
        f"/curriculum/skills/{skill_b}/prerequisites",
        json={"prerequisite_skill_id": skill_a},
        headers=admin_headers,
    )
    assert cycle_response.status_code == 400
    assert cycle_response.json()["detail"] == "prerequisite_would_create_a_cycle"
