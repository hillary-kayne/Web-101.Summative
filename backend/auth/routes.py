import psycopg2.errors
from flask import Blueprint, jsonify, request

from auth.service import hash_password, issue_token, verify_password
from db import get_cursor
from errors import ApiError

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _validate_credentials(data):
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if len(username) < 3 or len(username) > 50:
        raise ApiError("Username must be 3-50 characters", 400)
    if len(password) < 6:
        raise ApiError("Password must be at least 6 characters", 400)
    return username, password


@bp.post("/signup")
def signup():
    data = request.get_json(silent=True) or {}
    username, password = _validate_credentials(data)
    password_hash = hash_password(password)
    try:
        with get_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id",
                (username, password_hash),
            )
            user_id = cur.fetchone()["id"]
    except psycopg2.errors.UniqueViolation:
        raise ApiError("Username already taken", 400)
    token = issue_token(user_id, username)
    return jsonify({"token": token, "username": username}), 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    with get_cursor() as cur:
        cur.execute("SELECT id, username, password_hash FROM users WHERE username = %s", (username,))
        row = cur.fetchone()
    if not row or not verify_password(password, row["password_hash"]):
        raise ApiError("Invalid username or password", 401)
    token = issue_token(row["id"], row["username"])
    return jsonify({"token": token, "username": row["username"]}), 200
