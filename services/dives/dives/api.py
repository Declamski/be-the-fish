"""JSON API for dives, used by the static UI. Every route needs a login token.

Same rules as routes.py: read the request, call service.py, answer. A ValueError
from the service becomes a 400 with {"error": "..."}.
"""
import io

import flask

import users

from . import importer, service

api_bp = flask.Blueprint("dives_api", __name__, url_prefix="/api/dives")


def get_connection():
    return flask.g.db


def read_json():
    """The request's JSON body as a dict ({} if there is none)."""
    data = flask.request.get_json(silent=True)
    if not isinstance(data, dict):
        return {}
    return data


def optional_number(data, key, kind):
    """data[key] as a float or int, or None if it is missing or empty.
    Raises ValueError with a clear message if it is not a number."""
    value = data.get(key)
    if value is None or value == "":
        return None
    try:
        return kind(value)
    except (TypeError, ValueError):
        raise ValueError(key + " must be a number")


def error(message, status=400):
    return flask.jsonify({"error": message}), status


@api_bp.route("/options", methods=["GET"])
@users.token_required
def api_options():
    """The allowed values for the dive form's dropdowns. Sites come from the sites service."""
    return flask.jsonify({
        "disciplines": sorted(service.VALID_DISCIPLINES),
        "visibility_levels": service.VALID_VISIBILITY,
        "current_levels": service.VALID_CURRENT,
        "audiences": service.VALID_AUDIENCES,
    })


@api_bp.route("", methods=["GET"])
@users.token_required
def api_list_dives():
    return flask.jsonify(service.list_dives(get_connection(), flask.g.user_id))


@api_bp.route("", methods=["POST"])
@users.token_required
def api_create_dive():
    """Scuba: one dive with max_depth_m and duration_s.
    Freedive/spearfishing: a session with a "descents" list, saved all at once."""
    data = read_json()
    conn = get_connection()
    discipline = data.get("discipline", "")
    try:
        site_id = optional_number(data, "site_id", int)
        if discipline == "scuba":
            dive_id = service.create_scuba_dive(
                conn,
                user_id=flask.g.user_id,
                started_at=data.get("started_at", ""),
                max_depth_m=optional_number(data, "max_depth_m", float),
                duration_s=optional_number(data, "duration_s", int),
                site_id=site_id,
                water_temp_c=optional_number(data, "water_temp_c", float),
                visibility=data.get("visibility") or None,
                current=data.get("current") or None,
                audience=data.get("audience", "private"),
                notes=data.get("notes") or None,
            )
        else:
            # The same steps the page version does one at a time: start, add descents, finish.
            draft = service.start_session_draft(
                discipline=discipline,
                started_at=data.get("started_at", ""),
                site_id=site_id,
                visibility=data.get("visibility") or None,
                current=data.get("current") or None,
                audience=data.get("audience", "private"),
                notes=data.get("notes") or None,
            )
            for descent in data.get("descents") or []:
                draft = service.add_descent_to_draft(
                    draft,
                    depth_m=optional_number(descent, "depth_m", float),
                    duration_s=optional_number(descent, "duration_s", int),
                )
            dive_id = service.finish_session(conn, flask.g.user_id, draft)
    except ValueError as e:
        return error(str(e))
    return flask.jsonify({"id": dive_id}), 201


@api_bp.route("/<int:dive_id>", methods=["GET"])
@users.token_required
def api_dive_detail(dive_id):
    try:
        detail = service.get_dive_detail(get_connection(), dive_id, flask.g.user_id)
    except ValueError as e:
        return error(str(e), 404)
    return flask.jsonify(detail)


@api_bp.route("/<int:dive_id>/site", methods=["PUT"])
@users.token_required
def api_set_site_and_conditions(dive_id):
    data = read_json()
    try:
        service.set_dive_site_and_conditions(
            get_connection(), dive_id, flask.g.user_id,
            site_id=optional_number(data, "site_id", int),
            visibility=data.get("visibility") or None,
            current=data.get("current") or None,
        )
    except ValueError as e:
        return error(str(e))
    return flask.jsonify({"id": dive_id})


@api_bp.route("/<int:dive_id>/audience", methods=["PUT"])
@users.token_required
def api_set_audience(dive_id):
    data = read_json()
    try:
        service.set_dive_audience(get_connection(), dive_id, flask.g.user_id,
                                  data.get("audience", ""))
    except ValueError as e:
        return error(str(e))
    return flask.jsonify({"id": dive_id})


@api_bp.route("/<int:dive_id>/catches", methods=["POST"])
@users.token_required
def api_add_catch(dive_id):
    data = read_json()
    try:
        catch_id = service.add_catch(
            get_connection(), dive_id=dive_id, user_id=flask.g.user_id,
            species=data.get("species", ""),
            weight_kg=optional_number(data, "weight_kg", float),
        )
    except ValueError as e:
        return error(str(e))
    return flask.jsonify({"id": catch_id}), 201


@api_bp.route("/import", methods=["POST"])
@users.token_required
def api_import_dives():
    """A Subsurface CSV sent as a file upload (multipart form, field "file")."""
    upload = flask.request.files.get("file")
    if upload is None or not upload.filename:
        return error("Choose a file first")
    if not upload.filename.lower().endswith(".csv"):
        return error("Only .csv files can be imported. Export .fit files from Subsurface as CSV.")

    text_stream = io.TextIOWrapper(upload.stream, encoding="utf-8", newline="")
    try:
        summary = importer.import_csv_stream(
            get_connection(),
            user_id=flask.g.user_id,
            text_stream=text_stream,
            discipline_override=flask.request.form.get("discipline_override") or None,
        )
    except ValueError as e:
        return error(str(e))
    except UnicodeDecodeError:
        return error("That file is not readable text")
    return flask.jsonify(summary)
