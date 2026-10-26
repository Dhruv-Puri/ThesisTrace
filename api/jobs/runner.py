"""In-process background jobs.

A laptop CPU cannot run two summarizers at once, so jobs are queued behind a
semaphore.  ``POST /api/jobs`` returns immediately; the browser polls
``GET /api/jobs/{id}`` every 1.5 s.  This is the honest latency story (CO6):
progress is visible instead of hiding a 30-60 s request behind a timeout.

The store is intentionally in-memory: no database, no host files, no cleanup job.
Uploaded files live under the project-local ``.data/uploads`` (or the Docker
volume), so deleting the project removes everything.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api.pipeline.analyze import analyze_document
from api.pipeline.ingest import IngestError

logger = logging.getLogger("paper2reality.jobs")

MAX_JOBS = 40


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Job:
    job_id: str
    filename: str
    path: Path
    status: str = "queued"
    progress: int = 0
    stage: str = "Queued"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    result: dict[str, Any] | None = None
    error: dict[str, str] | None = None


_JOBS: dict[str, Job] = {}
_LOCK = threading.Lock()
_SEMAPHORE = threading.Semaphore(1)


def _public(job: Job) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "stage": job.stage,
        "filename": job.filename,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }
    if job.result:
        payload.update(job.result)
        payload["job_id"] = job.job_id
        payload["status"] = job.status
    if job.error:
        payload["error"] = job.error
    return payload


def _update(job_id: str, **fields: Any) -> None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if not job:
            return
        for key, value in fields.items():
            setattr(job, key, value)
        job.updated_at = _now()


def _progress(job_id: str, percent: int, stage: str) -> None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if not job:
            return
        job.progress = max(job.progress, min(99, int(percent)))
        job.stage = stage
        job.updated_at = _now()


def _prune() -> None:
    with _LOCK:
        finished = [
            job for job in _JOBS.values() if job.status in {"done", "error"}
        ]
        finished.sort(key=lambda item: item.updated_at)
        while len(_JOBS) > MAX_JOBS and finished:
            oldest = finished.pop(0)
            _JOBS.pop(oldest.job_id, None)


def _run(job_id: str, path: Path, filename: str) -> None:
    with _SEMAPHORE:
        _update(job_id, status="running", progress=1, stage="Starting")
        try:
            result = analyze_document(
                path,
                filename,
                progress=lambda percent, stage: _progress(job_id, percent, stage),
            )
            _update(
                job_id,
                status="done",
                progress=100,
                stage="Report ready",
                result=result,
                error=None,
            )
        except IngestError as exc:
            logger.info("Ingest failed for job %s: %s", job_id, exc.code)
            _update(
                job_id,
                status="error",
                stage="Failed",
                error={"code": exc.code, "message": exc.message},
            )
        except MemoryError:
            logger.exception("Out of memory for job %s", job_id)
            _update(
                job_id,
                status="error",
                stage="Failed",
                error={
                    "code": "OUT_OF_MEMORY",
                    "message": "Not enough memory to analyse this document. Try LOW_RAM=1.",
                },
            )
        except Exception as exc:  # keep the API alive; report a safe message
            logger.exception("Unexpected analysis failure for job %s", job_id)
            _update(
                job_id,
                status="error",
                stage="Failed",
                error={
                    "code": "ANALYSIS_FAILED",
                    "message": f"Analysis failed ({exc.__class__.__name__}). "
                               "Check the API logs for details.",
                },
            )


def create_job(path: Path | str, filename: str, job_id: str | None = None) -> dict[str, Any]:
    job_id = job_id or uuid.uuid4().hex[:12]
    job = Job(job_id=job_id, filename=filename, path=Path(path))
    with _LOCK:
        _JOBS[job_id] = job
    _prune()
    thread = threading.Thread(
        target=_run,
        args=(job_id, Path(path), filename),
        name=f"analysis-{job_id}",
        daemon=True,
    )
    thread.start()
    return _public(job)


def get_job(job_id: str) -> dict[str, Any] | None:
    with _LOCK:
        job = _JOBS.get(job_id)
        return _public(job) if job else None


def get_report(job_id: str) -> str | None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if not job or job.status != "done" or not job.result:
            return None
        return job.result.get("report", {}).get("markdown")


def wait_for(job_id: str, timeout: float = 30.0) -> dict[str, Any] | None:
    """Small helper for tests and scripts, not used by the HTTP API."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = get_job(job_id)
        if job and job["status"] in {"done", "error"}:
            return job
        time.sleep(0.05)
    return get_job(job_id)
