"""The sites JSON API, which the dives service and the UI call."""


def test_list_sites_json(app, conn):
    response = app.test_client().get("/api/sites?q=blue")
    assert response.status_code == 200
    labels = [site["label"] for site in response.get_json()]
    assert "Blue Hole - Gozo, Malta" in labels


def test_get_unknown_site_is_404(app, conn):
    response = app.test_client().get("/api/sites/999999")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Site not found"}


def test_cors_allows_only_the_ui(app, conn):
    response = app.test_client().get("/api/sites")
    assert response.headers["Access-Control-Allow-Origin"] == "http://ui.test"
