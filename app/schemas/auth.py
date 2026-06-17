from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.principal import Role


class LoginRequest(BaseModel):
    """Credentials for the login endpoint."""

    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    """An issued access token."""

    access_token: str
    token_type: str = "bearer"  # noqa: S105 - token type label, not a secret
    role: Role
    expires_in: int


class UserCreateRequest(BaseModel):
    """Request to create a new user."""

    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=8, max_length=256)
    role: Role


class UserResponse(BaseModel):
    """A user as stored, without the password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: Role
    created_at: datetime
