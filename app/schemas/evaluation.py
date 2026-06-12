from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.threshold import ConfusionCounts


class EvaluationReportResponse(BaseModel):
    """Consolidated offline evaluation report for a model on a labeled holdout."""

    generated_at: datetime
    model_version: str
    sample_size: int
    threshold: float
    positive_rate: float
    roc_auc: float | None
    average_precision: float | None
    brier_score: float = Field(ge=0.0, le=1.0)
    expected_calibration_error: float = Field(ge=0.0, le=1.0)
    precision: float
    recall: float
    f1: float
    accuracy: float
    confusion: ConfusionCounts
