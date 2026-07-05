import hashlib
import secrets
import uuid
from datetime import datetime, timezone, timedelta

import bcrypt
import jwt
try:
    import pyotp
    _TOTP_AVAILABLE = True
except ImportError:
    _TOTP_AVAILABLE = False

from fastapi import Cookie, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from src.core import config, services
from src.core.logger import get_logger

log = get_logger("auth")

_COOKIE = "ai_token"
_REFRESH_COOKIE = "ai_refresh"
_TOTP_PENDING_COOKIE = "ai_totp_pending"
_LOGIN_PATH = "/login"


# ── Password ──

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── Access token (JWT, short-lived) ──

def issue_token(username: str) -> str:
    if not config.JWT_SECRET:
        raise RuntimeError("JWT_SECRET is not set in .env")
    user = services.users.get(username)
    role = user["role"] if user else "member"
    exp = datetime.now(timezone.utc) + timedelta(hours=config.JWT_EXPIRY_HOURS)
    payload = {
        "sub": username,
        "role": role,
        "jti": str(uuid.uuid4()),
        "exp": exp,
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")


def _decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
        sub = payload.get("sub")
        if not sub:
            return None
        return {
            "sub": sub,
            "role": payload.get("role", "member"),
            "jti": payload.get("jti", ""),
            "exp": payload.get("exp"),
        }
    except jwt.PyJWTError:
        return None


def revoke_token(token: str):
    """Invalidate a JWT immediately by storing its jti. Called on logout."""
    try:
        payload = jwt.decode(
            token, config.JWT_SECRET, algorithms=["HS256"],
            options={"verify_exp": False},
        )
        jti = payload.get("jti")
        exp = payload.get("exp")
        if not jti:
            return
        exp_dt = datetime.utcfromtimestamp(exp) if exp else datetime.utcnow()
        services.tokens.revoke(jti, exp_dt)
    except Exception:
        pass


def set_auth_cookie(response, token: str):
    is_prod = config.ENVIRONMENT == "prod"
    response.set_cookie(
        key=_COOKIE, value=token, httponly=True, secure=is_prod,
        samesite="lax", path="/", max_age=config.JWT_EXPIRY_HOURS * 3600,
    )


def clear_auth_cookie(response):
    response.delete_cookie(key=_COOKIE, path="/")


# ── Refresh token (opaque random string, long-lived, stored hashed) ──

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_refresh_token(username: str) -> str:
    """Returns the raw refresh token. Stores its SHA-256 hash in DB."""
    token = secrets.token_urlsafe(32)
    exp = datetime.utcnow() + timedelta(days=config.REFRESH_TOKEN_EXPIRY_DAYS)
    services.tokens.create_refresh(username, _hash_token(token), exp)
    return token


def validate_refresh_token(token: str) -> str | None:
    """Returns username if the refresh token is valid, None otherwise."""
    row = services.tokens.get_refresh(_hash_token(token))
    if not row or row["revoked"]:
        return None
    exp = datetime.fromisoformat(row["expires_at"]).replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > exp:
        return None
    return row["username"]


def revoke_refresh_token(token: str):
    services.tokens.revoke_refresh(_hash_token(token))


def set_refresh_cookie(response, token: str):
    is_prod = config.ENVIRONMENT == "prod"
    response.set_cookie(
        key=_REFRESH_COOKIE, value=token, httponly=True, secure=is_prod,
        samesite="lax", path="/", max_age=config.REFRESH_TOKEN_EXPIRY_DAYS * 86400,
    )


def clear_refresh_cookie(response):
    response.delete_cookie(key=_REFRESH_COOKIE, path="/")


# ── TOTP (two-factor authentication) ──

def setup_totp(username: str) -> tuple[str, str]:
    """Generate a TOTP secret (disabled until verified). Returns (secret, provisioning_uri)."""
    if not _TOTP_AVAILABLE:
        raise RuntimeError("pyotp not installed. Run: python311 -m pip install pyotp")
    secret = pyotp.random_base32()
    services.totp.set(username, secret, enabled=False)
    uri = pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name=config.TOTP_ISSUER)
    return secret, uri


def enable_totp(username: str, code: str) -> bool:
    """Verify the code against the pending secret and enable TOTP. Returns True on success."""
    if not _TOTP_AVAILABLE:
        return False
    row = services.totp.get(username)
    if not row:
        return False
    if not pyotp.TOTP(row["secret"]).verify(code, valid_window=1):
        return False
    services.totp.set(username, row["secret"], enabled=True)
    return True


