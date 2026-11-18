import functools

import flask
from werkzeug.security import generate_password_hash, check_password_hash

import db

bp = flask.Blueprint("users", __name__)


def create_user(conn, email, name, password):
    email = email.strip().lower()
    name = name.strip()

    if not email:
        raise ValueError("Email is required")
    if not name:
        raise ValueError("Name is required")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    existing = db.query_one(conn, "SELECT id FROM users WHERE email = %s", (email,))
    if existing is not None:
        raise ValueError("An account with this email already exists")

    password_hash = generate_password_hash(password)
    return db.insert(
        conn,
        "INSERT INTO users (email, name, password_hash) OUTPUT INSERTED.id VALUES (%s, %s, %s)",
        (email, name, password_hash),
    )


def authenticate(conn, email, password):
    email = email.strip().lower()
    row = db.query_one(
        conn, "SELECT id, email, name, password_hash FROM users WHERE email = %s", (email,)
    )
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
    row = db.query_one(conn, "SELECT id, email, name FROM users WHERE id = %s", (user_id,))
    if row is None:
        return None
    return {"id": row["id"], "email": row["email"], "name": row["name"]}


def get_user_name(conn, user_id):
    row = db.query_one(conn, "SELECT name FROM users WHERE id = %s", (user_id,))
    if row is None:
        return None
    return row["name"]


# --- Friends ---

def get_friendship(conn, user_id, other_id):
    """The friendships row between two users, whichever of them sent the request."""
    return db.query_one(
        conn,
        """
        SELECT * FROM friendships
        WHERE (requester_id = %s AND addressee_id = %s)
           OR (requester_id = %s AND addressee_id = %s)
        """,
        (user_id, other_id, other_id, user_id),
    )


def get_friend_status(conn, user_id, other_id):
    """Describe the link from user_id's point of view: none, sent, received or friends."""
    row = get_friendship(conn, user_id, other_id)
    if row is None:
        return "none"
    if row["status"] == "accepted":
        return "friends"
    if row["requester_id"] == user_id:
        return "sent"
    return "received"


def are_friends(conn, user_id, other_id):
    return get_friend_status(conn, user_id, other_id) == "friends"


def search_users(conn, user_id, query):
    """Other users whose name contains `query` (ignoring case), with their friend status."""
    if query is None or not query.strip():
        return []
    query = query.strip().lower()

    rows = db.query_all(conn, "SELECT id, name FROM users WHERE id != %s ORDER BY name", (user_id,))

    matches = []
    for row in rows:
        if query in row["name"].lower():
            matches.append({
                "id": row["id"],
                "name": row["name"],
                "status": get_friend_status(conn, user_id, row["id"]),
            })
    return matches


def send_friend_request(conn, user_id, other_id):
    if user_id == other_id:
        raise ValueError("You cannot add yourself as a friend")
    if get_user_name(conn, other_id) is None:
        raise ValueError("User not found")

    status = get_friend_status(conn, user_id, other_id)
    if status == "friends":
        raise ValueError("You are already friends")
    if status == "sent":
        raise ValueError("You already sent this person a request")
    if status == "received":
        raise ValueError("This person already sent you a request - accept it instead")

    db.execute(
        conn,
        "INSERT INTO friendships (requester_id, addressee_id, status) VALUES (%s, %s, 'pending')",
        (user_id, other_id),
    )


def accept_friend_request(conn, user_id, other_id):
    """user_id accepts the request that other_id sent them."""
    if get_friend_status(conn, user_id, other_id) != "received":
        raise ValueError("There is no friend request from this person")

    db.execute(
        conn,
        "UPDATE friendships SET status = 'accepted' WHERE requester_id = %s AND addressee_id = %s",
        (other_id, user_id),
    )


def remove_friend(conn, user_id, other_id):
    """Delete the link between two users. Used to decline, cancel a request, or unfriend."""
    row = get_friendship(conn, user_id, other_id)
    if row is None:
        raise ValueError("There is no friend request or friendship with this person")

    db.execute(conn, "DELETE FROM friendships WHERE id = %s", (row["id"],))


def list_friends(conn, user_id):
    rows = db.query_all(
        conn,
        """
        SELECT requester_id, addressee_id FROM friendships
        WHERE status = 'accepted' AND (requester_id = %s OR addressee_id = %s)
        """,
        (user_id, user_id),
    )

    friends = []
    for row in rows:
        # The friend is whichever side of the row is not me.
        if row["requester_id"] == user_id:
            friend_id = row["addressee_id"]
        else:
            friend_id = row["requester_id"]
        friends.append({"id": friend_id, "name": get_user_name(conn, friend_id)})

    friends.sort(key=lambda friend: friend["name"].lower())
    return friends


def list_incoming_requests(conn, user_id):
    return db.query_all(
        conn,
        """
        SELECT users.id, users.name FROM friendships
        JOIN users ON users.id = friendships.requester_id
        WHERE friendships.addressee_id = %s AND friendships.status = 'pending'
        ORDER BY users.name
        """,
        (user_id,),
    )


def list_outgoing_requests(conn, user_id):
    return db.query_all(
        conn,
        """
        SELECT users.id, users.name FROM friendships
        JOIN users ON users.id = friendships.addressee_id
        WHERE friendships.requester_id = %s AND friendships.status = 'pending'
        ORDER BY users.name
        """,
        (user_id,),
    )


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


def render_friends_page(error=None, status=200):
    conn = get_connection()
    user_id = flask.session["user_id"]
    return flask.render_template(
        "friends.html",
        error=error,
        friends=list_friends(conn, user_id),
        incoming=list_incoming_requests(conn, user_id),
        outgoing=list_outgoing_requests(conn, user_id),
    ), status


@bp.route("/friends", methods=["GET"])
@login_required
def friends_page():
    return render_friends_page()


@bp.route("/friends/search", methods=["GET"])
@login_required
def friends_search():
    # Returns only a piece of HTML. static/live_search.js puts it into the
    # friends page while the user types.
    query = flask.request.args.get("q", "")
    results = search_users(get_connection(), flask.session["user_id"], query)
    return flask.render_template("friends_search_results.html", results=results, query=query)


@bp.route("/friends/<int:other_id>/request", methods=["POST"])
@login_required
def friends_request(other_id):
    try:
        send_friend_request(get_connection(), flask.session["user_id"], other_id)
    except ValueError as e:
        return render_friends_page(error=str(e), status=400)
    return flask.redirect("/friends")


@bp.route("/friends/<int:other_id>/accept", methods=["POST"])
@login_required
def friends_accept(other_id):
    try:
        accept_friend_request(get_connection(), flask.session["user_id"], other_id)
    except ValueError as e:
        return render_friends_page(error=str(e), status=400)
    return flask.redirect("/friends")


@bp.route("/friends/<int:other_id>/remove", methods=["POST"])
@login_required
def friends_remove(other_id):
    try:
        remove_friend(get_connection(), flask.session["user_id"], other_id)
    except ValueError as e:
        return render_friends_page(error=str(e), status=400)
    return flask.redirect("/friends")
