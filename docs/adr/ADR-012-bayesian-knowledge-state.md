# ADR-012: Bayesian Knowledge State (Beta-Binomial per Student/Skill/Facet)

Status: Proposed
Date: 2026-08-28
Related: CLAUDE.md §24–§28, §31, §39, §42, §87, §99

This ADR is Step 5A of Phase 5 (§113 P4). No implementation code accompanies
it. It documents the mathematical model before any code is written (§25).

## Context

Phase 4 produced `Evidence` rows (§23): interpreted, quality-weighted signals
foreign-keyed to an immutable `Observation`, each carrying `facet_type`
(recognition/recall/application/transfer/retention, §28), `polarity`
(positive/negative), `directness`, `reliability`, `task_validity`,
`transfer_relevance`, and `evaluation_confidence`. Nothing yet turns a stream
of Evidence into a Knowledge State the PDE (Phase 6) can consume. That is the
gap this ADR closes.

## Hypothesis

A learner's mastery of a single (skill, facet) pair can be usefully modeled
as an unknown probability `p` — "probability the learner would answer a new,
similarly-valid item of this facet correctly" — and each piece of Evidence is
a noisy, quality-weighted Bernoulli trial informative about `p`. A
Beta-Binomial conjugate model lets us maintain a closed-form posterior over
`p` that updates cheaply, exposes both a point estimate and a confidence
measure, and never collapses to a boolean fact (§24, §26).

## Mathematical Formulation

### State unit

One Knowledge State row per `(tenant_id, student_user_id, skill_id,
facet_type)`. This is the atomic unit — see "Five Facets" below for why
facets are never pooled.

### Prior

Each unit starts at the uninformative prior `Beta(alpha_0 = 1, beta_0 = 1)`
(uniform over `[0, 1]`) — before any evidence, the model asserts nothing
about the learner beyond "anything is equally possible," matching "insufficient
evidence" (§26).

### Per-evidence weight

Raw Beta-Binomial updates treat every observation as one full pseudo-trial.
Evidence quality (§27) must instead scale how much a given row counts. Define
the weight of an Evidence row `e`:

```
directness_multiplier(e) = 1.0 if e.directness == DIRECT else 0.4

w(e) = e.reliability
     * e.task_validity
     * e.evaluation_confidence
     * directness_multiplier(e)
     * decay(e, as_of)
```

`reliability`, `task_validity`, and `evaluation_confidence` are already
stored as `[0, 1]` floats on the Evidence row (§27), so their product is a
natural down-weighting factor: a low-validity task or a low-confidence
grading contributes less pseudo-evidence than a clean, high-confidence,
high-validity one. `transfer_relevance` is deliberately **not** a multiplier
here — see "Transfer is a facet, not a weight" below.

