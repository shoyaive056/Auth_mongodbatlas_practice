from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, Query, Response
from pymongo.database import Database

from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.auth import EmailRequest, LoginRequest, RegisterRequest, ResetPasswordRequest
from app.services import auth_service, user_service
from app.utils.rate_limit import RateLimiter
from app.utils.responses import success_response

router = APIRouter(prefix="/auth", tags=["Authentication"])

REFRESH_COOKIE = "refresh_token"
# The cookie is only sent to /api/v1/auth/* (login, refresh, logout), never to other endpoints.
COOKIE_PATH = "/api/v1/auth"


def set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        max_age=settings.refresh_token_expire_days * 86400,
        httponly=True,  # JavaScript cannot read it, which limits the damage of XSS
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite.lower(),
        path=COOKIE_PATH,
    )


def clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=REFRESH_COOKIE,
        path=COOKIE_PATH,
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite.lower(),
    )


def token_payload(user: dict, access_token: str, expires_in: int) -> dict:
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": user_service.serialize_user(user),
    }


@router.post("/register", status_code=201, dependencies=[Depends(RateLimiter("register", 10, 3600))])
def register(data: RegisterRequest, background: BackgroundTasks, db: Database = Depends(get_db)) -> dict:
    user = auth_service.register(db, data, background)
    return success_response(
        "Account created. Please check your email to verify your address.",
        {"user": user_service.serialize_user(user)},
    )


@router.post("/login", dependencies=[Depends(RateLimiter("login", 10, 300))])
def login(data: LoginRequest, response: Response, db: Database = Depends(get_db)) -> dict:
    user, access_token, expires_in, refresh_token = auth_service.login(db, data.email, data.password)
    set_refresh_cookie(response, refresh_token)
    return success_response("Logged in successfully.", token_payload(user, access_token, expires_in))


@router.post("/refresh", dependencies=[Depends(RateLimiter("refresh", 60, 300))])
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Database = Depends(get_db),
) -> dict:
    user, access_token, expires_in, new_refresh_token = auth_service.refresh_session(db, refresh_token)
    set_refresh_cookie(response, new_refresh_token)
    return success_response("Token refreshed.", token_payload(user, access_token, expires_in))


@router.post("/logout")
def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Database = Depends(get_db),
) -> dict:
    auth_service.logout(db, refresh_token)
    clear_refresh_cookie(response)
    return success_response("Logged out.")


@router.get("/verify-email", dependencies=[Depends(RateLimiter("verify-email", 20, 3600))])
def verify_email(token: str = Query(min_length=10, max_length=200), db: Database = Depends(get_db)) -> dict:
    auth_service.verify_email(db, token)
    return success_response("Email verified. You can now log in.")


@router.post("/resend-verification", dependencies=[Depends(RateLimiter("resend-verification", 5, 3600))])
def resend_verification(data: EmailRequest, background: BackgroundTasks, db: Database = Depends(get_db)) -> dict:
    auth_service.resend_verification(db, data.email, background)
    return success_response("If that account exists and is not verified yet, a new verification email has been sent.")


@router.post("/forgot-password", dependencies=[Depends(RateLimiter("forgot-password", 5, 3600))])
def forgot_password(data: EmailRequest, background: BackgroundTasks, db: Database = Depends(get_db)) -> dict:
    auth_service.forgot_password(db, data.email, background)
    return success_response("If an account with that email exists, a password reset link has been sent.")


@router.post("/reset-password", dependencies=[Depends(RateLimiter("reset-password", 10, 3600))])
def reset_password(data: ResetPasswordRequest, db: Database = Depends(get_db)) -> dict:
    auth_service.reset_password(db, data.token, data.new_password)
    return success_response("Password updated. You can now log in with your new password.")
