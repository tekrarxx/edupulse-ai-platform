"""consent/age-based PDE authorization (Phase 10 / P10, §81)

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-30

Additive: two nullable columns. No existing schema changes, no backfill —
neither date_of_birth nor consent_given_at can be honestly reconstructed
for existing rows (§105).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("date_of_birth", sa.Date(), nullable=True))
    op.add_column("parent_student_links", sa.Column("consent_given_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("parent_student_links", "consent_given_at")
    op.drop_column("users", "date_of_birth")
