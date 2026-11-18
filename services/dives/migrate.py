"""Applies the numbered SQL files in migrations/ in order, each exactly once.

Every applied file is recorded in the schema_migrations table, so a second start
applies nothing. Applied files are never edited: a change goes in a new file.
"""
import os

import db

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")


def list_migration_files():
    """Every .sql file in migrations/, sorted by name, so 001 runs before 002."""
    filenames = []
    for filename in os.listdir(MIGRATIONS_DIR):
        if filename.endswith(".sql"):
            filenames.append(filename)
    filenames.sort()
    return filenames


def create_migrations_table(conn):
    db.execute(conn, """
        IF OBJECT_ID('schema_migrations') IS NULL
            CREATE TABLE schema_migrations (
                filename NVARCHAR(255) PRIMARY KEY,
                applied_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
            )
    """)


def list_applied_migrations(conn):
    applied = []
    for row in db.query_all(conn, "SELECT filename FROM schema_migrations"):
        applied.append(row["filename"])
    return applied


def apply_migrations(conn):
    """Run every migration file that is not in schema_migrations yet. Returns the names applied."""
    create_migrations_table(conn)
    applied = list_applied_migrations(conn)

    newly_applied = []
    for filename in list_migration_files():
        if filename in applied:
            continue

        with open(os.path.join(MIGRATIONS_DIR, filename)) as f:
            sql = f.read()

        # The migration and its schema_migrations row are saved together:
        # if the SQL fails, neither is saved and the service does not start.
        cursor = conn.cursor()
        try:
            cursor.execute(sql)
            cursor.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (filename,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

        print("Applied migration", filename, flush=True)
        newly_applied.append(filename)

    if not newly_applied:
        print("No new migrations to apply", flush=True)
    return newly_applied
