"""Seeds a real "School" plan (§61) with no AI-explanation entitlement row
at all — unlimited, the correct posture for an institutional pilot tenant,
distinct from the Free plan's 10/month B2C default (migration 0010).
Idempotent. Does not assign any tenant to it — that remains a deliberate,
separate operational step (an admin or a future billing flow sets
`Tenant.plan_id`), matching this codebase's existing seed-script convention
of never silently mutating unrelated rows.

Run: `python -m scripts.seed_school_plan` (inside the api container/venv).
"""
from app.db.session import SessionLocal
from app.models.plan import Plan


def seed() -> None:
    db = SessionLocal()
    try:
        plan = db.query(Plan).filter(Plan.slug == "school").first()
        if plan is None:
            plan = Plan(slug="school", name="Okul")
            db.add(plan)
            db.commit()
            print(f"Seeded plan: {plan.name} ({plan.id}) — no entitlement rows, i.e. unlimited on every key.")
        else:
            print(f"Plan already exists: {plan.name} ({plan.id})")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
