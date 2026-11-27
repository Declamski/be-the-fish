# Architecture Decision Records

## 1. Framework choice
* **Date:** 2026-09-27
* **Status:** Decided
* **Context:** Framework choice is the core of the code that is to be used. All though most code is to be written with AI it is very important that I use langagues that I am familiar with for both checking AI written code before accepting it and debugging it
* **Decision:** The main programming language of the code will be done in python as I am not knowledgeable in any others to make them acceptable choices. For the backend I will be using Flask, HTML/CSS for frontend and jinja for passing data through.
* **Alternatives considered:** Django - I've worked with it a bit before but it's much heavier than required. FastAPI - this was my biggest this-or-that, I ended up going with Flask because of the built in support with jinja. Other languages such as C for backend or JavaScript for front end - I am simply not comfortable enough in either to use them over a python-based framework
* **Consequences:** Jinja uses server-side rendering meaning that it won't get live updates with data. This is fine because of the app but it could be a negative in the future for a social module in the app such as seeing new posts from others, follow requests and messages. 

---

## 2. Domain modularisation
* **Date:** 2026-09-28
* **Status:** Decided
* **Context:** The project requires at least 2 distict backend domains that must be seperable for the future Assignment 2 which wants the distinct domains to be their own microservices.
* **Decision:** Each domain has it's own tables, a domain doesn't access other domains through foreign keys. For any cross domain information access (gets) public functions will be used.
* **Alternatives considered:** Foreign keys for JOIN access across all tables freely was a thought but, although it's simpler and faster, it would make for a lot of complication in Assignment 2. 
* **Consequences:** Without JOINS complications can arrise if you ever need data that spans more than one domain, eg. listing dives at a certain site. This can cause complications in both ensuring that all access is done through functions to ensure domains are properly seperated as well as keeping track of access functions used

---

## 3. SQLite data model
* **Date:** 2026-09-28
* **Status:** Decided
* **Context:** There are three classes of dives that will be features of the app. For this decision I will be looking at how freedives and spearfishing are logged in the database. Scuba diving works differently as it is one sustained period underwater while the others involve multiple descents throughout a session.
* **Decision:** I have decided that one session will be one row in the database and the multiple dives throughout a session will be logged. With that there will be a child table with the per-descent details joined with the dive_id as a foreign key.
* **Alternatives considered:** The first consideration that I had to make was having each descent count as it's own dive, I decided this would only complicate the logic of a dive session making it more difficult to track a full session together. After deciding on one session = one row, I had to decide between a child table or keeping all the innformation in the initial dive table. Keeping it in the initial table would limit the amount of information I could show, allowing me to show max depth, longest dive and dive count but crucially not letting me shoe metrics for each individual descent.
* **Consequences:** The main consequences is added complexity. Having the extra child table means that I will need additional functions, validations and testing due to how ADR2 defines the database as a whole. It also requires more logic for imported datasets and can be a hassle if a user is filling out data manually for whatever reason.

---

## 4. Testing approach
* **Date:** 2026-10-04
* **Status:** Decided
* **Context:** We are required to test ≥70% of our core logic. Where and how tests run has to be decided. 
* **Decision:** The thing to be tested was the core business logic over the domains. I decided to test mainly the /service.py files for each domain and leave much of routes.py untested, doing this is testing the logic for each section but not the translation from services to browser. Tests are run on their own fresh databases in a side folder, this allows for them to be tested properly without interfering with the real data.
* **Alternatives considered:** Running the tests on the actual database and deleting additions after: It just adds too much complication and is unnecessary. Also testing routes: Although it would have covered more they aren't fully required and would sometimes just be retesting service files.
* **Consequences:** Pages aren't automatically checked, those have to be done through human testing to find any bugs throughout the app. Coverage is 74% which is barely above the limit, testing more could have been a generally smarter thing to do.

---

## 5. What is deliberately not built
* **Date:** 2026-10-04
* **Status:** Decided
* **Context:** A very powerful feature to have in fitness/activity apps is connection to hardware devices such as watches. In diving, freediving and spearfishing you often use a dive computer (essentially a dive watch) to give you statistics on your dives as well as keep you safe.
* **Decision:** Although I originally wanted to connect devices directly to upload dive logs I ended up going down a different path. I allowed for 2 means of data imports, manual entry and importing csv files. This allows for logs to be entered without going directly through an external device.
* **Alternatives considered:** Allowing direct communication with a dive computer. I could have spent time trying to implement this as a feature but I realised that it was out of my current scope as I'm without hardware to test the direct access. I could have looked into making a mock connection a different way but I decided it would be eating time that I could use on other things.
* **Consequences:** Not having this feature is a big hit because it adds a big user experience addition for users. It is definitely something I would like to implement as I move forward with the project and have access to what's required to make it happen.

---

