# Blue-green model deployment

This service supports blue-green deployment **at the model layer**: a new model
version can be registered and validated while the current one keeps serving, then
promoted with an atomic, zero-downtime swap — and rolled back just as fast. This
is independent of infrastructure deploys, so you can ship a new model without
shipping new code.

## How it works

The model registry and the live model provider make this possible:

- The **model registry** stores every model version (`POST /v1/models`); only one is active at a time.
- **Promotion** (`POST /v1/models/{model_id}/activate`) loads the artifact, then hot-swaps the in-memory model the API serves. The swap is atomic — in-flight requests finish on the old model, new requests use the new one — so there is no downtime and no dropped traffic.
- The active version is recorded in the database, so it is **re-loaded on startup**: a promotion survives restarts and rollouts.
- A failed load (missing or invalid artifact) aborts the promotion with `422` and leaves the current model serving, so a bad artifact can never take the service down.

In blue-green terms: **blue** is the currently active model; **green** is the newly registered candidate. Promotion flips the pointer from blue to green.

## Workflow

All model-management calls require an admin token (see the [auth section](../../README.md#authentication-and-roles)). Assume `$TOKEN` is an admin access token and `$URL` the base URL.

1. **Register the candidate (green)** alongside the active model:

   ```bash
   curl -X POST "$URL/v1/models" -H "Authorization: Bearer $TOKEN" \
     -d '{"name":"fraud-model","version":"v2","artifact_path":"artifacts/fraud_model_v2.joblib","training_dataset":"2026-06","metrics":{}}'
   ```

   The candidate is registered **inactive** — it does not serve traffic yet.

2. **Validate green offline**, before it serves a single request:
   - `GET /v1/models/compare?baseline_id=<blue>&candidate_id=<green>` — compare stored metrics (ROC AUC, average precision, Brier score, ECE) version to version.
   - `GET /v1/evaluation/report` and `GET /v1/calibration/report` for the active model give you the blue baseline to gate against.

   Gate promotion on your own thresholds (for example: green's ROC AUC is not worse than blue's, and its expected calibration error is within tolerance).

3. **Promote green** — the zero-downtime swap:

   ```bash
   curl -X POST "$URL/v1/models/$GREEN_ID/activate" -H "Authorization: Bearer $TOKEN"
   ```

   `GET /v1/models/current` now reports the green version, and an audit event `model_promoted` is recorded.

4. **Monitor** after promotion using signals already exposed:
   - Prometheus `model_predictions_total{risk_level,decision}` for shifts in the decision mix, and `model_prediction_duration_seconds` for latency.
   - `POST /v1/drift/jobs` then `GET /v1/drift/reports/latest` to watch feature drift against the baseline.

5. **Roll back instantly** if green misbehaves. Blue is still registered, so re-activating it is one call and the same atomic swap:

   ```bash
   curl -X POST "$URL/v1/models/$BLUE_ID/activate" -H "Authorization: Bearer $TOKEN"
   ```

## Validation gates (recommended)

Automate step 2 in your release pipeline. Promote only when the candidate clears:

- **Performance** — ROC AUC / average precision at least as good as the active model (`/v1/models/compare`).
- **Calibration** — Brier score and expected calibration error within tolerance (`/v1/calibration/report`).
- **Business cost** — the cost-optimal threshold and expected cost are acceptable (`POST /v1/threshold/optimize`).

## Infrastructure-level blue-green (alternative)

The in-process swap above gives blue-green within a single service and is the
recommended default. For a **canary** rollout (serve green to a fraction of
traffic before full promotion), run two deployments — one pinned to blue, one to
green — and shift weight at the load balancer (ALB weighted target groups, or an
ingress/service-mesh traffic split). Compare the two using the same metrics and
drift endpoints, then either promote green everywhere or drain it. This trades
the simplicity of the in-process swap for percentage-based traffic control.
