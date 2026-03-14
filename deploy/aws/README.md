# AWS deployment for NovaPilot

This repo is set up for:

- frontend on AWS Amplify Hosting
- backend on Amazon ECS Fargate behind an Application Load Balancer

## Why this layout

- The frontend is a standard Next.js app and already builds with `npm run build`.
- The backend runs FastAPI plus subprocess-based Nova Act workflows from `scripts/`.
- Live workflows need a container image with Python, Playwright-compatible browser dependencies, and a real secret injection path for `NOVA_ACT_API_KEY`.

## Files added

- `amplify.yml`
- `backend/Dockerfile`
- `.dockerignore`
- `backend/.env.example`
- `deploy/aws/ecs-task-definition.template.json`

## 1. Deploy the frontend with Amplify

In Amplify:

1. Connect the GitHub repository.
2. Select the app root.
3. Amplify should detect `amplify.yml`.
4. Add frontend environment variables:
   - `NEXT_PUBLIC_API_BASE_URL=https://api.example.com`
   - `NEXT_PUBLIC_DEFAULT_USER_LOCATION=Nigeria`
5. Deploy.

You will get a default URL like:

- `https://main.<app-id>.amplifyapp.com`

## 2. Build and push the backend image

Create an ECR repository, then build from the repo root so the Docker build can copy both `backend/` and `scripts/`.

```powershell
aws ecr create-repository --repository-name novapilot-backend
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker build -f backend/Dockerfile -t novapilot-backend .
docker tag novapilot-backend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/novapilot-backend:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/novapilot-backend:latest
```

## 3. Store the Nova Act secret

Create the backend secret in AWS Secrets Manager:

```powershell
aws secretsmanager create-secret `
  --name novapilot/nova-act-api-key `
  --secret-string "<your-nova-act-key>"
```

## 4. Create CloudWatch logs

```powershell
aws logs create-log-group --log-group-name /ecs/novapilot-backend
```

## 5. Create the ECS task definition and service

1. Copy `deploy/aws/ecs-task-definition.template.json`
2. Replace the placeholders:
   - `<account-id>`
   - `<region>`
   - Amplify/custom frontend URLs in `NOVAPILOT_CORS_ALLOW_ORIGINS`
3. Register the task definition.
4. Create an ECS Fargate service with:
   - public subnets or private subnets + NAT
   - security group allowing inbound HTTP/HTTPS from the ALB
   - ALB target group pointing to container port `8000`
   - health check path `/api/health`

## 6. Add HTTPS and a stable API URL

For production:

1. Request an ACM certificate for `api.example.com`
2. Attach it to the ALB HTTPS listener
3. Point Route 53 to the ALB

Then set:

- `NEXT_PUBLIC_API_BASE_URL=https://api.example.com`

in Amplify and redeploy the frontend.

## 7. Runtime environment variables

Recommended backend env values:

```bash
AWS_REGION=us-east-1
NOVAPILOT_LOG_LEVEL=INFO
NOVAPILOT_CORS_ALLOW_ORIGINS=https://main.<app-id>.amplifyapp.com,https://app.example.com
USD_TO_NGN_RATE=1600
NOVAPILOT_USE_NOVA_ACT_AUTOMATION=true
NOVAPILOT_NOVA_ACT_STRICT_MODE=true
NOVAPILOT_NOVA_ACT_TIMEOUT_SECONDS=120
NOVAPILOT_NOVA_ACT_POLL_INTERVAL_SECONDS=2
NOVAPILOT_JOBS_STORAGE_PATH=/tmp/novapilot-jobs.json
```

## 8. Important production note about job storage

The backend currently persists job state to a local JSON file path configured by `NOVAPILOT_JOBS_STORAGE_PATH`.

That is acceptable for:

- a single ECS task
- low-volume deployment

It is not ideal for:

- multiple ECS tasks
- high availability
- zero-downtime rollouts for in-flight jobs

For the next production hardening step, move job state to DynamoDB or Redis.
