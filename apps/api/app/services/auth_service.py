"""Auth application service (§15 — routes stay thin, logic lives here).

Every public function here either returns a domain result or raises one of
the AuthError subclasses below; routes translate those into HTTP responses.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    generate_password_reset_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.plan import Plan
from app.models.tenant import Tenant, TenantType
from app.models.user import PasswordResetToken, Role, User, UserSession
from app.schemas.auth import CreateTenantUserRequest, LoginRequest, RegisterRequest
from app.services import email_service
from app.services.audit_service import record_audit as _record_audit

_DEFAULT_PLAN_SLUG = "free"

# §53/§78 least-privilege creation matrix: which roles an admin of a given
# role may create within their own tenant. SUPER_ADMIN can create any role,
# including other admins; TENANT_ADMIN and SCHOOL_ADMIN cannot create an
# admin role at or above their own — closes the privilege-escalation path a
# flat "any staff role can create any role" check would leave open.
_ROLE_CREATION_MATRIX: dict[Role, frozenset[Role]] = {
    Role.SUPER_ADMIN: frozenset(Role),
    Role.TENANT_ADMIN: frozenset({Role.SCHOOL_ADMIN, Role.TEACHER, Role.STUDENT, Role.PARENT}),
    Role.SCHOOL_ADMIN: frozenset({Role.TEACHER, Role.STUDENT, Role.PARENT}),
}


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


class PasswordResetTokenInvalid(AuthError):
    """Covers "doesn't exist", "expired", and "already used" alike — the API
    response must not distinguish between them (§90: no information that
    aids probing a token or brute-forcing the reset flow)."""
    pass


class InsufficientRoleForUserCreation(AuthError):
    pass


def register(db: Session, request: RegisterRequest) -> User:
    existing = db.query(User).filter(User.email == request.email).first()
    if existing is not None:
        raise EmailAlreadyRegistered()

    default_plan = db.query(Plan).filter(Plan.slug == _DEFAULT_PLAN_SLUG).first()
    tenant = Tenant(name=request.display_name, tenant_type=TenantType.INDIVIDUAL, plan_id=default_plan.id if default_plan else None)
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


def create_tenant_user(
    db: Session, *, tenant_id: str, actor_user_id: str, actor_role: Role, request: CreateTenantUserRequest
) -> User:
    """Admin-initiated enrollment (the "safe to defer, but noticed" gap
    MVP-GATE.md flagged: real schools need this before a pilot, not just
    self-service B2C signup). Always creates the user in the *actor's own*
    tenant_id — never a client-supplied one (§51)."""
    if request.role not in _ROLE_CREATION_MATRIX.get(actor_role, frozenset()):
        raise InsufficientRoleForUserCreation()

    existing = db.query(User).filter(User.email == request.email).first()
    if existing is not None:
        raise EmailAlreadyRegistered()

    user = User(
        tenant_id=tenant_id,
        email=request.email,
        password_hash=hash_password(request.password),
        display_name=request.display_name,
        role=request.role,
        date_of_birth=request.date_of_birth,
    )
    db.add(user)
    db.flush()

    _record_audit(
        db, tenant_id=tenant_id, actor_user_id=actor_user_id, action="user.created_by_admin", target_type="user", target_id=user.id
    )

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


def request_password_reset(db: Session, email: str) -> None:
    """Always succeeds from the caller's point of view, whether or not the
    email belongs to a real account (§90 — a distinguishable response here
    would let an attacker enumerate registered emails). If a matching,
    active user exists, a real token is created and a real email is sent;
    email-delivery failure is swallowed here (already logged by
    email_service) rather than surfaced, for the same anti-enumeration
    reason — the API's response shape never depends on whether sending
    actually succeeded."""
    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        return

    raw_token, token_hash, expires_at = generate_password_reset_token()
    db.add(PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
    db.commit()

    settings = get_settings()
    reset_link = f"{settings.web_base_url}/reset-password?token={raw_token}"
    try:
        email_service.send_password_reset_email(to_email=user.email, reset_link=reset_link)
    except email_service.EmailDeliveryError:
        pass


def reset_password(db: Session, raw_token: str, new_password: str) -> User:
    """Consumes a password-reset token exactly once and revokes every
    existing session for the account (§78 — if the account was compromised,
    a reset should not leave an attacker's session alive; the legitimate
    user simply logs in again with the new password)."""
    token_hash = hash_refresh_token(raw_token)
    reset_token = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()

    now = datetime.now(timezone.utc)
    if reset_token is None or reset_token.used_at is not None or reset_token.expires_at < now:
        raise PasswordResetTokenInvalid()

    user = db.get(User, reset_token.user_id)
    if user is None or not user.is_active:
        raise PasswordResetTokenInvalid()

    user.password_hash = hash_password(new_password)
    reset_token.used_at = now
    db.query(UserSession).filter(UserSession.user_id == user.id, UserSession.revoked_at.is_(None)).update(
        {UserSession.revoked_at: now}
    )
    _record_audit(db, tenant_id=user.tenant_id, actor_user_id=user.id, action="user.password_reset", target_type="user", target_id=user.id)
    db.commit()
    db.refresh(user)
    return user
