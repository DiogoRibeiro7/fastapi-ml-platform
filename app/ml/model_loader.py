import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from numpy.typing import NDArray

from app.ml.feature_pipeline import FEATURE_NAMES


class ProbabilityModel(Protocol):
    """Protocol implemented by any model that can estimate fraud probability."""

    def predict_proba(self, features: NDArray[Any]) -> NDArray[Any]:
        """Return class probabilities for a feature matrix."""


@dataclass(frozen=True)
class ModelBundle:
    """Loaded model and the metadata needed by the API layer."""

    model: ProbabilityModel
    name: str
    version: str
    model_type: str
    features: list[str]
    metrics: dict[str, Any]
    loaded_from: str
    loaded_at: datetime
    coefficients: dict[str, float]


class RuleBasedFraudModel:
    """Deterministic fallback fraud model.

    This model is intentionally simple, but it has the same `predict_proba`
    interface as a scikit-learn classifier. That keeps the rest of the app
    independent from the concrete model implementation.
    """

    coefficients: dict[str, float] = {
        "amount": 0.0015,
        "amount_ratio": 0.55,
        "country_mismatch": 1.20,
        "is_night": 0.45,
        "is_weekend": 0.20,
        "is_card_not_present": 0.65,
        "customer_age_days": -0.003,
        "num_transactions_last_24h": 0.18,
        "chargeback_count_last_90d": 1.10,
        "high_risk_merchant_category": 0.70,
    }
    intercept: float = -4.0

    def predict_proba(self, features: NDArray[Any]) -> NDArray[Any]:
        """Estimate probability using a logistic transformation."""

        import numpy as np

        weights = np.array(
            [self.coefficients[name] for name in FEATURE_NAMES],
            dtype=np.float64,
        )
        logits = self.intercept + features @ weights
        positive = 1.0 / (1.0 + np.exp(-logits))
        negative = 1.0 - positive
        return np.column_stack([negative, positive])


def _load_joblib_model(artifact_path: Path) -> ProbabilityModel | None:
    """Load a joblib model if the artifact exists."""

    if not artifact_path.exists():
        return None

    import joblib

    loaded_model = joblib.load(artifact_path)
    if not hasattr(loaded_model, "predict_proba"):
        raise TypeError("Loaded model must expose a predict_proba method.")
    return loaded_model


def _load_metadata(metadata_path: Path) -> dict[str, Any]:
    """Load optional model metadata from JSON."""

    if not metadata_path.exists():
        return {}

    with metadata_path.open("r", encoding="utf-8") as file:
        raw_metadata: dict[str, Any] = json.load(file)
    return raw_metadata


def _extract_coefficients(model: ProbabilityModel) -> dict[str, float]:
    """Extract linear-model coefficients when available."""

    if isinstance(model, RuleBasedFraudModel):
        return model.coefficients

    raw_coef = getattr(model, "coef_", None)
    if raw_coef is None:
        return {name: 0.0 for name in FEATURE_NAMES}

    values = raw_coef[0]
    return {name: float(values[index]) for index, name in enumerate(FEATURE_NAMES)}


def load_model_bundle(artifact_path: Path, metadata_path: Path) -> ModelBundle:
    """Load a persisted model or fall back to a deterministic demo model."""

    loaded_at = datetime.now(timezone.utc)
    model = _load_joblib_model(artifact_path)
    metadata = _load_metadata(metadata_path)

    if model is None:
        fallback_model = RuleBasedFraudModel()
        return ModelBundle(
            model=fallback_model,
            name="fallback-fraud-risk-model",
            version="rule-based-v1",
            model_type="rule_based_logistic_score",
            features=FEATURE_NAMES,
            metrics={"note": "Fallback model. Train a model with scripts/train_model.py."},
            loaded_from="fallback",
            loaded_at=loaded_at,
            coefficients=fallback_model.coefficients,
        )

    metrics = metadata.get("metrics", {})
    return ModelBundle(
        model=model,
        name=str(metadata.get("name", "fraud-risk-model")),
        version=str(metadata.get("version", "artifact-v1")),
        model_type=type(model).__name__,
        features=list(metadata.get("features", FEATURE_NAMES)),
        metrics=metrics if isinstance(metrics, dict) else {},
        loaded_from=str(artifact_path),
        loaded_at=loaded_at,
        coefficients=_extract_coefficients(model),
    )


def fraud_probability(model: ProbabilityModel, feature_array: NDArray[Any]) -> float:
    """Return the positive-class probability from a probability model."""

    probabilities = model.predict_proba(feature_array)
    probability = float(probabilities[0][1])
    if math.isnan(probability):
        raise ValueError("Model returned NaN probability.")
    return min(max(probability, 0.0), 1.0)
