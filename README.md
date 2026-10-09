# Authentication System (FastAPI + MongoDB Atlas + React)

A learning-oriented, production-style authentication system: registration, email verification,
login with short-lived JWT access tokens + rotating refresh tokens (HttpOnly cookie), password
reset, profile, roles (user/admin), admin user management, rate limiting and security headers.

## 1. Architecture

```
React (Vite)  ──HTTP/JSON──▶  FastAPI  ──▶  MongoDB Atlas
 access token in memory        routes → services → database
 refresh token = HttpOnly      dependencies (auth/roles), rate limit,
 cookie (invisible to JS)      security headers, CORS, email service
```

| Layer | Responsibility |
|---|---|
| `routes/` | HTTP only: parse request, call a service, shape the response |
| `services/` | Business logic (register, login, tokens, email, users) |
| `schemas/` | Pydantic request/response models + validation (password policy) |
| `models/` | Collection names, indexes, document builders |
| `core/` | Settings (`.env`), MongoDB connection, hashing + JWT |
| `dependencies/` | `require_authenticated_user`, `require_admin` |
| `utils/` | Error format, response format, rate limiter, validators, email templates |

## 2. Folder structure

```
authentication-system/
├── backend/
│   ├── app/
│   │   ├── main.py                 # app, CORS, security headers, startup (indexes)
│   │   ├── core/                   # config.py  database.py  security.py
│   │   ├── models/                 # user, refresh_token, verification_token, password_reset_token
│   │   ├── schemas/                # auth.py  user.py
│   │   ├── routes/                 # auth.py  users.py  admin.py  health.py
│   │   ├── services/               # auth_service  token_service  user_service  email_service
│   │   ├── dependencies/auth.py
│   │   └── utils/                  # errors  responses  rate_limit  validators  time  email_templates
│   ├── scripts/create_admin.py     # promote a user to admin
│   ├── tests/                      # pytest + mongomock (never touches Atlas)
│   ├── requirements.txt  pytest.ini  .env.example  .gitignore
├── frontend/
│   ├── src/ components/ pages/ services/ context/ hooks/ routes/ utils/  App.jsx  main.jsx
│   └── package.json  vite.config.js  .env.example  .gitignore
├── README.md
└── .gitignore
```

## 3. MongoDB Atlas setup (you already have a cluster)

1. **Database user**: Atlas → *Database Access* → *Add New Database User* → choose *Password*, give it a
   username + strong password, privilege *Read and write to any database* (or restrict to `authentication_db`).
   Avoid `@ : / ? # %` in the password, or URL-encode them.
2. **Network Access**: Atlas → *Network Access* → *Add IP Address* → *Add Current IP Address*
   (do not use `0.0.0.0/0` outside quick experiments).
3. **Connection string**: Atlas → *Database* → *Connect* → *Drivers* → copy the `mongodb+srv://...` string.
4. **Where to paste it**: in **`backend/.env`**, on the line `MONGODB_URL=`. Shape:

   ```
   MONGODB_URL=mongodb+srv://<DB_USERNAME>:<DB_PASSWORD>@<CLUSTER_HOST>/authentication_db?retryWrites=true&w=majority
   ```
   Replace `<DB_USERNAME>`, `<DB_PASSWORD>`, `<CLUSTER_HOST>` yourself. Never put it in a `.py` file.
   The database and collections are created automatically on first run, together with their indexes.

## 4. Configure `backend/.env`

```powershell
cd backend
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(64))"   # paste the output as JWT_SECRET_KEY
```

Fields **you must fill**: `MONGODB_URL`, `JWT_SECRET_KEY`.
Fields for real email (optional in development): `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`,
`SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME`.
Everything else has a safe local default (`FRONTEND_URL`, `CORS_ORIGINS`, token lifetimes, cookie flags...).

### SMTP
Use any provider (Gmail with an *App Password*, Brevo, Mailgun, Mailtrap...). Typical values:
`SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587` (STARTTLS) or `465` (SSL), your account as `SMTP_USERNAME`,
the app password as `SMTP_PASSWORD`, and a sender address as `SMTP_FROM_EMAIL`.

