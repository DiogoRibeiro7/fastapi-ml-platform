from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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
    max_severity: DriftSeverity
    features: list[FeatureDriftResult]
    summary: str


class StoredDriftReportResponse(DriftReportResponse):
    """A drift report persisted in the database."""

    model_config = ConfigDict(from_attributes=True)

    id: str


class DriftJobResponse(BaseModel):
    """Acknowledgement for a scheduled drift-computation job."""

    report_id: str
