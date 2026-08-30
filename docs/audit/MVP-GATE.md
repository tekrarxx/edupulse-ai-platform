# MVP Gate Report

Status: PASS
Date: 2026-08-28
Related: CLAUDE.md §115 (MVP definition), §113 P0–P6 (Phases 1–7)

Read-only verification per the Phase doc's MVP Gate prompt. Nothing was
implemented in producing this report; it verifies Phases 1–7 as committed
(`e39a925`..`8b5b121`).

---

## 1. End-to-End Trace of One Real Learner Journey

Run against the real local Docker stack (`docker compose up -d`, Postgres,
not the SQLite test fallback), through genuine HTTP calls to the running
API — not test fixtures. Curriculum: the real seeded Physics slice
(`scripts/seed_curriculum.py`) — Fizik → Mekanik → Kuvvet → **Newton'un
İkinci Hareket Yasası** (F = m·a). Learner: a real `STUDENT` account
(`mvp-student@example.com`) provisioned in a real `SCHOOL`-type tenant.

### Step 1 — Assessment → Observation → Evidence

5 real graded `APPLICATION`-facet attempts submitted via `POST
/assessment/attempts`, all correct (F = m·a computations). Each call
produced a real `Attempt`, an append-only `Observation`
(`answer_correct`), and an `Evidence` row (§21–§23).

### Step 2 — Knowledge State (Phase 5)

`GET /knowledge-state?skill_id=...` after the 5th attempt:

```
application: mastery_probability=0.857, confidence_label=high_confidence, evidence_count=5
recognition, recall, transfer, retention: mastery_probability=0.5, confidence_label=insufficient_evidence
```

Facet independence holds exactly as ADR-012 specifies: only the facet with
real evidence moved off the prior.

### Step 3 — Prometheus Decision (Phase 6)

`POST /decisions/next-action?skill_id=...` (as the student):

```
selected_action: transfer_task
reason_codes: [high_mastery_application, transfer_not_yet_evidenced]
authorization_result: allowed
policy_version: pde-policy-v1
model_version: bayesian-beta-binomial-v1
confidence (score margin): 0.143
all 12 candidate actions scored, e.g. harder_task=0.714, review_task=0.571,
  retrieval_question=0.15, teacher_intervention=0.05, ...
evidence_ids: [5 real Evidence ids]
```

`GET /decisions/{id}` returned the identical record with full explanation
(§33); `GET /decisions?skill_id=...` returned it in history — the decision
is durable, not a one-shot computation.

### Step 4 — Retention Checkpoints Auto-Scheduled (Phase 7)

Confirmed by `GET /retention/checkpoints`: exactly two checkpoints (14-day,
28-day), both `status=pending`, each carrying a **frozen** `Hypothesis`
(`predicted_mastery_probability=0.857`, `predicted_confidence_label=
high_confidence`, `verdict=pending`) — created automatically inside the
5th attempt's evaluation, no separate call needed.

### Step 5 — Transfer Task (following the decision)

A real `TRANSFER`-facet question (surface-varied: friction added, new
numbers) answered incorrectly. `GET /assessment/evidence` shows:
`facet_type=transfer, polarity=negative, failure_mode=transfer_failure` —
set automatically per ADR-014, no human classification needed for a
structural fact.

### Step 6 — Delayed Retention Completion + Falsification (Phase 7)

The 14-day checkpoint's `scheduled_for` was moved to the past (simulating
elapsed time — no scheduler exists yet, see §4 below) and it correctly
appeared in `GET /retention/checkpoints/due`. Completed via `POST
/retention/checkpoints/{id}/complete` with a real correct answer:

```
status: completed
retention_estimate: 0.875 (recomputed APPLICATION mastery_probability)
hypothesis.actual_is_correct: true
hypothesis.verdict: supported   (predicted 0.857 > 0.5, actual correct → match)
```

**The full §115 loop is demonstrated end to end on real, persistent data**:
Student → Physics Skill → Assessment → Observation → Evidence → Knowledge
State → Prometheus Decision → Next Task (transfer) → Transfer → Retention →
Falsification verdict.

---

## 2. Test-Run Report Per Layer

Run just now, fresh, full suite (Postgres-backed, real Alembic migration
chain, not `create_all`):

