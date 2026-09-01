# ADR-016: SaaS Plans and Entitlements (Narrow Scope)

Status: Accepted
Date: 2026-08-30
Related: CLAUDE.md §59-§61, §63, §65, §95, §116, Roadmap Stage C

## Context

CLAUDE.md §60 requires an entitlement system — "Plan → Entitlements →
Tenant/User → Feature Access" — rather than scattered `if user.plan ==
"pro":` checks, and §65 requires usage metering. Neither existed anywhere
in the codebase before this ADR: `docs/audit/MVP-GATE.md` and the project
roadmap both recorded Phase 9 (P9: Usage/Entitlements/Billing/SaaS) as
entirely unstarted.

At the same time, §116 is explicit that the MVP does **not** need full
enterprise billing, and §113's own phase ordering puts this after the
adaptive-learning core (P0-P8) and alongside, not before, production
hardening (P10). Building a full billing system (invoices, payments,
Stripe integration, dunning, proration) now — before a single real paying
customer exists — would be exactly the "designing for a hypothetical
future requirement" §125/§141 warn against, and would risk becoming unused
plumbing (§126).

## Decision

Build the smallest real slice that gives the *shape* CLAUDE.md's SaaS
sections ask for, with at least one feature actually gated by it end to
end — not a data model with nothing consuming it.

**Data model** (`app/models/plan.py`, migration `0010`):
- `Plan`: `id`, `slug` (unique), `name`. No price, no billing cycle, no
  Stripe product id — those are Phase 9-proper concerns, added when a real
  payment flow is built, not fabricated now.
- `EntitlementKey`: a closed, extensible enum (same discipline as
  `AIUsageCapability`, ADR-015 Assumption 1) — starts with exactly one
  member, `AI_EXPLANATIONS_MONTHLY_LIMIT`, because that is the one feature
  this ADR actually gates. A key is added only when a real feature needs
  gating, never speculatively.
- `Entitlement`: `plan_id` + `key` + nullable `value`. **Absence of a row
  for a given plan+key means unlimited** — not zero, not a fabricated
  default. This lets a plan exist (and be assigned to tenants) before every
  entitlement it might ever need is decided, without ever inventing a
  restriction nobody configured (§105).
- `Tenant.plan_id`: nullable at the DB level. A genuinely nullable FK,
  never forced `NOT NULL`, because this codebase's tests fall back to
  SQLite when Docker/Postgres is unavailable (`tests/conftest.py`, §86),
  and SQLite cannot `ALTER COLUMN` to change nullability without Alembic's
  batch-table-rebuild mode, which no prior migration here uses. The
  invariant "every tenant effectively has a plan" is enforced in
  `app/services/entitlement_service.py` instead: a `None` `plan_id` is
  resolved to the `free` plan, never to "unlimited" (§107 — additive
  migration over a destructive/riskier one; the practical effect is
  identical, just enforced one layer up).

**Enforcement, one real example**: `app/services/entitlement_service.py`'s
`enforce_ai_explanation_quota` is called from
`app/services/explanation_service.py` *before* the AI Gateway is invoked
(§48 — an over-quota tenant must never pay for a real LLM call it will be
rejected for anyway). `POST /ai/explanations` maps a `QuotaExceeded` to
`429` with `detail="ai_explanation_quota_exceeded"`, distinguishable from
the existing per-user rate limit's `"rate_limited"` — they are two
independent controls (one throttles request *rate*, the other caps
monthly *usage against a plan*) and are tested separately
(`tests/api/test_ai.py`).

**Usage counting reuses `AIUsageRecord`** (ADR-015, §5) rather than a new
usage-events table — it already carries `tenant_id` and `created_at` for
every AI Gateway call, so "AI explanations used this month" is a `COUNT(*)
WHERE tenant_id = ... AND created_at >= month_start`, not a new telemetry
stream (§143 — avoid data hoarding; reuse what already exists before adding
a new field).

**Default plan on signup**: `auth_service.register()` (self-service B2C)
assigns the new individual tenant's `plan_id` to the `free` plan
immediately — every tenant created after this migration has a real plan
from the start; only pre-existing tenants relied on the migration's own
backfill.

**Second real tier**: `scripts/seed_school_plan.py` creates a `school`
plan with **zero** `Entitlement` rows — i.e., unlimited on every currently-
gated key, the correct default posture for an institutional pilot tenant
(§72's pilot-school process), assigned to a tenant as a separate,
deliberate operational step (an admin, or a future billing flow), never
automatically.

## What Is Explicitly Not Built

- No `Subscription`, `Invoice`, or `Payment` model — no money changes
  hands anywhere in this codebase yet, and §116 does not require it.
- No self-service plan-upgrade UI or endpoint — plan assignment is
  currently an operational/admin action (matching how `ParentStudentLink`
  and admin-enrollment work — ADR pattern already established this
  session), not a customer-facing flow.
- No per-role or per-seat entitlements (e.g. "max teachers") — only the
  one key a real feature (`POST /ai/explanations`) actually needs today.
- Pricing amounts/currency — `Entitlement.value` stores a usage limit
  (an integer), never a price; §63's "pricing MUST remain configurable, not
  hard-coded" is satisfied by the entitlement rows being data, but no
  price field exists to hard-code in the first place at this stage.

## Consequences

- Prometheus/PDE code (`decision_policy.py`, `authorization_service.py`,
  `decision_engine_service.py`) must never import
  `app.services.entitlement_service` or `app.models.plan` — §95's "the
  Prometheus engine must not know whether a learner is Free/Pro/Enterprise"
  is a hard boundary, checked by the same reasoning ADR-015 §7 already
  applies to the AI Gateway.
- Adding a second gated feature (e.g. a future cap on generated questions)
  is a new `EntitlementKey` member + one `enforce_*` function in
  `entitlement_service.py` + one call site — not a new subsystem.
- The `free` plan's `10`/month AI-explanation limit is a real, live
  default from this ADR's own migration, not a placeholder — changing it
  is a data change (`UPDATE entitlements SET value = ... WHERE ...`), never
  a code deploy, which is the entire point of §60/§63.

## Falsifiability / Review Trigger

Revisit this ADR (not just tweak the numbers) when either becomes true:
1. A second commercial tier needs a **different** enforcement mechanism
   than "count `AIUsageRecord` rows this month" (e.g. a hard cap enforced
   mid-request, or a non-AI-Gateway feature) — the current design assumes
   this shape generalizes; the first counter-example is real evidence it
   doesn't.
2. Real billing (money) needs to exist — at that point `Plan` gains a
   price/billing-cycle relationship to a genuine `Subscription`/`Invoice`
   domain, which is new modeling work, not an extension of this one.

## Addendum (Roadmap Stage E, 2026-09-01): `max_tenant_users` — the Second Gated Feature

Falsifiability trigger 1 above is now real evidence *for* the design, not
against it: `EntitlementKey.MAX_TENANT_USERS` is a second key added the
exact way the "Consequences" section predicted — "a new `EntitlementKey`
member + one `enforce_*` function in `entitlement_service.py` + one call
site — not a new subsystem." No enforcement-mechanism change was needed.

**What it gates**: `POST /auth/tenant/users` (admin-initiated enrollment,
Roadmap Stage A item 1). `entitlement_service.enforce_tenant_user_seat_limit`
counts every `User` row (any role) in the tenant and compares against the
plan's `MAX_TENANT_USERS` entitlement, called before the write — same
"check before the effect happens" discipline as the AI-explanation quota
(§48/§60), except here the resource being protected is enrollment capacity,
not LLM spend. A rejected request maps to `429
tenant_seat_limit_exceeded` (`app/api/routes/auth.py`), distinguishable
from `email_already_registered` (409) and
`insufficient_role_for_target_role` (403) — three independent rejection
reasons, tested separately (`tests/api/test_auth.py`).

**Data**: migration `0012` seeds `max_tenant_users = 5` on the existing
`free` plan only — no schema change, since `entitlements.key` carries no
database-level `CHECK` constraint (SQLAlchemy 2.0's `Enum` defaults
`create_constraint` to `False`), so a new `EntitlementKey` member is a
pure application-layer change; the migration's job is only the data row.
The `school` plan (`scripts/seed_school_plan.py`) intentionally gets no
row — zero `Entitlement` rows still means unlimited, the same default
posture ADR-016's original decision established for institutional pilot
tenants.

**Dashboard**: `AdminDashboardOut.tenant_user_count`/`tenant_user_limit`
mirror `ai_explanations_used_this_month`/`ai_explanations_monthly_limit`'s
existing shape (`app/services/dashboard_service.py`,
`app/services/entitlement_service.get_tenant_user_seat_usage`) — an admin
approaching their seat limit can see it before hitting the 429, not just
after.

This addendum does not change the ADR's core decision or its remaining
"what is explicitly not built" list (§Billing) — it is the second data
point closing trigger 1, not a new architecture.

## Addendum 2 (2026-09-01): Self-Service Plan Switching

The original "What Is Explicitly Not Built" section named this directly:
"No self-service plan-upgrade UI or endpoint — plan assignment is
currently an operational/admin action... not a customer-facing flow,"
closeable "once there is a second real tier a tenant would plausibly
self-upgrade into." The `school` plan (`scripts/seed_school_plan.py`) is
that second tier, so this closes it:

- `entitlement_service.list_plans`/`get_current_plan`/`switch_tenant_plan`
  — the same "only entitlement_service reads `Tenant.plan_id`" invariant
  this ADR established stays intact; switching is a new function in the
  same module, not a new reader of the plan tables elsewhere.
- `GET /plans`, `GET /plans/tenant/current`, `PUT /plans/tenant`
  (`app/api/routes/plan.py`) — restricted to `TENANT_ADMIN`/
  `SCHOOL_ADMIN`/`SUPER_ADMIN` of the caller's own tenant (§51: no
  client-supplied tenant_id anywhere in the request). Every switch writes
  a `tenant.plan_changed` audit record (§131).
- **Deliberately symmetric, not upgrade-only**: since no `Subscription`/
  `Invoice`/`Payment` exists (§116, still true), there is no payment event
  to gate an upgrade on — restricting this to "upgrade" direction only
  would fabricate a distinction the system cannot actually enforce
  (§105). A real payment gate remains this ADR's second falsifiability
  trigger, unfired.
- Admin dashboard gained a plan-switcher control
  (`apps/web/components/plan-switcher.tsx`) alongside the existing
  AI-quota/seat-usage display.

This does not change what ADR-016 still says is unbuilt — `Subscription`/
`Invoice`/`Payment` remain genuinely absent.
