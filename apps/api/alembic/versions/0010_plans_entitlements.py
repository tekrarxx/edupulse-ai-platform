"""plans and entitlements (Roadmap Stage C, narrow SaaS foundation, §59-§61)

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-30

Additive: two new tables, one new nullable column on tenants. A real data
migration too (not just schema): seeds one default "free" Plan + its one
Entitlement row, and backfills every existing tenant's plan_id to it, so no
existing tenant is left without a plan (§60). `tenants.plan_id` stays
nullable at the DB level rather than being flipped NOT NULL afterward —
SQLite (tests/conftest.py's no-Docker fallback, §86) cannot ALTER COLUMN
without Alembic's batch mode, which no prior migration in this repo uses;
the invariant "every tenant has a plan" is enforced at the application
layer instead (app/services/entitlement_service.py treats a null plan_id
the same as the free plan, §107 additive-over-destructive).
"""
import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ENTITLEMENT_KEYS = ("ai_explanations_monthly_limit",)
_FREE_PLAN_ID = str(uuid.uuid4())
_FREE_AI_EXPLANATIONS_LIMIT = 10


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("slug", name="uq_plans_slug"),
    )

    op.create_table(
        "entitlements",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("plan_id", sa.String(length=36), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("key", sa.Enum(*_ENTITLEMENT_KEYS, name="entitlement_key", native_enum=False), nullable=False),
        sa.Column("value", sa.Integer(), nullable=True),
        sa.UniqueConstraint("plan_id", "key", name="uq_entitlement_plan_key"),
    )
    op.create_index("ix_entitlements_plan_id", "entitlements", ["plan_id"])

    op.add_column("tenants", sa.Column("plan_id", sa.String(length=36), sa.ForeignKey("plans.id"), nullable=True))
    op.create_index("ix_tenants_plan_id", "tenants", ["plan_id"])

    plans_table = sa.table(
        "plans", sa.column("id", sa.String), sa.column("slug", sa.String), sa.column("name", sa.String), sa.column("created_at", sa.DateTime)
    )
    op.bulk_insert(plans_table, [{"id": _FREE_PLAN_ID, "slug": "free", "name": "Free", "created_at": datetime.now(timezone.utc)}])

    entitlements_table = sa.table(
        "entitlements",
        sa.column("id", sa.String),
        sa.column("plan_id", sa.String),
        sa.column("key", sa.String),
        sa.column("value", sa.Integer),
    )
    op.bulk_insert(
        entitlements_table,
        [
            {
                "id": str(uuid.uuid4()),
                "plan_id": _FREE_PLAN_ID,
                "key": "ai_explanations_monthly_limit",
                "value": _FREE_AI_EXPLANATIONS_LIMIT,
            }
        ],
    )

    tenants_table = sa.table("tenants", sa.column("plan_id", sa.String))
    op.execute(tenants_table.update().where(tenants_table.c.plan_id.is_(None)).values(plan_id=_FREE_PLAN_ID))


def downgrade() -> None:
    op.drop_index("ix_tenants_plan_id", table_name="tenants")
    op.drop_column("tenants", "plan_id")
    op.drop_index("ix_entitlements_plan_id", table_name="entitlements")
    op.drop_table("entitlements")
    op.drop_table("plans")
