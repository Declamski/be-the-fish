-- dive_id and user_id are plain numbers, not FOREIGN KEYs: dives and users are
-- other domains (ADR-2). The dive is checked through dives.service instead.

-- One kudos per person per dive: the PRIMARY KEY makes a second one impossible.
CREATE TABLE IF NOT EXISTS kudos (
    dive_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    PRIMARY KEY (dive_id, user_id)
);

CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dive_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
);
