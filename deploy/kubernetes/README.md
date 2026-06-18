# Kubernetes manifests (optional)

Optional manifests for running the FastAPI ML platform on Kubernetes. They mirror
the [AWS ECS deployment](../../docs/deployment/aws-ecs.md): one Deployment behind a
Service and Ingress, configuration split between a ConfigMap (non-secret) and a
Secret, and `/health` / `/ready` probes.

## Files

| File | Purpose |
| --- | --- |
| `configmap.yaml` | Non-secret environment variables. |
| `secret.example.yaml` | Template for secrets — do not commit real values. |
| `deployment.yaml` | The app Deployment (port 8000, liveness/readiness probes, Prometheus scrape annotations). |
| `service.yaml` | ClusterIP Service exposing port 80 → 8000. |
| `ingress.yaml` | Host-based Ingress with TLS (nginx example). |
| `hpa.yaml` | Optional horizontal autoscaler. |

## Apply

```bash
# Create the secret out-of-band (preferred over committing secret.example.yaml):
kubectl create secret generic fraud-api-secrets \
  --from-literal=DATABASE_URL='postgresql+asyncpg://user:password@postgres:5432/fraud' \
  --from-literal=API_KEY='...' \
  --from-literal=JWT_SECRET='...' \
  --from-literal=BOOTSTRAP_ADMIN_PASSWORD='...'

kubectl apply -f configmap.yaml -f deployment.yaml -f service.yaml -f ingress.yaml
```

## Scheduling and scaling

The Deployment defaults to a single replica because scheduled work (drift reports,
retention cleanup) runs **in-process** on each pod. Running multiple replicas would
fire those jobs on every pod.

To scale the API horizontally, run the API with scheduling disabled (leave
`SCHEDULED_REPORT_INTERVAL_SECONDS` / `RETENTION_CLEANUP_INTERVAL_SECONDS` unset)
and run a separate single-replica Deployment with scheduling enabled, or a
`CronJob` that calls `POST /v1/admin/retention/cleanup`. Then apply `hpa.yaml`.

Database schema is created on startup for convenience; for production run Alembic
migrations as a `Job` before rolling out a new image (see the deployment guide).
