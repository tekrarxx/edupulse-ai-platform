# EduPulse AI — Architecture

Date: 2026-09-01. Describes what exists and where — the *why* behind each
decision lives in the cited ADR (`docs/adr/`), not repeated here.

## Deployment shape: modular monolith (ADR-017)

```
Next.js web (apps/web)
        │
        ▼
FastAPI api (apps/api) — single deployable process
        │
   ┌────┼──────────────────────────┐
   ▼    ▼                          ▼
Identity  Education/Assessment   Prometheus (PDE)
   │         │                      │
   └─────────┼──────────────────────┘
              ▼
        PostgreSQL (single database, tenant_id-scoped tables)
```

One FastAPI process, one Postgres database. Domain boundaries are enforced
by *import discipline*, not process/network separation (§13–14) — e.g.
`decision_policy.py`/`authorization_service.py`/`decision_engine_service.py`
must never import `entitlement_service.py` or `app/models/plan.py` (§95,
enforced by ADR-015 §7's reasoning, reapplied in ADR-016 §Consequences).

## Docker Compose service graph (`docker-compose.yml`)

```
postgres ─┐
redis ────┼─► api ─► web
mailpit ──┘    │
ollama ────────┘  (no depends_on — api degrades gracefully if absent, §43)
api (healthy) ──► n8n  (schedules retention checkpoints via real API calls)
```

7 services, all with healthchecks. `postgres` also runs an init script
(`infrastructure/postgres/init/01-create-test-db.sql`) creating a separate
`edupulse_test` database so pytest never touches dev data (§86). See
ADR-020 for the full local-first rationale and cloud-migration mapping
(§119–120).

## Backend layout (`apps/api/app/`)

```
api/routes/    — 9 routers (auth, curriculum, assessment, knowledge_state,
                 decision, retention, ai, dashboard, health). Thin (§15–16):
                 request validation + service call + typed HTTP mapping,
                 no business logic.
models/        — SQLAlchemy 2.x. tenant_id present on every tenant-owned
                 table; absent, deliberately, on curriculum.py (shared
                 reference data) and plan.py (global catalog).
services/      — 14 modules, one per domain concern (auth, curriculum,
                 assessment, knowledge_state, decision_engine, decision_
                 policy, authorization, retention, entitlement,
                 explanation, dashboard, relationship, audit, email).
                 Routes call services; services never import routes.
schemas/       — Pydantic request/response contracts (§128).
ai/            — gateway.py (provider-agnostic entry point), providers/
                 (ollama.py — the only provider today, §44), safety.py,
                 prompts.py (versioned prompt templates).
db/, core/     — session/engine setup, config, security primitives
                 (argon2 hashing, JWT, ADR-011).
```

`apps/api/alembic/versions/`: 12 migrations, `0001`→`0012`, linear chain,
no branches. Every migration is additive except where explicitly justified
(§107) — see each migration's own docstring for its reasoning.

## Frontend layout (`apps/web/app/`)

`login/`, `register/`, `forgot-password/`, `reset-password/`,
`dashboard/{student,teacher,parent,admin}/`, `status/`. No authoritative
business logic in the frontend (§18) — `lib/*.ts` files are typed fetch
wrappers only; every authorization decision is re-verified server-side.

## Multi-tenancy enforcement (ADR-002, §51–52)

`tenant_id` is never read from the client. Every service function that
needs it takes it from the authenticated request's own token
(`current_user.tenant_id`), never a request body/query field for a
resource's *own* tenant. Cross-tenant access is tested negatively per
resource (`tests/security/test_tenant_isolation.py` plus per-feature
tests) — §52/§88's mandatory pattern, not just a general design intent.

## PDE isolation from SaaS/billing (§95, ADR-016 §Consequences)

The Prometheus Decision Engine must never know which plan a tenant is on.
Concretely: `decision_policy.py`, `authorization_service.py`, and
`decision_engine_service.py` contain no import of `entitlement_service.py`
or `app/models/plan.py`. The only consumers of the entitlement system
today are `explanation_service.py` (AI quota) and `auth_service.py`
(tenant seat limit) — both outside the PDE's own module set.

## AI Gateway (ADR-015)

```
explanation_service.py (only real caller today)
        ↓
app/ai/gateway.py  — provider selection, structured-output validation,
                      safety check, usage/cost accounting (writes
                      AIUsageRecord unconditionally, success or failure)
        ↓
app/ai/providers/ollama.py  — the only provider; OLLAMA_BASE_URL is the
                                sole swap point for a future external
                                provider (§140 routing strategy, not yet
                                built beyond this one provider)
```

## Observability (§83, Phase 10 slice 4)

Structured logging with correlation IDs + Prometheus/Grafana metrics
exporters. Distinct from the **Prometheus Decision Engine** — same word,
two unrelated things in this repo; see `PHASE0-AUDIT-PROMPT.md`'s
terminology warning if this is ever ambiguous in code review.

## Where to find "why"

Every non-obvious architectural decision has a numbered ADR in
`docs/adr/`: multi-tenancy (002), auth/token strategy (011), Bayesian
knowledge state (012), PDE candidate scoring/authorization (013),
transfer/retention/falsification (014), AI Gateway (015), SaaS
entitlements (016, + this session's seat-limit addendum), modular
monolith (017), event sourcing via `Observation` (018), shadow mode (019),
local-first Docker Compose (020). This document does not restate their
reasoning — read the ADR for that.
