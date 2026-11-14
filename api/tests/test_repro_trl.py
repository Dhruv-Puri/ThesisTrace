import unittest
from pathlib import Path

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


CORPUS = Path(__file__).resolve().parents[2] / "eval" / "corpus"


def _trl(name: str, **kwargs) -> dict:
    text = (CORPUS / name).read_text(encoding="utf-8")
    return assess_trl(ingest_text(text, name), [], None, **kwargs)


class TRLDetectionRegressionTests(unittest.TestCase):
    """Cases found by probing the v1 rubric (inflation, over-filtering, review misfire)."""

    def test_benchmark_words_are_not_a_real_world_environment(self):
        result = _trl("benchmark_only_certified_robustness.txt")
        self.assertEqual(result["level"], 4)
        self.assertFalse(result["signals"]["relevant"])
        self.assertFalse(result["signals"]["certified"])

    def test_hedged_deployment_is_a_near_miss_not_evidence(self):
        result = _trl("benchmark_only_certified_robustness.txt")
        self.assertFalse(result["signals"]["operational"])
        reasons = {item["reason"] for item in result["near_misses"]}
        self.assertIn("hedged or future wording", reasons)
        self.assertEqual(result["level_range"], [4, 5])

    def test_future_plans_do_not_count(self):
        result = _trl("hedged_future_deployment.txt")
        self.assertLessEqual(result["level"], 4)
        self.assertFalse(result["signals"]["field"])

    def test_other_peoples_deployments_do_not_count(self):
        result = _trl("related_work_deployment_by_others.txt")
        self.assertEqual(result["level"], 4)
        self.assertFalse(result["signals"]["operational"])

    def test_unrelated_not_and_will_do_not_delete_a_signal(self):
        result = _trl("deployed_fraud_system.txt")
        self.assertTrue(result["signals"]["baseline"])
        self.assertGreaterEqual(result["level"], 7)

    def test_baseline_is_not_required_for_environment_levels(self):
        text = (CORPUS / "deployed_fraud_system.txt").read_text(encoding="utf-8")
        text = text.replace(
            "Existing systems do not scale, and our model outperforms the baseline, which will be shown in Table 2.",
            "We report accuracy only.",
        )
        result = assess_trl(ingest_text(text, "nobase.txt"), [], None)
        self.assertFalse(result["signals"]["baseline"])
        self.assertGreaterEqual(result["level"], 7)

    def test_surveying_users_is_not_a_literature_review(self):
        result = _trl("user_survey_field_study.txt")
        self.assertFalse(result["review_document"])
        self.assertGreaterEqual(result["level"], 6)

    def test_real_survey_is_still_capped(self):
        result = _trl("survey_of_methods.txt")
        self.assertTrue(result["review_document"])
        self.assertLessEqual(result["level"], 3)

    def test_environment_wording_without_experiment_is_not_counted(self):
        doc = ingest_text(
            "Method\nWe propose a system. The system was deployed in production at the bank.",
            "noexp.txt",
        )
        result = assess_trl(doc, [], None)
        self.assertLessEqual(result["level"], 2)
        self.assertIn("without an experimental evaluation", result["note"])

    def test_future_work_section_is_never_evidence(self):
        text = LAB_PAPER + "\n5. Future Work\nWe ran a field trial in a hospital and deployed it in production at the bank.\n"
        result = assess_trl(ingest_text(text, "future.txt"), [], None)
        self.assertEqual(result["level"], 4)

    def test_result_exposes_confidence_range_and_flags(self):
        result = _trl("testbed_validation.txt")
        self.assertEqual(result["level"], 5)
        self.assertIn(result["confidence"], {"low", "medium", "high"})
        low, high = result["level_range"]
        self.assertLessEqual(low, result["level"])
        self.assertGreaterEqual(high, result["level"])
        self.assertFalse(result["nli_checked"])

    def test_nli_can_veto_environment_evidence(self):
        reject = lambda premise, hypothesis: {"entailment": 0.05, "neutral": 0.9, "contradiction": 0.05}
        result = _trl("deployed_fraud_system.txt", nli_scorer=reject)
        self.assertTrue(result["nli_checked"])
        self.assertEqual(result["level"], 4)
        self.assertTrue(any("NLI entailment" in item["reason"] for item in result["near_misses"]))

    def test_nli_confirmation_keeps_level_and_raises_confidence(self):
        accept = lambda premise, hypothesis: {"entailment": 0.97, "neutral": 0.02, "contradiction": 0.01}
        result = _trl("deployed_fraud_system.txt", nli_scorer=accept)
        self.assertGreaterEqual(result["level"], 7)
        self.assertEqual(result["confidence"], "high")
        self.assertTrue(all("nli" in e for e in result["evidence"] if e["level"] >= 5))

    def test_failed_nli_scorer_falls_back_to_regex(self):
        def broken(premise, hypothesis):
            raise RuntimeError("model down")
        result = _trl("deployed_fraud_system.txt", nli_scorer=broken)
        self.assertGreaterEqual(result["level"], 7)
        self.assertFalse(result["nli_checked"])


class TRLGoldSeedTests(unittest.TestCase):
    def test_seed_corpus_stays_within_one_level(self):
        from eval.run_trl_eval import evaluate

        report = evaluate()
        misses = [row["file"] for row in report["rows"] if not row["within1"]]
        self.assertEqual(misses, [])


if __name__ == "__main__":
    unittest.main()
