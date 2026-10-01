import pytest

import users
from app import create_app
from db import get_connection
from dives import service
from sites.service import SEED_SITES


@pytest.fixture
def conn(tmp_path):
    data_dir = str(tmp_path)
    create_app({"PORT": 8000, "DATA_DIR": data_dir, "SECRET_KEY": "test"})
    connection = get_connection(data_dir)
    yield connection
    connection.close()


def test_create_scuba_dive_valid(conn):
    dive_id = service.create_scuba_dive(
        conn, user_id=1, started_at="2026-01-01T10:00:00Z",
        max_depth_m=18.5, duration_s=2400,
    )
    assert dive_id is not None


def test_create_scuba_dive_rejects_bad_depth(conn):
    with pytest.raises(ValueError):
        service.create_scuba_dive(
            conn, user_id=1, started_at="2026-01-01T10:00:00Z",
            max_depth_m=0, duration_s=2400,
        )


def test_create_scuba_dive_rejects_bad_duration(conn):
    with pytest.raises(ValueError):
        service.create_scuba_dive(
            conn, user_id=1, started_at="2026-01-01T10:00:00Z",
            max_depth_m=10, duration_s=-5,
        )


def test_create_scuba_dive_rejects_missing_started_at(conn):
    with pytest.raises(ValueError):
        service.create_scuba_dive(
            conn, user_id=1, started_at="",
            max_depth_m=10, duration_s=100,
        )


def test_start_session_draft_rejects_scuba(conn):
    with pytest.raises(ValueError):
        service.start_session_draft(discipline="scuba", started_at="2026-01-01T10:00:00Z")


def test_start_session_draft_valid(conn):
    draft = service.start_session_draft(discipline="freedive", started_at="2026-01-01T10:00:00Z")
    assert draft["descents"] == []
    assert draft["discipline"] == "freedive"


def test_add_descent_to_draft_rejects_bad_depth():
    draft = service.start_session_draft(discipline="freedive", started_at="2026-01-01T10:00:00Z")
    with pytest.raises(ValueError):
        service.add_descent_to_draft(draft, depth_m=0, duration_s=60)


def test_add_descent_to_draft_does_not_mutate_input():
    draft = service.start_session_draft(discipline="freedive", started_at="2026-01-01T10:00:00Z")
    new_draft = service.add_descent_to_draft(draft, depth_m=12, duration_s=60)
    assert draft["descents"] == []
    assert len(new_draft["descents"]) == 1


def test_finish_session_rejects_empty_draft(conn):
    draft = service.start_session_draft(discipline="freedive", started_at="2026-01-01T10:00:00Z")
    with pytest.raises(ValueError):
        service.finish_session(conn, user_id=1, draft=draft)


def test_finish_session_derives_aggregates(conn):
    draft = service.start_session_draft(discipline="freedive", started_at="2026-01-01T10:00:00Z")
    draft = service.add_descent_to_draft(draft, depth_m=10, duration_s=60)
    draft = service.add_descent_to_draft(draft, depth_m=15, duration_s=90)

    dive_id = service.finish_session(conn, user_id=1, draft=draft)

    detail = service.get_dive_detail(conn, dive_id, viewer_id=1)
    assert detail["dive"]["max_depth_m"] == 15
    assert detail["dive"]["duration_s"] == 150
    assert len(detail["descents"]) == 2


def test_add_catch_rejects_non_spearfishing_dive(conn):
    dive_id = service.create_scuba_dive(
        conn, user_id=1, started_at="2026-01-01T10:00:00Z",
        max_depth_m=10, duration_s=100,
    )
    with pytest.raises(ValueError):
        service.add_catch(conn, dive_id=dive_id, user_id=1, species="Grouper")


def test_add_catch_rejects_other_users_dive(conn):
    draft = service.start_session_draft(discipline="spearfishing", started_at="2026-01-01T10:00:00Z")
    draft = service.add_descent_to_draft(draft, depth_m=10, duration_s=60)
    dive_id = service.finish_session(conn, user_id=1, draft=draft)

    with pytest.raises(ValueError):
        service.add_catch(conn, dive_id=dive_id, user_id=2, species="Grouper")


def test_add_catch_rejects_empty_species(conn):
    draft = service.start_session_draft(discipline="spearfishing", started_at="2026-01-01T10:00:00Z")
    draft = service.add_descent_to_draft(draft, depth_m=10, duration_s=60)
    dive_id = service.finish_session(conn, user_id=1, draft=draft)

    with pytest.raises(ValueError):
        service.add_catch(conn, dive_id=dive_id, user_id=1, species="  ")


