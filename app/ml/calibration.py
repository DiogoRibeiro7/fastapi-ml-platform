from typing import Any

import numpy as np
from numpy.typing import NDArray


def brier_score(y_true: NDArray[Any], y_prob: NDArray[Any]) -> float:
    """Return the Brier score (mean squared error of probabilities)."""

    true = np.asarray(y_true, dtype=np.float64)
    prob = np.asarray(y_prob, dtype=np.float64)
    return float(np.mean((prob - true) ** 2))


def calibration_bins(
    y_true: NDArray[Any],
    y_prob: NDArray[Any],
    n_bins: int = 10,
) -> list[dict[str, float]]:
    """Bin predictions into equal-width probability bins.

    Each bin reports its range, sample count, mean predicted probability, and
    observed positive frequency, which together form a reliability diagram.
    """

    true = np.asarray(y_true, dtype=np.float64)
    prob = np.asarray(y_prob, dtype=np.float64)
    edges = np.linspace(0.0, 1.0, n_bins + 1)

    bins: list[dict[str, float]] = []
    for index in range(n_bins):
        lower = edges[index]
        upper = edges[index + 1]
        # The last bin includes its upper edge so probability 1.0 is counted.
        if index == n_bins - 1:
            mask = (prob >= lower) & (prob <= upper)
        else:
            mask = (prob >= lower) & (prob < upper)

        count = int(mask.sum())
        bins.append(
            {
                "lower": float(lower),
                "upper": float(upper),
                "count": count,
                "mean_predicted": float(prob[mask].mean()) if count else 0.0,
                "observed_frequency": float(true[mask].mean()) if count else 0.0,
            }
        )
    return bins


def expected_calibration_error(bins: list[dict[str, float]], total: int) -> float:
    """Return the count-weighted gap between predicted and observed frequency."""

    if total <= 0:
        return 0.0

    error = 0.0
    for current_bin in bins:
        count = current_bin["count"]
        if count == 0:
            continue
        gap = abs(current_bin["mean_predicted"] - current_bin["observed_frequency"])
        error += (count / total) * gap
    return float(error)


def calibration_report(
    y_true: NDArray[Any],
    y_prob: NDArray[Any],
    n_bins: int = 10,
) -> dict[str, Any]:
    """Compute Brier score, expected calibration error, and reliability bins."""

    bins = calibration_bins(y_true, y_prob, n_bins=n_bins)
    total = int(np.asarray(y_true).shape[0])
    return {
        "sample_size": total,
        "brier_score": brier_score(y_true, y_prob),
        "expected_calibration_error": expected_calibration_error(bins, total),
        "bins": bins,
    }
