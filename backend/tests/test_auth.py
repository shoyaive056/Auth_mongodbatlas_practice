from datetime import timedelta

import jwt

from app.core.config import get_settings
from app.core.security import hash_token
from app.utils.rate_limit import reset_rate_limits
from app.utils.time import utcnow
from tests.conftest import (
    PASSWORD,
    auth_header,
    last_token_from_email,
    login,
    register_and_verify,
    user_payload,
)

API = "/api/v1"


# 1. Health -------------------------------------------------------------------
def test_health(client):
    response = client.get(f"{API}/health")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "healthy"
    assert response.headers["x-content-type-options"] == "nosniff"


# 2. Registration -------------------------------------------------------------
def test_register_success_and_no_secrets_leak(client, db):
    response = client.post(f"{API}/auth/register", json=user_payload())
    assert response.status_code == 201
    body = response.text
    assert "password" not in body and "token" not in body
    stored = db.users.find_one({"email": "ada@example.com"})
    assert stored["password_hash"].startswith("$argon2id$")
    assert stored["is_verified"] is False
    # Only the hash of the verification token is stored.
    raw = last_token_from_email()
    assert db.email_verification_tokens.find_one({"token_hash": hash_token(raw)})
    assert not db.email_verification_tokens.find_one({"token_hash": raw})


def test_register_weak_password_and_mismatch(client):
    weak = client.post(f"{API}/auth/register", json=user_payload(password="short", confirm_password="short"))
    assert weak.status_code == 422
    assert weak.json()["error"]["code"] == "VALIDATION_ERROR"
    mismatch = client.post(f"{API}/auth/register", json=user_payload(confirm_password="Different1Password"))
    assert mismatch.status_code == 422


# 3. Duplicate registration ----------------------------------------------------
def test_duplicate_email_and_username(client):
    assert client.post(f"{API}/auth/register", json=user_payload()).status_code == 201
    dup_email = client.post(f"{API}/auth/register", json=user_payload(username="other"))
    assert dup_email.status_code == 409
    assert dup_email.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"
    dup_name = client.post(f"{API}/auth/register", json=user_payload(email="new@example.com"))
    assert dup_name.status_code == 409
    assert dup_name.json()["error"]["code"] == "USERNAME_TAKEN"


# 4. Login --------------------------------------------------------------------
def test_login_requires_verified_email(client):
    client.post(f"{API}/auth/register", json=user_payload())
    response = login(client)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "EMAIL_NOT_VERIFIED"


def test_login_success_sets_httponly_cookie(client, verified_user):
    response = login(client)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["access_token"] and "refresh_token" not in data
    assert "password_hash" not in response.text
    cookie = response.headers["set-cookie"].lower()
    assert "refresh_token=" in cookie and "httponly" in cookie and "samesite=lax" in cookie


# 5. Invalid login -------------------------------------------------------------
def test_invalid_login(client, verified_user):
    wrong = login(client, password="WrongPassw0rd")
    unknown = login(client, email="nobody@example.com")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["error"] == unknown.json()["error"]  # same message: no user enumeration


def test_inactive_account_cannot_login(client, db, verified_user):
    db.users.update_one({"email": "ada@example.com"}, {"$set": {"is_active": False}})
    response = login(client)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_INACTIVE"


