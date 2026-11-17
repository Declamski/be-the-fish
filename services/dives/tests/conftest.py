"""Shared test setup for the dives service.

pytest loads this file automatically before the tests in this folder.
"""
import pytest

from dives import sites_client

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
