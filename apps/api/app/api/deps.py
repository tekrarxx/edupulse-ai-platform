"""Shared FastAPI dependencies: authentication, RBAC, and rate limiting.

Centralizing tenant/role extraction here (rather than re-deriving it in each
route) is the enforcement point for §51: a route can only ever see the
tenant_id that came off a verified access token, never one a client passed
as a query param or body field.
"""
import logging

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import Role, User

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")
    if credentials is None:
        raise unauthorized

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise unauthorized

    user = db.get(User, payload.get("sub"))
    if user is None or not user.is_active:
        raise unauthorized
    # Defense in depth: even though the token was just verified, re-derive
    # tenant/role from the current DB row rather than trusting stale claims
    # if a role/tenant change happened after the token was issued.
    return user


def require_role(*allowed_roles: Role):
    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient_role")
        return current_user

    return _check


def enforce_rate_limit(request: Request, *, key_prefix: str, limit: int, window_seconds: int) -> None:
    """Fixed-window limiter backed by Redis (§78). Fails open (does not block
    the request) if Redis is unreachable — availability of auth must not
    depend on a cache being up, but the failure is logged so it is visible."""
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"
    key = f"ratelimit:{key_prefix}:{client_ip}"

    try:
        redis_client = Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        current = redis_client.incr(key)
        if current == 1:
            redis_client.expire(key, window_seconds)
        if current > limit:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="rate_limited")
    except RedisError as exc:
        logger.error("Rate limiter unavailable, failing open: %s", exc.__class__.__name__)
