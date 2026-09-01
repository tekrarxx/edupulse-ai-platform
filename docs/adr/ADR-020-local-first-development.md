# ADR-020: Local-First Development via Docker Compose

Status: Accepted
Date: 2026-09-01
Related: CLAUDE.md §9–§11, §91, §119–§120

This ADR documents a decision already in effect since Phase 1/P0 — the whole
project has been built and tested this way from the first commit, but it was
never written down as its own ADR (§102 gap, same as ADR-017–019). No code
changes accompany this ADR.

## Context

§9 requires EduPulse be fully developable locally, without depending on AWS,
Azure, GCP, Kubernetes, managed Postgres/Redis, external LLM APIs, cloud
queues, or cloud observability services. §119 additionally requires that
this not become "local-only" — the architecture must stay cloud-migratable
even while cloud adoption is deliberately deferred (§10).

## Decision

**`docker-compose.yml` at the repo root is the entire local development
environment**, one service per infrastructure/application concern
(`docker-compose.yml`):

- `postgres` — the authoritative database (§55), with a named volume
  (`postgres_data`) for persistence and an init script
  (`infrastructure/postgres/init/01-create-test-db.sql`) that creates the
  dedicated `edupulse_test` database the pytest suite runs against, so tests
  never write into local dev data.
- `redis` — caching/rate-limiting/temporary state (§93), never the
  authoritative store for historical learner state.
- `ollama` — the local-first LLM interface (§44), reached over
  `http://host.docker.internal:11434` from the `api` container. Optional and
  degrade-gracefully (§43): nothing is pulled or started by default, and
  `AI_REQUEST_TIMEOUT_SECONDS` bounds how long the API waits for it.
- `n8n` — workflow orchestration (§92), currently running the
  retention-checkpoint scheduler
  (`infrastructure/n8n/workflows/retention-checkpoint-scheduler.json`); §92
  is respected by keeping the actual retention logic inside
  `retention_service.py`, with n8n only calling the real API on a schedule,
  never embedding domain logic itself.
- `mailpit` — a local-dev-only SMTP catcher for password-reset emails,
  standing in for a real transactional-email provider without ever sending
  mail to a real inbox during development.
- `api` — the FastAPI backend (`apps/api`, `python:3.12-slim` per its
  `Dockerfile`), depending on `postgres`/`redis`/`mailpit` being healthy.
- `web` — the Next.js frontend (`apps/web`).

Configuration is entirely environment-variable driven (§108):
`.env.example` at the repo root is the single template every variable
`docker-compose.yml` references must appear in, copied to a local,
never-committed `.env` (`.gitignore` excludes it). Running natively
(non-Docker, e.g. `uvicorn` directly) is also supported by the same `.env`
file — variables like `OLLAMA_BASE_URL` and `DATABASE_URL` carry two
documented values in their `.env.example` comments (one for native, one for
the Docker-internal hostname override), rather than requiring a second
config file.

## Cloud Migratability (§119–§120)

Local-first is not local-only: every domain-logic module in
`apps/api/app/services/` reaches Postgres/Redis only through SQLAlchemy
sessions and the `redis` client — there is no filesystem-only state, no
`localhost`-hardcoded business logic, and no single-machine assumption
baked into a service function's signature. §120's migration principle
("replace infrastructure adapters, not domain logic") is achievable as-is:

- Local PostgreSQL → managed PostgreSQL: a `DATABASE_URL` change.
- Local Redis → managed Redis: a `REDIS_URL` change.
- Ollama → an external AI provider: the AI Gateway's provider-router
  boundary (ADR-015) exists precisely so this is a routing config change,
  not a rewrite of any caller.
- Docker Compose → a cloud deployment target: out of scope until Phase 10+
  (§113), deliberately, per §10's "first build a correct system, then move
  infrastructure to the cloud."

## Alternatives Considered

- **A cloud-hosted dev environment from the start** (e.g. a shared staging
  Postgres, a hosted LLM API for every developer): rejected per §9/§10 —
  couples local iteration speed to network availability and cloud cost from
  day one, and violates the explicit "MUST NOT be introduced merely because
  it is considered production-like" rule (§10).
- **A single `docker-compose.yml` service running everything in one
  container** (Postgres, Redis, API, web all in one image): rejected — loses
  the ability to reason about each service's health check, restart policy,
  and volume independently, and does not mirror how these components will
  actually be deployed later (§120's "infrastructure adapters" framing
  assumes they are already separable).

## Consequences

- Any new infrastructure dependency must justify itself against §11's "MUST
  NOT be added without a concrete reason" and get its own service entry with
  a health check, matching the pattern above — not be bolted onto an
  existing service's container.
- `.env.example` must stay exhaustive: every variable a service in
  `docker-compose.yml` references must have a documented entry there (this
  session found and fixed a drift where the local `.env` was missing 10
  variables `docker-compose.yml` already required — a process gap this ADR
  now names explicitly so it doesn't recur silently).
