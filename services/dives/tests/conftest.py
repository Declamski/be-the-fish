"""Shared test setup for the dives service.

pytest loads this file automatically before the tests in this folder.

Tests run against a real SQL Server test database, given by the TEST_DATABASE_URL
env var (e.g. mssql://sa:<password>@localhost:1433/dives_test). The database is
created if missing, migrated once, and emptied before every test.
"""
import os

import pymssql
import pytest

import db
from app import create_app
from dives import sites_client

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

# Children before parents, so no FOREIGN KEY blocks a delete.
TABLES_TO_EMPTY = ["catches", "descents", "kudos", "comments", "dives", "friendships", "users"]


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
    # Runs the migrations, like a real start.
    return create_app({"PORT": 8000, "DATABASE_URL": TEST_DATABASE_URL, "SECRET_KEY": "test",
                       "SITES_URL": "http://sites.invalid", "SITES_TIMEOUT_S": 1})


@pytest.fixture
def conn(app):
    """A connection to the test database with every table emptied."""
    connection = db.get_connection(TEST_DATABASE_URL)
    for table in TABLES_TO_EMPTY:
        # Table names come from the fixed list above, never from input.
        db.execute(connection, "DELETE FROM " + table)
    yield connection
    connection.close()

# Stand-in for the sites service, so these tests don't need it running.
FAKE_SITES = {
    1: {"id": 1, "name": "Bloody Bay Wall", "location": "Little Cayman, Cayman Islands",
        "label": "Bloody Bay Wall - Little Cayman, Cayman Islands"},
    2: {"id": 2, "name": "Blue Hole", "location": "Dahab, Egypt",
        "label": "Blue Hole - Dahab, Egypt"},
    3: {"id": 3, "name": "Blue Hole", "location": "Gozo, Malta",
        "label": "Blue Hole - Gozo, Malta"},
}


@pytest.fixture(autouse=True)
def fake_sites(monkeypatch):
    """Replace the two HTTP calls in sites_client with lookups in FAKE_SITES."""
    def fake_get_site(site_id):
        return FAKE_SITES.get(site_id)

    def fake_search_sites(query):
        return list(FAKE_SITES.values())

    monkeypatch.setattr(sites_client, "get_site", fake_get_site)
    monkeypatch.setattr(sites_client, "search_sites", fake_search_sites)