`directness_multiplier` reflects that no INDIRECT evidence source exists yet
(the Phase 4 model docstring notes this); the constant is fixed here so the
day an indirect source (e.g. a teacher's qualitative note) is added, it does
not silently carry full weight against direct graded attempts.

### Decay

```
age_days(e, as_of) = (as_of - e.observation.occurred_at) in days
decay(e, as_of) = 0.5 ** (age_days(e, as_of) / HALF_LIFE_DAYS)
```

`HALF_LIFE_DAYS = 60` as the Phase 5 default, applied uniformly across all
five facets. This is an explicit, documented assumption (see Assumptions
below), not a derived constant — it is expected to be revisited with real
retention data once Phase 6/P6 delayed-retention checkpoints (14d/28d)
produce evidence about actual forgetting curves. Until then, 60 days is a
deliberately conservative middle ground: short enough that stale evidence
stops dominating, long enough that a single session's worth of evidence
isn't discarded before the next session.

### Posterior computation

Knowledge State is **recomputed from the full Evidence history at read time**
as of an explicit `as_of` timestamp, not maintained as an incrementally
mutated running total:

```
alpha(as_of) = alpha_0 + sum( w(e) for e in evidence where e.polarity == POSITIVE )
beta(as_of)  = beta_0  + sum( w(e) for e in evidence where e.polarity == NEGATIVE )

mastery_probability = alpha(as_of) / (alpha(as_of) + beta(as_of))
```

Recomputation-from-log (rather than incremental mutation) is chosen because:

1. **Reproducibility (§99)** falls out for free: given the same Evidence set,
   the same `as_of`, and the same `model_version`, the result is a pure
   function — no ordering-dependent floating point drift, no risk of a
   missed update leaving the stored row stale.
2. It matches the event-sourced shape already established for `Observation`
   (§40) — Evidence is itself an immutable log, so Knowledge State is a
   materialized view over it, not a second source of truth.
3. Decay depends on `as_of - occurred_at`, which changes on every call by
   construction; an incrementally-updated stored posterior would need a
   background job just to keep decay current even with zero new evidence.

A stored Knowledge State row is a **cache** of this computation as of the
last time it was requested, tagged with the `as_of` and `model_version` used
to produce it (§42) — never treated as authoritative ahead of recomputation.

### Confidence

```
effective_n = alpha(as_of) + beta(as_of) - alpha_0 - beta_0   # pseudo-evidence beyond the prior
variance    = (alpha * beta) / ((alpha + beta)^2 * (alpha + beta + 1))
```

Confidence is exposed as a discrete label, never a bare float, to enforce the
language discipline in §26:

```
effective_n < 1        -> "insufficient_evidence"
effective_n < 4         -> "low_confidence"
otherwise               -> "high_confidence"
```

Thresholds are an explicit assumption (below), chosen so that a single
low-quality piece of evidence (`w(e)` well under 1.0) cannot alone produce
`high_confidence`, and so a handful of high-quality direct attempts can. The
raw `variance` and `effective_n` are still stored on the state row for
downstream/debugging use, but API responses must use the label per §26.

## Assumptions (stated explicitly, per §25)

1. **Facet independence.** Evidence for one facet never updates another
   facet's posterior. A learner scoring well on recognition items does not
   move the recall, application, transfer, or retention posteriors for the
   same skill. This is a strong, deliberately conservative assumption — real
   facets likely correlate — but §28 explicitly forbids collapsing them, and
   modeling cross-facet transfer is future work requiring its own hypothesis
   and ADR, not a default.
2. **Uniform decay half-life across facets.** A single `HALF_LIFE_DAYS = 60`
   is used for all five facets rather than facet-specific decay curves,
   because there is no data yet to justify differentiating them. This is the
   single most likely-to-change constant in this model.
3. **Multiplicative, independent quality weighting.** `reliability`,
   `task_validity`, and `evaluation_confidence` are treated as independent
   multiplicative factors rather than a learned or additive combination. This
   is a simplifying assumption; it has the correct qualitative behavior
   (any factor going to 0 zeroes the weight) without requiring a fitted
   model this phase.
4. **`transfer_relevance` is informational, not a weight.** A transfer-facet
   Evidence row is already routed to the `TRANSFER` facet's own posterior by
   `facet_type`; using `transfer_relevance` as an additional multiplier would
   double-count the same signal. The column is retained on the Evidence row
   as description/provenance and is available for a future policy (Phase
   6/P5 PDE candidate scoring) that may want to know "was this evidence
   transfer-relevant" independent of which facet posterior it updated.
5. **No cross-skill effects.** Prerequisite relationships (§19) are not fed
   into this model. A skill's Knowledge State depends only on Evidence
   targeting that exact `skill_id`. Propagating belief along the
   prerequisite graph is out of scope — it would require its own hypothesis
   about how prerequisite mastery informs a dependent skill's prior, which
   this ADR does not attempt.
6. **`INDIRECT` directness multiplier of 0.4 is a placeholder.** No indirect
   evidence source exists yet in this codebase; the constant exists so the
   model has defined behavior the day one is added, and is expected to be
   revisited with a real example in hand rather than treated as validated.

## How Evidence Quality (§27) Weights Into the Update

Covered above under "Per-evidence weight" — `reliability`, `task_validity`,
`evaluation_confidence`, and `directness` all multiply into `w(e)`; decay is
a further multiplicative factor. This directly satisfies the CLAUDE.md
requirement that "a correct answer to a trivial recognition question should
not automatically outweigh multiple high-quality transfer failures" (§27):
a trivial item should be entered with low `task_validity`, giving it a small
`w(e)`, while multiple high-quality (`reliability` and `task_validity` near
1.0) negative-polarity transfer-facet rows accumulate larger combined weight
in `beta`. This is enforced as a property test (see Mandatory Tests below),
not asserted by convention.

## Expected Behavior, Including Monotonicity

Given a **fixed `as_of`** (so decay factors for existing evidence do not
shift mid-comparison):

- Adding one additional POSITIVE-polarity Evidence row strictly increases
  `alpha` and therefore never decreases `mastery_probability` (monotonic
  non-decrease). Symmetrically for NEGATIVE rows and `beta`.
- Adding evidence to facet X never changes the Knowledge State for facet Y
  of the same skill (facet independence, Assumption 1).
- Two Evidence sets that are permutations of each other (same rows, evidence
  submitted/graded in a different order) yield an identical posterior at the
  same `as_of`, because the update is a commutative sum, not a sequential
  fold with intermediate rounding.
- Holding evidence fixed and increasing `as_of` monotonically decreases every
  evidence row's `decay(e, as_of)` weight, pulling `mastery_probability`
  toward whatever the *other*-polarity evidence implies, and pulling
  `effective_n` (and therefore the confidence label) downward toward
  `insufficient_evidence` as all evidence ages out. This is not "the learner
  forgets" (that is Phase 6/P6's retention model) — it is "the system's
  confidence in old evidence decays," a distinct claim.

## Edge Cases

- **Zero evidence.** `alpha = alpha_0 = 1`, `beta = beta_0 = 1`,
  `mastery_probability = 0.5`, confidence label = `insufficient_evidence`.
  The API must never present `0.5` as "the learner is at 50% mastery" — the
  confidence label is mandatory alongside the point estimate specifically to
  prevent this misreading (§26).
- **Contradictory evidence** (roughly equal positive and negative weight).
  `mastery_probability` settles near 0.5 but `effective_n` is *not* small —
  confidence can legitimately be `high_confidence` while the estimate itself
  is uninformative about direction. This is correct Bayesian behavior (the
  model is confident the truth is genuinely mixed/borderline), not a bug, and
  must not be papered over.
- **All evidence very old** (decay ≈ 0 for every row). The posterior
  approaches the prior (`0.5`, `insufficient_evidence`) regardless of how
  much evidence historically existed — full decay of confidence is the
  intended behavior, not evidence loss (nothing is deleted from the
  underlying Evidence log; only the derived weight shrinks).
- **Single very-low-quality evidence row** (e.g. `reliability = 0.1`).
  Contributes a small but nonzero `w(e)`; cannot alone cross the
  `insufficient_evidence -> low_confidence` threshold, per the threshold
  design above.
- **`alpha + beta` numerically large** (long-lived skill with heavy evidence
  volume). `variance` shrinks as expected under Beta-distribution algebra;
  no special-casing required, but implementation must use floating point
  carefully (no integer division) since `w(e)` is fractional.

## Five Facets, Modeled Separately

Enforced structurally, not by convention: the Knowledge State primary/lookup
key includes `facet_type`, and the posterior computation filters Evidence by
`facet_type` before folding. There is no code path that aggregates across
facets in this phase (Assumption 1). A future cross-facet model is possible
but requires its own ADR per §98 — it is not something Phase 6/P5's PDE
should assume exists.

## `model_version` Scheme

`model_version` is a string of the form `bayesian-beta-binomial-v<N>`,
starting at `bayesian-beta-binomial-v1` for this ADR's formulation. Every
Knowledge State row (cached computation) stores the `model_version` that
produced it (§42). A version bump is required — and only required — when any
of the following changes: the prior (`alpha_0`, `beta_0`), the weight formula
(`w(e)`), the decay function or `HALF_LIFE_DAYS`, the confidence thresholds,
or the unit of aggregation (e.g. if facet independence is ever relaxed).
Bumping `model_version` does not require a new ADR for pure constant tuning
backed by data (e.g. adjusting `HALF_LIFE_DAYS` from real retention-checkpoint
results), but does require the new value and rationale recorded in this
ADR's changelog; a change to the *formulation* itself (weight structure,
independence assumption, aggregation unit) requires a new ADR per §98.

