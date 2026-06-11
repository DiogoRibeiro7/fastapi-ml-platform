import sys
import types
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.ml.feature_pipeline import FEATURE_NAMES
from app.ml.model_loader import RuleBasedFraudModel
from app.ml.shap_explainer import ShapExplainer


def _rule_based_explainer() -> ShapExplainer:
    background = np.zeros((10, len(FEATURE_NAMES)), dtype=np.float64)
    return ShapExplainer(RuleBasedFraudModel(), FEATURE_NAMES, background)


def test_explain_maps_feature_names_to_shap_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """The wrapper should map SHAP values onto feature names for one row."""

    fake_shap = types.ModuleType("shap")

    class FakeExplanation:
        def __init__(self, values: np.ndarray) -> None:
            self.values = values

    class FakeExplainer:
        def __init__(self, fn: object, background: np.ndarray) -> None:
            self._n = background.shape[1]

        def __call__(self, data: np.ndarray) -> FakeExplanation:
            return FakeExplanation(np.arange(self._n, dtype=float).reshape(1, self._n))

    fake_shap.Explainer = FakeExplainer  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "shap", fake_shap)

    impacts = _rule_based_explainer().explain(
        np.zeros((1, len(FEATURE_NAMES)), dtype=np.float64)
    )

    assert impacts is not None
    assert set(impacts) == set(FEATURE_NAMES)
    assert impacts[FEATURE_NAMES[0]] == 0.0
    assert impacts[FEATURE_NAMES[-1]] == float(len(FEATURE_NAMES) - 1)


def test_explain_returns_none_and_disables_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A SHAP failure should return None and disable further attempts."""

    fake_shap = types.ModuleType("shap")

    class FakeExplainer:
        def __init__(self, fn: object, background: np.ndarray) -> None:
            raise RuntimeError("boom")

    fake_shap.Explainer = FakeExplainer  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "shap", fake_shap)

    explainer = _rule_based_explainer()
    row = np.zeros((1, len(FEATURE_NAMES)), dtype=np.float64)

    assert explainer.explain(row) is None
    assert explainer.explain(row) is None


def test_real_shap_path_produces_per_feature_values() -> None:
    """When SHAP is installed, the real explainer yields per-feature values."""

    pytest.importorskip("shap")
    from app.ml.training import make_synthetic_dataset

    background, _ = make_synthetic_dataset(n_samples=50, seed=7)
    explainer = ShapExplainer(RuleBasedFraudModel(), FEATURE_NAMES, background[:20])

    impacts = explainer.explain(background[:1])

    assert impacts is not None
    assert set(impacts) == set(FEATURE_NAMES)
    assert all(isinstance(value, float) for value in impacts.values())


def _shap_settings(tmp_path: Path, api_key: str, enable: bool) -> Settings:
    return Settings(
        api_key=api_key,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        model_artifact_path=tmp_path / "missing_model.joblib",
        model_metadata_path=tmp_path / "missing_metadata.json",
        train_baseline_if_missing=False,
        enable_shap_explanations=enable,
    )


def test_predictions_use_shap_when_enabled(
    tmp_path: Path,
    api_key: str,
    auth_headers: dict[str, str],
    sample_transaction: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With SHAP enabled, top features should come from the SHAP impacts."""

    from app.ml import model_provider as model_provider_module

    class FakeExplainer:
        def explain(self, feature_array: np.ndarray) -> dict[str, float]:
            impacts = dict.fromkeys(FEATURE_NAMES, 0.0)
            impacts["amount"] = 0.9
            return impacts

    monkeypatch.setattr(
        model_provider_module, "build_shap_explainer", lambda bundle, **kw: FakeExplainer()
    )

    app = create_app(settings=_shap_settings(tmp_path, api_key, enable=True))
    with TestClient(app) as client:
        response = client.post(
            "/v1/transactions/score", headers=auth_headers, json=sample_transaction
        )

    assert response.status_code == 201
    top_features = response.json()["top_features"]
    assert top_features[0]["name"] == "amount"
    assert top_features[0]["impact"] == 0.9


def test_predictions_fall_back_when_shap_unavailable(
    tmp_path: Path,
    api_key: str,
    auth_headers: dict[str, str],
    sample_transaction: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If SHAP yields no impacts, scoring should fall back to linear contributions."""

    from app.ml import model_provider as model_provider_module

    class FailingExplainer:
        def explain(self, feature_array: np.ndarray) -> None:
            return None

    monkeypatch.setattr(
        model_provider_module, "build_shap_explainer", lambda bundle, **kw: FailingExplainer()
    )

    app = create_app(settings=_shap_settings(tmp_path, api_key, enable=True))
    with TestClient(app) as client:
        response = client.post(
            "/v1/transactions/score", headers=auth_headers, json=sample_transaction
        )

    assert response.status_code == 201
    assert response.json()["top_features"]
