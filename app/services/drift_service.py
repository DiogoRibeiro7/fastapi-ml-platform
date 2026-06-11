from datetime import UTC, datetime

from app.ml.drift import (
    baseline_from_feature_names,
    drift_severity,
    observed_feature_values,
    population_stability_index,
)
from app.ml.feature_pipeline import FEATURE_NAMES
from app.repositories.prediction_repository import PredictionRepository
from app.schemas.drift import DriftReportResponse, FeatureDriftResult


class DriftService:
    """Business logic for feature-drift reports."""

    def __init__(self, repository: PredictionRepository) -> None:
        self._repository = repository

    async def current_report(self) -> DriftReportResponse:
        """Return a PSI-based drift report for recent predictions."""

        rows = await self._repository.list_recent(limit=500)
        observed_rows = [row.features for row in rows]
        baseline = baseline_from_feature_names(FEATURE_NAMES)

        feature_results: list[FeatureDriftResult] = []
        for feature_name in FEATURE_NAMES:
            observed = observed_feature_values(observed_rows, feature_name)
            psi = population_stability_index(
                baseline=baseline[feature_name],
                observed=observed,
            )
            feature_results.append(
                FeatureDriftResult(
                    feature=feature_name,
                    psi=psi,
                    severity=drift_severity(psi),  # type: ignore[arg-type]
                )
            )

        max_severity = self._max_severity(feature_results)
        if not rows:
            summary = "No prediction data is available yet. Drift is reported as none."
        else:
            summary = f"Recent prediction features show {max_severity} drift severity."

        return DriftReportResponse(
            generated_at=datetime.now(UTC),
            sample_size=len(rows),
            features=feature_results,
            summary=summary,
        )

    @staticmethod
    def _max_severity(results: list[FeatureDriftResult]) -> str:
        """Return the highest severity from feature-level results."""

        severity_order = {"none": 0, "low": 1, "medium": 2, "high": 3}
        if not results:
            return "none"
        return max(results, key=lambda item: severity_order[item.severity]).severity
