# Deploying to AWS ECS (Fargate)

This guide describes a practical, production-shaped deployment of the FastAPI ML platform on AWS ECS Fargate. It is intentionally concise; adapt names, sizes, and account-specific values to your environment.

An example Terraform module that provisions this stack (ECR, ECS, RDS, ALB, secrets, IAM) lives in [`deploy/terraform/`](../../deploy/terraform/). Optional Kubernetes manifests for an equivalent deployment are in [`deploy/kubernetes/`](../../deploy/kubernetes/).

## Architecture overview

```text
            ┌──────────────┐
  client →  │  ALB (HTTPS) │  → target group health check: GET /health
            └──────┬───────┘
                   │
            ┌──────▼───────────────────────────┐
            │  ECS Fargate service (N tasks)    │
            │  ┌─────────────┐  ┌────────────┐  │
            │  │ app (uvicorn)│  │ ADOT side- │  │ → scrapes GET /metrics, exports
            │  │  port 8000   │  │ car (opt.) │  │   OTLP traces + Prometheus metrics
            │  └──────┬──────┘  └────────────┘  │
            └─────────┼─────────────────────────┘
                      │ asyncpg
            ┌─────────▼─────────┐
            │  RDS PostgreSQL    │
            └────────────────────┘

  Logs → CloudWatch Logs (structured JSON)
  Secrets → Secrets Manager / SSM Parameter Store
```

- The container runs `uvicorn app.main:app` on port `8000` (see the [Dockerfile](../../Dockerfile)).
- The Application Load Balancer terminates TLS and routes to the ECS service; its target group health check uses `GET /health` (liveness) and you can add a deeper check on `GET /ready` (verifies the database and model).
- State lives in RDS PostgreSQL. The app connects with the async `asyncpg` driver.
- Background work (scheduled drift reports, retention cleanup, batch jobs) runs in-process on each task. Run exactly one task if you need the scheduler to fire once per interval, or move scheduling to a dedicated single-task service / EventBridge-triggered task when scaling the API horizontally.

## Required AWS services

| Service | Purpose |
| --- | --- |
| ECR | Stores the container image. |
| ECS (Fargate) | Runs the API as a long-lived service. |
| RDS (PostgreSQL) | Primary datastore for predictions, jobs, users, reports. |
| Application Load Balancer | Public HTTPS entrypoint and health checks. |
| CloudWatch Logs | Collects the container's structured JSON logs. |
| Secrets Manager or SSM Parameter Store | Holds `API_KEY`, `JWT_SECRET`, and the database URL. |
| IAM | Task execution role (pull image, read secrets) and task role (runtime AWS access). |
| Amazon Managed Prometheus + ADOT (optional) | Scrapes `/metrics`; pair with X-Ray for OTLP traces. |

## Environment variables

Set non-secret values directly in the task definition `environment`, and inject secrets via the task definition `secrets` (sourced from Secrets Manager / SSM). See [`.env.example`](../../.env.example) for the full list.

| Variable | Example | Notes |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host:5432/fraud` | Must use the `+asyncpg` driver. Inject as a secret. |
| `API_KEY` | (random) | Service-to-service key. Secret. |
| `JWT_SECRET` | (random, 32+ bytes) | Signs access tokens. Secret. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Token lifetime. |
| `BOOTSTRAP_ADMIN_USERNAME` / `BOOTSTRAP_ADMIN_PASSWORD` | `admin` / (random) | Seeds the first admin on startup. Rotate or disable after creating real users. |
| `LOG_LEVEL` | `INFO` | |
| `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS` | `120` / `60` | Per-task limit; back with Redis for multi-task accuracy. |
| `MAX_REQUEST_BYTES` | `1048576` | Request body cap. |
| `DATA_RETENTION_DAYS` / `RETENTION_CLEANUP_INTERVAL_SECONDS` | `90` / `86400` | Enables scheduled purges. |
| `SCHEDULED_REPORT_INTERVAL_SECONDS` | `3600` | Enables periodic drift reports. |
| `ENABLE_TRACING` / `OTEL_EXPORTER_OTLP_ENDPOINT` | `true` / `http://localhost:4318/v1/traces` | Point at the ADOT sidecar. |

## Build and push the image

```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com"

# Build, tag, and push
docker build -t fraud-api .
docker tag fraud-api:latest "$ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/fraud-api:$GIT_SHA"
docker push "$ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/fraud-api:$GIT_SHA"
```

The Docker build trains and bakes the baseline model artifact into the image, so a fresh container serves a real model immediately without external state. Tag images with the git SHA and reference that exact tag in the task definition for reproducible, rollback-friendly deploys.

## Database and migration strategy

The app calls `create_all` on startup, which is convenient for demos but is **not** a migration strategy for production. For real deployments:

1. Add Alembic and generate migrations from the SQLAlchemy models in [`app/db/models.py`](../../app/db/models.py).
2. Run migrations as a one-off ECS task (same image, command overridden to `alembic upgrade head`) **before** rolling out a new service revision. Gate the deploy on its success.
3. Keep `create_all` for local/dev only, or guard it behind an environment flag.

Provision RDS with automated backups and Multi-AZ for production. Restrict the database security group to the ECS task security group only. The bootstrap admin is created idempotently on startup; rotate its password and create per-user accounts via `POST /v1/auth/users`.

## Monitoring strategy

- **Health checks** — ALB target group: `GET /health` (fast liveness). Optionally add an ECS/route check on `GET /ready`, which verifies the database connection and that a model is loaded.
- **Metrics** — `GET /metrics` exposes Prometheus format (`http_requests_total`, `http_request_duration_seconds`, `model_prediction_duration_seconds`, `model_predictions_total`). Run an ADOT collector sidecar to scrape it and ship to Amazon Managed Prometheus, then dashboard/alert in Grafana or CloudWatch.
- **Tracing** — set `ENABLE_TRACING=true` and `OTEL_EXPORTER_OTLP_ENDPOINT` to the ADOT sidecar, which forwards spans to AWS X-Ray. Each request carries an `X-Request-ID` correlation id that also appears in every log line.
- **Logs** — the container logs structured JSON to stdout; use the `awslogs` driver to send it to CloudWatch Logs. Sensitive fields are masked, and security events (auth failures, model promotions, denials) are emitted as audit records you can route to a metric filter or alert.
- **Alarms** — suggested CloudWatch alarms: ALB 5xx rate, target health, `/ready` failures, RDS CPU/connections, and ECS task restarts.

## Rollout and rollback

Deploy by registering a new task definition revision pointing at the new image tag and updating the service. ECS performs a rolling replacement behind the ALB; unhealthy tasks are drained automatically. To roll back, update the service to the previous task definition revision — because images are pinned by git SHA, this is deterministic.

Deploying a new **model** is separate from deploying new **code**: see [blue-green-models.md](blue-green-models.md) for zero-downtime model promotion and rollback via the model registry.
