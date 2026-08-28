# EduPulse AI — Claude Code Phase Prompts

Complete prompt sequence for building EduPulse AI with Claude Code, mapped onto
the P0–P10 priority ladder in CLAUDE.md §113 and gated by the MVP definition
in §115.

---

## How to use this document

1. Rename `Claude.txt` → `CLAUDE.md` and place it at the repository root.
2. Run **one phase per Claude Code session**. Start each phase with a fresh
   context (`/clear`). Long-running sessions drift, and drift in this codebase
   means silently broken tenant isolation or a rewritten Bayesian update.
3. Each phase prompt below is paste-ready. Paste the **Standing Rules** block
   first in every session, then the phase prompt.
4. Every phase ends with a `STOP`. Approve explicitly before the next one.
5. Phases 1–7 are the MVP. Do not start Phase 8+ until the MVP gate passes.

**Recommended:** commit a `.claude/settings.json` with deny rules for
destructive commands (`git push --force`, `git reset --hard`, `rm -rf`,
`docker compose down -v`, `alembic downgrade`). A prompt is guidance; a
permission rule is enforcement.

---

## STANDING RULES — paste at the top of every session

```
STANDING RULES FOR THIS REPOSITORY

1. CLAUDE.md is the engineering constitution (§0). Read it before you touch
   anything. When it conflicts with my instruction, tell me — do not silently
   pick one.

2. "Prometheus" is overloaded. PDE = Prometheus Decision Engine, the adaptive
   learning core (§6, §32–39). Prometheus/Grafana = the metrics stack (§83).
   Never conflate them in code, comments, or your reports.

3. Before implementing anything non-trivial, give me the Pre-Implementation
   Report from §122:
   UNDERSTANDING / PLAN / FILES AFFECTED / DATABASE IMPACT / API IMPACT /
   PDE IMPACT / SECURITY RISKS / TEST PLAN / DOCUMENTATION IMPACT /
   ROLLBACK & RISK NOTES
   Then stop and wait for approval.

4. Work in vertical slices (§125, §126): Domain → Database → Application
   Service → API → Frontend → Tests. Never 15 disconnected entities at once.

5. Never do these without explicit approval (§135):
   delete existing work, rewrite architecture wholesale, destroy or edit
   existing migrations, run destructive DB operations, introduce Kubernetes or
   new microservices, change PDE mathematics, remove event sourcing or
   provenance, bypass authorization, weaken tenant isolation, commit secrets,
   send learner data to external services, replace deterministic logic with
   LLM calls, add large dependencies, add hidden background jobs.

6. No fake implementations (§105). No hardcoded responses to make tests pass.
   No stub that pretends to work. If something cannot be built yet, say so.

7. Conflict priority (§134): Security > Privacy > Data Integrity >
   Correctness > PDE Scientific Integrity > Educational Safety >
   Maintainability > Testability > Observability > Performance >
   Developer Convenience > UI Polish.

8. Commits: small, single-purpose, prefixed feat|fix|refactor|test|docs|
   chore|security|perf (§103). Never rewrite history. Never force push.

9. If you are unsure, ask. Do not resolve ambiguity by picking a plausible
   default and proceeding.
```

---

## PHASE 0 — Repository Audit (read-only)

Use the separate `PHASE0-AUDIT-PROMPT.md` file. Summary of its purpose: inspect
everything, compare against CLAUDE.md, produce CURRENT STATE / TARGET
ARCHITECTURE / GAP ANALYSIS / RISKS / IMPLEMENTATION ORDER / FILE LISTS /
DATABASE + API + PDE + OBSERVABILITY CHANGES / TEST STRATEGY / OPEN QUESTIONS.
Write nothing except the report. Stop.

Everything below assumes the Phase 0 report is approved.

---

## PHASE 1 — P0 Foundation

