"""Retention: delete uploads and old jobs so a public deployment cannot fill the disk.

Policy (all values configurable, see ``api/pipeline/config.py``):

* A job that **fails** loses its upload immediately - nothing can use it.
* A **finished** job keeps its upload for ``UPLOAD_TTL_SECONDS`` (the Ask tab
  re-reads it), then only the analysis result remains.
* The whole job (result included) is deleted after ``RESULT_TTL_SECONDS``, and at
  most ``JOB_MAX_STORED`` finished jobs are kept.
* Files in the upload directory that no job references (crashed upload, wiped
  database) are deleted after a grace period.
* A file is only ever deleted if it resolves *inside* the upload directory, so a
  bad database row can never delete anything else.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from .store import JobStore

logger = logging.getLogger("thesistrace.jobs.cleanup")

ORPHAN_GRACE_SECONDS = 3600


def remove_upload(path: str | Path | None, upload_dir: Path) -> bool:
    """Delete one upload if (and only if) it lives inside ``upload_dir``."""
    if not path:
        return False
    try:
        root = Path(upload_dir).resolve()
        target = Path(path).resolve()
        if root != target and root not in target.parents:
            logger.warning("Refusing to delete a file outside the upload directory: %s", target)
            return False
        if target.is_file():
            target.unlink()
            return True
    except OSError:
        logger.exception("Could not delete upload %s", path)
    return False


def sweep(
    store: JobStore,
    upload_dir: Path,
    *,
    upload_ttl: float,
    result_ttl: float,
    max_stored: int,
    orphan_grace: float = ORPHAN_GRACE_SECONDS,
    now: float | None = None,
) -> dict[str, int]:
    """Run one retention pass. Safe to call repeatedly and from several processes."""
    now = time.time() if now is None else now
    stats = {"requeued": 0, "failed": 0, "uploads_deleted": 0, "jobs_deleted": 0, "orphans_deleted": 0}

    requeued, failed = store.requeue_expired(now)
    stats["requeued"], stats["failed"] = len(requeued), len(failed)
    for job_id in failed:
        job = store.get(job_id)
        if job and remove_upload(job.get("path"), upload_dir):
            store.clear_path(job_id)
            stats["uploads_deleted"] += 1

    for job_id, path in store.finished_with_source(now - upload_ttl):
        if remove_upload(path, upload_dir):
            stats["uploads_deleted"] += 1
        store.clear_path(job_id)

    doomed = dict(store.expired_jobs(now - result_ttl))
    doomed.update(dict(store.overflow_jobs(max_stored)))
    for job_id, path in doomed.items():
        if remove_upload(path, upload_dir):
            stats["uploads_deleted"] += 1
        store.delete(job_id)
        stats["jobs_deleted"] += 1

    try:
        known = {str(Path(p).resolve()) for p in store.known_paths()}
        for entry in Path(upload_dir).iterdir():
            if not entry.is_file() or str(entry.resolve()) in known:
                continue
            if now - entry.stat().st_mtime >= orphan_grace and remove_upload(entry, upload_dir):
                stats["orphans_deleted"] += 1
    except FileNotFoundError:
        pass
    except OSError:
        logger.exception("Orphan sweep failed")

    if any(stats.values()):
        logger.info("Retention sweep: %s", stats)
    return stats
