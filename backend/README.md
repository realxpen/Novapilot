# NovaPilot Backend

NovaPilot backend is a FastAPI orchestration service for AI-assisted shopping comparisons.

## Setup

1. Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```bash
pip install -r backend/requirements.txt
```

3. Copy the example environment file:

```bash
Copy-Item backend/.env.example backend/.env
```

You can also place the same variables in a repo-level `.env`. The backend loads `backend/.env` first, then repo `.env`.
`get_settings()` is cached for the lifetime of the backend process, so restart the backend after changing env vars.

## Run Locally

```bash
uvicorn backend.app.main:app --reload
```

## API Endpoints

- `GET /api/health`
- `POST /api/run-novapilot`

### Example Request

```json
{
  "query": "Find the best laptop under 800000 NGN for UI/UX design",
  "user_location": "Nigeria",
  "top_n": 3
}
```

## Live Integration Environment Variables

```bash
# Bedrock
AWS_REGION=us-east-1
NOVAPILOT_USE_BEDROCK_INTERPRETATION=true
NOVAPILOT_USE_BEDROCK_REPORT_GENERATION=true
NOVAPILOT_USE_BEDROCK_SITE_SELECTION=true
NOVAPILOT_BEDROCK_INTERPRET_MODEL_ID=amazon.nova-lite-v1:0
NOVAPILOT_BEDROCK_REPORT_MODEL_ID=amazon.nova-lite-v1:0
NOVAPILOT_BEDROCK_SITE_SELECTION_MODEL_ID=amazon.nova-lite-v1:0

# Nova Act
NOVAPILOT_USE_NOVA_ACT_AUTOMATION=true
NOVAPILOT_FALLBACK_TO_MOCK_ON_LIVE_FAILURE=false
NOVA_ACT_API_KEY=your_real_key_here
NOVAPILOT_NOVA_ACT_MODEL_ID=amazon.nova-act-v1:0
NOVAPILOT_NOVA_ACT_LOG_GROUP_NAME=
NOVAPILOT_NOVA_ACT_TIMEOUT_SECONDS=90
NOVAPILOT_NOVA_ACT_POLL_INTERVAL_SECONDS=2
NOVAPILOT_NOVA_ACT_WORKFLOW_AMAZON=novapilot_search_amazon
NOVAPILOT_NOVA_ACT_WORKFLOW_JUMIA=novapilot_search_jumia
NOVAPILOT_NOVA_ACT_WORKFLOW_KONGA=novapilot_search_konga
NOVAPILOT_NOVA_ACT_WORKFLOW_SLOT=novapilot_search_slot
NOVAPILOT_NOVA_ACT_WORKFLOW_JIJI=novapilot_search_jiji
```

Recommended local development setup:

1. Put `NOVA_ACT_API_KEY=...` in `backend/.env`
2. Restart the backend
3. Let the backend inject the key into the Nova Act subprocess
4. Optionally enable `NOVAPILOT_FALLBACK_TO_MOCK_ON_LIVE_FAILURE=true` if you want mock data when live Nova Act fails locally

## Site Selection Policy

- If the user names sites in the query, NovaPilot uses those sites only.
- If the user does not name sites, Nova Lite recommends sites using location, category, budget, and expected availability.
- For Nigeria, fallback priority is `jumia`, `konga`, `slot`, `jiji`, with `amazon` added only when relevant.
