from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="FastAPI ML Platform")
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    api_key: str = Field(default="dev-api-key")

    database_url: str = Field(default="sqlite+aiosqlite:///./fraud_api.db")
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
    scheduled_report_interval_seconds: int | None = Field(default=None, ge=1)
    max_ingest_records: int = Field(default=10_000, ge=1)

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        """Normalize log-level values to the form expected by logging."""

        return value.upper()


@lru_cache(maxsize=1)
def get_cached_settings() -> Settings:
    """Return cached settings for non-request contexts."""

    return Settings()
