# EduPulse AI — Roadmap

Date: 2026-09-01. Reconciles two naming schemes that exist only in commit
messages/ADR addenda today: CLAUDE.md §113's P0–P10 phase ladder, and the
ad-hoc "Roadmap Stage A–E" label five post-MVP commits used. This is the
first place both are written down together.

## Done: P0–P10 (Phases 1–10) + MVP Gate

All of §113's P0–P10 phases are built (verified this session: 236/236
backend tests, 34/34 frontend tests, ruff/tsc clean — see
`docs/PROJECT_STATUS.md`). `docs/audit/MVP-GATE.md` recorded **PASS** for
the §115 loop (Student → Skill → Assessment → Observation → Evidence →
Knowledge State → PDE Decision → Next Task → Transfer → Retention) on
2026-08-28, against Phases 1–7; Phases 8–10 (AI Gateway, dashboards, SaaS
entitlements v1, security/observability hardening, load testing) followed
and are also complete.

## Done: Roadmap Stage A–E (post-MVP-gate slices)

These closed specific gaps `MVP-GATE.md` §4 had flagged as real but
deferrable:

| Stage | What | Commit |
|---|---|---|
| A.1 | Admin-initiated student/staff enrollment (`POST /auth/tenant/users`) | `e8099dd` |
| A.2 | Automated e2e MVP learning-loop test | `5ae5d30` |
| A.3 | Second subject (Chemistry) proven with zero code changes | `75b6433` |
| A.4 | Role/tenant-education-policy authorization gap — documented deliberate deferral, not a fix | `2633292` |
| B.1 | AI skill-explanation UI on the student dashboard | `51985a9` |
| B.2 | Parent portal | `c506e1d` |
| C | Narrow SaaS entitlement system (Plan/Entitlement, AI-quota gating) | `fed5f52` |
| D | 5-facet knowledge-state read path batched (perf) | `3b3c9a4` |
| — | Rebrand, login-redirect fix, self-service password reset, 4 backfilled ADRs | `fa34db5`, `7643c37`, `ca51aa6`, `4e2ae78` |
| E | Tenant seat-limit entitlement (`MAX_TENANT_USERS`), ADR-016 addendum | `0911776` (this session) |

## What's next — P0/P1/P2/P3

Framed per the priority tiers requested in the master-prompt message
(P0=blocking, P1=critical, P2=important, P3=later). Every item below is
grounded in something already flagged as real and deferred — in
`MVP-GATE.md` §4, an ADR's own falsifiability trigger, or a concrete
finding from this audit (`docs/PROJECT_STATUS.md` §Known drift) — not a
speculative new feature list.

### P0 — blocking nothing, but zero-cost to fix now
- **Fix ADR-012's stale `Status: Proposed` header to `Accepted`.** The
  model it describes has been in production since Phase 5. One-line
  documentation fix, S effort, no code/behavior change.

### P1 — critical for the next real pilot (not for MVP itself)
- **Role/tenant-education-policy authorization** (ADR-013 addendum 2).
  Trigger already defined: a second pilot tenant needing genuinely
  different authorization behavior than the first. Do not build this
  speculatively before that trigger fires (§125/§141) — but track it as
  the literal next thing to revisit once a second real tenant exists.
- ~~**Execution layer**~~ — **CLOSED (this session, ADR-021)**: `GET
  /decisions/{id}/task` resolves a Decision's `selected_action` to a real
  `Question` (never fabricated, §105); the student dashboard's "Başla"
  button lets a student answer it through the existing
  `POST /assessment/attempts`. 6 of 12 `CandidateActionType`s are
  task-resolvable by design (ADR-021); the other 6 are deliberately not
  question-answering activities. **Residual scope**: no execution UI yet
  for the 6 non-question actions (still label-only, honest given no
  content system backs them), and `NoQuestionAvailable` is a real,
  surfaced content gap for skills without questions in the resolved
  facet — not a code bug, see ADR-021 "What Is Explicitly Not Built."

### P2 — important, ADR-016 has already named the trigger
- **A third gated `EntitlementKey`** — the same narrow pattern that
  `AI_EXPLANATIONS_MONTHLY_LIMIT` and `MAX_TENANT_USERS` already
  established (new key + one `enforce_*` function + one call site). No
  candidate feature is named yet; add one only when a real feature needs
  gating (ADR-016 §Consequences), not preemptively.
- **Self-service plan upgrade flow.** Today plan assignment is an
  admin/script action (`scripts/seed_school_plan.py`). Turning this into
  a customer-facing upgrade path is explicitly still unbuilt per ADR-016
  §"What Is Explicitly Not Built" — worth doing once there is a second
  real tier a tenant would plausibly self-upgrade into.

### P3 — later, real money required first
- **Billing domain** (`Subscription`, `Invoice`, `Payment`). ADR-016's
  second falsifiability trigger: "real billing (money) needs to exist."
  Nothing in the codebase requires this before then (§116). When it
  fires, this is new modeling work, not an extension of the existing
  narrow entitlement system (ADR-016 says so explicitly) — plan it as
  its own ADR, not a patch to ADR-016.
- **Open-ended (non-auto-gradable) delayed-retention grading**
  (ADR-014's narrow v1 constraint). Revisit once a real pilot's content
  needs free-response retention checks, not before.
- **A second AI provider** beyond Ollama (§140 routing strategy). The
  `OLLAMA_BASE_URL` swap point already exists in the AI Gateway
  (ADR-015); adding a second provider is infrastructure-adapter work,
  not a redesign — but there is no current cost/quality/latency pressure
  forcing it yet.

## Explicitly not on this roadmap

Per §114 and ADR-016/ADR-017's own "what's not built" sections: no
Kubernetes, no microservice split, no enterprise SSO, no marketplace, no
mobile native app. None of these have a real trigger yet; adding them
before one exists would be exactly the "designing for a hypothetical
requirement" §125/§141 warn against.
