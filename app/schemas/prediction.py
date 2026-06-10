from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

RiskLevel = Literal["low", "medium", "high", "critical"]
Decision = Literal["approve", "review", "decline"]


class TransactionInput(BaseModel):
    """Input contract for scoring a payment transaction."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "transaction_id": "txn_001",
                "customer_id": "customer_001",
                "amount": 450.0,
                "merchant_category": "electronics",
                "merchant_country": "PT",
                "card_country": "PT",
                "hour_of_day": 2,
                "day_of_week": 5,
                "is_card_present": False,
                "customer_age_days": 45,
                "num_transactions_last_24h": 12,
                "avg_amount_last_7d": 55.0,
                "chargeback_count_last_90d": 1,
            }
        }
    )

    transaction_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        description="Optional client-provided transaction identifier.",
    )
    customer_id: str = Field(min_length=1, max_length=128)
    amount: float = Field(ge=0.0)
    merchant_category: str = Field(min_length=1, max_length=64)
    merchant_country: str = Field(min_length=2, max_length=2)
    card_country: str = Field(min_length=2, max_length=2)
    hour_of_day: int = Field(ge=0, le=23)
    day_of_week: int = Field(ge=0, le=6, description="Monday is 0 and Sunday is 6.")
    is_card_present: bool
    customer_age_days: int = Field(ge=0)
    num_transactions_last_24h: int = Field(ge=0)
    avg_amount_last_7d: float = Field(ge=0.0)
    chargeback_count_last_90d: int = Field(ge=0)

    @field_validator("merchant_country", "card_country")
    @classmethod
    def normalize_country_code(cls, value: str) -> str:
        """Normalize ISO-like country codes to uppercase."""

        return value.upper()

    @field_validator("merchant_category")
    @classmethod
    def normalize_merchant_category(cls, value: str) -> str:
        """Normalize merchant categories for feature engineering."""

        return value.strip().lower().replace(" ", "_")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def resolved_transaction_id(self) -> str:
        """Return a stable transaction id, generating one when omitted."""

        return self.transaction_id or f"txn_{uuid4().hex}"


class BatchPredictionRequest(BaseModel):
    """Input contract for batch scoring."""

    transactions: list[TransactionInput] = Field(min_length=1)


class FeatureContribution(BaseModel):
    """A local explanation item for a prediction."""

    name: str
    impact: float


class PredictionResponse(BaseModel):
    """Output contract returned by fraud scoring endpoints."""

    transaction_id: str
    customer_id: str
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel
    decision: Decision
    top_features: list[FeatureContribution]
    model_version: str


class BatchPredictionResponse(BaseModel):
    """Output contract for batch scoring."""

    predictions: list[PredictionResponse]
