from datetime import datetime

from pydantic import BaseModel, Field


class CalibrationBin(BaseModel):
    """One reliability-diagram bin."""

    lower: float
    upper: float
    count: int
    mean_predicted: float
    observed_frequency: float


class CalibrationReportResponse(BaseModel):
    """Calibration report for the active model on a labeled holdout."""

    generated_at: datetime
    model_version: str
    sample_size: int
    brier_score: float = Field(ge=0.0, le=1.0)
    expected_calibration_error: float = Field(ge=0.0, le=1.0)
    bins: list[CalibrationBin]
