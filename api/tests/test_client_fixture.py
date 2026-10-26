import json
import unittest
from pathlib import Path

from api.pipeline import config


MOCK_PATH = config.ROOT / "client" / "src" / "mocks" / "paperAnalysis.json"


class ClientFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock = json.loads(MOCK_PATH.read_text(encoding="utf-8"))

    def test_fixture_has_the_full_analysis_contract(self):
        required = {
            "doc", "stats", "summary", "entities", "key_concepts", "claims",
            "reproducibility", "trl", "report", "tokenization", "key_terms",
            "signals", "timings", "warnings", "pipeline_version", "engine",
        }
        self.assertTrue(required.issubset(self.mock))
        self.assertEqual(self.mock["status"], "done")
        self.assertTrue(self.mock["job_id"].startswith("demo"))

    def test_fixture_score_matches_its_checklist(self):
        report = self.mock["reproducibility"]
        items = report["items"]
        self.assertEqual(len(items), 12)
        earned = sum(item["weight"] * item["points"] for item in items)
        total = sum(item["weight"] for item in items)
        self.assertEqual(report["score"], round(100 * earned / total))
        yes = sum(1 for item in items if item["status"] == "yes")
        partial = sum(1 for item in items if item["status"] == "partial")
        self.assertEqual(report["summary"], f"{yes} present, {partial} partial, "
                                            f"{len(items) - yes - partial} missing.")
        self.assertIn(f"{report['score']}/100", self.mock["report"]["markdown"])

    def test_fixture_citations_and_bounds(self):
        self.assertTrue(1 <= self.mock["trl"]["level"] <= 9)
        for claim in self.mock["claims"]:
            self.assertIn(claim["verdict"],
                          {"supported", "partially_supported", "insufficient"})
            self.assertGreaterEqual(claim["page"], 1)
            for item in claim["evidence"]:
                self.assertGreaterEqual(item["page"], 1)
        for term in self.mock["key_terms"]:
            self.assertGreaterEqual(term["score"], 0)


if __name__ == "__main__":
    unittest.main()
