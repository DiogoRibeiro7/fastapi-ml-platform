"""Train the baseline fraud classifier and save it under artifacts/.

Training logic lives in app.ml.training so the application can also train the
baseline automatically at startup when no artifact exists.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.ml.training import train_baseline_model

ARTIFACT_DIR = Path("artifacts")
MODEL_PATH = ARTIFACT_DIR / "fraud_model.joblib"
METADATA_PATH = ARTIFACT_DIR / "fraud_model_metadata.json"


def main() -> None:
    """Train and persist the baseline model."""

    metadata = train_baseline_model(MODEL_PATH, METADATA_PATH)
    print(f"Saved model to {MODEL_PATH}")
    print(f"Saved metadata to {METADATA_PATH}")
    print(json.dumps(metadata["metrics"], indent=2))


if __name__ == "__main__":
    main()
