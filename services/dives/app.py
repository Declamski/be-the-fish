import logging
import time

import flask
from config import load_config
import db
import migrate
import health
import users
import dives
import feed


def create_app(config=None):
    app = flask.Flask(__name__)

    if config is None:
        config = load_config()

    app.config["VERSION"] = config["VERSION"]
    app.config["CORS_ORIGIN"] = config["CORS_ORIGIN"]
    app.config["DATABASE_URL"] = config["DATABASE_URL"]
    app.config["SECRET_KEY"] = config["SECRET_KEY"]
    app.config["SITES_URL"] = config["SITES_URL"]
    app.config["SITES_TIMEOUT_S"] = config["SITES_TIMEOUT_S"]

    # On startup: bring the schema up to date.
    conn = db.get_connection(app.config["DATABASE_URL"])
    migrate.apply_migrations(conn)
    conn.close()

    # Our own one-line request log replaces Flask's built-in one.
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    @app.before_request
    def start_request():
        flask.g.start_time = time.perf_counter()
        # /health opens its own quick connection (health.py), so it can answer 503 fast.
        # / does not use the database at all.
        if flask.request.endpoint in ("health.health", "index"):
            return
        flask.g.db = db.get_connection(app.config["DATABASE_URL"])

    @app.after_request
    def log_request(response):
        """One line per request on stdout: method, path, status, duration."""
        duration_ms = (time.perf_counter() - flask.g.start_time) * 1000
        print(flask.request.method, flask.request.path, response.status_code,
              f"{duration_ms:.1f}ms", flush=True)
        return response

    @app.after_request
    def add_cors_headers(response):
        """Let the UI, which runs on another address (CORS_ORIGIN), call this service
        from the browser. Any other website is still blocked by the browser."""
        response.headers["Access-Control-Allow-Origin"] = app.config["CORS_ORIGIN"]
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return response

    @app.teardown_request
    def close_db_connection(exception):
        conn = getattr(flask.g, "db", None)
        if conn is not None:
            conn.close()

    app.register_blueprint(health.bp)
    app.register_blueprint(users.api_bp)
    app.register_blueprint(dives.api_bp)
    app.register_blueprint(feed.api_bp)

    @app.route("/")
    def index():
        """Someone opening the service's address in a browser sees which service and
        which build this is. The real pages are the static UI."""
        return flask.jsonify({"service": "dives", "version": app.config["VERSION"]})

    return app


if __name__ == "__main__":
    config = load_config()
    app = create_app(config)
    print("Starting on port", config["PORT"], "version", config["VERSION"], flush=True)
    app.run(host="0.0.0.0", port=config["PORT"], debug=False, use_reloader=False)
