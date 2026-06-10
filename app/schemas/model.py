from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ModelMetadataResponse(BaseModel):
    """Metadata for the active model."""

    name: str
    version: str
    model_type: str
    features: list[str]
    metrics: dict[str, Any] = Field(default_factory=dict)
    loaded_from: str
    loaded_at: datetime
