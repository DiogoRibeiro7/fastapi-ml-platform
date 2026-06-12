from datetime import UTC, datetime

from app.ml.evaluation import evaluate_predictions
from app.ml.holdout import labeled_holdout_scores
from app.ml.model_loader import ModelBundle
from app.schemas.evaluation import EvaluationReportResponse
from app.schemas.threshold import ConfusionCounts


class EvaluationService:
    """Business logic for offline model evaluation reports."""

    def __init__(
        self,
        model_bundle: ModelBundle,
        default_threshold: float = 0.5,
        sample_size: int = 2_000,
        seed: int = 123,
    ) -> None:
        self._model_bundle = model_bundle
        self._default_threshold = default_threshold
        self._sample_size = sample_size
        self._seed = seed

    def current_report(self, threshold: float | None = None) -> EvaluationReportResponse:
        """Evaluate the active model on a labeled holdout at a decision threshold."""

        labels, probabilities = labeled_holdout_scores(
            self._model_bundle, sample_size=self._sample_size, seed=self._seed
        )
        report = evaluate_predictions(
            labels,
            probabilities,
            threshold=self._default_threshold if threshold is None else threshold,
        )

        return EvaluationReportResponse(
            generated_at=datetime.now(UTC),
            model_version=self._model_bundle.version,
            sample_size=report["sample_size"],
            threshold=report["threshold"],
            positive_rate=report["positive_rate"],
            roc_auc=report["roc_auc"],
            average_precision=report["average_precision"],
            brier_score=report["brier_score"],
            expected_calibration_error=report["expected_calibration_error"],
            precision=report["precision"],
            recall=report["recall"],
            f1=report["f1"],
            accuracy=report["accuracy"],
            confusion=ConfusionCounts(**report["confusion"]),
        )
