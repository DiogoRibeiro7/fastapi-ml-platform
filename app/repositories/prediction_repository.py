from collections import Counter
from typing import Any

from sqlalchemy import Select, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PredictionLog
from app.schemas.prediction import PredictionResponse


class PredictionRepository:
    """Persistence operations for prediction logs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        response: PredictionResponse,
        features: dict[str, float],
        request_payload: dict[str, Any],
    ) -> PredictionLog:
        """Create and persist a prediction log row."""

        row = PredictionLog(
            transaction_id=response.transaction_id,
            customer_id=response.customer_id,
            risk_score=response.risk_score,
            risk_level=response.risk_level,
            decision=response.decision,
            model_version=response.model_version,
            features=features,
            request_payload=request_payload,
            top_features=[item.model_dump() for item in response.top_features],
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def get_by_transaction_id(self, transaction_id: str) -> PredictionLog | None:
        """Fetch a prediction log by transaction id."""

        result = await self._session.execute(
            select(PredictionLog).where(PredictionLog.transaction_id == transaction_id)
        )
        return result.scalar_one_or_none()

    async def list_recent(self, limit: int = 500) -> list[PredictionLog]:
        """Return the most recent prediction logs."""

        statement: Select[tuple[PredictionLog]] = (
            select(PredictionLog)
            .order_by(desc(PredictionLog.created_at))
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def count(self) -> int:
        """Count all prediction logs."""

        result = await self._session.execute(select(func.count()).select_from(PredictionLog))
        return int(result.scalar_one())

    async def aggregate_metrics(self) -> dict[str, Any]:
        """Compute simple operational metrics from logged predictions."""

        rows = await self.list_recent(limit=10_000)
        if not rows:
            return {
                "prediction_count": 0,
                "average_risk_score": 0.0,
                "risk_level_counts": {},
                "decision_counts": {},
            }

        risk_level_counts = Counter(row.risk_level for row in rows)
        decision_counts = Counter(row.decision for row in rows)
        average_risk_score = sum(row.risk_score for row in rows) / len(rows)
        return {
            "prediction_count": len(rows),
            "average_risk_score": float(average_risk_score),
            "risk_level_counts": dict(risk_level_counts),
            "decision_counts": dict(decision_counts),
        }
