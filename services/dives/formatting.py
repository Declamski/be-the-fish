"""Turn stored values into readable text for the templates.

The database keeps SI units and ISO dates (CLAUDE.md conventions). These
functions are registered as Jinja filters in app.py, so a template can write
{{ dive.duration_s | duration }} or {{ dive.started_at | datetime }}.
"""
import datetime


def format_duration(seconds):
    """2700 -> "45 min", 80 -> "1 min 20 s", 45 -> "45 s", 3900 -> "1 h 5 min"."""
    if seconds is None:
        return "-"
    seconds = int(seconds)

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    rest = seconds % 60

    if hours > 0:
        return str(hours) + " h " + str(minutes) + " min"
    if minutes > 0 and rest > 0:
        return str(minutes) + " min " + str(rest) + " s"
    if minutes > 0:
        return str(minutes) + " min"
    return str(rest) + " s"


def format_datetime(text):
    """ "2026-09-01T10:00" -> "1 Sep 2026, 10:00". Anything unreadable is shown as-is."""
    if not text:
        return "-"
    try:
        value = datetime.datetime.fromisoformat(text)
    except ValueError:
        return text
    return str(value.day) + " " + value.strftime("%b %Y, %H:%M")


def format_number(value, unit):
    """(18.0, "m") -> "18 m", (17.73, "m") -> "17.7 m", (None, "m") -> "-"."""
    if value is None:
        return "-"
    rounded = round(float(value), 1)
    if rounded == int(rounded):
        return str(int(rounded)) + " " + unit
    return str(rounded) + " " + unit
