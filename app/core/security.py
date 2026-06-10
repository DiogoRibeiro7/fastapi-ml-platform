from secrets import compare_digest

from fastapi import HTTPException, status


def validate_api_key(provided_key: str | None, expected_key: str) -> None:
    """Validate an API key using constant-time comparison."""

    if provided_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key.",
        )

    if not compare_digest(provided_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key.",
        )
