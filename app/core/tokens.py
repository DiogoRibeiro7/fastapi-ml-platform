from datetime import datetime, timedelta
from typing import Any

import jwt

from app.core.principal import Role


class TokenError(Exception):
    """Raised when a token is missing, malformed, or expired."""


def create_access_token(
    *,
    subject: str,
    role: Role,
    secret: str,
    algorithm: str,
    issued_at: datetime,
    expires_minutes: int,
) -> str:
    """Create a signed JWT access token for a user."""

    payload = {
        "sub": subject,
        "role": role,
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_access_token(token: str, *, secret: str, algorithm: str) -> dict[str, Any]:
    """Decode and verify a JWT access token, raising TokenError on failure."""

    try:
        payload: dict[str, Any] = jwt.decode(token, secret, algorithms=[algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Token is invalid.") from exc
    return payload
