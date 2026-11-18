import db
import migrate


def test_migration_files_are_sorted():
    files = migrate.list_migration_files()
    assert files[0] == "001_init.sql"
    assert files == sorted(files)


def test_startup_recorded_every_migration(conn):
    # The app fixture already started the service once, which applied the migrations.
    assert migrate.list_applied_migrations(conn) == migrate.list_migration_files()


def test_second_run_applies_nothing(conn):
    assert migrate.apply_migrations(conn) == []


def test_health_check_row_exists(conn):
    row = db.query_one(conn, "SELECT id FROM health_check WHERE id = 1")
    assert row is not None