def test_add_catch_valid(conn):
    draft = service.start_session_draft(discipline="spearfishing", started_at="2026-01-01T10:00:00Z")
    draft = service.add_descent_to_draft(draft, depth_m=10, duration_s=60)
    dive_id = service.finish_session(conn, user_id=1, draft=draft)

    service.add_catch(conn, dive_id=dive_id, user_id=1, species="Grouper", weight_kg=2.5)

    detail = service.get_dive_detail(conn, dive_id, viewer_id=1)
    assert len(detail["catches"]) == 1
    assert detail["catches"][0]["species"] == "Grouper"


def test_get_dive_detail_rejects_other_users_dive(conn):
    dive_id = service.create_scuba_dive(
        conn, user_id=1, started_at="2026-01-01T10:00:00Z",
        max_depth_m=10, duration_s=100,
    )
    with pytest.raises(ValueError):
        service.get_dive_detail(conn, dive_id, viewer_id=2)


# --- site and conditions ---
# The test database is seeded with SEED_SITES at startup, so site 1 exists.

def make_scuba_dive(conn, user_id=1):
    return service.create_scuba_dive(
        conn, user_id=user_id, started_at="2026-01-01T10:00:00",
        max_depth_m=10, duration_s=100,
    )


def test_create_scuba_dive_with_site_and_conditions(conn):
    dive_id = service.create_scuba_dive(
        conn, user_id=1, started_at="2026-01-01T10:00:00",
        max_depth_m=10, duration_s=100, site_id=1, visibility="good", current="light",
    )
    detail = service.get_dive_detail(conn, dive_id, viewer_id=1)
    assert detail["dive"]["visibility"] == "good"
    assert detail["dive"]["current"] == "light"
    assert detail["site_label"] == "Bloody Bay Wall - Little Cayman, Cayman Islands"


def test_create_scuba_dive_rejects_unknown_site(conn):
    with pytest.raises(ValueError):
        service.create_scuba_dive(
            conn, user_id=1, started_at="2026-01-01T10:00:00",
            max_depth_m=10, duration_s=100, site_id=9999,
        )


def test_create_scuba_dive_rejects_unknown_visibility(conn):
    with pytest.raises(ValueError):
        service.create_scuba_dive(
            conn, user_id=1, started_at="2026-01-01T10:00:00",
            max_depth_m=10, duration_s=100, visibility="crystal",
        )


def test_create_scuba_dive_rejects_unknown_current(conn):
    with pytest.raises(ValueError):
        service.create_scuba_dive(
            conn, user_id=1, started_at="2026-01-01T10:00:00",
            max_depth_m=10, duration_s=100, current="raging",
        )


def test_dive_without_site_has_no_label(conn):
    dive_id = make_scuba_dive(conn)
    detail = service.get_dive_detail(conn, dive_id, viewer_id=1)
    assert detail["site_label"] is None
    assert detail["dive"]["visibility"] is None


def test_finish_session_saves_site_and_conditions(conn):
    draft = service.start_session_draft(
        discipline="freedive", started_at="2026-01-01T10:00:00",
        site_id=1, visibility="excellent", current="none",
    )
    draft = service.add_descent_to_draft(draft, depth_m=10, duration_s=60)
    dive_id = service.finish_session(conn, user_id=1, draft=draft)

    dive = service.get_dive_detail(conn, dive_id, viewer_id=1)["dive"]
    assert dive["site_id"] == 1
    assert dive["visibility"] == "excellent"
    assert dive["current"] == "none"


def test_finish_session_rejects_unknown_site(conn):
    draft = service.start_session_draft(
        discipline="freedive", started_at="2026-01-01T10:00:00", site_id=9999,
    )
    draft = service.add_descent_to_draft(draft, depth_m=10, duration_s=60)
    with pytest.raises(ValueError):
        service.finish_session(conn, user_id=1, draft=draft)


def test_set_dive_site_and_conditions(conn):
    dive_id = make_scuba_dive(conn)
    service.set_dive_site_and_conditions(
        conn, dive_id, user_id=1, site_id=2, visibility="poor", current="strong",
    )
    detail = service.get_dive_detail(conn, dive_id, viewer_id=1)
    assert detail["dive"]["site_id"] == 2
    assert detail["dive"]["visibility"] == "poor"
    assert detail["dive"]["current"] == "strong"


def test_set_dive_site_and_conditions_can_clear_them(conn):
    dive_id = make_scuba_dive(conn)
    service.set_dive_site_and_conditions(
        conn, dive_id, user_id=1, site_id=2, visibility="poor", current="strong",
    )
    service.set_dive_site_and_conditions(
        conn, dive_id, user_id=1, site_id=None, visibility=None, current=None,
    )
    detail = service.get_dive_detail(conn, dive_id, viewer_id=1)
    assert detail["dive"]["site_id"] is None
    assert detail["site_label"] is None


