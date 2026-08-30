# Load Test Report — Phase 10 / P10

Status: baseline established, bottleneck identified, diagnosed, **and
fixed** (Roadmap Stage D) — see §7 for the real before/after measurement.

## 1. Method

Two complementary tools, both against the real local Docker stack
(`docker compose up`), never a mocked/in-memory server:

1. **`tests/load/locustfile.py`** (Locust, headless) — simulates real
   concurrent students: each virtual user calls the real `POST
   /auth/register` in `on_start` (its own fresh account, exactly like a
   real signup — not one token replayed), then loops through
   `submit_attempt` / `request_decision` / `view_dashboard` with 1–3s
   pacing between tasks, deliberately realistic rather than maximal, so it
   also exercises the per-user rate limits added in Phase 10 slice 1 the
   way real concurrent traffic would.
2. **A direct `asyncio.gather` burst script** (ad hoc, not committed) —
   fires N truly-simultaneous requests from N distinct pre-seeded accounts
   (seeded straight via the ORM, bypassing `/auth/register`'s own rate
   limit deliberately, since this measures one endpoint's concurrency
   ceiling, not the signup flow's). Used to find the load level at which
   latency visibly degrades, which the paced Locust run was too gentle to
   surface.

Curriculum setup: `apps/api/scripts/seed_load_test_curriculum.py` creates
one skill and 20 auto-gradable questions once, so measured latency reflects
the endpoints under test, not question-creation overhead.

**Caveat, stated plainly**: this ran on the same modest single-machine
Docker Desktop setup used for the Ollama hardware testing earlier in this
project (a mobile 4-core/8-thread CPU, no dedicated load-generation
hardware), with the load generator itself sharing that CPU with the
services under test. The absolute numbers below are therefore pessimistic
relative to real server-class hardware — but the *shape* of the finding
(where latency inflects, and why) is real and portable.

## 2. Baseline: realistic paced concurrency (Locust)

15 concurrent simulated students, slow ramp-up (0.15 users/s, to stay under
`/auth/register`'s 10/min-per-IP limit — Phase 10 slice 1's protection
working exactly as designed against a simulated signup burst), 3 minutes,
1–3s wait between each user's tasks.

| Endpoint | Requests | Failures | Median | p95 | p99 | Max |
|---|---|---|---|---|---|---|
| `POST /assessment/attempts` | 505 | 0 | 35ms | 63ms | 80ms | 110ms |
| `GET /dashboard/student` | 297 | 0 | 16ms | 36ms | 57ms | 93ms |
| `POST /decisions/next-action` | 191 | 0 | 83ms | 120ms | 140ms | 170ms |
| `POST /auth/register` | 15 | 0 | 110ms | 170ms | 170ms | 170ms |
| **Aggregate** | **1008** | **0** | **34ms** | **98ms** | **120ms** | **171ms** |

**Zero failures across 1008 requests.** Every endpoint stays comfortably
interactive (sub-200ms even at the max) at this concurrency and pacing —
this is a realistic approximation of an early pilot's actual traffic (§72
"10–20 students... 50–100 students"), and the system handles it cleanly.

## 3. Finding the inflection point (direct concurrency burst)

The paced Locust run was too gentle to show where things degrade, so a
second script fired N genuinely simultaneous `POST /decisions/next-action`
calls from N distinct pre-seeded accounts (no pacing at all):

| Concurrent requests | Median latency | p95 | Max | Failures |
|---|---|---|---|---|
| 10 | 629ms | 635ms | 635ms | 0 |
| 15 | 899ms | 927ms | 927ms | 0 |
| 25 | 1063ms | 1564ms | 1603ms | 0 |
| 40 | 1996ms | 2637ms | 2648ms | 0 |

**No errors at any concurrency level tested** — the system degrades
gracefully (slower, not broken) rather than failing under this load. That
is itself a real, positive finding: no 500s, no dropped requests, no
connection-pool exhaustion errors surfaced up to 40 simultaneous decision
requests.

## 4. Diagnosis: where the latency actually comes from

Two hypotheses were tested and one was falsified by direct measurement,
not assumed:

- **Hypothesis A — the dev server's single `--reload` worker process is
  the bottleneck.** Tested by starting a second, production-shaped uvicorn
  instance (`--workers 4`, no `--reload`) on a second port inside the same
  container and re-running the 25- and 40-concurrent bursts against it.
  **Result: no meaningful difference** (25 concurrent: 1031ms median vs.
  1063ms; 40 concurrent: 1932ms median vs. 1996ms). Hypothesis A is not
  supported by this measurement — more worker processes did not help.
