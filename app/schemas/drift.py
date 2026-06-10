from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DriftSeverity = Literal["none", "low", "medium", "high"]


class FeatureDriftResult(BaseModel):
    """Drift result for one feature."""

    feature: str
    psi: float = Field(ge=0.0)
    severity: DriftSeverity


class DriftReportResponse(BaseModel):
    """PSI-based drift report."""

    generated_at: datetime
    sample_size: int
    features: list[FeatureDriftResult]
    summary: str
