import numpy as np
from fastapi.testclient import TestClient

from app.ml.calibration import (
    brier_score,
    calibration_bins,
    calibration_report,
    expected_calibration_error,
)


def test_brier_score_perfect_and_worst() -> None:
    """Brier score is 0 for perfect predictions and 1 for fully wrong ones."""

    assert brier_score(np.array([1, 0, 1, 0]), np.array([1.0, 0.0, 1.0, 0.0])) == 0.0
    assert brier_score(np.array([1, 0]), np.array([0.0, 1.0])) == 1.0


def test_expected_calibration_error_detects_miscalibration() -> None:
    """A confident-but-wrong model should show a large calibration error."""

    y_true = np.array([1, 1, 0, 0])
    y_prob = np.array([0.0, 0.0, 0.0, 0.0])  # predicts 0 while half are positive

    bins = calibration_bins(y_true, y_prob, n_bins=10)
    error = expected_calibration_error(bins, total=len(y_true))

    assert brier_score(y_true, y_prob) == 0.5
    assert error == 0.5


def test_expected_calibration_error_is_zero_when_consistent() -> None:
    """A bin whose mean prediction matches its observed frequency has no error."""

    y_true = np.zeros(20, dtype=int)
    y_prob = np.zeros(20, dtype=float)

    bins = calibration_bins(y_true, y_prob)
    assert expected_calibration_error(bins, total=20) == 0.0


def test_calibration_report_bins_cover_all_samples() -> None:
    """Every sample should fall into exactly one reliability bin."""

    rng = np.random.default_rng(0)
    y_prob = rng.uniform(0.0, 1.0, size=500)
    y_true = rng.binomial(1, y_prob)

    report = calibration_report(y_true, y_prob, n_bins=10)

    assert report["sample_size"] == 500
    assert sum(item["count"] for item in report["bins"]) == 500
    assert 0.0 <= report["brier_score"] <= 1.0
    assert 0.0 <= report["expected_calibration_error"] <= 1.0


def test_calibration_report_endpoint(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """The calibration endpoint should return a report for the active model."""

    response = client.get("/v1/calibration/report", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_version"] == "rule-based-v1"
    assert payload["sample_size"] > 0
    assert 0.0 <= payload["brier_score"] <= 1.0
    assert 0.0 <= payload["expected_calibration_error"] <= 1.0
    assert sum(item["count"] for item in payload["bins"]) == payload["sample_size"]


def test_calibration_endpoint_requires_api_key(client: TestClient) -> None:
    """The calibration endpoint should reject unauthenticated requests."""

    response = client.get("/v1/calibration/report")

    assert response.status_code == 401