```
PHASE 1 — P0 FOUNDATION (§113 P0)

Goal: a running skeleton that a developer can start with `docker compose up -d`
and that has one real end-to-end path through every layer.

SCOPE
1. Repository structure. Move toward §57, but incrementally and only where the
   Phase 0 audit identified a concrete mismatch. Do not restructure wholesale
   (§57 closing note, §58). Every move is a separate commit.
2. Docker Compose (§91): postgres, redis, api, web, and n8n if the audit found
   it in use. Health checks, named volumes, predictable service names,
   isolated network. Local development must stay lightweight (§83).
3. Configuration (§108, §79): `.env.example` with every variable documented and
   no real values. Verify `.env` is gitignored. No secrets anywhere in the tree.
4. Backend skeleton (§16): FastAPI, Python 3.x, type hints throughout, Pydantic
   v2 schemas, SQLAlchemy 2.x, Alembic initialized. Layering per §15:
   API route → application service → domain logic → repository. Routes stay
   thin. Set up the module boundaries from §54 as directories now, even if most
   are empty — the boundary is the point.
5. Alembic baseline: one initial migration only. If migrations already exist,
   do not touch them; extend the chain.
6. Frontend skeleton (§17): Next.js + TypeScript + Tailwind + shadcn/ui.
   App shell, layout, one page. No business logic in the frontend (§15).
   Avoid generic "AI dashboard" aesthetics (§17).
7. Error handling (§90) and structured logging (§84) as shared infrastructure.
   Logs must never contain passwords, tokens, or learner-sensitive data.
8. Test harness (§86): pytest configured with unit/integration/api directories,
   a test database fixture, and a frontend test runner. At least one real
   passing test per layer — not placeholders.
9. `Makefile` with: up, down, logs, migrate, test, lint, format, seed.

OUT OF SCOPE
Auth, tenancy, education models, PDE, AI, dashboards, billing. Do not
anticipate them beyond leaving the module directories in place.

DEFINITION OF DONE
- `docker compose up -d` produces a healthy stack from a clean clone
- `make migrate` runs cleanly against an empty database
- `make test` passes
- health endpoint returns real status, not a hardcoded 200
- README documents setup in steps a new developer can follow
- §145 quality gate reviewed and reported

Give me the §122 Pre-Implementation Report first. STOP for approval.
```

---

## PHASE 2 — P1 Identity, Tenancy, RBAC

```
PHASE 2 — P1 IDENTITY / TENANT / RBAC (§113 P1)

This phase decides whether the product is secure. Treat every shortcut here as
a future breach.

SCOPE
1. Tenant model (§50): tenant types individual, teacher, school, course_center,
   enterprise. Every tenant-owned entity carries tenant_id from this point on —
   no exceptions, no retrofitting later.
2. Identity: users, secure password hashing, token handling, session/refresh
   strategy (§78). Document the choice in an ADR (§101).
3. RBAC (§53): SUPER_ADMIN, TENANT_ADMIN, SCHOOL_ADMIN, TEACHER, STUDENT,
   PARENT. Permissions explicit and enumerated. Never assume everyone inside a
   tenant may see everything.
4. Tenant isolation enforced server-side (§51). Never trust a client-supplied
   tenant_id or role. Implement isolation at the repository/query layer so it
   cannot be forgotten in a route handler. Evaluate PostgreSQL Row Level
   Security for sensitive tables and record the decision in an ADR either way.
5. Parent–student and teacher–student relationships (§81), since minor safety
   depends on them existing from the start.
6. Audit records for permission, role, and tenant changes (§131).
7. Auth API: register, login, refresh, logout, me. Typed Pydantic contracts
   (§128). Rate limiting on auth endpoints (§78).
8. Frontend: login, session handling, route protection. No authorization logic
   that only exists in the frontend.

MANDATORY TESTS (§52, §88 — this is not optional)
- positive access test per tenant-scoped resource
- negative cross-tenant test: Tenant A accessing Tenant B's resource MUST FAIL
- role permission tests for every role above
- token expiry, refresh, and revocation
- password hashing verification
- rate limit behavior

DEFINITION OF DONE
§145 quality gate + §149 SaaS DoD (tenant scope, authorization, auditability,
security, testing). Tell me explicitly which cross-tenant tests exist and
what they assert.

Give me the §122 report first. STOP for approval.
```

---

## PHASE 3 — P2 Education Domain & Curriculum

