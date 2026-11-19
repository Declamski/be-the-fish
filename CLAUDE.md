# CLAUDE.md — Be the Fish (IE University DevOps, Individual Assignment 2)

Strava-style logbook for scuba divers, freedivers and spearfishers. Built by Declan (student).
Assignment 1 (Flask + SQLite monolith) is finished and on `main`. Assignment 2 splits it into
two services, containerises it, adds migrations and CI/CD, and deploys it to Azure.
Deadline: **2026-11-22 23:59 (Europe/Madrid)**. Graded coursework — read the rules below first.

Detailed context — read the relevant one before working on that area:
- @docs/ASSIGNMENT2.md — A2 requirements, Azure contract, CI/CD, grading, what is banned
- @docs/PLAN2.md — day-by-day plan, commit cadence, status log, open ADR decisions
- @docs/DATA.md — watch data, CSV importer, privacy rules (schema there is the A1 SQLite one)
- `docs/a1/` — the Assignment 1 brief and plan, history only. Where A1 and A2 conflict, A2 wins.

---

## 1. Rules for you (Claude Code) — non-negotiable

1. **The student must be able to explain every line closed-book** — including every line of
   Dockerfiles, compose, workflows, migrations, SQL and IaC. Write the simplest thing that
   works. No clever one-liners, no abstractions "for later". Prefer explicit over DRY.
2. **Discuss before building.** Propose the design and the open questions, wait for the
   student's OK, then write code. Only small mechanical choices may be defaulted.
3. **Small steps.** One feature or layer per task. After each task, explain in plain English
   what each new function/file does, naming them. For infra files, explain line by line.
4. **ADR.md and AI_USAGE.md — Claude writes them, in the student's style:**
   - **ADRs (6–10):** Claude writes the full entry from the decisions the student made (ask if
     a decision is not made yet — never invent one). Old ADRs 1–5 are only changed to add
     `Status: Superseded by [N]` when the student agrees. Each new ADR goes in its own commit,
     and ADRs 6–10 must land on ≥3 different commit dates (brief §6).
   - **AI_USAGE.md:** after each meaningful task Claude appends a row and fills columns 1–5
     completely (Date, Tool `Claude Code`, Prompt, Disposition, What changed & why). Rows go in
     the "Assignment 2" table. Infra files (Dockerfile, compose, workflows, IaC) are logged too.
   - **The "In my own words, how this works" column is NEVER written by Claude** — the heading
     says the words are the student's. Leave `TODO: write yourself`. Claude may help by
     (a) tidying grammar/function names of what the student says, keeping their meaning, or
     (b) quizzing the student, whose answers become the column.
   - **Style = copy the existing entries (ADR 1–5, the A1 AI_USAGE rows). There is no other
     style guide.** That means:
     - ADR layout: `## N. Title`, then `* **Date:**`, `* **Status:** Decided`, `* **Context:**`,
       `* **Decision:**`, `* **Alternatives considered:**`, `* **Consequences:**`, `---` between.
     - First person ("I decided", "I chose"), plain and direct, like a student explaining to the
       professor — no marketing words, no bullet lists inside fields, 1–4 sentences per field.
     - Alternatives: name each one, then a colon and why it was rejected
       ("Running the tests on the actual database: It just adds too much complication…").
     - Consequences: honest about the downside first, then what it enables.
     - AI_USAGE "What changed & why": first person, says what the student decided vs. what
       Claude proposed ("My decision: …", "(my call)", "Claude first … ; I rejected that"),
       real function/file names in backticks, 2–3 sentences.
     - Date = the day the entry is committed (YYYY-MM-DD).
   Alongside each AI_USAGE row, append an entry to `notes_from_AI.md`: what it does in plain
   English, why this approach, alternatives considered.
5. **Git:**
   - **Never run `git add`, `git commit`, `git push`, `git tag` or open PRs.** The student does
     all of these themselves. You may propose a descriptive commit message (what and why).
     No `Co-Authored-By` trailer in any proposed message.
   - Never suggest `--amend` on pushed commits, `rebase`, `reset --hard`, force-push, or setting
     `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE`. Backdated history is an academic-integrity violation.
   - Never propose "Initial commit", "WIP", "update", "fix" as a message.
   - Work happens on branches; changes reach `main` only through pull requests.
6. **Secrets:** never write a password, connection string with a password, token, Azure
   credential or service-principal value into any file (source, compose, workflow, README,
   docs). Secrets come from GitHub Actions secrets / Container Apps secrets / local env vars.
   Local compose may use an obviously-local dev SA password only via env var substitution
   with no real credential committed — discuss with the student first. If a secret is ever
   committed, stop and tell the student: it must be revoked/rotated (or reported to the
   professor if it is the class service principal) within 24h and recorded in the README.
7. **Never commit real dive data or GPS coordinates.** Real exports live in `imports/`, local
   data in `data/` — both gitignored. Test fixtures must be sanitised (see docs/DATA.md).
