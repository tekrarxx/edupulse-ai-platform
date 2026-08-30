import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._types import uuid_fk, uuid_pk, utcnow


class Role(str, enum.Enum):
    """§53. One role per user in this phase (see ADR-011) — a user acting in
    two capacities (e.g. a parent who is also a teacher) needs two accounts
    until multi-role support is explicitly designed."""

    SUPER_ADMIN = "SUPER_ADMIN"
    TENANT_ADMIN = "TENANT_ADMIN"
    SCHOOL_ADMIN = "SCHOOL_ADMIN"
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"
    PARENT = "PARENT"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = uuid_fk("tenants.id")
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="user_role", native_enum=False, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # §81 minor-safety input. Nullable and not backfilled for existing rows
    # (§107 additive migration) — app/services/authorization_service.py
    # treats an unknown date of birth as "cannot verify minor status", never
    # as an assumed adult or an assumed minor (§105: no fabricated fact).
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class UserSession(Base):
    """A live refresh-token session. Existence of a row = a session that can
    still be used to mint access tokens; `revoked_at` set = dead (§78 secure
    token handling — logout must be a real revocation, not just "forget the
    cookie and hope")."""

    __tablename__ = "user_sessions"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = uuid_fk("users.id")
    refresh_token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
