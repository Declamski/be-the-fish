"""The JSON API used by the static UI: login tokens, a few dive/feed calls, CORS.

These go through Flask's test client, so they test the routes as the browser uses
them. The business rules themselves are tested in the service tests.
"""
import users


def sign_up(client, email="diver@example.com", name="Diver"):
    response = client.post("/api/signup", json={"email": email, "name": name,
                                                 "password": "password123"})
    return response.get_json()["token"]


def auth(token):
    return {"Authorization": "Bearer " + token}


# --- tokens ---

def test_token_round_trip(app):
    with app.app_context():
        token = users.make_token(42)
        assert users.read_token(token) == 42


def test_changed_token_is_rejected(app):
    with app.app_context():
        token = users.make_token(42)
        assert users.read_token(token + "x") is None
        assert users.read_token("not-a-token") is None


def test_expired_token_is_rejected(app, monkeypatch):
    with app.app_context():
        token = users.make_token(42)
        monkeypatch.setattr(users, "TOKEN_MAX_AGE_S", -1)
        assert users.read_token(token) is None


# --- signup / login / me ---

def test_signup_then_me(app, conn):
    client = app.test_client()
    token = sign_up(client)
    response = client.get("/api/me", headers=auth(token))
    assert response.status_code == 200
    assert response.get_json()["email"] == "diver@example.com"


def test_login_gives_a_working_token(app, conn):
    client = app.test_client()
    sign_up(client)
    response = client.post("/api/login", json={"email": "diver@example.com",
                                                "password": "password123"})
    assert response.status_code == 200
    token = response.get_json()["token"]
    assert client.get("/api/me", headers=auth(token)).status_code == 200


def test_login_with_wrong_password_is_401(app, conn):
    client = app.test_client()
    sign_up(client)
    response = client.post("/api/login", json={"email": "diver@example.com",
                                                "password": "wrong-password"})
    assert response.status_code == 401


def test_api_without_token_is_401(app, conn):
    client = app.test_client()
    assert client.get("/api/dives").status_code == 401
    assert client.get("/api/dives", headers=auth("not-a-token")).status_code == 401


def test_signup_error_is_400_json(app, conn):
    response = app.test_client().post("/api/signup", json={"email": "", "name": "x",
                                                            "password": "password123"})
    assert response.status_code == 400
    assert "error" in response.get_json()


# --- dives ---

def test_create_and_read_scuba_dive(app, conn):
    client = app.test_client()
    token = sign_up(client)
    response = client.post("/api/dives", headers=auth(token), json={
        "discipline": "scuba", "started_at": "2026-11-01T10:00", "max_depth_m": 18.5,
        "duration_s": 2400, "site_id": 1, "current": "light",
    })
    assert response.status_code == 201
    dive_id = response.get_json()["id"]

    detail = client.get("/api/dives/" + str(dive_id), headers=auth(token)).get_json()
    assert detail["dive"]["max_depth_m"] == 18.5
    assert detail["dive"]["current_level"] == "light"
    assert detail["site_label"] == "Bloody Bay Wall - Little Cayman, Cayman Islands"


def test_create_freedive_session_with_descents(app, conn):
    client = app.test_client()
    token = sign_up(client)
    response = client.post("/api/dives", headers=auth(token), json={
        "discipline": "freedive", "started_at": "2026-11-01T10:00",
        "descents": [{"depth_m": 12, "duration_s": 60}, {"depth_m": 20, "duration_s": 90}],
    })
    assert response.status_code == 201
    dive_id = response.get_json()["id"]
    detail = client.get("/api/dives/" + str(dive_id), headers=auth(token)).get_json()
    assert detail["dive"]["max_depth_m"] == 20
    assert len(detail["descents"]) == 2


def test_create_dive_with_bad_number_is_400(app, conn):
    client = app.test_client()
    token = sign_up(client)
    response = client.post("/api/dives", headers=auth(token), json={
        "discipline": "scuba", "started_at": "2026-11-01T10:00", "max_depth_m": "deep",
        "duration_s": 2400,
    })
    assert response.status_code == 400
    assert response.get_json()["error"] == "max_depth_m must be a number"


def test_other_users_private_dive_is_404(app, conn):
    client = app.test_client()
    owner = sign_up(client, "owner@example.com", "Owner")
    stranger = sign_up(client, "stranger@example.com", "Stranger")
    dive_id = client.post("/api/dives", headers=auth(owner), json={
        "discipline": "scuba", "started_at": "2026-11-01T10:00", "max_depth_m": 10,
        "duration_s": 600,
    }).get_json()["id"]
    response = client.get("/api/dives/" + str(dive_id), headers=auth(stranger))
    assert response.status_code == 404


# --- feed ---

def test_feed_kudos_and_comment(app, conn):
    client = app.test_client()
    owner = sign_up(client, "owner@example.com", "Owner")
    viewer = sign_up(client, "viewer@example.com", "Viewer")
    dive_id = client.post("/api/dives", headers=auth(owner), json={
        "discipline": "scuba", "started_at": "2026-11-01T10:00", "max_depth_m": 10,
        "duration_s": 600, "audience": "public",
    }).get_json()["id"]

    feed = client.get("/api/feed", headers=auth(viewer)).get_json()
    assert feed["items"][0]["id"] == dive_id

    assert client.post(f"/api/feed/dives/{dive_id}/kudos", headers=auth(viewer)).status_code == 201
    assert client.post(f"/api/feed/dives/{dive_id}/comments", headers=auth(viewer),
                       json={"body": "Nice dive"}).status_code == 201
    social = client.get(f"/api/feed/dives/{dive_id}/social", headers=auth(viewer)).get_json()
    assert social["kudos_count"] == 1
    assert social["comments"][0]["body"] == "Nice dive"


# --- CORS ---

def test_cors_allows_only_the_ui(app, conn):
    response = app.test_client().get("/health")
    assert response.headers["Access-Control-Allow-Origin"] == "http://ui.test"


def test_cors_preflight_is_answered(app, conn):
    # Before a POST with a token, the browser first asks with OPTIONS.
    response = app.test_client().options("/api/dives", headers={
        "Origin": "http://ui.test", "Access-Control-Request-Method": "POST"})
    assert response.status_code == 200
    assert "Authorization" in response.headers["Access-Control-Allow-Headers"]
