import unittest

from api.pipeline.report import build_report, enforce_citations, polish_markdown, _parse_sections
from api.tests.helpers import sample_document


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.doc = sample_document()
        self.stats = {
            "words": 1200,
            "sections": 6,
            "reading_minutes": 6,
            "technical_term_density": 0.044,
            "complexity_score": 4.2,
        }
        self.summary = {"bullets": ["One.", "Two.", "Three."]}
        self.key_concepts = {
            "datasets": [{"name": "WMT14", "pages": [1], "count": 2, "type": "DATASET"}],
            "models": [{"name": "Transformer", "pages": [1], "count": 3, "type": "MODEL"}],
            "metrics": [{"name": "BLEU", "pages": [1], "count": 1, "type": "METRIC"}],
            "others": [],
        }
        self.claims = [
            {
                "id": "c1",
                "text": "Our method reduces latency by 42% compared with the baseline.",
                "claim_type": "quantitative",
                "page": 1,
                "verdict": "supported",
                "confidence": 0.8,
                "evidence": [{"page": 3, "text": "latency fell by 42%"}],
                "note": "",
            },
            {
                "id": "c2",
                "text": "The approach is ready for production deployment.",
                "claim_type": "qualitative",
                "page": 1,
                "verdict": "partially_supported",
                "confidence": 0.5,
                "evidence": [{"page": 4, "text": "lab only"}],
                "note": "Only lab evidence is reported [p.4].",
            },
        ]
        self.repro = {
            "score": 57,
            "items": [
                {"key": "dataset_available", "name": "Dataset availability", "status": "yes"},
                {"key": "random_seed", "name": "Random seed reported", "status": "no"},
            ],
            "summary": "1 present, 0 partial, 1 missing.",
            "note": "Text-level audit only; no code was executed.",
        }
        self.trl = {
            "level": 4,
            "label": "Technology validated in lab",
            "evidence": [{"signal": "baseline", "level": 4, "page": 4, "quote": "baseline"}],
            "why": "Level 4 is supported.",
            "note": "No field evidence.",
        }

    def test_report_bullets_and_markdown(self):
        report, warnings = build_report(
            self.doc, self.stats, self.summary, self.key_concepts,
            self.claims, self.repro, self.trl,
        )
        self.assertIsInstance(warnings, list)
        self.assertTrue(report["proven"])
        self.assertIn("[p.3]", report["proven"][0])
        self.assertTrue(report["not_proven"])
        self.assertIn("[p.4]", report["not_proven"][0])
        self.assertIn("## 2. What is proven", report["markdown"])
        self.assertIn("TRL 4/9", report["markdown"])
        self.assertIn("57/100", report["markdown"])
        self.assertIn("Random seed reported", " ".join(report["risks"]))

    def test_citation_enforcement_drops_uncited_lines(self):
        text = "## Risks\n- Supported statement [p.1]\n- Unsupported statement\n- Wrong page [p.9]"
        filtered, dropped = enforce_citations(text, {1})
        self.assertEqual(dropped, 2)
        self.assertIn("Supported statement", filtered)
        self.assertNotIn("Unsupported statement", filtered)
        self.assertNotIn("[p.9]", filtered)

    def test_section_parser(self):
        sections = _parse_sections("## A\n- one\n## B\n- two")
        self.assertEqual(sections["a"], "- one")
        self.assertEqual(sections["b"], "- two")

    def test_polish_is_a_noop_without_a_key(self):
        base = "## 3. What is not proven\n- A claim [p.1]"
        text, warnings = polish_markdown(base, {}, {1})
        self.assertEqual(text, base)
        self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
