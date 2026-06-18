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
| `POST` | `/v1/transactions/batch-score` | Score many transactions synchronously. |
| `POST` | `/v1/transactions/batch-score-jobs` | Submit a batch for asynchronous scoring. |
| `POST` | `/v1/transactions/ingest` | Ingest a transactions payload (JSON or JSONL) as a job. |
| `GET` | `/v1/jobs/{job_id}` | Check a batch job's status and result. |
| `GET` | `/v1/jobs/{job_id}/dead-letters` | List transactions that failed within a job. |
| `POST` | `/v1/jobs/{job_id}/retry-dead-letters` | Resubmit a job's failed transactions. |
| `GET` | `/v1/transactions/{transaction_id}` | Fetch a logged prediction. |
| `GET` | `/v1/models/current` | Show active model metadata. |
| `GET` | `/v1/models` | List registered models. |
| `GET` | `/v1/models/compare` | Compare two model versions by metrics. |
| `POST` | `/v1/models` | Register a model version. |
| `POST` | `/v1/models/{model_id}/activate` | Promote one registered model to active (hot-swaps the served model). |
| `GET` | `/v1/metrics/model` | Show prediction-count and risk-distribution metrics. |
| `GET` | `/v1/drift/report` | Show a PSI-based drift report computed on demand. |
| `POST` | `/v1/drift/jobs` | Schedule a background drift-computation job. |
| `GET` | `/v1/drift/reports/latest` | Show the latest stored drift report. |
| `GET` | `/v1/drift/reports/{report_id}` | Show a stored drift report by id. |
| `GET` | `/v1/calibration/report` | Show a calibration report (Brier score, ECE, reliability bins). |
| `POST` | `/v1/threshold/optimize` | Recommend a cost-minimizing decision threshold. |
| `GET` | `/v1/evaluation/report` | Show a consolidated offline evaluation report. |
| `GET` | `/metrics` | Expose Prometheus metrics for scraping. |
| `POST` | `/v1/auth/login` | Exchange credentials for a JWT access token. |
| `POST` | `/v1/auth/users` | Create a user (admin only). |
| `POST` | `/v1/admin/retention/cleanup` | Purge records past the retention window (admin only). |

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
- Redis on port `6379`.
- An RQ worker processing batch-scoring jobs (the compose stack runs with `JOB_BACKEND=redis`).

## Configuration profiles

`APP_ENV` selects the environment profile: `development` (default), `staging`, or `production`. Example profiles are provided as [.env.staging.example](.env.staging.example) and [.env.production.example](.env.production.example) — copy one to `.env` or inject the values as environment variables.

In `production`, startup **fails fast** if `API_KEY`, `JWT_SECRET`, or `BOOTSTRAP_ADMIN_PASSWORD` is left at its insecure development default, so a misconfigured deployment cannot start with shipped secrets.

## Deployment

A practical, production-shaped deployment walkthrough for AWS ECS Fargate (architecture, required services, environment variables, image build/push, migration strategy, and monitoring) is in [docs/deployment/aws-ecs.md](docs/deployment/aws-ecs.md).

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

## Asynchronous batch jobs

Large batches can be scored asynchronously. `POST /v1/transactions/batch-score-jobs` returns `202 Accepted` with a job id, then `GET /v1/jobs/{job_id}` reports the status (`queued`, `running`, `completed`, `failed`), progress, and a result summary. The synchronous `POST /v1/transactions/batch-score` remains for small batches.

Jobs are persisted in the database and processed by a configurable backend (`JOB_BACKEND`):

