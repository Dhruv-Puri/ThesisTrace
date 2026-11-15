import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from api.jobs import runner
from api.pipeline import research_differentiator, research_profile
from api.tests.helpers import SAMPLE_PAPER, temp_dir

HAS_FASTAPI = bool(
    importlib.util.find_spec("fastapi") and importlib.util.find_spec("httpx")
)


def _paper(tmp: str, text: str = SAMPLE_PAPER) -> Path:
    path = Path(tmp) / "paper.txt"
    path.write_text(text, encoding="utf-8")
    return path


@unittest.skipUnless(HAS_FASTAPI, "FastAPI / TestClient is required for route tests")
class ResearchDifferentiatorApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from api.main import app

        cls.client = TestClient(app)

    def _finished_job(self, tmp: str) -> str:
        path = _paper(tmp)
        with patch("api.jobs.runner.analyze_document", lambda *a, **k: {
            "status": "done",
            "doc": {"title": "Test Paper"},
        }):
            job = runner.create_job(path, "paper.txt")
            runner.wait_for(job["job_id"], timeout=5)
        return job["job_id"]

    def test_missing_key_returns_503(self):
        with temp_dir() as tmp, patch("api.pipeline.config.GEMINI_API_KEY", ""):
            job_id = self._finished_job(tmp)
            response = self.client.post(f"/api/jobs/{job_id}/differentiate")
        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertEqual(body["error"]["code"], "DIFFERENTIATOR_DISABLED")

    def test_invalid_limit_returns_400(self):
        with temp_dir() as tmp, patch("api.pipeline.config.GEMINI_API_KEY", "test-key"):
            job_id = self._finished_job(tmp)
            response = self.client.post(f"/api/jobs/{job_id}/differentiate?limit=99")
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["error"]["code"], "INVALID_LIMIT")

    def test_unknown_job_returns_404(self):
        with patch("api.pipeline.config.GEMINI_API_KEY", "test-key"):
            response = self.client.post("/api/jobs/missing-id/differentiate")
        self.assertEqual(response.status_code, 404)
        body = response.json()
        self.assertEqual(body["error"]["code"], "JOB_NOT_FOUND")

    def test_successful_differentiation_round_trip(self):
        fake_profile = {
            "research_problem": "Inference latency in neural translation",
            "methodology": "Sparse conditional computation",
            "architecture_or_model": "SparseRoute",
            "main_contributions": ["42% latency reduction"],
            "datasets": ["WMT14"],
        }
        fake_discovery = {
            "query": "Inference latency SparseRoute WMT14",
            "papers": [{
                "id": "https://openalex.org/W123",
                "doi": "https://doi.org/10.1234/test",
                "title": "Dense Transformers",
                "year": 2021,
                "type": "article",
                "authors": ["Alice Smith"],
                "venue": "NeurIPS",
                "citations": 45,
                "abstract": "Dense baseline models are slow.",
            }],
            "warnings": [],
        }
        fake_comparison = {
            "comparison": {
                "overall_assessment": "Meaningful efficiency contribution.",
                "novelty_assessment": "Adaptive routing is novel relative to retrieved dense baselines.",
                "established_elements": ["Standard transformer encoder"],
                "potentially_novel_elements": ["SparseRoute routing mechanism"],
                "methodology_comparison": ["SparseRoute activates 30% of layers vs 100% in Alice Smith 2021"],
                "dataset_comparison": ["Both evaluated on WMT14 En-De"],
                "metric_and_result_comparison": ["42% lower latency with minor BLEU impact"],
                "research_gaps": ["Not tested on multilingual corpora"],
                "limitations": ["Requires hardware support for dynamic execution"],
                "evidence_and_uncertainties": ["Only tested on a single GPU"],
            },
            "warnings": [],
        }

        with temp_dir() as tmp, patch("api.pipeline.config.GEMINI_API_KEY", "test-key"):
            with patch(
                "api.pipeline.research_profile.extract_research_profile",
                return_value={"profile": fake_profile, "extraction": "gemini", "warnings": []},
            ), patch(
                "api.pipeline.research_differentiator.discover_related_papers",
                return_value=fake_discovery,
            ), patch(
                "api.pipeline.research_differentiator.compare_with_literature",
                return_value=fake_comparison,
            ):
                job_id = self._finished_job(tmp)
                response = self.client.post(f"/api/jobs/{job_id}/differentiate?limit=5")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["job_id"], job_id)
        self.assertEqual(body["search_query"], "Inference latency SparseRoute WMT14")
        self.assertEqual(len(body["related_papers"]), 1)
        self.assertEqual(body["related_papers"][0]["title"], "Dense Transformers")
        self.assertEqual(body["comparison"]["overall_assessment"], "Meaningful efficiency contribution.")
        self.assertEqual(len(body["comparison"]["potentially_novel_elements"]), 1)
