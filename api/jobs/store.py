"""Durable job store: a small SQLite-backed queue.

Why SQLite: the pipeline's models live in-process, so the queue only has to be
durable and safe for a handful of workers on one host - no extra service to run.
The same ``JobStore`` interface can be re-implemented on Redis/Postgres later.

Guarantees
* **Durable** - queued and finished jobs survive an API restart.
* **Atomic claim** - ``claim`` runs in ``BEGIN IMMEDIATE`` so two workers can
  never take the same job.
* **Leases** - a running job holds a lease that its worker keeps extending
  (heartbeat).  If the worker dies, the lease expires and the job is retried
  (``max_attempts``) or failed with ``WORKER_LOST``.
* **Fencing** - progress/finish/fail only apply while the caller still owns the
  lease, so a zombie worker cannot overwrite a retried job.
* **Bounded** - ``enqueue`` refuses new work above ``max_queue`` (queued+running).
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

logger = logging.getLogger("thesistrace.jobs.store")

TERMINAL = ("done", "error")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id       TEXT PRIMARY KEY,
    filename     TEXT NOT NULL,
    path         TEXT,
    status       TEXT NOT NULL DEFAULT 'queued',
    progress     INTEGER NOT NULL DEFAULT 0,
    stage        TEXT NOT NULL DEFAULT 'Queued',
    attempts     INTEGER NOT NULL DEFAULT 0,
    worker       TEXT,
    lease_until  REAL,
    created_at   REAL NOT NULL,
    updated_at   REAL NOT NULL,
    started_at   REAL,
    finished_at  REAL,
    result       TEXT,
    error        TEXT
);
CREATE INDEX IF NOT EXISTS jobs_status_created ON jobs(status, created_at);
CREATE INDEX IF NOT EXISTS jobs_finished ON jobs(finished_at);
"""


class QueueFull(RuntimeError):
    """Raised by :meth:`JobStore.enqueue` when the queue is at capacity."""


