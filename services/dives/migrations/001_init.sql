-- 001: first schema of the dives database (ported from the A1 SQLite schemas of
-- users.py, dives/ and feed/). Users, dives and feed share this one database.

-- users.py --------------------------------------------------------------------

CREATE TABLE users (
    id INT IDENTITY(1,1) PRIMARY KEY,
    email NVARCHAR(254) NOT NULL UNIQUE,
    name NVARCHAR(100) NOT NULL,
    password_hash NVARCHAR(255) NOT NULL
);

-- One row per pair of users. A request starts as 'pending' and becomes
-- 'accepted' when the other person accepts. Declining, cancelling and
-- unfriending all delete the row.
CREATE TABLE friendships (
    id INT IDENTITY(1,1) PRIMARY KEY,
    requester_id INT NOT NULL REFERENCES users(id),
    addressee_id INT NOT NULL REFERENCES users(id),
    status NVARCHAR(20) NOT NULL
);

-- dives/ ----------------------------------------------------------------------

-- site_id is a plain number: sites live in another service and database, so it
-- is checked through the sites API (dives/sites_client.py), not a FOREIGN KEY.
-- current_level, not current: CURRENT is a reserved word in SQL Server.
CREATE TABLE dives (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    site_id INT,
    source_device NVARCHAR(100),
    external_id NVARCHAR(100),
    started_at NVARCHAR(32) NOT NULL,
    discipline NVARCHAR(20) NOT NULL,
    max_depth_m FLOAT,
    duration_s INT,
    water_temp_c FLOAT,
    visibility NVARCHAR(20),
    current_level NVARCHAR(20),
    audience NVARCHAR(20) NOT NULL DEFAULT 'private',
    notes NVARCHAR(MAX)
);

-- external_id must be unique, but many manual dives have none. A plain UNIQUE
-- would allow only one NULL in SQL Server, so the rule skips NULLs.
CREATE UNIQUE INDEX ux_dives_external_id ON dives (external_id) WHERE external_id IS NOT NULL;

CREATE TABLE descents (
    id INT IDENTITY(1,1) PRIMARY KEY,
    dive_id INT NOT NULL REFERENCES dives(id),
    depth_m FLOAT NOT NULL,
    duration_s INT NOT NULL,
    started_at NVARCHAR(32)
);

CREATE TABLE catches (
    id INT IDENTITY(1,1) PRIMARY KEY,
    dive_id INT NOT NULL REFERENCES dives(id),
    species NVARCHAR(200) NOT NULL,
    weight_kg FLOAT
);

-- feed/ -----------------------------------------------------------------------

-- dive_id and user_id are plain numbers, not FOREIGN KEYs: dives and users are
-- other domains (ADR-2). The dive is checked through dives.service instead.

-- One kudos per person per dive: the PRIMARY KEY makes a second one impossible.
CREATE TABLE kudos (
    dive_id INT NOT NULL,
    user_id INT NOT NULL,
    PRIMARY KEY (dive_id, user_id)
);

CREATE TABLE comments (
    id INT IDENTITY(1,1) PRIMARY KEY,
    dive_id INT NOT NULL,
    user_id INT NOT NULL,
    body NVARCHAR(500) NOT NULL,
    created_at NVARCHAR(32) NOT NULL
);

-- GET /health -----------------------------------------------------------------

-- One row that GET /health updates, to prove the service can write to its database.
CREATE TABLE health_check (
    id INT PRIMARY KEY,
    checked_at DATETIME2 NOT NULL
);
INSERT INTO health_check (id, checked_at) VALUES (1, SYSUTCDATETIME());
