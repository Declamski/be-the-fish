"""JSON API for the dive site catalogue, called by the dives service (the seam) and the UI."""
import flask

from . import service

api_bp = flask.Blueprint("sites_api", __name__, url_prefix="/api/sites")


def get_connection():
    return flask.g.db


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