class JobStore:
    def __init__(self, path: Path | str, *, max_queue: int = 20, max_attempts: int = 2):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_queue = max_queue
        self.max_attempts = max_attempts
        self._local = threading.local()
        self._conns: list[sqlite3.Connection] = []
        self._conns_lock = threading.Lock()
        self._warned_journal = False
        self._conn().executescript(_SCHEMA)

    # -- connections -------------------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(
                str(self.path), timeout=15, isolation_level=None, check_same_thread=False
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout=15000")
            mode = str(conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]).lower()
            if mode != "wal" and not self._warned_journal:
                # Some bind-mounted filesystems cannot do WAL; SQLite falls back safely.
                self._warned_journal = True
                logger.warning("SQLite WAL unavailable on %s (journal_mode=%s)", self.path, mode)
            conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn = conn
            with self._conns_lock:
                self._conns.append(conn)
        return conn

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        conn = self._conn()
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise

    def close(self) -> None:
        with self._conns_lock:
            conns, self._conns = self._conns, []
        for conn in conns:
            try:
                conn.close()
            except sqlite3.Error:  # pragma: no cover
                pass
        self._local = threading.local()

    # -- row helpers -------------------------------------------------------

    @staticmethod
    def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        data = dict(row)
        for key in ("result", "error"):
            raw = data.get(key)
            data[key] = json.loads(raw) if raw else None
        return data

    # -- producer side -----------------------------------------------------

    def enqueue(self, job_id: str, filename: str, path: Path | str | None, now: float | None = None) -> None:
        now = time.time() if now is None else now
        with self._tx() as conn:
            active = conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running')"
            ).fetchone()[0]
            if active >= self.max_queue:
                raise QueueFull(f"The queue is full ({active}/{self.max_queue} jobs).")
            conn.execute(
                "INSERT INTO jobs (job_id, filename, path, status, stage, created_at, updated_at) "
                "VALUES (?, ?, ?, 'queued', 'Queued', ?, ?)",
                (job_id, filename, str(path) if path is not None else None, now, now),
            )

    def has_capacity(self) -> bool:
        row = self._conn().execute(
            "SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running')"
        ).fetchone()
        return row[0] < self.max_queue

    def get(self, job_id: str) -> dict[str, Any] | None:
        row = self._conn().execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return self._row(row)

    def queue_ahead(self, job: dict[str, Any]) -> int:
        """Jobs that will run before this queued job (running + queued earlier)."""
        conn = self._conn()
        running = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='running'").fetchone()[0]
        earlier = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE status='queued' AND "
            "(created_at < ? OR (created_at = ? AND rowid < (SELECT rowid FROM jobs WHERE job_id = ?)))",
            (job["created_at"], job["created_at"], job["job_id"]),
        ).fetchone()[0]
        return int(running + earlier)

    def counts(self) -> dict[str, int]:
        rows = self._conn().execute("SELECT status, COUNT(*) FROM jobs GROUP BY status").fetchall()
        counts = {"queued": 0, "running": 0, "done": 0, "error": 0}
        counts.update({row[0]: row[1] for row in rows})
        return counts

    # -- worker side -------------------------------------------------------

    def claim(self, worker_id: str, lease_seconds: float, now: float | None = None) -> dict[str, Any] | None:
        now = time.time() if now is None else now
        with self._tx() as conn:
            row = conn.execute(
                "SELECT job_id FROM jobs WHERE status='queued' ORDER BY created_at, rowid LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                "UPDATE jobs SET status='running', worker=?, attempts=attempts+1, lease_until=?, "
                "started_at=?, stage='Starting', progress=MAX(progress, 1), updated_at=? WHERE job_id=?",
                (worker_id, now + lease_seconds, now, now, row["job_id"]),
            )
            claimed = conn.execute("SELECT * FROM jobs WHERE job_id=?", (row["job_id"],)).fetchone()
        return self._row(claimed)

    def heartbeat(self, job_id: str, worker_id: str, lease_seconds: float, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        cur = self._conn().execute(
            "UPDATE jobs SET lease_until=?, updated_at=? WHERE job_id=? AND worker=? AND status='running'",
            (now + lease_seconds, now, job_id, worker_id),
        )
        return cur.rowcount == 1

    def progress(
        self, job_id: str, worker_id: str, percent: int, stage: str,
        lease_seconds: float, now: float | None = None,
    ) -> bool:
        now = time.time() if now is None else now
        cur = self._conn().execute(
            "UPDATE jobs SET progress=MAX(progress, ?), stage=?, lease_until=?, updated_at=? "
            "WHERE job_id=? AND worker=? AND status='running'",
            (max(0, min(99, int(percent))), stage, now + lease_seconds, now, job_id, worker_id),
        )
        return cur.rowcount == 1

    def finish(self, job_id: str, worker_id: str, result: dict[str, Any], now: float | None = None) -> bool:
        now = time.time() if now is None else now
        cur = self._conn().execute(
            "UPDATE jobs SET status='done', progress=100, stage='Report ready', result=?, error=NULL, "
            "lease_until=NULL, finished_at=?, updated_at=? WHERE job_id=? AND worker=? AND status='running'",
            (json.dumps(result, default=str), now, now, job_id, worker_id),
        )
        return cur.rowcount == 1

    def fail(self, job_id: str, worker_id: str, error: dict[str, str], now: float | None = None) -> bool:
        now = time.time() if now is None else now
        cur = self._conn().execute(
            "UPDATE jobs SET status='error', stage='Failed', error=?, lease_until=NULL, "
            "finished_at=?, updated_at=? WHERE job_id=? AND worker=? AND status='running'",
            (json.dumps(error), now, now, job_id, worker_id),
        )
        return cur.rowcount == 1

    def requeue_expired(self, now: float | None = None) -> tuple[list[str], list[str]]:
        """Recover jobs whose worker stopped heartbeating. Returns (requeued, failed)."""
        now = time.time() if now is None else now
        requeued: list[str] = []
        failed: list[str] = []
        with self._tx() as conn:
            rows = conn.execute(
                "SELECT job_id, attempts FROM jobs WHERE status='running' AND lease_until < ?", (now,)
            ).fetchall()
            for row in rows:
                if row["attempts"] < self.max_attempts:
                    conn.execute(
                        "UPDATE jobs SET status='queued', worker=NULL, lease_until=NULL, progress=0, "
                        "stage='Queued (retrying)', updated_at=? WHERE job_id=?",
                        (now, row["job_id"]),
                    )
                    requeued.append(row["job_id"])
                else:
                    conn.execute(
                        "UPDATE jobs SET status='error', stage='Failed', lease_until=NULL, finished_at=?, "
                        "updated_at=?, error=? WHERE job_id=?",
                        (now, now, json.dumps({
                            "code": "WORKER_LOST",
                            "message": "The analysis worker stopped unexpectedly. Please upload the paper again.",
                        }), row["job_id"]),
                    )
                    failed.append(row["job_id"])
        return requeued, failed

    # -- retention ---------------------------------------------------------

    def delete_if_status(self, job_id: str, statuses: tuple[str, ...]) -> tuple[bool, str | None]:
        """Delete a job in one of ``statuses``. Returns (deleted, upload_path)."""
        marks = ",".join("?" for _ in statuses)
        with self._tx() as conn:
            row = conn.execute(
                f"SELECT path FROM jobs WHERE job_id=? AND status IN ({marks})", (job_id, *statuses)
            ).fetchone()
            if row is None:
                return False, None
            conn.execute("DELETE FROM jobs WHERE job_id=?", (job_id,))
        return True, row["path"]

    def finished_with_source(self, finished_before: float) -> list[tuple[str, str]]:
        rows = self._conn().execute(
            "SELECT job_id, path FROM jobs WHERE status IN ('done','error') AND path IS NOT NULL "
            "AND finished_at < ?", (finished_before,),
        ).fetchall()
        return [(row["job_id"], row["path"]) for row in rows]

    def clear_path(self, job_id: str) -> None:
        self._conn().execute("UPDATE jobs SET path=NULL WHERE job_id=?", (job_id,))

    def expired_jobs(self, finished_before: float) -> list[tuple[str, str | None]]:
        rows = self._conn().execute(
            "SELECT job_id, path FROM jobs WHERE status IN ('done','error') AND finished_at < ?",
            (finished_before,),
        ).fetchall()
        return [(row["job_id"], row["path"]) for row in rows]

    def overflow_jobs(self, keep: int) -> list[tuple[str, str | None]]:
        rows = self._conn().execute(
            "SELECT job_id, path FROM jobs WHERE status IN ('done','error') "
            "ORDER BY finished_at DESC LIMIT -1 OFFSET ?", (keep,),
        ).fetchall()
        return [(row["job_id"], row["path"]) for row in rows]

    def delete(self, job_id: str) -> None:
        self._conn().execute("DELETE FROM jobs WHERE job_id=?", (job_id,))

    def known_paths(self) -> set[str]:
        rows = self._conn().execute("SELECT path FROM jobs WHERE path IS NOT NULL").fetchall()
        return {row[0] for row in rows}
