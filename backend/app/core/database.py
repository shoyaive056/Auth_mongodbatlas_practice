"""MongoDB connection and index creation."""
import certifi
from pymongo import MongoClient
from pymongo.database import Database

from app.core.config import get_settings
from app.models import password_reset_token, refresh_token, user, verification_token

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        settings = get_settings()
        options: dict = {"serverSelectionTimeoutMS": 5000, "tz_aware": True}
        if settings.mongodb_url.startswith("mongodb+srv://"):
            # Uses an up-to-date CA bundle; avoids TLS errors on some Windows setups.
            options["tlsCAFile"] = certifi.where()
        _client = MongoClient(settings.mongodb_url, **options)
    return _client


def get_db() -> Database:
    """FastAPI dependency. Tests override this to use an in-memory database."""
    return get_client()[get_settings().database_name]


def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def create_indexes(db: Database) -> None:
    """Idempotent: safe to run on every startup."""
    for module in (user, refresh_token, verification_token, password_reset_token):
        for keys, options in module.INDEXES:
            db[module.COLLECTION].create_index(keys, **options)
