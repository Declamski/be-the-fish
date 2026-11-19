# Assignment 2 requirements (condensed from docs/Assignment_2.pdf)

**Split, Ship and Operate:** services, containers, CI/CD and Azure.
Deadline **2026-11-22 23:59**. Written comprehension check in the first class after the deadline.
A1 rules still apply. No new features required — same repo, same use case, same stack/language.
No infrastructure is provided: the student writes Dockerfiles, compose, pipeline and deployment,
and **any line in them can be asked about** at the comprehension check.

## Objective
1. Split along the A1 seam (ADR-2): one service per feature domain, own container, own data.
2. Run locally with one command: `docker compose up`.
3. Evolve the DB with versioned migrations that preserve data.
4. Every push is tested; every merge to main is deployed to Azure with no manual steps.
5. UI is a static site on Azure Static Web Apps, calling both services.
6. Each service reports its own health.

## 1a. Hard requirements
- **Exactly two service containers**, one per feature domain, each from its own Dockerfile.
- **Static UI** in `ui/`, deployed to one Static Web App (`<prefix>-ui`). Calls both services
  from the browser over HTTPS. Service base URLs are config (e.g. `config.js` generated at
  deploy time), not hardcoded. Each service allows CORS **only from the UI's origin**.
  Locally: stock web-server image (e.g. `nginx:alpine`, folder mounted, no Dockerfile) —
  not counted as a service container.
- **Database per service:** own serverless SQL DB, own login with no access to the other DB.
  No service connects to another's DB; other data is requested over HTTP.
- **HTTP between services**, located via env var (e.g. `SITES_URL=http://sites:8000`).
  No hardcoded hostnames/ports.
- **SQL Server.** Azure SQL Database serverless on Azure; locally one
  `mcr.microsoft.com/mssql/server:2022-latest` container with one DB per service (Apple Silicon:
  enable Rosetta in Docker Desktop). Each service reads `DATABASE_URL`. Locally DBs + logins are
  created by an idempotent `db/init.sql` run by a one-off compose service; on Azure, logins are
  created once during initial setup.
