import json
import unittest
from pathlib import Path
from unittest.mock import patch

from api.pipeline import config
from api.pipeline.analyze import analyze_document
from api.tests.helpers import SAMPLE_PAPER, temp_dir


class AnalyzeTests(unittest.TestCase):
    def test_end_to_end_contract_without_models(self):
        with temp_dir() as tmp:
            path = Path(tmp) / "paper.txt"
            path.write_text(SAMPLE_PAPER, encoding="utf-8")
            with patch.object(config, "TOKENIZER_STUDY_ENABLED", False):
                result = analyze_document(path, "paper.txt", use_llm=False, use_nli=False)

        expected = {
            "status", "doc", "stats", "summary", "entities", "key_concepts",
            "claims", "reproducibility", "trl", "report", "tokenization",
            "key_terms", "signals", "timings", "warnings", "pipeline_version", "engine",
        }
        self.assertTrue(expected.issubset(result.keys()))
        self.assertEqual(result["status"], "done")
        self.assertEqual(result["doc"]["filename"], "paper.txt")
        self.assertEqual(len(result["summary"]["bullets"]), 3)
        self.assertLessEqual(len(result["claims"]), 8)
        self.assertEqual(len(result["reproducibility"]["items"]), 12)
        self.assertGreaterEqual(result["trl"]["level"], 1)
        self.assertLessEqual(result["trl"]["level"], 9)
        self.assertIn("Executive Report", result["report"]["markdown"])
        self.assertIn("total_ms", result["timings"])
        self.assertIsInstance(result["warnings"], list)
        self.assertEqual(result["tokenization"]["tokenizers"], [])
        json.dumps(result, ensure_ascii=False)

    def test_low_text_document_is_flagged(self):
        with temp_dir() as tmp:
            path = Path(tmp) / "tiny.txt"
            path.write_text("Abstract\nA short abstract about a model.", encoding="utf-8")
            with patch.object(config, "TOKENIZER_STUDY_ENABLED", False):
                result = analyze_document(path, "tiny.txt", use_llm=False, use_nli=False)
        self.assertTrue(any("little text" in warning.lower() for warning in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
