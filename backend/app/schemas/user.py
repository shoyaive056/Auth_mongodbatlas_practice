from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ValidationInfo, field_validator, model_validator

from app.utils.validators import clean_name, validate_password_strength, validate_username


class UserPublic(BaseModel):
    """The ONLY shape in which a user leaves the API. It has no password_hash field."""

    id: str
    email: str
    username: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: datetime | None = None


class UpdateProfileRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def check_name(cls, value: str | None) -> str | None:
        return None if value is None else clean_name(value)

    @field_validator("username")
    @classmethod
    def check_username(cls, value: str | None) -> str | None:
        return None if value is None else validate_username(value)

    @model_validator(mode="after")
    def at_least_one_field(self) -> "UpdateProfileRequest":
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        return self


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

    _check_password = field_validator("new_password")(validate_password_strength)

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, value: str, info: ValidationInfo) -> str:
        if value != info.data.get("new_password"):
            raise ValueError("Passwords do not match")
        return value


class RoleUpdateRequest(BaseModel):
    role: Literal["user", "admin"]
