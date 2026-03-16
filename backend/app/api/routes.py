"""HTTP routes for the NovaPilot API."""

import os
import socket
import ssl
import time

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.orchestrator.run_pipeline import NovaPilotOrchestrator
from app.schemas.request import RunNovaPilotRequest
from app.schemas.response import JobStatusResponse, JobSubmissionResponse
from app.services.job_manager import JobManager
from app.utils.logger import get_logger
from app.utils.secrets import mask_secret


router = APIRouter(prefix="/api", tags=["novapilot"])
settings = get_settings()
orchestrator = NovaPilotOrchestrator()
job_manager = JobManager()
logger = get_logger(__name__)


def _run_live_connectivity_preflight(timeout_seconds: float = 3.0) -> dict[str, object]:
    host = "api.nova.amazon.com"
    report: dict[str, object] = {
        "host": host,
        "port": 443,
        "timeout_seconds": timeout_seconds,
        "live_nova_act_enabled": settings.use_nova_act_automation,
        "nova_act_timeout_seconds": settings.nova_act_timeout_seconds,
        "nova_api_key_present": bool(settings.nova_api_key),
        "masked_nova_api_key": mask_secret(settings.nova_api_key),
        "os_environ_has_nova_act_api_key": bool(os.environ.get("NOVA_ACT_API_KEY")),
        "os_environ_has_nova_api_key": bool(os.environ.get("NOVA_API_KEY")),
        "dns_resolution_ok": False,
        "tcp_connect_ok": False,
        "tls_handshake_ok": False,
        "resolved_addresses": [],
    }

    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        addresses = sorted({info[4][0] for info in infos if info and len(info) > 4 and info[4]})
        report["resolved_addresses"] = addresses
        report["dns_resolution_ok"] = bool(addresses)
    except Exception as exc:  # noqa: BLE001
        report["dns_error"] = str(exc)
        return report

    try:
        start = time.perf_counter()
        with socket.create_connection((host, 443), timeout=timeout_seconds) as sock:
            report["tcp_connect_ok"] = True
            report["tcp_connect_ms"] = round((time.perf_counter() - start) * 1000, 1)
            ssl_start = time.perf_counter()
            context = ssl.create_default_context()
            with context.wrap_socket(sock, server_hostname=host):
                report["tls_handshake_ok"] = True
                report["tls_handshake_ms"] = round((time.perf_counter() - ssl_start) * 1000, 1)
    except Exception as exc:  # noqa: BLE001
        report["connectivity_error"] = str(exc)

    return report


@router.get("/health")
def health_check() -> dict[str, str]:
    """Basic health check endpoint."""
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}


@router.get("/live-preflight")
def live_preflight(timeout_seconds: float = 3.0) -> dict[str, object]:
    """Quick preflight to verify local machine can reach Nova Act API over TLS."""
    report = _run_live_connectivity_preflight(timeout_seconds=max(0.5, min(timeout_seconds, 10.0)))
    logger.info("NOVAPILOT_DEBUG live_preflight=%s", report)
    return report


@router.get("/amazon-diagnostics")
def amazon_diagnostics(
    query: str,
    max_search_terms: int = 3,
    search_timeout: int = 10,
) -> dict[str, object]:
    """Probe Amazon reachability and search-result HTML from the live container."""
    try:
        from scripts.amazon_workflow import collect_amazon_http_diagnostics

        report = collect_amazon_http_diagnostics(
            query=query,
            max_terms=max(1, min(max_search_terms, 5)),
            search_timeout=max(3, min(search_timeout, 20)),
        )
        logger.info("NOVAPILOT_DEBUG amazon_diagnostics=%s", report)
        return report
    except Exception as exc:  # noqa: BLE001
        logger.exception("NOVAPILOT_DEBUG amazon_diagnostics_failed")
        raise HTTPException(status_code=500, detail=f"Amazon diagnostics failed: {exc}") from exc


@router.post("/run-novapilot", response_model=JobSubmissionResponse)
def run_novapilot(request: RunNovaPilotRequest) -> JobSubmissionResponse:
    """Queue the NovaPilot report job and return instant guidance immediately."""
    try:
        logger.info("NOVAPILOT_DEBUG incoming_request_payload=%s", request.model_dump(mode="json"))
        response = job_manager.submit(request, orchestrator)
        logger.info(
            "NOVAPILOT_DEBUG api_submission_response=%s",
            response.model_dump(mode="json"),
        )
        return response
    except Exception as exc:  # noqa: BLE001 - return readable API errors
        logger.exception("NOVAPILOT_DEBUG api_submission_failed")
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {exc}") from exc


@router.get("/run-novapilot/{job_id}", response_model=JobStatusResponse)
def get_novapilot_job(job_id: str) -> JobStatusResponse:
    """Fetch the current status for a queued or running report job."""
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    logger.info(
        "NOVAPILOT_DEBUG api_job_status_response=%s",
        job.model_dump(mode="json"),
    )
    return job
