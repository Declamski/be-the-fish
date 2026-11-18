"""Shared test setup for the sites service.

Tests run against a real SQL Server test database, given by the TEST_DATABASE_URL
env var (e.g. mssql://sa:<password>@localhost:1433/sites_test). The database is
created if missing, migrated once, and emptied before every test.
"""
import os

import pymssql
import pytest

import db
from app import create_app
from sites import service

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


def create_test_database():
    """Create the test database if it does not exist yet (done from the 'master' database)."""
    args = db.parse_database_url(TEST_DATABASE_URL)
    name = args["database"]
    args["database"] = "master"
    conn = pymssql.connect(**args, autocommit=True)
    cursor = conn.cursor()
    cursor.execute("""
        DECLARE @name SYSNAME = %s;
        DECLARE @quoted NVARCHAR(300) = QUOTENAME(@name);
        IF DB_ID(@name) IS NULL EXEC('CREATE DATABASE ' + @quoted);
    """, (name,))
    conn.close()


@pytest.fixture(scope="session")
def app():
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not set: these tests need a SQL Server test database")
    create_test_database()
    # Runs the migrations and the seeding, like a real start.
    return create_app({"PORT": 8000, "DATABASE_URL": TEST_DATABASE_URL})


@pytest.fixture
def conn(app):
    """A connection to an empty test database holding only the seed sites."""
    connection = db.get_connection(TEST_DATABASE_URL)
    db.execute(connection, "DELETE FROM sites")
    service.seed_sites(connection)
    yield connection
    connection.close()
