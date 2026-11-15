"""Analysis job facade: durable queue + worker pool + retention.

``POST /api/jobs`` enqueues and returns immediately; the browser polls
``GET /api/jobs/{id}`` every 1.5 s, which is the honest latency story (CO6):
progress and queue position are visible instead of hiding a 30-60 s request
behind a timeout.

Architecture (see documentation/Architecture.md, "Job queue"):

    API request -> JobStore (SQLite, durable) <- Worker threads/processes
                                   ^
                                   +-- Janitor (leases, upload/result retention)

The public functions below (``create_job``, ``get_job``, ``get_source``,
``get_report``, ``wait_for``) keep their original signatures.
"""

from __future__ import annotations

import logging
import signal
import threading
import time
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from api.pipeline import config
from api.pipeline.analyze import analyze_document

from . import cleanup
from .store import JobStore, QueueFull
from .worker import Janitor, Worker, default_worker_id

logger = logging.getLogger("thesistrace.jobs")

__all__ = [
    "QueueFull", "Settings", "create_job", "delete_job", "get_job", "get_report", "get_source",
    "has_capacity", "queue_stats", "reset", "run_forever", "shutdown", "start", "wait_for",
]


@dataclass(frozen=True)
class Settings:
    db_path: Path
    upload_dir: Path
    mode: str = "inline"
    workers: int = 1
    max_queue: int = 20
    max_attempts: int = 2
    lease_seconds: float = 90.0
    timeout_seconds: float = 900.0
    upload_ttl: float = 3600
    result_ttl: float = 86400
    max_stored: int = 200
    cleanup_interval: float = 300.0
    poll_interval: float = 0.5


def _default_settings() -> Settings:
    return Settings(
        db_path=config.JOB_DB,
        upload_dir=config.UPLOAD_DIR,
        mode=config.JOB_MODE,
        workers=config.JOB_WORKERS,
        max_queue=config.JOB_MAX_QUEUE,
        max_attempts=config.JOB_MAX_ATTEMPTS,
        lease_seconds=config.JOB_LEASE_SECONDS,
        timeout_seconds=config.JOB_TIMEOUT_SECONDS,
        upload_ttl=config.UPLOAD_TTL_SECONDS,
        result_ttl=config.RESULT_TTL_SECONDS,
        max_stored=config.JOB_MAX_STORED,
        cleanup_interval=config.CLEANUP_INTERVAL_SECONDS,
    )


class _State:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.settings: Settings | None = None
        self.store: JobStore | None = None
        self.stop = threading.Event()
        self.wake = threading.Event()
        self.threads: list[threading.Thread] = []
        self.workers_started = False


_S = _State()


# -- lifecycle --------------------------------------------------------------

def _settings() -> Settings:
    with _S.lock:
        if _S.settings is None:
            _S.settings = _default_settings()
        return _S.settings


def _store() -> JobStore:
    with _S.lock:
        if _S.store is None:
            settings = _settings()
            _S.store = JobStore(
                settings.db_path, max_queue=settings.max_queue, max_attempts=settings.max_attempts
            )
        return _S.store


def _execute(job: dict[str, Any], progress: Callable[[int, str], None]) -> dict[str, Any]:
    # Resolved at call time so tests (and plugins) can patch ``runner.analyze_document``.
    return analyze_document(Path(job["path"]), job["filename"], progress=progress)


def _sweep() -> dict[str, int]:
    settings = _settings()
    return cleanup.sweep(
        _store(), settings.upload_dir,
        upload_ttl=settings.upload_ttl, result_ttl=settings.result_ttl, max_stored=settings.max_stored,
    )


def start(*, run_workers: bool | None = None) -> None:
    """Open the store and start the janitor (+ workers in inline mode). Idempotent."""
    settings = _settings()
    store = _store()
    with _S.lock:
        if _S.workers_started:
            return
        _S.workers_started = True
        _S.stop.clear()
        if run_workers is None:
            run_workers = settings.mode == "inline"
        _sweep()  # recover jobs from a previous crash before taking new ones
        if run_workers:
            for index in range(settings.workers):
                worker = Worker(
                    store, _execute,
                    upload_dir=settings.upload_dir,
                    worker_id=default_worker_id(index),
                    stop=_S.stop, wake=_S.wake,
                    poll_interval=settings.poll_interval,
                    lease_seconds=settings.lease_seconds,
                    timeout_seconds=settings.timeout_seconds,
                )
                worker.start()
                _S.threads.append(worker)
            janitor = Janitor(store, _S.stop, settings.cleanup_interval, _sweep)
            janitor.start()
            _S.threads.append(janitor)
        logger.info(
            "Job queue ready | mode=%s | workers=%s | max_queue=%s | db=%s",
            settings.mode, settings.workers if run_workers else 0, settings.max_queue, settings.db_path,
        )