8. **Dependencies:** ask before adding any third-party package. Soft cap ~12 per service.
9. If a request conflicts with docs/ASSIGNMENT2.md or the decisions below, say so instead
   of doing it.

## 2. Stack (same as A1 — do not change language or framework)

- Python 3.13, managed with **uv**. **One `pyproject.toml` + `uv.lock` per service**
  (`services/<name>/`). This replaces A1's single-root-manifest rule.
- **Flask** services exposing **JSON APIs only** (no Jinja pages any more).
- **SQL Server** with raw SQL through **pymssql**. No ORM. Azure SQL serverless on Azure,
  `mcr.microsoft.com/mssql/server:2022-latest` locally.
- **Static UI** in `ui/` (HTML/CSS/vanilla JS), calls both services from the browser.
  Hosting: `system.schema.json` says Azure **Storage static website** (`dvandamieu2024ui`),
  the PDF says Static Web Apps — conflict open (docs/PLAN2.md). Follow the schema meanwhile.
- **`system.schema.json`** (repo root, from the professor) is the format `system.yaml` must
  pass in CI: every env var listed, secrets `secret: true` with no default.
- Auth: **token in a request header** (not cookies) — UI and services are on different origins.

## 3. Decided architecture (from the student — follow it)

Exactly **two service containers** (professor's instruction):

```
services/dives/   # dives + feed + users/auth. One container, one database (dives-db).
                  # dives, feed, users stay separate packages; no domain imports another's
                  # repository (ADR-2 rule still applies inside the service).
services/sites/   # sites only. Read-only seeded catalogue, no auth. Own database (sites-db).
ui/               # static site → Azure Static Web App; nginx:alpine in compose (no Dockerfile)
db/init.sql       # local only: idempotent creation of both databases + one login each
docker-compose.yml  system.yaml  system.schema.json   # repo root
.github/workflows/  # CI on every push/PR, CD on push to main
```

Each service folder will hold: its package(s), `app.py`, `config.py`, `db.py`,
`migrations/NNN_name.sql`, `tests/`, `Dockerfile`, `openapi.yaml`, `pyproject.toml`, `uv.lock`.

- **The seam:** the only cross-service flow is **dives → sites over HTTP**
  (`site_exists`, `search_sites`, `get_site_label`). Sites never calls dives.
  Located via `SITES_URL`; **every outbound call has a timeout** (`SITES_TIMEOUT_S`).
- **Partial failure:** if sites is down, dive pages still work and show "site unavailable";
  creating/editing a dive with a site returns a clear error. Never a stack trace or a hang.
- `dives.site_id` is a plain integer (no FK across the seam); integrity is checked in code
  through the sites API. Users, kudos and comments live in the dives database.
- Layer rules inside each service stay as in A1: `routes.py` thin (parse → service → JSON),
  `service.py` holds all logic and validation (what tests target), `repository.py` holds
  all SQL for that package's own tables. Services raise `ValueError`; routes turn it into a
  4xx JSON error.

## 4. Runtime contract (each service)

- Single process, binds `0.0.0.0`, `PORT` env var (default 8000).
- Configured **only** by env vars (no `.env` requirement). Every env var a service reads
  must be listed in `system.yaml` with its default; secrets have no default and `secret: true`.
  Expected: `PORT`, `DATABASE_URL` (secret), `SITES_URL`, `SITES_TIMEOUT_S`,
  `CORS_ORIGIN` (the UI origin), `VERSION` (git SHA), plus the token-signing secret.
- **Migrations:** numbered SQL files in `migrations/`, applied in order at startup by our own
  runner, each recorded in a `schema_migrations` table and run exactly once. Never edit an
  applied migration — corrections go in a new file. Never drop/recreate tables or the DB.
  At least one migration must alter a table that already holds data, preserving rows.
- **Seeding** (sites) is idempotent.
- Connect to the DB **with retries and backoff** (Azure SQL resumes from pause, error 40613).
- `GET /health` → 200 `{"status": "ok", "db": "ok", "version": "<sha>"}` when the service can
  read and write its own DB, else 503. Reflects only its own state, never the other service's.
- **Logs to stdout:** one line per request — method, path, status, duration.
- **CORS:** accept cross-origin requests only from the UI's origin.

## 5. Containers, CI/CD, Azure

- **Dockerfiles:** no `COPY . .`, no secrets or `.env` in the image, pinned dependencies
  (from `uv.lock`), run as a non-root user.
- `docker compose up --build` from a clean clone brings up: SQL Server, a one-off init service
  running `db/init.sql`, both services, and nginx serving `ui/`.
- **CI (every push + PR):** install, lint, test each service; coverage ≥70% per service on
  core logic (fail otherwise); validate `system.yaml` against `system.schema.json` and each
  `openapi.yaml`; build every image. Tests use a SQL Server container — **CI never touches
  Azure SQL**.
- **CD (push to main only, after CI passed on that commit):** push images to GHCR tagged with
  the commit SHA; deploy to Azure Container Apps; deploy `ui/` to Static Web Apps with the
  service URLs as config (`config.js` generated at deploy time); then poll `/health` and fail
  if not 200 in time.
- **Azure:** shared class resource group (`rg-sdd-3a`/`3b` — not known yet). Every resource
  prefixed with **`dvandam-ieu2024`** (IE username `dvandam.ieu2024`, dot → hyphen).
  Personal "Azure for Students" subscription must NOT be used — class RG only.
  Allowance: 2 Container Apps (Consumption, min 0 / max 1 replica), 1 SQL server
  `<prefix>-sql` with 2 serverless DBs `<prefix>-<service>-db` (Gen5, 0.5–1 vCore,
  shortest auto-pause, 2 GB, LRS backups), 1 Static Web App `<prefix>-ui`. Never create
  resource groups or extra resources, never touch other students' resources.
- **Out of scope:** VMs, App Service plans, AKS, Redis/queues/Service Bus, background job
  runners, any other DB, a third container (gateway/frontend), ACR without justification.

## 6. Commands

Whole system (repo root): `cp .env.example .env`, fill in passwords, then
`docker compose up --build` → dives http://localhost:8000, sites http://localhost:8001,
SQL Server on 127.0.0.1:1433 (sa password from .env; also usable for TEST_DATABASE_URL).
`docker compose down` keeps the data volume; never use `down -v` on data you need.

Single service / tests (inside the service folder) need a SQL Server reachable at the URLs below (compose or a local container).
`DATABASE_URL` / `TEST_DATABASE_URL` format: `mssql://user:password@host:port/database`.
Never write a real password into a file — pass it in the shell.

```bash
cd services/sites && PORT=8001 DATABASE_URL=... uv run python app.py
cd services/dives && DATABASE_URL=... SECRET_KEY=... SITES_URL=http://localhost:8001 uv run python app.py
cd services/dives && TEST_DATABASE_URL=mssql://sa:...@localhost:1433/dives_test \
    uv run pytest --cov=dives --cov=feed --cov=users --cov=migrate --cov=db --cov-report=term-missing
cd services/sites && TEST_DATABASE_URL=mssql://sa:...@localhost:1433/sites_test \
    uv run pytest --cov=sites --cov=migrate --cov=db --cov-report=term-missing
```
- Tests create the test DB if missing, migrate it once, and empty the tables before each test
  (`tests/conftest.py`). Without `TEST_DATABASE_URL` the DB tests are skipped.
- Dives tests replace the sites HTTP calls with `FAKE_SITES` (`services/dives/tests/conftest.py`).
- Schema changes = a NEW file `migrations/NNN_name.sql`, applied at startup by `migrate.py`.
  Never edit an applied migration. Note: in one batch, SQL Server cannot ALTER TABLE ADD a
  column and then use that column in the same file (compile error) — split or use `EXEC`.
- **New top-level file or folder in a service → add it to that service's Dockerfile COPY lines**
  (no `COPY . .`). Tests pass without it; only the container fails (`ModuleNotFoundError`).
- `GET /health` (`health.py`) uses `db.connect_once` (one try, 5 s) so it answers 503 fast;
  every other request uses `db.get_connection` (retries ~1 min). Request log = `log_request`
  in `app.py`; Flask's own werkzeug request log is silenced.
- **JSON API (for the static UI)** — dives service: `users.py` `api_bp` (`POST /api/signup`,
  `POST /api/login` → `{"token", "user"}`, `GET /api/me`, `/api/friends...`), `dives/api.py`
  (`/api/dives...`), `feed/api.py` (`/api/feed...`). Sites: `GET /api/sites?q=`,
  `GET /api/sites/<id>`. Logged-in calls send `Authorization: Bearer <token>`;
  `users.token_required` answers 401 otherwise and sets `flask.g.user_id`. Tokens are signed
  with `SECRET_KEY` (itsdangerous), valid `TOKEN_MAX_AGE_S` = 7 days, nothing stored server-side.
  Errors are `{"error": "..."}` with 400/401/404. The Jinja page routes (`routes.py`, cookie
  login) stay until the static UI replaces them (Fri), then get deleted.
- CORS: `add_cors_headers` in each `app.py` allows only `CORS_ORIGIN` (default
  `http://localhost:8080`, the local UI).
- SQL helpers live in each service's `db.py`: `query_one`, `query_all`, `execute`, `insert`
  (INSERT must contain `OUTPUT INSERTED.id`). Placeholders are `%s`.

## 7. Conventions (unchanged from A1)

- Units in column names: `max_depth_m`, `duration_s`, `water_temp_c`, `weight_kg`. SI units.
- Timestamps: ISO 8601 in the diver's local time, no timezone suffix (`started_at`).
- `discipline` values: `scuba`, `freedive`, `spearfishing`.
- Parameterised SQL only (pymssql uses `%s` placeholders). Never f-strings into SQL.
- SQL Server dialect: `INT IDENTITY` not `AUTOINCREMENT`, `NVARCHAR` not `TEXT`,
  `OFFSET … FETCH` / `TOP` not `LIMIT`.
- Tests never touch `./data` or Azure; use a temp/test database.