| Layer | Location | Result |
|---|---|---|
| Unit | `tests/unit/` | 45 passed |
| Integration | `tests/integration/` | 3 passed |
| Security | `tests/security/` | 9 passed |
| API | `tests/api/` | 69 passed |
| **Total** | | **126 passed, 0 failed** |
| Frontend | `apps/web/__tests__/` | 2 test files (login page, status badge) — not re-run in this pass; frontend has not progressed past the Phase 1/2 auth skeleton, see §4 |

**Update (Roadmap Stage A, 2026-08-30)**: `tests/e2e/test_mvp_learning_loop.py`
now exists — the exact §1 journey above, automated as one real, CI-repeatable
pytest test against the same Postgres-backed fixtures every other API test
uses. The gap this section originally described is closed; see the updated
row in §4's table.

Cross-tenant negative tests (§52) exist for every tenant-scoped resource
added since Phase 2: auth/tenant users, curriculum, assessment/evidence,
knowledge-state, decisions, retention checkpoints — 6+ dedicated
cross-tenant test functions plus the dedicated `tests/security/
test_tenant_isolation.py` suite.

---

## 3. §145 Quality Gate, Per Phase

| Phase | Impl. | Migration | Unit | API | Security/tenant | Docs/ADR | Notes |
|---|---|---|---|---|---|---|---|
| 1 — P0 Foundation | ✅ | ✅ (0001) | ✅ | ✅ (health) | n/a | README | |
| 2 — P1 Identity/RBAC | ✅ | ✅ (0002) | ✅ | ✅ | ✅ | ADR-002, ADR-011 | |
| 3 — P2 Curriculum | ✅ | ✅ (0003) | ✅ (prereq cycle) | ✅ | ✅ | — | 2nd-subject-needs-no-code demonstrated (Roadmap Stage A, `tests/e2e/test_second_subject_chemistry.py`) |
| 4 — P3 Assessment/Evidence | ✅ | ✅ (0004) | ✅ (traceability) | ✅ | ✅ | — | append-only enforced by Postgres trigger |
| 5 — P4 Knowledge State | ✅ | ✅ (0005) | ✅ (property-based) | ✅ | ✅ | ADR-012 | reproducibility fixed to float-tolerance this session |
| 6 — P5 Decision Engine | ✅ | ✅ (0006) | ✅ (property + scenario) | ✅ | ✅ | ADR-013 | shadow mode data-level only, no execution layer (by design, §113 P8+) |
| 7 — P6 Transfer/Retention/Falsification | ✅ | ✅ (0007) | ✅ (verdict rule) | ✅ | ✅ | ADR-014 | scheduler/n8n trigger not wired (§4) |

No secrets in the tree (`.env` gitignored, `.env~` stray file present but
untracked — flagged, not committed). No unrelated regressions: full suite
green after every phase's commit in this session.

---

## 4. Deferred Items — What's Missing and Is It Safe to Defer