- **Hypothesis B — the bottleneck is generic HTTP/Docker overhead under
  concurrency, not this endpoint specifically.** Tested by bursting 40
  simultaneous `GET /health` requests (one cheap DB read, no writes, no
  Bayesian computation) against the same server. **Result: 340ms median,
  390ms max** — roughly 5–6× faster than the same concurrency level against
  `/decisions/next-action`. Hypothesis B is not supported either: generic
  request handling stays fast at this concurrency.

**What the evidence actually points to**: `POST /decisions/next-action`'s
own database access pattern. `decision_engine_service.generate_decision`
calls `knowledge_state_service.get_knowledge_states_for_skill`, which — by
design, per ADR-012's facet-independence assumption — recomputes each of
the 5 skill facets (§28: Recognition/Recall/Application/Transfer/Retention)
**independently**, each with its own Evidence+Observation query and its own
KnowledgeState upsert query. Add the decision-generation step's own
Evidence-id and Skill lookups, and a single `/decisions/next-action` call
issues on the order of 12–15 sequential database round-trips. Under real
concurrency, with Postgres itself sharing this session's modest hardware,
that multiplies out to the queueing observed above. This is a correctness-
preserving, intentional design (ADR-012's facet-independence is a
deliberate scientific-integrity choice, not an oversight — see ADR-012),
just not yet optimized for concurrent throughput.

## 5. Recommendation (implemented — see §6)

Profile and reduce the ~12–15 round-trips above — batch the 5 facets'
Evidence+Observation queries into one query instead of five, then compute
each facet's posterior from the shared result set. Implemented in
`app/services/knowledge_state_service.py::get_knowledge_states_for_skill`
(Roadmap Stage D), with a dedicated reproducibility test
(`tests/unit/test_knowledge_state_batching.py`) proving the batched path
produces bit-identical results to the original per-facet path for the same
data — not merely similar (§99).

## 6. After: Real Before/After Measurement (Roadmap Stage D)

Same methodology as §3 exactly — 40 fresh accounts, one real skill, the
same `asyncio.gather` burst script, same single-machine hardware — run
again after the batching change:

| Concurrent requests | Median (before) | Median (after) | Change |
|---|---|---|---|
| 10 | 629ms | 329ms | −48% |
| 25 | 1063ms | 578ms | −46% |
| 40 | 1996ms | 1018ms | −49% |

Roughly a 2× reduction in latency at every concurrency level tested, zero
failures either before or after. This is consistent with the diagnosis in
§4: the fix collapsed the ~12–15 sequential round-trips per decision down
to a handful (one Skill lookup, one Evidence query, one KnowledgeState
query, one commit for the knowledge-state phase), and did not require
touching `compute_knowledge_state` (the pure Bayesian core, ADR-012) or
`decision_policy.py`/`authorization_service.py` at all.

**Still not eliminated**: `decision_engine_service.generate_decision` has
its own additional queries downstream of knowledge-state computation (an
Evidence-id list query, the consent/age gate's `ParentStudentLink` lookup,
the `Decision` insert) not touched by this change — the remaining latency
at high concurrency is consistent with those plus normal Postgres
contention on this session's shared hardware, not a new unexplained cost.
Further reduction is a real, identifiable next step if a future pilot's
traffic actually requires it — not undertaken speculatively here (§109).

## 7. What this load test does not cover

- Sustained load over minutes/hours (both runs here were short — 3 minutes
  paced, seconds for the concurrency bursts). Memory growth, connection
  leaks, or slow degradation over a full school day are not tested.
- Multi-tenant contention at realistic pilot scale (§72: dozens to low
  hundreds of students in one tenant) — the concurrency burst used 40
  separate individual tenants, not many students inside one shared tenant,
  which is the more realistic school-pilot shape.
- The AI Gateway (`POST /ai/explanations`) under concurrency — excluded
  because it calls a real LLM whose own latency (seconds, per ADR-015's
  real-hardware addendum) would dominate any finding about this codebase's
  own performance.
- Real production infrastructure (managed Postgres, multiple hosts,
  horizontal scaling) — this entire report is a single-machine local-dev
  measurement, explicitly flagged as pessimistic relative to real
  deployment hardware in §1.
