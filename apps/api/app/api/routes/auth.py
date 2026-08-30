import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import enforce_rate_limit, get_current_user, require_role
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import Role, User
from app.schemas.auth import (
    CreateTenantUserRequest,
    LoginRequest,
    RegisterRequest,
    SetDateOfBirthRequest,
    TokenResponse,
    UserOut,
)
from app.schemas.relationship import ParentChildOut, ParentLinkCreate, ParentLinkOut
from app.services import auth_service, relationship_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth")

_REFRESH_COOKIE_NAME = "edupulse_refresh_token"
_REFRESH_COOKIE_PATH = "/auth"


def _set_refresh_cookie(response: Response, raw_token: str, expires_at) -> None:
    settings = get_settings()
    response.set_cookie(
        key=_REFRESH_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        path=_REFRESH_COOKIE_PATH,
        expires=expires_at,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=_REFRESH_COOKIE_NAME, path=_REFRESH_COOKIE_PATH)


def _token_response(user: User, response: Response, db: Session) -> TokenResponse:
    access_token, access_expires_at = auth_service.issue_access_token(user)
    refresh_token, refresh_expires_at = auth_service.create_session(db, user)
    _set_refresh_cookie(response, refresh_token, refresh_expires_at)
    return TokenResponse(access_token=access_token, expires_at=access_expires_at, user=UserOut.model_validate(user))


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    enforce_rate_limit(request, key_prefix="register", limit=10, window_seconds=60)
    try:
        user = auth_service.register(db, payload)
    except auth_service.EmailAlreadyRegistered:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email_already_registered")
    return _token_response(user, response, db)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    enforce_rate_limit(request, key_prefix="login", limit=5, window_seconds=60)
    try:
        user = auth_service.authenticate(db, payload)
    except (auth_service.InvalidCredentials, auth_service.AccountInactive):
        # Same message for both — do not reveal which check failed (§90).
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")
    return _token_response(user, response, db)


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    enforce_rate_limit(request, key_prefix="refresh", limit=30, window_seconds=60)
    raw_refresh_token = request.cookies.get(_REFRESH_COOKIE_NAME)
    if raw_refresh_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")

    try:
        user, new_raw_token, new_expires_at = auth_service.rotate_session(db, raw_refresh_token)
    except auth_service.SessionInvalid:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")

    access_token, access_expires_at = auth_service.issue_access_token(user)
    _set_refresh_cookie(response, new_raw_token, new_expires_at)
    return TokenResponse(access_token=access_token, expires_at=access_expires_at, user=UserOut.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    raw_refresh_token = request.cookies.get(_REFRESH_COOKIE_NAME)
    if raw_refresh_token is not None:
        auth_service.revoke_session(db, raw_refresh_token)
    _clear_refresh_cookie(response)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)


@router.get("/tenant/users", response_model=list[UserOut])
def list_tenant_users(
    current_user: User = Depends(require_role(Role.TENANT_ADMIN, Role.SCHOOL_ADMIN, Role.SUPER_ADMIN)),
    db: Session = Depends(get_db),
) -> list[UserOut]:
    """Tenant-scoped user directory (§51 enforcement point + §52 cross-tenant
    test target). SUPER_ADMIN is still scoped to their own tenant here —
    a cross-tenant admin view is a deliberately separate, more sensitive
    endpoint this phase does not build."""
    query = db.query(User).filter(User.tenant_id == current_user.tenant_id)
    return [UserOut.model_validate(u) for u in query.all()]


_relationship_staff_access = require_role(Role.TENANT_ADMIN, Role.SCHOOL_ADMIN, Role.SUPER_ADMIN)


@router.get("/parent/children", response_model=list[ParentChildOut])
def list_my_children(
    current_user: User = Depends(require_role(Role.PARENT)),
    db: Session = Depends(get_db),
) -> list[ParentChildOut]:
    """A parent's own portal entry point — the piece that was missing for
    a parent to use `GET /dashboard/student?student_id=...` and friends at
    all: those endpoints already accepted a linked parent, but nothing let
    a parent discover their own children's ids without already knowing a
    UUID (§80: returns only what a parent needs to pick a child, not a
    full account record)."""
    rows = relationship_service.list_children_for_parent(db, tenant_id=current_user.tenant_id, parent_user_id=current_user.id)
    return [
        ParentChildOut(student_user_id=student.id, display_name=student.display_name, consent_on_file=link.consent_given_at is not None)
        for student, link in rows
    ]


@router.post("/tenant/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_tenant_user(
    payload: CreateTenantUserRequest,
    request: Request,
    current_user: User = Depends(_relationship_staff_access),
    db: Session = Depends(get_db),
) -> UserOut:
    """Admin-initiated enrollment into the admin's own tenant (§53) — closes
    the gap `/auth/register` deliberately leaves open (ADR-011: self-service
    only ever creates a fresh individual tenant + STUDENT). No access token
    is issued here; this creates an account for someone else, never signs
    the caller in as them."""
    enforce_rate_limit(request, key_prefix="tenant_user_create", limit=30, window_seconds=60, identity=current_user.id)
    try:
        user = auth_service.create_tenant_user(
            db, tenant_id=current_user.tenant_id, actor_user_id=current_user.id, actor_role=current_user.role, request=payload
        )
    except auth_service.EmailAlreadyRegistered:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email_already_registered")
    except auth_service.InsufficientRoleForUserCreation:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient_role_for_target_role")
    return UserOut.model_validate(user)


@router.post("/tenant/users/{user_id}/date-of-birth", response_model=UserOut)
def set_user_date_of_birth(
    user_id: str,
    payload: SetDateOfBirthRequest,
    current_user: User = Depends(_relationship_staff_access),
    db: Session = Depends(get_db),
) -> UserOut:
    """§81: an admin records a student's date of birth from an already-
    verified source (enrollment records) — used by the PDE's consent/age
    authorization gate (app/services/authorization_service.py)."""
    try:
        user = relationship_service.set_date_of_birth(
            db,
            tenant_id=current_user.tenant_id,
            actor_user_id=current_user.id,
            target_user_id=user_id,
            date_of_birth=payload.date_of_birth,
        )
    except relationship_service.UserNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
    return UserOut.model_validate(user)


@router.post("/tenant/parent-links", response_model=ParentLinkOut, status_code=status.HTTP_201_CREATED)
def create_parent_link(
    payload: ParentLinkCreate,
    current_user: User = Depends(_relationship_staff_access),
    db: Session = Depends(get_db),
) -> ParentLinkOut:
    """§81: an admin attests that a parent-student relationship and (when
    `consent_given=true`) guardian consent were already verified through an
    external process — this endpoint records that fact, it does not collect
    consent itself (see app/services/relationship_service.py)."""
    try:
        link = relationship_service.create_parent_link(
            db,
            tenant_id=current_user.tenant_id,
            actor_user_id=current_user.id,
            parent_user_id=payload.parent_user_id,
            student_user_id=payload.student_user_id,
            consent_given=payload.consent_given,
        )
    except relationship_service.ParentOrStudentNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="parent_or_student_not_found")
    except relationship_service.InvalidRoleForLink:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_role_for_link")
    except relationship_service.LinkAlreadyExists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="link_already_exists")
    return ParentLinkOut.model_validate(link)
