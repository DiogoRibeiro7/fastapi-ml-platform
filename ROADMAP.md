# Roadmap

Stages 1–6 are complete. Stage 7 captures enhancements delivered beyond the
original plan. Stages 8+ are forward-looking and not yet started.

## Stage 1 — Complete API foundation

- [x] FastAPI app factory.
- [x] Lifespan startup for settings, database, and model loading.
- [x] Health and readiness endpoints.
- [x] Typed schemas with examples.
- [x] API-key authentication.
- [x] Async SQLAlchemy repository layer.
- [x] Single-transaction scoring endpoint.
- [x] Batch scoring endpoint.
- [x] Prediction retrieval endpoint.
- [x] Model metadata endpoint.
- [x] Drift report endpoint.
- [x] Basic model metrics endpoint.

## Stage 2 — ML engineering maturity

- [x] Replace fallback model with a trained baseline model by default.
- [x] Add model registry table.
- [x] Add model promotion workflow.
- [x] Add model version comparison.
- [x] Add calibration metrics.
- [x] Add SHAP-based explainability.
- [x] Add threshold optimization by business cost.
- [x] Add offline evaluation reports.

## Stage 3 — Production observability

- [x] Add Prometheus metrics endpoint.
- [x] Add OpenTelemetry tracing.
- [x] Add request correlation IDs.
- [x] Add structured audit logs.
- [x] Add latency histograms by endpoint. (http_request_duration_seconds)
- [x] Add model-latency metrics. (model_prediction_duration_seconds)

## Stage 4 — Background processing

- [x] Add async batch job queue (in-process; Redis/RQ backend is a drop-in extension point).
- [x] Move drift computation into a background job.
- [x] Add async batch ingestion.
- [x] Add scheduled model-quality reports.
- [x] Add dead-letter handling for failed batch requests.

## Stage 5 — Security and governance

- [x] Add JWT auth.
- [x] Add role-based access control.
- [x] Add per-client rate limits.
- [x] Add request-size limits.
- [x] Add data-retention policies.
- [x] Add PII masking in logs.

## Stage 6 — Deployment

- [x] Add staging and production config profiles.
- [x] Add Terraform example.
- [x] Add AWS ECS deployment guide.
- [x] Add Kubernetes manifests as optional material.
- [x] Add blue-green model deployment strategy.

## Stage 7 — Post-roadmap enhancements (delivered)

- [x] Add a Redis/RQ job-queue backend (selectable via `JOB_BACKEND`).
- [x] Add Alembic database migrations (gated by `AUTO_CREATE_TABLES`).
- [x] Harden CI: PostgreSQL integration test, coverage gate, dependency audit.
- [x] Propagate correlation IDs across the Redis worker boundary.

## Stage 8 — ML lifecycle automation

- [ ] Add a train-and-register flow (train, persist artifact, and register in one step).
- [ ] Add canary / weighted model serving (route a fraction of traffic to a candidate).
- [ ] Add shadow scoring (run a candidate alongside the active model without affecting decisions).
- [ ] Trigger retraining automatically when drift exceeds a threshold.
- [ ] Record model lineage (training data snapshot, code version, parent model).
- [ ] Capture ground-truth outcomes to enable calibration on real production data.

## Stage 9 — Performance and scale

- [ ] Add load and latency benchmarks (`.benchmarks/`) with a regression gate.
- [ ] Add response/feature caching for repeated lookups.
- [ ] Externalize the scheduler so the API can scale horizontally.
- [ ] Parallelize batch scoring within a job.
- [ ] Tune database connection pooling and add read replicas support.
- [ ] Back rate limiting with Redis for multi-instance accuracy.

## Stage 10 — Operations and governance

- [ ] Add Grafana dashboards and Prometheus alerting rules.
- [ ] Define SLOs and error budgets for scoring latency and availability.
- [ ] Ship audit logs to a dedicated sink (SIEM) with retention.
- [ ] Add a model approval workflow (request, review, approve before promotion).
- [ ] Add data-subject deletion (GDPR) by customer id.
- [ ] Add role-scoped API keys and key rotation.
