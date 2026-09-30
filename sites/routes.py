import flask

import users
from . import service

bp = flask.Blueprint("sites", __name__, url_prefix="/sites")


def get_connection():
    return flask.g.db


@bp.route("", methods=["GET"])
@users.login_required
def list_sites():
    # The page filters as you type with static/filter.js. The ?q= search is
    # what runs if the form is submitted (Enter, or JavaScript turned off).
    query = flask.request.args.get("q", "")
    sites = service.search_sites(get_connection(), query)
    return flask.render_template("sites/list.html", sites=sites, query=query)


@bp.route("/<int:site_id>", methods=["GET"])
@users.login_required
def site_detail(site_id):
    try:
        site = service.get_site(get_connection(), site_id)
    except ValueError as e:
        return flask.render_template("sites/list.html", sites=[], query="", error=str(e)), 404
    return flask.render_template("sites/detail.html", site=site)
