import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._types import uuid_pk, utcnow


class TenantType(str, enum.Enum):
    """§50. The initial tenant taxonomy — extend, never repurpose a value."""

    INDIVIDUAL = "individual"
    TEACHER = "teacher"
    SCHOOL = "school"
    COURSE_CENTER = "course_center"
    ENTERPRISE = "enterprise"


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = uuid_pk()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    tenant_type: Mapped[TenantType] = mapped_column(
        # values_callable: SQLAlchemy's Enum type stores the Python enum
        # MEMBER NAME by default (e.g. "INDIVIDUAL"), not its `.value`
        # ("individual") — without this override it would violate the
        # lowercase CHECK constraint from alembic/versions/0002_identity_tenancy.py.
        Enum(TenantType, name="tenant_type", native_enum=False, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )
    # §96 feature flag for PDE policy rollout (ADR-013 "Shadow Mode"): when
    # true, every decision generated for this tenant is stored with
    # is_shadow=True regardless of who requested it — a hard floor a staff
    # caller's per-request `mode` cannot override.
    pde_shadow_mode_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
