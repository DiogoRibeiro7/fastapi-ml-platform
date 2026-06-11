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
- [ ] Add model promotion workflow.
- [ ] Add model version comparison.
- [ ] Add calibration metrics.
- [ ] Add SHAP-based explainability.
- [ ] Add threshold optimization by business cost.
- [ ] Add offline evaluation reports.

## Stage 3 — Production observability

- [ ] Add Prometheus metrics endpoint.
- [ ] Add OpenTelemetry tracing.
- [ ] Add request correlation IDs.
- [ ] Add structured audit logs.
- [ ] Add latency histograms by endpoint.
- [ ] Add model-latency metrics.

## Stage 4 — Background processing

- [ ] Add Redis-backed queue.
- [ ] Move drift computation into a background job.
- [ ] Add async batch ingestion.
- [ ] Add scheduled model-quality reports.
- [ ] Add dead-letter handling for failed batch requests.

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