## 6. The split
* **Date:** 2026-11-19
* **Status:** Decided
* **Context:** Assignment 2 requires the monolith to be split into separate services along the seam from ADR-2, each in its own container with its own database, with a maximum of two service containers. In Assignment 1 I had three domains (dives, sites and feed), so not every domain could become its own service.
* **Decision:** I split the app into two services: `services/dives`, which holds dives, feed and users/login, and `services/sites`, which holds the dive site catalogue. The seam between dives and sites from ADR-2 held, and the only thing that crosses it is dives calling sites over HTTP (`site_exists`, `search_sites` and `get_site_label` in `dives/sites_client.py`), found through `SITES_URL` and with a timeout on every call. Feed did not get its own service because of the two container maximum, so it was put inside dives, but it is still its own package and never touches the dives repository.
* **Alternatives considered:** Putting feed and users in the second service and moving sites into dives: feed needs dives for almost everything it does (every feed page, kudos and comment checks the dive), so this would have meant many calls across the seam, while dives only needs sites when a site is picked or shown. Making users/login its own service: it would need a third container, which isn't allowed, and every request would have to call it. Having the UI call both services and join the data in the browser: at least one flow has to cross on the server, and checking that a site exists has to happen on the server anyway, otherwise someone could save a dive with a made up site.
* **Consequences:** Dive pages now depend on a network call to sites, so if sites is slow or down it affects dives, which is why every call has a timeout. `site_id` is now just a number with no foreign key, so it is only checked when a dive is saved, and some files (`db.py`, `migrate.py`, `config.py`) are copied into both services. In return each service can be deployed and fail on its own, and because feed kept its own package it could be split out into a third service later without restructuring it.

---

## 7. Data and migrations
* **Date:** 2026-11-19
* **Status:** Decided
* **Context:** In Assignment 1 all tables were in one SQLite file and were created with `CREATE TABLE IF NOT EXISTS` on start. Assignment 2 needs one SQL Server database per service and a schema that can change while the database already holds data, so tables can't just be recreated anymore.
* **Decision:** Each service has its own numbered SQL files in `migrations/` that `migrate.py` runs in order at startup, each one exactly once, and records in a `schema_migrations` table. The A1 tables were split by owner: users, friendships, dives, descents, catches, kudos and comments went into `dives`' `001_init.sql`, and sites went into `sites`' `001_init.sql`. No rows had to be moved because the A1 app was never deployed, so both Azure databases start empty and get their data through the app. If a migration goes wrong in production I fix it forward with a new migration, and only if data was actually lost or damaged I use Azure's point-in-time restore to go back to before the deploy.
* **Alternatives considered:** Alembic: it would track migrations for me, but it brings in SQLAlchemy and a tool I would have to learn and explain, when my runner is one small file. Down migrations for every change: the brief allows forward only and writing an undo for each file doubles the work for something I would rarely use. Always restoring from backup: it throws away everything written after the backup, so it's only worth it when data is already damaged.
* **Consequences:** `dives.site_id` can't be a foreign key anymore because sites live in another database, so the site is only checked through the sites API when a dive is saved; this is safe because sites are read-only and never deleted. Feed's kudos and comments still point at dives with plain ids like in A1. A migration that fails stops the service from starting instead of running half-applied, and because applied files are never edited, every database can always be rebuilt by running the same files in order.

---

## 8. Serverless hosting on Azure
* **Date:** 2026-11-27
* **Status:** Decided
* **Context:** The system runs on my own Azure for Students subscription and should cost nothing while nobody uses it, so nothing can be always on.
* **Decision:** Both services run as Container Apps (Consumption) with min 0 and max 1 replicas, each has its own serverless Azure SQL database (0.5 to 1 vCore, max 2 GB, pauses after 60 minutes idle), the UI is a Storage static website and the images are on GHCR. I wanted the free SQL offer, but on my subscription italynorth and switzerlandnorth refuse new SQL servers and belgiumcentral and austriaeast don't support free databases, so the SQL server and Container Apps are in austriaeast on the brief's serverless settings and only the UI storage is in italynorth. I set it up once with Azure CLI commands written in the README, and after that only the CD workflow changes anything. To handle a cold start, `db.py` retries the connection for about a minute while a paused database resumes, and the UI tells the user to try again in a moment.
* **Alternatives considered:** Bicep or Terraform: another language to learn for a setup that only runs once. One replica always on and no database pause: no waiting, but it costs money even with no users. Retrying automatically in the UI: nicer, but more code when a clear message does the job.
* **Consequences:** The first request after an idle hour can take up to a minute. Migrations run at startup, which is only safe with one replica, so at 100x the traffic I would raise max replicas and move the migrations into a deploy step so they run once. The databases are paid for only while they are awake, so at 100x they would rarely pause and cost more, and I would raise their max vCores.

---

## 9. Pipeline and testing
<!-- Brief: what CI gates on and why, how the cross-seam test works, what is deliberately not tested. -->
* **Date:** 
* **Status:** Decided
* **Context:** 
* **Decision:** 
* **Alternatives considered:** 
* **Consequences:** 

---

## 10. What is deliberately not built
<!-- Brief: one thing deliberately not built (from section 1c or elsewhere) and the conditions under which it would be worth building. -->
* **Date:** 
* **Status:** Decided
* **Context:** 
* **Decision:** 
* **Alternatives considered:** 
* **Consequences:** 
