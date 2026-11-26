# Assignment 2 — plan & status

Deadline **Sun 2026-11-29 23:59 (Madrid)** (moved from 22 Nov). Work on branch `a2-split`, merge to `main` via PRs.

## Commit cadence (hard constraint)
- No A2 commits existed on 2026-11-17, and Tue 17 → Sun 22 is exactly **6 days**, so there must
  be a **pushed commit every day**. Push before ~23:00 Madrid.
- ≥12 new commits total; no day >40%. With 12 commits that is **max 4 on any day**
  (aim for 2–3 per day; Sun 22 only 1–2).
- ADR 6–10 must land on ≥3 distinct commit dates.

## Schedule

| Day | Work | ADR (student writes) |
|---|---|---|
| Tue 17 | Branch `a2-split`. Commit 1: docs (ASSIGNMENT2.md, CLAUDE.md, PLAN2.md, .gitignore). Commit 2: split into `services/dives` + `services/sites`, own `pyproject.toml`/`uv.lock` each, existing tests passing (still SQLite) | |
| Wed 18 | SQL Server port (pymssql), numbered-SQL migration runner + `001_init.sql`, idempotent seeding, Dockerfiles, `docker-compose.yml`, `db/init.sql`, `/health`, per-request logs | 6 |
| Thu 19 | JSON APIs, HTTP seam with timeouts + degraded responses, CORS, unit tests + cross-seam test, ≥70% coverage per service. Azure one-off setup (documented in README) | 7 |
| Fri 20 | Static UI in `ui/` (replaces Jinja), CI + CD workflows, first Azure deploy with 001 only, then insert data | 8 |
| Sat 21 | Migration 002 (alters a table with data, keeps rows) deployed to Azure = evidence; a failed-then-fixed CI run; OpenAPI per service + `system.yaml` | 9 |
| Sun 22 | README, report, final checks, `git tag submission`. Few commits | 10 |

## Decided (student)
- 2 containers: `services/dives` (dives + feed + users/auth) and `services/sites` (sites only).
- Only cross-seam flow: dives → sites over HTTP (`site_exists`, `search_sites`, `get_site_label`),
  via `SITES_URL`, every call with a timeout.
- Sites down → dive pages still work with "site unavailable"; creating a dive with a site
  returns a clear error.
- Users, kudos, comments live in the dives DB.
- Auth: token in a header, not cookies (UI and services on different origins).
- Migrations: numbered SQL files with our own runner.
- Dives → sites goes through `dives/sites_client.py` over HTTP from the start (no stub),
  stdlib `urllib.request` (no `requests`), sites exposes `GET /api/sites?q=` and
  `GET /api/sites/<id>`. Each service has its own copy of `app.py`/`config.py`/`db.py`
  (no shared package). Jinja pages stay in both services until the static UI on Fri.
- `CLAUDE.md` and `docs/` are tracked in git for A2 (they were gitignored in A1).

## Open — student decides, then writes the ADR
- ADR-1 → superseded? (Jinja server rendering replaced by a static UI.) Any other A1 ADR superseded?
- ADR-6: is putting feed + users inside the dives service a moved seam? (A1 had feed as its own
  domain; the brief says one service per feature domain — the professor said 2 containers.)
- ADR-7: what does migration 002 change? Recovery plan for a bad migration (forward-only fix,
  Azure point-in-time restore…)?
