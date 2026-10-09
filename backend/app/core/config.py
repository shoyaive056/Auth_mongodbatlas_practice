"""Application settings, loaded from environment variables / the .env file.

No secret is ever written in source code. Every value below comes from the
environment (see .env.example).
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"

    mongodb_url: str = ""
    database_name: str = "authentication_db"

    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    email_verification_expire_minutes: int = 30
    password_reset_expire_minutes: int = 15

    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    cors_origins: str = ""

    smtp_host: str = ""
    smtp_port: str = ""
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "Auth Practice"

    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    rate_limit_enabled: bool = True

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]
        return origins or [self.frontend_url.rstrip("/")]

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_port and self.smtp_from_email)

    def validate_for_startup(self) -> None:
        """Fail fast with a readable message if the .env file is incomplete."""
        problems: list[str] = []
        if not self.mongodb_url:
            problems.append("MONGODB_URL is empty (paste your Atlas connection string in backend/.env)")
        if len(self.jwt_secret_key) < 32:
            problems.append("JWT_SECRET_KEY must be at least 32 characters (see .env.example for how to generate one)")
        if self.cookie_samesite.lower() not in {"lax", "strict", "none"}:
            problems.append("COOKIE_SAMESITE must be lax, strict or none")
        if self.cookie_samesite.lower() == "none" and not self.cookie_secure:
            problems.append("COOKIE_SAMESITE=none requires COOKIE_SECURE=true")
        if "*" in self.cors_origin_list:
            problems.append("CORS_ORIGINS must list explicit origins, not '*'")
        if self.is_production and not self.cookie_secure:
            problems.append("COOKIE_SECURE must be true when ENVIRONMENT=production (HTTPS)")
        if problems:
            raise RuntimeError("Invalid configuration:\n - " + "\n - ".join(problems))


@lru_cache
def get_settings() -> Settings:
    return Settings()
