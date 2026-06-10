from collections.abc import Iterable, Mapping

import numpy as np


def population_stability_index(
    baseline: Iterable[float],
    observed: Iterable[float],
    bins: int = 10,
) -> float:
    """Compute Population Stability Index for one numeric feature."""

    baseline_array = np.asarray(list(baseline), dtype=np.float64)
    observed_array = np.asarray(list(observed), dtype=np.float64)

    if baseline_array.size == 0 or observed_array.size == 0:
        return 0.0

    quantiles = np.linspace(0.0, 1.0, bins + 1)
    breakpoints = np.unique(np.quantile(baseline_array, quantiles))
    if breakpoints.size < 2:
        return 0.0

    baseline_counts, _ = np.histogram(baseline_array, bins=breakpoints)
    observed_counts, _ = np.histogram(observed_array, bins=breakpoints)

    epsilon = 1e-6
    baseline_share = baseline_counts / max(baseline_counts.sum(), 1)
    observed_share = observed_counts / max(observed_counts.sum(), 1)

    baseline_share = np.where(baseline_share == 0, epsilon, baseline_share)
    observed_share = np.where(observed_share == 0, epsilon, observed_share)

    psi_values = (observed_share - baseline_share) * np.log(observed_share / baseline_share)
    return float(np.sum(psi_values))


def drift_severity(psi: float) -> str:
    """Map PSI values to a practical severity label."""

    if psi < 0.1:
        return "none"
    if psi < 0.2:
        return "low"
    if psi < 0.5:
        return "medium"
    return "high"


def baseline_from_feature_names(feature_names: Iterable[str]) -> dict[str, list[float]]:
    """Create a deterministic synthetic baseline distribution.

    A production system should load this from the training dataset profile.
    """

    rng = np.random.default_rng(seed=42)
    baseline: dict[str, list[float]] = {}
    for feature in feature_names:
        if feature == "amount":
            values = rng.gamma(shape=2.0, scale=80.0, size=500)
        elif feature == "amount_ratio":
            values = rng.lognormal(mean=0.1, sigma=0.5, size=500)
        elif feature in {"country_mismatch", "is_night", "is_weekend", "is_card_not_present"}:
            values = rng.binomial(n=1, p=0.2, size=500)
        elif feature == "customer_age_days":
            values = rng.integers(low=1, high=2_000, size=500)
        else:
            values = rng.poisson(lam=2.0, size=500)
        baseline[feature] = [float(item) for item in values]
    return baseline


def observed_feature_values(
    rows: Iterable[Mapping[str, float]],
    feature_name: str,
) -> list[float]:
    """Extract observed values for one feature from stored feature rows."""

    return [float(row[feature_name]) for row in rows if feature_name in row]
