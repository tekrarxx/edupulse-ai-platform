# ADR-015: AI Gateway — Provider Abstraction, Safety, and Usage Accounting

Status: Accepted
Date: 2026-08-29
Related: CLAUDE.md §43–§48, §82, §105, §106, §136, §113 P7

This is the first AI-touching feature in the codebase. Per §98's spirit
(applied here even though this isn't a Prometheus math model), this ADR
documents the provider contract, the safety rules and their explicit
limits, the cost-ladder positioning, and what data does/doesn't leave the
system — before/alongside implementation.

## Context

Nothing in this codebase has ever called an LLM. Before any capability
ships (question generation, feedback, content drafting — §46), a single,
swappable path for all LLM calls must exist (§45), local-first by default
(§44), with structured output the caller can trust (§47) and usage that is
measurable (§45, §65, §139). This ADR covers the gateway itself and its
first real consumer: generating a short worked explanation for a Physics
skill.

## 1. Provider Abstraction

`AIProvider` (ABC, `app/ai/providers/base.py`) defines one method:
`generate(GenerationRequest) -> GenerationResult`, where `GenerationRequest`
carries the rendered prompt text, a target Pydantic schema class, and
generation parameters (max tokens, temperature). Application code never
imports a specific provider — the gateway is handed an `AIProvider` instance
via dependency injection (§3 below). `OllamaProvider` is the first (and, in
this phase, only) implementation: a real `httpx` client against Ollama's
`/api/generate` endpoint with `format="json"`, a bounded manual retry (2–3
attempts, no new dependency — `tenacity`/`backoff` are not in this repo and
are not justified for a two-or-three-attempt loop), and Ollama's own
`eval_count`/`prompt_eval_count` mapped to token counts. Those counts are
Ollama's own tokenizer output, not a billing-grade measurement — documented
here explicitly so they are never mistaken for exact figures later.

Structured output is requested from the model directly (`format="json"`),
not parsed out of free text after the fact — this is the mechanism that
makes §47 ("request structured output, validate schema, reject malformed
output") enforceable at all.

## 2. Cost Ladder Positioning (§48)

This feature sits at the **local model** rung of `deterministic logic →
local model → small external model → large external model`. Explanation
generation is genuinely generative (not reducible to deterministic logic),
so it cannot sit at the first rung, but no external-provider code exists in
this codebase at all — there is nothing to accidentally route to a paid
model. Escalating past Ollama requires a new `AIProvider` implementation and
its own ADR, not a config flag flip.

## 3. What Data Is Sent Externally (§136)

**Nothing leaves the machine in this phase** — Ollama runs locally in this
stack. Within the local call itself, the only data sent to the model is
`Skill.name` and `Skill.description`: already-trusted, tenant-neutral
curriculum reference data (§19's shared-content model, same precedent as
`Question` — "reusable content, not tenant-owned"). `_render_skill_explanation`'s
signature deliberately accepts only these two fields — structurally, there
is no code path in this slice that lets learner free-text, attempt
responses, or any PII reach a prompt. This is a v1 scope boundary, not a
permanent constraint: a future capability that summarizes a learner's own
answers, for instance, would need its own data-minimization review under
§136, not inherit this one's clearance.

## 4. Safety Validation and Its Explicit Limits (§82, §105)

`validate_output_safety` (`app/ai/safety.py`) checks: non-empty, a hard
maximum length (defense in depth beyond the schema's own `max_length`), and
a small literal denylist scan. **This is explicitly a minimal placeholder,
not a claim of real content-moderation coverage.** No confidence score, no
factual-accuracy check, no bias detection exists. Per §82's "never assume a
confident LLM is a correct LLM" — nothing in this gateway asserts that a
safety-passing explanation is *educationally correct*, only that it isn't
empty, absurdly long, or contains one of a handful of denylisted strings.
Any future learner-facing free-text-generating capability (rather than
short factual explanations of curriculum content already known to be
correct) needs a materially stronger safety design before shipping,
including the teacher-review path §82 describes — deliberately **not**
built in this slice (see §6, "Decisions Made This Session").

## 5. Usage Accounting (§45, §48, §65, §139)

Every `AIGateway.generate()` call writes exactly one `AIUsageRecord` —
success or failure — capturing provider, model, capability, prompt
name/version, tenant/actor, approximate token counts, latency, and (on
failure) a short, length-bounded `error_reason`. The raw failing output is
never written into `error_reason` — only the exception class name/short
label — so a malformed or unsafe generation can't leak arbitrary model
output into a database column with no bound (mirroring the "never expose
internals" discipline `app/main.py`'s global exception handler already
applies to HTTP errors).

## 6. Decisions Made This Session

Two scope decisions were made explicitly with the product owner rather than
assumed:

- **No teacher-review gate before a student sees an explanation.** Content
  is generated and returned directly to whichever authenticated tenant
  member (including `STUDENT`) requests it via `POST /ai/explanations` — no
  `require_role` restriction. A review-gate (`pending_review` state,
  approval endpoint, RBAC split) is a real future need per §82's own
  language, but is explicitly out of scope for this first slice; revisit if
  factual-accuracy problems surface (§39-style falsification signal: if
  explanations are reported wrong often, that is evidence this decision
  needs revisiting, not a silent tolerance).
- **No content-caching table.** Only `AIUsageRecord` (metadata) persists;
  the generated explanation text itself is not stored or reused across
  requests. Rationale: no evidence yet of request volume that would justify
  cache-invalidation complexity (a cache key would need to fold in
  `Skill.content_version`, since curriculum content is versioned per §20),
  and `AIUsageRecord` already gives full reproducibility/provenance without
  conflating accounting with content storage. Deferring this costs nothing
  — a `AIGeneratedContent` cache table is a clean additive migration later
  if cost/latency becomes a real problem.

## 7. PDE Is Untouched

This slice does not read from or write to `app/services/decision_policy.py`,
`app/services/authorization_service.py`,
`app/services/decision_engine_service.py`, or the `Decision` model. The AI
Gateway has no code path into Prometheus decision-making — §43/§46's
"LLMs MUST NOT replace deterministic logic" and "must not touch PDE
decision-making" are enforced by the simple fact that no import or call
exists between these modules, verified by this ADR's own review, not
merely asserted.

## Assumptions

1. Capability set is exactly `skill_explanation` v1 — the `AIUsageCapability`
   enum will grow as real capabilities are added, never pre-populated
   speculatively.
2. Provider set is exactly Ollama — no external provider exists yet.
3. `app.dependency_overrides` is used for the first time in this codebase
   (`get_ai_provider` is the override seam) — a standard, idiomatic FastAPI
   testing pattern, introduced here because this is the first component
   that genuinely needs a swappable-at-test-time external dependency (the
   database and auth dependencies are exercised for real against a test
   Postgres/SQLite instance instead, per existing convention — an LLM call
   is different in kind, not degree, from those).
4. `AIUsageRecord.tenant_id`/`actor_user_id` are non-nullable — every caller
   in this codebase reaches the gateway through an authenticated,
   tenant-scoped user. A future system/background AI caller with no human
   actor is a genuinely new case, not speculatively designed for now.

## What Would Falsify This Model (§39-style discipline applied here)

- If `AIUsageRecord.success = false` rates are high in real usage, the
  retry/timeout tuning (or Ollama's local performance characteristics) is
  wrong and needs revisiting.
- If teachers or students report explanations as factually wrong often,
  the "no review gate" decision (§6) is not supportable and must be
  revisited — this is the single most likely assumption in this ADR to be
  overturned by real usage.
- If the denylist/length-only safety check lets through content a human
  reviewer would clearly reject, §4's "minimal placeholder" framing was
  understating the actual risk, not just conservatively describing it.

## Alternatives Considered

- **Free-text (unstructured) LLM output, parsed with regex/heuristics
  after the fact.** Rejected — §47 requires structured, schema-validated
  output; asking the model for JSON directly is more reliable than parsing
  prose after the fact.
- **A content-cache table now.** Deferred, not rejected (§6).
- **A hosted/external LLM as the default provider.** Rejected for this
  phase — §44 local-first; no learner data should leave the system by
  default, and Ollama has zero marginal cost.
- **A generic `Protocol` instead of an ABC for `AIProvider`.** An ABC was
  chosen to match this codebase's existing preference for concrete
  exception-hierarchy-bearing base classes (e.g. `RetentionError` and
  siblings in `retention_service.py`) over structural typing, for
  consistency rather than a strong technical requirement either way.

## Consequences

- `OllamaProvider` was not run against a live Ollama instance in the
  session that implemented it — that gap has since been closed, see the
  addendum below.
- Any future AI capability should go through this same gateway/provider
  seam rather than making its own ad-hoc LLM call (§106 — no undocumented
  AI calls).
- The two scope decisions in §6 are tracked, not permanent — see the
  memory this session already recorded about closing documented gaps over
  time.

## Addendum (2026-08-29): Real Hardware Verification

The user asked, in the immediately following session, whether their
development machine can actually run Ollama, and to find a solution if not.
Ollama was installed (`winget install Ollama.Ollama`) and genuinely
exercised — not simulated — against this machine's real hardware and this
repo's real Docker stack. Findings:

**Hardware**: Intel Core i5-8265U (4 cores / 8 threads, 1.6 GHz base,
mobile U-series), 15.79 GB RAM (~7–9 GB typically free alongside the
running Docker stack and other applications), 51 GB free disk, Intel UHD
620 + AMD Radeon 540X (mobile, 2 GB VRAM) — **neither GPU is CUDA or ROCm
capable, so Ollama runs CPU-only on this machine.**

**Verdict: capable, but only for small (1–3B parameter) models, not the
8B model this ADR originally defaulted to.** `llama3.2:1b` (1.3 GB) was
pulled and run successfully:
- ~11 tokens/second generation speed, CPU-only. A short structured
  explanation takes roughly 6–9 seconds end to end — usable for
  interactive dev/testing, not instant.
- Idle memory footprint is low (~50 MB for the Ollama server with no model
  loaded; Ollama unloads models after a few minutes of inactivity), so it
  does not permanently compete with the Docker stack for RAM.
- An 8B model was not tested but is not recommended on this hardware — the
  proportionally larger memory footprint (likely 5–6 GB resident) and much
  slower CPU-only generation would make it impractical, and would compete
  directly with Docker Desktop's WSL2 VM memory ceiling (see below).
- **Reliability finding, not just a capability finding**: across a handful
  of real calls to `llama3.2:1b` requesting the `SkillExplanationOutput`
  schema (a nested string-array field, `key_points`), roughly **1 in 3
  responses failed schema validation** — the model sometimes serialized
  `key_points` as a single string (e.g. `"[a, b, c]"`) instead of a real
  JSON array, despite `format="json"` being requested. **The gateway
  correctly rejected every one of these** (`SchemaValidationError`, logged
  as `success=false, error_reason=ValidationError` in a real
  `AIUsageRecord` row, and a real `502 ai_provider_returned_invalid_output`
  HTTP response) — this is §47's "reject malformed output, never coerced"
  working exactly as designed, verified against a real model's real
  failure mode, not a hypothetical one. Small local models should be
  expected to have a non-trivial malformed-structured-output rate; this is
  evidence for that, not an argument to weaken schema validation.
- A secondary quality observation (not a hard finding, just noted): the
  1B model's Turkish output quality was mediocre — it mixed English
  fragments into Turkish sentences (e.g. "forcesnin", "inversely
  proportional olduğu"). Given this product's primary market is Turkish-
  speaking students (§2), a 1–3B model may not be the right *production*
  choice even though it is the right *local-dev-hardware-appropriate*
  default — a stronger small model with better Turkish coverage, or a
  larger model run on better hardware/hosted, is a real product question
  for later, not resolved by this ADR.

**Bug found and fixed**: `OLLAMA_BASE_URL=http://localhost:11434` — this
ADR's original default — does **not** work when the API runs inside the
`api` Docker container (confirmed by a real connectivity test: it connects
successfully from a native/non-Docker process, and fails with "Connection
refused" from inside the container). `localhost` inside a container refers
to the container itself, not the Windows host running Ollama.
`docker-compose.yml`'s `api` service now overrides `OLLAMA_BASE_URL` to
`http://host.docker.internal:11434` (Docker Desktop's standard host alias
on Windows/Mac) with an `extra_hosts: host.docker.internal:host-gateway`
entry added so the same override also resolves correctly on native Linux
Docker, keeping this compose file portable across platforms. The
`.env.example`/`Settings` default (`http://localhost:11434`) is still
correct for the non-Docker, run-uvicorn-natively dev loop — the two
defaults are for two different ways of running the API, not a
contradiction.

**Default model changed**: `OLLAMA_MODEL` default is now `llama3.2:1b`
(was `llama3.1:8b`), and `AI_REQUEST_TIMEOUT_SECONDS` raised from 20.0 to
30.0 to give real observed CPU-only latency (up to ~17s was seen on a
schema-invalid response that still had to generate a full completion)
comfortable headroom.

**End-to-end verification performed**: a real user registered through
`POST /auth/register`, a real request to `POST /ai/explanations` for the
already-seeded "Newton'un İkinci Hareket Yasası" skill, through the actual
running `api` Docker container, through the actual Docker networking path,
against the actual local Ollama instance. First call hit the malformed-
output case above (502, correctly handled); second call succeeded (200,
valid explanation, correct `AIUsageRecord`). This is the first genuine
end-to-end proof that `OllamaProvider` and the full request path work, not
just the `FakeProvider`-backed test suite.

## Mandatory Tests

- Gateway success path: valid structured output → correct
  `AIUsageRecord` fields (§45 accounting).
- Malformed JSON / schema-invalid output → `SchemaValidationError`,
  `success=false` usage record, no exception (§47 "reject malformed
  output," not silently coerced).
- Safety-rejected output → `SafetyRejected`, `success=false,
  error_reason="safety_violation"`.
- Bounded retry: N-failures-then-success terminates correctly;
  always-fails terminates after the configured attempt count (assert call
  count, not just outcome — a runaway retry loop is its own bug class).
- API: success (200), unknown skill (404), malformed provider output (502),
  provider unavailable (503), and a usage-record-persisted-after-call check.
