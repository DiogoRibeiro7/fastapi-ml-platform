from collections.abc import Mapping

from app.schemas.prediction import FeatureContribution


def top_contributions_from_impacts(
    impacts: Mapping[str, float],
    limit: int = 5,
) -> list[FeatureContribution]:
    """Return the largest absolute feature impacts as contribution items.

    The impacts are already per-feature contribution values, so this is shared
    by both the linear and SHAP explanation paths.
    """

    contributions = [
        FeatureContribution(name=name, impact=float(value)) for name, value in impacts.items()
    ]
    return sorted(contributions, key=lambda item: abs(item.impact), reverse=True)[:limit]


def top_feature_contributions(
    features: Mapping[str, float],
    coefficients: Mapping[str, float],
    limit: int = 5,
) -> list[FeatureContribution]:
    """Return the largest absolute feature contributions for a linear model.

    This is a lightweight local explanation for linear or rule-based models,
    used as the fallback when SHAP explanations are disabled or unavailable.
    """

    impacts = {
        name: float(value * coefficients.get(name, 0.0)) for name, value in features.items()
    }
    return top_contributions_from_impacts(impacts, limit=limit)