```
PHASE 3 — P2 EDUCATION MODEL (§113 P2)

SCOPE
1. Domain hierarchy (§19): Curriculum → Subject → Topic → Concept → Skill →
   Prerequisite → Assessment relationship.
2. Curriculum versioning (§20). Curriculum data MUST be versioned. Never model
   it as permanently immutable. Support MEB curriculum and Türkiye Yüzyılı
   Maarif Modeli structure: grade level, subject, topic, learning outcome,
   skill, prerequisite.
3. Prerequisite graph: skill-to-skill dependencies, with cycle detection
   enforced at write time.
4. Skill facets (§28): recognition, recall, application, transfer, retention
   must be representable as distinct dimensions of the same skill. They are not
   interchangeable and must not collapse into one column.
5. Physics as the first domain, NOT as a hard-coded assumption (§2). No table,
   enum, or code path may assume the subject is Physics.
6. Seed data: one real Physics slice — Mechanics → Force → Newton's Second Law
   with its prerequisites and skill facets. Real curriculum content, not lorem
   ipsum.
7. CRUD API for curriculum, tenant-scoped and role-gated. Typed schemas (§128).
8. Database constraints over application assumptions (§132): FKs, tenant-scoped
   uniqueness, check constraints, non-null where invariant.

DEFINITION OF DONE
§145 gate. Plus: demonstrate that adding a second subject (e.g. Chemistry)
requires only data, no code change. Show me the query or seed that proves it.

Give me the §122 report first. STOP for approval.
```

---

## PHASE 4 — P3 Assessment, Observation, Evidence

```
PHASE 4 — P3 ASSESSMENT / OBSERVATION / EVIDENCE (§113 P3)

The separation in this phase is the scientific foundation of the product. If
observation and evidence blur together here, the PDE is worthless later.

SCOPE
1. Assessment as a first-class domain (§21): diagnostic, formative, retrieval
   practice, application, transfer, delayed retention. Each assessment record
   preserves: what was asked, targeted skill, difficulty, content version,
   learner response, evaluation method, evaluation confidence, timestamp.
2. Questions and attempts, tenant-scoped, content-versioned.
3. Observations (§22): directly recorded facts only. An observation MUST NOT
   contain a hidden conclusion. Model the event types listed in §22.
4. Evidence (§23): interpreted signals derived from observations, stored
   SEPARATELY, with a foreign key to the originating observation. Never store
   an inference as if it were a raw observation.
5. Evidence quality attributes (§27): directness, recency, reliability, task
   validity, transfer relevance, evaluation confidence. A trivial recognition
   success must not be able to outweigh multiple transfer failures — encode
   that as a property, not a comment.
6. Event sourcing (§40): immutable event log with event ID, tenant ID, actor,
   subject, timestamp, event type, payload, schema version, correlation ID,
   provenance. Historical events MUST NOT be mutable. Enforce append-only at
   the database level, not by convention.
7. Provenance on all derived data (§41).
8. Idempotent event ingestion (§130).
9. API: submit attempt, record observation, query evidence. Tenant-scoped.

MANDATORY TESTS
- an observation record cannot carry an interpreted conclusion (schema-enforced)
- evidence always traces to at least one observation
- event log rejects updates and deletes
- duplicate event submission is idempotent
- cross-tenant negative tests (§52)

DEFINITION OF DONE
§145 gate + append-only enforcement demonstrated by a failing-write test.

Give me the §122 report first. STOP for approval.
```

---

## PHASE 5 — P4 Knowledge State & Bayesian Model

