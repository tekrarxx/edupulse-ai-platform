# ADR-002: Multi-Tenancy & Tenant Isolation Enforcement

Status: Accepted
Date: 2026-08-28
Related: CLAUDE.md §50–§52

## Context

EduPulse is multi-tenant from the first schema (§50). Every tenant-owned
table (`users`, `parent_student_links`, `teacher_student_links`,
`audit_logs`, and every education/assessment table that will follow) carries
a `tenant_id` foreign key. The open question is *where* isolation is
enforced: application code, the database (Postgres Row Level Security), or
both.

## Decision

**Enforce tenant isolation at the application/repository layer for this
phase.** Specifically:

1. `tenant_id` is never accepted from the client (not a query param, not a
   request body field, not a header). It is derived exclusively from the
   authenticated user's access token, re-validated against the current DB
   row in `app/api/deps.py::get_current_user` on every request.
2. Every query against a tenant-owned table filters by
   `current_user.tenant_id`. The `GET /auth/tenant/users` endpoint
   (`app/api/routes/auth.py`) is the reference implementation and the target
   of the mandatory cross-tenant test (§52).
3. Postgres Row Level Security is **deferred, not rejected**. It is
   evaluated here and picked up as a slice once there are several
   tenant-owned tables with real query traffic through them (Phase 3+),
   because:
   - RLS policies are Postgres-specific. The test suite currently runs
     against SQLite when Docker/Postgres is unavailable (§86, `tests/conftest.py`),
     so RLS enforcement could only be verified in the Postgres-backed
     integration/docker test run, not the fast local loop — that gap needs
     its own test-infrastructure decision, which is out of scope for this
     slice.
   - Application-layer enforcement is fully testable right now and gives
     the mandatory §52 negative test a clear, inspectable enforcement point.
   - RLS is additive defense-in-depth, not a replacement for correct
     application logic — adding it later does not require touching the
     tables added in this phase, only new `CREATE POLICY` statements.

## Alternatives Considered

- **RLS as the only enforcement layer**: rejected — leaves the application
  layer trusting client input if a policy is ever misconfigured, and cannot
  be exercised by the SQLite fallback tests.
- **RLS + application layer together, now**: deferred rather than rejected,
  for the testing-infrastructure reason above. Revisit explicitly before
  Phase 3 introduces the first high-volume tenant-scoped tables
  (curriculum, assessment).

## Consequences

- Every new tenant-scoped route MUST derive `tenant_id` from
  `get_current_user`, never from client input. Code review should treat a
  client-supplied `tenant_id` field on a request schema as a defect.
- The mandatory cross-tenant negative test (§52, §88) is required for every
  tenant-scoped endpoint added from this phase forward.
- RLS adoption is tracked as an open follow-up, not silently dropped.
