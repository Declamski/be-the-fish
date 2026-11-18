import db


def insert_site(conn, name, location, description=None):
    return db.insert(
        conn,
        "INSERT INTO sites (name, location, description) OUTPUT INSERTED.id VALUES (%s, %s, %s)",
        (name, location, description),
    )


def get_site(conn, site_id):
    return db.query_one(conn, "SELECT * FROM sites WHERE id = %s", (site_id,))


def find_site(conn, name, location):
    return db.query_one(
        conn,
        "SELECT * FROM sites WHERE LOWER(name) = LOWER(%s) AND LOWER(location) = LOWER(%s)",
        (name, location),
    )


def list_sites(conn):
    return db.query_all(conn, "SELECT * FROM sites ORDER BY name, location")
