import unittest
from pathlib import Path

from api.pipeline.artifacts import collect_artifacts
from api.pipeline.ingest import build_document, ingest_text
from api.pipeline.trl import assess_trl

CORPUS = Path(__file__).resolve().parents[2] / "eval" / "corpus"

BASE = """Toy Paper

Abstract
We propose a method and evaluate it on a benchmark.

1. Method
We design a small model.

2. Experiments
We evaluate on a benchmark. Our model outperforms the baseline.
{extra}
"""


def _doc(extra: str = "", head: str = ""):
    return ingest_text(head + BASE.format(extra=extra), "toy.txt")


def _status(result, key):
    return next(item for item in result["classes"] if item["key"] == key)["status"]


class ArtifactDetectionTests(unittest.TestCase):
    def test_full_release_is_detected_and_raises_the_level(self):
        text = (CORPUS / "released_toolkit.txt").read_text(encoding="utf-8")
        doc = ingest_text(text, "kit.txt")
        found = collect_artifacts(doc)
        for key in ("source_released", "installable", "container", "api_service", "live_demo",
                    "tests_ci", "documentation", "license"):
            self.assertEqual(_status(found, key), "available", key)
        self.assertEqual(found["level_hint"], 6)
        trl = assess_trl(doc, [], None)
        self.assertEqual(trl["level"], 6)
        self.assertTrue(trl["signals"]["artifacts"])
        self.assertTrue(any(e["signal"] == "artifacts" for e in trl["evidence"]))

    def test_front_matter_link_is_read(self):
        doc = _doc(head="Code: https://github.com/lab/proj\n\n")
        self.assertEqual(_status(collect_artifacts(doc), "source_released"), "available")

    def test_references_are_ignored(self):
        doc = _doc("\nReferences\n[1] Smith et al. Baseline. Code at https://github.com/smith/baseline\n")
        self.assertEqual(_status(collect_artifacts(doc), "source_released"), "absent")

    def test_promised_artifacts_do_not_count_but_show_as_near_miss(self):
        doc = _doc("\n3. Conclusion\nOur code will be released upon acceptance.\n")
        found = collect_artifacts(doc)
        self.assertEqual(_status(found, "source_released"), "promised")
        self.assertEqual(found["level_hint"], 0)
        trl = assess_trl(doc, [], None)
        self.assertEqual(trl["level"], 4)
        self.assertEqual(trl["level_range"], [4, 5])
        self.assertTrue(any("promised" in n["reason"] for n in trl["near_misses"]))

    def test_third_party_code_is_not_the_authors_artifact(self):
        doc = _doc("\n3. Conclusion\nWe build on the implementation at https://github.com/facebookresearch/fairseq.\n")
        found = collect_artifacts(doc)
        self.assertEqual(_status(found, "source_released"), "absent")
        self.assertTrue(any(r["reason"].startswith("third-party") for r in found["rejected"]))

    def test_negated_and_cited_statements_are_rejected(self):
        doc = _doc("\n3. Conclusion\nNo code is publicly available at github.com/lab/x. "
                   "Smith et al. [4] released a Docker image.\n")
        found = collect_artifacts(doc)
        self.assertEqual(_status(found, "source_released"), "absent")
        self.assertEqual(_status(found, "container"), "absent")

    def test_one_artifact_alone_does_not_raise_the_level(self):
        doc = _doc("\n3. Conclusion\nOur code is available at github.com/lab/proj.\n")
        found = collect_artifacts(doc)
        self.assertEqual(_status(found, "source_released"), "available")
        self.assertEqual(found["level_hint"], 0)
        self.assertEqual(assess_trl(doc, [], None)["level"], 4)

    def test_artifacts_need_an_experiment(self):
        text = (CORPUS / "released_toolkit.txt").read_text(encoding="utf-8")
        text = text.replace("We evaluate on a benchmark. Our model outperforms the baseline.", "")
        trl = assess_trl(ingest_text(text, "noexp.txt"), [], None)
        self.assertLessEqual(trl["level"], 2)
        self.assertIn("without an experimental evaluation", trl["note"])

    def test_artifacts_alone_never_exceed_trl_6(self):
        text = (CORPUS / "released_toolkit.txt").read_text(encoding="utf-8")
        self.assertLessEqual(assess_trl(ingest_text(text, "kit.txt"), [], None)["level"], 6)

    def test_page_is_where_the_sentence_is_not_where_the_section_starts(self):
        page1 = "Toy\n\nAbstract\nWe propose a method.\n\n1. Method\nWe design a small model."
        page2 = "More method text about the model.\n\nOur code is available at https://github.com/lab/proj."
        doc = build_document("two.txt", [page1, page2], source="text")
        item = next(i for i in collect_artifacts(doc)["classes"] if i["key"] == "source_released")
        self.assertEqual(item["status"], "available")
        self.assertEqual(item["page"], 2)


if __name__ == "__main__":
    unittest.main()
