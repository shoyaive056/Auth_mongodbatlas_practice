"""Everything that reads or writes the `users` collection."""
from bson import ObjectId
from bson.errors import InvalidId
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.core.security import hash_password
from app.models.user import COLLECTION, build_user_document
from app.schemas.auth import RegisterRequest
from app.schemas.user import UserPublic
from app.utils.errors import AppError
from app.utils.time import utcnow


def serialize_user(doc: dict) -> dict:
    """Turn a MongoDB document into the safe public shape."""
    return UserPublic(
        id=str(doc["_id"]),
        email=doc["email"],
        username=doc["username"],
        first_name=doc["first_name"],
        last_name=doc["last_name"],
        role=doc["role"],
        is_active=doc["is_active"],
        is_verified=doc["is_verified"],
        created_at=doc["created_at"],
        last_login=doc.get("last_login"),
    ).model_dump(mode="json")


def get_by_id(db: Database, user_id: str | ObjectId) -> dict | None:
    try:
        oid = user_id if isinstance(user_id, ObjectId) else ObjectId(user_id)
    except (InvalidId, TypeError):
        return None
    return db[COLLECTION].find_one({"_id": oid})


def get_by_email(db: Database, email: str) -> dict | None:
    return db[COLLECTION].find_one({"email": email.lower()})


def get_by_username(db: Database, username: str) -> dict | None:
    return db[COLLECTION].find_one({"username": username.lower()})


def create_user(db: Database, data: RegisterRequest) -> dict:
    if get_by_email(db, data.email):
        raise AppError(409, "EMAIL_ALREADY_REGISTERED", "An account with this email already exists.")
    if get_by_username(db, data.username):
        raise AppError(409, "USERNAME_TAKEN", "This username is already taken.")

    document = build_user_document(
        email=data.email,
        username=data.username,
        password_hash=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
    )
    try:
        document["_id"] = db[COLLECTION].insert_one(document).inserted_id
    except DuplicateKeyError:
        # Two requests raced past the checks above; the unique indexes are the real guard.
        raise AppError(409, "EMAIL_OR_USERNAME_TAKEN", "Email or username is already in use.")
    return document


def update_profile(db: Database, user: dict, changes: dict) -> dict:
    if "username" in changes and changes["username"] != user["username"]:
        if get_by_username(db, changes["username"]):
            raise AppError(409, "USERNAME_TAKEN", "This username is already taken.")
    changes = {**changes, "updated_at": utcnow()}
    try:
        db[COLLECTION].update_one({"_id": user["_id"]}, {"$set": changes})
    except DuplicateKeyError:
        raise AppError(409, "USERNAME_TAKEN", "This username is already taken.")
    return get_by_id(db, user["_id"])


def set_password(db: Database, user_id: ObjectId, new_password: str) -> None:
    db[COLLECTION].update_one(
        {"_id": user_id},
        {"$set": {"password_hash": hash_password(new_password), "updated_at": utcnow()}},
    )


def mark_verified(db: Database, user_id: ObjectId) -> None:
    db[COLLECTION].update_one({"_id": user_id}, {"$set": {"is_verified": True, "updated_at": utcnow()}})


def set_active(db: Database, user_id: ObjectId, is_active: bool) -> None:
    db[COLLECTION].update_one({"_id": user_id}, {"$set": {"is_active": is_active, "updated_at": utcnow()}})


def set_role(db: Database, user_id: ObjectId, role: str) -> None:
    db[COLLECTION].update_one({"_id": user_id}, {"$set": {"role": role, "updated_at": utcnow()}})


def list_users(db: Database, page: int, page_size: int) -> tuple[list[dict], int]:
    cursor = db[COLLECTION].find().sort("created_at", -1).skip((page - 1) * page_size).limit(page_size)
    return list(cursor), db[COLLECTION].count_documents({})
