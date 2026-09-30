import io

import flask

import users
from . import importer, service

bp = flask.Blueprint("dives", __name__, url_prefix="/dives")


def get_connection():
    return flask.g.db


def current_user_id():
    return flask.session["user_id"]


def render_new_form(error=None, status=200):
    """Show the new-dive form, with the site dropdown and condition levels filled in."""
    return flask.render_template(
        "dives/new.html",
        error=error,
        site_choices=service.get_site_choices(get_connection()),
        visibility_levels=service.VALID_VISIBILITY,
        current_levels=service.VALID_CURRENT,
    ), status


def render_detail(dive_id, error=None, status=200):
    """Show a dive's page, including the form to set its site and conditions."""
    try:
        detail = service.get_dive_detail(get_connection(), dive_id, current_user_id())
    except ValueError as e:
        return flask.render_template("dives/list.html", dives=[], error=str(e)), 404
    return flask.render_template(
        "dives/detail.html",
        error=error,
        site_choices=service.get_site_choices(get_connection()),
        visibility_levels=service.VALID_VISIBILITY,
        current_levels=service.VALID_CURRENT,
        **detail,
    ), status


@bp.route("/new", methods=["GET", "POST"])
@users.login_required
def new_dive():
    if flask.request.method == "GET":
        return render_new_form()

    conn = get_connection()
    discipline = flask.request.form.get("discipline", "")
    started_at = flask.request.form.get("started_at", "")
    site_id = flask.request.form.get("site_id") or None
    notes = flask.request.form.get("notes") or None
    visibility = flask.request.form.get("visibility") or None
    current = flask.request.form.get("current") or None

    if discipline == "scuba":
        max_depth_m = flask.request.form.get("max_depth_m") or None
        duration_s = flask.request.form.get("duration_s") or None
        water_temp_c = flask.request.form.get("water_temp_c") or None
        try:
            dive_id = service.create_scuba_dive(
                conn,
                user_id=current_user_id(),
                started_at=started_at,
                max_depth_m=float(max_depth_m) if max_depth_m else None,
                duration_s=int(duration_s) if duration_s else None,
                site_id=int(site_id) if site_id else None,
                water_temp_c=float(water_temp_c) if water_temp_c else None,
                visibility=visibility,
                current=current,
                notes=notes,
            )
        except ValueError as e:
            return render_new_form(error=str(e), status=400)
        return flask.redirect(f"/dives/{dive_id}")

    try:
        draft = service.start_session_draft(
            discipline=discipline,
            started_at=started_at,
            site_id=int(site_id) if site_id else None,
            visibility=visibility,
            current=current,
            notes=notes,
        )
    except ValueError as e:
        return render_new_form(error=str(e), status=400)

    flask.session["draft_dive"] = draft
    return flask.redirect("/dives/new/descents")


@bp.route("/new/descents", methods=["GET", "POST"])
@users.login_required
def new_descent():
    draft = flask.session.get("draft_dive")
    if draft is None:
        return flask.redirect("/dives/new")

    if flask.request.method == "GET":
        return flask.render_template("dives/descents.html", draft=draft)

    depth_m = flask.request.form.get("depth_m") or None
    duration_s = flask.request.form.get("duration_s") or None

    try:
        draft = service.add_descent_to_draft(
            draft,
            depth_m=float(depth_m) if depth_m else None,
            duration_s=int(duration_s) if duration_s else None,
        )
    except ValueError as e:
        return flask.render_template("dives/descents.html", draft=draft, error=str(e)), 400

    flask.session["draft_dive"] = draft
    return flask.redirect("/dives/new/descents")


@bp.route("/new/finish", methods=["POST"])
@users.login_required
def finish_dive():
    draft = flask.session.get("draft_dive")
    if draft is None:
        return flask.redirect("/dives/new")

    try:
        dive_id = service.finish_session(get_connection(), current_user_id(), draft)
    except ValueError as e:
        return flask.render_template("dives/descents.html", draft=draft, error=str(e)), 400

    flask.session.pop("draft_dive", None)
    return flask.redirect(f"/dives/{dive_id}")


@bp.route("/import", methods=["GET", "POST"])
@users.login_required
def import_dives():
    if flask.request.method == "GET":
        return flask.render_template("dives/import.html")

    upload = flask.request.files.get("file")
    if upload is None or not upload.filename:
        return flask.render_template("dives/import.html", error="Choose a file first"), 400

    filename = upload.filename.lower()
    if filename.endswith(".fit"):
        return flask.render_template("dives/import.html", error=(
            "FIT files are not read directly. Open the .fit file in Subsurface, "
            "then export it as CSV and upload that."
        )), 400
    if not filename.endswith(".csv"):
        return flask.render_template("dives/import.html", error="Only .csv files can be imported"), 400

    discipline_override = flask.request.form.get("discipline_override") or None
    text_stream = io.TextIOWrapper(upload.stream, encoding="utf-8", newline="")

    try:
        summary = importer.import_csv_stream(
            get_connection(),
            user_id=current_user_id(),
            text_stream=text_stream,
            discipline_override=discipline_override,
        )
    except ValueError as e:
        return flask.render_template("dives/import.html", error=str(e)), 400
    except UnicodeDecodeError:
        return flask.render_template("dives/import.html", error="That file is not readable text"), 400

    return flask.render_template("dives/import.html", summary=summary)


@bp.route("", methods=["GET"])
@users.login_required
def list_dives():
    dives = service.list_dives(get_connection(), current_user_id())
    return flask.render_template("dives/list.html", dives=dives)


@bp.route("/<int:dive_id>", methods=["GET"])
@users.login_required
def dive_detail(dive_id):
    return render_detail(dive_id)


@bp.route("/<int:dive_id>/site", methods=["POST"])
@users.login_required
def set_site_and_conditions(dive_id):
    site_id = flask.request.form.get("site_id") or None
    visibility = flask.request.form.get("visibility") or None
    current = flask.request.form.get("current") or None

    try:
        service.set_dive_site_and_conditions(
            get_connection(),
            dive_id=dive_id,
            user_id=current_user_id(),
            site_id=int(site_id) if site_id else None,
            visibility=visibility,
            current=current,
        )
    except ValueError as e:
        return render_detail(dive_id, error=str(e), status=400)

    return flask.redirect(f"/dives/{dive_id}")


@bp.route("/<int:dive_id>/catches", methods=["POST"])
@users.login_required
def add_catch(dive_id):
    species = flask.request.form.get("species", "")
    weight_kg = flask.request.form.get("weight_kg") or None

    try:
        service.add_catch(
            get_connection(),
            dive_id=dive_id,
            user_id=current_user_id(),
            species=species,
            weight_kg=float(weight_kg) if weight_kg else None,
        )
    except ValueError as e:
        return render_detail(dive_id, error=str(e), status=400)

    return flask.redirect(f"/dives/{dive_id}")
