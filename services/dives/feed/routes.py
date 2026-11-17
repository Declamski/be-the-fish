import datetime

import flask

import users
from . import service

bp = flask.Blueprint("feed", __name__, url_prefix="/feed")


def get_connection():
    return flask.g.db


def current_user_id():
    return flask.session["user_id"]


def read_offset():
    try:
        return int(flask.request.args.get("offset", 0))
    except ValueError:
        return 0


@bp.route("", methods=["GET"])
@users.login_required
def feed_page():
    page = service.get_feed_page(get_connection(), current_user_id(), read_offset())
    return flask.render_template("feed/feed.html", **page)


@bp.route("/more", methods=["GET"])
@users.login_required
def feed_more():
    # Only a fragment: static/infinite_scroll.js adds it to the bottom of the feed.
    page = service.get_feed_page(get_connection(), current_user_id(), read_offset())
    return flask.render_template("feed/_items.html", **page)


@bp.route("/dives/<int:dive_id>/social", methods=["GET"])
@users.login_required
def dive_social(dive_id):
    # Only a fragment: static/load_fragment.js puts it at the bottom of the dive page.
    # This keeps the dives domain from importing the feed domain.
    try:
        social = service.get_dive_social(get_connection(), dive_id, current_user_id())
    except ValueError:
        return "", 404
    return flask.render_template("feed/_dive_social.html", **social)


# The forms below come from the dive page, so they always go back to it.
# Errors are shown there with flask.flash (see base.html).

@bp.route("/dives/<int:dive_id>/kudos", methods=["POST"])
@users.login_required
def give_kudos(dive_id):
    try:
        service.give_kudos(get_connection(), dive_id, current_user_id())
    except ValueError as e:
        flask.flash(str(e))
    return flask.redirect(f"/dives/{dive_id}")


@bp.route("/dives/<int:dive_id>/kudos/remove", methods=["POST"])
@users.login_required
def remove_kudos(dive_id):
    try:
        service.remove_kudos(get_connection(), dive_id, current_user_id())
    except ValueError as e:
        flask.flash(str(e))
    return flask.redirect(f"/dives/{dive_id}")


@bp.route("/dives/<int:dive_id>/comments", methods=["POST"])
@users.login_required
def add_comment(dive_id):
    body = flask.request.form.get("body", "")
    try:
        service.add_comment(get_connection(), dive_id, current_user_id(), body,
                            now=datetime.datetime.now())
    except ValueError as e:
        flask.flash(str(e))
    return flask.redirect(f"/dives/{dive_id}")


@bp.route("/comments/<int:comment_id>/delete", methods=["POST"])
@users.login_required
def delete_comment(comment_id):
    try:
        dive_id = service.delete_comment(get_connection(), comment_id, current_user_id())
    except ValueError as e:
        flask.flash(str(e))
        return flask.redirect("/feed")
    return flask.redirect(f"/dives/{dive_id}")
