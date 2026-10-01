import datetime

import pytest

import users
from app import create_app
from db import get_connection
from dives import service as dives_service
from feed import service

NOW = datetime.datetime(2026, 10, 2, 12, 0)


@pytest.fixture
def conn(tmp_path):
    data_dir = str(tmp_path)
    create_app({"PORT": 8000, "DATA_DIR": data_dir, "SECRET_KEY": "test"})
    connection = get_connection(data_dir)
    yield connection
    connection.close()


@pytest.fixture
def people(conn):
    """owner and friend are friends; stranger knows nobody."""
    owner = users.create_user(conn, "owner@example.com", "Owner", "password123")
    friend = users.create_user(conn, "friend@example.com", "Friend", "password123")
    stranger = users.create_user(conn, "stranger@example.com", "Stranger", "password123")
    users.send_friend_request(conn, owner, friend)
    users.accept_friend_request(conn, friend, owner)
    return {"owner": owner, "friend": friend, "stranger": stranger}


def make_dive(conn, user_id, audience, started_at="2026-09-01T10:00"):
    return dives_service.create_scuba_dive(
        conn, user_id=user_id, started_at=started_at,
        max_depth_m=10, duration_s=100, audience=audience,
    )


# --- kudos ---

def test_give_kudos(conn, people):
    dive_id = make_dive(conn, people["owner"], "public")
    service.give_kudos(conn, dive_id, people["stranger"])
    social = service.get_dive_social(conn, dive_id, people["stranger"])
    assert social["kudos_count"] == 1
    assert social["viewer_gave_kudos"] is True


def test_cannot_give_kudos_to_own_dive(conn, people):
    dive_id = make_dive(conn, people["owner"], "public")
    with pytest.raises(ValueError):
        service.give_kudos(conn, dive_id, people["owner"])


def test_cannot_give_kudos_twice(conn, people):
    dive_id = make_dive(conn, people["owner"], "public")
    service.give_kudos(conn, dive_id, people["friend"])
    with pytest.raises(ValueError):
        service.give_kudos(conn, dive_id, people["friend"])


def test_cannot_give_kudos_to_dive_you_cannot_see(conn, people):
    dive_id = make_dive(conn, people["owner"], "friends")
    with pytest.raises(ValueError):
        service.give_kudos(conn, dive_id, people["stranger"])


def test_cannot_give_kudos_to_missing_dive(conn, people):
    with pytest.raises(ValueError):
        service.give_kudos(conn, 9999, people["friend"])


def test_take_back_kudos(conn, people):
    dive_id = make_dive(conn, people["owner"], "public")
    service.give_kudos(conn, dive_id, people["friend"])
    service.remove_kudos(conn, dive_id, people["friend"])
    assert service.get_dive_social(conn, dive_id, people["friend"])["kudos_count"] == 0


def test_cannot_take_back_kudos_never_given(conn, people):
    dive_id = make_dive(conn, people["owner"], "public")
    with pytest.raises(ValueError):
        service.remove_kudos(conn, dive_id, people["friend"])


# --- comments ---

def test_add_comment(conn, people):
    dive_id = make_dive(conn, people["owner"], "friends")
    service.add_comment(conn, dive_id, people["friend"], "  Nice dive!  ", NOW)
    comments = service.get_dive_social(conn, dive_id, people["owner"])["comments"]
    assert len(comments) == 1
    assert comments[0]["body"] == "Nice dive!"
    assert comments[0]["author_name"] == "Friend"
    assert comments[0]["created_at"] == "2026-10-02T12:00"
    assert comments[0]["is_author"] is False


def test_comment_cannot_be_empty(conn, people):
    dive_id = make_dive(conn, people["owner"], "public")
    with pytest.raises(ValueError):
        service.add_comment(conn, dive_id, people["friend"], "   ", NOW)


def test_comment_can_be_exactly_500_characters(conn, people):
    dive_id = make_dive(conn, people["owner"], "public")
    service.add_comment(conn, dive_id, people["friend"], "a" * 500, NOW)


def test_comment_cannot_be_over_500_characters(conn, people):
    dive_id = make_dive(conn, people["owner"], "public")
    with pytest.raises(ValueError):
        service.add_comment(conn, dive_id, people["friend"], "a" * 501, NOW)


def test_cannot_comment_on_dive_you_cannot_see(conn, people):
    dive_id = make_dive(conn, people["owner"], "private")
    with pytest.raises(ValueError):
        service.add_comment(conn, dive_id, people["friend"], "Hello", NOW)


