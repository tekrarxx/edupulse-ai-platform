# ADR-017: Modular Monolith, Not Microservices

Status: Accepted
Date: 2026-09-01
Related: CLAUDE.md §12–§14, §54, §113–§114

This ADR documents a decision already in effect since the first commit — it
was never written down as its own ADR, which §102 requires ("code changes
architecture" implies documentation must exist; not writing it down let
implementation and documentation silently diverge, which §102 forbids). No
code changes accompany this ADR.

## Context

CLAUDE.md §13 mandates a modular monolith as the default architecture, and
§14 restricts introducing a separate service to concrete reasons (independent
scaling, computational isolation, deployment independence, a security
boundary, domain ownership, or an infrastructure requirement) — never merely
because "this is a SaaS" (§14) or because microservices are considered
"production-like" (§10).

## Decision

**One FastAPI process (`apps/api`) hosts every backend domain; one Next.js
process (`apps/web`) hosts the frontend.** Domain boundaries are enforced by
Python module structure, not process/network boundaries:

- `apps/api/app/models/` — one file per domain (`tenant.py`, `user.py`,
  `curriculum.py`, `assessment.py`, `observation.py`, `evidence.py`,
  `knowledge_state.py`, `decision.py`, `retention.py`, `plan.py`,
  `ai_usage.py`, `audit_log.py`, `relationship.py`) — this list itself is
  the domain-boundary map called for in §54 (Identity, Tenancy, Education,
  Curriculum, Assessment, Learning State, Prometheus, AI, Content, Billing).
- `apps/api/app/services/` — one service module per domain, each importing
  only the models/services it needs. The one enforced cross-domain rule with
  its own explicit test coverage is §95's billing/Prometheus wall:
  `entitlement_service.py` is never imported by `decision_policy.py` or
  `authorization_service.py` (see ADR-016).
- `apps/api/app/api/routes/` — thin HTTP routes per domain, calling into
  services; no business logic lives in a route handler (§16).
- `apps/api/app/ai/` — the AI Gateway (ADR-015), a distinct module boundary
  even though it runs in the same process, because §43 requires it to be
  swappable (Ollama today, an external provider later) without touching
  callers.

No domain currently has a concrete reason from §14's list to become a
separate deployable. The AI Gateway is the closest candidate (it is the one
component that talks to an external-ish process, Ollama) but even it runs
in-process today, calling out over HTTP to the `ollama` container — the
gateway module boundary already gives it the isolation it needs (provider
swap, timeout, fallback) without a second FastAPI deployment.

## Alternatives Considered

- **Microservices per domain** (a separate service for identity, education,
  assessment, Prometheus, AI, billing): rejected per §14 — none of identity,
  tenancy, education, assessment, or Prometheus have today's concrete reason
  (independent scaling, isolation, deployment independence, a security
  boundary, or an infrastructure requirement) to be split. Splitting now
  would be exactly the "premature microservices" §12 warns against, and would
  multiply the multi-tenant/auth/observability wiring several times over for
  no measured benefit.
- **A single undifferentiated module** (all models/services/routes in one
  file or one package with no internal boundaries): rejected — this is what
  §54 explicitly forbids ("do not create one giant module containing all
  business logic"). The per-domain file/module split above is how §54 is
  actually satisfied inside a monolith.

## Consequences

- Any future service extraction (§14) must point to one of its named
  concrete reasons, not "SaaS-ness" in the abstract, and should be recorded
  in its own ADR at that time (§120's cloud-migration principle already
  anticipates infrastructure adapters swapping — Local PostgreSQL → Managed
  PostgreSQL, Ollama → external provider — without this module boundary
  needing to change).
- Code review should treat a new cross-domain import that bypasses a
  service's public functions (e.g. a route reaching directly into another
  domain's models) as a defect against §54's domain-boundary intent, the
  same way a client-supplied `tenant_id` is treated as a defect against
  ADR-002.
