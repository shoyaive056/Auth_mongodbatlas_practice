"""The authentication use-cases. Routes stay thin and call these functions."""
from fastapi import BackgroundTasks
from pymongo.database import Database

from app.core.security import (
    DUMMY_HASH,
    create_access_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)
from app.models.user import COLLECTION as USERS
from app.schemas.auth import RegisterRequest
from app.services import email_service, token_service, user_service
from app.utils.errors import AppError
from app.utils.time import utcnow


def register(db: Database, data: RegisterRequest, background: BackgroundTasks) -> dict:
    user = user_service.create_user(db, data)
    raw_token = token_service.create_email_verification_token(db, user["_id"])
    background.add_task(email_service.send_verification_email, user["email"], user["first_name"], raw_token)
    return user


def login(db: Database, email: str, password: str) -> tuple[dict, str, int, str]:
    user = user_service.get_by_email(db, email)
    if user is None:
        verify_password(password, DUMMY_HASH)  # keep timing similar to a real check
        raise AppError(401, "INVALID_CREDENTIALS", "Invalid email or password.")
    # Check the password FIRST, so account status is only revealed to the real owner.
    if not verify_password(password, user["password_hash"]):
        raise AppError(401, "INVALID_CREDENTIALS", "Invalid email or password.")
    if not user["is_active"]:
        raise AppError(403, "ACCOUNT_INACTIVE", "This account has been deactivated. Please contact support.")
    if not user["is_verified"]:
        raise AppError(403, "EMAIL_NOT_VERIFIED", "Please verify your email address before logging in.")

    updates = {"last_login": utcnow()}
    if password_needs_rehash(user["password_hash"]):
        updates["password_hash"] = hash_password(password)
    db[USERS].update_one({"_id": user["_id"]}, {"$set": updates})
    user = {**user, **updates}

    access_token, expires_in = create_access_token(str(user["_id"]), user["role"])
    refresh_token = token_service.create_refresh_token(db, user["_id"])
    return user, access_token, expires_in, refresh_token


def refresh_session(db: Database, raw_refresh_token: str | None) -> tuple[dict, str, int, str]:
    if not raw_refresh_token:
        raise AppError(401, "INVALID_REFRESH_TOKEN", "No active session. Please log in.")
    user_id, new_refresh_token = token_service.rotate_refresh_token(db, raw_refresh_token)
    user = user_service.get_by_id(db, user_id)
    if user is None or not user["is_active"]:
        token_service.revoke_all_user_tokens(db, user_id)
        raise AppError(401, "INVALID_REFRESH_TOKEN", "Your session is no longer valid. Please log in again.")
    access_token, expires_in = create_access_token(str(user["_id"]), user["role"])
    return user, access_token, expires_in, new_refresh_token


def logout(db: Database, raw_refresh_token: str | None) -> None:
    if raw_refresh_token:
        token_service.revoke_refresh_token(db, raw_refresh_token)


def verify_email(db: Database, raw_token: str) -> None:
    user_id = token_service.consume_email_verification_token(db, raw_token)
    user = user_service.get_by_id(db, user_id)
    if user is None:
        raise AppError(400, "INVALID_TOKEN", "This verification link is invalid.")
    if user["is_verified"]:
        raise AppError(400, "ALREADY_VERIFIED", "This email address is already verified.")
    user_service.mark_verified(db, user_id)


def resend_verification(db: Database, email: str, background: BackgroundTasks) -> None:
    """The route always answers the same way, so nobody can probe which emails exist."""
    user = user_service.get_by_email(db, email)
    if user is None or user["is_verified"] or not user["is_active"]:
        return
    raw_token = token_service.create_email_verification_token(db, user["_id"])
    background.add_task(email_service.send_verification_email, user["email"], user["first_name"], raw_token)


def forgot_password(db: Database, email: str, background: BackgroundTasks) -> None:
    user = user_service.get_by_email(db, email)
    if user is None or not user["is_active"]:
        return
    raw_token = token_service.create_password_reset_token(db, user["_id"])
    background.add_task(email_service.send_password_reset_email, user["email"], user["first_name"], raw_token)


def reset_password(db: Database, raw_token: str, new_password: str) -> None:
    user_id = token_service.consume_password_reset_token(db, raw_token)
    user_service.set_password(db, user_id, new_password)
    token_service.revoke_all_user_tokens(db, user_id)  # log out every device


def change_password(db: Database, user: dict, current_password: str, new_password: str) -> str:
    """Returns a fresh refresh token for the current device (all others are revoked)."""
    if not verify_password(current_password, user["password_hash"]):
        raise AppError(400, "INVALID_CURRENT_PASSWORD", "Your current password is incorrect.")
    user_service.set_password(db, user["_id"], new_password)
    token_service.revoke_all_user_tokens(db, user["_id"])
    return token_service.create_refresh_token(db, user["_id"])
