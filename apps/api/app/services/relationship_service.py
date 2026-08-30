"""Staff-managed relationship/consent operations (§81, §16 — routes stay
thin). Both functions here are administrative attestations: a staff member
records a fact (a student's date of birth, that a guardian's consent was
obtained) that was already established through some external, out-of-band
process — a signed enrollment form, a phone call, an in-person conversation.
Neither function collects consent itself; that self-service flow is still
deferred (see app/models/relationship.py module docstring).
"""
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models.relationship import ParentStudentLink
from app.models.user import Role, User
from app.services.audit_service import record_audit


class RelationshipError(Exception):
    pass


class UserNotFound(RelationshipError):
    pass


class ParentOrStudentNotFound(RelationshipError):
    pass


class InvalidRoleForLink(RelationshipError):
    pass


class LinkAlreadyExists(RelationshipError):
    pass


def set_date_of_birth(db: Session, *, tenant_id: str, actor_user_id: str, target_user_id: str, date_of_birth: date) -> User:
    user = db.get(User, target_user_id)
    if user is None or user.tenant_id != tenant_id:
        raise UserNotFound()

    user.date_of_birth = date_of_birth
    record_audit(
        db,
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        action="user.date_of_birth_set",
        target_type="user",
        target_id=user.id,
    )
    db.commit()
    db.refresh(user)
    return user


def create_parent_link(
    db: Session,
    *,
    tenant_id: str,
    actor_user_id: str,
    parent_user_id: str,
    student_user_id: str,
    consent_given: bool,
) -> ParentStudentLink:
    parent = db.get(User, parent_user_id)
    student = db.get(User, student_user_id)
    if parent is None or parent.tenant_id != tenant_id or student is None or student.tenant_id != tenant_id:
        raise ParentOrStudentNotFound()
    if parent.role != Role.PARENT or student.role != Role.STUDENT:
        raise InvalidRoleForLink()

    existing = (
        db.query(ParentStudentLink)
        .filter(ParentStudentLink.parent_user_id == parent_user_id, ParentStudentLink.student_user_id == student_user_id)
        .first()
    )
    if existing is not None:
        raise LinkAlreadyExists()

    link = ParentStudentLink(
        tenant_id=tenant_id,
        parent_user_id=parent_user_id,
        student_user_id=student_user_id,
        consent_given_at=datetime.now(timezone.utc) if consent_given else None,
    )
    db.add(link)
    db.flush()

    record_audit(
        db,
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        action="parent_link.created_with_consent" if consent_given else "parent_link.created",
        target_type="parent_student_link",
        target_id=link.id,
    )
    db.commit()
    db.refresh(link)
    return link
