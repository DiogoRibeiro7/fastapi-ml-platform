from pydantic import BaseModel, Field


class ModelMetricsResponse(BaseModel):
    """Operational model metrics computed from logged predictions."""

    prediction_count: int = Field(ge=0)
    average_risk_score: float = Field(ge=0.0, le=1.0)
    risk_level_counts: dict[str, int]
    decision_counts: dict[str, int]
