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
* **Date:** 
* **Status:** Decided
* **Context:**
* **Decision:**
* **Alternatives considered:**
* **Consequences:**

---

## 5. What is deliberately not built
* **Date:** 
* **Status:** Decided
* **Context:**
* **Decision:**
* **Alternatives considered:**
* **Consequences:**