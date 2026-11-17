import os


def init_db(conn):
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path) as f:
        conn.executescript(f.read())
    conn.commit()


def insert_site(conn, name, location, description=None):
    cursor = conn.execute(
        "INSERT INTO sites (name, location, description) VALUES (?, ?, ?)",
        (name, location, description),
    )
    conn.commit()
    return cursor.lastrowid


def get_site(conn, site_id):
    return conn.execute("SELECT * FROM sites WHERE id = ?", (site_id,)).fetchone()


def find_site(conn, name, location):
    return conn.execute(
        "SELECT * FROM sites WHERE LOWER(name) = LOWER(?) AND LOWER(location) = LOWER(?)",
        (name, location),
    ).fetchone()


def list_sites(conn):
    return conn.execute("SELECT * FROM sites ORDER BY name, location").fetchall()
