import logging
import time

import flask
from config import load_config
import db
import migrate
import health
import sites


def create_app(config=None):
    app = flask.Flask(__name__)

    if config is None:
        config = load_config()

    app.config["VERSION"] = config["VERSION"]
    app.config["DATABASE_URL"] = config["DATABASE_URL"]

    # On startup: bring the schema up to date, then add any missing seed sites.
    conn = db.get_connection(app.config["DATABASE_URL"])
    migrate.apply_migrations(conn)
    sites.seed_sites(conn)
    conn.close()

    # Our own one-line request log replaces Flask's built-in one.
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    @app.before_request
    def start_request():
        flask.g.start_time = time.perf_counter()
        # /health opens its own quick connection (health.py), so it can answer 503 fast.
        if flask.request.endpoint == "health.health":
            return
        flask.g.db = db.get_connection(app.config["DATABASE_URL"])

    @app.after_request
    def log_request(response):
        """One line per request on stdout: method, path, status, duration."""
        duration_ms = (time.perf_counter() - flask.g.start_time) * 1000
        print(flask.request.method, flask.request.path, response.status_code,
              f"{duration_ms:.1f}ms", flush=True)
        return response

    @app.teardown_request
    def close_db_connection(exception):
        conn = getattr(flask.g, "db", None)
        if conn is not None:
            conn.close()

    app.register_blueprint(health.bp)
    app.register_blueprint(sites.bp)
    app.register_blueprint(sites.api_bp)

    @app.route("/")
    def index():
        return flask.redirect("/sites")

    return app


if __name__ == "__main__":
    config = load_config()
    app = create_app(config)
    print("Starting on port", config["PORT"], "version", config["VERSION"], flush=True)
    app.run(host="0.0.0.0", port=config["PORT"], debug=False, use_reloader=False)
