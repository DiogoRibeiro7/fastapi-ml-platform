"""Evaluate a saved model offline and write a JSON evaluation report.

Loads the current artifact (or the rule-based fallback), scores it on a seeded
labeled holdout, and writes a consolidated report to artifacts/.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.ml.evaluation import evaluate_predictions
from app.ml.holdout import labeled_holdout_scores
from app.ml.model_loader import load_model_bundle

ARTIFACT_DIR = Path("artifacts")
MODEL_PATH = ARTIFACT_DIR / "fraud_model.joblib"
METADATA_PATH = ARTIFACT_DIR / "fraud_model_metadata.json"
REPORT_PATH = ARTIFACT_DIR / "evaluation_report.json"

DECISION_THRESHOLD = 0.90


def main() -> None:
    """Evaluate the current model and persist the report."""

    bundle = load_model_bundle(MODEL_PATH, METADATA_PATH)
    labels, probabilities = labeled_holdout_scores(bundle)
    report = evaluate_predictions(labels, probabilities, threshold=DECISION_THRESHOLD)
    report["model_version"] = bundle.version

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved evaluation report to {REPORT_PATH}")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
