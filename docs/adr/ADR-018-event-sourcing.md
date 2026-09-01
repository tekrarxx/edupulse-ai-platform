# ADR-018: Event Sourcing via Observation, Not a Separate Event Store

Status: Accepted
Date: 2026-09-01
Related: CLAUDE.md §22–§23, §40–§41, §113 P3

This ADR documents a decision already in effect since Phase 3/P3 (migration
`0004_assessment_observation_evidence.py`) — never written down as its own
ADR (§102 gap, same as ADR-017). No code changes accompany this ADR;
`app/models/observation.py`'s own module docstring already states this
reasoning informally — this ADR is that reasoning made a formal, discoverable
record per §101.

## Context

§40 calls for immutable event-sourced telemetry of important learner
activity (`answer.submitted`, `answer.evaluated`, `decision.generated`, …),
each event carrying an event ID, tenant ID, actor, subject, timestamp, event
type, payload, schema version, correlation ID, and provenance, and never
silently mutated. Separately, §22 defines `Observation` as a directly
recorded fact with no hidden conclusion. The question this ADR answers:
build a distinct, general-purpose event store alongside `Observation`, or
let one system satisfy both requirements?

## Decision

**`Observation` (`app/models/observation.py`) is EduPulse's event log.**
There is no separate `events` table. `Observation` already carries every
field §40 requires:

| §40 requirement | `Observation` column |
|---|---|
| event ID | `id` |
| tenant ID | `tenant_id` |
| actor | `actor_user_id` |
| subject | `subject_type` + `subject_id` |
| timestamp | `occurred_at` |
| event type | `event_type` (a closed `ObservationEventType` enum — §22's own examples: `answer_submitted`, `answer_correct`, `hint_requested`, `task_completed`, `transfer_failed`, `retention_assessment_completed`, …) |
| payload | `payload` (JSON, primitive-scalar-only, enforced at the Pydantic boundary in `app/schemas/assessment.py`, not by the column type) |
| schema version | `schema_version` |
| correlation ID | `correlation_id` |
| provenance | `idempotency_key` (§130) plus the FK chain every downstream row carries back to it |

Immutability is enforced at the database level, not by application
convention: a Postgres trigger installed in
`alembic/versions/0004_assessment_observation_evidence.py` rejects `UPDATE`
and `DELETE` against `observations`. This holds even against a raw SQL
statement issued outside the service layer, or a future application bug that
bypasses `assessment_service.py` — a stronger guarantee than "the ORM layer
doesn't expose an update method."

`Evidence` (`app/models/evidence.py`) is the interpreted layer §23 requires
to sit downstream of — and always foreign-keyed to — exactly one
`Observation`. There is no API path that creates `Evidence` directly; it is
only ever produced by `assessment_service.evaluate_attempt`, which is what
guarantees every interpreted row traces back to a raw fact rather than
smuggling in an inference as if it were directly observed (§23's own
warning).

## Alternatives Considered

- **A separate, general-purpose `events` table plus `Observation` as a
  domain-specific view over it**: rejected. Every field §40 asks for and
  every field `Observation` needs (§22) are the same fields; building two
  parallel systems would mean either duplicating writes into both, or
  `Observation` becoming a thin wrapper with no independent reason to exist.
  `Observation`'s defining property — "a directly recorded fact, no inferred
  conclusion" — is already a *stricter* version of the general event-sourcing
  idea, not a different one.
- **Soft-delete / `is_deleted` flag instead of a hard DB-level immutability
  trigger**: rejected — a flag is an application-layer convention a bug or a
  raw SQL statement can still bypass; §56's "prefer soft deletion" is about
  *learner evidence and decisions generally*, but §40's "must not be
  silently mutated" for the event log specifically calls for a stronger
  guarantee, which only a DB-level constraint provides.
- **Event sourcing as its own microservice/queue** (e.g. publishing to a
  message broker before persisting): rejected per ADR-017/§14 — no concrete
  reason (independent scaling, isolation) exists yet for this to be
  anything other than a table in the same Postgres database the rest of the
  monolith already uses.

## Consequences

- Every future "did X happen" question is answered by querying
  `observations`, not by reconstructing state from mutable rows elsewhere.
- Any new learner-activity type that needs event-sourcing treatment should
  first ask "is this a new `ObservationEventType` member" before considering
  a new table — the enum is deliberately closed and extended, not
  duplicated (§22: "a client can never invent an event type").
- Because immutability is DB-enforced, any future correction to a mistaken
  observation must be a new compensating row, never an `UPDATE` — the same
  discipline real event-sourced systems require, gained here without a
  second piece of infrastructure.
