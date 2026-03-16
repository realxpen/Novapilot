# Local Testing Guide

This repo contains:

- a Next.js frontend in the repo root
- a FastAPI backend in [`backend`](./backend)

The fastest way to test locally is to run the frontend and backend in separate terminals.

## Prerequisites

- Git
- Node.js 20+
- Python 3.11+

Optional for full live testing:

- AWS account with Bedrock access
- a valid `NOVA_ACT_API_KEY`

## 1. Clone the repository

```bash
git clone <your-repo-url>
cd Novapilot
```

## 2. Install frontend dependencies

```bash
npm install
```

## 3. Create the frontend env file

Copy [`.env.local.example`](./.env.local.example) to `.env.local`.

Use:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_DEFAULT_USER_LOCATION=Nigeria
```

Important:

- do not add a trailing `/` to `NEXT_PUBLIC_API_BASE_URL`

## 4. Create a Python virtual environment

PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

## 5. Create the backend env file

Copy [`backend/.env.example`](./backend/.env.example) to `backend/.env`.

### Option A: Smoke test mode

Use this if you just want the app to boot locally and test the UI/API flow without Bedrock or Nova Act.

Set these values in `backend/.env`:

```env
NOVAPILOT_CORS_ALLOW_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
NOVAPILOT_USE_BEDROCK_INTERPRETATION=false
NOVAPILOT_USE_BEDROCK_REPORT_GENERATION=false
NOVAPILOT_USE_BEDROCK_SITE_SELECTION=false
NOVAPILOT_USE_NOVA_ACT_AUTOMATION=false
NOVAPILOT_JOBS_STORAGE_PATH=/tmp/novapilot-jobs.json
```

What to expect in smoke test mode:

- the backend starts normally
- `/api/health` works
- searches return instant guidance
- live product extraction is disabled, so warnings are expected

### Option B: Full live mode

Use this only if you have valid credentials and want live Bedrock/Nova Act behavior.

Set these values in `backend/.env`:

```env
NOVAPILOT_CORS_ALLOW_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
AWS_REGION=us-east-1
NOVAPILOT_USE_BEDROCK_INTERPRETATION=true
NOVAPILOT_USE_BEDROCK_REPORT_GENERATION=true
NOVAPILOT_USE_BEDROCK_SITE_SELECTION=true
NOVAPILOT_BEDROCK_INTERPRET_MODEL_ID=amazon.nova-lite-v1:0
NOVAPILOT_BEDROCK_REPORT_MODEL_ID=amazon.nova-lite-v1:0
NOVAPILOT_BEDROCK_SITE_SELECTION_MODEL_ID=amazon.nova-lite-v1:0
NOVAPILOT_USE_NOVA_ACT_AUTOMATION=true
NOVAPILOT_NOVA_ACT_STRICT_MODE=true
NOVAPILOT_NOVA_ACT_TIMEOUT_SECONDS=120
NOVAPILOT_NOVA_ACT_POLL_INTERVAL_SECONDS=2
NOVA_ACT_API_KEY=your_real_key_here
NOVAPILOT_JOBS_STORAGE_PATH=/tmp/novapilot-jobs.json
```

Notes:

- your AWS credentials still need Bedrock access on the machine running the backend
- if you change env vars, restart the backend because settings are cached per process

## 6. Start the backend

From the repo root:

```bash
python -m uvicorn app.main:app --app-dir backend --reload
```

Health check:

```text
http://127.0.0.1:8000/api/health
```

Expected response:

```json
{"status":"ok","service":"NovaPilot Backend","version":"0.1.0"}
```

## 7. Start the frontend

In a second terminal from the repo root:

```bash
npm run dev
```

Open:

```text
http://localhost:3000
```

## 8. Recommended local test

Try a query like:

```text
Laptop for programming under NGN 900k
```

Expected behavior:

- the results page opens
- the frontend can reach the backend
- in smoke test mode, you should still see the advisory flow even if live extraction is disabled
- in live mode, you should see real store-backed products when the integrations succeed

## Troubleshooting

### `ModuleNotFoundError: No module named 'app'`

Use the backend start command from this guide:

```bash
python -m uvicorn app.main:app --app-dir backend --reload
```

Do not use:

```bash
python -m uvicorn backend.app.main:app --reload
```

### `Failed to fetch`

Check:

- `.env.local` points to `http://127.0.0.1:8000`
- the backend is running
- `NOVAPILOT_CORS_ALLOW_ORIGINS` includes both `http://localhost:3000` and `http://127.0.0.1:3000`

### `Nova Act actuator could not start`

This means live browser automation failed to start.

For general contributor testing, switch to smoke test mode by setting:

```env
NOVAPILOT_USE_NOVA_ACT_AUTOMATION=false
```

### Env changes are ignored

Restart the backend after editing `backend/.env`. The settings object is cached for the lifetime of the process.
