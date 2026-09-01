"""max_tenant_users entitlement for the free plan (Roadmap Stage E, ADR-016
second gated feature, §59-§61)

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-01

Data-only: seeds one Entitlement row (`max_tenant_users` = 5) on the
existing "free" plan. No schema change — `entitlements.key` is a
non-native, no-CHECK-constraint enum column (SQLAlchemy 2.0's Enum defaults
`create_constraint` to False), so a new EntitlementKey member is purely an
application-layer change (app/models/plan.py); this migration only adds the
new key's actual data row, matching migration 0010's own seeding pattern.
The "school" plan (scripts/seed_school_plan.py) intentionally gets no row
here — zero Entitlement rows means unlimited, the correct default posture
for an institutional pilot tenant (ADR-016).
"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FREE_PLAN_SLUG = "free"
_FREE_MAX_TENANT_USERS = 5


def upgrade() -> None:
    connection = op.get_bind()
    plans_table = sa.table("plans", sa.column("id", sa.String), sa.column("slug", sa.String))
    free_plan_id = connection.execute(sa.select(plans_table.c.id).where(plans_table.c.slug == _FREE_PLAN_SLUG)).scalar()
    if free_plan_id is None:
        # Defensive, not assumed (§107): migration 0010 always seeds "free",
        # but never silently skip a real data step if that invariant breaks.
        raise RuntimeError("free plan not found — migration 0010 must run before 0012")

    entitlements_table = sa.table(
        "entitlements",
        sa.column("id", sa.String),
        sa.column("plan_id", sa.String),
        sa.column("key", sa.String),
        sa.column("value", sa.Integer),
    )
    op.bulk_insert(
        entitlements_table,
        [{"id": str(uuid.uuid4()), "plan_id": free_plan_id, "key": "max_tenant_users", "value": _FREE_MAX_TENANT_USERS}],
    )


def downgrade() -> None:
    connection = op.get_bind()
    entitlements_table = sa.table(
        "entitlements", sa.column("plan_id", sa.String), sa.column("key", sa.String)
    )
    plans_table = sa.table("plans", sa.column("id", sa.String), sa.column("slug", sa.String))
    free_plan_id = connection.execute(sa.select(plans_table.c.id).where(plans_table.c.slug == _FREE_PLAN_SLUG)).scalar()
    if free_plan_id is not None:
        op.execute(
            entitlements_table.delete().where(
                entitlements_table.c.plan_id == free_plan_id, entitlements_table.c.key == "max_tenant_users"
            )
        )
