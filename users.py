import functools

import flask
from werkzeug.security import generate_password_hash, check_password_hash

bp = flask.Blueprint("users", __name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL
);
"""


def init_db(conn):
    conn.execute(SCHEMA_SQL)
    conn.commit()


def create_user(conn, email, name, password):
    email = email.strip().lower()
    name = name.strip()

    if not email:
        raise ValueError("Email is required")
    if not name:
        raise ValueError("Name is required")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    existing = conn.execute(
        "SELECT id FROM users WHERE email = ?", (email,)
    ).fetchone()
    if existing is not None:
        raise ValueError("An account with this email already exists")

    password_hash = generate_password_hash(password)
    cursor = conn.execute(
        "INSERT INTO users (email, name, password_hash) VALUES (?, ?, ?)",
        (email, name, password_hash),
    )
    conn.commit()
    return cursor.lastrowid


def authenticate(conn, email, password):
    email = email.strip().lower()
    row = conn.execute(
        "SELECT id, email, name, password_hash FROM users WHERE email = ?", (email,)
    ).fetchone()
    if row is None:
        return None
    if not check_password_hash(row["password_hash"], password):
        return None
    return {"id": row["id"], "email": row["email"], "name": row["name"]}


def get_connection():
    return flask.g.db


def get_current_user(conn):
    user_id = flask.session.get("user_id")
    if user_id is None:
        return None
    row = conn.execute(
        "SELECT id, email, name FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if row is None:
        return None
    return {"id": row["id"], "email": row["email"], "name": row["name"]}


def login_required(view_func):
    @functools.wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if flask.session.get("user_id") is None:
            return flask.redirect("/login")
        return view_func(*args, **kwargs)
    return wrapped_view


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if flask.request.method == "GET":
        return flask.render_template("signup.html")

    email = flask.request.form.get("email", "")
    name = flask.request.form.get("name", "")
    password = flask.request.form.get("password", "")

    try:
        user_id = create_user(get_connection(), email, name, password)
    except ValueError as e:
        return flask.render_template("signup.html", error=str(e)), 400

    flask.session["user_id"] = user_id
    return flask.redirect("/")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if flask.request.method == "GET":
        return flask.render_template("login.html")

    email = flask.request.form.get("email", "")
    password = flask.request.form.get("password", "")

    user = authenticate(get_connection(), email, password)
    if user is None:
        return flask.render_template("login.html", error="Invalid email or password"), 400

    flask.session["user_id"] = user["id"]
    return flask.redirect("/")


@bp.route("/logout", methods=["POST"])
def logout():
    flask.session.pop("user_id", None)
    return flask.redirect("/login")
