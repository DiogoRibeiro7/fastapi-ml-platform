import numpy as np
from fastapi.testclient import TestClient

from app.ml.drift import drift_severity, population_stability_index


def test_psi_identical_distributions_is_zero() -> None:
    """Identical baseline and observed distributions should have near-zero PSI."""

    rng = np.random.default_rng(0)
    values = rng.normal(size=1_000)
    assert population_stability_index(values, values) < 1e-6


def test_psi_empty_observed_returns_zero() -> None:
    """An empty observed sample should yield a PSI of zero, not an error."""

    assert population_stability_index([1.0, 2.0, 3.0], []) == 0.0


def test_psi_constant_baseline_returns_zero() -> None:
    """A constant baseline has too few bin edges to score, returning zero."""

    assert population_stability_index([5.0] * 100, [1.0, 2.0, 3.0]) == 0.0


def test_psi_shifted_distribution_is_positive() -> None:
    """A clearly shifted distribution should produce a positive PSI."""

    rng = np.random.default_rng(1)
    baseline = rng.normal(loc=0.0, size=1_000)
    observed = rng.normal(loc=3.0, size=1_000)
    assert population_stability_index(baseline, observed) > 0.2


def test_drift_severity_thresholds() -> None:
    """Severity labels should follow the standard PSI thresholds."""

    assert drift_severity(0.05) == "none"
    assert drift_severity(0.15) == "low"
    assert drift_severity(0.3) == "medium"
    assert drift_severity(0.8) == "high"


def test_submit_drift_job_and_fetch_report(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """A drift job should store a report retrievable by id and as latest."""

    report_id = client.post("/v1/drift/jobs", headers=auth_headers).json()["report_id"]

    by_id = client.get(f"/v1/drift/reports/{report_id}", headers=auth_headers)
    assert by_id.status_code == 200
    payload = by_id.json()
    assert payload["id"] == report_id
    assert payload["features"]
    assert payload["max_severity"] in {"none", "low", "medium", "high"}

    latest = client.get("/v1/drift/reports/latest", headers=auth_headers)
    assert latest.status_code == 200
    assert latest.json()["id"] == report_id


def test_latest_drift_report_404_when_none(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Latest should return 404 before any drift report is generated."""

    assert client.get("/v1/drift/reports/latest", headers=auth_headers).status_code == 404


def test_unknown_drift_report_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """An unknown drift report id should return 404."""

    response = client.get("/v1/drift/reports/nope", headers=auth_headers)
    assert response.status_code == 404
