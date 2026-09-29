import csv

from . import repository
from .service import VALID_DISCIPLINES

# Subsurface writes one of four dive modes. CCR and pSCR are rebreathers,
# which are still scuba. Open circuit is Subsurface's default, and it leaves
# the cell EMPTY rather than writing "OC", so an empty mode means scuba.
# There is no spearfishing mode, so that one comes from the tags column.
# Columns parse_row() reads. If an uploaded file is missing any of them it is
# not a Subsurface export and we reject the whole file rather than every row.
REQUIRED_COLUMNS = [
    "date", "time", "duration [min]", "maxdepth [m]", "mode", "watertemp [C]",
    "notes", "tags",
]

MODE_TO_DISCIPLINE = {
    "": "scuba",
    "OC": "scuba",
    "CCR": "scuba",
    "pSCR": "scuba",
    "Freedive": "freedive",
}


def parse_duration_to_seconds(text):
    """Turn Subsurface's "59:00" (minutes:seconds) into 3540 seconds."""
    if not text or ":" not in text:
        return None
    minutes, seconds = text.split(":")
    return int(minutes) * 60 + int(seconds)


def parse_number(text):
    """Turn "17.73" into 17.73, and an empty cell into None."""
    if not text or not text.strip():
        return None
    return float(text)


def map_mode_to_discipline(mode, tags):
    """Decide the discipline from the watch mode, upgraded by the tags column."""
    discipline = MODE_TO_DISCIPLINE.get((mode or "").strip())
    if discipline is None:
        return None
    if discipline == "freedive" and tags and "spearfishing" in tags.lower():
        return "spearfishing"
    return discipline


def make_external_id(date, time):
    """Build the key that identifies this real-world dive across re-imports."""
    return "subsurface:" + date + "T" + time


def parse_row(row, discipline_override=None):
    """Turn one CSV row into dive fields. Raises ValueError if the row is unusable."""
    date = row["date"]
    time = row["time"]
    if not date or not time:
        raise ValueError("Row has no date or time")

    if discipline_override is not None:
        discipline = discipline_override
    else:
        discipline = map_mode_to_discipline(row["mode"], row["tags"])
    if discipline is None:
        raise ValueError("Unknown dive mode: " + str(row["mode"]))

    max_depth_m = parse_number(row["maxdepth [m]"])
    duration_s = parse_duration_to_seconds(row["duration [min]"])
    if max_depth_m is None or max_depth_m <= 0:
        raise ValueError("Row has no usable max depth")
    if duration_s is None or duration_s <= 0:
        raise ValueError("Row has no usable duration")

    return {
        "external_id": make_external_id(date, time),
        "started_at": date + "T" + time,
        "discipline": discipline,
        "max_depth_m": max_depth_m,
        "duration_s": duration_s,
        "water_temp_c": parse_number(row["watertemp [C]"]),
        "notes": row["notes"] or None,
    }


def import_csv_stream(conn, user_id, text_stream, discipline_override=None):
    """Read Subsurface CSV rows from an open file or upload and insert the new dives."""
    if discipline_override is not None and discipline_override not in VALID_DISCIPLINES:
        raise ValueError("Unknown discipline: " + str(discipline_override))

    reader = csv.DictReader(text_stream)
    columns = reader.fieldnames or []
    for name in REQUIRED_COLUMNS:
        if name not in columns:
            raise ValueError("This does not look like a Subsurface CSV export: "
                             "the column '" + name + "' is missing")

    imported = 0
    skipped_invalid = 0
    skipped_duplicate = 0

    for row in reader:
        try:
            fields = parse_row(row, discipline_override)
        except ValueError:
            skipped_invalid = skipped_invalid + 1
            continue

        if repository.get_dive_by_external_id(conn, fields["external_id"]) is not None:
            skipped_duplicate = skipped_duplicate + 1
            continue

        repository.insert_dive(
            conn,
            user_id=user_id,
            discipline=fields["discipline"],
            started_at=fields["started_at"],
            source_device="subsurface",
            external_id=fields["external_id"],
            max_depth_m=fields["max_depth_m"],
            duration_s=fields["duration_s"],
            water_temp_c=fields["water_temp_c"],
            notes=fields["notes"],
        )
        imported = imported + 1

    return {
        "imported": imported,
        "skipped_invalid": skipped_invalid,
        "skipped_duplicate": skipped_duplicate,
    }


def import_csv_file(conn, user_id, csv_path, discipline_override=None):
    """Open a Subsurface CSV export on disk and import it."""
    with open(csv_path, newline="") as f:
        return import_csv_stream(conn, user_id, f, discipline_override)
