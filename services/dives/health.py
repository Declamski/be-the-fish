"""GET /health: is this service able to use its own database right now?

It checks only this service's own database, never the other service.
"""
import flask
import pymssql

import db

bp = flask.Blueprint("health", __name__)


def check_database(database_url):
    """True if we can write to and then read from our own database right now."""
    try:
        conn = db.connect_once(database_url)
    except pymssql.Error:
        return False
    try:
        db.execute(conn, "UPDATE health_check SET checked_at = SYSUTCDATETIME() WHERE id = 1")
        row = db.query_one(conn, "SELECT checked_at FROM health_check WHERE id = 1")
        return row is not None
    except pymssql.Error:
        return False
    finally:
        conn.close()


@bp.route("/health", methods=["GET"])
def health():
    version = flask.current_app.config["VERSION"]
    if check_database(flask.current_app.config["DATABASE_URL"]):
        return flask.jsonify({"status": "ok", "db": "ok", "version": version}), 200
    return flask.jsonify({"status": "error", "db": "error", "version": version}), 503
