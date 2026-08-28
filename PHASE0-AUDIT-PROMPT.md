# EduPulse AI — Phase 0: Repository Audit Prompt

Paste everything below the line into Claude Code as your first message in the repository.

---

## ROLE

You are performing a **read-only architectural audit** of the EduPulse AI repository.
This is Phase 0. No implementation happens in this phase.

## STEP 1 — READ THE CONSTITUTION

Read `CLAUDE.md` in full before doing anything else. It is the authoritative
engineering constitution (§0). Do not skim it, and do not rely on assumptions
about what a "typical" FastAPI/Next.js SaaS looks like.

When you have read it, state in one paragraph what you understand the product to
be and what the MVP loop is (§115), so I can correct you before you spend effort
on a wrong mental model.

## STEP 2 — HARD CONSTRAINTS FOR THIS PHASE

You MUST NOT, during this entire phase:

- create, modify, move, rename, or delete any file
- create migrations or touch Alembic in any way
- run any command that writes to the database
- run `git add`, `git commit`, `git checkout`, `git stash`, `git clean`, or any
  other state-changing git command
- run `docker compose up`, `down`, or anything that starts/stops containers
- install, upgrade, or remove dependencies
- reorganize the repository toward the target structure in §57
- write code, even as an "example" or "sketch"

Read-only commands are expected and encouraged: `ls`, `tree`, `cat`, `grep`,
`rg`, `find`, `wc`, `git status`, `git log`, `git branch`, `git diff` (without
writes), `alembic history` (read-only), reading Docker/compose files.

**Exception, explicitly authorized:** you may write exactly one file,
`docs/audit/PHASE0-AUDIT.md`, containing the final report. Nothing else.
If you would rather output to chat only, ask me first.

## STEP 3 — TERMINOLOGY WARNING

The word "Prometheus" is overloaded in this repository. Keep the two strictly
separate everywhere in your report:

- **PDE** — the Prometheus Decision Engine, the core adaptive-learning domain
  (§6, §32–39, §98–100). This is the product.
- **Prometheus/Grafana** — the metrics and observability stack (§83).

If you find code, packages, or config that could be either, say which one it is
and cite the file that told you.

## STEP 4 — INSPECTION

Inspect the repository and produce evidence for each of the following. Do not
guess. If something does not exist, write `NOT PRESENT` — never invent, never
infer from a package name alone, never describe what you assume is there.

1. Repository structure (full tree, excluding `node_modules`, `.venv`,
   `.next`, `__pycache__`, `.git`)
2. Applications present (`apps/web`, `apps/api`, `apps/admin`, or whatever
   actually exists)
3. Backend architecture — layering, module boundaries, whether routes are thin
   (§15, §16), whether the modular monolith boundary holds (§13)
4. Frontend architecture — Next.js version, routing model, state, UI library,
   and whether any authoritative business logic has leaked into it (§18)
5. Database models — every SQLAlchemy model, its table, its tenant column (if
   any), its FKs, its timestamp handling (§55)
6. Migrations — Alembic revision chain, current head, whether it is linear,
   whether anything is out of sync with the models
7. Docker configuration — services, health checks, volumes, networks (§91)
8. API endpoints — full route inventory: method, path, auth requirement,
   tenant scoping, request/response schema
9. **PDE** implementation status — knowledge state, Bayesian update, candidate
   actions, decision policy, explainability, shadow mode, falsification
   (§24–39)
10. **Prometheus/Grafana** observability status — metrics, exporters,
    dashboards, decision logging (§83–85)
11. Tests — what exists per layer (unit / integration / api / e2e, §86), plus
    whether property-based tests (§87) and cross-tenant tests (§88) exist
12. Authentication / authorization — mechanism, role model, where enforcement
    actually happens (§53, §78)
13. Tenant architecture — isolation strategy, where `tenant_id` is enforced,
    and whether any query path can escape it (§51, §52)
14. AI/LLM integration — gateway presence, providers, local-first status,
    cost controls, RAG (§43–49)
15. n8n integration — workflows present, and critically: whether any PDE logic
    has leaked into n8n (§92)
16. Event sourcing, provenance, and immutable telemetry (§40–42)
17. Documentation — `docs/`, ADRs (§101), README accuracy
18. Git status — branch, uncommitted changes, untracked files, recent commit
    history, anything that looks like work-in-progress

For each item, cite **actual file paths** (and line numbers where a specific
claim depends on them). A finding with no path behind it does not go in the
report.

## STEP 5 — REPORT

Produce the report with exactly these sections:

**1. CURRENT STATE**
What exists, per area, with file evidence. Distinguish three levels:
`IMPLEMENTED` / `PARTIAL` / `NOT PRESENT`. Include a short note on code quality
where it affects whether the existing work is worth keeping (§124).

**2. TARGET ARCHITECTURE**
What CLAUDE.md requires, cited by section number. Distinguish MVP-required
(§115) from later-phase (§116, §114).

**3. GAP ANALYSIS**
A table: `Area | Current | Target | CLAUDE.md § | Severity | Effort`.
Severity uses the §134 conflict priority order — a tenant-isolation gap
outranks a missing dashboard, always. Effort is S/M/L, not hours.

**4. RISKS**
Split into: (a) risks in the existing code, (b) risks created by the changes
you will later propose. Call out anything touching security, privacy, data
integrity, tenant isolation, or PDE scientific integrity (§98) explicitly.

**5. RECOMMENDED IMPLEMENTATION ORDER**
Map the gaps onto the P0–P10 priority ladder in §113. Every unit of work must
be a vertical slice (§126) and small enough to review (§125). State
dependencies between slices explicitly.

**6. FILES THAT SHOULD BE MODIFIED**
With a one-line reason each.

**7. FILES THAT SHOULD NOT BE MODIFIED**
Especially: existing migrations, working PDE math, anything carrying provenance
or event-sourced data (§40, §127, §135).

**8. DATABASE CHANGES**
Proposed schema deltas, and for each: additive or breaking, migration strategy,
backfill needs, index implications. Nothing destructive without justification
(§56).

**9. API CHANGES**
New / changed / deprecated endpoints. Flag every backward-incompatible change
(§107, §128).

**10. PDE (DECISION ENGINE) CHANGES**
Any change to decision logic, and how reproducibility (§99) and explainability
(§33) are preserved. If you propose changing the mathematics, say so loudly —
that requires explicit approval (§135).

**11. OBSERVABILITY / PROMETHEUS-GRAFANA CHANGES**
Metrics, decision logging, dashboards.

**12. TEST STRATEGY**
Per layer (§86), plus property-based (§87), cross-tenant (§88), and API (§89).
State what the first slice's tests look like concretely.

**13. OPEN QUESTIONS**
Anything ambiguous in CLAUDE.md, anything the repository contradicts, anything
you need me to decide. Do not resolve these yourself by picking a default.

**14. COVERAGE CHECKLIST**
The 18 inspection items from Step 4, each marked `INSPECTED` or `COULD NOT
INSPECT — reason`. This exists so nothing gets silently skipped.

## STEP 6 — STOP

After presenting the report, stop and wait.

Do not write code. Do not create migrations. Do not reorganize. Do not begin
the first slice. Do not ask "shall I start?" and then start.

I will review the report and approve a specific, named slice. Approval of the
analysis is not approval to implement.
