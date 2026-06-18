# Terraform example — AWS ECS Fargate

Example Terraform for the deployment described in
[../../docs/deployment/aws-ecs.md](../../docs/deployment/aws-ecs.md). It is a
starting point, not a turnkey production module: review security groups, TLS,
and IAM scoping before real use.

## What it creates

- ECR repository for the container image.
- ECS Fargate cluster, task definition, and service behind an Application Load Balancer.
- RDS PostgreSQL instance (Multi-AZ in production).
- Security groups wiring ALB → service → database.
- A Secrets Manager secret holding the database URL and app secrets, injected into the task.
- CloudWatch log group, execution/task IAM roles.

It assumes an **existing VPC** and subnets, passed as variables, rather than creating networking.

## Usage

```bash
cd deploy/terraform
terraform init

terraform apply \
  -var 'vpc_id=vpc-0123456789abcdef0' \
  -var 'public_subnet_ids=["subnet-aaa","subnet-bbb"]' \
  -var 'private_subnet_ids=["subnet-ccc","subnet-ddd"]' \
  -var 'container_image=123456789012.dkr.ecr.eu-west-1.amazonaws.com/fraud-api:<git-sha>' \
  -var 'db_password=...' \
  -var 'api_key=...' \
  -var 'jwt_secret=...' \
  -var 'bootstrap_admin_password=...'
```

Pass secrets via a `*.tfvars` file (git-ignored) or your CI's secret store rather than on the command line. After `apply`, push the image to the `ecr_repository_url` output and the service will pull it on the next deployment.

## Production notes

- The listener is plain HTTP for the example. In production, switch it to HTTPS with an ACM certificate and redirect HTTP→HTTPS.
- `APP_ENV=production` makes the app refuse to start with default secrets, so the `api_key`, `jwt_secret`, and `bootstrap_admin_password` variables are required.
- The app's startup `create_all` is not a migration strategy — run Alembic migrations as a one-off task before rolling out (see the deployment guide).
- Use a remote Terraform backend (S3 + DynamoDB lock) for shared state.
