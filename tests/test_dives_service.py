import pytest

from app import create_app
from db import get_connection
from dives import service


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

    detail = service.get_dive_detail(conn, dive_id, user_id=1)
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

    detail = service.get_dive_detail(conn, dive_id, user_id=1)
    assert len(detail["catches"]) == 1
    assert detail["catches"][0]["species"] == "Grouper"


def test_get_dive_detail_rejects_other_users_dive(conn):
    dive_id = service.create_scuba_dive(
        conn, user_id=1, started_at="2026-01-01T10:00:00Z",
        max_depth_m=10, duration_s=100,
    )
    with pytest.raises(ValueError):
        service.get_dive_detail(conn, dive_id, user_id=2)
