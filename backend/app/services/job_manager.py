"""File-backed job orchestration for long-running live report generation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock, Thread
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import TypeAdapter

from app.config import get_settings
from app.orchestrator.run_pipeline import NovaPilotOrchestrator
from app.schemas.request import RunNovaPilotRequest
from app.schemas.response import ExecutionLogItem, JobStatusResponse, JobSubmissionResponse, NovaPilotResponse
from app.utils.logger import get_logger


logger = get_logger(__name__)


@dataclass
class _JobRecord:
    job_id: str
    status: str
    query: str
    interpreted_request: object
    instant_guidance: object
    current_step: Optional[str] = None
    execution_log: list[ExecutionLogItem] | None = None
    final_report: Optional[NovaPilotResponse] = None
    error: Optional[str] = None
    updated_at: str = ""


class JobManager:
    """Manage background report jobs with simple disk persistence."""

    def __init__(self) -> None:
        settings = get_settings()
        self._jobs: Dict[str, _JobRecord] = {}
        self._lock = Lock()
        self._storage_path = Path(settings.jobs_storage_path)
        self._stale_after = timedelta(seconds=settings.nova_act_timeout_seconds + 30)
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._job_response_adapter = TypeAdapter(JobStatusResponse)
        self._load()

    def submit(
        self,
        request: RunNovaPilotRequest,
        orchestrator: NovaPilotOrchestrator,
    ) -> JobSubmissionResponse:
        preview = orchestrator.build_instant_guidance(request)
        job_id = uuid4().hex
        record = _JobRecord(
            job_id=job_id,
            status="queued",
            query=request.query,
            interpreted_request=preview["interpreted_request"],
            instant_guidance=preview["instant_guidance"],
            updated_at=self._now(),
            execution_log=[],
        )
        with self._lock:
            self._jobs[job_id] = record
            self._persist_locked()
        logger.info(
            "NOVAPILOT_DEBUG job_submitted job_id=%s preview=%s",
            job_id,
            {
                "status": record.status,
                "query": record.query,
                "interpreted_request": self._to_jsonable(record.interpreted_request),
                "instant_guidance": self._to_jsonable(record.instant_guidance),
            },
        )

        thread = Thread(
            target=self._run_job,
            args=(job_id, request, orchestrator),
            daemon=True,
        )
        thread.start()

        return JobSubmissionResponse(
            job_id=job_id,
            status=record.status,
            query=record.query,
            interpreted_request=record.interpreted_request,
            instant_guidance=record.instant_guidance,
            current_step=record.current_step,
            execution_log=record.execution_log or [],
        )

    def get(self, job_id: str) -> Optional[JobStatusResponse]:
        with self._lock:
            record = self._jobs.get(job_id)
            if record:
                self._expire_stale_record_locked(record)
        if not record:
            return None
        return JobStatusResponse(
            job_id=record.job_id,
            status=record.status,
            query=record.query,
            interpreted_request=record.interpreted_request,
            instant_guidance=record.instant_guidance,
            current_step=record.current_step,
            execution_log=record.execution_log or [],
            final_report=record.final_report,
            error=record.error,
        )

    def _run_job(
        self,
        job_id: str,
        request: RunNovaPilotRequest,
        orchestrator: NovaPilotOrchestrator,
    ) -> None:
        self._update(job_id, status="running", current_step="Starting live report")
        try:
            report = orchestrator.run(
                request,
                progress_callback=self._make_progress_callback(job_id),
            )
            logger.info(
                "NOVAPILOT_DEBUG job_completed job_id=%s final_report=%s",
                job_id,
                self._to_jsonable(report),
            )
            self._update(job_id, status="completed", final_report=report)
        except Exception as exc:  # noqa: BLE001
            logger.exception("NOVAPILOT_DEBUG job_failed job_id=%s", job_id)
            self._update(job_id, status="failed", error=str(exc))

    def _update(self, job_id: str, **updates: object) -> None:
        with self._lock:
            record = self._jobs[job_id]
            for key, value in updates.items():
                setattr(record, key, value)
            record.updated_at = self._now()
            self._persist_locked()
        logger.info(
            "NOVAPILOT_DEBUG job_update job_id=%s updates=%s",
            job_id,
            {key: self._to_jsonable(value) for key, value in updates.items()},
        )

    def _persist_locked(self) -> None:
        payload = {
            job_id: self._serialize_record(record)
            for job_id, record in self._jobs.items()
        }
        self._storage_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _serialize_record(self, record: _JobRecord) -> Dict[str, Any]:
        return {
            "job_id": record.job_id,
            "status": record.status,
            "query": record.query,
            "interpreted_request": self._to_jsonable(record.interpreted_request),
            "instant_guidance": self._to_jsonable(record.instant_guidance),
            "current_step": record.current_step,
            "execution_log": self._to_jsonable(record.execution_log or []),
            "final_report": self._to_jsonable(record.final_report),
            "error": record.error,
            "updated_at": record.updated_at,
        }

    def _load(self) -> None:
        if not self._storage_path.exists():
            return
        try:
            payload = json.loads(self._storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(payload, dict):
            return

        for job_id, raw in payload.items():
            if not isinstance(raw, dict):
                continue
            try:
                job_response = self._job_response_adapter.validate_python(
                    {
                        "job_id": raw.get("job_id", job_id),
                        "status": raw.get("status", "failed"),
                        "query": raw.get("query", ""),
                        "interpreted_request": raw.get("interpreted_request", {}),
                        "instant_guidance": raw.get("instant_guidance", {}),
                        "current_step": raw.get("current_step"),
                        "execution_log": raw.get("execution_log", []),
                        "final_report": raw.get("final_report"),
                        "error": raw.get("error"),
                    }
                )
            except Exception:
                continue

            self._jobs[job_id] = _JobRecord(
                job_id=job_response.job_id,
                status=job_response.status,
                query=job_response.query,
                interpreted_request=job_response.interpreted_request,
                instant_guidance=job_response.instant_guidance,
                current_step=job_response.current_step,
                execution_log=job_response.execution_log,
                final_report=job_response.final_report,
                error=job_response.error,
                updated_at=str(raw.get("updated_at", self._now())),
            )
        with self._lock:
            changed = False
            for record in self._jobs.values():
                changed = self._expire_stale_record_locked(record) or changed
            if changed:
                self._persist_locked()

    def _to_jsonable(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, list):
            return [self._to_jsonable(item) for item in value]
        if isinstance(value, dict):
            return {key: self._to_jsonable(item) for key, item in value.items()}
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        return value

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _expire_stale_record_locked(self, record: _JobRecord) -> bool:
        if record.status not in {"queued", "running"}:
            return False
        try:
            updated_at = datetime.fromisoformat(record.updated_at)
        except ValueError:
            updated_at = datetime.now(timezone.utc) - self._stale_after - timedelta(seconds=1)
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - updated_at <= self._stale_after:
            return False
        record.status = "failed"
        record.error = (
            "The live report stopped updating before completion. "
            "Possible causes: backend restart, lost connectivity to store/Nova endpoints, "
            "or a stalled browser session."
        )
        record.current_step = "Live report failed"
        record.updated_at = self._now()
        return True

    def _make_progress_callback(self, job_id: str):
        def callback(execution_log: list[ExecutionLogItem], current_step: str) -> None:
            self._update(
                job_id,
                execution_log=list(execution_log),
                current_step=current_step,
            )

        return callback
