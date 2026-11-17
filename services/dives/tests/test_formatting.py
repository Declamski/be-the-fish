from formatting import format_datetime, format_duration, format_number


def test_duration_whole_minutes():
    assert format_duration(2700) == "45 min"


def test_duration_minutes_and_seconds():
    assert format_duration(80) == "1 min 20 s"


def test_duration_seconds_only():
    assert format_duration(45) == "45 s"


def test_duration_hours():
    assert format_duration(3900) == "1 h 5 min"


def test_duration_missing():
    assert format_duration(None) == "-"


def test_datetime_readable():
    assert format_datetime("2026-09-01T10:00") == "1 Sep 2026, 10:00"


def test_datetime_with_seconds():
    assert format_datetime("2026-09-15T10:08:16") == "15 Sep 2026, 10:08"


def test_datetime_unreadable_shown_as_is():
    assert format_datetime("yesterday") == "yesterday"


def test_datetime_missing():
    assert format_datetime("") == "-"


def test_number_whole():
    assert format_number(18.0, "m") == "18 m"


def test_number_rounded_to_one_decimal():
    assert format_number(17.73, "m") == "17.7 m"


def test_number_missing():
    assert format_number(None, "m") == "-"
