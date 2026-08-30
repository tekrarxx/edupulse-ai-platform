from datetime import date, datetime

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
    # §81 optional at signup — a self-registering B2C user may choose not to
    # share it. When absent, authorization_service treats the student's age
    # as unknown, never as an assumed adult (§105).
    date_of_birth: date | None = None

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
    date_of_birth: date | None

    model_config = {"from_attributes": True}


class SetDateOfBirthRequest(BaseModel):
    date_of_birth: date


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserOut
