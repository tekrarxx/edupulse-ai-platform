"""Shared audit-log writer (§131). Any service that performs a permission,
role, tenant, or important-decision change writes through here instead of
constructing `AuditLog` rows itself, so every caller's `action` vocabulary
stays discoverable in one place.
"""
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def record_audit(
    db: Session, *, tenant_id: str, actor_user_id: str | None, action: str, target_type: str, target_id: str
) -> None:
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
        )
    )
