# n8n workflows

## retention-checkpoint-scheduler.json

Closes the MVP-GATE "retention-checkpoint scheduler" gap: `GET
/retention/checkpoints/due` (real application logic, unchanged) previously
had no automated caller — a human had to poll it manually. This workflow
polls it on an hourly schedule instead. No core Prometheus/domain logic
lives in the workflow itself (§92) — it only calls existing, already-tested
API endpoints and summarizes the result.

**What it does**, in order:
1. **Every Hour** (Schedule Trigger) — or **Manual Test Run** (Execute
   Workflow Trigger), for on-demand verification without waiting for the
   schedule.
2. **Login As Scheduler** — `POST /auth/login` as a dedicated staff
   account, using `$env.RETENTION_SCHEDULER_EMAIL` /
   `$env.RETENTION_SCHEDULER_PASSWORD` (never written into this file — see
   Setup below).
3. **Get Due Checkpoints** — `GET /retention/checkpoints/due` with the
   access token from step 2.
4. **Summarize Due Count** — reduces the response to
   `{ due_checkpoint_count: N }`, visible in n8n's own execution history.

**What it deliberately does not do**: administer the delayed retention
question to the student, or send an email/push notification. Neither a
content-delivery/execution layer nor a notification channel exists in this
codebase yet (both explicitly out of scope elsewhere — see
`docs/audit/MVP-GATE.md`); this workflow's job is only to replace "a human
manually polling," per the gap it closes. `n8n`'s own execution list is the
real, inspectable output for now — a genuine artifact, not a stand-in for a
notification that isn't built.

## Setup (one time per environment)

1. Bring up n8n: `docker compose up -d n8n`.
2. Create the scheduler's staff account (a real `TEACHER`, the
   least-privileged role that satisfies this endpoint's access check) in
   the tenant you want it to poll:
   ```
   docker compose exec api python3 scripts/seed_retention_scheduler_account.py \
     --tenant-id <your-tenant-id> --email scheduler@yourschool.example --password <a-real-password>
   ```
3. Set `RETENTION_SCHEDULER_EMAIL` / `RETENTION_SCHEDULER_PASSWORD` in your
   `.env` to that account's credentials, and restart n8n so it picks them up:
   `docker compose up -d n8n`.
4. Open the n8n UI (`http://localhost:5678`, basic-auth login from
   `N8N_BASIC_AUTH_USER`/`N8N_BASIC_AUTH_PASSWORD`) and import
   `retention-checkpoint-scheduler.json`, or via CLI:
   `docker compose exec n8n n8n import:workflow --input=/workflows/retention-checkpoint-scheduler.json`.
5. Activate the workflow in the n8n UI (toggle "Active") so the hourly
   schedule actually runs — an imported workflow starts inactive.

This workflow currently targets **one tenant** (the account from step 2
belongs to exactly one tenant, and `/retention/checkpoints/due` is
tenant-scoped by the caller's token — §51). A school running multiple
tenants needs one scheduler account and one activated workflow copy per
tenant; a true cross-tenant poller is not built, since no cross-tenant
staff endpoint exists (by design — §52).

## Verified

Imported and executed via `n8n execute --id=retention-checkpoint-scheduler`
against the real local API in this session: confirmed `due_checkpoint_count`
correctly reports `0` for a tenant with no due checkpoints and `1` after a
real checkpoint (created through the ordinary evidence → high-confidence →
`maybe_schedule_checkpoints` path) was backdated into its due window. Not
yet exercised on a real schedule over real wall-clock time, or against more
than one tenant — those remain real, if lower-risk, gaps for the next pilot.
