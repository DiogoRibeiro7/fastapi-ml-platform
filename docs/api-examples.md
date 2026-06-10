# API examples

## Health

```bash
curl http://localhost:8000/health
```

## Readiness

```bash
curl http://localhost:8000/ready
```

## Score one transaction

```bash
curl -X POST "http://localhost:8000/v1/transactions/score" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key" \
  -d '{
    "transaction_id": "txn_001",
    "customer_id": "customer_001",
    "amount": 450.0,
    "merchant_category": "electronics",
    "merchant_country": "PT",
    "card_country": "PT",
    "hour_of_day": 2,
    "day_of_week": 5,
    "is_card_present": false,
    "customer_age_days": 45,
    "num_transactions_last_24h": 12,
    "avg_amount_last_7d": 55.0,
    "chargeback_count_last_90d": 1
  }'
```

## Score a batch

```bash
curl -X POST "http://localhost:8000/v1/transactions/batch-score" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key" \
  -d '{
    "transactions": [
      {
        "transaction_id": "txn_001",
        "customer_id": "customer_001",
        "amount": 450.0,
        "merchant_category": "electronics",
        "merchant_country": "PT",
        "card_country": "PT",
        "hour_of_day": 2,
        "day_of_week": 5,
        "is_card_present": false,
        "customer_age_days": 45,
        "num_transactions_last_24h": 12,
        "avg_amount_last_7d": 55.0,
        "chargeback_count_last_90d": 1
      }
    ]
  }'
```