# 6. Protected route + profile -------------------------------------------------
def test_protected_route(client, user_headers):
    assert client.get(f"{API}/users/me").status_code == 401
    assert client.get(f"{API}/users/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    me = client.get(f"{API}/users/me", headers=user_headers)
    assert me.status_code == 200
    assert me.json()["data"]["user"]["email"] == "ada@example.com"


def test_update_profile_and_cannot_set_role(client, user_headers):
    response = client.patch(
        f"{API}/users/me", headers=user_headers, json={"first_name": "Augusta", "role": "admin"}
    )
    assert response.status_code == 200
    user = response.json()["data"]["user"]
    assert user["first_name"] == "Augusta"
    assert user["role"] == "user"


def test_change_password(client, user_headers):
    bad = client.post(
        f"{API}/users/change-password",
        headers=user_headers,
        json={"current_password": "WrongPassw0rd", "new_password": "NewPassw0rd1", "confirm_password": "NewPassw0rd1"},
    )
    assert bad.status_code == 400
    ok = client.post(
        f"{API}/users/change-password",
        headers=user_headers,
        json={"current_password": PASSWORD, "new_password": "NewPassw0rd1", "confirm_password": "NewPassw0rd1"},
    )
    assert ok.status_code == 200
    assert login(client, password=PASSWORD).status_code == 401
    assert login(client, password="NewPassw0rd1").status_code == 200


# 7. Email verification --------------------------------------------------------
def test_email_verification_flow(client, db):
    client.post(f"{API}/auth/register", json=user_payload())
    token = last_token_from_email()
    assert client.get(f"{API}/auth/verify-email", params={"token": "x" * 40}).status_code == 400
    assert client.get(f"{API}/auth/verify-email", params={"token": token}).status_code == 200
    assert db.users.find_one({"email": "ada@example.com"})["is_verified"] is True
    # token is single-use
    assert client.get(f"{API}/auth/verify-email", params={"token": token}).status_code == 400


def test_resend_verification_is_generic(client):
    client.post(f"{API}/auth/register", json=user_payload())
    before = len(__import__("app.services.email_service", fromlist=["x"]).dev_outbox)
    known = client.post(f"{API}/auth/resend-verification", json={"email": "ada@example.com"})
    unknown = client.post(f"{API}/auth/resend-verification", json={"email": "ghost@example.com"})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    from app.services import email_service

    assert len(email_service.dev_outbox) == before + 1


# 8-9. Forgot / reset password -------------------------------------------------
def test_forgot_password_is_generic(client, verified_user):
    known = client.post(f"{API}/auth/forgot-password", json={"email": "ada@example.com"})
    unknown = client.post(f"{API}/auth/forgot-password", json={"email": "ghost@example.com"})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()


def test_reset_password_single_use_and_revokes_sessions(client, db, verified_user):
    login(client)  # creates a refresh token
    client.post(f"{API}/auth/forgot-password", json={"email": "ada@example.com"})
    token = last_token_from_email()
    assert db.password_reset_tokens.find_one({"token_hash": hash_token(token)})["used"] is False

    body = {"token": token, "new_password": "BrandNewPassw0rd", "confirm_password": "BrandNewPassw0rd"}
    assert client.post(f"{API}/auth/reset-password", json=body).status_code == 200
    assert client.post(f"{API}/auth/reset-password", json=body).status_code == 400  # single use
    assert login(client, password=PASSWORD).status_code == 401
    assert login(client, password="BrandNewPassw0rd").status_code == 200
    assert db.refresh_tokens.count_documents({"revoked": False}) == 1  # only the fresh login


# 10. Logout + refresh ----------------------------------------------------------
def test_refresh_rotation_and_logout(client, verified_user):
    login(client)
    first = client.post(f"{API}/auth/refresh")
    assert first.status_code == 200 and first.json()["data"]["access_token"]
    assert client.post(f"{API}/auth/logout").status_code == 200
    assert client.post(f"{API}/auth/refresh").status_code == 401  # cookie cleared / token revoked


def test_refresh_token_reuse_revokes_everything(client, db, verified_user):
    login(client)
    old_cookie = client.cookies.get("refresh_token")
    assert client.post(f"{API}/auth/refresh").status_code == 200  # rotates; old token now revoked
    client.cookies.clear()
    client.cookies.set("refresh_token", old_cookie, path="/api/v1/auth")
    assert client.post(f"{API}/auth/refresh").status_code == 401
    assert db.refresh_tokens.count_documents({"revoked": False}) == 0


# 11-12. Authorization ----------------------------------------------------------
def test_admin_endpoints_forbidden_for_normal_user(client, user_headers):
    assert client.get(f"{API}/admin/users").status_code == 401
    forbidden = client.get(f"{API}/admin/users", headers=user_headers)
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "FORBIDDEN"


def test_admin_can_manage_users(client, db, admin_headers):
    register_and_verify(client, username="grace", email="grace@example.com")
    grace_id = str(db.users.find_one({"email": "grace@example.com"})["_id"])

    listing = client.get(f"{API}/admin/users", headers=admin_headers)
    assert listing.status_code == 200 and listing.json()["data"]["total"] == 2
    assert "password_hash" not in listing.text

    assert client.patch(f"{API}/admin/users/{grace_id}/deactivate", headers=admin_headers).status_code == 200
    assert login(client, "grace@example.com").status_code == 403
    assert client.patch(f"{API}/admin/users/{grace_id}/activate", headers=admin_headers).status_code == 200
    assert login(client, "grace@example.com").status_code == 200

    role = client.patch(f"{API}/admin/users/{grace_id}/role", headers=admin_headers, json={"role": "admin"})
    assert role.json()["data"]["user"]["role"] == "admin"
    assert client.get(f"{API}/admin/users/not-an-id", headers=admin_headers).status_code == 404


def test_admin_cannot_demote_or_deactivate_self(client, db, admin_headers):
    my_id = str(db.users.find_one({"email": "boss@example.com"})["_id"])
    assert client.patch(f"{API}/admin/users/{my_id}/deactivate", headers=admin_headers).status_code == 400
    assert client.patch(f"{API}/admin/users/{my_id}/role", headers=admin_headers, json={"role": "user"}).status_code == 400


def test_role_comes_from_database_not_token(client, db, user_headers):
    """A stale/forged 'admin' claim is useless: the server re-reads the role."""
    user = db.users.find_one({"email": "ada@example.com"})
    settings = get_settings()
    forged = jwt.encode(
        {"sub": str(user["_id"]), "role": "admin", "type": "access", "iat": utcnow(), "exp": utcnow() + timedelta(minutes=5)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    assert client.get(f"{API}/admin/users", headers={"Authorization": f"Bearer {forged}"}).status_code == 403


# 13. Expired tokens -------------------------------------------------------------
def test_expired_access_token(client, db, verified_user):
    user = db.users.find_one({"email": "ada@example.com"})
    settings = get_settings()
    expired = jwt.encode(
        {"sub": str(user["_id"]), "role": "user", "type": "access", "iat": utcnow() - timedelta(minutes=30), "exp": utcnow() - timedelta(minutes=15)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    response = client.get(f"{API}/users/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_EXPIRED"


def test_wrong_secret_and_none_algorithm_rejected(client, db, verified_user):
    user = db.users.find_one({"email": "ada@example.com"})
    payload = {"sub": str(user["_id"]), "role": "user", "type": "access", "iat": utcnow(), "exp": utcnow() + timedelta(minutes=5)}
    wrong = jwt.encode(payload, "some-other-secret-key-some-other-secret-key", algorithm="HS256")
    assert client.get(f"{API}/users/me", headers={"Authorization": f"Bearer {wrong}"}).status_code == 401
    unsigned = jwt.encode(payload, None, algorithm="none")
    assert client.get(f"{API}/users/me", headers={"Authorization": f"Bearer {unsigned}"}).status_code == 401


def test_expired_verification_and_reset_tokens(client, db, verified_user):
    past = utcnow() - timedelta(minutes=1)
    # The fake database deletes expired docs instantly (like a TTL index would, after up to ~60s in
    # real MongoDB). Drop those indexes so we exercise the application's own expiry check.
    db.password_reset_tokens.drop_index("ttl_expires_at")
    db.email_verification_tokens.drop_index("ttl_expires_at")
    # reset token
    client.post(f"{API}/auth/forgot-password", json={"email": "ada@example.com"})
    token = last_token_from_email()
    db.password_reset_tokens.update_one({"token_hash": hash_token(token)}, {"$set": {"expires_at": past}})
    body = {"token": token, "new_password": "BrandNewPassw0rd", "confirm_password": "BrandNewPassw0rd"}
    response = client.post(f"{API}/auth/reset-password", json=body)
    assert response.status_code == 400 and response.json()["error"]["code"] == "TOKEN_EXPIRED"
    # verification token
    register = client.post(f"{API}/auth/register", json=user_payload(username="bob", email="bob@example.com"))
    assert register.status_code == 201
    vtoken = last_token_from_email()
    db.email_verification_tokens.update_one({"token_hash": hash_token(vtoken)}, {"$set": {"expires_at": past}})
    expired = client.get(f"{API}/auth/verify-email", params={"token": vtoken})
    assert expired.status_code == 400 and expired.json()["error"]["code"] == "TOKEN_EXPIRED"


def test_expired_refresh_token(client, db, verified_user):
    login(client)
    db.refresh_tokens.drop_index("ttl_expires_at")
    db.refresh_tokens.update_many({}, {"$set": {"expires_at": utcnow() - timedelta(minutes=1)}})
    assert client.post(f"{API}/auth/refresh").status_code == 401


# Extras --------------------------------------------------------------------------
def test_rate_limiting(client, monkeypatch, verified_user):
    monkeypatch.setattr(get_settings(), "rate_limit_enabled", True)
    reset_rate_limits()
    statuses = [login(client, password="WrongPassw0rd").status_code for _ in range(11)]
    assert statuses[:10] == [401] * 10
    assert statuses[10] == 429


def test_indexes_created(db):
    assert "uniq_email" in db.users.index_information()
    assert "uniq_username" in db.users.index_information()
    assert "ttl_expires_at" in db.refresh_tokens.index_information()
