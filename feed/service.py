import users
from dives import service as dives_service

from . import repository

MAX_COMMENT_LENGTH = 500
FEED_PAGE_SIZE = 20


def get_dive_or_error(conn, dive_id, user_id):
    """Ask the dives domain for the dive. Raises if it doesn't exist or user_id can't see it."""
    dive = dives_service.get_visible_dive(conn, dive_id, user_id)
    if dive is None:
        raise ValueError("Dive not found")
    return dive


# --- kudos ---

def give_kudos(conn, dive_id, user_id):
    dive = get_dive_or_error(conn, dive_id, user_id)
    if dive["user_id"] == user_id:
        raise ValueError("You cannot give kudos to your own dive")
    if repository.has_kudos(conn, dive_id, user_id):
        raise ValueError("You already gave kudos to this dive")

    repository.insert_kudos(conn, dive_id, user_id)


def remove_kudos(conn, dive_id, user_id):
    if not repository.has_kudos(conn, dive_id, user_id):
        raise ValueError("You have not given kudos to this dive")

    repository.delete_kudos(conn, dive_id, user_id)


# --- comments ---

def add_comment(conn, dive_id, user_id, body, now):
    """`now` is passed in (a datetime) so tests can choose the time."""
    get_dive_or_error(conn, dive_id, user_id)
    if body is None or not body.strip():
        raise ValueError("Comment cannot be empty")
    body = body.strip()
    if len(body) > MAX_COMMENT_LENGTH:
        raise ValueError("Comment must be " + str(MAX_COMMENT_LENGTH) + " characters or fewer")

    created_at = now.strftime("%Y-%m-%dT%H:%M")
    return repository.insert_comment(conn, dive_id, user_id, body, created_at)


def delete_comment(conn, comment_id, user_id):
    """Delete a comment. Only its author can. Returns the dive_id it was on."""
    comment = repository.get_comment(conn, comment_id)
    if comment is None:
        raise ValueError("Comment not found")
    if comment["user_id"] != user_id:
        raise ValueError("You can only delete your own comments")

    repository.delete_comment(conn, comment_id)
    return comment["dive_id"]


# --- what the pages show ---

def get_dive_social(conn, dive_id, viewer_id):
    """Kudos and comments for the bottom of a dive page."""
    dive = get_dive_or_error(conn, dive_id, viewer_id)

    comments = []
    for comment in repository.list_comments(conn, dive_id):
        comments.append({
            "id": comment["id"],
            "body": comment["body"],
            "created_at": comment["created_at"],
            "author_name": users.get_user_name(conn, comment["user_id"]),
            "is_author": comment["user_id"] == viewer_id,
        })

    return {
        "dive_id": dive_id,
        "kudos_count": repository.count_kudos(conn, dive_id),
        "viewer_gave_kudos": repository.has_kudos(conn, dive_id, viewer_id),
        "can_give_kudos": dive["user_id"] != viewer_id,
        "comments": comments,
        "max_comment_length": MAX_COMMENT_LENGTH,
    }


def get_feed_page(conn, viewer_id, offset):
    """One page of the feed: dives viewer_id may see, with owner name and counts."""
    if offset < 0:
        offset = 0
    result = dives_service.list_feed_dives(conn, viewer_id, offset, FEED_PAGE_SIZE)

    items = []
    for dive in result["dives"]:
        item = dict(dive)
        item["owner_name"] = users.get_user_name(conn, dive["user_id"])
        item["kudos_count"] = repository.count_kudos(conn, dive["id"])
        item["comment_count"] = repository.count_comments(conn, dive["id"])
        items.append(item)

    return {
        "items": items,
        "has_more": result["has_more"],
        "next_offset": offset + FEED_PAGE_SIZE,
    }
