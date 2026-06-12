from typing import Any

import numpy as np
from numpy.typing import NDArray


def optimize_threshold(
    y_true: NDArray[Any],
    y_prob: NDArray[Any],
    cost_false_positive: float,
    cost_false_negative: float,
    n_thresholds: int = 101,
) -> dict[str, Any]:
    """Find the decision threshold that minimizes total business cost.

    A transaction is flagged (declined) when its probability is at or above the
    threshold. Total cost is ``cost_fp * false_positives + cost_fn *
    false_negatives``; correct decisions are free. The threshold grid is swept
    over [0, 1] and ties are broken toward the higher threshold, which flags
    fewer legitimate transactions.
    """

    true = np.asarray(y_true, dtype=np.int64)
    prob = np.asarray(y_prob, dtype=np.float64)
    positives = true == 1
    negatives = ~positives

    thresholds = np.linspace(0.0, 1.0, n_thresholds)
    curve: list[dict[str, float]] = []
    best: dict[str, Any] | None = None

    for threshold in thresholds:
        flagged = prob >= threshold
        false_positives = int(np.sum(flagged & negatives))
        false_negatives = int(np.sum(~flagged & positives))
        total_cost = (
            cost_false_positive * false_positives + cost_false_negative * false_negatives
        )

        point = {
            "threshold": float(threshold),
            "total_cost": float(total_cost),
            "false_positives": false_positives,
            "false_negatives": false_negatives,
        }
        curve.append(point)

        # `<=` keeps updating on ties, so the highest tied threshold wins.
        if best is None or total_cost <= best["total_cost"]:
            true_positives = int(np.sum(flagged & positives))
            true_negatives = int(np.sum(~flagged & negatives))
            best = {
                "threshold": float(threshold),
                "total_cost": float(total_cost),
                "true_positives": true_positives,
                "false_positives": false_positives,
                "true_negatives": true_negatives,
                "false_negatives": false_negatives,
            }

    assert best is not None  # n_thresholds >= 1 guarantees one point
    return {
        "sample_size": int(true.shape[0]),
        "recommended_threshold": best["threshold"],
        "expected_cost": best["total_cost"],
        "confusion": {
            "true_positives": best["true_positives"],
            "false_positives": best["false_positives"],
            "true_negatives": best["true_negatives"],
            "false_negatives": best["false_negatives"],
        },
        "curve": curve,
    }