**No SMTP yet?** Leave the `SMTP_*` values empty. In development the backend prints each email
(including the verification / reset link) in the terminal running uvicorn, so you can click the link.
This console mode is disabled when `ENVIRONMENT=production`.

## 5. Run the backend (Windows PowerShell)

```powershell
cd authentication-system\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Open http://localhost:8000/docs (Swagger UI) and http://localhost:8000/api/v1/health.
If `.env` is incomplete the server stops with a readable list of what is missing.

## 6. Run the frontend

```powershell
cd authentication-system\frontend
Copy-Item .env.example .env
npm install
npm run dev
```
Open http://localhost:5173. `VITE_API_BASE_URL` is public (it is bundled into the browser code): never put secrets in it.

## 7. Run the tests

```powershell
cd authentication-system\backend
.\.venv\Scripts\Activate.ps1
python -m pytest -v
```
Tests use `mongomock` (an in-memory fake MongoDB) and force their own environment variables, so
they cannot read or modify your Atlas data, even if `.env` exists. 27 tests cover health, registration,
duplicates, login, invalid login, protected routes, verification, forgot/reset password, logout,
refresh rotation + reuse detection, admin/user authorization, forged and expired tokens, rate limiting.

## 8. Create an admin safely

There is no default admin and no admin password in the code.
1. Register a normal account in the app and verify the email.
2. Promote it (the email is the only argument, no password is typed or stored):
   ```powershell
   cd backend
   python -m scripts.create_admin you@example.com
   ```
3. Log out and log in again. The "Admin" link and `/admin/users` page appear.

## 9. API endpoints (`/api/v1`)

| Method | Path | Access |
|---|---|---|
| GET | `/health` | public |
| POST | `/auth/register` | public, rate limited |
| POST | `/auth/login` | public, rate limited |
| POST | `/auth/refresh` | refresh cookie |
| POST | `/auth/logout` | refresh cookie |
| GET | `/auth/verify-email?token=` | public |
| POST | `/auth/resend-verification` | public, rate limited |
| POST | `/auth/forgot-password` | public, rate limited |
| POST | `/auth/reset-password` | public, rate limited |
| GET / PATCH | `/users/me` | logged in |
| POST | `/users/change-password` | logged in |
| GET | `/admin/users` (`?page=&page_size=`) , `/admin/users/{id}` | admin |
| PATCH | `/admin/users/{id}/activate`, `/deactivate`, `/role` | admin |

Responses always look like `{"success": true, "message": "...", "data": {...}}` or
`{"success": false, "error": {"code": "...", "message": "...", "details": ...}}`.

## 10. Authentication flows

**Register** → validate (Pydantic) → check email/username → Argon2id hash → insert user (`is_verified=false`)
→ create random token → store only its SHA-256 hash (TTL-expiring) → email the raw token link.

**Verify email** → frontend page `/verify-email?token=...` calls the API → hash token → atomically find+delete
→ check expiry → `is_verified=true`.

**Login** → find user → verify password → check active → check verified → issue 15-min JWT (returned in JSON,
kept in React memory) + 7-day refresh token (random, hash stored, sent as HttpOnly cookie).

**Refresh** (automatic) → cookie token is hashed and looked up → revoked + replaced by a new one (rotation)
→ new access token. If an already-revoked token shows up again, every session of that user is revoked.
The React Axios interceptor does this on a 401, and once on page load to restore the session.

**Logout** → revoke refresh token in the DB → delete the cookie → clear in-memory token and user.

**Forgot / reset password** → always the same generic response → token hash stored (15 min, single-use,
flipped `used` atomically) → on reset the password is re-hashed and **all refresh tokens are revoked**.

**Authorization** → `require_authenticated_user` decodes the JWT, then loads the user from the DB
(active check, current role). `require_admin` builds on it. Frontend guards are UX only.

## 11. Database design (`authentication_db`)

| Collection | Fields | Indexes |
|---|---|---|
| `users` | email, username, password_hash, first_name, last_name, role, is_active, is_verified, created_at, updated_at, last_login | unique `email`, unique `username`, `created_at` |
| `refresh_tokens` | user_id, token_hash, expires_at, revoked, created_at | unique `token_hash`, `user_id`, **TTL** `expires_at` |
| `email_verification_tokens` | user_id, token_hash, expires_at, created_at | unique `token_hash`, `user_id`, **TTL** `expires_at` |
| `password_reset_tokens` | user_id, token_hash, expires_at, used, created_at | unique `token_hash`, `user_id`, **TTL** `expires_at` |

Indexes are created on every startup (idempotent). TTL indexes make MongoDB delete expired documents
(its cleanup runs about once a minute, so the code also checks `expires_at` itself).
Emails and usernames are stored lowercase.

## 12. Security decisions

- **Argon2id** password hashes; plaintext passwords are never stored, logged or returned; `UserPublic` has no hash field.
- **Tokens hashed at rest** (SHA-256 of 256-bit random values); a database leak does not reveal usable tokens.
- **Short access token, rotating refresh token** in an HttpOnly, `SameSite=Lax` cookie scoped to `/api/v1/auth`.
  Access token only lives in JS memory, nothing sensitive in `localStorage`.
- **JWT**: secret only from env (≥32 chars enforced), algorithm pinned on decode, `exp`/`iat`/`sub` required, role re-read from DB.
- **Login order**: the password is verified *before* "inactive / unverified" is revealed, and a dummy hash keeps timing similar for unknown emails. (A deliberate deviation from the checklist order in the brief, to avoid leaking account status.)
- **No enumeration** on login, forgot-password and resend-verification. Registration does say "email already exists", which is a common usability trade-off.
- **Rate limiting**: in-memory sliding window per IP on sensitive routes. Per-process only: use Redis in multi-server deployments, and configure your proxy so the real client IP is seen.
- **Headers**: `nosniff`, `X-Frame-Options`, strict `Content-Security-Policy` for the API, `Referrer-Policy`, `Permissions-Policy`, `no-store`, and HSTS when `COOKIE_SECURE=true`.
- **CORS**: explicit origin list from env (wildcard refused at startup), credentials enabled only for those origins.
- **Errors**: one JSON format; database/unexpected errors are logged server-side and returned generically.
- **Known trade-off**: two browser tabs refreshing with the same old cookie at the same moment can trigger reuse detection and log you out. Production systems often add a short grace window.

### Local vs production cookies
Local (`http://localhost`): `COOKIE_SECURE=false`, `COOKIE_SAMESITE=lax`.
Production (HTTPS): `ENVIRONMENT=production`, `COOKIE_SECURE=true` (enforced), `FRONTEND_URL`/`CORS_ORIGINS` set to your real domain.
If frontend and API are on different *sites* (not just subdomains) you need `COOKIE_SAMESITE=none` + `COOKIE_SECURE=true`, and should add CSRF protection to `/auth/refresh`.
Swagger docs are disabled in production.

## 13. Never commit

`backend/.env`, `frontend/.env` (any `.env.*` except `.env.example`), `.venv/` / `venv/`, `node_modules/`,
`dist/`, `__pycache__/`, `.pytest_cache/`. These are all listed in the `.gitignore` files. If a secret was ever
committed, rotate it (new Atlas password, new JWT secret, new SMTP password): deleting it from Git history is not enough.

## First Run Checklist

- [ ] `backend/.env` created from `.env.example`
- [ ] `MONGODB_URL` pasted (Atlas user created, your IP allowed in Network Access)
- [ ] `JWT_SECRET_KEY` generated and pasted
- [ ] (optional) SMTP fields filled, or left empty to read emails in the terminal
- [ ] `pip install -r requirements.txt`, then `python -m pytest` passes
- [ ] `uvicorn app.main:app --reload --port 8000` starts without a configuration error
- [ ] `frontend/.env` created, `npm install`, `npm run dev`
- [ ] Register → click the verification link (email or backend terminal) → log in
- [ ] `python -m scripts.create_admin you@example.com` → log in again → open `/admin/users`