- `inprocess` (default) — an in-process `asyncio` worker. Set `PROCESS_JOBS_INLINE=true` to run jobs synchronously (used in tests).
- `redis` — batch jobs are enqueued to Redis via [RQ](https://python-rq.org/) and executed by a separate worker process, so scoring scales independently of the API. Install the extra (`pip install -e ".[queue]"`), set `REDIS_URL`, and run a worker with `make worker` (or `python scripts/run_worker.py`). The worker rebuilds its own database session and model from settings; dead-letter handling and result reporting are identical to the in-process backend.

For bulk ingestion from a file or stream, `POST /v1/transactions/ingest` accepts a raw payload — a JSON array, a single JSON object, or newline-delimited JSON (one transaction per line) — parses and validates it, and submits it as a batch job. Payloads above `MAX_INGEST_RECORDS` are rejected with `413`; malformed or invalid payloads return `422`.

Scoring is isolated per transaction: if one transaction fails, it is captured in a **dead-letter** store and the rest of the batch continues, so a single bad record never fails the whole job. The job's result summary reports `scored` and `failed` counts. Inspect the failures with `GET /v1/jobs/{job_id}/dead-letters`, and resubmit them as a fresh job with `POST /v1/jobs/{job_id}/retry-dead-letters` once the underlying issue is resolved.

## Drift monitoring

The service reports feature drift using the Population Stability Index (PSI), comparing each feature's recent distribution against a baseline. `GET /v1/drift/report` computes a report on demand; for larger windows, `POST /v1/drift/jobs` runs the computation as a background job and stores the result, retrievable via `GET /v1/drift/reports/latest` or `GET /v1/drift/reports/{report_id}`.

Interpreting PSI per feature (industry-standard thresholds):

| PSI | Severity | Interpretation |
|---|---|---|
| `< 0.1` | none | No significant shift; no action needed. |
| `0.1 – 0.2` | low | Minor shift; worth monitoring. |
| `0.2 – 0.5` | medium | Material shift; investigate the feature and consider retraining. |
| `>= 0.5` | high | Large shift; the model is likely operating outside its training distribution. |

The report's `max_severity` is the worst severity across all features, which is a quick signal for alerting.

Set `SCHEDULED_REPORT_INTERVAL_SECONDS` to have the service generate and store drift reports automatically on that interval (an in-process scheduler started at app startup and stopped on shutdown). Leave it unset to disable scheduling. The latest snapshot is always available at `GET /v1/drift/reports/latest`.

## Authentication and roles

The API supports two authentication methods:

- **API key** (`X-API-Key` header) for service-to-service access. It authenticates a `service` principal.
- **JWT bearer tokens** for users. `POST /v1/auth/login` exchanges a username and password for a token whose claims carry the user's role. Send it as `Authorization: Bearer <token>`.

Passwords are hashed with PBKDF2-HMAC-SHA256. A bootstrap admin (configurable via `BOOTSTRAP_ADMIN_*`) is created on startup so an administrator always exists; admins can create further users with `POST /v1/auth/users`.

Roles and access:

| Role | Predictions & jobs | Model management | Reports & metrics |
|---|---|---|---|
| `admin` | yes | yes | yes |
| `service` | yes | no | yes |
| `analyst` | no | no | yes |

Model-management endpoints (registering and activating models) require `admin`. Prediction and batch endpoints require `service` or `admin`. Missing credentials return `401`; an authenticated caller without a sufficient role returns `403`. Authentication failures and authorization denials are recorded as audit events.

### Rate limiting

Requests are rate limited per client over a fixed window. The client is identified by its API key, bearer token, or source IP (in that order). Exceeding `RATE_LIMIT_REQUESTS` within `RATE_LIMIT_WINDOW_SECONDS` returns `429` with a `Retry-After` header; allowed responses carry `X-RateLimit-Remaining`. Health and metrics endpoints are exempt. Set `RATE_LIMIT_REQUESTS=0` to disable. The counter is in-process; a multi-instance deployment would back it with a shared store such as Redis.

### Request-size limits

Requests whose body exceeds `MAX_REQUEST_BYTES` are rejected with `413` based on the `Content-Length` header, before the body is read into memory. Set `MAX_REQUEST_BYTES=0` to disable.

## Metrics and monitoring

The service exposes Prometheus metrics at `GET /metrics` (unauthenticated, for scraping):

- `http_requests_total{method, endpoint, status_code}` — request counts.
- `http_request_duration_seconds{method, endpoint}` — request latency histogram.
- `model_prediction_duration_seconds` — model inference latency, tracked separately from HTTP latency.
- `model_predictions_total{risk_level, decision}` — scored predictions by outcome.

HTTP metrics are collected in middleware and prediction metrics in the scoring service, so route handlers stay free of instrumentation. The `endpoint` label uses the matched route template (e.g. `/v1/transactions/{transaction_id}`) to keep label cardinality bounded.

### Correlation IDs

Every response carries an `X-Request-ID` header. Send your own to trace a request across services, or let the service generate one. The id is attached to every structured log line as `request_id`, so logs for a single request can be grouped end to end.

### Data retention

Prediction logs, drift reports, and dead letters can be purged after a retention window. Set `DATA_RETENTION_DAYS` to the number of days to keep, and `RETENTION_CLEANUP_INTERVAL_SECONDS` to run the purge automatically on that interval. Administrators can also trigger a one-off cleanup with `POST /v1/admin/retention/cleanup` (an optional `days` query parameter overrides the configured window); the response reports how many rows were deleted per table.

### PII masking

A redacting filter on the logging pipeline masks sensitive fields (`customer_id`, `email`, `password`, `card_number`, `token`, and similar) before any log line is emitted. Anything passed to a logger via `extra=` under a sensitive key is replaced with `***`, so personal data and secrets never reach the log sink even if logged accidentally.

### Audit logs

Security- and governance-relevant actions emit structured audit events on the dedicated `audit` logger, each carrying an `action`, an `outcome`, the `request_id`, and action-specific fields:

- `auth_failed` — a rejected request (missing or invalid API key), with the reason, method, and path.
- `model_registered` — a new model version was registered.
- `model_promoted` — a model was activated and hot-swapped into serving.

Routing the `audit` logger to a separate sink (file, SIEM) is a configuration change only, since audit events are already isolated to that logger.

### Distributed tracing

OpenTelemetry tracing is optional and disabled by default. Install the extra and enable it:

```bash
pip install -e ".[tracing]"
```

```text
ENABLE_TRACING=true
OTEL_SERVICE_NAME=fastapi-ml-platform
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318/v1/traces
```

When enabled, incoming requests are auto-instrumented (one server span per request) and model inference is recorded as a child `model.inference` span. Spans export to the configured OTLP endpoint, or to the console when none is set. All OpenTelemetry imports are lazy, so the dependency is only needed when tracing is on; the inference span is a no-op otherwise.

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
