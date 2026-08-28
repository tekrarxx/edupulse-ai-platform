"""Password hashing, access-token (JWT), and refresh-token primitives (§78).

Decisions recorded in docs/adr/ADR-011-auth-token-strategy.md:
- Password hashing: Argon2id (argon2-cffi), OWASP's current recommendation.
- Access token: short-lived JWT (HS256), returned in the response body.
- Refresh token: opaque random value, stored server-side only as a SHA-256
  hash (so a stolen DB row cannot be replayed as a live token), delivered to
  the client exclusively via an httpOnly secure cookie. This lets logout and
  admin-triggered revocation actually invalidate a session, which a pure
  stateless JWT refresh token cannot do.
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

from app.core.config import get_settings

_hasher = PasswordHasher()

ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=30)
JWT_ALGORITHM = "HS256"


def hash_password(plain_password: str) -> str:
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """True if the stored hash was made with weaker-than-current parameters."""
    return _hasher.check_needs_rehash(password_hash)


def create_access_token(*, user_id: str, tenant_id: str, role: str) -> tuple[str, datetime]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires_at = now + ACCESS_TOKEN_TTL
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "iat": now,
        "exp": expires_at,
        "jti": str(uuid.uuid4()),
        "type": "access",
    }
    token = jwt.encode(payload, settings.api_secret_key, algorithm=JWT_ALGORITHM)
    return token, expires_at


def decode_access_token(token: str) -> dict:
    """Raises jwt.PyJWTError (or a subclass) on any invalid/expired token."""
    settings = get_settings()
    payload = jwt.decode(token, settings.api_secret_key, algorithms=[JWT_ALGORITHM])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("not an access token")
    return payload


def generate_refresh_token() -> tuple[str, str, datetime]:
    """Returns (raw_token_for_client, sha256_hash_for_storage, expires_at)."""
    raw_token = secrets.token_urlsafe(48)
    token_hash = hash_refresh_token(raw_token)
    expires_at = datetime.now(timezone.utc) + REFRESH_TOKEN_TTL
    return raw_token, token_hash, expires_at


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
