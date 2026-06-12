import numpy as np
from fastapi.testclient import TestClient

from app.ml.evaluation import evaluate_predictions


def test_evaluate_perfect_separation() -> None:
    """A perfectly separating threshold should give precision and recall of 1."""

    y_true = np.array([1, 1, 0, 0])
    y_prob = np.array([0.9, 0.8, 0.2, 0.1])

    report = evaluate_predictions(y_true, y_prob, threshold=0.5)

    assert report["precision"] == 1.0
    assert report["recall"] == 1.0
    assert report["f1"] == 1.0
    assert report["accuracy"] == 1.0
    assert report["roc_auc"] == 1.0
    assert report["confusion"] == {
        "true_positives": 2,
        "false_positives": 0,
        "true_negatives": 2,
        "false_negatives": 0,
    }


def test_evaluate_single_class_has_no_ranking_metrics() -> None:
    """Ranking metrics are undefined when only one class is present."""

    y_true = np.array([0, 0, 0])
    y_prob = np.array([0.1, 0.2, 0.3])

    report = evaluate_predictions(y_true, y_prob, threshold=0.5)

    assert report["roc_auc"] is None
    assert report["average_precision"] is None
    assert report["positive_rate"] == 0.0


def test_evaluate_confusion_counts_sum_to_sample_size() -> None:
    """The confusion-matrix counts should always cover every sample."""

    rng = np.random.default_rng(2)
    y_prob = rng.uniform(0.0, 1.0, size=300)
    y_true = rng.binomial(1, y_prob)

    report = evaluate_predictions(y_true, y_prob, threshold=0.4)

    assert sum(report["confusion"].values()) == report["sample_size"] == 300


def test_evaluation_endpoint_uses_default_threshold(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """The endpoint should return a full report for the active model."""

    response = client.get("/v1/evaluation/report", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_version"] == "rule-based-v1"
    assert payload["threshold"] == 0.90  # default decline score
    assert payload["sample_size"] > 0
    assert 0.0 <= payload["roc_auc"] <= 1.0
    assert sum(payload["confusion"].values()) == payload["sample_size"]


def test_evaluation_endpoint_accepts_threshold_override(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """A threshold query parameter should override the default."""

    response = client.get(
        "/v1/evaluation/report", headers=auth_headers, params={"threshold": 0.5}
    )

    assert response.status_code == 200
    assert response.json()["threshold"] == 0.5


def test_evaluation_endpoint_rejects_out_of_range_threshold(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """A threshold outside [0, 1] should fail validation."""

    response = client.get(
        "/v1/evaluation/report", headers=auth_headers, params={"threshold": 1.5}
    )

    assert response.status_code == 422
