import flask

from . import service

bp = flask.Blueprint("sites", __name__, url_prefix="/sites")
# JSON for the dives service (the seam). Same service functions, no HTML.
api_bp = flask.Blueprint("sites_api", __name__, url_prefix="/api/sites")


def get_connection():
    return flask.g.db


@bp.route("", methods=["GET"])
def list_sites():
    # The page filters as you type with static/filter.js. The ?q= search is
    # what runs if the form is submitted (Enter, or JavaScript turned off).
    query = flask.request.args.get("q", "")
    sites = service.search_sites(get_connection(), query)
    return flask.render_template("sites/list.html", sites=sites, query=query)


@bp.route("/<int:site_id>", methods=["GET"])
def site_detail(site_id):
    try:
        site = service.get_site(get_connection(), site_id)
    except ValueError as e:
        return flask.render_template("sites/list.html", sites=[], query="", error=str(e)), 404
    return flask.render_template("sites/detail.html", site=site)


@api_bp.route("", methods=["GET"])
def api_list_sites():
    query = flask.request.args.get("q", "")
    sites = service.search_sites(get_connection(), query)
    result = []
    for site in sites:
        result.append(service.site_to_dict(site))
    return flask.jsonify(result)


@api_bp.route("/<int:site_id>", methods=["GET"])
def api_get_site(site_id):
    try:
        site = service.get_site(get_connection(), site_id)
    except ValueError as e:
        return flask.jsonify({"error": str(e)}), 404
    return flask.jsonify(service.site_to_dict(site))
