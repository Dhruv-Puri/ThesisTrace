import unittest

from api.pipeline.classical import extract_regex_facts
from api.pipeline.gazetteer import find_entities
from api.pipeline.ingest import ingest_text
from api.pipeline.repro import assess_reproducibility
from api.pipeline.trl import assess_trl
from api.tests.helpers import FIELD_PAPER, LAB_PAPER, REVIEW_PAPER, sample_document


class ReproTests(unittest.TestCase):
    def test_reproducibility_signals_and_score(self):
        doc = sample_document()
        entities = find_entities(doc)
        facts = extract_regex_facts(doc)
        report = assess_reproducibility(doc, entities, facts)

        by_key = {item["key"]: item for item in report["items"]}
        self.assertEqual(by_key["dataset_available"]["status"], "yes")
        self.assertEqual(by_key["code_available"]["status"], "yes")
        self.assertEqual(by_key["hyperparameters"]["status"], "yes")
        self.assertEqual(by_key["random_seed"]["status"], "yes")
        self.assertEqual(by_key["baseline"]["status"], "yes")
        self.assertEqual(by_key["metrics"]["status"], "yes")
        self.assertGreaterEqual(report["score"], 50)
        self.assertLessEqual(report["score"], 100)
        self.assertEqual(len(report["items"]), 12)
        self.assertIn("no code was executed", report["note"].lower())

    def test_missing_signals_are_explicit(self):
        doc = ingest_text(
            "Method\nWe describe a method without any reproducibility details.",
            "sparse.txt",
        )
        report = assess_reproducibility(doc, [], {})
        self.assertLess(report["score"], 50)
        for item in report["items"]:
            self.assertIn(item["status"], {"yes", "partial", "no"})
            self.assertTrue(item["evidence"])


class TRLTests(unittest.TestCase):
    def test_lab_paper_is_level_4(self):
        doc = ingest_text(LAB_PAPER, "lab.txt")
        readiness = assess_trl(doc, [], None)
        self.assertEqual(readiness["level"], 4)
        self.assertIn("4", readiness["why"])

    def test_field_trial_raises_level_but_negation_does_not(self):
        field_doc = ingest_text(FIELD_PAPER, "field.txt")
        field = assess_trl(field_doc, [], None)
        self.assertGreaterEqual(field["level"], 6)

        negated = FIELD_PAPER.replace(
            "We conducted a field trial in a hospital and validated the method in a relevant clinical environment.",
            "No field trial was conducted.",
        )
        negated_doc = ingest_text(negated, "negated.txt")
        self.assertLess(assess_trl(negated_doc, [], None)["level"], 6)

    def test_review_is_capped_and_evidence_is_cited(self):
        doc = ingest_text(REVIEW_PAPER, "review.txt")
        readiness = assess_trl(doc, [], None)
        self.assertLessEqual(readiness["level"], 3)
        self.assertTrue(readiness["review_document"])
        for item in readiness["evidence"]:
            self.assertGreaterEqual(item["page"], 1)
            self.assertIn("signal", item)
            self.assertIn("quote", item)


if __name__ == "__main__":
    unittest.main()