```
PHASE 5 — P4 KNOWLEDGE STATE / BAYESIAN ENGINE (§113 P4)

THIS PHASE HAS TWO STEPS. Do not merge them.

STEP 5A — MATHEMATICS FIRST, NO CODE (§25)
The mathematical model MUST be documented before implementation. Produce an
ADR at docs/adr/ containing:
- hypothesis
- mathematical formulation (Beta-Binomial for binary mastery evidence, per §25,
  unless you argue otherwise)
- assumptions, stated explicitly
- how evidence quality (§27) weights into the update
- how recency and decay are handled
- expected behavior, including monotonicity properties
- edge cases: zero evidence, contradictory evidence, very old evidence
- how the five facets (§28) are modeled separately
- model_version scheme
- what would falsify the model (§39)
Write NO implementation code in Step 5A. STOP for my approval of the ADR.

STEP 5B — IMPLEMENTATION (after ADR approval)
1. Knowledge state per (learner, skill) (§24): mastery_probability, confidence,
   evidence_count, recency/last_observed_at, retention estimate, transfer
   performance, model_version.
2. Knowledge state is an ESTIMATE, never a fact. No `mastery = true` boolean
   unless there is a documented deterministic reason (§24).
3. Bayesian update service consuming Evidence from Phase 4.
4. Language discipline (§26): the system never claims a learner "knows" a
   skill. Estimated / likely / evidence suggests / high confidence / low
   confidence / insufficient evidence. Enforce this in the API response
   vocabulary, not just the UI copy.
5. Misconception representation (§31) as a distinct signal requiring supporting
   evidence. An incorrect answer MUST NOT set misconception = true.
6. model_version stamped on every state record (§42).

MANDATORY TESTS (§87 property-based)
- probabilities remain in [0,1] under every input sequence
- Bayesian updates are monotonic under the assumptions stated in the ADR
- impossible values are rejected
- identical evidence sequences produce identical states (reproducibility, §99)
- timestamps behave correctly across timezones
- low-quality positive evidence does not outweigh high-quality negative evidence

DEFINITION OF DONE
§147 (PDE DoD): mathematical formulation + assumptions + implementation + unit
tests + edge-case tests + reproducibility tests + versioning + provenance, all
addressed.

STOP after 5A. STOP again after 5B.
```

---

## PHASE 6 — P5 Prometheus Decision Engine

```
PHASE 6 — P5 PROMETHEUS DECISION ENGINE (§113 P5)

This is the product (§6, §150). PDE, not Prometheus/Grafana.

SCOPE
1. Decision engine input (§32): learner context + knowledge state + evidence +
   educational policy + available actions + constraints.
2. Structured decision output (§32): decision_id, learner_id, skill_id,
   selected_action, candidate_actions, scores, reason_codes, policy_version,
   model_version, confidence, created_at. Never an untyped dict (§128).
3. Candidate action set (§34), all of them: new concept explanation, retrieval
   question, easier task, harder task, transfer task, review task, delayed
   retention assessment, hint, worked example, teacher intervention, defer
   decision, insufficient-evidence action. The engine must not collapse into
   always choosing one action type — test for that.
4. MANDATORY SEPARATION (§35): knowledge state (what the system believes) is
   separate from decision policy (what should follow). Separate modules,
   separate versioning.
5. Content strategy vs learner policy separation (§36). Do not personalize
   aggressively from sparse evidence.
6. Authorization layer (§37): PDE decision → authorization → allow/reject/
   escalate. Decision generation and authorization MUST be separate components.
   Authorization inputs: role, tenant policy, educational policy, safety
   policy, consent, age rules, configuration, confidence threshold, feature
   flags.
7. Explainability (§33): every decision traceable to learner, skill,
   observations, evidence, knowledge state, model version, policy version,
   candidate actions, scoring, constraints, authorization result.
8. Decision logging (§85) answering all twelve questions listed there.
9. Shadow Mode (§38): new algorithms produce hypothetical decisions that are
   logged and do not affect learners. Build this now, not later — it is how
   every future change ships safely.
10. Feature flags (§96) for policy rollout.
11. API: request next action for a learner+skill, retrieve decision explanation,
    query decision history.

MANDATORY TESTS
- reproducibility: identical inputs + versions produce identical decisions (§99)
- action diversity: the engine selects different action types across scenarios
- authorization rejects what policy forbids, and rejection is logged
- shadow decisions never reach the learner-facing path
- explanation completeness for every decision
- cross-tenant negative tests

DEFINITION OF DONE
§147 fully satisfied, including shadow-mode consideration.

Give me the §122 report first. STOP for approval.
```

---

## PHASE 7 — P6 Transfer, Retention, Falsification