def test_set_dive_site_and_conditions_rejects_other_users_dive(conn):
    dive_id = make_scuba_dive(conn, user_id=1)
    with pytest.raises(ValueError):
        service.set_dive_site_and_conditions(
            conn, dive_id, user_id=2, site_id=1, visibility=None, current=None,
        )


def test_set_dive_site_and_conditions_rejects_unknown_site(conn):
    dive_id = make_scuba_dive(conn)
    with pytest.raises(ValueError):
        service.set_dive_site_and_conditions(
            conn, dive_id, user_id=1, site_id=9999, visibility=None, current=None,
        )


def test_get_site_choices_lists_every_site_with_label(conn):
    choices = service.get_site_choices(conn)
    labels = [choice["label"] for choice in choices]
    assert "Blue Hole - Dahab, Egypt" in labels
    assert "Blue Hole - Gozo, Malta" in labels
    assert len(choices) == len(SEED_SITES)


# --- audience: who can see a dive ---

@pytest.fixture
def three_users(conn):
    owner = users.create_user(conn, "owner@example.com", "Owner", "password123")
    friend = users.create_user(conn, "friend@example.com", "Friend", "password123")
    stranger = users.create_user(conn, "stranger@example.com", "Stranger", "password123")
    users.send_friend_request(conn, owner, friend)
    users.accept_friend_request(conn, friend, owner)
    return {"owner": owner, "friend": friend, "stranger": stranger}


def make_dive_with_audience(conn, user_id, audience):
    return service.create_scuba_dive(
        conn, user_id=user_id, started_at="2026-01-01T10:00:00",
        max_depth_m=10, duration_s=100, audience=audience,
    )


def test_new_dive_is_private_by_default(conn):
    dive_id = make_scuba_dive(conn)
    assert service.get_dive_detail(conn, dive_id, viewer_id=1)["dive"]["audience"] == "private"


def test_create_dive_rejects_unknown_audience(conn):
    with pytest.raises(ValueError):
        make_dive_with_audience(conn, 1, "everyone")


def test_private_dive_only_visible_to_owner(conn, three_users):
    dive_id = make_dive_with_audience(conn, three_users["owner"], "private")
    service.get_dive_detail(conn, dive_id, viewer_id=three_users["owner"])
    with pytest.raises(ValueError):
        service.get_dive_detail(conn, dive_id, viewer_id=three_users["friend"])


def test_friends_dive_visible_to_friend_not_stranger(conn, three_users):
    dive_id = make_dive_with_audience(conn, three_users["owner"], "friends")
    detail = service.get_dive_detail(conn, dive_id, viewer_id=three_users["friend"])
    assert detail["is_owner"] is False
    assert detail["owner_name"] == "Owner"
    with pytest.raises(ValueError):
        service.get_dive_detail(conn, dive_id, viewer_id=three_users["stranger"])


def test_public_dive_visible_to_anyone(conn, three_users):
    dive_id = make_dive_with_audience(conn, three_users["owner"], "public")
    detail = service.get_dive_detail(conn, dive_id, viewer_id=three_users["stranger"])
    assert detail["is_owner"] is False


def test_owner_detail_says_is_owner(conn, three_users):
    dive_id = make_dive_with_audience(conn, three_users["owner"], "public")
    assert service.get_dive_detail(conn, dive_id, viewer_id=three_users["owner"])["is_owner"]


def test_session_keeps_audience(conn):
    draft = service.start_session_draft(
        discipline="freedive", started_at="2026-01-01T10:00:00", audience="public",
    )
    draft = service.add_descent_to_draft(draft, depth_m=10, duration_s=60)
    dive_id = service.finish_session(conn, user_id=1, draft=draft)
    assert service.get_dive_detail(conn, dive_id, viewer_id=1)["dive"]["audience"] == "public"


def test_set_dive_audience(conn, three_users):
    dive_id = make_dive_with_audience(conn, three_users["owner"], "private")
    service.set_dive_audience(conn, dive_id, three_users["owner"], "public")
    service.get_dive_detail(conn, dive_id, viewer_id=three_users["stranger"])


def test_set_dive_audience_only_owner(conn, three_users):
    dive_id = make_dive_with_audience(conn, three_users["owner"], "public")
    with pytest.raises(ValueError):
        service.set_dive_audience(conn, dive_id, three_users["friend"], "private")


def test_set_dive_audience_rejects_unknown_value(conn, three_users):
    dive_id = make_dive_with_audience(conn, three_users["owner"], "private")
    with pytest.raises(ValueError):
        service.set_dive_audience(conn, dive_id, three_users["owner"], "everyone")
