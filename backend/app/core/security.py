"""Password hashing, JWT access tokens and random one-time tokens."""
import hashlib
import secrets
import uuid
from datetime import timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings
from app.utils.errors import AppError
from app.utils.time import utcnow

# --- Passwords -------------------------------------------------------------
# argon2-cffi's PasswordHasher uses Argon2id with safe default parameters.
_hasher = PasswordHasher()

# Verified against when the email does not exist, so login takes similar time either way.
DUMMY_HASH = _hasher.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


# --- Random tokens (refresh / email verification / password reset) ----------
def generate_token() -> str:
    """256 bits of randomness. This raw value goes to the user, never to the database."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 is fine because the token is already high-entropy random data.
    The database only ever stores this hash."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# --- JWT access tokens ------------------------------------------------------
_BEARER = {"WWW-Authenticate": "Bearer"}


def create_access_token(user_id: str, role: str) -> tuple[str, int]:
    settings = get_settings()
    now = utcnow()
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + expires_delta,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],  # never trust the algorithm named inside the token
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise AppError(401, "TOKEN_EXPIRED", "Your session has expired. Please refresh or log in again.",
                       headers=_BEARER)
    except jwt.InvalidTokenError:
        raise AppError(401, "INVALID_TOKEN", "Invalid authentication token.", headers=_BEARER)
    if payload.get("type") != "access":
        raise AppError(401, "INVALID_TOKEN", "Invalid authentication token.", headers=_BEARER)
    return payload