```
PHASE 7 — P6 TRANSFER / RETENTION / FALSIFICATION (§113 P6)

SCOPE
1. Transfer tasks (§29): a transfer task changes surface characteristics while
   preserving the underlying skill. Model the relationship explicitly so the
   system can distinguish memorization ≠ conceptual understanding ≠ transfer.
   Transfer outcomes become evidence.
2. Delayed retention (§30): 14-day and 28-day checkpoints. Retention records
   preserve original learning event, skill/concept, elapsed time, delayed
   assessment, result, evidence, retention estimate, model version. Never
   reduce retention to a single unexplained percentage.
3. Scheduling for retention checkpoints via background jobs (§94) or n8n (§92).
   If n8n: the schedule trigger may live in n8n, but the retention logic MUST
   live in application code. n8n is not the source of truth.
4. Falsification framework (§39): explicit hypotheses with evidence →
   prediction → action → outcome → supported / not supported / inconclusive.
   The system must be able to record that it was wrong.
5. Failure-mode discrimination (§31): lack of knowledge vs retrieval failure vs
   careless error vs misconception vs transfer failure vs retention failure.

MANDATORY TESTS
- temporal behavior: retention checkpoints fire at the right elapsed time,
  including across DST and timezone boundaries
- a transfer failure produces appropriately weighted negative evidence
- falsification records can express "not supported" and this changes nothing
  silently — it surfaces
- reproducibility of retention estimates

DEFINITION OF DONE
§147. Plus: the §115 MVP loop is now testable end to end.

Give me the §122 report first. STOP for approval.
```

---

## MVP GATE — run before Phase 8

```
MVP GATE (§115)

Do not implement anything. Verify and report.

Demonstrate, with real data and a real test run, that this loop works
end to end:

Student → Physics Skill → Assessment → Observation → Evidence →
Knowledge State → Prometheus Decision → Next Task → Transfer → Retention

with all six requirements from §115:
- persistent data
- reproducible decisions
- explainability
- tests
- authorization
- provenance

Produce:
1. An end-to-end trace of one real learner journey, with the actual decision
   record and its full explanation.
2. A test-run report per layer (unit / integration / api / e2e).
3. §145 quality gate status for every phase 1–7 feature.
4. A list of everything deferred so far, and whether each is safe to defer.
5. An explicit PASS or FAIL verdict on the MVP definition. Do not hedge.

If FAIL, tell me exactly what is missing and stop.
```

---

## PHASE 8 — P7 AI Gateway & LLM Integration

```
PHASE 8 — P7 AI GATEWAY (§113 P7)

LLMs are supporting components, never the source of truth (§43).

SCOPE
1. AI Gateway (§45), the single path for all production-relevant LLM calls.
   Must support: provider selection, model selection, capability detection,
   prompt versioning, structured output, retries, timeout, fallback, usage
   accounting, token tracking, cost tracking, safety validation, logging,
   model metadata.
2. Model router (§43): Ollama local-first (§44), external providers optional.
   Application business logic MUST NOT depend on a specific provider.
3. Cost escalation ladder (§48): cheap deterministic logic → local model →
   small external model → large external model. Do not route everything to the
   most expensive model. AI usage must be measurable.
4. LLM output is untrusted input (§47): request structured output, validate
   schema, reject malformed output, validate educational constraints, preserve
   provenance, record model and prompt versions.
5. Permitted LLM responsibilities only (§46): question generation, explanation
   generation, feedback, content drafting, semantic classification,
   natural-language analysis, teacher assistance, content transformation.
   LLMs MUST NOT replace deterministic logic — and specifically must not touch
   PDE decision-making.
6. Educational safety (§82): validation, provenance, teacher review path,
   structured constraints, content versioning. Never assume a confident LLM is
   a correct LLM.
7. External data transfer check (§136): before any learner data leaves the
   system, verify necessity, privacy, authorization, tenant policy, data
   minimization, configuration, provider requirements. Default posture: learner
   data does not leave. Document any exception explicitly.
8. RAG (§49) only if the audit justifies it now. RAG MUST NOT substitute for
   structured curriculum data. Curriculum structure stays in the database.

MANDATORY TESTS
- malformed LLM output is rejected, not coerced
- provider failure triggers documented fallback
- timeout and retry behave as specified
- cost and token tracking are accurate per request
- prompt version and model version appear in provenance
- no code path lets an LLM alter knowledge state or a decision

DEFINITION OF DONE
§148 (AI DoD): provider abstraction + structured output + validation + timeout
+ retry + cost tracking + usage tracking + prompt version + model version +
safety validation + fallback.

Give me the §122 report first. STOP for approval.
```