- **One repo**, each service in `services/<name>/` with its **own dependency manifest**
  (replaces A1's single-root-manifest rule).
- **System description:** `openapi.yaml` per service + `system.yaml` at root (§8a).
- **Own Dockerfiles:** no `COPY . .`, no secrets or `.env` in the image, pinned deps, non-root user.
- `docker-compose.yml` at root: `docker compose up --build` from a clean clone brings up everything.
- **CI/CD in GitHub Actions** (`.github/workflows/`), per §5.
- **Serverless Azure** per §7: Container Apps (Consumption), scale to zero. Nothing costs money idle.
- **No secrets in the repo** — not in source, workflows, compose, or Git history.

## 1b. Free choices (justify in ADR.md)
- Where the cross-seam flow lives: server side (service → service) or client side (UI calls both).
  **At least one flow must cross server side.**
- Behaviour when the other service is down: fail / degrade / cache / retry (must be handled).
- Migrations: numbered SQL files + own runner, or a tool (Alembic etc.).
- Infra definition: Azure CLI in the workflow, or IaC (Bicep/Terraform).
- Registry: GHCR (free) by default; ACR has a fixed cost and must be justified.
- Deps: soft cap ~12 third-party packages per service.

## 1c. Out of scope
Always-on compute (VMs, App Service plans, dedicated workload profiles, running Container
Instances), Kubernetes/AKS, message brokers (Redis, RabbitMQ, Service Bus), background job
runners, any other DB (provisioned Azure SQL, Postgres, MySQL, Cosmos, >1 DB per service),
service meshes, **a third container** (frontend, gateway…). If useful, document in ADR-10.

## 2. What changes from A1
- Each table belongs to exactly one service. A cross-seam FK becomes a plain ID; integrity is
  enforced in code or deliberately not enforced.
- Server-rendered pages → static UI fetching JSON. Services keep only their APIs.
- Joins across domains → HTTP call + code. Many such calls = seam misplaced.
- Seed data moves with its table; seeding stays idempotent.
- SQLite → SQL Server: `INTEGER PRIMARY KEY AUTOINCREMENT` → `INT IDENTITY`, `TEXT` → `NVARCHAR`,
  `LIMIT` → `TOP` / `OFFSET … FETCH`. Raw SQL must be ported. Python driver: pymssql or pyodbc.
- Moving the seam is allowed; ADR-6 must explain why.

## 3. Required behaviour
- Both domains work end to end through the UI, across two services.
- ≥1 user-visible flow crosses the seam (a request to one service that needs the other's data).
- **Partial failure:** with one service stopped (`docker compose stop <service>`) the other keeps
  serving its own domain; the cross-seam flow fails in a designed way (clear error, degraded
  response, cache) — no stack trace, no hung request. **Every outbound call has a timeout.**
- `GET /health` on every service: 200 `{"status":"ok","db":"ok","version":"<git sha>"}` when it
  can read **and write** its own DB, else 503. Own state only, not the other service's.
- Logs to stdout: ≥1 line per request (method, path, status, duration).

## 4. Database migrations
1. Schema defined by versioned migration files (`migrations/001_init.sql`, `002_...sql`), applied
   automatically and in order on startup.
2. Each runs exactly once, recorded in the DB (`schema_migrations`). Second boot applies nothing.
3. ≥1 migration changes a table **that already holds data** (add column with default/backfill,
   rename, split), preserving rows. Drop + recreate does not count.
4. Forward-only is fine; ADR-7 gives the recovery plan for a bad migration in production.
5. Applied migrations are never edited; corrections go in a new migration.
6. **Evidence on Azure:** DB has data before the migration in (3) is deployed and keeps it after.
   Report includes the deployment run, the startup log line showing the migration, data before/after.
Dropping tables on boot, recreating the DB on deploy, or deleting the volume are checked in the code.

## 5. CI/CD (GitHub Actions)
**Every push and PR (CI):**
- Install, lint (any standard linter), test each service.
- Validate `system.yaml` against `system.schema.json`; validate each `openapi.yaml` against the spec.
- Coverage per service; fail if either is <70% on core logic.
- Build every Docker image; a failed build fails the pipeline.

**Push to main only (CD):**
- Push images to a registry tagged with the **commit SHA** (not only `latest`).
- Deploy to Azure, only if CI passed on the same commit.
- Build + deploy the UI to its Static Web App (deployment token as a GitHub secret), with the
  service URLs as config.
- Call `/health` on deployed services; fail the run if not 200 within a set time.

**CI never touches Azure SQL** — tests use a SQL Server container (Actions service container or
the compose stack).

**Secrets:** professor's service principal stored as GitHub Actions secrets, read only by the
workflow. DB passwords and other secrets stored the same way and passed to Container Apps **as
secrets, never plain env vars**.

**Leaked secret** (pushed to GitHub = compromised, even if deleted later). Within 24h:
- own credential → revoke/rotate it and update the GitHub secret;
- professor's credential (class service principal) → notify the professor;
- both → remove from current code and record the incident in the README (what, when, what done).
Never revoked/rotated/reported at the graded commit → **grade capped at 40/100**.

**Testing beyond A1:** unit tests per service + **≥1 integration test across the seam**, against
the compose stack or with the other service stubbed (justify in ADR-9).

## 6. Process deliverables
- **ADR.md:** keep 1–5 unchanged (if a decision changed: `Status: Superseded by [N]`). Add
  **exactly 5 new entries, 6–10**, same format, spanning **≥3 distinct commit dates**:
  6. The split — where the seam is, what crosses it, did ADR-2 hold, why it moved if it did.
  7. Data and migrations — how data moved to one DB per service, integrity lost at the seam and
     how compensated, recovery plan for a bad migration.
  8. Serverless hosting on Azure — resources + cost model; scale-to-zero consequences (cold
     starts, DB resume from pause, connection retries, migrations at startup with one replica);
     changes needed at 100x traffic.
  9. Pipeline and testing — what CI gates on and why, how the cross-seam test works, what is
     deliberately not tested.
  10. One thing deliberately not built (from §1c or elsewhere) and when it would be worth building.
- **AI_USAGE.md:** same columns. Infra files produced by AI must be logged and explained in the
  "In my own words" column.
- **Commits:** ≥12 new commits after A1 submission, ≥6 distinct calendar days, no day >40%.
  Pushed to GitHub; push timestamps checked.

## 7. Azure deployment contract

> **Overridden by `docs/a2-azure-deployment-guide.pdf`** (later than the PDF brief): the
> individual assignment runs in your **own Azure for Students** subscription, in a resource
> group you create (`rg-<prefix>`); the pipeline signs in as your own **managed identity** via
> OIDC (no service principal); the UI is a **Storage static website**; SQL databases use the
> **free offer** (60-min auto-pause, 32 GB fixed); give the professors Reader on the group.
> The text below is the original brief — where it conflicts, the guide wins (see CLAUDE.md §5).
- Shared subscription. Class resource group already exists: `rg-sdd-3a` or `rg-sdd-3b`. Create
  everything there; **never create resource groups**.
- Pipeline signs in with the class service principal (Contributor on the class RG only; shared
  by the class; GitHub secret only; only touch resources with your prefix).
- **Allowance:** max 2 Container Apps, 2 serverless SQL DBs, 1 Static Web App. Nothing more, not
  even temporarily.
- **Naming:** prefix = IE username (before `@`), dots → hyphens, e.g. `jsmith-ieu2023-tasks`,
  `jsmith-ieu2023-sql`, `jsmith-ieu2023-tasks-db`. Never modify other students' resources.
- The deployed system must:
  1. Run both services on Container Apps (Consumption) and the UI on one SWA (`<prefix>-ui`),
     deployed only by the pipeline. After initial setup nothing is changed in the portal; initial
     setup documented step by step in the README or done by IaC.
  2. Public URL = the SWA's. Both services have public HTTPS ingress, CORS restricted to the UI.
  3. One Azure SQL serverless DB per service on one logical server (`<prefix>-sql`), named
     `<prefix>-<service>-db`: General Purpose, Gen5, min 0.5 / max 1 vCore, auto-pause at the
     shortest delay, max 2 GB, locally redundant backups. One login per service, own DB only.
     Firewall: allow Azure services; own IP only while needed.
  4. Min replicas 0, max 1 for every service.
  5. Tolerate cold starts: DB may be paused (up to ~1 min, error 40613) → connect with retries
     and backoff; request served (after pending migrations) within the HTTP timeout.
  6. Pay-per-use only: Container Apps Consumption, Azure SQL serverless, SWA, GHCR. Anything
     with a fixed cost justified in ADR-8.
  7. Configured entirely through env vars and secrets set by the pipeline or IaC.
  8. Reachable at the live URL until grades are published.
- Shared budget: single environment, delete experiments promptly.

## 8. Documentation
**8a. System description** (must match code + deployment at the graded commit; used in grading):
- `services/<name>/openapi.yaml` — OpenAPI 3, every endpoint incl. `/health`, methods,
  parameters, request/response schemas, status codes. Committed as a file. Endpoints one service
  calls on the other must exist in the other's document with the same shapes.
- `system.yaml` at root in the format of the provided `system.schema.json` (copy it to the root).
  First line: `# yaml-language-server: $schema=./system.schema.json`. Lists every service, its
  config, its calls across the seam (`url_env`, `endpoints`, `timeout_s`, `on_failure`) and its
  Azure resources. **Every env var a service reads is listed with its default; secrets have no
  default and `secret: true`.** (Example in the PDF, page 7.)

**8b. Report (4–5 pages):**
- Architecture diagrams before (A1 monolith) and after (split, seam, HTTP calls, DB per service).
- Deployment diagram: GitHub → Actions → registry → Azure (Container Apps, SQL DBs, SWA), naming
  the resources.
- DB diagram per service, matching the migrations.
- Migration evidence on Azure (§4.6).
- Partial-failure evidence (screenshot/response).
- Pipeline evidence: link to a successful CD run on main and one failed run that was fixed + cause.
- AI-disclosure statement as in A1.

**README:** run locally with compose; run a single service; tests + coverage; how deployment works
and how to reproduce the initial Azure setup; the live URL.

## 9. Version control
- Same repo as A1. Changes reach `main` through **pull requests** from branches (CI before CD).
- Graded version = commit tagged `submission`, on main, deployed, pushed before the deadline:
  `git tag submission <sha>` + `git push origin submission`. Tag and submitted SHA must match,
  otherwise the last commit on main before the deadline is graded.

## Deliverables
Repo URL + full SHA of the `submission` commit; services, Dockerfiles, compose, migrations,
workflows, `system.yaml`, `system.schema.json`, OpenAPI docs, updated ADR.md + AI_USAGE.md;
live Azure URL (README + report); report; attendance at the comprehension check.

## Grading
| Category | Weight | Breakdown |
|---|---|---|
| Split & working system | 20% | 10 both domains as separate services with own DBs · 10 cross-seam flow, timeouts, partial failure |
| Containers & migrations | 15% | 5 Dockerfiles + compose (clean clone) · 10 data-preserving migrations evidenced on Azure |
| CI/CD & deployment | 20% | 10 CI gates (tests, ≥70% per service, image builds) · 10 CD from main only, SHA tags, SWA, health check, serverless config, no secrets, live URL |
| Testing & observability | 10% | 5 cross-seam integration test · 5 `/health` + request logs |
| Documentation & report | 10% | 5 diagrams matching deployment · 5 system.yaml + OpenAPI matching code, README, evidence |
| Process evidence | 25% | 10 ADR 6–10 · 10 AI_USAGE.md · 5 commit cadence/hygiene + PR flow |
| × Written comprehension check | multiplier | |

Leaked, never-handled credential at the graded commit or in history → final grade capped at 40/100.
