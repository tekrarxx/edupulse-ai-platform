# ADR-022: Model Router — an Optional Second Provider, Ollama Always Primary

Status: Accepted
Date: 2026-09-01
Related: CLAUDE.md §16, §43–§44, §48, §136, §140, ADR-015 (AI Gateway),
ROADMAP.md P3

## Context

ADR-015 built the AI Gateway with a provider abstraction (`AIProvider`)
specifically so `OllamaProvider` would not be the only thing that could
ever exist behind it, but no second provider was ever implemented —
`ROADMAP.md` P3 named this explicitly: "the `OLLAMA_BASE_URL` swap point
already exists... adding a second provider is infrastructure-adapter work,
not a redesign — but there is no current cost/quality/latency pressure
forcing it yet." This session builds it at explicit user direction, not
because new pressure appeared — the same "not speculative, but not
evidence-driven either" footing ADR-015 itself started from for Ollama.

§140 describes eventual routing "based on cost, latency, task complexity,
privacy, availability, tenant configuration, model quality." None of that
selection logic exists yet because no real feature needs it (§125) — this
ADR builds only the one real thing §44's "external providers should be
optional" already implies but nothing enforced: an actual fallback path,
not just an unused config knob.

## Decision

**`app/ai/providers/openai_compatible.py`**: a provider for any endpoint
implementing the OpenAI Chat Completions API shape — deliberately not
named after one vendor, since this exact contract is also served by Groq,
Together, OpenRouter, DeepSeek, a self-hosted vLLM/LM Studio instance, and
others (§43 "must not depend on a particular model provider"). Mirrors
`OllamaProvider`'s structure exactly: same bounded retry (3 attempts),
same `ProviderError` subclass mapping, same `AIProvider` interface. Like
`OllamaProvider` when it was first built, this is reviewed, production-
shaped code that has never been exercised against a real API key —
verifying it live is an open item for whichever deployment first
configures one, not something the automated suite does (§86).

**`app/ai/router.py`**: `ModelRouter`, itself an `AIProvider`, wrapping an
ordered list of providers. `generate()` tries each in order, falling back
to the next only on a `ProviderError` (transport/protocol failure —
timeout, connection refused, non-2xx status). It does **not** retry across
providers on `SchemaValidationError` or `SafetyRejected` — those happen
inside `AIGateway`, after a provider's `generate()` has already returned
successfully, so the router never even sees them; a provider that returns
syntactically-fine-but-schema-invalid content is not "unavailable," it
answered.

`ModelRouter.provider_name`/`model_name` update to whichever provider is
currently being tried — including on total failure, so
`AIGateway._record_usage`'s `AIUsageRecord` (read after `generate()`
returns or raises) still attributes the call to a real provider, never a
placeholder (§65/§139).

**Wiring** (`app/api/deps.py`'s `get_ai_provider`): Ollama is always the
primary provider (§44). A second provider is added only when all three of
`SECONDARY_AI_PROVIDER_BASE_URL`/`_API_KEY`/`_MODEL` are set — never
partially, and never in place of Ollama, which stays first in the list
regardless. Unconfigured (the shipped default, `.env.example`), the
function returns the bare `OllamaProvider`, identical to before this ADR
— no behavior change for the common case.

## What Is Explicitly Not Built

- Cost/latency/quality/tenant-based routing (§140's fuller vision) — this
  is a fixed-order fallback list, not a scoring router. Build that when a
  real routing decision is actually needed, not speculatively.
- Retrying a different provider on `SchemaValidationError` — a weak
  model's structured-output unreliability (this session's ADR-015
  addendum found `llama3.2:1b` fails roughly half the time on one shape)
  is a data-quality problem the fallback ordering does not address; that
  remains `SkillExplanationOutput`'s normalization fix, not a routing
  concern.
- Per-tenant provider selection — every tenant gets the same router
  configuration today; the entitlement system (ADR-016) still never
  informs this module (§95's isolation is a PDE-specific rule, but the
  same "AI infra must not know about billing tiers" spirit extends here
  by convention, not yet by a real per-tenant requirement).

## Consequences

- `AIUsageRecord.provider`/`model` can now legitimately read a value other
  than `"ollama"`/`ollama_model` for a tenant whose deployment configured
  a fallback — cost dashboards (§139) already read these columns generically,
  no change needed there.
- Adding a third provider to the fallback chain is a list append in
  `get_ai_provider`, not a `ModelRouter` change.

## Mandatory Tests

- `OpenAICompatibleProvider`: success path field mapping, malformed
  response, non-2xx status, transient-failure-then-success retry, bounded
  retry exhaustion — `tests/unit/test_openai_compatible_provider.py`,
  mirroring `test_ollama_provider.py`'s existing coverage exactly.
- `ModelRouter`: primary succeeds (no fallback call), primary
  `ProviderError`s and secondary succeeds (fallback + correct
  `provider_name` attribution), both fail (last error raised, still
  correct attribution), single-provider passthrough, empty-list rejected
  — `tests/unit/test_model_router.py`.
- `get_ai_provider` wiring: Ollama-alone by default, `ModelRouter` only
  when all three secondary settings are present, Ollama-alone again when
  only some are set (no accidental partial configuration) —
  `tests/unit/test_ai_provider_wiring.py`.
