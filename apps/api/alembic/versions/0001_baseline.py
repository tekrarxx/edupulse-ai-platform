"""baseline (empty schema)

Revision ID: 0001
Revises:
Create Date: 2026-08-28

No domain tables are created here on purpose. Domain modeling starts in
Phase 2 (P1 Identity/Tenant/RBAC) so that tenant_id is designed in from the
first real table rather than retrofitted (CLAUDE.md §147). This revision
exists only to establish the Alembic chain head.
"""
from typing import Sequence, Union

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
