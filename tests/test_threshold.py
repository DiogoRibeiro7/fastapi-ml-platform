import numpy as np
from fastapi.testclient import TestClient

from app.ml.threshold import optimize_threshold


def test_high_false_negative_cost_lowers_threshold() -> None:
    """When missing fraud is expensive, the recommended threshold should drop."""

    y_true = np.array([1, 1, 0, 0])
    y_prob = np.array([0.4, 0.6, 0.3, 0.2])

    cheap_fn = optimize_threshold(
        y_true, y_prob, cost_false_positive=10.0, cost_false_negative=1.0
    )
    costly_fn = optimize_threshold(
        y_true, y_prob, cost_false_positive=1.0, cost_false_negative=100.0
    )

    assert costly_fn["recommended_threshold"] <= cheap_fn["recommended_threshold"]


def test_optimize_threshold_minimizes_total_cost() -> None:
    """The recommended threshold should have the minimum cost on the curve."""

    rng = np.random.default_rng(1)
    y_prob = rng.uniform(0.0, 1.0, size=200)
    y_true = rng.binomial(1, y_prob)

    result = optimize_threshold(
        y_true, y_prob, cost_false_positive=2.0, cost_false_negative=5.0, n_thresholds=51
    )

    min_curve_cost = min(point["total_cost"] for point in result["curve"])
    assert result["expected_cost"] == min_curve_cost
    confusion = result["confusion"]
    assert sum(confusion.values()) == result["sample_size"]


def test_optimize_threshold_zero_cost_is_free() -> None:
    """Zero costs make every threshold free, so cost is zero everywhere."""

    y_true = np.array([1, 0, 1, 0])
    y_prob = np.array([0.9, 0.1, 0.8, 0.2])

    result = optimize_threshold(y_true, y_prob, cost_false_positive=0.0, cost_false_negative=0.0)

    assert result["expected_cost"] == 0.0


def test_threshold_endpoint_returns_recommendation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """The endpoint should return a recommended threshold and a cost curve."""

    response = client.post(
        "/v1/threshold/optimize",
        headers=auth_headers,
        json={"cost_false_positive": 1.0, "cost_false_negative": 20.0, "n_thresholds": 51},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_version"] == "rule-based-v1"
    assert 0.0 <= payload["recommended_threshold"] <= 1.0
    assert payload["expected_cost"] >= 0.0
    assert len(payload["curve"]) == 51
    confusion = payload["confusion"]
    assert (
        confusion["true_positives"]
        + confusion["false_positives"]
        + confusion["true_negatives"]
        + confusion["false_negatives"]
        == payload["sample_size"]
    )


def test_threshold_endpoint_rejects_negative_cost(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Negative costs should fail request validation."""

    response = client.post(
        "/v1/threshold/optimize",
        headers=auth_headers,
        json={"cost_false_positive": -1.0, "cost_false_negative": 5.0},
    )

    assert response.status_code == 422
