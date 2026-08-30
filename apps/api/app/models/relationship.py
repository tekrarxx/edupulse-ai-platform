"""Parent-student and teacher-student links (§81 minor safety).

`ParentStudentLink.consent_given_at` and the staff-only
`POST /auth/tenant/parent-links` endpoint (Phase 10) close the "consent data
model does not exist yet" gap `authorization_service.py` used to document —
an admin records that consent was obtained through some external,
already-verified process (a signed form, a phone call, an in-person
enrollment conversation), the same way a real school's office handles it.
A self-service parent-initiated invite/consent UX is still deliberately
deferred (§114): building a full relationship-management surface before a
pilot needs it would be scope creep ahead of need.
"""
from datetime import datetime

from sqlalchemy import DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._types import uuid_fk, uuid_pk, utcnow


class ParentStudentLink(Base):
    __tablename__ = "parent_student_links"
    __table_args__ = (UniqueConstraint("parent_user_id", "student_user_id", name="uq_parent_student"),)

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = uuid_fk("tenants.id")
    parent_user_id: Mapped[str] = uuid_fk("users.id")
    student_user_id: Mapped[str] = uuid_fk("users.id")
    # Null = link exists but consent has not been recorded yet. Set once, at
    # creation or via a later grant — never cleared by application code
    # (a withdrawal is a policy decision this phase does not implement, not
    # a silent field reset).
    consent_given_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class TeacherStudentLink(Base):
    __tablename__ = "teacher_student_links"
    __table_args__ = (UniqueConstraint("teacher_user_id", "student_user_id", name="uq_teacher_student"),)

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = uuid_fk("tenants.id")
    teacher_user_id: Mapped[str] = uuid_fk("users.id")
    student_user_id: Mapped[str] = uuid_fk("users.id")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
