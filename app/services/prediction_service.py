import logging
import time
from typing import Any

from numpy.typing import NDArray

from app.core.config import Settings
from app.core.exceptions import PredictionNotFoundError
from app.core.metrics import record_prediction
from app.core.tracing import start_span
from app.ml.explainer import top_contributions_from_impacts, top_feature_contributions
from app.ml.feature_pipeline import build_feature_dict, features_to_array
from app.ml.model_loader import ModelBundle, fraud_probability
from app.ml.shap_explainer import ShapExplainer
from app.repositories.prediction_repository import PredictionRepository
from app.schemas.prediction import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    Decision,
    FeatureContribution,
    PredictionResponse,
    RiskLevel,
    TransactionInput,
)

logger = logging.getLogger(__name__)


class PredictionService:
    """Business logic for fraud-risk scoring."""

    def __init__(
        self,
        *,
        repository: PredictionRepository,
        model_bundle: ModelBundle,
        settings: Settings,
        shap_explainer: ShapExplainer | None = None,
    ) -> None:
        self._repository = repository
        self._model_bundle = model_bundle
        self._settings = settings
        self._shap_explainer = shap_explainer

    async def score_transaction(self, transaction: TransactionInput) -> PredictionResponse:
        """Score and persist one transaction."""

        features = build_feature_dict(transaction)
        feature_array = features_to_array(features)

        inference_start = time.perf_counter()
        with start_span("model.inference"):
            risk_score = fraud_probability(self._model_bundle.model, feature_array)
        inference_seconds = time.perf_counter() - inference_start

        risk_level = self._risk_level(risk_score)
        decision = self._decision(risk_score)
        record_prediction(risk_level, decision, inference_seconds)
        top_features = self._explain(features, feature_array)

        response = PredictionResponse(
            transaction_id=transaction.resolved_transaction_id,
            customer_id=transaction.customer_id,
            risk_score=risk_score,
            risk_level=risk_level,
            decision=decision,
            top_features=top_features,
            model_version=self._model_bundle.version,
        )

        await self._repository.create(
            response=response,
            features=features,
            request_payload=transaction.model_dump(mode="json"),
        )
        logger.info(
            "prediction_created",
            extra={
                "transaction_id": response.transaction_id,
                "risk_score": response.risk_score,
                "risk_level": response.risk_level,
                "decision": response.decision,
            },
        )
        return response

    async def score_batch(self, request: BatchPredictionRequest) -> BatchPredictionResponse:
        """Score a batch of transactions."""

        if len(request.transactions) > self._settings.max_batch_size:
            msg = f"Batch size exceeds maximum of {self._settings.max_batch_size}."
            raise ValueError(msg)

        predictions = [
            await self.score_transaction(transaction)
            for transaction in request.transactions
        ]
        return BatchPredictionResponse(predictions=predictions)

    async def get_prediction(self, transaction_id: str) -> PredictionResponse:
        """Return a stored prediction by transaction id."""

        row = await self._repository.get_by_transaction_id(transaction_id)
        if row is None:
            raise PredictionNotFoundError(f"Prediction not found: {transaction_id}")

        return PredictionResponse(
            transaction_id=row.transaction_id,
            customer_id=row.customer_id,
            risk_score=row.risk_score,
            risk_level=row.risk_level,  # type: ignore[arg-type]
            decision=row.decision,  # type: ignore[arg-type]
            top_features=row.top_features,  # type: ignore[arg-type]
            model_version=row.model_version,
        )

    def _explain(
        self,
        features: dict[str, float],
        feature_array: NDArray[Any],
    ) -> list[FeatureContribution]:
        """Explain a prediction with SHAP when available, else linearly.

        SHAP is opt-in and may fail at runtime, so the linear contribution
        fallback always covers the case where no SHAP impacts are produced.
        """

        if self._shap_explainer is not None:
            impacts = self._shap_explainer.explain(feature_array)
            if impacts is not None:
                return top_contributions_from_impacts(impacts, limit=5)

        return top_feature_contributions(
            features=features,
            coefficients=self._model_bundle.coefficients,
            limit=5,
        )

    def _decision(self, risk_score: float) -> Decision:
        """Map risk score to a business decision."""

        if risk_score >= self._settings.min_decline_score:
            return "decline"
        if risk_score >= self._settings.min_review_score:
            return "review"
        return "approve"

    @staticmethod
    def _risk_level(risk_score: float) -> RiskLevel:
        """Map risk score to a readable risk level."""

        if risk_score >= 0.90:
            return "critical"
        if risk_score >= 0.65:
            return "high"
        if risk_score >= 0.35:
            return "medium"
        return "low"


def prediction_response_to_dict(response: PredictionResponse) -> dict[str, Any]:
    """Serialize a prediction response for logs or external sinks."""

    return response.model_dump(mode="json")
