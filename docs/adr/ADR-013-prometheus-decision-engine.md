# ADR-013: Prometheus Decision Engine — Candidate Scoring & Authorization

Status: Accepted
Date: 2026-08-28
Related: CLAUDE.md §32–§39, §98, §100, §113 P5

Per §98, this ADR documents the decision-policy hypothesis, formulation,
assumptions, expected behavior, and falsification criteria before/alongside
the Phase 6 implementation, the same discipline ADR-012 applied to the
knowledge-state model.

## Context

Phase 5 (ADR-012) produces, for a given `(student, skill, facet)`, a Beta
posterior: `mastery_probability` and a `confidence_label`
(`insufficient_evidence` / `low_confidence` / `high_confidence`). The PDE
must turn the five facet states for one skill into: (a) a score for each of
the 12 candidate actions in §34, (b) a selected action, (c) an independent
authorization verdict, (d) a structured, explainable, versioned, append-only
record (§32, §100).

## Hypothesis

A small set of deterministic, hand-specified scoring functions — one per
candidate action, each a function of only the five facet states — is
sufficient to produce (1) sensible per-scenario action choices, (2) genuine
diversity of selected actions across different learner states (§34's "must
not collapse into one type"), and (3) full reproducibility and
explainability, without requiring a learned/ML ranking model this phase.
This is a content-strategy-level policy (§36): it reasons about population-
level pedagogical structure ("if application mastery is low, an easier task
is appropriate"), not an individually-tuned model — sparse per-learner
evidence is never allowed to override the aggressive-personalization gate
described below.

## Mathematical Formulation

### Inputs

For skill `S` and student `L`, the five `FacetInput` values (from Phase 5,
one per `SkillFacetType`): `mastery_probability (p)` and `confidence_label`.
Define the confidence weight:

```
w(insufficient_evidence) = 0.0
w(low_confidence)        = 0.5
w(high_confidence)       = 1.0
```

`APPLICATION` is treated as the **primary/reference facet** — the one
gating whether personalization (easier/harder/transfer/retention-check) is
attempted at all. This is a deliberate, documented assumption: application
("can they use it") is the closest single-facet proxy for "do they know
this skill" that the current five-facet model offers; recognition/recall are
treated as prerequisite-diagnostic facets, transfer/retention as
advanced-diagnostic facets.

### Per-action scores (all bounded to `[0, 1]`)

Let `p_x`, `w_x` denote mastery/weight for facet `x` ∈
{APP, REC, RCL, TRF, RET}.

```
INSUFFICIENT_EVIDENCE_ACTION = 1 - w_APP
RETRIEVAL_QUESTION           = 0.85·(1 - w_APP) + 0.15·(1 - w_REC)
NEW_CONCEPT_EXPLANATION      = 0.6·w_REC·(1 - p_REC) + 0.4·w_RCL·(1 - p_RCL)
EASIER_TASK                  = w_APP · max(0, 0.5 - p_APP) · 2
HARDER_TASK                  = w_APP · max(0, p_APP - 0.5) · 2 · (1 - w_TRF)
TRANSFER_TASK                = w_APP · p_APP · (1 - w_TRF)
DELAYED_RETENTION_ASSESSMENT = w_APP · p_APP · w_TRF · p_TRF · (1 - w_RET)
REVIEW_TASK                  = w_APP · (1 - |2·p_APP - 1|) · 0.6 + (1 - w_RET) · 0.4
HINT                         = 0.5 · EASIER_TASK
WORKED_EXAMPLE                = 0.5 · NEW_CONCEPT_EXPLANATION
TEACHER_INTERVENTION         = 1.0  if confidence_label_APP == low_confidence
                                       and 0.4 <= p_APP <= 0.6
                                else 0.05
DEFER_DECISION                = 0.05  (flat floor)
```

Every term is a product/sum of values already in `[0, 1]` with
coefficients summing to ≤ 1, so every score is bounded in `[0, 1]` by
construction — verified by property test, not just by inspection.

### Selection

`selected_action = argmax(score)`. Ties broken by `CandidateActionType`
declaration order (a fixed, arbitrary but reproducible tie-break — §99).

### Decision confidence

```
decision_confidence = clamp(score(selected) - score(runner_up), 0, 1)
```

The margin between the top and second-best action — a low margin means the
policy was nearly indifferent between two actions, which is itself useful
explanatory information, distinct from the underlying knowledge-state
`confidence_label`.

### Reason codes (closed vocabulary, structural not per-instance)

Each `CandidateActionType` carries a **fixed** set of `ReasonCode` values
describing what its formula measures (e.g. `HARDER_TASK` always carries
`HIGH_MASTERY_APPLICATION`), attached whenever that action appears in the
ranked list — not dynamically computed per instance from which term
happened to dominate. This is a simplification: reason codes explain the
*qualitative* rationale for the action type; the *quantitative* rationale is
the score plus the persisted `knowledge_state_snapshot`, which together are
sufficient to answer "why" (§33) without per-instance dynamic attribution.
A future iteration could compute per-instance dominant-term attribution;
deferred as unnecessary complexity for v1.

### Policy version

`POLICY_VERSION = "pde-policy-v1"`. A version bump is required for any
change to the scoring formulas, thresholds, tie-break rule, or the
authorization rules below (see Authorization) — the whole decision pipeline
versions together, mirroring `model_version`'s scope in ADR-012.

## Authorization (§37 — separate from policy)

`authorize(selected_action, primary_facet_confidence_label)` is a second,
independent pure function — it does not re-run the scoring policy, only
checks the policy's output:

1. `TEACHER_INTERVENTION` → always **ESCALATED** (§81: high-impact
   educational decisions must remain reviewable; this action is inherently
   "flag a human," never auto-executed).
2. Any of `{EASIER_TASK, HARDER_TASK, TRANSFER_TASK,
   DELAYED_RETENTION_ASSESSMENT}` selected while
   `primary_facet_confidence_label == insufficient_evidence` → **REJECTED**
   (`insufficient_confidence_for_personalized_action`). This should rarely
   trigger, since the scoring formulas already down-weight these actions to
   near-zero when `w_APP = 0` — it exists as an independent defense-in-depth
   check per §37's requirement that generation and authorization be separate
   components, not because the policy is expected to need correcting often.
3. Otherwise → **ALLOWED**.

**Explicit scope gap**: role-based, tenant-policy-based, consent-based, and
age-based authorization (§37 lists these as inputs) are **not implemented**
in this phase. No consent or age data model exists yet in this codebase, and
fabricating a check that always returns "consent granted" would be exactly
the "no fake implementations" violation §105 forbids. This ADR records the
gap rather than hiding it; a future ADR must define the consent/age data
model before those checks can be real. Tenant-level policy is implemented
only as the `pde_shadow_mode_default` flag (below) — it affects visibility,
not the ALLOWED/REJECTED/ESCALATED verdict itself, in this phase.

## Shadow Mode (§38, §96)

`Tenant.pde_shadow_mode_default` (boolean, default `false`) is a
tenant-level feature flag: when `true`, every decision generated for that
tenant is stored with `is_shadow = true`, regardless of who requested it.
Independently, a staff-role caller (`TEACHER`/`SCHOOL_ADMIN`/`TENANT_ADMIN`/
`SUPER_ADMIN`) may pass `mode=shadow` on an individual request to force a
single dry-run without changing the tenant default; a student or parent
cannot request shadow mode — the tenant flag is the only way a student's own
decision request becomes shadowed, and in that case it is shadowed for
everyone equally, not selectively hidden from them. `mode=live` cannot
override a tenant-level shadow lock — the tenant flag is a hard floor, since
it is meant as a rollout safety switch, not something an individual caller
should bypass by passing a different `mode`.

**Explicit scope boundary**: "the decision does not affect the learner"
(§38) is enforced today only at the data/API level — `is_shadow` decisions
are excluded from the default `GET /decisions` history view and are never
the response to a non-staff caller who didn't explicitly request them. No
code path in this codebase currently *executes* any decision (assigns a
task, changes what content is served) for any learner, shadow or live —
that execution layer belongs to a later phase (dashboards/content delivery,
§113 P8+). This ADR records that boundary explicitly rather than claiming a
guarantee the system cannot yet fully back up (§105).

## Assumptions (stated explicitly)

1. Application is the primary/reference facet gating personalization
   (above) — the single biggest simplification in this model.
2. The specific coefficients and the `[0.4, 0.6]` "ambiguous evidence" band
   for `TEACHER_INTERVENTION` are hand-specified, not fitted — a first-cut
   heuristic explicitly flagged for revisit once pilot data exists (agreed
   with the product owner before implementation).
3. Reason codes are structural (per action type), not dynamically computed
   per instance.
4. Authorization does not yet implement role/consent/age/tenant-education-
   policy checks beyond the shadow-mode flag — explicit gap, not a silent
   omission.
5. `DEFER_DECISION`'s flat `0.05` floor means it can only ever be selected
   if every other action also scores at or below `0.05` — an extremely flat,
   uninformative evidence state across all five facets simultaneously. This
   is intentional: a genuine "nothing indicated" state should be rare by
   construction, since `INSUFFICIENT_EVIDENCE_ACTION` already dominates the
   "we know nothing" regime.

## Expected Behavior, Including Monotonicity

Holding `w_APP` fixed at `high_confidence` and `w_TRF` fixed at
`insufficient_evidence` (isolating the `p_APP` effect):
- `EASIER_TASK` score is non-increasing in `p_APP`.
- `HARDER_TASK` score is non-decreasing in `p_APP`.

Holding all facet inputs fixed, `score_candidates` is a pure function —
identical inputs always yield identical output (§99), verified directly
(no DB, no clock).

## Edge Cases

- All five facets at the prior (zero evidence): `w_APP = 0` →
  `INSUFFICIENT_EVIDENCE_ACTION` scores `1.0`, strictly higher than every
  other action's ceiling under `w_APP = 0`. Selected every time.
- `APP` at `low_confidence` with `p_APP` near `0.5` (ADR-012's
  "contradictory evidence" case): both `REVIEW_TASK` and
  `TEACHER_INTERVENTION` score highly; `TEACHER_INTERVENTION`'s hard `1.0`
  wins inside its narrow band, escalating genuinely ambiguous evidence to a
  human rather than letting the policy guess.
- `APP` and `TRF` both `high_confidence` and near `1.0` mastery, `RET`
  still `insufficient_evidence`: `DELAYED_RETENTION_ASSESSMENT` dominates —
  the skill is well-evidenced and untested for retention, exactly the
  intended trigger for a delayed-retention check (§30, prerequisite to
  Phase 7's 14/28-day scheduling).

## What Would Falsify This Model (§39)

- If, across real pilot usage, the action-type distribution is heavily
  skewed toward one or two actions despite genuinely varied learner states,
  the scoring coefficients (not just thresholds) need revision.
- If teachers report `TEACHER_INTERVENTION` firing too often or too rarely
  relative to cases they'd independently flag, the `[0.4, 0.6]` band and the
  `low_confidence`-only gate need revision.
- If `REJECTED` authorizations never occur in practice, the defense-in-depth
  check may be redundant with the policy's own down-weighting (not
  necessarily wrong, but worth knowing).
- If decision explanations (score + reason codes + knowledge-state snapshot)
  are reported by teachers as not actually explaining the "why," the
  structural (non-per-instance) reason-code design (Assumption 3) is too
  coarse and needs the dynamic-attribution follow-up noted above.

## Alternatives Considered

- **Learned/ML ranking model.** Rejected for v1: no labeled outcome data
  exists yet to train against, and §36 explicitly warns against aggressive
  personalization from sparse evidence — a hand-specified, auditable policy
  is the more defensible starting point, consistent with §98's mandate to
  define the model in an ADR before writing code.
- **First-matching-rule priority list** instead of scoring every action.
  Rejected: CLAUDE.md §32/§100 explicitly want a full ranked `candidate_actions`
  list with scores for every evaluated action, not just the winner, both for
  explainability and for the mandatory action-diversity test.
- **Dynamic per-instance reason-code attribution** (which term dominated).
  Deferred, not rejected — noted as a concrete follow-up (Assumption 3).

## Consequences

- `decision_policy.py` and `authorization_service.py` are separate,
  independently unit-testable modules with no DB access — mirroring
  ADR-012's "pure computation, DB-facing wrapper separate" shape.
- `POLICY_VERSION` must be bumped for any change to scoring, thresholds, or
  authorization rules; this is the single version field covering both.
- The execution-layer gap (shadow mode's guarantee, and authorization's
  missing role/consent/age checks) is explicitly tracked here, not hidden,
  and must be revisited before this system is used with real minors at
  scale (§81).

## Mandatory Tests (to be written in this phase)

- Every candidate action's score stays in `[0, 1]` under generated facet
  inputs (property-based).
- `EASIER_TASK`/`HARDER_TASK` monotonicity under the isolation above.
- Reproducibility: identical `FacetInput` dict → identical ranked list.
- Action diversity: at least six distinct crafted scenarios each select a
  different top action.
- Authorization: `TEACHER_INTERVENTION` always escalates; a forced
  insufficient-confidence personalization action is rejected and the
  rejection reason is present.
- Shadow: a tenant with `pde_shadow_mode_default = true` produces
  `is_shadow = true` decisions that are excluded from the default
  `GET /decisions` history.
- Cross-tenant negative tests (§52) on all three `/decisions` endpoints.

## Addendum (Phase 10, 2026-08-30): Consent/Age-Based Authorization

The Consequences section above flagged authorization's missing role/consent/
age checks as something to revisit "before this system is used with real
minors at scale." This addendum closes the age/consent half of that gap
(role- and tenant-education-policy-based checks remain open — no such policy
data model exists yet).

**What changed.** `User.date_of_birth` (nullable) and
`ParentStudentLink.consent_given_at` (nullable) were added (migration 0009,
purely additive, no backfill — §107). `authorization_service.authorize()`
gained a third rule: a student under 18 with no `ParentStudentLink` row
carrying a non-null `consent_given_at` has every otherwise-`ALLOWED` action
escalated to `ESCALATED` instead. The existing two rules (teacher-
intervention escalation, insufficient-confidence rejection) still take
precedence — the consent gate only intercepts what would otherwise have
been allowed to auto-execute.

**How consent is recorded.** Two new staff-only endpoints
(`POST /auth/tenant/users/{id}/date-of-birth`,
`POST /auth/tenant/parent-links`) let a `TENANT_ADMIN`/`SCHOOL_ADMIN`/
`SUPER_ADMIN` record facts already established through an external,
out-of-band process (a signed enrollment form, a phone call) — the
endpoints are an attestation, not a consent-collection UX. A self-service
parent-initiated flow is still deferred, unchanged from the original
`app/models/relationship.py` scope note.

**The unknown-age default.** A `null` `date_of_birth` is treated as "cannot
verify minor status," never as an assumed adult or an assumed minor — §105
forbids fabricating a fact the system does not have. This is a deliberate,
documented trade-off: it means the consent gate protects only students
whose age has actually been recorded, and every student who existed before
this migration (or who self-registered without supplying it) is unprotected
by this specific gate until an admin records their date of birth. This is
the same "safe to defer, but time-boxed" posture the MVP Gate report
(`docs/audit/MVP-GATE.md`) already used for this exact gap — closing the
code path was the prerequisite; populating real dates of birth for a real
student population is an operational rollout step for the next pilot, not
a code change.

**Falsifiability check.** This is not a Prometheus *scoring* change (§98's
mathematical-formulation process does not apply — `decision_policy.py` and
its `score_candidates` output are untouched); it is an authorization-layer
policy change (§37), reviewed under §134's ordinary priority rules instead.
