import pytest

from app import create_app
from db import get_connection
from sites import repository, service


@pytest.fixture
def conn(tmp_path):
    data_dir = str(tmp_path)
    create_app({"PORT": 8000, "DATA_DIR": data_dir, "SECRET_KEY": "test"})
    connection = get_connection(data_dir)
    yield connection
    connection.close()


# --- create_site ---

def test_create_site_valid(conn):
    site_id = service.create_site(conn, name="Test Reef", location="Testland")
    assert service.get_site_label(conn, site_id) == "Test Reef - Testland"


def test_create_site_cleans_extra_spaces(conn):
    site_id = service.create_site(conn, name="  Test   Reef ", location=" Testland  ")
    assert service.get_site_label(conn, site_id) == "Test Reef - Testland"


def test_create_site_rejects_empty_name(conn):
    with pytest.raises(ValueError):
        service.create_site(conn, name="   ", location="Testland")


def test_create_site_rejects_empty_location(conn):
    with pytest.raises(ValueError):
        service.create_site(conn, name="Test Reef", location="")


def test_create_site_rejects_same_name_and_location(conn):
    service.create_site(conn, name="Test Reef", location="Testland")
    with pytest.raises(ValueError):
        service.create_site(conn, name="TEST reef", location="  testland ")


def test_create_site_allows_same_name_in_other_location(conn):
    first_id = service.create_site(conn, name="Test Reef", location="Testland")
    second_id = service.create_site(conn, name="Test Reef", location="Otherland")
    assert first_id != second_id


# --- seed_sites ---

def test_seed_sites_runs_at_startup(conn):
    assert len(repository.list_sites(conn)) == len(service.SEED_SITES)


def test_seed_sites_does_not_duplicate_when_run_again(conn):
    added = service.seed_sites(conn)
    assert added == 0
    assert len(repository.list_sites(conn)) == len(service.SEED_SITES)


def test_seed_includes_cayman_islands(conn):
    matches = service.search_sites(conn, "cayman islands")
    assert len(matches) >= 1


# --- search_sites ---

def test_search_sites_empty_query_returns_all(conn):
    assert len(service.search_sites(conn, "")) == len(service.SEED_SITES)
    assert len(service.search_sites(conn, None)) == len(service.SEED_SITES)


def test_search_sites_matches_name_ignoring_case(conn):
    matches = service.search_sites(conn, "BLUE HOLE")
    locations = [site["location"] for site in matches]
    assert "Dahab, Egypt" in locations
    assert "Gozo, Malta" in locations


def test_search_sites_matches_location(conn):
    matches = service.search_sites(conn, "egypt")
    names = [site["name"] for site in matches]
    assert names == ["Blue Hole", "SS Thistlegorm"]


def test_search_sites_no_match(conn):
    assert service.search_sites(conn, "atlantis") == []


# --- public functions for other domains ---

def test_site_exists(conn):
    site_id = service.create_site(conn, name="Test Reef", location="Testland")
    assert service.site_exists(conn, site_id)
    assert not service.site_exists(conn, 9999)


def test_get_site_label_unknown_site(conn):
    assert service.get_site_label(conn, 9999) is None


# --- get_site ---

def test_get_site(conn):
    site_id = service.create_site(conn, name="Test Reef", location="Testland",
                                  description="A reef for tests")
    site = service.get_site(conn, site_id)
    assert site["description"] == "A reef for tests"


def test_get_site_unknown_site(conn):
    with pytest.raises(ValueError):
        service.get_site(conn, 9999)
