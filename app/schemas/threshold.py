from pydantic import BaseModel, Field


class ThresholdOptimizationRequest(BaseModel):
    """Business costs used to optimize the decision threshold."""

    cost_false_positive: float = Field(
        ge=0.0, description="Cost of flagging a legitimate transaction."
    )
    cost_false_negative: float = Field(
        ge=0.0, description="Cost of missing a fraudulent transaction."
    )
    n_thresholds: int = Field(default=101, ge=2, le=1001)


class ConfusionCounts(BaseModel):
    """Confusion-matrix counts at a threshold."""

    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int


class ThresholdCostPoint(BaseModel):
    """Total cost and error counts at one threshold."""

    threshold: float
    total_cost: float
    false_positives: int
    false_negatives: int


class ThresholdOptimizationResponse(BaseModel):
    """Recommended cost-minimizing threshold and the full cost curve."""

    model_version: str
    sample_size: int
    cost_false_positive: float
    cost_false_negative: float
    recommended_threshold: float
    expected_cost: float
    confusion: ConfusionCounts
    curve: list[ThresholdCostPoint]
