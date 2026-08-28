"""Parent-student and teacher-student links (§81 minor safety).

Only the data model lands in this phase — enough that the schema does not
need retrofitting once invite/consent flows exist. The invite UX, consent
capture, and management API are deliberately deferred (§114): building a full
relationship-management surface before there are curriculum/assessment
entities for it to be useful against would be scope creep ahead of need.
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class TeacherStudentLink(Base):
    __tablename__ = "teacher_student_links"
    __table_args__ = (UniqueConstraint("teacher_user_id", "student_user_id", name="uq_teacher_student"),)

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = uuid_fk("tenants.id")
    teacher_user_id: Mapped[str] = uuid_fk("users.id")
    student_user_id: Mapped[str] = uuid_fk("users.id")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
