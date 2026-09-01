# ADR-019: Shadow Mode — Tenant-Level Flag + Per-Request Override

Status: Accepted
Date: 2026-09-01
Related: CLAUDE.md §38, §96, ADR-013 (Prometheus Decision Engine)

Shadow Mode was designed and built as part of Phase 6/ADR-013 (see that
ADR's "Shadow Mode (§38, §96)" section for the full original reasoning); it
never got its own ADR file under the name §101 lists it by. This ADR is that
existing decision, extracted and formalized as its own record — no code
changes accompany it.

## Context

§38 requires that a new decision algorithm be able to run against real
learner activity and log a hypothetical decision **without the decision
affecting the learner**, ahead of a policy change entering the active
learning flow. §96 requires this be implemented as an explicit, inspectable
feature flag, not a scattered hard-coded conditional.

## Decision

Shadow Mode has two independent triggers, both landing on the same
`Decision.is_shadow` boolean column (`app/models/decision.py:99`):

1. **Tenant-level default**: `Tenant.pde_shadow_mode_default`
   (`app/models/tenant.py:34-38`), a boolean defaulting to `false`. When
   `true`, every decision generated for that tenant is stored with
   `is_shadow = true`, regardless of who requested it — a hard floor.
2. **Per-request override**: `POST /decisions/next-action?mode=shadow`
   (`app/api/routes/decision.py:50-59`, `_resolve_is_shadow`). A staff caller
   (`TEACHER`/`SCHOOL_ADMIN`/`TENANT_ADMIN`/`SUPER_ADMIN`) may force a single
   dry-run without changing the tenant default. A student or parent has no
   `mode` parameter available to them — the tenant flag is the only way their
   own request becomes shadowed, and when it does, it is shadowed uniformly,
   not selectively hidden from just them.

The tenant flag is a **hard floor**: `mode=live` on an individual request
cannot override a tenant-level shadow lock, since the flag exists as a
rollout safety switch, not something a single caller should be able to
bypass by passing a different mode.

**Enforcement that "the decision does not affect the learner" is currently
scoped to data/API visibility, not execution.** `is_shadow = true` decisions
are excluded from the default `GET /decisions` history view
(`app/api/routes/decision.py:116-136`, `include_shadow` query param,
staff-only) and are never returned to a non-staff caller who did not
explicitly request them. Separately, and more fundamentally: no code path in
this codebase today *executes* any decision (assigns a task, changes what
content is served) for any learner, shadow or live — that execution layer
belongs to a later phase (dashboards/content delivery, §113 P8+). So today,
"shadow" and "live" decisions differ only in visibility, not in effect,
because nothing yet has an effect. This is recorded explicitly rather than
claimed as a guarantee the system cannot yet back up (§105) — see ADR-013's
own "Explicit scope boundary" note.

One additional interaction with authorization: a real (non-shadow)
`ESCALATED` result is treated as noteworthy in
`decision_engine_service.py:134-138` — a shadow decision escalating is not
surfaced the same way, since nothing is actually waiting on a shadow
decision's outcome.

## Alternatives Considered

- **Per-request-only shadow mode** (no tenant-level flag): rejected — this
  would leave no way to roll out a new policy version to an entire tenant's
  traffic gradually, only to individual staff-initiated dry-runs, which does
  not satisfy §38's "real learner activity" framing (student-originated
  requests would always be live).
- **A separate `shadow_decisions` table**: rejected — `is_shadow` as a
  boolean column on the same `Decision` table keeps the schema, versioning
  (`policy_version`/`model_version`), and provenance fields (§100) identical
  between shadow and live rows, which is exactly what makes a shadow
  decision comparable to what a live decision would have been.

## Consequences

- Any future policy-version rollout should default new tenants' shadow flag
  to `true` during a validation window before flipping it, rather than
  inventing a separate rollout mechanism.
- Once an execution layer exists (§113 P8+), it MUST check `is_shadow` before
  taking any learner-visible action — that check does not exist yet because
  there is nothing yet to gate, and its absence must not be read as an
  oversight when that layer is built.
