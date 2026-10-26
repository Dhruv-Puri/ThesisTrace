import unittest
from pathlib import Path
from unittest.mock import patch

from api.jobs import runner
from api.pipeline.ingest import IngestError
from api.tests.helpers import temp_dir


class JobTests(unittest.TestCase):
    def test_job_completes_and_exposes_result(self):
        def fake_analyze(path, filename, progress=None):
            if progress:
                progress(50, "Halfway")
            return {"status": "done", "doc": {"title": "Fake paper", "pages": 1}}

        with temp_dir() as tmp:
            path = Path(tmp) / "fake.txt"
            path.write_text("fake", encoding="utf-8")
            with patch("api.jobs.runner.analyze_document", fake_analyze):
                job = runner.create_job(path, "fake.txt")
                finished = runner.wait_for(job["job_id"], timeout=5)

        self.assertIsNotNone(finished)
        self.assertEqual(finished["status"], "done")
        self.assertEqual(finished["progress"], 100)
        self.assertEqual(finished["doc"]["title"], "Fake paper")

    def test_ingest_error_becomes_a_structured_job_error(self):
        def failing_analyze(path, filename, progress=None):
            raise IngestError("NO_TEXT_LAYER", "The PDF has no text layer.")

        with temp_dir() as tmp:
            path = Path(tmp) / "bad.pdf"
            path.write_bytes(b"%PDF-fake")
            with patch("api.jobs.runner.analyze_document", failing_analyze):
                job = runner.create_job(path, "bad.pdf")
                finished = runner.wait_for(job["job_id"], timeout=5)

        self.assertEqual(finished["status"], "error")
        self.assertEqual(finished["error"]["code"], "NO_TEXT_LAYER")


if __name__ == "__main__":
    unittest.main()
