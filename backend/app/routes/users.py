from fastapi import APIRouter, Depends, Response
from pymongo.database import Database

from app.core.database import get_db
from app.dependencies.auth import require_authenticated_user
from app.routes.auth import set_refresh_cookie
from app.schemas.user import ChangePasswordRequest, UpdateProfileRequest
from app.services import auth_service, user_service
from app.utils.responses import success_response

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me")
def get_me(user: dict = Depends(require_authenticated_user)) -> dict:
    return success_response("Profile loaded.", {"user": user_service.serialize_user(user)})


@router.patch("/me")
def update_me(
    data: UpdateProfileRequest,
    user: dict = Depends(require_authenticated_user),
    db: Database = Depends(get_db),
) -> dict:
    # Only first_name / last_name / username can be changed here; role and
    # is_active are not in the schema, so a user cannot promote themselves.
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    updated = user_service.update_profile(db, user, changes)
    return success_response("Profile updated.", {"user": user_service.serialize_user(updated)})


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    response: Response,
    user: dict = Depends(require_authenticated_user),
    db: Database = Depends(get_db),
) -> dict:
    new_refresh_token = auth_service.change_password(db, user, data.current_password, data.new_password)
    set_refresh_cookie(response, new_refresh_token)  # this device stays logged in; others are revoked
    return success_response("Password changed. Other devices have been logged out.")
