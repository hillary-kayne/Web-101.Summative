from datetime import datetime, timedelta, timezone
from functools import wraps

import bcrypt
import jwt
from flask import g, request

from config import config
from errors import ApiError


def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password, password_hash):
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def issue_token(user_id, username):
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=config.JWT_EXP_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, config.SESSION_SECRET, algorithm="HS256")


def decode_token(token):
    return jwt.decode(token, config.SESSION_SECRET, algorithms=["HS256"])


def require_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            raise ApiError("Missing or invalid Authorization header", 401)
        token = header[len("Bearer "):]
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            raise ApiError("Token expired", 401)
        except jwt.InvalidTokenError:
            raise ApiError("Invalid token", 401)
        g.user_id = int(payload["sub"])
        g.username = payload["username"]
        return view(*args, **kwargs)

    return wrapped
