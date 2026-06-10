from collections.abc import Mapping

import numpy as np
from numpy.typing import NDArray

from app.schemas.prediction import TransactionInput

FEATURE_NAMES: list[str] = [
    "amount",
    "amount_ratio",
    "country_mismatch",
    "is_night",
    "is_weekend",
    "is_card_not_present",
    "customer_age_days",
    "num_transactions_last_24h",
    "chargeback_count_last_90d",
    "high_risk_merchant_category",
]

HIGH_RISK_CATEGORIES = {
    "crypto",
    "gambling",
    "electronics",
    "jewelry",
    "gift_cards",
    "travel",
}


def build_feature_dict(transaction: TransactionInput) -> dict[str, float]:
    """Convert a transaction request into model-ready numeric features."""

    amount_ratio = transaction.amount / max(transaction.avg_amount_last_7d, 1.0)

    return {
        "amount": float(transaction.amount),
        "amount_ratio": float(amount_ratio),
        "country_mismatch": float(transaction.merchant_country != transaction.card_country),
        "is_night": float(transaction.hour_of_day <= 5 or transaction.hour_of_day >= 23),
        "is_weekend": float(transaction.day_of_week >= 5),
        "is_card_not_present": float(not transaction.is_card_present),
        "customer_age_days": float(transaction.customer_age_days),
        "num_transactions_last_24h": float(transaction.num_transactions_last_24h),
        "chargeback_count_last_90d": float(transaction.chargeback_count_last_90d),
        "high_risk_merchant_category": float(
            transaction.merchant_category in HIGH_RISK_CATEGORIES
        ),
    }


def features_to_array(features: Mapping[str, float]) -> NDArray[np.float64]:
    """Convert a feature dictionary into a single-row NumPy array."""

    return np.array([[features[name] for name in FEATURE_NAMES]], dtype=np.float64)
