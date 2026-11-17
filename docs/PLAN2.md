# Assignment 2 — plan & status

Deadline **Sun 2026-11-22 23:59 (Madrid)**. Work on branch `a2-split`, merge to `main` via PRs.

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
- Today's commit 2: how dives calls sites before the HTTP client exists (temporary stub vs
  early HTTP client).
- Token format for auth (signed token via Flask's `itsdangerous` vs random token stored in DB).

## Still needed from outside
- IE username → Azure prefix (dots → hyphens).
- Class resource group (`rg-sdd-3a` / `rg-sdd-3b`).
- `system.schema.json` from the professor (copy to repo root).
- Class service principal credentials (GitHub secrets only).
- GitHub repo is `Declamski/sdd-assignment1.py` (same repo as A1, required).

## Status log
- 2026-11-17: read the brief; docs set up (CLAUDE.md for A2, ASSIGNMENT2.md, PLAN2.md, A1 docs
  moved to `docs/a1/`, .gitignore updated).