## What Would Falsify This Model (§39)

- If `mastery_probability` computed at time T does not correlate with actual
  performance on a held-out, high-quality item of the same skill/facet
  presented shortly after T, the core hypothesis (Evidence-weighted Beta
  posterior tracks true ability) is not supported.
- If `confidence = high_confidence` states are *not* meaningfully more
  predictive of near-term performance than `low_confidence` states of similar
  `mastery_probability`, the confidence measure is not doing useful work and
  needs redesign.
- If the 60-day half-life produces `insufficient_evidence` confidence for
  skills that Phase 6/P6 delayed-retention checkpoints (14d/28d) show are
  still reliably retained, the decay assumption is too aggressive and must be
  revised with the retention data as evidence.
- If facet independence (Assumption 1) produces knowledge states that
  teachers/pilot users consistently report as wrong in a specific,
  reproducible direction (e.g. transfer-facet mastery is always
  underestimated relative to application-facet mastery for the same
  learners), that is evidence the independence assumption is too strong and
  a cross-facet model is warranted — via a new ADR, not a silent patch.

Any of the above should be run in Shadow Mode (§38) against real learner
activity before changing production-facing behavior, once Phase 6/P5 makes
Shadow Mode available.

## Alternatives Considered

- **Simple moving average / exponential moving average of correctness.**
  Rejected: no principled confidence measure, no clean way to fold in
  per-evidence quality weights as pseudo-counts, and no natural prior for the
  zero-evidence case (§26).
