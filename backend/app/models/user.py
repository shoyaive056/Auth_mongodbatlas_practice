from pymongo import ASCENDING

from app.utils.time import utcnow

COLLECTION = "users"
ROLE_USER = "user"
ROLE_ADMIN = "admin"

INDEXES = [
    ([("email", ASCENDING)], {"unique": True, "name": "uniq_email"}),
    ([("username", ASCENDING)], {"unique": True, "name": "uniq_username"}),
    ([("created_at", ASCENDING)], {"name": "created_at"}),  # admin list sorting
]


def build_user_document(
    *, email: str, username: str, password_hash: str, first_name: str, last_name: str, role: str = ROLE_USER
) -> dict:
    now = utcnow()
    return {
        "email": email,
        "username": username,
        "password_hash": password_hash,
        "first_name": first_name,
        "last_name": last_name,
        "role": role,
        "is_active": True,
        "is_verified": False,
        "created_at": now,
        "updated_at": now,
        "last_login": None,
    }
