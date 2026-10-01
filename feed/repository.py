import os


def init_db(conn):
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path) as f:
        conn.executescript(f.read())
    conn.commit()


# --- kudos ---

def insert_kudos(conn, dive_id, user_id):
    conn.execute("INSERT INTO kudos (dive_id, user_id) VALUES (?, ?)", (dive_id, user_id))
    conn.commit()


def delete_kudos(conn, dive_id, user_id):
    conn.execute("DELETE FROM kudos WHERE dive_id = ? AND user_id = ?", (dive_id, user_id))
    conn.commit()


def has_kudos(conn, dive_id, user_id):
    row = conn.execute(
        "SELECT 1 FROM kudos WHERE dive_id = ? AND user_id = ?", (dive_id, user_id)
    ).fetchone()
    return row is not None


def count_kudos(conn, dive_id):
    row = conn.execute("SELECT COUNT(*) AS total FROM kudos WHERE dive_id = ?", (dive_id,)).fetchone()
    return row["total"]


# --- comments ---

def insert_comment(conn, dive_id, user_id, body, created_at):
    cursor = conn.execute(
        "INSERT INTO comments (dive_id, user_id, body, created_at) VALUES (?, ?, ?, ?)",
        (dive_id, user_id, body, created_at),
    )
    conn.commit()
    return cursor.lastrowid


def get_comment(conn, comment_id):
    return conn.execute("SELECT * FROM comments WHERE id = ?", (comment_id,)).fetchone()


def delete_comment(conn, comment_id):
    conn.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
    conn.commit()


def list_comments(conn, dive_id):
    return conn.execute(
        "SELECT * FROM comments WHERE dive_id = ? ORDER BY created_at, id", (dive_id,)
    ).fetchall()


def count_comments(conn, dive_id):
    row = conn.execute(
        "SELECT COUNT(*) AS total FROM comments WHERE dive_id = ?", (dive_id,)
    ).fetchone()
    return row["total"]