- **Item Response Theory (IRT).** Deferred, not rejected: IRT models
  item difficulty and learner ability jointly and could produce better
  estimates, but requires calibrated item-difficulty parameters that do not
  exist yet (Phase 4's Assessment model stores a `difficulty` field but it is
  not yet calibrated against real response data). Beta-Binomial is the
  simpler model that ships now; IRT is a candidate for a future ADR once
  enough attempt volume exists to calibrate it.
- **Incrementally mutated posterior (update-in-place on each new Evidence
  row).** Rejected in favor of recompute-from-log, per the reproducibility
  argument above.
- **Facet-specific decay half-lives from the start.** Rejected for this
  phase: no data exists yet to set them differently, and inventing five
  unvalidated constants is worse than one explicitly-provisional constant.

## Consequences

- Knowledge State is a materialized, cacheable, re-derivable view over the
  Evidence log — never the source of truth itself.
- Every Knowledge State computation must record (or accept as input) an
  explicit `as_of` timestamp for the result to be reproducible and testable;
  "now" must never be implicitly read inside the core computation function.
- API responses exposing mastery must always pair the numeric estimate with
  the discrete confidence label, never the float alone (§26 enforcement
  point).
- `HALF_LIFE_DAYS`, the confidence thresholds, and the `INDIRECT` multiplier
  are flagged as the most likely constants to be revisited once Phase 6/P6
  retention data exists; that revisit is a `model_version` bump, documented
  in this ADR, not a silent tune.
- Facet independence (Assumption 1) is the biggest scientific bet in this
  ADR and the first thing to revisit if pilot feedback disagrees with the
  model.

## Mandatory Tests (§87, to be written in Step 5B)

- `mastery_probability` remains in `[0, 1]` under every generated evidence
  sequence (property-based).
- Monotonic non-decrease under adding same-polarity evidence at fixed
  `as_of` (property-based).
- Permutation invariance: any ordering of the same Evidence set at the same
  `as_of` yields bit-identical `alpha`/`beta` (reproducibility, §99).
- Identical `(evidence set, as_of, model_version)` triples always yield
  identical Knowledge State output (§99).
- A single low-quality positive Evidence row cannot outweigh multiple
  high-quality negative Evidence rows for the same facet (§27 property).
- Confidence label transitions occur exactly at the documented `effective_n`
  thresholds, not through floating-point-sensitive comparisons.
- Facet isolation: Evidence for facet X never changes the stored/computed
  state for facet Y of the same `(student, skill)`.
- Decay pulls `effective_n` toward the insufficient-evidence threshold as
  `as_of` moves forward with no new evidence, and never produces negative
  `alpha`/`beta`.
- Timestamps: decay computation is correct across timezone-aware inputs and
  DST boundaries (all stored timestamps are already `DateTime(timezone=True)`
  per the existing models).

STOP — this ADR requires approval before Step 5B (implementation) begins.
