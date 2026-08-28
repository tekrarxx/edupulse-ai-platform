# ADR-014: Transfer Variants, Delayed Retention, and Falsification

Status: Accepted
Date: 2026-08-28
Related: CLAUDE.md §29–§31, §39, §98, §113 P6

Per §98, this ADR documents the retention-scheduling trigger, the
falsification verdict rule, and the failure-mode classification boundary
before/alongside the Phase 7 implementation — the same discipline ADR-012
and ADR-013 applied to their respective pieces of Prometheus.

## Context

Phase 4 already tags `Evidence.facet_type = TRANSFER` and `= RETENTION` as
distinct facets (§28), and Phase 5's Beta-Binomial model already keeps them
statistically independent (ADR-012). What's still missing: (1) an explicit
structural link from a transfer item back to the base item it varies from
(§29 — right now "transfer" is only a facet tag, not a modeled
relationship); (2) a real 14/28-day delayed-retention checkpoint mechanism
(§30); (3) a falsification framework that turns a knowledge-state
prediction into a checkable claim with a recorded verdict (§39); (4)
discrimination among failure modes for negative evidence (§31), which
`app/models/evidence.py`'s own docstring explicitly deferred to this phase.

## 1. Transfer Variants (§29)

`Question` gains two nullable columns: `source_question_id` (self-FK) and
`surface_variation` (free text describing what changed — e.g. "same
Newton's-second-law relationship, different everyday scenario and numbers").
A transfer-facet `Question` *may* reference the base (non-transfer) item it
varies from. This is additive and optional — not every transfer item needs
a recorded source, but when a transfer item is deliberately authored as a
surface-varied sibling, the relationship is now first-class data, not just
inferred from the shared `skill_id` and a `TRANSFER` facet tag. This
directly represents §29's "changes surface characteristics while preserving
the underlying skill" as an explicit edge, not a convention.

No new scoring or evidence-weighting logic changes here — a transfer
attempt still produces `Evidence` exactly as it does today (ADR-012's
`TRANSFER` facet handling is unchanged).

## 2. Delayed Retention Scheduling (§30)

### Trigger

A `RetentionCheckpoint` pair (14-day, 28-day) is scheduled for
`(tenant, student, skill)` the **first time** the `APPLICATION` facet's
knowledge state (recomputed via the existing Phase 5 service) reaches
`confidence_label == high_confidence`, evaluated immediately after each
graded attempt inside `assessment_service._apply_evaluation`. Rationale for
using `APPLICATION` as the trigger facet: it is the same "primary/reference
facet" ADR-013 already treats as the skill-level readiness signal — reusing
it here keeps the two ADRs' notion of "the skill is meaningfully learned"
consistent rather than inventing a second criterion.

Scheduling is **idempotent per `(tenant, student, skill)`**: once any
`RetentionCheckpoint` exists for that triple, no more are scheduled,
regardless of how many further high-confidence crossings occur (enforced by
a unique constraint on `(tenant_id, student_user_id, skill_id,
checkpoint_days)`, not just application-level convention). This is a
deliberate v1 simplification — only the *first* mastery event per skill
gets a retention check, not every subsequent one.

### Completion

A checkpoint is completed via a delayed-retention `Attempt`
(`assessment_type = DELAYED_RETENTION`, already an existing enum value)
against a **question targeting the same skill**. **Explicit v1
constraint**: the question must be auto-gradable (`correct_answer` set) —
open-ended delayed-retention grading is deferred, since the falsification
verdict (below) needs a definite `is_correct` at completion time, and
introducing async manual-grading-then-verdict is unnecessary complexity for
the first version. On completion, the knowledge state is recomputed and the
resulting `mastery_probability` is stored on the checkpoint as
`retention_estimate` — a real number with an explicit `as_of`, never "a
single unexplained percentage" (§30's own warning).

## 3. Falsification (§39)

Each scheduled `RetentionCheckpoint` gets exactly one linked `Hypothesis`
row, created at scheduling time with the **frozen** prediction: the
`APPLICATION` facet's `mastery_probability` and `confidence_label` *at
scheduling time* (not recomputed later — a falsifiable prediction must be
fixed before the outcome is known).

### Verdict rule

At checkpoint completion, given the frozen prediction
`(predicted_mastery_probability, predicted_confidence_label)` and the
delayed attempt's `is_correct`:

```
if predicted_confidence_label != high_confidence:
    verdict = INCONCLUSIVE   # can't meaningfully falsify a claim the
                              # system itself was not confident about
else:
    predicted_correct = predicted_mastery_probability > 0.5
    verdict = SUPPORTED if predicted_correct == is_correct else NOT_SUPPORTED
```

This is a deliberately simple, documented-as-provisional rule (same honesty
as ADR-013's scoring coefficients): a single delayed attempt is a noisy
single sample of "did retention hold," and `0.5` as the correct/incorrect
threshold is an assumption, not a derived value. A `NOT_SUPPORTED` verdict
is recorded and surfaced via the API — nothing about the knowledge-state
model automatically changes in response (§39: "the system must be able to
record that it was wrong," not silently self-correct); model revision in
response to falsification is a human/future-ADR decision, not an automatic
one.

## 4. Failure-Mode Discrimination (§31)

`Evidence` gains a nullable `failure_mode` column with six values:
`LACK_OF_KNOWLEDGE, RETRIEVAL_FAILURE, CARELESS_ERROR, MISCONCEPTION,
TRANSFER_FAILURE, RETENTION_FAILURE`. Two different write paths, by design:

1. **Structural, automatic**: if the negative evidence's `facet_type` is
   `TRANSFER` or `RETENTION`, `failure_mode` is set to `TRANSFER_FAILURE` /
   `RETENTION_FAILURE` automatically at evidence-creation time — this is
   not an inference beyond what the system already recorded (the facet type
   itself), so auto-setting it violates nothing in §31.
2. **Manual, teacher-only**: `LACK_OF_KNOWLEDGE`, `RETRIEVAL_FAILURE`,
   `CARELESS_ERROR`, and `MISCONCEPTION` can **only** be set by an explicit
   `POST /assessment/evidence/{id}/failure-mode` call from a grader role
   (teacher/school admin/tenant admin/super admin) — never automatically
   inferred from a single incorrect answer (§31's explicit warning: "an
   incorrect answer MUST NOT automatically become misconception=true"). A
   `RECOGNITION`/`RECALL`/`APPLICATION`-facet negative evidence row starts
   with `failure_mode = NULL` ("unclassified") and stays that way unless a
   human classifies it. Classification is one-shot — once set, a second
   classification attempt is rejected, preventing silent reclassification.

## Assumptions

1. `APPLICATION` facet, `high_confidence` crossing = the retention-scheduling
   trigger — same choice as ADR-013's primary-facet gating, for consistency.
2. Only the *first* high-confidence crossing per skill schedules checkpoints
   (idempotent, not re-triggered).
3. Delayed-retention completion requires an auto-gradable question (v1
   constraint, documented, not hidden).
4. The falsification verdict's `0.5` threshold and single-attempt sampling
   are first-cut, flagged for revisit once real 14/28-day pilot data exists.
5. Structural failure modes (transfer/retention) are set automatically;
   ambiguous ones require a human — this is the single most important
   invariant in this ADR and is enforced by the service layer, not just
   convention (there is no code path that sets `MISCONCEPTION` other than
   the explicit classification endpoint).

## What Would Falsify This Model (§39, applied to itself)

- If `NOT_SUPPORTED` verdicts cluster heavily around one skill or one
  learner population, the retention-scheduling trigger or the model's decay
  half-life (ADR-012) likely needs revision.
- If teachers report the automatic `TRANSFER_FAILURE`/`RETENTION_FAILURE`
  tagging as misleading in specific cases (e.g. a transfer item that was
  actually a careless slip, not a transfer failure), the "structural ⇒
  automatic" rule in §4 is too coarse and needs a teacher-override path.
- If the `0.5` verdict threshold produces `NOT_SUPPORTED` for predictions
  that were only barely above `0.5` (e.g. `0.51`), that is evidence the
  threshold needs a margin/band rather than a hard cutoff.

## Alternatives Considered

- **Recompute the prediction at completion time instead of freezing it at
  scheduling time.** Rejected: a falsifiable prediction must be fixed
  before the outcome is observed, or it isn't actually falsifiable — it
  would just be re-describing the outcome after the fact.
- **Schedule a checkpoint on every high-confidence crossing, not just the
  first.** Deferred: meaningfully more scheduling/dedup complexity for an
  MVP; first-crossing-only still validates the full loop.
- **Allow open-ended delayed-retention questions with async grading.**
  Deferred, not rejected — needs a "pending verdict, evaluate later" state
  this ADR intentionally avoids for v1 simplicity.

## Consequences

- `retention_service.py` owns scheduling, due-listing, and completion —
  reuses `knowledge_state_service` and `assessment_service.submit_attempt`
  rather than duplicating their logic.
- **Explicit scope gap, consistent with the Pre-Implementation Report**:
  no scheduler/cron/n8n service exists in this repo's `docker-compose.yml`.
  `GET /retention/checkpoints/due` is real, correct application logic that
  a future scheduler would poll — it is not itself a scheduler. This gap is
  tracked for closure in a later phase, not treated as permanent.
- The failure-mode automatic/manual split is the enforcement point for
  §31 and must be preserved by any future change to evidence creation.

## Mandatory Tests

- Retention checkpoints schedule exactly once per `(tenant, student,
  skill)`, at the correct `scheduled_for` offsets (14d, 28d), including
  correctness across a DST boundary.
- Verdict rule: all three verdicts (`SUPPORTED`, `NOT_SUPPORTED`,
  `INCONCLUSIVE`) are reachable and match the documented rule exactly.
- `failure_mode` is never automatically set to `MISCONCEPTION`,
  `CARELESS_ERROR`, `RETRIEVAL_FAILURE`, or `LACK_OF_KNOWLEDGE` by any
  automatic code path — only `TRANSFER_FAILURE`/`RETENTION_FAILURE` are
  ever auto-set, and only for their matching facet.
- Cross-tenant negative tests (§52) on all new endpoints.
