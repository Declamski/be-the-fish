import flask
from config import load_config
import db
import migrate
import sites


def create_app(config=None):
    app = flask.Flask(__name__)

    if config is None:
        config = load_config()

    app.config["DATABASE_URL"] = config["DATABASE_URL"]

    # On startup: bring the schema up to date, then add any missing seed sites.
    conn = db.get_connection(app.config["DATABASE_URL"])
    migrate.apply_migrations(conn)
    sites.seed_sites(conn)
    conn.close()

    @app.before_request
    def open_db_connection():
        flask.g.db = db.get_connection(app.config["DATABASE_URL"])

    @app.teardown_request
    def close_db_connection(exception):
        conn = getattr(flask.g, "db", None)
        if conn is not None:
            conn.close()

    app.register_blueprint(sites.bp)
    app.register_blueprint(sites.api_bp)

    @app.route("/")
    def index():
        return flask.redirect("/sites")

    return app


if __name__ == "__main__":
    config = load_config()
    app = create_app(config)
    app.run(host="0.0.0.0", port=config["PORT"], debug=False, use_reloader=False)
