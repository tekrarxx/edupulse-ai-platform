"""AI usage accounting (§45, §48, §65, §139, ADR-015 §5). Written exactly
once per AIGateway.generate() call, success or failure, by
app/ai/gateway.py — the only code path that creates these rows.
"""
import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._types import uuid_fk, uuid_pk, utcnow


def _enum_column(enum_cls, name: str):
    return Enum(enum_cls, name=name, native_enum=False, values_callable=lambda ec: [e.value for e in ec])


class AIUsageCapability(str, enum.Enum):
    """Closed vocabulary — grows as real capabilities ship, never
    pre-populated speculatively (ADR-015, Assumption 1)."""

    SKILL_EXPLANATION = "skill_explanation"


class AIUsageRecord(Base):
    __tablename__ = "ai_usage_records"

    id: Mapped[str] = uuid_pk()
    # Every caller reaches the gateway through an authenticated,
    # tenant-scoped user in this phase — non-nullable (ADR-015, Assumption 4).
    tenant_id: Mapped[str] = uuid_fk("tenants.id")
    actor_user_id: Mapped[str] = uuid_fk("users.id")
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    capability: Mapped[AIUsageCapability] = mapped_column(
        _enum_column(AIUsageCapability, "ai_usage_capability"), nullable=False
    )
    prompt_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False)
    # Ollama's own tokenizer counts — approximate, not billing-grade (§1).
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # A short class-name-level reason only — never raw provider/model output
    # (§5: don't leak internals into an unbounded column).
    error_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
