import unittest
from types import SimpleNamespace
from unittest.mock import patch

from api.pipeline.portfolio import build_portfolio


def _analysis(job_id: str, title: str, trl_level: int, claims: list[dict]) -> dict:
    return {
        "job_id": job_id,
        "doc": {"title": title, "filename": f"{job_id}.pdf", "pages": 9},
        "claims": claims,
        "trl": {
            "level": trl_level,
            "label": "validated",
            "confidence": "medium",
            "level_range": [trl_level, trl_level],
            "artifacts": {"available": ["source_release"], "promised": ["container"]},
        },
        "reproducibility": {
            "score": 60,
            "items": [
                {"name": "Dataset availability", "status": "yes"},
                {"name": "Random seed", "status": "no"},
                {"name": "Hyperparameters", "status": "partial"},
            ],
        },
    }


def _claim(claim_id: str, text: str, verdict: str) -> dict:
    return {
        "id": claim_id,
        "text": text,
        "page": 4,
        "verdict": verdict,
        "confidence": 0.8,
        "source": "nli",
        "audit": {"method": "nli"},
        "evidence": [{"page": 5, "sentence_id": 10, "text": "support", "relevance": 0.6}],
    }


class PortfolioTests(unittest.TestCase):
    def test_readiness_table_and_shared_claims(self):
        left = _analysis(
            "a" * 32,
            "Paper A",
            5,
            [_claim("c1", "The method reduces latency by 42% on WMT14.", "supported")],
        )
        right = _analysis(
            "b" * 32,
            "Paper B",
            3,
            [_claim("c1", "The method reduces latency by 42% on WMT14.", "supported")],
        )

        with patch("api.pipeline.portfolio.models.get_pipeline", return_value=None):
            result = build_portfolio([left, right], use_nli=False)

        self.assertEqual(result["summary"]["papers"], 2)
        self.assertEqual(result["summary"]["claims"], 2)
        self.assertEqual(len(result["papers"]), 2)
        self.assertEqual(result["papers"][0]["trl"]["level"], 5)
        self.assertEqual(result["papers"][1]["reproducibility"]["missing"], 1)
        self.assertEqual(result["papers"][0]["gaps"][0], "Random seed")
        self.assertEqual(result["ledger"][0]["stance"], "unscored")
        self.assertGreaterEqual(result["ledger"][0]["similarity"], 0.45)

    def test_conflicting_shared_claims_are_flagged(self):
        left = _analysis(
            "c" * 32,
            "Paper C",
            4,
            [_claim("c1", "Our model improves accuracy by 12% on the benchmark.", "supported")],
        )
        right = _analysis(
            "d" * 32,
            "Paper D",
            4,
            [_claim("c1", "Our model improves accuracy by 12% on the benchmark.", "supported")],
        )

        class ContradictingPipe:
            model = SimpleNamespace(config=SimpleNamespace(id2label={}))

            def __call__(self, inputs, **kwargs):
                return [
                    {"label": "contradiction", "score": 0.91},
                    {"label": "entailment", "score": 0.04},
                    {"label": "neutral", "score": 0.05},
                ]

        with patch(
            "api.pipeline.portfolio.models.get_pipeline",
            return_value=ContradictingPipe(),
        ):
            result = build_portfolio([left, right], use_nli=True)

        self.assertEqual(result["ledger"][0]["stance"], "conflict")
        self.assertEqual(result["summary"]["conflicts"], 1)
        self.assertIn("disagree", result["summary"]["headline"])

    def test_a_portfolio_needs_two_distinct_papers(self):
        one = _analysis("e" * 32, "Only paper", 4, [])
        with self.assertRaises(ValueError):
            build_portfolio([one, one], use_nli=False)


if __name__ == "__main__":
    unittest.main()
