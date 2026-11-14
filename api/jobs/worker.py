"""Queue workers and the retention janitor.

``Worker`` threads pull jobs from the :class:`~api.jobs.store.JobStore`.  They run
inside the API process by default (``THESISTRACE_JOB_MODE=inline``) or in their own
process (``python -m api.jobs.worker`` with ``THESISTRACE_JOB_MODE=external`` on the
API), which is how you scale beyond one box-sized worker.

While a job runs, a heartbeat thread extends its lease.  The progress callback
doubles as the cooperative cancel point: it raises if the job timed out or the
worker lost its lease (so a zombie never overwrites a retried job).
"""

from __future__ import annotations

import logging
import os
import socket
import threading
import time
from typing import Any, Callable

from api.pipeline.ingest import IngestError

from . import cleanup
from .store import JobStore

logger = logging.getLogger("thesistrace.jobs.worker")

Execute = Callable[[dict[str, Any], Callable[[int, str], None]], dict[str, Any]]


class LeaseLost(RuntimeError):
    """This worker no longer owns the job (lease expired and it was re-queued)."""


class JobTimeout(RuntimeError):
    pass


def classify_error(exc: BaseException, timeout_seconds: float) -> dict[str, str]:
    if isinstance(exc, IngestError):
        return {"code": exc.code, "message": exc.message}
    if isinstance(exc, JobTimeout):
        return {
            "code": "JOB_TIMEOUT",
            "message": f"The analysis took longer than {int(timeout_seconds)} s and was stopped.",
        }
    if isinstance(exc, MemoryError):
        return {
            "code": "OUT_OF_MEMORY",
            "message": "Not enough memory to analyse this document. Try LOW_RAM=1.",
        }
    return {
        "code": "ANALYSIS_FAILED",
        "message": f"Analysis failed ({exc.__class__.__name__}). Check the API logs for details.",
    }


class Worker(threading.Thread):
    def __init__(
        self,
        store: JobStore,
        execute: Execute,
        *,
        upload_dir,
        worker_id: str,
        stop: threading.Event,
        wake: threading.Event,
        poll_interval: float = 0.5,
        lease_seconds: float = 90.0,
        timeout_seconds: float = 900.0,
    ):
        super().__init__(name=f"worker-{worker_id}", daemon=True)
        self.store = store
        self.execute = execute
        self.upload_dir = upload_dir
        self.worker_id = worker_id
        self._halt = stop
        self._wake = wake
        self.poll_interval = poll_interval
        self.lease_seconds = lease_seconds
        self.timeout_seconds = timeout_seconds

    def run(self) -> None:
        while not self._halt.is_set():
            try:
                job = self.store.claim(self.worker_id, self.lease_seconds)
            except Exception:
                logger.exception("Could not claim a job")
                self._halt.wait(self.poll_interval * 4)
                continue
            if job is None:
                self._wake.wait(self.poll_interval)
                self._wake.clear()
                continue
            self.process(job)

    def process(self, job: dict[str, Any]) -> None:
        job_id = job["job_id"]
        deadline = time.time() + self.timeout_seconds
        done = threading.Event()

        def heartbeat() -> None:
            interval = max(1.0, self.lease_seconds / 3)
            while not done.wait(interval):
                if not self.store.heartbeat(job_id, self.worker_id, self.lease_seconds):
                    return

        def progress(percent: int, stage: str) -> None:
            if time.time() > deadline:
                raise JobTimeout()
            if not self.store.progress(job_id, self.worker_id, percent, stage, self.lease_seconds):
                raise LeaseLost()

        beat = threading.Thread(target=heartbeat, name=f"heartbeat-{job_id[:8]}", daemon=True)
        beat.start()
        try:
            result = self.execute(job, progress)
            if not self.store.finish(job_id, self.worker_id, result):
                logger.warning("Job %s finished but its lease was lost; result discarded", job_id)
        except LeaseLost:
            logger.warning("Job %s: lease lost, abandoning", job_id)
        except BaseException as exc:  # noqa: BLE001 - one bad job must never kill the worker
            if isinstance(exc, IngestError):
                logger.info("Ingest failed for job %s: %s", job_id, exc.code)
            elif isinstance(exc, JobTimeout):
                logger.warning("Job %s timed out", job_id)
            else:
                logger.exception("Analysis failed for job %s", job_id)
            if self.store.fail(job_id, self.worker_id, classify_error(exc, self.timeout_seconds)):
                # Nothing can use the upload of a failed job.
                cleanup.remove_upload(job.get("path"), self.upload_dir)
                self.store.clear_path(job_id)
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
        finally:
            done.set()


class Janitor(threading.Thread):
    def __init__(self, store: JobStore, stop: threading.Event, interval: float, sweep: Callable[[], Any]):
        super().__init__(name="janitor", daemon=True)
        self.store = store
        self._halt = stop
        self.interval = interval
        self.sweep = sweep

    def run(self) -> None:
        while True:
            try:
                self.sweep()
            except Exception:
                logger.exception("Retention sweep failed")
            if self._halt.wait(self.interval):
                return


def default_worker_id(index: int) -> str:
    return f"{socket.gethostname()}-{os.getpid()}-{index}"


def main() -> None:  # pragma: no cover - process entry point
    """``python -m api.jobs.worker``: run workers + janitor in this process."""
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    from api.jobs import runner

    runner.run_forever()


if __name__ == "__main__":  # pragma: no cover
    main()
