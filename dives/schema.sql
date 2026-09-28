CREATE TABLE IF NOT EXISTS dives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    site_id INTEGER,
    source_device TEXT,
    external_id TEXT UNIQUE,
    started_at TEXT NOT NULL,
    discipline TEXT NOT NULL,
    max_depth_m REAL,
    duration_s INTEGER,
    water_temp_c REAL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS descents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dive_id INTEGER NOT NULL,
    depth_m REAL NOT NULL,
    duration_s INTEGER NOT NULL,
    started_at TEXT,
    FOREIGN KEY (dive_id) REFERENCES dives(id)
);

CREATE TABLE IF NOT EXISTS catches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dive_id INTEGER NOT NULL,
    species TEXT NOT NULL,
    weight_kg REAL,
    FOREIGN KEY (dive_id) REFERENCES dives(id)
);
