from app.ml.holdout import labeled_holdout_scores
from app.ml.model_loader import ModelBundle
from app.ml.threshold import optimize_threshold
from app.schemas.threshold import (
    ConfusionCounts,
    ThresholdCostPoint,
    ThresholdOptimizationRequest,
    ThresholdOptimizationResponse,
)


class ThresholdOptimizationService:
    """Business logic for cost-based decision-threshold optimization."""

    def __init__(
        self,
        model_bundle: ModelBundle,
        sample_size: int = 2_000,
        seed: int = 123,
    ) -> None:
        self._model_bundle = model_bundle
        self._sample_size = sample_size
        self._seed = seed

    def optimize(
        self, request: ThresholdOptimizationRequest
    ) -> ThresholdOptimizationResponse:
        """Recommend the decision threshold that minimizes business cost."""

        labels, probabilities = labeled_holdout_scores(
            self._model_bundle, sample_size=self._sample_size, seed=self._seed
        )
        result = optimize_threshold(
            labels,
            probabilities,
            cost_false_positive=request.cost_false_positive,
            cost_false_negative=request.cost_false_negative,
            n_thresholds=request.n_thresholds,
        )

        return ThresholdOptimizationResponse(
            model_version=self._model_bundle.version,
            sample_size=result["sample_size"],
            cost_false_positive=request.cost_false_positive,
            cost_false_negative=request.cost_false_negative,
            recommended_threshold=result["recommended_threshold"],
            expected_cost=result["expected_cost"],
            confusion=ConfusionCounts(**result["confusion"]),
            curve=[ThresholdCostPoint(**point) for point in result["curve"]],
        )