---

## PHASE 9 — P8 Dashboards

```
PHASE 9 — P8 DASHBOARDS (§113 P8)

Analytics philosophy (§74): do not build 37 charts. Build answers.

SCOPE
1. Student dashboard (§75): current learning state, progress, next action,
   completed skills, weak skills, retention, transfer. Motivation elements only
   where educationally appropriate. Do not overwhelm students with technical
   metrics — no raw mastery_probability floats in the student UI.
2. Teacher dashboard (§76), answering exactly these questions: Which students
   need attention? Which skills are weak? Which students are improving? Which
   are forgetting? Which misconceptions appear? What should I do next?
3. Admin dashboard (§77): active students, active teachers, adoption, usage,
   learning outcomes, class performance, retention, system health,
   subscription. Do not expose unnecessary sensitive learner information (§80).
4. Frontend product principle (§18) and §17 aesthetics. Responsive, accessible,
   fast, mobile-friendly. No authoritative business logic in the frontend.
5. Explainability surfaced to teachers: a teacher must be able to see why the
   system recommended what it did (§33), in plain Turkish-appropriate language
   that does not overclaim mastery (§26).
6. Aggregation endpoints, tenant-scoped and role-gated, with pagination and
   filtering (§89).

MANDATORY TESTS
- a teacher sees only their own students; a school admin only their school
- students cannot access teacher or admin views
- parents see only their own children
- aggregation queries cannot leak across tenants
- accessibility checks on the main flows

DEFINITION OF DONE
§145 + §149. Every dashboard number traceable to a query, not to a hardcoded
demo value (§105).

Give me the §122 report first. STOP for approval.
```

---

## PHASE 10 — P9 Usage, Entitlements, Billing

```
PHASE 10 — P9 SAAS LAYER (§113 P9)

SaaS functionality MUST be separated from core learning logic (§59).

SCOPE
1. SaaS entities (§59): Tenant, Plan, Subscription, Entitlement, Usage,
   Invoice, Payment — in their own module, not woven into education code.
2. Entitlement system (§60). NO scattered `if user.plan == "pro"` checks
   anywhere. Plan → Entitlements → Tenant/User → Feature Access. Pricing plans
   must be able to change without rewriting business logic.
3. Pricing configurable, never hard-coded (§63).
4. Usage metering (§65): AI requests, token usage, model usage, generated
   questions, student attempts, assessments, storage, API calls, teacher usage,
   active learners. Records must support billing, cost analysis, abuse
   prevention, and product analytics.
5. Unit economics measurability (§64): the data model must make MRR, ARR, ARPU,
   ARPA, churn, retention, conversion, activation, expansion revenue, gross
   margin, AI cost per user, and AI cost per learning session computable.
   Computing them is not this phase; making them computable is.
6. Billing isolation (§95) and idempotent payment/webhook handling (§130).
7. Audit records for billing and plan changes (§131).
8. Keep it simple (§114): no elaborate enterprise billing yet.

MANDATORY TESTS
- entitlement checks cannot be bypassed by direct API call
- usage records are idempotent under retry
- a tenant cannot read another tenant's usage, invoice, or subscription
- plan change takes effect without a code deploy

DEFINITION OF DONE
§149 (SaaS DoD): tenant scope + authorization + entitlement + usage metering +
billing implications + auditability + security + testing.

Growth guardrail (§112, §144): confirm in your report that nothing added here
optimizes engagement at the expense of learning outcomes.

Give me the §122 report first. STOP for approval.
```

---

## PHASE 11 — P10 Hardening, Observability, Performance, Deployment

