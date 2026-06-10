"""Train a small synthetic fraud classifier for local demos.

This script intentionally uses generated data so the repository works without
external datasets. For a real portfolio extension, replace this with a public
fraud dataset and a reproducible feature-building pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.ml.feature_pipeline import FEATURE_NAMES

ARTIFACT_DIR = Path("artifacts")
MODEL_PATH = ARTIFACT_DIR / "fraud_model.joblib"
METADATA_PATH = ARTIFACT_DIR / "fraud_model_metadata.json"


def make_synthetic_dataset(n_samples: int = 15_000, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    """Create synthetic feature data with a known fraud-risk mechanism."""

    rng = np.random.default_rng(seed)

    amount = rng.gamma(shape=2.0, scale=80.0, size=n_samples)
    avg_amount = np.maximum(rng.gamma(shape=2.0, scale=60.0, size=n_samples), 1.0)
    amount_ratio = amount / avg_amount
    country_mismatch = rng.binomial(1, 0.08, size=n_samples)
    is_night = rng.binomial(1, 0.18, size=n_samples)
    is_weekend = rng.binomial(1, 0.28, size=n_samples)
    is_card_not_present = rng.binomial(1, 0.35, size=n_samples)
    customer_age_days = rng.integers(1, 2_000, size=n_samples)
    num_transactions_last_24h = rng.poisson(3.0, size=n_samples)
    chargeback_count_last_90d = rng.poisson(0.15, size=n_samples)
    high_risk_merchant_category = rng.binomial(1, 0.18, size=n_samples)

    X = np.column_stack(
        [
            amount,
            amount_ratio,
            country_mismatch,
            is_night,
            is_weekend,
            is_card_not_present,
            customer_age_days,
            num_transactions_last_24h,
            chargeback_count_last_90d,
            high_risk_merchant_category,
        ]
    )

    logits = (
        -4.2
        + 0.0012 * amount
        + 0.50 * amount_ratio
        + 1.10 * country_mismatch
        + 0.35 * is_night
        + 0.20 * is_weekend
        + 0.55 * is_card_not_present
        - 0.002 * customer_age_days
        + 0.12 * num_transactions_last_24h
        + 1.25 * chargeback_count_last_90d
        + 0.60 * high_risk_merchant_category
    )
    probability = 1.0 / (1.0 + np.exp(-logits))
    y = rng.binomial(1, probability)
    return X.astype(np.float64), y.astype(np.int64)


def main() -> None:
    """Train and persist the demo model."""

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    X, y = make_synthetic_dataset()
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )

    model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(max_iter=1_000, class_weight="balanced")),
        ]
    )
    model.fit(X_train, y_train)
    probabilities = model.predict_proba(X_test)[:, 1]

    metrics = {
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "average_precision": float(average_precision_score(y_test, probabilities)),
        "positive_rate": float(y.mean()),
    }

    joblib.dump(model, MODEL_PATH)
    metadata = {
        "name": "synthetic-fraud-risk-model",
        "version": "sklearn-logistic-v1",
        "features": FEATURE_NAMES,
        "metrics": metrics,
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"Saved model to {MODEL_PATH}")
    print(f"Saved metadata to {METADATA_PATH}")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
