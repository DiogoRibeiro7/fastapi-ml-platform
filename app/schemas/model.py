from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelMetadataResponse(BaseModel):
    """Metadata for the active model."""

    name: str
    version: str
    model_type: str
    features: list[str]
    metrics: dict[str, Any] = Field(default_factory=dict)
    loaded_from: str
    loaded_at: datetime


class ModelRegistrationRequest(BaseModel):
    """Request payload for registering a model version."""

    name: str = Field(min_length=1, max_length=128)
    version: str = Field(min_length=1, max_length=128)
    artifact_path: str = Field(min_length=1, max_length=512)
    training_dataset: str = Field(min_length=1, max_length=256)
    metrics: dict[str, Any] = Field(default_factory=dict)


class RegisteredModelResponse(BaseModel):
    """A registered model as stored in the registry."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    version: str
    artifact_path: str
    training_dataset: str
    metrics: dict[str, Any]
    is_active: bool
    created_at: datetime


class RegisteredModelListResponse(BaseModel):
    """List of registered models."""

    models: list[RegisteredModelResponse]
