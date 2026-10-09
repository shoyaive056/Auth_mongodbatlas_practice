"""Test setup.

Safety: the tests NEVER talk to MongoDB Atlas. They use `mongomock`, an
in-memory fake, and replace the app's get_db dependency with it. Environment
variables are forced below *before* the app is imported, so even a real
backend/.env cannot leak into the tests.
"""
import os

os.environ.update(
    {
        "ENVIRONMENT": "test",
        "MONGODB_URL": "mongodb://localhost:27017",  # never connected to
        "DATABASE_NAME": "authentication_test_db",
        "JWT_SECRET_KEY": "test-only-secret-key-that-is-long-enough-0123456789",
        "JWT_ALGORITHM": "HS256",
        "FRONTEND_URL": "http://localhost:5173",
        "SMTP_HOST": "",
        "SMTP_PORT": "",
        "SMTP_FROM_EMAIL": "",
        "COOKIE_SECURE": "false",
        "COOKIE_SAMESITE": "lax",
        "RATE_LIMIT_ENABLED": "false",
    }
)

from urllib.parse import parse_qs, urlparse  # noqa: E402

import mongomock  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import create_indexes, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services import email_service  # noqa: E402
from app.utils.rate_limit import reset_rate_limits  # noqa: E402

PASSWORD = "Str0ngPassw0rd"


@pytest.fixture()
def db():
    database = mongomock.MongoClient()["authentication_test_db"]
    create_indexes(database)
    return database


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    email_service.dev_outbox.clear()
    reset_rate_limits()
    yield TestClient(app)
    app.dependency_overrides.clear()


def user_payload(**overrides) -> dict:
    data = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "username": "ada",
        "email": "ada@example.com",
        "password": PASSWORD,
        "confirm_password": PASSWORD,
    }
    data.update(overrides)
    return data


def last_token_from_email() -> str:
    link = email_service.dev_outbox[-1]["link"]
    return parse_qs(urlparse(link).query)["token"][0]


def register_and_verify(client, **overrides) -> dict:
    payload = user_payload(**overrides)
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    token = last_token_from_email()
    assert client.get("/api/v1/auth/verify-email", params={"token": token}).status_code == 200
    return payload


def login(client, email="ada@example.com", password=PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def auth_header(response) -> dict:
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


@pytest.fixture()
def verified_user(client):
    return register_and_verify(client)


@pytest.fixture()
def user_headers(client, verified_user):
    return auth_header(login(client))


@pytest.fixture()
def admin_headers(client, db):
    register_and_verify(client, username="boss", email="boss@example.com")
    db.users.update_one({"email": "boss@example.com"}, {"$set": {"role": "admin"}})
    return auth_header(login(client, "boss@example.com"))