def shutdown(timeout: float = 5.0) -> None:
    """Stop workers/janitor and close the store. Running jobs resume after restart (lease)."""
    with _S.lock:
        _S.stop.set()
        _S.wake.set()
        threads, _S.threads = _S.threads, []
        _S.workers_started = False
    for thread in threads:
        thread.join(timeout=timeout)
    with _S.lock:
        if _S.store is not None:
            _S.store.close()
        _S.store = None


def reset(**overrides: Any) -> Settings:
    """Stop everything and apply new settings (used by tests and tools)."""
    shutdown()
    base = _default_settings()
    with _S.lock:
        _S.settings = replace(base, **overrides) if overrides else base
        _S.stop = threading.Event()
        _S.wake = threading.Event()
        return _S.settings


def run_forever() -> None:  # pragma: no cover - exercised by `python -m api.jobs.worker`
    """Entry point of a standalone worker process."""
    config.ensure_dirs()
    start(run_workers=True)
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    while not stop.wait(1.0):
        pass
    logger.info("Worker shutting down")
    shutdown(timeout=25.0)


# -- public API -------------------------------------------------------------

def _iso(timestamp: float | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat(timespec="seconds")


def _public(row: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "job_id": row["job_id"],
        "status": row["status"],
        "progress": row["progress"],
        "stage": row["stage"],
        "filename": row["filename"],
        "created_at": _iso(row["created_at"]),
        "updated_at": _iso(row["updated_at"]),
    }
    if row["status"] == "queued":
        ahead = _store().queue_ahead(row)
        payload["queue_ahead"] = ahead
        payload["stage"] = "Queued - next up" if ahead == 0 else f"Queued - {ahead} ahead of you"
    if row.get("result"):
        payload.update(row["result"])
        payload["job_id"] = row["job_id"]
        payload["status"] = row["status"]
    if row.get("error"):
        payload["error"] = row["error"]
    return payload


def has_capacity() -> bool:
    return _store().has_capacity()


def create_job(path: Path | str, filename: str, job_id: str | None = None) -> dict[str, Any]:
    """Enqueue one analysis. Raises :class:`QueueFull` when the queue is at capacity."""
    start()
    job_id = job_id or uuid.uuid4().hex
    store = _store()
    store.enqueue(job_id, filename, Path(path))
    _S.wake.set()
    return _public(store.get(job_id))


def get_job(job_id: str) -> dict[str, Any] | None:
    row = _store().get(job_id)
    return _public(row) if row else None


def get_source(job_id: str) -> tuple[Path, str] | None:
    """Stored upload path and filename for a finished job (used by the chat)."""
    row = _store().get(job_id)
    if not row or row["status"] != "done" or not row.get("path"):
        return None
    return Path(row["path"]), row["filename"]


def get_report(job_id: str) -> str | None:
    row = _store().get(job_id)
    if not row or row["status"] != "done" or not row.get("result"):
        return None
    return row["result"].get("report", {}).get("markdown")


def delete_job(job_id: str) -> str:
    """Delete a job and its upload. Returns "deleted", "active" or "missing"."""
    store = _store()
    row = store.get(job_id)
    if row is None:
        return "missing"
    if row["status"] == "running":
        return "active"
    deleted, path = store.delete_if_status(job_id, ("queued", "done", "error"))
    if not deleted:
        return "active"
    cleanup.remove_upload(path, _settings().upload_dir)
    return "deleted"


def queue_stats() -> dict[str, Any]:
    settings = _settings()
    counts = _store().counts()
    return {
        "mode": settings.mode,
        "workers": settings.workers if settings.mode == "inline" else None,
        "max_queue": settings.max_queue,
        "queued": counts["queued"],
        "running": counts["running"],
    }


def wait_for(job_id: str, timeout: float = 30.0) -> dict[str, Any] | None:
    """Small helper for tests and scripts, not used by the HTTP API."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = get_job(job_id)
        if job and job["status"] in {"done", "error"}:
            return job
        time.sleep(0.02)
    return get_job(job_id)
