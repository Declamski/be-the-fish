# Watch data, import & schema

> **A2 note:** the schema below is the Assignment 1 SQLite design. In A2 the tables move to
> SQL Server, one database per service (dives/feed/users → dives DB, sites → sites DB), and the
> real schema is defined by each service's `migrations/*.sql`. The privacy rules still apply.

## Sources
| Watch | How data gets out | Status |
|---|---|---|
| Garmin Descent G2 | Garmin Connect website → activity → gear icon → "Export Original" → zipped `.FIT` per dive | Requested from owner |
| Suunto D4i | No Bluetooth. Needs Suunto's proprietary USB cable + desktop software (Subsurface or Suunto DM5) | Unknown if cable exists |

## Pipeline (manual prep, NOT a runtime dependency)
1. Student installs **Subsurface** (free desktop dive log) on their own machine.
2. Garmin: place `.FIT` files in a folder `<somepath>/Garmin/Activity/`, run a Subsurface download with connection = `<somepath>`.
   Suunto (if cable): Subsurface → Import from dive computer → Suunto → D4i.
3. Export from Subsurface as **CSV** (summary per dive) — or UDDF (XML) if depth profiles are wanted.
4. Put exports in `imports/` (gitignored). The app's `dives/importer.py` parses that ONE format with stdlib `csv` (or `xml.etree`).
   No FIT-parsing library in the app.

Fallbacks: if Suunto data is unobtainable → Garmin only, and/or manual entry via the form (catches are always manual — no watch records them).

**Do not finalise importer column mapping until a real export has been inspected.** Build manual entry first.

## Importer requirements (core logic → must be tested)
- Map export columns → dive fields; convert units to SI (m, s, °C).
- Map watch mode → `discipline` (scuba / freedive; spearfishing = Garmin "apnea hunt" or set manually).
- De-duplicate: `external_id` (e.g. device + start time) is UNIQUE; re-importing the same file must not create duplicates.
- Reject/skip rows with missing essential fields, and report how many were skipped.

## Privacy (repo is PUBLIC)
- Real exports → `imports/`; DB → `data/`. Both gitignored. Never commit them.
- Test fixtures in `tests/fixtures/`: 3–5 dives, hand-sanitised — no real GPS (remove or replace with a well-known public dive site), no real names, pseudonymous users.

## Draft schema (NOT final — ADR-3 decides the open points)
```
users(id, email UNIQUE, name, password_hash)             -- shared, session-based login (email = login, name = display name)
friendships(id, requester_id, addressee_id, status)      -- in users.py; status pending/accepted; mutual
-- dives/ (ADR-3: one row = one event. scuba = single dive, direct max_depth_m/duration_s.
--          freedive/spearfishing = one session, max_depth_m/duration_s derived from descents)
dives(id, user_id, site_id NULL, source_device, external_id UNIQUE,
      started_at, discipline, max_depth_m, duration_s, water_temp_c,
      visibility NULL, current NULL, audience DEFAULT 'private', notes)
      -- audience: private / friends / public (who can see the dive)
descents(id, dive_id FK, depth_m, duration_s, started_at)   -- freedive/spearfishing sessions only
catches(id, dive_id, species, weight_kg)                    -- spearfishing only, tied to the session
-- sites/
sites(id, name, location, description)    -- read-only catalogue; admin adds sites by editing
                                          -- sites.service.SEED_SITES (added at startup if missing).
                                          -- Same name allowed; same name + same location = same site.
-- visibility (poor/moderate/good/excellent) and current (none/light/moderate/strong) are
-- optional columns on dives, not on sites: they describe the dive, not the site.
-- feed/ (was social; dive_id/user_id are plain ints, checked via dives.service)
comments(id, dive_id, user_id, body, created_at)
kudos(dive_id, user_id, PRIMARY KEY (dive_id, user_id))
```
Optional polish only: `dive_samples(dive_id, t_s, depth_m, temp_c)` for depth profiles.

## Business logic ideas worth testing
- Dives: validation (depth > 0, duration > 0, discipline valid, catches only on spearfishing dives), personal bests per discipline, totals/averages over a date range.
- Sites: create_site (name + location required, duplicate = same name + location ignoring case/spaces), seed_sites idempotent, search_sites by name or location.
- Dives <-> sites: site must exist (via `sites.service.site_exists`), visibility/current must be valid levels.
- Friends (users.py): no self-request, no duplicates, only the receiver accepts, remove = decline/cancel/unfriend.
- Dives audience: can_view_dive (owner / public / friends via users.are_friends / private).
- Feed: one kudos per person, none on own dive, can take back; comment 1-500 chars, only author deletes; feed = visible dives (own included), newest first, pages of 20.
