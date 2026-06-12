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
| `GET` | `/v1/models/compare` | Compare two model versions by metrics. |
| `POST` | `/v1/models` | Register a model version. |
| `POST` | `/v1/models/{model_id}/activate` | Promote one registered model to active (hot-swaps the served model). |
| `GET` | `/v1/metrics/model` | Show prediction-count and risk-distribution metrics. |
| `GET` | `/v1/drift/report` | Show a PSI-based drift report. |
| `GET` | `/v1/calibration/report` | Show a calibration report (Brier score, ECE, reliability bins). |
| `POST` | `/v1/threshold/optimize` | Recommend a cost-minimizing decision threshold. |
| `GET` | `/v1/evaluation/report` | Show a consolidated offline evaluation report. |
| `GET` | `/metrics` | Expose Prometheus metrics for scraping. |

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

## Explainability

Each prediction returns `top_features`, a local explanation of the score. By default this is a fast linear contribution (`feature value × model coefficient`).

For SHAP-based explanations, install the optional dependency and enable the flag:

```bash
pip install -e ".[explain]"
```

```text
ENABLE_SHAP_EXPLANATIONS=true
```

The SHAP explainer is built lazily on first use and cached for the lifetime of the active model (and rebuilt after a promotion). If `shap` is not installed or an explanation fails, the service logs it once and falls back to the linear contribution, so enabling the flag is always safe.

**Performance:** SHAP runs a perturbation-based explainer per prediction, which is substantially slower than the linear path (milliseconds vs. microseconds) and adds CPU load proportional to the background sample size. Keep it disabled for high-throughput real-time scoring; enable it for review queues, audits, or offline analysis where per-decision explanations matter more than latency.

## Offline evaluation

Generate a consolidated evaluation report (ranking, calibration, and threshold-based classification metrics) for the current model:

```bash
python scripts/evaluate_model.py
```

This scores the model on a seeded labeled holdout and writes `artifacts/evaluation_report.json`. The same report is available live at `GET /v1/evaluation/report`, where an optional `threshold` query parameter overrides the default decline score.

## Metrics and monitoring

The service exposes Prometheus metrics at `GET /metrics` (unauthenticated, for scraping):

- `http_requests_total{method, endpoint, status_code}` — request counts.
- `http_request_duration_seconds{method, endpoint}` — request latency histogram.
- `model_prediction_duration_seconds` — model inference latency, tracked separately from HTTP latency.
- `model_predictions_total{risk_level, decision}` — scored predictions by outcome.

HTTP metrics are collected in middleware and prediction metrics in the scoring service, so route handlers stay free of instrumentation. The `endpoint` label uses the matched route template (e.g. `/v1/transactions/{transaction_id}`) to keep label cardinality bounded.

### Correlation IDs

Every response carries an `X-Request-ID` header. Send your own to trace a request across services, or let the service generate one. The id is attached to every structured log line as `request_id`, so logs for a single request can be grouped end to end.

Example scrape config:

```yaml
scrape_configs:
  - job_name: fraud-api
    static_configs:
      - targets: ["localhost:8000"]
```

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
