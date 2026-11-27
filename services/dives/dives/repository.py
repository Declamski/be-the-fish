import db


def insert_dive(conn, user_id, discipline, started_at, site_id=None, source_device=None,
                 external_id=None, max_depth_m=None, duration_s=None, water_temp_c=None,
                 visibility=None, current=None, audience="private", notes=None):
    return db.insert(
        conn,
        """
        INSERT INTO dives (user_id, site_id, source_device, external_id, started_at,
                            discipline, max_depth_m, duration_s, water_temp_c,
                            visibility, current_level, audience, notes)
        OUTPUT INSERTED.id
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (user_id, site_id, source_device, external_id, started_at, discipline,
         max_depth_m, duration_s, water_temp_c, visibility, current, audience, notes),
    )


def get_dive(conn, dive_id):
    return db.query_one(conn, "SELECT * FROM dives WHERE id = %s", (dive_id,))


def list_dives_for_user(conn, user_id):
    return db.query_all(
        conn, "SELECT * FROM dives WHERE user_id = %s ORDER BY started_at DESC", (user_id,)
    )


def update_dive_aggregates(conn, dive_id, max_depth_m, duration_s):
    db.execute(
        conn,
        "UPDATE dives SET max_depth_m = %s, duration_s = %s WHERE id = %s",
        (max_depth_m, duration_s, dive_id),
    )


def update_dive_site_and_conditions(conn, dive_id, site_id, visibility, current):
    db.execute(
        conn,
        "UPDATE dives SET site_id = %s, visibility = %s, current_level = %s WHERE id = %s",
        (site_id, visibility, current, dive_id),
    )


def update_dive_audience(conn, dive_id, audience):
    db.execute(conn, "UPDATE dives SET audience = %s WHERE id = %s", (audience, dive_id))


def insert_descent(conn, dive_id, depth_m, duration_s, started_at=None):
    return db.insert(
        conn,
        """
        INSERT INTO descents (dive_id, depth_m, duration_s, started_at)
        OUTPUT INSERTED.id
        VALUES (%s, %s, %s, %s)
        """,
        (dive_id, depth_m, duration_s, started_at),
    )


def list_descents(conn, dive_id):
    return db.query_all(
        conn, "SELECT * FROM descents WHERE dive_id = %s ORDER BY id", (dive_id,)
    )


def insert_catch(conn, dive_id, species, weight_kg=None):
    return db.insert(
        conn,
        "INSERT INTO catches (dive_id, species, weight_kg) OUTPUT INSERTED.id VALUES (%s, %s, %s)",
        (dive_id, species, weight_kg),
    )


def list_catches(conn, dive_id):
    return db.query_all(
        conn, "SELECT * FROM catches WHERE dive_id = %s ORDER BY id", (dive_id,)
    )


def list_shared_and_own_dives(conn, user_id):
    """Every dive that is not private, plus all of this user's own dives, newest first."""
    return db.query_all(
        conn,
        """
        SELECT * FROM dives
        WHERE audience != 'private' OR user_id = %s
        ORDER BY started_at DESC, id DESC
        """,
        (user_id,),
    )


def get_dive_by_external_id(conn, external_id):
    return db.query_one(conn, "SELECT * FROM dives WHERE external_id = %s", (external_id,))