def disable_totp(username: str):
    services.totp.set(username, "", enabled=False)


def verify_totp(username: str, code: str) -> bool:
    """Returns True if TOTP passes (or TOTP is not configured for this user)."""
    if not _TOTP_AVAILABLE:
        return True
    row = services.totp.get(username)
    if not row or not row["enabled"]:
        return True
    return pyotp.TOTP(row["secret"]).verify(code, valid_window=1)


def is_totp_enabled(username: str) -> bool:
    row = services.totp.get(username)
    return bool(row and row["enabled"])


# ── TOTP pending temp token (carries username across 2-step login) ──

_TOTP_PENDING_TYPE = "totp_pending"


def issue_totp_temp_token(username: str) -> str:
    payload = {
        "sub": username,
        "type": _TOTP_PENDING_TYPE,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")


def validate_totp_temp_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
        if payload.get("type") != _TOTP_PENDING_TYPE:
            return None
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


def set_totp_pending_cookie(response, token: str):
    is_prod = config.ENVIRONMENT == "prod"
    response.set_cookie(
        key=_TOTP_PENDING_COOKIE, value=token, httponly=True, secure=is_prod,
        samesite="lax", path="/login", max_age=300,
    )


def clear_totp_pending_cookie(response):
    response.delete_cookie(key=_TOTP_PENDING_COOKIE, path="/login")


# ── Shared token validation logic ──

def _validate_token_data(data: dict | None) -> dict:
    """Checks revocation + user active. Raises on failure — caller chooses status code."""
    if not data:
        raise ValueError("invalid_token")
    if data["jti"] and services.tokens.is_revoked(data["jti"]):
        raise ValueError("revoked_token")
    if not services.users.is_active(data["sub"]):
        raise ValueError("inactive_user")
    return data


# ── FastAPI dependencies: page routes (redirect on failure) ──

def require_auth(ai_token: str = Cookie(default=None)) -> str:
    """Page dependency. Returns username. Redirects to /login on any auth failure."""
    if not ai_token:
        raise HTTPException(status_code=302, headers={"Location": _LOGIN_PATH})
    try:
        data = _validate_token_data(_decode_token(ai_token))
    except ValueError as e:
        log.warning(f"require_auth rejected: {e}")
        raise HTTPException(status_code=302, headers={"Location": _LOGIN_PATH})
    return data["sub"]


def get_current_user(ai_token: str = Cookie(default=None)) -> dict:
    """Page dependency. Returns {username, role}. Redirects to /login on failure."""
    if not ai_token:
        raise HTTPException(status_code=302, headers={"Location": _LOGIN_PATH})
    try:
        data = _validate_token_data(_decode_token(ai_token))
    except ValueError as e:
        log.warning(f"get_current_user rejected: {e}")
        raise HTTPException(status_code=302, headers={"Location": _LOGIN_PATH})
    return {"username": data["sub"], "role": data["role"]}


def require_role(role: str):
    """Factory for page routes. Usage: Depends(require_role('admin'))"""
    def _check(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] != role:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return _check


# ── FastAPI dependencies: API routes (401 JSON on failure) ──

def require_api_auth(ai_token: str = Cookie(default=None)) -> str:
    """API dependency. Returns username. Raises 401 JSON on any auth failure."""
    if not ai_token:
        raise HTTPException(status_code=401, detail="unauthorized")
    try:
        data = _validate_token_data(_decode_token(ai_token))
    except ValueError:
        raise HTTPException(status_code=401, detail="unauthorized")
    return data["sub"]


def require_api_user(ai_token: str = Cookie(default=None)) -> dict:
    """API dependency. Returns {username, role}. Raises 401 JSON on any auth failure."""
    if not ai_token:
        raise HTTPException(status_code=401, detail="unauthorized")
    try:
        data = _validate_token_data(_decode_token(ai_token))
    except ValueError:
        raise HTTPException(status_code=401, detail="unauthorized")
    return {"username": data["sub"], "role": data["role"]}


def require_api_role(role: str):
    """Factory for API routes. Usage: Depends(require_api_role('admin'))"""
    def _check(user: dict = Depends(require_api_user)) -> dict:
        if user["role"] != role:
            raise HTTPException(status_code=403, detail="forbidden")
        return user
    return _check


# ── Security headers middleware ──

_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none';"
)


async def security_headers_middleware(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = _CSP
    if config.ENVIRONMENT == "prod":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
