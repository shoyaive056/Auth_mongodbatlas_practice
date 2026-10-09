"""Refresh, email-verification and password-reset tokens.

Rule for all three: the raw token is returned to the caller (to be emailed or
put in a cookie) and ONLY its SHA-256 hash is stored in MongoDB.
"""
from datetime import timedelta

from bson import ObjectId
from pymongo.database import Database

from app.core.config import get_settings
from app.core.security import generate_token, hash_token
from app.models import password_reset_token as reset_model
from app.models import refresh_token as refresh_model
from app.models import verification_token as verify_model
from app.utils.errors import AppError
from app.utils.time import ensure_utc, utcnow

# ------------------------------------------------------------------ refresh
def create_refresh_token(db: Database, user_id: ObjectId) -> str:
    raw = generate_token()
    expires_at = utcnow() + timedelta(days=get_settings().refresh_token_expire_days)
    db[refresh_model.COLLECTION].insert_one(
        refresh_model.build_refresh_token_document(user_id, hash_token(raw), expires_at)
    )
    return raw


def rotate_refresh_token(db: Database, raw: str) -> tuple[ObjectId, str]:
    """Validate a refresh token, revoke it and issue a replacement (rotation)."""
    invalid = AppError(401, "INVALID_REFRESH_TOKEN", "Your session is no longer valid. Please log in again.")
    collection = db[refresh_model.COLLECTION]
    doc = collection.find_one({"token_hash": hash_token(raw)})
    if doc is None:
        raise invalid
    if doc["revoked"]:
        # A revoked token being used again suggests it was stolen: kill every session.
        revoke_all_user_tokens(db, doc["user_id"])
        raise invalid
    if ensure_utc(doc["expires_at"]) <= utcnow():
        raise invalid
    # Only one concurrent request can flip revoked False -> True.
    result = collection.update_one({"_id": doc["_id"], "revoked": False}, {"$set": {"revoked": True}})
    if result.modified_count != 1:
        raise invalid
    return doc["user_id"], create_refresh_token(db, doc["user_id"])


def revoke_refresh_token(db: Database, raw: str) -> None:
    db[refresh_model.COLLECTION].update_one({"token_hash": hash_token(raw)}, {"$set": {"revoked": True}})


def revoke_all_user_tokens(db: Database, user_id: ObjectId) -> None:
    db[refresh_model.COLLECTION].update_many({"user_id": user_id, "revoked": False}, {"$set": {"revoked": True}})


# ------------------------------------------------------- email verification
def create_email_verification_token(db: Database, user_id: ObjectId) -> str:
    collection = db[verify_model.COLLECTION]
    collection.delete_many({"user_id": user_id})  # only the newest link works
    raw = generate_token()
    expires_at = utcnow() + timedelta(minutes=get_settings().email_verification_expire_minutes)
    collection.insert_one(verify_model.build_verification_token_document(user_id, hash_token(raw), expires_at))
    return raw


def consume_email_verification_token(db: Database, raw: str) -> ObjectId:
    """Find + delete in one atomic step, so a token can only be used once."""
    doc = db[verify_model.COLLECTION].find_one_and_delete({"token_hash": hash_token(raw)})
    if doc is None:
        raise AppError(400, "INVALID_TOKEN", "This verification link is invalid or has already been used.")
    if ensure_utc(doc["expires_at"]) <= utcnow():
        raise AppError(400, "TOKEN_EXPIRED", "This verification link has expired. Please request a new one.")
    return doc["user_id"]


# ---------------------------------------------------------- password reset
def create_password_reset_token(db: Database, user_id: ObjectId) -> str:
    collection = db[reset_model.COLLECTION]
    collection.delete_many({"user_id": user_id})
    raw = generate_token()
    expires_at = utcnow() + timedelta(minutes=get_settings().password_reset_expire_minutes)
    collection.insert_one(reset_model.build_password_reset_document(user_id, hash_token(raw), expires_at))
    return raw


def consume_password_reset_token(db: Database, raw: str) -> ObjectId:
    """Atomically flip used False -> True, which makes the token single-use."""
    doc = db[reset_model.COLLECTION].find_one_and_update(
        {"token_hash": hash_token(raw), "used": False}, {"$set": {"used": True}}
    )
    if doc is None:
        raise AppError(400, "INVALID_TOKEN", "This reset link is invalid or has already been used.")
    if ensure_utc(doc["expires_at"]) <= utcnow():
        raise AppError(400, "TOKEN_EXPIRED", "This reset link has expired. Please request a new one.")
    return doc["user_id"]