def test_owner_can_comment_on_own_dive(conn, people):
    dive_id = make_dive(conn, people["owner"], "private")
    service.add_comment(conn, dive_id, people["owner"], "Note to self", NOW)


def test_delete_own_comment(conn, people):
    dive_id = make_dive(conn, people["owner"], "public")
    comment_id = service.add_comment(conn, dive_id, people["friend"], "Hello", NOW)
    assert service.delete_comment(conn, comment_id, people["friend"]) == dive_id
    assert service.get_dive_social(conn, dive_id, people["owner"])["comments"] == []


def test_cannot_delete_someone_elses_comment(conn, people):
    dive_id = make_dive(conn, people["owner"], "public")
    comment_id = service.add_comment(conn, dive_id, people["friend"], "Hello", NOW)
    with pytest.raises(ValueError):
        service.delete_comment(conn, comment_id, people["owner"])


def test_delete_missing_comment(conn, people):
    with pytest.raises(ValueError):
        service.delete_comment(conn, 9999, people["owner"])


# --- get_dive_social ---

def test_dive_social_owner_cannot_give_kudos(conn, people):
    dive_id = make_dive(conn, people["owner"], "public")
    assert service.get_dive_social(conn, dive_id, people["owner"])["can_give_kudos"] is False
    assert service.get_dive_social(conn, dive_id, people["friend"])["can_give_kudos"] is True


def test_dive_social_hidden_from_people_who_cannot_see_dive(conn, people):
    dive_id = make_dive(conn, people["owner"], "private")
    with pytest.raises(ValueError):
        service.get_dive_social(conn, dive_id, people["stranger"])


# --- feed ---

def feed_ids(conn, viewer_id, offset=0):
    return [item["id"] for item in service.get_feed_page(conn, viewer_id, offset)["items"]]


def test_feed_shows_what_each_person_may_see(conn, people):
    own_private = make_dive(conn, people["owner"], "private")
    own_friends = make_dive(conn, people["owner"], "friends")
    own_public = make_dive(conn, people["owner"], "public")

    assert set(feed_ids(conn, people["owner"])) == {own_private, own_friends, own_public}
    assert set(feed_ids(conn, people["friend"])) == {own_friends, own_public}
    assert set(feed_ids(conn, people["stranger"])) == {own_public}


def test_feed_is_newest_first(conn, people):
    older = make_dive(conn, people["owner"], "public", started_at="2026-09-01T10:00")
    newer = make_dive(conn, people["owner"], "public", started_at="2026-09-20T10:00")
    assert feed_ids(conn, people["stranger"]) == [newer, older]


def test_feed_items_have_owner_name_and_counts(conn, people):
    dive_id = make_dive(conn, people["owner"], "public")
    service.give_kudos(conn, dive_id, people["friend"])
    service.add_comment(conn, dive_id, people["friend"], "Nice", NOW)

    item = service.get_feed_page(conn, people["friend"], 0)["items"][0]
    assert item["owner_name"] == "Owner"
    assert item["kudos_count"] == 1
    assert item["comment_count"] == 1


def test_feed_pages(conn, people):
    for day in range(1, 26):
        make_dive(conn, people["owner"], "public", started_at=f"2026-09-{day:02d}T10:00")

    first = service.get_feed_page(conn, people["stranger"], 0)
    assert len(first["items"]) == service.FEED_PAGE_SIZE
    assert first["has_more"] is True
    assert first["next_offset"] == service.FEED_PAGE_SIZE

    second = service.get_feed_page(conn, people["stranger"], first["next_offset"])
    assert len(second["items"]) == 25 - service.FEED_PAGE_SIZE
    assert second["has_more"] is False

    first_ids = {item["id"] for item in first["items"]}
    second_ids = {item["id"] for item in second["items"]}
    assert first_ids.isdisjoint(second_ids)


def test_feed_negative_offset_starts_at_beginning(conn, people):
    dive_id = make_dive(conn, people["owner"], "public")
    assert feed_ids(conn, people["stranger"], offset=-5) == [dive_id]


def test_feed_shows_site_label(conn, people):
    dive_id = dives_service.create_scuba_dive(
        conn, user_id=people["owner"], started_at="2026-09-01T10:00",
        max_depth_m=10, duration_s=100, site_id=1, audience="public",
    )
    item = service.get_feed_page(conn, people["stranger"], 0)["items"][0]
    assert item["id"] == dive_id
    assert item["site_label"] == "Bloody Bay Wall - Little Cayman, Cayman Islands"
