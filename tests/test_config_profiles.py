import pytest
from pydantic import ValidationError

from app.core.config import (
    _DEFAULT_ADMIN_PASSWORD,
    _DEFAULT_API_KEY,
    _DEFAULT_JWT_SECRET,
    Settings,
)

SECURE = "a-secure-value-1234567890"


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "app_env": "production",
        "api_key": SECURE,
        "jwt_secret": SECURE,
        "bootstrap_admin_password": SECURE,
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type]


def test_production_with_secure_values_is_valid() -> None:
    """Production settings with all secrets overridden should be accepted."""

    settings = _settings()
    assert settings.app_env == "production"


def test_production_rejects_default_api_key() -> None:
    """A default API key must be rejected in production."""

    with pytest.raises(ValidationError, match="API_KEY"):
        _settings(api_key=_DEFAULT_API_KEY)


def test_production_rejects_default_jwt_secret() -> None:
    """A default JWT secret must be rejected in production."""

    with pytest.raises(ValidationError, match="JWT_SECRET"):
        _settings(jwt_secret=_DEFAULT_JWT_SECRET)


def test_production_rejects_default_admin_password() -> None:
    """A default bootstrap admin password must be rejected in production."""

    with pytest.raises(ValidationError, match="BOOTSTRAP_ADMIN_PASSWORD"):
        _settings(bootstrap_admin_password=_DEFAULT_ADMIN_PASSWORD)


def test_development_allows_defaults() -> None:
    """Development keeps the convenient defaults without hardening."""

    settings = Settings(_env_file=None, app_env="development")  # type: ignore[arg-type]
    assert settings.api_key == _DEFAULT_API_KEY
    assert settings.jwt_secret == _DEFAULT_JWT_SECRET


def test_staging_is_not_hardened() -> None:
    """Staging does not enforce production hardening."""

    settings = Settings(_env_file=None, app_env="staging")  # type: ignore[arg-type]
    assert settings.app_env == "staging"


def test_unknown_environment_is_rejected() -> None:
    """Only the known profiles are accepted for app_env."""

    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="qa")  # type: ignore[arg-type]
