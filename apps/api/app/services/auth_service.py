"""Auth application service (§15 — routes stay thin, logic lives here).

Every public function here either returns a domain result or raises one of
the AuthError subclasses below; routes translate those into HTTP responses.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.tenant import Tenant, TenantType
from app.models.user import Role, User, UserSession
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.audit_service import record_audit as _record_audit


class AuthError(Exception):
    """Base class. Never leak the reason for a login failure to the client —
    routes must map every subclass of this to the same generic 401 message
    for credential-related errors (§90 — no information that aids probing)."""


class EmailAlreadyRegistered(AuthError):
    pass


class InvalidCredentials(AuthError):
    pass


class AccountInactive(AuthError):
    pass


class SessionInvalid(AuthError):
    pass


def register(db: Session, request: RegisterRequest) -> User:
    existing = db.query(User).filter(User.email == request.email).first()
    if existing is not None:
        raise EmailAlreadyRegistered()

    tenant = Tenant(name=request.display_name, tenant_type=TenantType.INDIVIDUAL)
    db.add(tenant)
    db.flush()  # assigns tenant.id without ending the transaction

    user = User(
        tenant_id=tenant.id,
        email=request.email,
        password_hash=hash_password(request.password),
        display_name=request.display_name,
        role=Role.STUDENT,
        date_of_birth=request.date_of_birth,
    )
    db.add(user)
    db.flush()

    _record_audit(db, tenant_id=tenant.id, actor_user_id=user.id, action="tenant.created", target_type="tenant", target_id=tenant.id)
    _record_audit(db, tenant_id=tenant.id, actor_user_id=user.id, action="user.registered", target_type="user", target_id=user.id)

    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, request: LoginRequest) -> User:
    user = db.query(User).filter(User.email == request.email).first()
    # Constant-shape failure: run a hash comparison even when there is no
    # user, so the response timing does not reveal whether the email exists.
    password_hash = user.password_hash if user is not None else "$argon2id$v=19$m=65536,t=3,p=4$AAAAAAAAAAAAAAAAAAAAAA$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    password_ok = verify_password(request.password, password_hash)

    if user is None or not password_ok:
        raise InvalidCredentials()
    if not user.is_active:
        raise AccountInactive()
    return user


def issue_access_token(user: User) -> tuple[str, datetime]:
    return create_access_token(user_id=user.id, tenant_id=user.tenant_id, role=user.role.value)


def create_session(db: Session, user: User) -> tuple[str, datetime]:
    raw_token, token_hash, expires_at = generate_refresh_token()
    db.add(UserSession(user_id=user.id, refresh_token_hash=token_hash, expires_at=expires_at))
    db.commit()
    return raw_token, expires_at


def rotate_session(db: Session, raw_refresh_token: str) -> tuple[User, str, datetime]:
    """Validates the presented refresh token, revokes it, and issues a
    replacement (rotation limits the blast radius of a leaked cookie)."""
    token_hash = hash_refresh_token(raw_refresh_token)
    session = db.query(UserSession).filter(UserSession.refresh_token_hash == token_hash).first()

    now = datetime.now(timezone.utc)
    if session is None or session.revoked_at is not None or session.expires_at < now:
        raise SessionInvalid()

    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise SessionInvalid()

    session.revoked_at = now
    new_raw_token, new_hash, new_expires_at = generate_refresh_token()
    db.add(UserSession(user_id=user.id, refresh_token_hash=new_hash, expires_at=new_expires_at))
    db.commit()
    return user, new_raw_token, new_expires_at


def revoke_session(db: Session, raw_refresh_token: str) -> None:
    token_hash = hash_refresh_token(raw_refresh_token)
    session = db.query(UserSession).filter(UserSession.refresh_token_hash == token_hash).first()
    if session is not None and session.revoked_at is None:
        session.revoked_at = datetime.now(timezone.utc)
        db.commit()
