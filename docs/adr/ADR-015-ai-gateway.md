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

- **`OllamaProvider` was never run against a live Ollama instance in this
  implementation session.** It is real, reviewed code, but it is an
  explicit, unverified open item — not a fake implementation (§105), but
  not yet a proven one either. Before treating `/ai/explanations` as
  production-ready, the user must run `docker compose up -d ollama`, pull a
  model (e.g. `docker compose exec ollama ollama pull llama3.1:8b` or a
  smaller model), set `OLLAMA_MODEL` accordingly, and exercise the endpoint
  for real. Until then, only the `FakeProvider`-backed test suite has
  verified the gateway's own logic (validation, safety, retry, accounting)
  — never the real model integration.
- Any future AI capability should go through this same gateway/provider
  seam rather than making its own ad-hoc LLM call (§106 — no undocumented
  AI calls).
- The two scope decisions in §6 are tracked, not permanent — see the
  memory this session already recorded about closing documented gaps over
  time.

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
