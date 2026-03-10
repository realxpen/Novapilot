# NovaPilot

NovaPilot is a shopping comparison app with a Next.js frontend and a FastAPI backend.
The frontend sends shopping queries to the backend, which interprets the request,
selects stores, runs store automation, normalizes results, ranks products, and
returns recommendations.

## Local Setup

### Prerequisites

- Node.js
- Python 3.11+

### Frontend

1. Install dependencies:
   `npm install`
2. Copy `.env.local.example` to `.env.local`.
3. Run the frontend:
   `npm run dev`

### Backend

1. Create and activate a virtual environment:
   `python -m venv .venv`
   `.venv\Scripts\Activate.ps1`
2. Install dependencies:
   `pip install -r backend/requirements.txt`
3. Copy `backend/.env.example` to `backend/.env` or repo `.env`.
4. Run the API:
   `uvicorn backend.app.main:app --reload`

## Environment Files

- Frontend uses `.env.local`.
- Backend loads `backend/.env` first, then repo `.env`.

## Default Site Policy

- If the query names sites, NovaPilot uses those sites only.
- If the query does not name sites, Nova Lite recommends sites using location, category, budget, and expected availability.
- For Nigeria, the fallback priority is `jumia`, `konga`, `slot`, `jiji`, then `amazon` when relevant.