- ADR-8: infra as Azure CLI in the workflow vs Bicep/Terraform; cold-start + retry strategy; 100x.
- ADR-9: cross-seam test against compose stack vs stubbed sites; lint tool; what is not tested.
- ADR-10: what is deliberately not built (gateway, cache of sites, message queue, …).
- Token format for auth (signed token via Flask's `itsdangerous` vs random token stored in DB).

## Still needed from outside
- ~~IE username → Azure prefix~~ → `dvandam-ieu2024`.
- 2026-11-19: `az` logged in as dvandam.ieu2024@student.ie.edu, but NO access to rg-sdd-3a/3b
  (AuthorizationFailed). Only role: Owner on personal "Azure for Students" (not to be used).
  → refresh `az login` / ask professor for class RG access + service principal.
- ~~Class resource group~~ → not used: the deployment guide says own Azure for Students,
  own `rg-dvandam-ieu2024`.
- ~~`system.schema.json`~~ → added at repo root 2026-11-19.
- **RESOLVED by the deployment guide (Storage static website):** the schema says the UI is an Azure **Storage static website**
  (`ui.storage_account`, required; name = prefix without hyphens + `ui` → `dvandamieu2024ui`),
  while the PDF says Azure **Static Web Apps** (`<prefix>-ui`). `static_web_app` fails schema
  validation (`additionalProperties: false`). Following the schema until told otherwise.
- ~~Class service principal~~ → own managed identity + OIDC (guide step 6).
- GitHub repo is `Declamski/be-the-fish` (same repo as A1, renamed from sdd-assignment1.py on ~26 Nov; ids unchanged: owner 189633300, repo 1387287070). Local clone: /Users/declanvandam/be-the-fish.

## Status log
- 2026-11-17: read the brief; docs set up (CLAUDE.md for A2, ASSIGNMENT2.md, PLAN2.md, A1 docs
  moved to `docs/a1/`, .gitignore updated).
- 2026-11-17: split into `services/dives` (dives, feed, users; `dives.db`) and `services/sites`
  (sites; `sites.db`), each with own pyproject/uv.lock (same versions as A1). Dives calls sites
  over HTTP via `sites_client.py`; tests use a fake. 129 tests pass (dives 111, 71%; sites 18,
  79%). Not yet: handling sites being down (dive pages 500 if sites is stopped) — Thu.
  Root README still describes the A1 monolith — rewrite Sun.
- 2026-11-18: SQL Server port (pymssql 2.4.6 in both services). `db.py` per service: parses
  DATABASE_URL, connects with retries (waits 1,2,4,8,15,30 s ~ 1 min for Azure resume) and
  query helpers. `migrate.py` + `migrations/001_init.sql` per service, `schema_migrations`.
  `dives.current` → `current_level` (CURRENT is reserved). `external_id` unique via filtered
  index. Dates stay NVARCHAR. `health_check` table in 001. Tests on a SQL Server test DB
  (TEST_DATABASE_URL): dives 115 pass, sites 22 pass.
  Gaps: SECRET_KEY still has a default (replaced by token auth Thu); NVARCHAR limits on
  name/species/notes are not validated in services (too-long input → DB error).
- 2026-11-18: Dockerfiles (python:3.13-slim, uv 0.9.15 pinned, `uv sync --frozen --no-dev`, explicit
  COPYs, non-root `app` user), `.dockerignore`, `docker-compose.yml` (sqlserver + one-off db-init
  + sites + dives, named volume), `db/init.sql` (dives/sites DBs, dives_user/sites_user each
  only in own DB), `.env.example` (passwords from gitignored .env — decision 5b). Verified:
  stack up, seam over compose network, non-root, login isolation, restart keeps data.
  Known: dives pages link to `SITES_URL` (http://sites:8000) which the browser can't open
  under compose — fixed by the static UI on Fri. No `ui` (nginx) service until Fri.
- 2026-11-18: `/health` (`health.py`: one quick connection, UPDATE + SELECT on `health_check`,
  200/503 JSON with `VERSION`), one stdout line per request (`log_request`), werkzeug log
  silenced, startup line. Tests: dives 120, sites 27. Compose: health 200; sites stopped →
  dives health still 200; SQL Server stopped → 503 in 0.09 s.
- 2026-11-19: ADR-6 written (moved from Wed). CLAUDE.md rule 4 changed: Claude writes ADRs and AI_USAGE cols 1–5; own-words column stays the student's.
- 2026-11-19: partial failure handled. `sites_client.SitesUnavailable` (timeout, refused, 5xx, bad
  JSON; 404 still = no such site). Dive page → "Site unavailable"; forms → no dropdown + note;
  save with site → `SITES_DOWN_MESSAGE` (400); feed stops calling after the first failure.
  Cross-seam test = option (a): fake sites server (`http.server`) in `tests/test_sites_seam.py`.
  Dives 131 tests, 72% total, `sites_client.py` 97%. Verified in compose with sites stopped.
- 2026-11-19: JSON API + token login + CORS. Decisions: signed itsdangerous token (no table),
  7 days, Jinja pages kept until Fri. `itsdangerous` made an explicit dependency (already came
  with Flask). `SECRET_KEY` now required (no default). `CORS_ORIGIN` env var in both services.
  Tests: dives 146, sites 30. Verified in compose (token, 401, preflight headers).
  Coverage note: Jinja `routes.py` files pull the total down to 72%; they go on Fri.
- 2026-11-19: `docs/a2-azure-deployment-guide.pdf` added (overrides the PDF brief for Azure):
  own Azure for Students subscription, own RG, managed identity + OIDC, Storage static website,
  free-offer SQL DBs, contained users, professors get Reader. Allowed regions: spaincentral,
  belgiumcentral, austriaeast, italynorth, switzerlandnorth. Providers not registered yet.
  `sqlcmd` not installed locally (use the mssql Docker image).
- 2026-11-26: deadline is now Sun 29 Nov. State: main = A1 only, a2-split stops at 70b3d19 (19 Nov), no tag, Azure not set up. Nothing done 20-25 Nov.
- 2026-11-26: repo renamed to Declamski/be-the-fish, new clone at /Users/declanvandam/be-the-fish (README Azure subjects updated). Static UI in `ui/` + nginx `ui` service in compose (port 8080). All flows tested in headless Chrome, incl. sites stopped. Next: delete Jinja pages/routes/cookie login, ADR-8.
- 2026-11-26: Jinja pages deleted: `templates/`, `static/`, `dives/routes.py`, `feed/routes.py`,
  `sites/routes.py` (its JSON routes moved to `sites/api.py`), `formatting.py` + its tests, cookie
  login and page routes in `users.py`. `GET /` = `{"service", "version"}` JSON (no DB). Dockerfile
  COPY lines updated; both images build. Tests: dives 135 (86%), sites 31 (89%).
  Azure setup moved to the other thread ("A2 Azure Deployment Setup Guide"); this thread does not run az.
- 2026-11-26: `openapi.yaml` per service (OpenAPI 3.0.3, every route, checked against `app.url_map`)
  and `system.yaml` (passes `check-jsonschema` against `system.schema.json`). Seam call listed:
  `GET /api/sites/{site_id}` only. Dead code found: `get_site_choices` + `sites_client.search_sites`.

