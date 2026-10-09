from fastapi import APIRouter, Depends, Query
from pymongo.database import Database

from app.core.database import get_db
from app.dependencies.auth import require_admin
from app.schemas.user import RoleUpdateRequest
from app.services import token_service, user_service
from app.utils.errors import AppError
from app.utils.responses import success_response

# Every route in this router requires an admin (checked on the server).
router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)])


def _get_user_or_404(db: Database, user_id: str) -> dict:
    user = user_service.get_by_id(db, user_id)
    if user is None:
        raise AppError(404, "USER_NOT_FOUND", "User not found.")
    return user


@router.get("/users")
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Database = Depends(get_db),
) -> dict:
    users, total = user_service.list_users(db, page, page_size)
    return success_response(
        "Users loaded.",
        {"items": [user_service.serialize_user(u) for u in users], "total": total, "page": page, "page_size": page_size},
    )


@router.get("/users/{user_id}")
def get_user(user_id: str, db: Database = Depends(get_db)) -> dict:
    return success_response("User loaded.", {"user": user_service.serialize_user(_get_user_or_404(db, user_id))})


@router.patch("/users/{user_id}/activate")
def activate_user(user_id: str, db: Database = Depends(get_db)) -> dict:
    user = _get_user_or_404(db, user_id)
    user_service.set_active(db, user["_id"], True)
    return success_response("User activated.", {"user": user_service.serialize_user(_get_user_or_404(db, user_id))})


@router.patch("/users/{user_id}/deactivate")
def deactivate_user(user_id: str, admin: dict = Depends(require_admin), db: Database = Depends(get_db)) -> dict:
    user = _get_user_or_404(db, user_id)
    if user["_id"] == admin["_id"]:
        raise AppError(400, "CANNOT_MODIFY_SELF", "You cannot deactivate your own account.")
    user_service.set_active(db, user["_id"], False)
    token_service.revoke_all_user_tokens(db, user["_id"])  # kick them out of every session
    return success_response("User deactivated.", {"user": user_service.serialize_user(_get_user_or_404(db, user_id))})


@router.patch("/users/{user_id}/role")
def change_role(
    user_id: str,
    data: RoleUpdateRequest,
    admin: dict = Depends(require_admin),
    db: Database = Depends(get_db),
) -> dict:
    user = _get_user_or_404(db, user_id)
    if user["_id"] == admin["_id"]:
        raise AppError(400, "CANNOT_MODIFY_SELF", "You cannot change your own role.")
    user_service.set_role(db, user["_id"], data.role)
    return success_response("Role updated.", {"user": user_service.serialize_user(_get_user_or_404(db, user_id))})
