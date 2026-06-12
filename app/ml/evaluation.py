from typing import Any

import numpy as np
from numpy.typing import NDArray
from sklearn.metrics import average_precision_score, roc_auc_score

from app.ml.calibration import brier_score, calibration_bins, expected_calibration_error


def evaluate_predictions(
    y_true: NDArray[Any],
    y_prob: NDArray[Any],
    threshold: float = 0.5,
    n_bins: int = 10,
) -> dict[str, Any]:
    """Compute a consolidated offline evaluation report.

    Combines threshold-independent ranking metrics (ROC AUC, average
    precision), calibration metrics (Brier score, expected calibration error),
    and threshold-dependent classification metrics (precision, recall, F1,
    accuracy, confusion counts). Ranking metrics are None when only one class
    is present, since they are undefined there.
    """

    true = np.asarray(y_true, dtype=np.int64)
    prob = np.asarray(y_prob, dtype=np.float64)
    total = int(true.shape[0])

    flagged = prob >= threshold
    true_positives = int(np.sum(flagged & (true == 1)))
    false_positives = int(np.sum(flagged & (true == 0)))
    true_negatives = int(np.sum(~flagged & (true == 0)))
    false_negatives = int(np.sum(~flagged & (true == 1)))

    predicted_positive = true_positives + false_positives
    actual_positive = true_positives + false_negatives
    precision = true_positives / predicted_positive if predicted_positive else 0.0
    recall = true_positives / actual_positive if actual_positive else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    accuracy = (true_positives + true_negatives) / total if total else 0.0

    both_classes_present = np.unique(true).shape[0] > 1
    roc_auc = float(roc_auc_score(true, prob)) if both_classes_present else None
    average_precision = (
        float(average_precision_score(true, prob)) if both_classes_present else None
    )

    bins = calibration_bins(true, prob, n_bins=n_bins)
    return {
        "sample_size": total,
        "threshold": float(threshold),
        "positive_rate": float(true.mean()) if total else 0.0,
        "roc_auc": roc_auc,
        "average_precision": average_precision,
        "brier_score": brier_score(true, prob),
        "expected_calibration_error": expected_calibration_error(bins, total),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "accuracy": float(accuracy),
        "confusion": {
            "true_positives": true_positives,
            "false_positives": false_positives,
            "true_negatives": true_negatives,
            "false_negatives": false_negatives,
        },
    }
