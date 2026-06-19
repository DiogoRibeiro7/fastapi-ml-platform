from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "staging", "production"]

# Insecure development defaults that must be overridden in production.
_DEFAULT_API_KEY = "dev-api-key"
_DEFAULT_JWT_SECRET = "dev-jwt-secret-change-me"  # noqa: S105 - placeholder, rejected in prod
_DEFAULT_ADMIN_PASSWORD = "admin-password"  # noqa: S105 - placeholder, rejected in prod


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="FastAPI ML Platform")
    app_env: Environment = Field(default="development")
    log_level: str = Field(default="INFO")
    api_key: str = Field(default=_DEFAULT_API_KEY)

    jwt_secret: str = Field(default=_DEFAULT_JWT_SECRET)
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30, ge=1)
    bootstrap_admin_username: str | None = Field(default="admin")
    bootstrap_admin_password: str | None = Field(default=_DEFAULT_ADMIN_PASSWORD)

    database_url: str = Field(default="sqlite+aiosqlite:///./fraud_api.db")
    auto_create_tables: bool = Field(default=True)
    model_artifact_path: Path = Field(default=Path("artifacts/fraud_model.joblib"))
    model_metadata_path: Path = Field(default=Path("artifacts/fraud_model_metadata.json"))
    train_baseline_if_missing: bool = Field(default=True)
    enable_shap_explanations: bool = Field(default=False)

    enable_tracing: bool = Field(default=False)
    otel_service_name: str = Field(default="fastapi-ml-platform")
    otel_exporter_otlp_endpoint: str | None = Field(default=None)

    min_review_score: float = Field(default=0.65, ge=0.0, le=1.0)
    min_decline_score: float = Field(default=0.90, ge=0.0, le=1.0)
    max_batch_size: int = Field(default=100, ge=1, le=10_000)
    process_jobs_inline: bool = Field(default=False)
    job_backend: Literal["inprocess", "redis"] = Field(default="inprocess")
    redis_url: str = Field(default="redis://localhost:6379/0")
    scheduled_report_interval_seconds: int | None = Field(default=None, ge=1)
    data_retention_days: int | None = Field(default=None, ge=1)
    retention_cleanup_interval_seconds: int | None = Field(default=None, ge=1)
    max_ingest_records: int = Field(default=10_000, ge=1)
    rate_limit_requests: int = Field(default=120, ge=0)
    rate_limit_window_seconds: int = Field(default=60, ge=1)
    max_request_bytes: int = Field(default=1_048_576, ge=0)

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        """Normalize log-level values to the form expected by logging."""

        return value.upper()

    @model_validator(mode="after")
    def enforce_production_hardening(self) -> "Settings":
        """Reject insecure development defaults when running in production."""

        if self.app_env != "production":
            return self

        insecure = []
        if self.api_key == _DEFAULT_API_KEY:
            insecure.append("API_KEY")
        if self.jwt_secret == _DEFAULT_JWT_SECRET:
            insecure.append("JWT_SECRET")
        if self.bootstrap_admin_password == _DEFAULT_ADMIN_PASSWORD:
            insecure.append("BOOTSTRAP_ADMIN_PASSWORD")

        if insecure:
            raise ValueError(
                "Insecure default values are not allowed when APP_ENV=production: "
                + ", ".join(insecure)
            )
        return self


@lru_cache(maxsize=1)
def get_cached_settings() -> Settings:
    """Return cached settings for non-request contexts."""

    return Settings()
