from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy ORM models."""


class PredictionLog(Base):
    """Persisted record of a single model prediction."""

    __tablename__ = "prediction_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(String(128), index=True, unique=True)
    customer_id: Mapped[str] = mapped_column(String(128), index=True)
    risk_score: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(32), index=True)
    decision: Mapped[str] = mapped_column(String(32), index=True)
    model_version: Mapped[str] = mapped_column(String(128), index=True)
    features: Mapped[dict[str, float]] = mapped_column(JSON)
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    top_features: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RegisteredModel(Base):
    """A model registered in the model registry."""

    __tablename__ = "model_registry"
    __table_args__ = (UniqueConstraint("name", "version", name="uq_model_name_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    version: Mapped[str] = mapped_column(String(128))
    artifact_path: Mapped[str] = mapped_column(String(512))
    training_dataset: Mapped[str] = mapped_column(String(256))
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
