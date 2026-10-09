from datetime import datetime

from bson import ObjectId
from pymongo import ASCENDING

from app.utils.time import utcnow

COLLECTION = "email_verification_tokens"

INDEXES = [
    ([("token_hash", ASCENDING)], {"unique": True, "name": "uniq_token_hash"}),
    ([("user_id", ASCENDING)], {"name": "user_id"}),
    ([("expires_at", ASCENDING)], {"expireAfterSeconds": 0, "name": "ttl_expires_at"}),
]


def build_verification_token_document(user_id: ObjectId, token_hash: str, expires_at: datetime) -> dict:
    return {
        "user_id": user_id,
        "token_hash": token_hash,
        "expires_at": expires_at,
        "created_at": utcnow(),
    }
