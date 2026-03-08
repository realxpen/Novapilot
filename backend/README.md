# NovaPilot Backend (MVP)

NovaPilot backend is a modular FastAPI orchestration service for AI-assisted shopping comparisons.
It takes a natural-language query, builds a plan, runs store automation (mocked), normalizes results,
ranks products, and returns a frontend-friendly recommendation payload.

## Features

- Clean synchronous pipeline for hackathon speed
- Modular service-oriented architecture
- Rule-based interpreter (easy to replace with Amazon Nova 2 Lite)
- Mock automation layer (easy to replace with Nova Act)
- Graceful partial-success fallbacks if one store fails
- Clear response model with best pick, alternatives, reasoning, and execution log

## Project Structure

```text
backend/
  app/
    main.py
    config.py
    api/
      routes.py
    schemas/
      request.py
      response.py
      product.py
    services/
      interpreter.py
      planner.py
      automation.py
      extractor.py
      ranking.py
      report.py
    orchestrator/
      run_pipeline.py
    clients/
      bedrock_client.py
      nova_act_client.py
    utils/
      logger.py
      normalizers.py
      scoring.py
  requirements.txt
  README.md
```

## Setup

1. Create and activate a virtual environment:

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```bash
pip install -r backend/requirements.txt
```

3. (Optional) configure environment variables:

```bash
$env:NOVAPILOT_APP_NAME="NovaPilot Backend"
$env:NOVAPILOT_DEFAULT_SUPPORTED_SITES="jumia,amazon"
$env:NOVAPILOT_LOG_LEVEL="INFO"
```

## Run Locally

From repo root:

```bash
uvicorn backend.app.main:app --reload
```

Or from `backend/` directory:

```bash
uvicorn app.main:app --reload
```

## API Endpoints

- `GET /api/health`
- `POST /api/run-novapilot`

### Example Request

```json
{
  "query": "Find the best laptop under ₦800,000 for UI/UX design",
  "supported_sites": ["jumia", "amazon"],
  "top_n": 3
}
```

### Example Response (shape)

```json
{
  "status": "success",
  "query": "Find the best laptop under ₦800,000 for UI/UX design",
  "interpreted_request": {
    "category": "laptop",
    "budget_currency": "NGN",
    "budget_max": 800000,
    "use_case": "ui/ux design",
    "priority_specs": ["RAM", "CPU", "storage", "display", "portability"],
    "top_n": 3
  },
  "execution_log": [
    "Validating request",
    "Interpreted user query into structured shopping intent",
    "Built execution plan with 7 steps",
    "Running automation for jumia",
    "Collected 4 raw products from jumia",
    "Normalized 4 products from jumia",
    "Running automation for amazon",
    "Collected 4 raw products from amazon",
    "Normalized 4 products from amazon",
    "Ranked 8 products",
    "Generated recommendation report"
  ],
  "best_pick": {
    "name": "Acer Swift X 14 - 16GB RAM 512GB SSD Ryzen 7 RTX 3050",
    "store": "amazon",
    "price": 799999,
    "currency": "NGN",
    "rating": 4.5,
    "ram_gb": 16,
    "storage_gb": 512,
    "cpu": "AMD Ryzen 7",
    "gpu": "NVIDIA RTX 3050",
    "screen_size": "14 inch",
    "url": "https://www.amazon.com/acer-swift-x-14",
    "score": 8.137,
    "image_url": "https://m.media-amazon.com/images/acer-swift-x.jpg",
    "short_reason": "within budget, 16GB RAM, AMD Ryzen 7, 4.5/5 rating"
  },
  "alternatives": [],
  "comparison_table": [],
  "reasoning": "Acer Swift X 14 - 16GB RAM 512GB SSD Ryzen 7 RTX 3050 was selected as the best option because it scored highest for ui/ux design, with strong specs and price-to-performance balance.",
  "warnings": null
}
```

## Where To Plug AWS Integrations

- Replace rule-based interpretation in `app/services/interpreter.py` with calls to `app/clients/bedrock_client.py` (Nova 2 Lite via Bedrock).
- Replace mock store methods in `app/services/automation.py` with `app/clients/nova_act_client.py` calls.

## Notes

- MVP intentionally avoids auth, database, and asynchronous orchestration.
- Designed for clean extension while keeping hackathon iteration fast.
