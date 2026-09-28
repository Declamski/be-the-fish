from . import repository

VALID_DISCIPLINES = {"scuba", "freedive", "spearfishing"}
SESSION_DISCIPLINES = {"freedive", "spearfishing"}


def create_scuba_dive(conn, user_id, started_at, max_depth_m, duration_s, site_id=None,
                       water_temp_c=None, notes=None):
    if not started_at:
        raise ValueError("Start date/time is required")
    if max_depth_m is None or max_depth_m <= 0:
        raise ValueError("Max depth must be greater than 0")
    if duration_s is None or duration_s <= 0:
        raise ValueError("Duration must be greater than 0")

    return repository.insert_dive(
        conn,
        user_id=user_id,
        discipline="scuba",
        started_at=started_at,
        site_id=site_id,
        max_depth_m=max_depth_m,
        duration_s=duration_s,
        water_temp_c=water_temp_c,
        notes=notes,
    )


def start_session_draft(discipline, started_at, site_id=None, notes=None):
    if discipline not in SESSION_DISCIPLINES:
        raise ValueError("Discipline must be freedive or spearfishing for a session")
    if not started_at:
        raise ValueError("Start date/time is required")

    return {
        "discipline": discipline,
        "started_at": started_at,
        "site_id": site_id,
        "notes": notes,
        "descents": [],
    }


def add_descent_to_draft(draft, depth_m, duration_s, started_at=None):
    if depth_m is None or depth_m <= 0:
        raise ValueError("Descent depth must be greater than 0")
    if duration_s is None or duration_s <= 0:
        raise ValueError("Descent duration must be greater than 0")

    new_descent = {"depth_m": depth_m, "duration_s": duration_s, "started_at": started_at}
    new_draft = dict(draft)
    new_draft["descents"] = draft["descents"] + [new_descent]
    return new_draft


def finish_session(conn, user_id, draft):
    descents = draft["descents"]
    if len(descents) == 0:
        raise ValueError("Add at least one descent before finishing the session")

    max_depth_m = max(d["depth_m"] for d in descents)
    duration_s = sum(d["duration_s"] for d in descents)

    dive_id = repository.insert_dive(
        conn,
        user_id=user_id,
        discipline=draft["discipline"],
        started_at=draft["started_at"],
        site_id=draft["site_id"],
        max_depth_m=max_depth_m,
        duration_s=duration_s,
        notes=draft["notes"],
    )

    for d in descents:
        repository.insert_descent(conn, dive_id, d["depth_m"], d["duration_s"], d["started_at"])

    return dive_id


def add_catch(conn, dive_id, user_id, species, weight_kg=None):
    dive = repository.get_dive(conn, dive_id)
    if dive is None:
        raise ValueError("Dive not found")
    if dive["user_id"] != user_id:
        raise ValueError("You can only log catches on your own dives")
    if dive["discipline"] != "spearfishing":
        raise ValueError("Catches can only be logged on spearfishing dives")
    if not species or not species.strip():
        raise ValueError("Species is required")
    if weight_kg is not None and weight_kg <= 0:
        raise ValueError("Weight must be greater than 0")

    return repository.insert_catch(conn, dive_id, species.strip(), weight_kg)


def list_dives(conn, user_id):
    return repository.list_dives_for_user(conn, user_id)


def get_dive_detail(conn, dive_id, user_id):
    dive = repository.get_dive(conn, dive_id)
    if dive is None or dive["user_id"] != user_id:
        raise ValueError("Dive not found")

    return {
        "dive": dive,
        "descents": repository.list_descents(conn, dive_id),
        "catches": repository.list_catches(conn, dive_id),
    }
