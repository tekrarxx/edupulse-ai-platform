"""§81 consent/age administration: staff-only date-of-birth recording and
parent-link/consent creation (app/services/relationship_service.py).
"""
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.audit_log import AuditLog
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


# --- date-of-birth ---


def test_admin_sets_student_date_of_birth(client: TestClient, db: Session) -> None:
    tenant = Tenant(name="T", tenant_type=TenantType.SCHOOL)
    db.add(tenant)
    db.flush()
    db.commit()
    student, _ = _seed_user(db, role=Role.STUDENT, tenant=tenant)
    _, admin_token = _seed_user(db, role=Role.SUPER_ADMIN, tenant=tenant)

    response = client.post(
        f"/auth/tenant/users/{student.id}/date-of-birth", json={"date_of_birth": "2012-01-01"}, headers=_headers(admin_token)
    )
    assert response.status_code == 200
    assert response.json()["date_of_birth"] == "2012-01-01"

    audit_row = db.query(AuditLog).filter(AuditLog.target_id == student.id, AuditLog.action == "user.date_of_birth_set").first()
    assert audit_row is not None


def test_teacher_cannot_set_date_of_birth(client: TestClient, db: Session) -> None:
    tenant = Tenant(name="T", tenant_type=TenantType.SCHOOL)
    db.add(tenant)
    db.flush()
    db.commit()
    student, _ = _seed_user(db, role=Role.STUDENT, tenant=tenant)
    _, teacher_token = _seed_user(db, role=Role.TEACHER, tenant=tenant)

    response = client.post(
        f"/auth/tenant/users/{student.id}/date-of-birth", json={"date_of_birth": "2012-01-01"}, headers=_headers(teacher_token)
    )
    assert response.status_code == 403


def test_admin_cannot_set_date_of_birth_for_another_tenants_user(client: TestClient, db: Session) -> None:
    """§52."""
    student, _ = _seed_user(db, role=Role.STUDENT)  # own (different) tenant
    _, admin_token = _seed_user(db, role=Role.SUPER_ADMIN)  # a different tenant again

    response = client.post(
        f"/auth/tenant/users/{student.id}/date-of-birth", json={"date_of_birth": "2012-01-01"}, headers=_headers(admin_token)
    )
    assert response.status_code == 404


# --- parent links / consent ---


def test_admin_creates_parent_link_with_consent(client: TestClient, db: Session) -> None:
    tenant = Tenant(name="T", tenant_type=TenantType.SCHOOL)
    db.add(tenant)
    db.flush()
    db.commit()
    student, _ = _seed_user(db, role=Role.STUDENT, tenant=tenant)
    parent, _ = _seed_user(db, role=Role.PARENT, tenant=tenant)
    _, admin_token = _seed_user(db, role=Role.SCHOOL_ADMIN, tenant=tenant)

    response = client.post(
        "/auth/tenant/parent-links",
        json={"parent_user_id": parent.id, "student_user_id": student.id, "consent_given": True},
        headers=_headers(admin_token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["consent_given_at"] is not None

    link = db.query(ParentStudentLink).filter(ParentStudentLink.id == body["id"]).first()
    assert link.consent_given_at is not None

    audit_row = db.query(AuditLog).filter(AuditLog.target_id == body["id"], AuditLog.action == "parent_link.created_with_consent").first()
    assert audit_row is not None


def test_admin_creates_parent_link_without_consent(client: TestClient, db: Session) -> None:
    tenant = Tenant(name="T", tenant_type=TenantType.SCHOOL)
    db.add(tenant)
    db.flush()
    db.commit()
    student, _ = _seed_user(db, role=Role.STUDENT, tenant=tenant)
    parent, _ = _seed_user(db, role=Role.PARENT, tenant=tenant)
    _, admin_token = _seed_user(db, role=Role.SCHOOL_ADMIN, tenant=tenant)

    response = client.post(
        "/auth/tenant/parent-links",
        json={"parent_user_id": parent.id, "student_user_id": student.id, "consent_given": False},
        headers=_headers(admin_token),
    )
    assert response.status_code == 201
    assert response.json()["consent_given_at"] is None


def test_duplicate_parent_link_rejected(client: TestClient, db: Session) -> None:
    tenant = Tenant(name="T", tenant_type=TenantType.SCHOOL)
    db.add(tenant)
    db.flush()
    db.commit()
    student, _ = _seed_user(db, role=Role.STUDENT, tenant=tenant)
    parent, _ = _seed_user(db, role=Role.PARENT, tenant=tenant)
    _, admin_token = _seed_user(db, role=Role.SCHOOL_ADMIN, tenant=tenant)

    payload = {"parent_user_id": parent.id, "student_user_id": student.id, "consent_given": False}
    first = client.post("/auth/tenant/parent-links", json=payload, headers=_headers(admin_token))
    assert first.status_code == 201
    second = client.post("/auth/tenant/parent-links", json=payload, headers=_headers(admin_token))
    assert second.status_code == 409


def test_parent_link_rejects_wrong_roles(client: TestClient, db: Session) -> None:
    tenant = Tenant(name="T", tenant_type=TenantType.SCHOOL)
    db.add(tenant)
    db.flush()
    db.commit()
    teacher, _ = _seed_user(db, role=Role.TEACHER, tenant=tenant)
    student, _ = _seed_user(db, role=Role.STUDENT, tenant=tenant)
    _, admin_token = _seed_user(db, role=Role.SCHOOL_ADMIN, tenant=tenant)

    response = client.post(
        "/auth/tenant/parent-links",
        json={"parent_user_id": teacher.id, "student_user_id": student.id, "consent_given": True},
        headers=_headers(admin_token),
    )
    assert response.status_code == 400


def test_teacher_cannot_create_parent_link(client: TestClient, db: Session) -> None:
    tenant = Tenant(name="T", tenant_type=TenantType.SCHOOL)
    db.add(tenant)
    db.flush()
    db.commit()
    student, _ = _seed_user(db, role=Role.STUDENT, tenant=tenant)
    parent, _ = _seed_user(db, role=Role.PARENT, tenant=tenant)
    _, teacher_token = _seed_user(db, role=Role.TEACHER, tenant=tenant)

    response = client.post(
        "/auth/tenant/parent-links",
        json={"parent_user_id": parent.id, "student_user_id": student.id, "consent_given": True},
        headers=_headers(teacher_token),
    )
    assert response.status_code == 403


def test_parent_link_across_tenants_rejected(client: TestClient, db: Session) -> None:
    """§52: a staff member cannot link a parent/student that belong to a different tenant."""
    student, _ = _seed_user(db, role=Role.STUDENT)  # tenant A
    parent, _ = _seed_user(db, role=Role.PARENT)  # tenant B
    _, admin_token = _seed_user(db, role=Role.SCHOOL_ADMIN)  # tenant C

    response = client.post(
        "/auth/tenant/parent-links",
        json={"parent_user_id": parent.id, "student_user_id": student.id, "consent_given": True},
        headers=_headers(admin_token),
    )
    assert response.status_code == 404
