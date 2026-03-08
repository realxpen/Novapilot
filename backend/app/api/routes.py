"""HTTP routes for the NovaPilot API."""

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.orchestrator.run_pipeline import NovaPilotOrchestrator
from app.schemas.request import RunNovaPilotRequest
from app.schemas.response import NovaPilotResponse


router = APIRouter(prefix="/api", tags=["novapilot"])
settings = get_settings()
orchestrator = NovaPilotOrchestrator()


@router.get("/health")
def health_check() -> dict[str, str]:
    """Basic health check endpoint."""
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}


@router.post("/run-novapilot", response_model=NovaPilotResponse)
def run_novapilot(request: RunNovaPilotRequest) -> NovaPilotResponse:
    """Run the NovaPilot orchestration pipeline."""
    try:
        return orchestrator.run(request)
    except Exception as exc:  # noqa: BLE001 - return readable API errors
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {exc}") from exc
