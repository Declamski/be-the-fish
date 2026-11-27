"""Cross-seam tests: the dives service talking to a sites service over real HTTP.

Instead of the real sites service, a small fake sites server runs inside the test
(Python's built-in http.server). It answers with the same JSON shapes as the real
GET /api/sites and GET /api/sites/<id>, and can be told to be slow or to fail, so
the real urllib code, the timeout and the "site unavailable" behaviour are tested.
"""
import http.server
import json
import threading
import time

import flask
import pytest

import users
from dives import service, sites_client

FAKE_SITE = {
    "id": 1,
    "name": "Blue Hole",
    "location": "Gozo, Malta",
    "description": "A rock pool that leads down through an arch into the open sea.",
    "label": "Blue Hole - Gozo, Malta",
}

# Port 1 on this computer: nothing listens there, so the connection is refused at once.
NOTHING_LISTENING_URL = "http://127.0.0.1:1"


class FakeSitesHandler(http.server.BaseHTTPRequestHandler):
    """Answers like the sites API. server.mode is "ok", "slow" or "error"."""

    def do_GET(self):
        if self.server.mode == "slow":
            time.sleep(1.5)
        if self.server.mode == "error":
            self.send_json(500, {"error": "Something broke"})
            return
        if self.path == "/api/sites/1":
            self.send_json(200, FAKE_SITE)
        else:
            self.send_json(404, {"error": "Site not found"})

    def send_json(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass  # keep the test output quiet


@pytest.fixture(autouse=True)
def fake_sites():
    """Turns off conftest's fake_sites (same name), so these tests use the real HTTP code."""


@pytest.fixture
def fake_sites_server():
    """Start the fake sites server on a free port in a background thread."""
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeSitesHandler)
    server.daemon_threads = True
    server.mode = "ok"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()


def point_dives_at(sites_url, timeout_s=0.5):
    """A tiny Flask app context with SITES_URL set, which is all sites_client needs."""
    app = flask.Flask(__name__)
    app.config["SITES_URL"] = sites_url
    app.config["SITES_TIMEOUT_S"] = timeout_s
    return app.app_context()


def server_url(server):
    return "http://127.0.0.1:" + str(server.server_port)


# --- sites_client against the fake server ---

def test_get_site_label_over_http(fake_sites_server):
    with point_dives_at(server_url(fake_sites_server)):
        assert sites_client.get_site_label(1) == "Blue Hole - Gozo, Malta"


def test_unknown_site_is_none_not_an_error(fake_sites_server):
    with point_dives_at(server_url(fake_sites_server)):
        assert sites_client.get_site(999) is None
        assert sites_client.site_exists(999) is False


def test_sites_error_answer_is_unavailable(fake_sites_server):
    fake_sites_server.mode = "error"
    with point_dives_at(server_url(fake_sites_server)), \
            pytest.raises(sites_client.SitesUnavailable):
        sites_client.get_site(1)


def test_slow_sites_times_out(fake_sites_server):
    fake_sites_server.mode = "slow"
    with point_dives_at(server_url(fake_sites_server), timeout_s=0.5):
        started = time.perf_counter()
        with pytest.raises(sites_client.SitesUnavailable):
            sites_client.get_site(1)
        # Gave up after the 0.5 s timeout, not after the 1.5 s the server takes.
        assert time.perf_counter() - started < 1.2


def test_sites_down_is_unavailable():
    with point_dives_at(NOTHING_LISTENING_URL), \
            pytest.raises(sites_client.SitesUnavailable):
        sites_client.get_site(1)


# --- what the dives service does when sites is down (needs the test database) ---

@pytest.fixture
def sites_down(app, monkeypatch):
    """Point the real test app at an address where nothing answers."""
    monkeypatch.setitem(app.config, "SITES_URL", NOTHING_LISTENING_URL)
    with app.app_context():
        yield


def test_dive_page_still_works_when_sites_down(conn, sites_down):
    # Saved directly so the site check is skipped, as if sites went down later.
    from dives import repository
    dive_id = repository.insert_dive(conn, user_id=1, discipline="scuba",
                                     started_at="2026-01-01T10:00:00", site_id=1)
    detail = service.get_dive_detail(conn, dive_id, viewer_id=1)
    assert detail["dive"]["id"] == dive_id
    assert detail["site_label"] is None
    assert detail["site_unavailable"] is True


def test_dive_without_site_can_be_saved_when_sites_down(conn, sites_down):
    dive_id = service.create_scuba_dive(
        conn, user_id=1, started_at="2026-01-01T10:00:00", max_depth_m=10, duration_s=100,
    )
    assert dive_id is not None


def test_dive_with_site_gives_clear_error_when_sites_down(conn, sites_down):
    with pytest.raises(ValueError) as error:
        service.create_scuba_dive(
            conn, user_id=1, started_at="2026-01-01T10:00:00", max_depth_m=10,
            duration_s=100, site_id=1,
        )
    assert str(error.value) == service.SITES_DOWN_MESSAGE


def test_feed_still_works_when_sites_down(conn, sites_down):
    from dives import repository
    owner = users.create_user(conn, "owner@example.com", "Owner", "password123")
    for day in range(1, 4):
        repository.insert_dive(conn, user_id=owner, discipline="scuba",
                               started_at="2026-01-0" + str(day) + "T10:00:00",
                               site_id=1, audience="public")
    page = service.list_feed_dives(conn, owner, offset=0, limit=20)
    assert len(page["dives"]) == 3
    for dive in page["dives"]:
        assert dive["site_label"] is None