```
PHASE 11 — P10 PRODUCTION READINESS (§113 P10)

SCOPE
1. Security hardening (§78), full sweep: authentication, password hashing,
   token handling, RBAC, tenant isolation, rate limiting, input validation,
   output validation, SQL injection, XSS, CSRF, secure headers, secret
   management, audit logging, dependency auditing, safe file handling.
2. Secrets audit (§79): scan the entire git history, not just the working tree.
   Report anything found; do not rewrite history without my instruction.
3. Observability (§83): metrics, logs, traces, errors, audit events, decision
   logs. Prometheus/Grafana (the metrics stack), Loki, Sentry as appropriate.
   Local development must stay lightweight.
4. Log hygiene (§84): verify no passwords, API keys, tokens, learner-sensitive
   data, or confidential institutional data reach the logs.
5. Privacy (§80): data minimization, purpose limitation, retention policies,
   secure deletion where legally required. Every telemetry field must have a
   documented purpose — list any that don't and propose removal.
6. Minor safety review (§81): parental relationships, teacher oversight,
   consent, age-related policies. High-impact educational decisions must be
   reviewable by a human.
7. Performance (§109) and load testing. Establish baselines before optimizing.
8. Reproducibility (§99) verification across the whole PDE path.
9. Backward compatibility review (§107) and API versioning (§128).
10. Deployment (§119, §120): cloud-ready architecture without cloud lock-in.
    Still no Kubernetes (§114, §135).
11. Documentation (§102) and ADR completeness (§101).

DELIVERABLE
A production readiness report against §137, plus the §145 gate applied to the
system as a whole. Include a prioritized remediation list — do not fix
everything in one pass.

Give me the §122 report first. STOP for approval.
```

---

## REUSABLE — Single Slice Prompt

For any individual feature between or within phases:

```
SLICE: <name>

Read CLAUDE.md. Implement this as one vertical slice (§126):
Domain → Database → Application Service → API → Frontend → Tests.

Requirement: <describe the behavior, not the implementation>

Constraints:
- smallest coherent change (§125)
- tenant-scoped and authorized (§51, §53)
- Alembic migration if the schema changes (§127); never edit an existing one
- typed Pydantic contracts, no bare dicts (§128)
- provenance and versioning where applicable (§41, §42)
- no new dependency without justifying it against §104
- no LLM call replacing deterministic logic (§46)

Give me the §122 Pre-Implementation Report first. STOP for approval.
Then implement, run tests, show me the diff, and report the §145 gate.
```

---

## REUSABLE — Review Prompt

Run this after any phase, in a fresh session, before you approve:

```
REVIEW — read-only. Change nothing.

Review the work in <commit range or branch> against CLAUDE.md.

Check specifically:
1. Tenant isolation — is there any query path that can escape tenant scope?
   Show me the enforcement point (§51).
2. Authorization — any endpoint reachable without the correct role? (§53)
3. Observation/Evidence separation — any inferred conclusion stored as a raw
   observation? (§22, §23)
4. Overclaiming — anywhere the system asserts mastery as fact? (§24, §26)
5. Fake implementations — hardcoded values, stubs pretending to work,
   tests passing for the wrong reason? (§105)
6. Hidden behavior — undocumented background jobs, silent AI calls,
   side effects not visible from the call site? (§106, §135)
7. Provenance and versioning gaps (§41, §42)
8. Secrets, in the working tree and in the diff (§79)
9. Migration safety — anything destructive or unreviewed? (§127)
10. Domain boundary erosion — is any module becoming the giant one? (§54)

Report findings by severity using the §134 priority order. Cite file and line.
Propose fixes but implement nothing. STOP.
```

---

## Sequencing summary

| Phase | CLAUDE.md priority | Output | Gate |
|---|---|---|---|
| 0 | — | Audit report | Approve findings |
| 1 | P0 | Running skeleton | `compose up` + tests green |
| 2 | P1 | Identity, tenancy, RBAC | Cross-tenant tests pass (§52) |
| 3 | P2 | Curriculum & skills | Second subject needs no code |
| 4 | P3 | Assessment / observation / evidence | Append-only log enforced |
| 5 | P4 | Knowledge state (ADR first) | §147 |
| 6 | P5 | Decision engine | §147 + reproducibility |
| 7 | P6 | Transfer / retention / falsification | §147 |
| — | — | **MVP GATE** | §115 PASS |
| 8 | P7 | AI gateway | §148 |
| 9 | P8 | Dashboards | §145 + §149 |
| 10 | P9 | SaaS layer | §149 |
| 11 | P10 | Hardening & deployment | §137 |
