import flask
from config import load_config
from db import init_db, get_connection
import users
import dives
import sites


def create_app(config=None):
    app = flask.Flask(__name__)

    if config is None:
        config = load_config()

    app.config["DATA_DIR"] = config["DATA_DIR"]
    app.config["SECRET_KEY"] = config["SECRET_KEY"]

    init_db(app.config["DATA_DIR"])

    @app.before_request
    def open_db_connection():
        flask.g.db = get_connection(app.config["DATA_DIR"])

    @app.teardown_request
    def close_db_connection(exception):
        db = getattr(flask.g, "db", None)
        if db is not None:
            db.close()

    app.register_blueprint(users.bp)
    app.register_blueprint(dives.bp)
    app.register_blueprint(sites.bp)

    @app.route("/")
    def index():
        user = users.get_current_user(flask.g.db)
        return flask.render_template("index.html", user=user)

    return app


if __name__ == "__main__":
    config = load_config()
    app = create_app(config)
    app.run(host="0.0.0.0", port=config["PORT"], debug=False, use_reloader=False)
