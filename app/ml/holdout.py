from typing import Any

import numpy as np
from numpy.typing import NDArray

from app.ml.model_loader import ModelBundle


def labeled_holdout_scores(
    bundle: ModelBundle,
    sample_size: int = 2_000,
    seed: int = 123,
) -> tuple[NDArray[Any], NDArray[Any]]:
    """Score the model on a seeded labeled holdout.

    Production prediction logs carry no ground-truth labels, so model-quality
    reports (calibration, threshold tuning) measure the active model on a
    freshly generated, seeded synthetic holdout. The seed keeps reports
    deterministic for a given model.

    Returns a tuple of (labels, positive-class probabilities).
    """

    from app.ml.training import make_synthetic_dataset

    features, labels = make_synthetic_dataset(n_samples=sample_size, seed=seed)
    probabilities = np.asarray(bundle.model.predict_proba(features))[:, 1]
    return labels, probabilities
