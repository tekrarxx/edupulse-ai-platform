# ADR-021: Execution Layer — Decision → Real Question, Not a New Content System

Status: Accepted
Date: 2026-09-01
Related: CLAUDE.md §7 (Learning Action stage of the core loop), §34, §37,
ROADMAP.md P1, docs/PROJECT_STATUS.md

## Context

`docs/ROADMAP.md`'s P1 named the largest gap between "the engine decides
correctly" (proven by `docs/audit/MVP-GATE.md`'s PASS) and "a student
experiences that decision": the student dashboard rendered
`next_action_label` as inert text (`app/services/dashboard_service.py`'s
`_ACTION_LABELS`) with nothing to click into. §113 always placed content
delivery at P8+, deliberately deferred until the decision layer itself was
proven — that trigger has now fired.

The candidate action set (§34, `CandidateActionType`) has 12 members, but
not all of them are "answer a question" activities — `HINT`,
`WORKED_EXAMPLE`, `NEW_CONCEPT_EXPLANATION`, `TEACHER_INTERVENTION`, and
`DEFER_DECISION` are not, and `DELAYED_RETENTION_ASSESSMENT` already has
its own dedicated flow (`GET /retention/checkpoints/due`, Phase 7). Content
generation (writing new questions) is a separate, larger concern (§22's
assessment engine, potential future AI-assisted authoring per §23) that
this ADR deliberately does not touch.

## Decision

Add `app/services/task_service.py`: a single function,
`resolve_task_for_decision`, that maps a `Decision`'s `selected_action` to
a real, already-existing `Question` row for that skill — never generating
or inventing content (§105). Six of the twelve candidate actions have a
task mapping (`INSUFFICIENT_EVIDENCE_ACTION`, `RETRIEVAL_QUESTION`,
`EASIER_TASK`, `HARDER_TASK`, `TRANSFER_TASK`, `REVIEW_TASK`); the other
six deliberately do not (`ActionHasNoTask`) — this is a structural fact
about what those actions mean, not an unfinished mapping.

**Authorization is re-checked, not re-derived**: `resolve_task_for_decision`
refuses a decision whose `authorization_result != ALLOWED` or whose
`is_shadow` is `True` (`DecisionNotExecutable`) — §37's "authorization is a
separate gate from decision generation" means a student must not be able
to self-execute around an ESCALATED or REJECTED decision by simply asking
for its task. `GET /decisions/{id}/task` (`app/api/routes/decision.py`)
additionally requires the caller to *be* the decision's own student —
matching who can actually submit the resulting attempt
(`POST /assessment/attempts` always attributes the attempt to
`current_user`), so a parent or staff caller previewing on someone else's
behalf is out of scope for this slice, not silently allowed to submit on
the student's behalf.

**Content-selection heuristic, kept deliberately simple**: prefer a
`Question` the student has not yet attempted for the resolved facet; fall
back to the earliest-created one if every question has been attempted;
`EASIER_TASK`/`HARDER_TASK` order by `difficulty` ascending/descending;
`REVIEW_TASK` is the one exception that always prefers a repeat (repeating
known content is the entire point of "review"). No spaced-repetition
scheduling, no difficulty-adaptive search beyond this ordering — a future
concern if evidence shows this heuristic picks poorly, not a speculative
build now (§125).

**No new write path**: the student still submits their answer through the
existing, unchanged `POST /assessment/attempts`
(`app/services/assessment_service.py`) — the same Attempt/Observation/
Evidence chain every other assessment path already uses. This module only
answers "which question, for which decision"; it creates nothing.

## What Is Explicitly Not Built

- Content generation for actions with no existing `Question` (`NoQuestionAvailable`
  is a real, surfaced gap — the UI shows an honest "no question available yet"
  message, never a fabricated one, §105/§106).
- The six non-question actions (`HINT`, `WORKED_EXAMPLE`,
  `NEW_CONCEPT_EXPLANATION`, `TEACHER_INTERVENTION`, `DEFER_DECISION`) have
  no execution UI yet — still label-only, which is honest given none of them
  are currently backed by a content system.
- Difficulty-adaptive or spaced-repetition question selection beyond the
  ordering described above.

## Consequences

- `app/services/task_service.py` depends on `Decision` (PDE) and
  `Question`/`Attempt` (assessment) — a legitimate cross-domain read, since
  this module is the execution layer connecting the two, not part of
  either domain itself. It must never be imported by
  `decision_policy.py`/`authorization_service.py` (§35/§37 stay intact:
  the PDE still scores and authorizes with no knowledge of content
  availability).
- Adding a task mapping for a currently-excluded action (e.g. once
  `WORKED_EXAMPLE` content exists) is a one-line addition to
  `_ACTION_TASK_MAPPING`, not a redesign.

## Addendum (2026-09-01): Client-Side Gap Behind the Server-Side Gate

Found by browsing the parent dashboard live, not by inspection: the
server-side self-only check (`GET /decisions/{id}/task` 403s a non-owning
caller, described above) was always correct, but `SkillProgressCard`
(`apps/web/components/`) is shared between a student's own dashboard and
a parent's read-only view of a linked child — the "Başla" button rendered
on both, so a parent always saw a button that would 403 on click, surfaced
as a misleading "couldn't load, try again later" message for what is
actually a permanent permission fact, not a transient failure.

Fixed with a `canExecute` prop on `SkillProgressCard`, defaulting to
`false` — only `apps/web/app/dashboard/page.tsx` (the student's own view)
opts in. This is a UX-honesty fix (§90), not a security fix: the 403 was
always enforced correctly server-side; no unauthorized action was ever
possible, only a confusing message shown to someone who was correctly
blocked. A general lesson for future consumers of this shared component
(a future teacher-facing student-detail view, say): default any
new "act on the student's behalf" affordance to off, same as this one.
