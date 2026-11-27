"""JSON API for the feed, kudos and comments, used by the static UI.
Every route needs a login token. A ValueError from the service becomes a 400."""
import datetime

import flask

import users

from . import service

api_bp = flask.Blueprint("feed_api", __name__, url_prefix="/api/feed")


def get_connection():
    return flask.g.db


def error(message, status=400):
    return flask.jsonify({"error": message}), status


@api_bp.route("", methods=["GET"])
@users.token_required
def api_feed():
    """One page of the feed. ?offset= says where to start (the previous next_offset)."""
    try:
        offset = int(flask.request.args.get("offset", 0))
    except ValueError:
        offset = 0
    return flask.jsonify(service.get_feed_page(get_connection(), flask.g.user_id, offset))


@api_bp.route("/dives/<int:dive_id>/social", methods=["GET"])
@users.token_required
def api_dive_social(dive_id):
    try:
        social = service.get_dive_social(get_connection(), dive_id, flask.g.user_id)
    except ValueError as e:
        return error(str(e), 404)
    return flask.jsonify(social)


@api_bp.route("/dives/<int:dive_id>/kudos", methods=["POST"])
@users.token_required
def api_give_kudos(dive_id):
    try:
        service.give_kudos(get_connection(), dive_id, flask.g.user_id)
    except ValueError as e:
        return error(str(e))
    return flask.jsonify({"dive_id": dive_id}), 201


@api_bp.route("/dives/<int:dive_id>/kudos", methods=["DELETE"])
@users.token_required
def api_remove_kudos(dive_id):
    try:
        service.remove_kudos(get_connection(), dive_id, flask.g.user_id)
    except ValueError as e:
        return error(str(e))
    return flask.jsonify({"dive_id": dive_id})


@api_bp.route("/dives/<int:dive_id>/comments", methods=["POST"])
@users.token_required
def api_add_comment(dive_id):
    data = flask.request.get_json(silent=True)
    body = ""
    if isinstance(data, dict):
        body = data.get("body", "")
    try:
        comment_id = service.add_comment(get_connection(), dive_id, flask.g.user_id, body,
                                         now=datetime.datetime.now())
    except ValueError as e:
        return error(str(e))
    return flask.jsonify({"id": comment_id}), 201


@api_bp.route("/comments/<int:comment_id>", methods=["DELETE"])
@users.token_required
def api_delete_comment(comment_id):
    try:
        dive_id = service.delete_comment(get_connection(), comment_id, flask.g.user_id)
    except ValueError as e:
        return error(str(e))
    return flask.jsonify({"dive_id": dive_id})
