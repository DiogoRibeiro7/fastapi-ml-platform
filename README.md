# FastAPI ML Platform

Production-style FastAPI service for real-time fraud-risk scoring.

This repository is designed as a portfolio project for showcasing backend engineering, ML engineering, API design, testing, observability, and deployment discipline in one coherent codebase.

## What this project demonstrates

- Clean FastAPI architecture with routers, services, repositories, schemas, and dependency injection.
- Typed request and response contracts using Pydantic v2.
- Real-time and batch ML inference endpoints.
- Model loading through an application lifespan hook.
- Prediction logging with async SQLAlchemy.
- API-key authentication for protected endpoints.
- Health and readiness checks.
- Drift report endpoint using Population Stability Index.
- Model metadata endpoint.
- Structured JSON logging.
- Docker and Docker Compose setup.
- Pytest test suite.
- GitHub Actions CI.
- Roadmap and implementation prompts for further development.

## Domain

The service scores payment transactions and returns a fraud-risk estimate.

Example response:

```json
{
  "transaction_id": "txn_001",
  "risk_score": 0.86,
  "risk_level": "high",
  "decision": "review",
  "top_features": [
    {"name": "amount_ratio", "impact": 0.41},
    {"name": "chargeback_count_last_90d", "impact": 0.24}
  ],
  "model_version": "rule-based-v1"
}
```

On first startup the app trains and saves a seeded scikit-learn baseline model automatically, so it serves a real trained model immediately. You can also train it ahead of time with `scripts/train_model.py`. A deterministic rule-based fallback remains for when training is disabled (`TRAIN_BASELINE_IF_MISSING=false`) or fails.

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Basic process health check. |
| `GET` | `/ready` | Readiness check for database and model availability. |
| `POST` | `/v1/transactions/score` | Score one transaction. |
| `POST` | `/v1/transactions/batch-score` | Score many transactions. |
| `GET` | `/v1/transactions/{transaction_id}` | Fetch a logged prediction. |
| `GET` | `/v1/models/current` | Show active model metadata. |
| `GET` | `/v1/models` | List registered models. |
| `POST` | `/v1/models` | Register a model version. |
| `POST` | `/v1/models/{model_id}/activate` | Activate one registered model. |
| `GET` | `/v1/metrics/model` | Show prediction-count and risk-distribution metrics. |
| `GET` | `/v1/drift/report` | Show a PSI-based drift report. |

## Quick start

### 1. Install dependencies

```bash
poetry install
```

Or with pip:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Create an environment file

```bash
cp .env.example .env
```

The default development API key is:

```text
dev-api-key
```

### 3. Run the app

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://localhost:8000/docs
```

### 4. Score a transaction

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

## Run with Docker Compose

```bash
docker compose up --build
```

This starts:

- FastAPI app on port `8000`.
- PostgreSQL on port `5432`.
- Redis on port `6379` for future background workers.

## Train a demo model

```bash
python scripts/train_model.py
```

This creates:

```text
artifacts/fraud_model.joblib
artifacts/fraud_model_metadata.json
```

On startup, the API loads this artifact. If it is missing, the API trains and saves the baseline model automatically (the dataset generator is seeded, so the result is deterministic). Set `TRAIN_BASELINE_IF_MISSING=false` to disable auto-training and use the rule-based fallback model instead. The Docker image bakes the trained artifact in at build time.

## Run tests

```bash
pytest
```

Run linting and typing:

```bash
ruff check .
mypy app
```

## Project structure

```text
app/
├── api/               # API routers and dependencies
├── core/              # Settings, logging, security, exceptions
├── db/                # Async SQLAlchemy session and ORM models
├── ml/                # Model loading, feature pipeline, explainability, drift
├── repositories/      # Persistence layer
├── schemas/           # Pydantic request/response models
└── services/          # Business logic
```

## Why this is a good portfolio project

Most FastAPI portfolio projects stop at CRUD. This project shows how to structure a service that has real production concerns: request validation, model serving, async persistence, authentication, metrics, drift checks, testing, and deployment.
