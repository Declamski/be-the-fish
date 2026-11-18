import health
from conftest import TEST_DATABASE_URL


def test_check_database_ok(conn):
    assert health.check_database(TEST_DATABASE_URL) is True


def test_check_database_unreachable():
    # Nothing listens on port 1, so the connection fails straight away.
    assert health.check_database("mssql://nobody:wrong@127.0.0.1:1/nothing") is False


def test_health_returns_200_with_version(app):
    response = app.test_client().get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "db": "ok", "version": "test"}


def test_health_returns_503_when_database_fails(app, monkeypatch):
    monkeypatch.setattr(health, "check_database", lambda database_url: False)
    response = app.test_client().get("/health")
    assert response.status_code == 503
    assert response.get_json()["db"] == "error"


def test_every_request_is_logged(app, capsys):
    app.test_client().get("/health")
    log = capsys.readouterr().out
    # e.g. "GET /health 200 12.3ms"
    assert "GET /health 200 " in log
    assert log.strip().endswith("ms")
