-- 001: first schema of the sites database (ported from the A1 SQLite schema).

CREATE TABLE sites (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(200) NOT NULL,
    location NVARCHAR(200) NOT NULL,
    description NVARCHAR(MAX)
);

-- One row that GET /health updates, to prove the service can write to its database.
CREATE TABLE health_check (
    id INT PRIMARY KEY,
    checked_at DATETIME2 NOT NULL
);
INSERT INTO health_check (id, checked_at) VALUES (1, SYSUTCDATETIME());
