from pydantic import BaseModel, EmailStr, Field, ValidationInfo, field_validator

from app.utils.validators import clean_name, validate_password_strength, validate_username


class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    username: str
    email: EmailStr
    password: str
    confirm_password: str

    _clean_names = field_validator("first_name", "last_name")(clean_name)
    _clean_username = field_validator("username")(validate_username)
    _check_password = field_validator("password")(validate_password_strength)

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, value: str, info: ValidationInfo) -> str:
        if value != info.data.get("password"):
            raise ValueError("Passwords do not match")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


class EmailRequest(BaseModel):
    """Used by forgot-password and resend-verification."""

    email: EmailStr

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    new_password: str
    confirm_password: str

    _check_password = field_validator("new_password")(validate_password_strength)

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, value: str, info: ValidationInfo) -> str:
        if value != info.data.get("new_password"):
            raise ValueError("Passwords do not match")
        return value
