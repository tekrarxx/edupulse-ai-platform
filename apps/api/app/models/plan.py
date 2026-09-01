"""SaaS plan/entitlement domain (§59-§61, Roadmap Stage C — deliberately
narrow scope, not full billing: see docs/adr/ADR-013 Addendum 2's reasoning
pattern applied here too — build the smallest real thing a second real
pricing decision could hang off of, not a speculative general framework).

`Plan` -> `Entitlement` -> `Tenant.plan_id` -> feature access (§60). Pricing
itself (§63 "pricing MUST remain configurable, not hard-coded") lives in
`Entitlement.value` rows, never as a literal in application code — a new
tier or a changed limit is a data change, not a deploy.

Billing (invoices, payments, subscriptions) is explicitly out of scope
here — §116 does not require it for the MVP, and Prometheus/learning logic
must never know which plan a tenant is on (§95 "Prometheus must not know
whether a learner is Free/Pro/Enterprise" — this module is consumed only
by non-Prometheus services, e.g. app/services/explanation_service.py).
"""
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._types import uuid_fk, uuid_pk, utcnow


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[str] = uuid_pk()
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class EntitlementKey(str, enum.Enum):
    """Closed vocabulary, extensible — grows only when a real feature needs
    gating (same discipline as `AIUsageCapability`, ADR-015 Assumption 1).
    A key with no `Entitlement` row for a given plan means "not limited,"
    never a fabricated default limit (§105)."""

    AI_EXPLANATIONS_MONTHLY_LIMIT = "ai_explanations_monthly_limit"
    # Total User rows (any role) in a tenant — gates admin-initiated
    # enrollment (POST /auth/tenant/users), the second real feature this
    # entitlement system gates (ADR-016 Falsifiability trigger 1).
    MAX_TENANT_USERS = "max_tenant_users"


class Entitlement(Base):
    __tablename__ = "entitlements"
    __table_args__ = (UniqueConstraint("plan_id", "key", name="uq_entitlement_plan_key"),)

    id: Mapped[str] = uuid_pk()
    plan_id: Mapped[str] = uuid_fk("plans.id")
    key: Mapped[EntitlementKey] = mapped_column(
        Enum(EntitlementKey, name="entitlement_key", native_enum=False, values_callable=lambda ec: [e.value for e in ec]),
        nullable=False,
    )
    # Null = unlimited for this key on this plan — an absent row means the
    # same thing (§60's "no restriction configured"), a row exists mainly
    # so a plan can be introspected/listed even when a key is unlimited.
    value: Mapped[int | None] = mapped_column(Integer, nullable=True)
