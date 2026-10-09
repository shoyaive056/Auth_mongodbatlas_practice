"""Reusable authentication / authorization dependencies."""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo.database import Database

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import ROLE_ADMIN
from app.services import user_service
from app.utils.errors import AppError

bearer_scheme = HTTPBearer(auto_error=False)


def require_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Database = Depends(get_db),
) -> dict:
    if credentials is None:
        raise AppError(401, "NOT_AUTHENTICATED", "Authentication required.", headers={"WWW-Authenticate": "Bearer"})
    payload = decode_access_token(credentials.credentials)
    user = user_service.get_by_id(db, payload["sub"])
    if user is None:
        raise AppError(401, "INVALID_TOKEN", "Invalid authentication token.", headers={"WWW-Authenticate": "Bearer"})
    if not user["is_active"]:
        raise AppError(403, "ACCOUNT_INACTIVE", "This account has been deactivated.")
    return user  # role comes from the database, NOT from the token or the frontend


def require_admin(user: dict = Depends(require_authenticated_user)) -> dict:
    if user["role"] != ROLE_ADMIN:
        raise AppError(403, "FORBIDDEN", "You do not have permission to perform this action.")
    return user
