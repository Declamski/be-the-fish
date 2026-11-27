import db

# --- kudos ---

def insert_kudos(conn, dive_id, user_id):
    db.execute(conn, "INSERT INTO kudos (dive_id, user_id) VALUES (%s, %s)", (dive_id, user_id))


def delete_kudos(conn, dive_id, user_id):
    db.execute(conn, "DELETE FROM kudos WHERE dive_id = %s AND user_id = %s", (dive_id, user_id))


def has_kudos(conn, dive_id, user_id):
    row = db.query_one(
        conn, "SELECT 1 AS found FROM kudos WHERE dive_id = %s AND user_id = %s", (dive_id, user_id)
    )
    return row is not None


def count_kudos(conn, dive_id):
    row = db.query_one(conn, "SELECT COUNT(*) AS total FROM kudos WHERE dive_id = %s", (dive_id,))
    return row["total"]


# --- comments ---

def insert_comment(conn, dive_id, user_id, body, created_at):
    return db.insert(
        conn,
        """
        INSERT INTO comments (dive_id, user_id, body, created_at)
        OUTPUT INSERTED.id
        VALUES (%s, %s, %s, %s)
        """,
        (dive_id, user_id, body, created_at),
    )


def get_comment(conn, comment_id):
    return db.query_one(conn, "SELECT * FROM comments WHERE id = %s", (comment_id,))


def delete_comment(conn, comment_id):
    db.execute(conn, "DELETE FROM comments WHERE id = %s", (comment_id,))


def list_comments(conn, dive_id):
    return db.query_all(
        conn, "SELECT * FROM comments WHERE dive_id = %s ORDER BY created_at, id", (dive_id,)
    )


def count_comments(conn, dive_id):
    row = db.query_one(
        conn, "SELECT COUNT(*) AS total FROM comments WHERE dive_id = %s", (dive_id,)
    )
    return row["total"]
