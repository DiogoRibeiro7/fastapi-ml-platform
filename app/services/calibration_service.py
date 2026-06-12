from datetime import UTC, datetime

from app.ml.calibration import calibration_report
from app.ml.holdout import labeled_holdout_scores
from app.ml.model_loader import ModelBundle
from app.schemas.calibration import CalibrationBin, CalibrationReportResponse


class CalibrationService:
    """Business logic for model calibration reports.

    Production prediction logs do not carry ground-truth fraud labels, so
    calibration is measured on a freshly generated, seeded labeled holdout.
    The seed keeps the report deterministic for a given model.
    """

    def __init__(
        self,
        model_bundle: ModelBundle,
        sample_size: int = 2_000,
        n_bins: int = 10,
        seed: int = 123,
    ) -> None:
        self._model_bundle = model_bundle
        self._sample_size = sample_size
        self._n_bins = n_bins
        self._seed = seed

    def current_report(self) -> CalibrationReportResponse:
        """Score the active model on a labeled holdout and report calibration."""

        labels, probabilities = labeled_holdout_scores(
            self._model_bundle, sample_size=self._sample_size, seed=self._seed
        )
        report = calibration_report(labels, probabilities, n_bins=self._n_bins)

        return CalibrationReportResponse(
            generated_at=datetime.now(UTC),
            model_version=self._model_bundle.version,
            sample_size=report["sample_size"],
            brier_score=report["brier_score"],
            expected_calibration_error=report["expected_calibration_error"],
            bins=[CalibrationBin(**item) for item in report["bins"]],
        )
