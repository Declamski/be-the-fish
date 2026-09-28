import os


def init_db(conn):
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path) as f:
        conn.executescript(f.read())
    conn.commit()


def insert_dive(conn, user_id, discipline, started_at, site_id=None, source_device=None,
                 external_id=None, max_depth_m=None, duration_s=None, water_temp_c=None,
                 notes=None):
    cursor = conn.execute(
        """
        INSERT INTO dives (user_id, site_id, source_device, external_id, started_at,
                            discipline, max_depth_m, duration_s, water_temp_c, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, site_id, source_device, external_id, started_at, discipline,
         max_depth_m, duration_s, water_temp_c, notes),
    )
    conn.commit()
    return cursor.lastrowid


def get_dive(conn, dive_id):
    return conn.execute("SELECT * FROM dives WHERE id = ?", (dive_id,)).fetchone()


def list_dives_for_user(conn, user_id):
    return conn.execute(
        "SELECT * FROM dives WHERE user_id = ? ORDER BY started_at DESC", (user_id,)
    ).fetchall()


def update_dive_aggregates(conn, dive_id, max_depth_m, duration_s):
    conn.execute(
        "UPDATE dives SET max_depth_m = ?, duration_s = ? WHERE id = ?",
        (max_depth_m, duration_s, dive_id),
    )
    conn.commit()


def insert_descent(conn, dive_id, depth_m, duration_s, started_at=None):
    cursor = conn.execute(
        "INSERT INTO descents (dive_id, depth_m, duration_s, started_at) VALUES (?, ?, ?, ?)",
        (dive_id, depth_m, duration_s, started_at),
    )
    conn.commit()
    return cursor.lastrowid


def list_descents(conn, dive_id):
    return conn.execute(
        "SELECT * FROM descents WHERE dive_id = ? ORDER BY id", (dive_id,)
    ).fetchall()


def insert_catch(conn, dive_id, species, weight_kg=None):
    cursor = conn.execute(
        "INSERT INTO catches (dive_id, species, weight_kg) VALUES (?, ?, ?)",
        (dive_id, species, weight_kg),
    )
    conn.commit()
    return cursor.lastrowid


def list_catches(conn, dive_id):
    return conn.execute(
        "SELECT * FROM catches WHERE dive_id = ? ORDER BY id", (dive_id,)
    ).fetchall()
