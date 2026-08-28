import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import enforce_rate_limit, get_current_user, require_role
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import Role, User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services import auth_service

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
