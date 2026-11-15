import importlib.util
import os
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from api.jobs import cleanup, runner
from api.jobs.store import JobStore, QueueFull
from api.pipeline.ingest import IngestError
from api.tests.helpers import isolated_jobs, temp_dir

HAS_FASTAPI = bool(importlib.util.find_spec("fastapi") and importlib.util.find_spec("httpx")
                   and importlib.util.find_spec("multipart"))


def _ok(path, filename, progress=None):
    if progress:
        progress(40, "Working")
    return {"status": "done", "doc": {"title": filename}}


def _upload(tmp: str, name: str = "p.txt") -> Path:
    path = Path(tmp) / "uploads" / name
    path.write_text("some paper text " * 20, encoding="utf-8")
    return path


class StoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = temp_dir()
        self.dir = Path(self._tmp.name)
        self.store = JobStore(self.dir / "j.sqlite3", max_queue=50, max_attempts=2)
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(self.store.close)

    def test_fifo_claim_and_fencing(self):
        self.store.enqueue("a", "a.txt", "/x/a", now=1)
        self.store.enqueue("b", "b.txt", "/x/b", now=2)
        first = self.store.claim("w1", 30, now=10)
        second = self.store.claim("w2", 30, now=10)
        self.assertEqual((first["job_id"], second["job_id"]), ("a", "b"))
        self.assertIsNone(self.store.claim("w3", 30, now=10))
        self.assertFalse(self.store.finish("a", "w2", {"x": 1}), "only the owner may finish")
        self.assertTrue(self.store.finish("a", "w1", {"x": 1}))
        self.assertEqual(self.store.get("a")["result"], {"x": 1})

    def test_claim_is_atomic_under_contention(self):
        for index in range(40):
            self.store.enqueue(f"j{index}", "f.txt", None, now=index)
        claimed: list[str] = []
        lock = threading.Lock()

        def grab(name):
            while True:
                job = self.store.claim(name, 60)
                if job is None:
                    return
                with lock:
                    claimed.append(job["job_id"])

        threads = [threading.Thread(target=grab, args=(f"w{n}",)) for n in range(6)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(len(claimed), 40)
        self.assertEqual(len(set(claimed)), 40, "no job was claimed twice")

    def test_queue_is_bounded(self):
        small = JobStore(self.dir / "small.sqlite3", max_queue=2)
        self.addCleanup(small.close)
        small.enqueue("a", "a", None)
        small.enqueue("b", "b", None)
        self.assertFalse(small.has_capacity())
        with self.assertRaises(QueueFull):
            small.enqueue("c", "c", None)
        small.claim("w", 30)
        small.finish("a", "w", {})
        self.assertTrue(small.has_capacity())

    def test_expired_lease_is_retried_then_failed(self):
        self.store.enqueue("a", "a.txt", None, now=0)
        self.store.claim("dead", 10, now=100)
        self.assertEqual(self.store.requeue_expired(now=105), ([], []), "lease still valid")
        self.assertEqual(self.store.requeue_expired(now=200), (["a"], []))
        self.assertEqual(self.store.get("a")["status"], "queued")
        self.store.claim("dead2", 10, now=300)
        self.assertEqual(self.store.requeue_expired(now=400), ([], ["a"]))
        job = self.store.get("a")
        self.assertEqual(job["status"], "error")
        self.assertEqual(job["error"]["code"], "WORKER_LOST")

    def test_zombie_worker_cannot_overwrite_a_retried_job(self):
        self.store.enqueue("a", "a.txt", None, now=0)
        self.store.claim("zombie", 10, now=100)
        self.store.requeue_expired(now=200)
        self.store.claim("healthy", 10, now=300)
        self.assertFalse(self.store.progress("a", "zombie", 50, "late", 10, now=301))
        self.assertFalse(self.store.finish("a", "zombie", {"stale": True}, now=301))
        self.assertTrue(self.store.finish("a", "healthy", {"fresh": True}, now=302))
        self.assertEqual(self.store.get("a")["result"], {"fresh": True})

    def test_jobs_survive_a_restart(self):
        path = self.dir / "durable.sqlite3"
        first = JobStore(path)
        first.enqueue("a", "a.txt", "/x/a")
        first.enqueue("b", "b.txt", "/x/b")
        first.claim("w", 30)
        first.finish("a", "w", {"answer": 42})
        first.close()
        second = JobStore(path)
        self.addCleanup(second.close)
        self.assertEqual(second.get("a")["result"], {"answer": 42})
        self.assertEqual(second.get("b")["status"], "queued")

    def test_queue_ahead_counts_running_and_earlier_jobs(self):
        for index, name in enumerate("abc"):
            self.store.enqueue(name, f"{name}.txt", None, now=index)
        self.store.claim("w", 30)  # a is running
        self.assertEqual(self.store.queue_ahead(self.store.get("b")), 1)
        self.assertEqual(self.store.queue_ahead(self.store.get("c")), 2)


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self._tmp = temp_dir()
        self.dir = Path(self._tmp.name)
        self.uploads = self.dir / "uploads"
        self.uploads.mkdir()
        self.store = JobStore(self.dir / "j.sqlite3")
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(self.store.close)

    def _finished(self, name: str, finished_at: float) -> Path:
        path = self.uploads / f"{name}.txt"
        path.write_text("paper", encoding="utf-8")
        self.store.enqueue(name, f"{name}.txt", path, now=finished_at - 5)
        self.store.claim("w", 30, now=finished_at - 4)
        self.store.finish(name, "w", {"ok": True}, now=finished_at)
        return path

    def _sweep(self, now: float, **kw):
        args = dict(upload_ttl=100, result_ttl=1000, max_stored=50, now=now)
        args.update(kw)
        return cleanup.sweep(self.store, self.uploads, **args)

    def test_upload_is_deleted_after_ttl_but_the_result_stays(self):
        path = self._finished("a", 1000)
        self._sweep(1050)
        self.assertTrue(path.exists(), "still inside the upload TTL")
        stats = self._sweep(1101)
        self.assertFalse(path.exists())
        self.assertEqual(stats["uploads_deleted"], 1)
        job = self.store.get("a")
        self.assertIsNone(job["path"])
        self.assertEqual(job["result"], {"ok": True})

    def test_job_is_deleted_after_result_ttl(self):
        self._finished("a", 1000)
        stats = self._sweep(2001)
        self.assertEqual(stats["jobs_deleted"], 1)
        self.assertIsNone(self.store.get("a"))

    def test_only_the_newest_finished_jobs_are_kept(self):
        for index in range(5):
            self._finished(f"j{index}", 1000 + index)
        self._sweep(1010, max_stored=2, upload_ttl=10_000, result_ttl=10_000)
        remaining = sorted(job for job in ("j0", "j1", "j2", "j3", "j4") if self.store.get(job))
        self.assertEqual(remaining, ["j3", "j4"])

    def test_active_jobs_are_never_swept(self):
        path = self.uploads / "q.txt"
        path.write_text("x", encoding="utf-8")
        self.store.enqueue("q", "q.txt", path, now=0)
        self._sweep(10_000_000)
        self.assertTrue(path.exists())
        self.assertEqual(self.store.get("q")["status"], "queued")

    def test_orphan_files_are_removed_after_the_grace_period_only(self):
        old = self.uploads / "orphan-old.txt"
        new = self.uploads / "orphan-new.txt"
        for path in (old, new):
            path.write_text("x", encoding="utf-8")
        now = time.time()
        os.utime(old, (now - 7200, now - 7200))
        referenced = self._finished("keep", now)
        os.utime(referenced, (now - 7200, now - 7200))
        stats = cleanup.sweep(self.store, self.uploads, upload_ttl=10_000, result_ttl=10_000,
                              max_stored=50, now=now)
        self.assertFalse(old.exists())
        self.assertTrue(new.exists(), "recent files may belong to an upload in progress")
        self.assertTrue(referenced.exists(), "files a job still references are kept")
        self.assertEqual(stats["orphans_deleted"], 1)

    def test_never_deletes_outside_the_upload_directory(self):
        outside = self.dir / "precious.txt"
        outside.write_text("do not delete", encoding="utf-8")
        self.store.enqueue("evil", "evil.txt", outside, now=0)
        self.store.claim("w", 30, now=1)
        self.store.finish("evil", "w", {}, now=2)
        self._sweep(10_000_000, result_ttl=1)
        self.assertTrue(outside.exists())
        self.assertFalse(cleanup.remove_upload(outside, self.uploads))

    def test_sweep_fails_jobs_whose_worker_vanished_and_removes_their_upload(self):
        path = self.uploads / "lost.txt"
        path.write_text("x", encoding="utf-8")
        self.store.enqueue("lost", "lost.txt", path, now=0)
        self.store.claim("dead", 10, now=1)
        self.store.requeue_expired(now=100)           # attempt 1 -> queued again
        self.store.claim("dead", 10, now=200)         # attempt 2, dies again
        stats = self._sweep(400)
        self.assertEqual(stats["failed"], 1)
        self.assertFalse(path.exists())
        self.assertEqual(self.store.get("lost")["error"]["code"], "WORKER_LOST")


class RunnerTests(unittest.TestCase):
    def test_workers_run_jobs_in_parallel_up_to_the_pool_size(self):
        for workers, expected_max in ((1, 1), (2, 2)):
            active = {"now": 0, "max": 0}
            lock = threading.Lock()

            def slow(path, filename, progress=None):
                with lock:
                    active["now"] += 1
                    active["max"] = max(active["max"], active["now"])
                time.sleep(0.15)
                with lock:
                    active["now"] -= 1
                return {"status": "done"}

            with isolated_jobs(workers=workers) as tmp, patch("api.jobs.runner.analyze_document", slow):
                ids = [runner.create_job(_upload(tmp, f"p{n}.txt"), f"p{n}.txt")["job_id"] for n in range(4)]
                results = [runner.wait_for(job_id, timeout=10) for job_id in ids]
            self.assertTrue(all(r["status"] == "done" for r in results))
            self.assertEqual(active["max"], expected_max, f"workers={workers}")

    def test_queue_full_and_position_reporting(self):
        gate = threading.Event()

        def blocked(path, filename, progress=None):
            gate.wait(10)
            return {"status": "done"}

        with isolated_jobs(max_queue=2) as tmp, patch("api.jobs.runner.analyze_document", blocked):
            try:
                first = runner.create_job(_upload(tmp, "a.txt"), "a.txt")
                for _ in range(100):
                    if runner.get_job(first["job_id"])["status"] == "running":
                        break
                    time.sleep(0.02)
                second = runner.create_job(_upload(tmp, "b.txt"), "b.txt")
                info = runner.get_job(second["job_id"])
                self.assertEqual(info["status"], "queued")
                self.assertEqual(info["queue_ahead"], 1)
                self.assertIn("ahead", info["stage"])
                self.assertFalse(runner.has_capacity())
                with self.assertRaises(QueueFull):
                    runner.create_job(_upload(tmp, "c.txt"), "c.txt")
                self.assertEqual(runner.queue_stats()["queued"], 1)
            finally:
                gate.set()
            self.assertEqual(runner.wait_for(second["job_id"], timeout=10)["status"], "done")

    def test_a_job_that_runs_too_long_is_stopped(self):
        def endless(path, filename, progress=None):
            for _ in range(100):
                time.sleep(0.05)
                progress(10, "Still going")
            return {"status": "done"}

        with isolated_jobs(timeout_seconds=0.1) as tmp, patch("api.jobs.runner.analyze_document", endless):
            path = _upload(tmp)
            job = runner.create_job(path, "p.txt")
            finished = runner.wait_for(job["job_id"], timeout=10)
        self.assertEqual(finished["status"], "error")
        self.assertEqual(finished["error"]["code"], "JOB_TIMEOUT")
        self.assertFalse(path.exists())

    def test_unexpected_errors_do_not_kill_the_worker(self):
        calls = {"n": 0}

        def flaky(path, filename, progress=None):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("boom")
            return {"status": "done"}

        with isolated_jobs() as tmp, patch("api.jobs.runner.analyze_document", flaky):
            bad = runner.wait_for(runner.create_job(_upload(tmp, "a.txt"), "a.txt")["job_id"], 5)
            good = runner.wait_for(runner.create_job(_upload(tmp, "b.txt"), "b.txt")["job_id"], 5)
        self.assertEqual(bad["error"]["code"], "ANALYSIS_FAILED")
        self.assertNotIn("boom", bad["error"]["message"], "internals are not leaked")
        self.assertEqual(good["status"], "done")

    def test_jobs_wait_durably_when_no_worker_runs_then_finish_after_restart(self):
        with isolated_jobs(mode="external") as tmp:
            path = _upload(tmp)
            job = runner.create_job(path, "p.txt")
            time.sleep(0.2)
            self.assertEqual(runner.get_job(job["job_id"])["status"], "queued")
            db_path = Path(tmp) / "jobs.sqlite3"
            runner.reset(db_path=db_path, upload_dir=Path(tmp) / "uploads",
                         poll_interval=0.02, cleanup_interval=3600.0)  # "restart" in inline mode
            with patch("api.jobs.runner.analyze_document", _ok):
                runner.start()
                finished = runner.wait_for(job["job_id"], timeout=5)
        self.assertEqual(finished["status"], "done")

    def test_a_job_orphaned_by_a_crashed_worker_is_recovered_on_start(self):
        with isolated_jobs(mode="external") as tmp:
            job = runner.create_job(_upload(tmp), "p.txt")
            runner._store().claim("crashed-worker", 0.01)       # claimed, then the process died
            time.sleep(0.05)
            runner.reset(db_path=Path(tmp) / "jobs.sqlite3", upload_dir=Path(tmp) / "uploads",
                         poll_interval=0.02, cleanup_interval=3600.0)
            with patch("api.jobs.runner.analyze_document", _ok):
                runner.start()
                finished = runner.wait_for(job["job_id"], timeout=5)
        self.assertEqual(finished["status"], "done")

    def test_delete_job(self):
        gate = threading.Event()

        def blocked(path, filename, progress=None):
            gate.wait(10)
            return {"status": "done"}

        with isolated_jobs() as tmp, patch("api.jobs.runner.analyze_document", blocked):
            try:
                a = runner.create_job(_upload(tmp, "a.txt"), "a.txt")
                for _ in range(100):
                    if runner.get_job(a["job_id"])["status"] == "running":
                        break
                    time.sleep(0.02)
                queued_path = _upload(tmp, "b.txt")
                b = runner.create_job(queued_path, "b.txt")
                self.assertEqual(runner.delete_job(a["job_id"]), "active")
                self.assertEqual(runner.delete_job(b["job_id"]), "deleted")
                self.assertFalse(queued_path.exists())
                self.assertEqual(runner.delete_job("nope"), "missing")
            finally:
                gate.set()
            self.assertEqual(runner.wait_for(a["job_id"], 5)["status"], "done")
            source = runner.get_source(a["job_id"])
            self.assertEqual(runner.delete_job(a["job_id"]), "deleted")
            self.assertFalse(source[0].exists())
            self.assertIsNone(runner.get_job(a["job_id"]))


@unittest.skipUnless(HAS_FASTAPI, "fastapi/httpx/python-multipart not installed")
class QueueApiTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from api.main import app

        self.client = TestClient(app)

    def _post(self, name="p.txt", body=b"A paper about sparse routing and its evaluation. " * 10):
        return self.client.post("/api/jobs", files={"file": (name, body, "text/plain")})

    def test_upload_poll_and_delete_round_trip(self):
        with isolated_jobs() as tmp, patch("api.pipeline.config.UPLOAD_DIR", Path(tmp) / "uploads"), \
                patch("api.jobs.runner.analyze_document", _ok):
            response = self._post()
            self.assertEqual(response.status_code, 202)
            job_id = response.json()["job_id"]
            self.assertEqual(len(job_id), 32)
            runner.wait_for(job_id, timeout=5)
            self.assertEqual(self.client.get(f"/api/jobs/{job_id}").json()["status"], "done")
            self.assertEqual(len(list((Path(tmp) / "uploads").iterdir())), 1)
            self.assertEqual(self.client.delete(f"/api/jobs/{job_id}").status_code, 200)
            self.assertEqual(self.client.get(f"/api/jobs/{job_id}").status_code, 404)
            self.assertEqual(list((Path(tmp) / "uploads").iterdir()), [], "the upload is removed")
            self.assertEqual(self.client.delete(f"/api/jobs/{job_id}").status_code, 404)

    def test_full_queue_returns_503_and_leaves_no_file_behind(self):
        gate = threading.Event()

        def blocked(path, filename, progress=None):
            gate.wait(10)
            return {"status": "done"}

        with isolated_jobs(max_queue=1) as tmp, patch("api.pipeline.config.UPLOAD_DIR", Path(tmp) / "uploads"), \
                patch("api.jobs.runner.analyze_document", blocked):
            try:
                first = self._post("a.txt")
                self.assertEqual(first.status_code, 202)
                second = self._post("b.txt")
                self.assertEqual(second.status_code, 503)
                self.assertEqual(second.json()["error"]["code"], "QUEUE_FULL")
                self.assertEqual(second.headers.get("retry-after"), "30")
                self.assertEqual(len(list((Path(tmp) / "uploads").iterdir())), 1)
                first_id = first.json()["job_id"]
                for _ in range(100):
                    if runner.get_job(first_id)["status"] == "running":
                        break
                    time.sleep(0.02)
                self.assertEqual(self.client.delete(f"/api/jobs/{first_id}").status_code, 409,
                                 "a running job cannot be deleted")
            finally:
                gate.set()

    def test_a_fake_pdf_is_rejected_before_it_is_queued(self):
        with isolated_jobs() as tmp, patch("api.pipeline.config.UPLOAD_DIR", Path(tmp) / "uploads"):
            response = self._post("paper.pdf", b"this is plainly not a pdf document " * 10)
            self.assertEqual(response.status_code, 415)
            self.assertEqual(list((Path(tmp) / "uploads").iterdir()), [])
            self.assertEqual(runner.queue_stats()["queued"], 0)

    def test_health_reports_the_queue(self):
        with isolated_jobs():
            body = self.client.get("/api/health").json()
        self.assertIn("queue", body)
        self.assertEqual(body["queue"]["mode"], "inline")
        self.assertIn("queued", body["queue"])


if __name__ == "__main__":
    unittest.main()
