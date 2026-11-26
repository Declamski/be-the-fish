import functools

import flask
import itsdangerous
from werkzeug.security import check_password_hash, generate_password_hash

import db

# JSON API for the static UI. Logged-in requests carry "Authorization: Bearer <token>".
api_bp = flask.Blueprint("users_api", __name__, url_prefix="/api")

# How long a login token works before the user has to log in again.
TOKEN_MAX_AGE_S = 7 * 24 * 60 * 60


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


# --- Login tokens (for the JSON API) ---

def get_token_serializer():
    """Signs and checks tokens with SECRET_KEY. The salt keeps these tokens separate
    from anything else signed with the same key."""
    return itsdangerous.URLSafeTimedSerializer(flask.current_app.config["SECRET_KEY"],
                                                salt="login-token")


def make_token(user_id):
    """A signed token holding the user id. Anyone can read it, nobody can change it."""
    return get_token_serializer().dumps({"user_id": user_id})


def read_token(token):
    """The user id in a token, or None if it was changed, is not a token, or is too old."""
    try:
        data = get_token_serializer().loads(token, max_age=TOKEN_MAX_AGE_S)
    except itsdangerous.BadSignature:
        # Also catches SignatureExpired (a token older than TOKEN_MAX_AGE_S).
        return None
    return data["user_id"]


def get_token_user_id():
    """The user id from the request's "Authorization: Bearer <token>" header, or None."""
    header = flask.request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    return read_token(header[len("Bearer "):])


def token_required(view_func):
    """For API routes: answer 401 unless the request has a valid token.
    The user id is put in flask.g.user_id for the route to use."""
    @functools.wraps(view_func)
    def wrapped_view(*args, **kwargs):
        user_id = get_token_user_id()
        if user_id is None:
            return flask.jsonify({"error": "Log in first"}), 401
        flask.g.user_id = user_id
        return view_func(*args, **kwargs)
    return wrapped_view


# --- JSON API ---

def read_json():
    """The request's JSON body as a dict ({} if there is none)."""
    data = flask.request.get_json(silent=True)
    if not isinstance(data, dict):
        return {}
    return data


def get_user(conn, user_id):
    return db.query_one(conn, "SELECT id, email, name FROM users WHERE id = %s", (user_id,))


@api_bp.route("/signup", methods=["POST"])
def api_signup():
    data = read_json()
    conn = get_connection()
    try:
        user_id = create_user(conn, data.get("email", ""), data.get("name", ""),
                              data.get("password", ""))
    except ValueError as e:
        return flask.jsonify({"error": str(e)}), 400
    return flask.jsonify({"token": make_token(user_id), "user": get_user(conn, user_id)}), 201


@api_bp.route("/login", methods=["POST"])
def api_login():
    data = read_json()
    user = authenticate(get_connection(), data.get("email", ""), data.get("password", ""))
    if user is None:
        return flask.jsonify({"error": "Invalid email or password"}), 401
    return flask.jsonify({"token": make_token(user["id"]), "user": user})


@api_bp.route("/me", methods=["GET"])
@token_required
def api_me():
    user = get_user(get_connection(), flask.g.user_id)
    if user is None:
        return flask.jsonify({"error": "Log in first"}), 401
    return flask.jsonify(user)


@api_bp.route("/friends", methods=["GET"])
@token_required
def api_friends():
    conn = get_connection()
    return flask.jsonify({
        "friends": list_friends(conn, flask.g.user_id),
        "incoming": list_incoming_requests(conn, flask.g.user_id),
        "outgoing": list_outgoing_requests(conn, flask.g.user_id),
    })


@api_bp.route("/friends/search", methods=["GET"])
@token_required
def api_friends_search():
    query = flask.request.args.get("q", "")
    return flask.jsonify(search_users(get_connection(), flask.g.user_id, query))


@api_bp.route("/friends/<int:other_id>/request", methods=["POST"])
@token_required
def api_friends_request(other_id):
    try:
        send_friend_request(get_connection(), flask.g.user_id, other_id)
    except ValueError as e:
        return flask.jsonify({"error": str(e)}), 400
    return flask.jsonify({"status": "sent"}), 201


@api_bp.route("/friends/<int:other_id>/accept", methods=["POST"])
@token_required
def api_friends_accept(other_id):
    try:
        accept_friend_request(get_connection(), flask.g.user_id, other_id)
    except ValueError as e:
        return flask.jsonify({"error": str(e)}), 400
    return flask.jsonify({"status": "friends"})


@api_bp.route("/friends/<int:other_id>", methods=["DELETE"])
@token_required
def api_friends_remove(other_id):
    try:
        remove_friend(get_connection(), flask.g.user_id, other_id)
    except ValueError as e:
        return flask.jsonify({"error": str(e)}), 400
    return flask.jsonify({"status": "removed"})
