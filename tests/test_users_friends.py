import pytest

import users
from app import create_app
from db import get_connection


@pytest.fixture
def conn(tmp_path):
    data_dir = str(tmp_path)
    create_app({"PORT": 8000, "DATA_DIR": data_dir, "SECRET_KEY": "test"})
    connection = get_connection(data_dir)
    yield connection
    connection.close()


@pytest.fixture
def people(conn):
    """Three users: ann, bob and cat. Returns their ids."""
    ann = users.create_user(conn, "ann@example.com", "Ann Diver", "password123")
    bob = users.create_user(conn, "bob@example.com", "Bob Fisher", "password123")
    cat = users.create_user(conn, "cat@example.com", "Cat Freediver", "password123")
    return {"ann": ann, "bob": bob, "cat": cat}


# --- sending, accepting, removing ---

def test_send_request_then_accept_makes_friends(conn, people):
    users.send_friend_request(conn, people["ann"], people["bob"])
    assert users.get_friend_status(conn, people["ann"], people["bob"]) == "sent"
    assert users.get_friend_status(conn, people["bob"], people["ann"]) == "received"
    assert not users.are_friends(conn, people["ann"], people["bob"])

    users.accept_friend_request(conn, people["bob"], people["ann"])

    assert users.are_friends(conn, people["ann"], people["bob"])
    assert users.are_friends(conn, people["bob"], people["ann"])


def test_cannot_add_yourself(conn, people):
    with pytest.raises(ValueError):
        users.send_friend_request(conn, people["ann"], people["ann"])


def test_cannot_add_unknown_user(conn, people):
    with pytest.raises(ValueError):
        users.send_friend_request(conn, people["ann"], 9999)


def test_cannot_send_request_twice(conn, people):
    users.send_friend_request(conn, people["ann"], people["bob"])
    with pytest.raises(ValueError):
        users.send_friend_request(conn, people["ann"], people["bob"])


def test_cannot_send_request_back_when_one_is_waiting(conn, people):
    users.send_friend_request(conn, people["ann"], people["bob"])
    with pytest.raises(ValueError):
        users.send_friend_request(conn, people["bob"], people["ann"])


def test_cannot_send_request_to_existing_friend(conn, people):
    users.send_friend_request(conn, people["ann"], people["bob"])
    users.accept_friend_request(conn, people["bob"], people["ann"])
    with pytest.raises(ValueError):
        users.send_friend_request(conn, people["ann"], people["bob"])


def test_sender_cannot_accept_own_request(conn, people):
    users.send_friend_request(conn, people["ann"], people["bob"])
    with pytest.raises(ValueError):
        users.accept_friend_request(conn, people["ann"], people["bob"])


def test_decline_request(conn, people):
    users.send_friend_request(conn, people["ann"], people["bob"])
    users.remove_friend(conn, people["bob"], people["ann"])
    assert users.get_friend_status(conn, people["ann"], people["bob"]) == "none"


def test_unfriend(conn, people):
    users.send_friend_request(conn, people["ann"], people["bob"])
    users.accept_friend_request(conn, people["bob"], people["ann"])
    users.remove_friend(conn, people["ann"], people["bob"])
    assert not users.are_friends(conn, people["ann"], people["bob"])


def test_remove_when_nothing_to_remove(conn, people):
    with pytest.raises(ValueError):
        users.remove_friend(conn, people["ann"], people["bob"])


# --- lists ---

def test_lists_of_friends_and_requests(conn, people):
    users.send_friend_request(conn, people["ann"], people["bob"])
    users.accept_friend_request(conn, people["bob"], people["ann"])
    users.send_friend_request(conn, people["cat"], people["ann"])

    friend_names = [friend["name"] for friend in users.list_friends(conn, people["ann"])]
    assert friend_names == ["Bob Fisher"]
    incoming_names = [row["name"] for row in users.list_incoming_requests(conn, people["ann"])]
    assert incoming_names == ["Cat Freediver"]
    outgoing_names = [row["name"] for row in users.list_outgoing_requests(conn, people["cat"])]
    assert outgoing_names == ["Ann Diver"]


# --- search ---

def test_search_matches_part_of_name_ignoring_case(conn, people):
    results = users.search_users(conn, people["ann"], "FISH")
    assert [person["name"] for person in results] == ["Bob Fisher"]


def test_search_needs_letters_in_order(conn, people):
    # "Diver" is in "Cat Freediver" and "Ann Diver", but "revid" (reversed) is in neither.
    assert users.search_users(conn, people["bob"], "revid") == []


def test_search_does_not_return_yourself(conn, people):
    results = users.search_users(conn, people["ann"], "diver")
    assert [person["name"] for person in results] == ["Cat Freediver"]


def test_search_empty_query_returns_nothing(conn, people):
    assert users.search_users(conn, people["ann"], "  ") == []


def test_search_shows_friend_status(conn, people):
    users.send_friend_request(conn, people["ann"], people["bob"])
    results = users.search_users(conn, people["ann"], "bob")
    assert results[0]["status"] == "sent"


def test_get_user_name(conn, people):
    assert users.get_user_name(conn, people["ann"]) == "Ann Diver"
    assert users.get_user_name(conn, 9999) is None
