import flask
from config import load_config
from db import init_db


def create_app(config=None):
    app = flask.Flask(__name__)

    if config is None:
        config = load_config()

    app.config["DATA_DIR"] = config["DATA_DIR"]

    init_db(app.config["DATA_DIR"])

    return app


if __name__ == "__main__":
    config = load_config()
    app = create_app(config)
    app.run(host="0.0.0.0", port=config["PORT"], debug=False, use_reloader=False)
