import sys
import unittest
from unittest.mock import patch

from api.pipeline.tokenizer_study import study


class TokenizerStudyTests(unittest.TestCase):
    def test_baseline_always_works_without_transformers(self):
        text = "SparseRoute reduces latency by 42% on WMT14. The BERT baseline is dense."
        with patch.dict(sys.modules, {"transformers": None}):
            result = study(text, ["SparseRoute", "BERT"])
        self.assertIn("tokenizers", result)
        self.assertIn("term_splits", result)
        baseline = result["tokenizers"][0]
        self.assertTrue(baseline["available"])
        self.assertEqual(baseline["model"], "builtin")
        self.assertGreater(baseline["tokens"], 0)
        self.assertIn("note", result)
        self.assertEqual(len(result["term_splits"]), 2)
        for row in result["term_splits"]:
            self.assertIn("term", row)

    def test_empty_text_is_safe(self):
        with patch.dict(sys.modules, {"transformers": None}):
            result = study("", [])
        self.assertTrue(result["tokenizers"])
        self.assertEqual(result["term_splits"], [])


if __name__ == "__main__":
    unittest.main()
