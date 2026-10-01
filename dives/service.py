import users
from sites import service as sites_service

from . import repository

VALID_DISCIPLINES = {"scuba", "freedive", "spearfishing"}
SESSION_DISCIPLINES = {"freedive", "spearfishing"}
VALID_VISIBILITY = ["poor", "moderate", "good", "excellent"]
VALID_CURRENT = ["none", "light", "moderate", "strong"]
# Who can see a dive. New and imported dives start as private.
VALID_AUDIENCES = ["private", "friends", "public"]


def check_audience(audience):
    if audience not in VALID_AUDIENCES:
        raise ValueError("Who can see this dive must be one of: " + ", ".join(VALID_AUDIENCES))


def can_view_dive(conn, dive, viewer_id):
    """True if viewer_id is allowed to see this dive."""
    if dive["user_id"] == viewer_id:
        return True
    if dive["audience"] == "public":
        return True
    if dive["audience"] == "friends":
        return users.are_friends(conn, dive["user_id"], viewer_id)
    return False


def check_site_and_conditions(conn, site_id, visibility, current):
    """All three are optional. Raise ValueError if any given value is not allowed."""
    # Sites belong to another domain, so we ask its service instead of querying its table.
    if site_id is not None and not sites_service.site_exists(conn, site_id):
        raise ValueError("That dive site does not exist")
    if visibility is not None and visibility not in VALID_VISIBILITY:
        raise ValueError("Visibility must be one of: " + ", ".join(VALID_VISIBILITY))
    if current is not None and current not in VALID_CURRENT:
        raise ValueError("Current must be one of: " + ", ".join(VALID_CURRENT))


def create_scuba_dive(conn, user_id, started_at, max_depth_m, duration_s, site_id=None,
                       water_temp_c=None, visibility=None, current=None, audience="private",
                       notes=None):
    if not started_at:
        raise ValueError("Start date/time is required")
    if max_depth_m is None or max_depth_m <= 0:
        raise ValueError("Max depth must be greater than 0")
    if duration_s is None or duration_s <= 0:
        raise ValueError("Duration must be greater than 0")
    check_site_and_conditions(conn, site_id, visibility, current)
    check_audience(audience)

    return repository.insert_dive(
        conn,
        user_id=user_id,
        discipline="scuba",
        started_at=started_at,
        site_id=site_id,
        max_depth_m=max_depth_m,
        duration_s=duration_s,
        water_temp_c=water_temp_c,
        visibility=visibility,
        current=current,
        audience=audience,
        notes=notes,
    )


def start_session_draft(discipline, started_at, site_id=None, visibility=None, current=None,
                        audience="private", notes=None):
    if discipline not in SESSION_DISCIPLINES:
        raise ValueError("Discipline must be freedive or spearfishing for a session")
    if not started_at:
        raise ValueError("Start date/time is required")

    return {
        "discipline": discipline,
        "started_at": started_at,
        "site_id": site_id,
        "visibility": visibility,
        "current": current,
        "audience": audience,
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
    check_site_and_conditions(conn, draft["site_id"], draft["visibility"], draft["current"])
    check_audience(draft["audience"])

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
        visibility=draft["visibility"],
        current=draft["current"],
        audience=draft["audience"],
        notes=draft["notes"],
    )

    for d in descents:
        repository.insert_descent(conn, dive_id, d["depth_m"], d["duration_s"], d["started_at"])

    return dive_id


def set_dive_site_and_conditions(conn, dive_id, user_id, site_id, visibility, current):
    """Set (or clear, with None) the site, visibility and current of an existing dive.

    This is how imported dives get a site and conditions.
    """
    dive = repository.get_dive(conn, dive_id)
    if dive is None or dive["user_id"] != user_id:
        raise ValueError("Dive not found")
    check_site_and_conditions(conn, site_id, visibility, current)

    repository.update_dive_site_and_conditions(conn, dive_id, site_id, visibility, current)


def set_dive_audience(conn, dive_id, user_id, audience):
    """Change who can see a dive. Only the dive's owner can do this."""
    dive = repository.get_dive(conn, dive_id)
    if dive is None or dive["user_id"] != user_id:
        raise ValueError("Dive not found")
    check_audience(audience)

    repository.update_dive_audience(conn, dive_id, audience)


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


def get_site_choices(conn):
    """Every dive site as {"id", "label"}, for the site dropdown on the dive forms."""
    choices = []
    for site in sites_service.search_sites(conn, ""):
        choices.append({"id": site["id"], "label": sites_service.get_site_label(conn, site["id"])})
    return choices


def get_dive_detail(conn, dive_id, viewer_id):
    """Everything the dive page shows. Other people may view it if the audience allows."""
    dive = repository.get_dive(conn, dive_id)
    # Same message for "doesn't exist" and "not allowed", so private dives stay hidden.
    if dive is None or not can_view_dive(conn, dive, viewer_id):
        raise ValueError("Dive not found")

    site_label = None
    if dive["site_id"] is not None:
        site_label = sites_service.get_site_label(conn, dive["site_id"])

    return {
        "dive": dive,
        "is_owner": dive["user_id"] == viewer_id,
        "owner_name": users.get_user_name(conn, dive["user_id"]),
        "site_label": site_label,
        "descents": repository.list_descents(conn, dive_id),
        "catches": repository.list_catches(conn, dive_id),
    }


# --- Public functions for other domains (the seam for Assignment 2) ---

def get_visible_dive(conn, dive_id, viewer_id):
    """The dive, or None if it doesn't exist or viewer_id is not allowed to see it."""
    dive = repository.get_dive(conn, dive_id)
    if dive is None or not can_view_dive(conn, dive, viewer_id):
        return None
    return dive


def list_feed_dives(conn, viewer_id, offset, limit):
    """One page of the dives viewer_id may see (their own included), newest first.

    Returns {"dives": [...], "has_more": True/False}. Each dive is a dict that
    also has the site's label, so the feed doesn't need to ask the sites domain.
    """
    visible = []
    for dive in repository.list_shared_and_own_dives(conn, viewer_id):
        # Friends-only dives still need checking against the friends list.
        if can_view_dive(conn, dive, viewer_id):
            visible.append(dive)

    page = visible[offset:offset + limit]

    dives = []
    for dive in page:
        site_label = None
        if dive["site_id"] is not None:
            site_label = sites_service.get_site_label(conn, dive["site_id"])
        dives.append({
            "id": dive["id"],
            "user_id": dive["user_id"],
            "started_at": dive["started_at"],
            "discipline": dive["discipline"],
            "max_depth_m": dive["max_depth_m"],
            "duration_s": dive["duration_s"],
            "site_label": site_label,
        })

    return {"dives": dives, "has_more": len(visible) > offset + limit}
