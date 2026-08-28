from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import Role

_MIN_PASSWORD_LENGTH = 10


class RegisterRequest(BaseModel):
    """Self-service B2C signup. Always provisions a fresh individual tenant
    and a STUDENT account — creating other roles/tenant types is an
    administrative operation, not exposed here (see ADR-011)."""

    email: EmailStr
    password: str = Field(min_length=_MIN_PASSWORD_LENGTH, max_length=200)
    display_name: str = Field(min_length=1, max_length=200)

    @field_validator("password")
    @classmethod
    def _reject_trivial_password(cls, value: str) -> str:
        if value.lower() in {"password", "12345678", "qwertyuiop"}:
            raise ValueError("password is too common")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    id: str
    tenant_id: str
    email: str
    display_name: str
    role: Role
    is_active: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserOut
