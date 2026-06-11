"""Train and persist the baseline fraud model.

The dataset is synthetic so the repository works without external data. The
generator is seeded, which makes training deterministic and therefore safe to
run automatically at application startup or during image builds.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from numpy.typing import NDArray
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.ml.feature_pipeline import FEATURE_NAMES

MODEL_NAME = "synthetic-fraud-risk-model"
MODEL_VERSION = "sklearn-logistic-v1"


def make_synthetic_dataset(
    n_samples: int = 15_000, seed: int = 42
) -> tuple[NDArray[np.float64], NDArray[np.int64]]:
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


def train_baseline_model(
    artifact_path: Path,
    metadata_path: Path,
    n_samples: int = 15_000,
    seed: int = 42,
) -> dict[str, Any]:
    """Train the baseline classifier and persist the artifact and metadata.

    Returns the metadata dictionary that was written next to the artifact.
    """

    X, y = make_synthetic_dataset(n_samples=n_samples, seed=seed)
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=seed,
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

    metadata: dict[str, Any] = {
        "name": MODEL_NAME,
        "version": MODEL_VERSION,
        "features": FEATURE_NAMES,
        "metrics": metrics,
    }

    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, artifact_path)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata
