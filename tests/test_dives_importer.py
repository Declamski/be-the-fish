import io
import os

import pytest

from app import create_app
from db import get_connection
from dives import importer, service

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "subsurface_export.csv")


@pytest.fixture
def conn(tmp_path):
    data_dir = str(tmp_path)
    create_app({"PORT": 8000, "DATA_DIR": data_dir, "SECRET_KEY": "test"})
    connection = get_connection(data_dir)
    yield connection
    connection.close()


def test_parse_duration_to_seconds():
    assert importer.parse_duration_to_seconds("59:00") == 3540
    assert importer.parse_duration_to_seconds("42:30") == 2550


def test_parse_duration_to_seconds_handles_empty():
    assert importer.parse_duration_to_seconds("") is None


def test_parse_number_handles_empty():
    assert importer.parse_number("17.73") == 17.73
    assert importer.parse_number("") is None


def test_map_mode_to_discipline_empty_mode_is_scuba():
    # Subsurface leaves the cell empty for open circuit, its default mode.
    assert importer.map_mode_to_discipline("", "") == "scuba"


def test_map_mode_to_discipline_missing_mode_column_is_scuba():
    assert importer.map_mode_to_discipline(None, "") == "scuba"


def test_map_mode_to_discipline_rebreathers_are_scuba():
    assert importer.map_mode_to_discipline("OC", "") == "scuba"
    assert importer.map_mode_to_discipline("CCR", "") == "scuba"
    assert importer.map_mode_to_discipline("pSCR", "") == "scuba"


def test_map_mode_to_discipline_freedive():
    assert importer.map_mode_to_discipline("Freedive", "") == "freedive"


def test_map_mode_to_discipline_tag_upgrades_to_spearfishing():
    assert importer.map_mode_to_discipline("Freedive", "spearfishing") == "spearfishing"


def test_map_mode_to_discipline_tag_does_not_upgrade_scuba():
    assert importer.map_mode_to_discipline("OC", "spearfishing") == "scuba"


def test_map_mode_to_discipline_unknown_mode():
    assert importer.map_mode_to_discipline("Gauge", "") is None


def test_make_external_id():
    assert importer.make_external_id("2026-09-15", "10:08:16") == "subsurface:2026-09-15T10:08:16"


def test_parse_row_rejects_missing_depth():
    row = {
        "date": "2026-09-17", "time": "11:00:00", "duration [min]": "",
        "maxdepth [m]": "", "mode": "Freedive", "watertemp [C]": "26.0",
        "notes": "", "tags": "",
    }
    with pytest.raises(ValueError):
        importer.parse_row(row)


def test_parse_row_override_beats_mode():
    row = {
        "date": "2026-09-15", "time": "10:08:16", "duration [min]": "59:00",
        "maxdepth [m]": "17.73", "mode": "Freedive", "watertemp [C]": "31.0",
        "notes": "", "tags": "",
    }
    fields = importer.parse_row(row, discipline_override="scuba")
    assert fields["discipline"] == "scuba"


def test_parse_row_keeps_local_time():
    row = {
        "date": "2026-09-15", "time": "10:08:16", "duration [min]": "59:00",
        "maxdepth [m]": "17.73", "mode": "Freedive", "watertemp [C]": "31.0",
        "notes": "", "tags": "",
    }
    fields = importer.parse_row(row)
    assert fields["started_at"] == "2026-09-15T10:08:16"


def test_import_csv_file_counts(conn):
    summary = importer.import_csv_file(conn, user_id=1, csv_path=FIXTURE)
    assert summary["imported"] == 3
    assert summary["skipped_invalid"] == 1
    assert summary["skipped_duplicate"] == 1


def test_import_csv_file_maps_fields(conn):
    importer.import_csv_file(conn, user_id=1, csv_path=FIXTURE)
    dives = service.list_dives(conn, user_id=1)

    by_start = {d["started_at"]: d for d in dives}
    freedive = by_start["2026-09-15T10:08:16"]
    assert freedive["discipline"] == "freedive"
    assert freedive["max_depth_m"] == 17.73
    assert freedive["duration_s"] == 3540
    assert freedive["water_temp_c"] == 31.0
    assert freedive["source_device"] == "subsurface"

    assert by_start["2026-09-16T09:30:00"]["discipline"] == "scuba"
    assert by_start["2026-09-16T14:02:10"]["discipline"] == "spearfishing"


def test_import_csv_file_twice_does_not_duplicate(conn):
    importer.import_csv_file(conn, user_id=1, csv_path=FIXTURE)
    second = importer.import_csv_file(conn, user_id=1, csv_path=FIXTURE)

    assert second["imported"] == 0
    assert second["skipped_duplicate"] == 4
    assert len(service.list_dives(conn, user_id=1)) == 3


def test_import_csv_file_override_applies_to_every_row(conn):
    importer.import_csv_file(conn, user_id=1, csv_path=FIXTURE, discipline_override="scuba")
    dives = service.list_dives(conn, user_id=1)
    assert all(d["discipline"] == "scuba" for d in dives)


def test_import_csv_stream_rejects_unknown_override(conn):
    with open(FIXTURE, newline="") as f:
        with pytest.raises(ValueError):
            importer.import_csv_stream(conn, 1, f, discipline_override="snorkelling")


def test_import_csv_stream_rejects_file_with_wrong_columns(conn):
    stream = io.StringIO("name,age\nDeclan,21\n")
    with pytest.raises(ValueError):
        importer.import_csv_stream(conn, 1, stream)


def test_import_csv_stream_reads_an_upload_style_stream(conn):
    with open(FIXTURE, newline="") as f:
        text = f.read()
    summary = importer.import_csv_stream(conn, 1, io.StringIO(text))
    assert summary["imported"] == 3
