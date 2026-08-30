"""One-time operational setup for the retention-checkpoint scheduler
(infrastructure/n8n/workflows/retention-checkpoint-scheduler.json).

Creates a real TEACHER account (the least-privileged role that satisfies
`GET /retention/checkpoints/due`'s staff-only access check, §78 least
privilege) in an existing tenant, for the n8n workflow to log in as. This is
an administrative account-provisioning step, the same as any other staff
account — there is no self-service endpoint for creating non-STUDENT
accounts (see ADR-011), so this script exists instead of a fabricated
"service account" auth mechanism.

Usage (from inside the api container):
    python3 scripts/seed_retention_scheduler_account.py --tenant-id <id> --email <email> --password <password>

Idempotent: re-running with the same email updates nothing and reports the
existing account rather than erroring or creating a duplicate.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so `app.*` resolves when run as a plain script

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.tenant import Tenant
from app.models.user import Role, User


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant-id", required=True, help="Existing tenant to create the scheduler account in")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True, help="Minimum 10 characters (same policy as /auth/register)")
    args = parser.parse_args()

    if len(args.password) < 10:
        print("password must be at least 10 characters", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        tenant = db.get(Tenant, args.tenant_id)
        if tenant is None:
            print(f"no tenant with id {args.tenant_id}", file=sys.stderr)
            return 1

        existing = db.query(User).filter(User.email == args.email).first()
        if existing is not None:
            print(f"account already exists: {existing.id} (role={existing.role.value}, tenant={existing.tenant_id})")
            return 0

        user = User(
            tenant_id=tenant.id,
            email=args.email,
            password_hash=hash_password(args.password),
            display_name="Retention Scheduler",
            role=Role.TEACHER,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"created scheduler account: {user.id} (tenant={tenant.id})")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
