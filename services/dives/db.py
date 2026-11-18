import time
import urllib.parse

import pymssql

# Seconds to wait between connection attempts. A paused Azure SQL database refuses
# connections (error 40613) for up to about a minute while it resumes, so the waits
# grow and add up to about a minute before we give up.
RETRY_WAITS_S = [1, 2, 4, 8, 15, 30]


def parse_database_url(database_url):
    """Turn mssql://user:password@host:port/database into pymssql.connect() arguments."""
    parts = urllib.parse.urlparse(database_url)
    return {
        "server": parts.hostname,
        "port": parts.port or 1433,
        "user": urllib.parse.unquote(parts.username),
        "password": urllib.parse.unquote(parts.password),
        "database": parts.path.lstrip("/"),
    }


def get_connection(database_url):
    """Open a connection, retrying with growing waits if the database is not ready yet."""
    args = parse_database_url(database_url)
    for wait_s in RETRY_WAITS_S:
        try:
            return pymssql.connect(**args)
        except pymssql.OperationalError as e:
            print("Database not ready, retrying in", wait_s, "s:", e, flush=True)
            time.sleep(wait_s)
    # Last try. If this one fails too, the error goes up to the caller.
    return pymssql.connect(**args)


def connect_once(database_url):
    """One quick connection attempt, no retries. Used by GET /health, which must
    answer straight away with 503 instead of waiting a minute for the database."""
    args = parse_database_url(database_url)
    return pymssql.connect(**args, login_timeout=5)


# --- Small helpers so the repositories don't repeat cursor code ---

def query_one(conn, sql, params=None):
    """Run a SELECT and return the first row as a dict, or None if there is no row."""
    cursor = conn.cursor(as_dict=True)
    cursor.execute(sql, params)
    row = cursor.fetchone()
    cursor.close()
    return row


def query_all(conn, sql, params=None):
    """Run a SELECT and return every row as a list of dicts."""
    cursor = conn.cursor(as_dict=True)
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    cursor.close()
    return rows


def execute(conn, sql, params=None):
    """Run an UPDATE/DELETE/INSERT that returns nothing, and save it."""
    cursor = conn.cursor()
    cursor.execute(sql, params)
    conn.commit()
    cursor.close()


def insert(conn, sql, params=None):
    """Run an INSERT containing OUTPUT INSERTED.id, save it, and return the new row's id."""
    cursor = conn.cursor()
    cursor.execute(sql, params)
    new_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    return new_id
