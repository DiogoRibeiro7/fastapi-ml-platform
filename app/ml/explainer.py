from collections.abc import Mapping

from app.schemas.prediction import FeatureContribution


def top_feature_contributions(
    features: Mapping[str, float],
    coefficients: Mapping[str, float],
    limit: int = 5,
) -> list[FeatureContribution]:
    """Return the largest absolute feature contributions.

    This is a lightweight local explanation for linear or rule-based models.
    A future extension can replace this with SHAP values for supported models.
    """

    contributions = [
        FeatureContribution(name=name, impact=float(value * coefficients.get(name, 0.0)))
        for name, value in features.items()
    ]
    return sorted(contributions, key=lambda item: abs(item.impact), reverse=True)[:limit]
