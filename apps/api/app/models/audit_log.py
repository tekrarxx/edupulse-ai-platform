from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._types import uuid_fk, uuid_pk, utcnow


class AuditLog(Base):
    """Append-only record of permission, role, and tenant changes (§131).
    Nothing updates or deletes rows in this table from application code —
    enforced by convention here; full DB-level append-only enforcement is
    scoped to Phase 4's event log (§40) which generalizes this pattern."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = uuid_fk("tenants.id")
    actor_user_id: Mapped[str | None] = uuid_fk("users.id", nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
