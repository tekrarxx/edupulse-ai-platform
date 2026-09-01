# EduPulse AI — Project Status

Date: 2026-09-01
Scope: current, factual snapshot of the repository as of commit `0911776`.
Supersedes nothing — `docs/audit/PHASE0-AUDIT.md` (2026-08-28) audited a
literally empty repository (three text files, no `apps/`, no git history)
before Phase 1 started; this document reflects the repository after
Phases 1–10 (§113) and five post-MVP "Roadmap Stage A–E" slices. See that
report for the historical baseline, not the current state.

## Verified test/lint status (this audit)

Run against the real local Docker stack (`docker compose up`, Postgres —
not the SQLite fallback), same commands `make test`/`make test-api`/
`make test-web` use:

| Check | Result |
|---|---|
| `pytest` (`apps/api`) | **247 passed**, 0 failed |
| `ruff check .` (`apps/api`) | All checks passed |
| `npm test -- --watchAll=false` (`apps/web`) | **37 passed**, 0 failed, 11 suites |
| `npx tsc --noEmit` (`apps/web`) | Clean, no errors |

(Updated after this session's execution-layer slice, ADR-021 — see ROADMAP.md P1.)

Backend test layout: `apps/api/tests/{unit,integration,api,security,e2e,load}/`,
32 test files, ~232 `def test_...` functions. Frontend: `apps/web/__tests__/`,
11 files.

## What's implemented, by domain

- **Identity/Tenancy/RBAC** (§50–53): `app/models/tenant.py`, `user.py`.
  6 roles (`SUPER_ADMIN`/`TENANT_ADMIN`/`SCHOOL_ADMIN`/`TEACHER`/`STUDENT`/
  `PARENT`). Self-service registration (`POST /auth/register`, always a
  fresh `INDIVIDUAL` tenant) and admin-initiated enrollment into an
  existing tenant (`POST /auth/tenant/users`, Roadmap Stage A item 1,
  least-privilege role-creation matrix in `auth_service.py`). Self-service
  password reset via a local Mailpit SMTP catcher (migration `0011`).
  Cross-tenant negative tests exist for every tenant-scoped resource
  (`tests/security/test_tenant_isolation.py` + per-feature tests, §52/§88).
- **Curriculum** (§19–20): `app/models/curriculum.py` — Curriculum→Subject→
  Topic→Skill→Prerequisite, cycle-safe prerequisite graph, versioned.
  Shared reference data, deliberately not tenant-scoped (`curriculum.py`
  has no `tenant_id` column). Physics is seeded
  (`scripts/seed_curriculum.py`); a second subject (Chemistry) was proven
  to require zero code changes (Roadmap Stage A item 3,
  `tests/e2e/test_second_subject_chemistry.py`).
- **Assessment/Observation/Evidence** (§21–23): `app/models/assessment.py`,
  `observation.py`, `evidence.py`. `Observation` is append-only, enforced
  by a Postgres trigger (ADR-018) — not just application-level discipline.
  `Evidence` is a separate, interpreted row, never conflated with the raw
  observation (§23's hard rule).
- **Knowledge State** (§24–27): `app/models/knowledge_state.py`,
  `knowledge_state_service.py`. Beta-Binomial Bayesian model per student/
  skill/facet (ADR-012 — see "Known drift" below), 5 facets (Recognition/
  Recall/Application/Transfer/Retention, §28), facet independence verified.
  Read path batched for all 5 facets in one query (Roadmap Stage D,
  `3b3c9a4`).
- **Prometheus Decision Engine** (§32–39): `app/models/decision.py`,
  `decision_engine_service.py`, `decision_policy.py`,
  `authorization_service.py`. 12 candidate action types scored per
  decision, structured `reason_codes`, full explainability
  (`GET /decisions/{id}`), authorization as a separate step from decision
  generation (§37, `AuthorizationResult`: ALLOWED/ESCALATED/REJECTED).
  Consent/age-based authorization gate exists (migration `0009`,
  ADR-013 addendum 1); role/tenant-education-policy-based authorization is
  a **documented, deliberate deferral**, not an oversight (ADR-013
  addendum 2, Roadmap Stage A item 4) — revisit trigger: a second pilot
  tenant needing genuinely different authorization behavior.
- **Transfer/Retention/Falsification** (§29–31, §39): `app/models/retention.py`
  (`RetentionCheckpoint`, `Hypothesis`). 14/28-day checkpoints
  auto-scheduled on the 5th application-facet attempt. Falsification
  verdicts (SUPPORTED/NOT_SUPPORTED/INCONCLUSIVE) computed at completion.
  Scheduler wired via n8n (`infrastructure/n8n/workflows/
  retention-checkpoint-scheduler.json`, Phase 10 slice 3) — n8n only calls
  the real API on a schedule, no domain logic in the workflow itself (§92).
- **AI Gateway** (§43–49): `app/ai/gateway.py`, `providers/ollama.py`,
  `safety.py`, `prompts.py`. One provider (Ollama, local-first, §44), one
  capability so far (`AIUsageCapability.SKILL_EXPLANATION`). Every call
  writes an `AIUsageRecord` (provider, model, prompt name+version, tokens,
  latency, success) regardless of outcome — real usage/cost accounting
  (§65, §139), not a placeholder.
- **Dashboards** (§74–77): Student, Teacher, Admin — `dashboard_service.py`,
  `routes/dashboard.py`. Student/Teacher never expose a raw
  `mastery_probability` float, only plain-language labels (§26). Admin
  dashboard is tenant-wide counts only, no per-student names (§80), and
  shows both AI-explanation and (as of this session) tenant-seat usage
  against plan limits.
- **SaaS Entitlements** (§59–61, §116): `app/models/plan.py`,
  `entitlement_service.py`, ADR-016 (+ this session's addendum). Two gated
  keys: `AI_EXPLANATIONS_MONTHLY_LIMIT` (free plan: 10/month) and
  `MAX_TENANT_USERS` (free plan: 5 seats, migration `0012`, this session).
  No `Subscription`/`Invoice`/`Payment` model exists — genuinely unbuilt,
  not faked (§105); see Deferred below.
- **Security** (§78): argon2 password hashing, JWT access + rotated
  refresh tokens (httpOnly cookie, ADR-011), rate limiting (login, tenant
  user creation, AI explanations), security headers, escalation audit
  logging (Phase 10 slice 1), structured logging + correlation IDs +
  Prometheus/Grafana metrics (Phase 10 slice 4, observability stack — not
  to be confused with the PDE, see ADR naming note in
  `PHASE0-AUDIT-PROMPT.md` §Step 3).

## What's explicitly deferred, and why

Pulled from `docs/audit/MVP-GATE.md` §4 and updated for what Stages B–E
already closed:

| Item | Status | Why deferred / trigger to revisit |
|---|---|---|
| ~~Execution layer~~ — **CLOSED (this session, ADR-021)**: `GET /decisions/{id}/task` (`app/services/task_service.py`) resolves a Decision to a real Question; the student dashboard's "Başla" button submits it through the existing `POST /assessment/attempts`. Residual: 6/12 action types are deliberately not question-answering (still label-only), and skills with no question in the resolved facet get an honest `no_question_available`, not a fabricated task. | — | See ADR-021. |
| Role/tenant-education-policy authorization | Deliberate deferral (ADR-013 addendum 2) | No second real tenant has asked for different policy behavior yet. |
| Billing (`Subscription`/`Invoice`/`Payment`) | Genuinely unbuilt | ADR-016: §116 doesn't require it for MVP; building it before a paying customer exists risks unused plumbing (§125/§141). Trigger: real money needs to move. |
| Self-service plan upgrade | Unbuilt | Plan assignment is an admin/script operation today (`scripts/seed_school_plan.py`), matching how `ParentStudentLink` and admin-enrollment work. |
| Per-role/per-seat entitlements beyond `MAX_TENANT_USERS` | Not needed yet | Only two keys exist because only two real features need gating; a third is added the same narrow way (ADR-016 §Consequences), not speculatively. |
| Open-ended (non-auto-gradable) delayed-retention grading | Deferred (ADR-014) | v1 requires auto-gradable questions so falsification has a definite outcome. |

## Known drift / technical debt found during this audit

- **ADR-012's `Status:` header still reads `Proposed`**, but the
  Beta-Binomial knowledge-state model it describes has been implemented,
  tested, and in production use since Phase 5 (migration `0005`) — every
  other ADR in the repo (`002`, `011`, `013`–`020`) reads `Accepted`. This
  is a stale header, not a live proposal; low severity (documentation-only,
  §134's lowest-priority tier) but worth a one-line fix.
- No other test/lint failures, broken imports, or dead code found during
  this audit's inspection of `apps/api/app/`, `apps/web/app/`, and the
  Alembic chain (`0001`→`0012`, linear, no branch points).
