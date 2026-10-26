import unittest

from api.pipeline.claims import extract_claims
from api.pipeline.ingest import build_sentence_index
from api.pipeline.textutils import is_verbatim
from api.tests.helpers import sample_document


class ClaimTests(unittest.TestCase):
    def test_heuristic_claims_are_verbatim_and_bounded(self):
        doc = sample_document()
        sentences = build_sentence_index(doc)
        claims, warnings = extract_claims(doc, sentences, use_llm=False)
        self.assertGreaterEqual(len(claims), 1)
        self.assertLessEqual(len(claims), 8)
        self.assertIsInstance(warnings, list)
        for claim in claims:
            self.assertTrue(is_verbatim(claim["text"], doc.full_text))
            self.assertIn(claim["claim_type"], {"quantitative", "qualitative", "comparative"})
            self.assertGreaterEqual(claim["page"], 1)
            self.assertTrue(claim["id"].startswith("c"))
            self.assertFalse(claim["section"].lower().startswith("reference"))
            self.assertFalse(claim["text"].startswith(("Method ", "Conclusion ", "Abstract ")))
        self.assertTrue(any(claim["claim_type"] == "quantitative" for claim in claims))

    def test_ids_are_unique(self):
        doc = sample_document()
        claims, _ = extract_claims(doc, build_sentence_index(doc), use_llm=False)
        ids = [claim["id"] for claim in claims]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
