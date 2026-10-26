import unittest

from api.pipeline.classical import (
    TfidfIndex,
    extract_key_terms,
    extract_regex_facts,
    pos_features,
)
from api.pipeline.ingest import build_sentence_index, ingest_text
from api.pipeline.stats import compute_stats
from api.tests.helpers import sample_document


class ClassicalTests(unittest.TestCase):
    def test_tfidf_ranks_relevant_sentence(self):
        index = TfidfIndex(
            [
                "The model reduces latency on the benchmark.",
                "We collected data from a hospital.",
                "Latency and the model are the topic of this result.",
            ]
        )
        scores = index.scores("latency model result")
        self.assertGreater(scores[0], scores[1])
        self.assertGreater(scores[2], scores[1])
        self.assertIn(index.backend, {"scikit-learn", "pure-python"})

    def test_key_terms_and_backend(self):
        terms, backend = extract_key_terms(sample_document(), 8)
        self.assertTrue(terms)
        self.assertIn("term", terms[0])
        self.assertIn(backend, {"scikit-learn", "pure-python"})

    def test_regex_facts(self):
        doc = ingest_text(
            "Results\n"
            "The model reaches 95.5% accuracy (p < 0.05) and improves BLEU by 2.1 points. "
            "Code is at https://github.com/example/repo.",
            "facts.txt",
        )
        facts = extract_regex_facts(doc)
        self.assertTrue(any(item["value"] == "95.5%" for item in facts["percentages"]))
        self.assertTrue(facts["p_values"])
        self.assertTrue(facts["metric_mentions"])
        self.assertTrue(facts["links"])
        self.assertEqual(facts["links"][0]["page"], 1)

    def test_stats_are_bounded_and_explainable(self):
        doc = sample_document()
        sentences = build_sentence_index(doc)
        stats = compute_stats(doc, sentences, technical_term_hits=12)
        self.assertGreater(stats["words"], 100)
        self.assertGreaterEqual(stats["complexity_score"], 0)
        self.assertLessEqual(stats["complexity_score"], 10)
        self.assertEqual(
            set(stats["complexity_parts"]),
            {"term_density", "sentence_length", "pos_mix", "references", "structure", "lexical_variety"},
        )
        self.assertIn("reading_minutes", stats)

    def test_pos_features_has_a_safe_fallback(self):
        features = pos_features([{"text": "The model reduces latency.", "page": 1, "id": 1, "section": "Body"}])
        self.assertIsInstance(features["available"], bool)
        self.assertIn("noun_ratio", features)
        self.assertGreaterEqual(features["noun_ratio"], 0)

    def test_empty_index_does_not_crash(self):
        index = TfidfIndex([])
        self.assertEqual(index.scores("anything"), [])
        self.assertEqual(index.top_terms(), [])


if __name__ == "__main__":
    unittest.main()
