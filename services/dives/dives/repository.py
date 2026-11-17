import os


def init_db(conn):
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path) as f:
        conn.executescript(f.read())
    conn.commit()


def insert_dive(conn, user_id, discipline, started_at, site_id=None, source_device=None,
                 external_id=None, max_depth_m=None, duration_s=None, water_temp_c=None,
                 visibility=None, current=None, audience="private", notes=None):
    cursor = conn.execute(
        """
        INSERT INTO dives (user_id, site_id, source_device, external_id, started_at,
                            discipline, max_depth_m, duration_s, water_temp_c,
                            visibility, current, audience, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, site_id, source_device, external_id, started_at, discipline,
         max_depth_m, duration_s, water_temp_c, visibility, current, audience, notes),
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


def update_dive_site_and_conditions(conn, dive_id, site_id, visibility, current):
    conn.execute(
        "UPDATE dives SET site_id = ?, visibility = ?, current = ? WHERE id = ?",
        (site_id, visibility, current, dive_id),
    )
    conn.commit()


def update_dive_audience(conn, dive_id, audience):
    conn.execute("UPDATE dives SET audience = ? WHERE id = ?", (audience, dive_id))
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


def list_shared_and_own_dives(conn, user_id):
    """Every dive that is not private, plus all of this user's own dives, newest first."""
    return conn.execute(
        """
        SELECT * FROM dives
        WHERE audience != 'private' OR user_id = ?
        ORDER BY started_at DESC, id DESC
        """,
        (user_id,),
    ).fetchall()


def get_dive_by_external_id(conn, external_id):
    return conn.execute(
        "SELECT * FROM dives WHERE external_id = ?", (external_id,)
    ).fetchone()