| Item | Deferred since | Safe to defer for MVP? | Why / when to close |
|---|---|---|---|
| ~~Retention-checkpoint scheduler (cron/n8n)~~ — **CLOSED in Phase 10** (`ADR-014` addendum, `docker-compose.yml` `n8n` service, `infrastructure/n8n/workflows/retention-checkpoint-scheduler.json`). Verified end to end via `n8n execute` against the real local API, both with zero and with one real due checkpoint. **Residual, still-open scope**: single-tenant per activated workflow copy (documented, by design — no cross-tenant staff endpoint exists, §52); not yet run unattended over real wall-clock time; still does not deliver the retention check to the student or send a notification (no content-delivery or notification channel exists yet). | Phase 7 | — | See ADR-014 addendum and `infrastructure/n8n/workflows/README.md`. |
| ~~Consent/age-based decision authorization~~ — **CLOSED in Phase 10** (`ADR-013` addendum, migration `0009`, `POST /auth/tenant/users/{id}/date-of-birth`, `POST /auth/tenant/parent-links`). A minor with no recorded guardian consent now has every otherwise-`ALLOWED` decision escalated instead of auto-executed, verified end to end against a live decision. **Residual scope, now a deliberate deferral, not an open unknown** (Roadmap Stage A, ADR-013 Addendum 2): role- and tenant-education-policy-based authorization checks remain unimplemented, decided to not block a first pilot — see the addendum for the full reasoning and the concrete trigger for revisiting it (a second pilot tenant needing different policy behavior). An unrecorded date of birth is treated as "unknown," not "adult," so students who existed before this migration — or who never had a date of birth recorded — are not protected by the consent/age gate until an admin records it, an operational rollout step for the next real pilot, not a code gap. | Phase 6 | — | See ADR-013 addenda 1 and 2. |
| Execution layer (actually serving the decided task to a student) | Phase 6 | **Yes** | Explicitly out of scope per the Phase 6 plan — belongs to Phase 9 dashboards/content delivery. The loop is provably correct up to "decision," which is what §115 asks for. |
| Open-ended delayed-retention grading | Phase 7 | **Yes** | v1 requires auto-gradable questions so the falsification verdict has a definite outcome. Narrow, documented constraint (ADR-014). |
| ~~`tests/e2e/` automated suite~~ — **CLOSED (Roadmap Stage A, 2026-08-30)**: `tests/e2e/test_mvp_learning_loop.py` automates this exact §1 trace end to end (enrollment through the real admin-enrollment API → curriculum → 5 attempts → knowledge state → Prometheus decision → auto-scheduled retention → transfer failure → backdated-checkpoint completion → falsification verdict), against real Postgres, in the ordinary pytest run. | Phase 1 (never built) | — | One golden-path journey by design — does not replace the targeted unit/API/security suites, which remain the place for edge cases and negative tests. |
| Admin/staff-initiated student enrollment into an existing tenant | Phase 2 | **Yes for now, but noticed** | `/auth/register` only self-provisions a fresh individual tenant + STUDENT. There is no API for a school admin to add a specific student to their tenant — this session had to seed the student directly via a DB script to build the trace. Real schools will need this before Phase 9/pilot. |
| ~~Second subject (e.g. Chemistry) demonstrated with zero code changes~~ — **CLOSED (Roadmap Stage A, 2026-08-30)**: `scripts/seed_curriculum_chemistry.py` (a real Kimya > Kimyasal Bağlar > İyonik Bağ slice) + `tests/e2e/test_second_subject_chemistry.py` run assessment, knowledge-state, and Prometheus decision generation against it, automated, through the exact same code paths as the Physics e2e test. Zero code changes were needed — only new curriculum rows. | Phase 3 | — | — |
| `.env~` stray untracked file | Session start | **Yes** | Pre-existing, untracked, not committed — likely an editor backup. Should be deleted or added to `.gitignore` if it recurs. |
| ADR-001/003–010 from §101's suggested initial set (modular-monolith, event-sourcing, AI-gateway, shadow-mode, SaaS-entitlements, local-first) | Various | **Yes** | Not required until those systems exist (AI Gateway is Phase 8, SaaS is Phase 10). Current ADRs (ADR-002, 011, 012, 013, 014) cover everything actually built. |

---

## 5. Verdict

# PASS

The §115 MVP loop — Student → Physics Skill → Assessment → Observation →
Evidence → Knowledge State → Prometheus Decision → Next Task → Transfer →
Retention — works end to end against real, persistent Postgres data, with:

- **persistent data**: every step above is a committed database row,
  verified by re-querying after the fact, not held in memory.
- **reproducible decisions**: `policy_version`/`model_version` stamped on
  every Decision and Knowledge State row; property-based tests enforce
  reproducibility at the unit level (§99).
- **explainability**: `GET /decisions/{id}` returns the full trace — every
  candidate action's score and reason codes, the knowledge-state snapshot,
  contributing evidence ids, and the authorization verdict.
- **tests**: 126/126 passing across unit, integration, security, and API
  layers, including the property-based and cross-tenant-negative tests
  §87/§52 mandate.
- **authorization**: a real, separate authorization step ran and recorded
  `allowed` on the live decision (and is unit-tested for `rejected`/
  `escalated` elsewhere).
- **provenance**: every Decision and Knowledge State carries model/policy
  versions and evidence ids; the retention Hypothesis carries a frozen
  prediction distinct from the later-measured outcome.

This PASS is qualified by the deferred-items list in §4 — none of them
block the MVP definition itself, but two (consent/age authorization, the
retention scheduler) must close before a real pilot with real students,
not be left indefinitely.
