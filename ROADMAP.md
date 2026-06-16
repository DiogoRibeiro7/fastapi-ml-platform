# Roadmap

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
- [ ] Add async batch ingestion.
- [x] Add scheduled model-quality reports.
- [x] Add dead-letter handling for failed batch requests.

## Stage 5 — Security and governance

- [ ] Add JWT auth.
- [ ] Add role-based access control.
- [ ] Add per-client rate limits.
- [ ] Add request-size limits.
- [ ] Add data-retention policies.
- [ ] Add PII masking in logs.

## Stage 6 — Deployment

- [ ] Add staging and production config profiles.
- [ ] Add Terraform example.
- [ ] Add AWS ECS deployment guide.
- [ ] Add Kubernetes manifests as optional material.
- [ ] Add blue-green model deployment strategy.
