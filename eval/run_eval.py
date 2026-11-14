"""Evaluate claim verification and retrieval on the hand-labelled seed set.

    python eval/run_eval.py
    python eval/run_eval.py --nli          # use the real cross-encoder (needs models)
    python eval/run_eval.py --analyze      # also time the full pipeline per paper
    python eval/run_eval.py --json

Metrics
  verdict accuracy, per-class precision/recall/F1, macro-F1
  retrieval recall@1/@3/@5 (only cases with a labelled evidence sentence)
  citation coverage (non-abstained verdicts that carry a page)
  mean verdict latency and, with --analyze, full-paper latency and an
  explicitly-assumed compute cost

The manifest is a SEED set labelled by the developer, not by two independent raters.
Report N with every number, and do not quote these as inter-annotator agreement.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.pipeline.analyze import analyze_document  # noqa: E402
from api.pipeline.evidence import SentenceIndex, verify_claims  # noqa: E402
from api.pipeline.ingest import build_sentence_index, ingest_file  # noqa: E402
from api.pipeline.textutils import normalize_for_match  # noqa: E402

DEFAULT_MANIFEST = ROOT / "eval" / "gold" / "claim_verdicts.json"
LABELS = ("supported", "partially_supported", "insufficient")
SHORT = {
    "supported": "supported",
    "partially_supported": "partial",
    "insufficient": "insufficient",
}


def _sentence_id(sentences: list[dict], needle: str | None) -> int | None:
    if not needle:
        return None
    target = normalize_for_match(needle)
    if not target:
        return None
    for sentence in sentences:
        if target in normalize_for_match(sentence["text"]):
            return int(sentence["id"])
    return None


def _prf(gold: list[str], predicted: list[str], label: str) -> dict:
    true_positive = sum(1 for g, p in zip(gold, predicted) if g == label and p == label)
    false_positive = sum(1 for g, p in zip(gold, predicted) if g != label and p == label)
    false_negative = sum(1 for g, p in zip(gold, predicted) if g == label and p != label)
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "support": sum(1 for g in gold if g == label),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
    }


def evaluate(manifest_path: Path = DEFAULT_MANIFEST, use_nli: bool = False) -> dict:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    rows = []
    for case in manifest["cases"]:
        path = ROOT / case["file"]
        document = ingest_file(path, path.name)
        sentences = build_sentence_index(document)
        source_id = _sentence_id(sentences, case.get("source"))
        expected_id = _sentence_id(sentences, case.get("evidence"))
        claim = {
            "id": case["id"],
            "text": case["claim"],
            "claim_type": "evaluation",
            "section": "",
            "page": 1,
            "sentence_id": source_id,
        }

        started = time.perf_counter()
        verified, _ = verify_claims([claim], sentences, use_nli=use_nli)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        result = verified[0]

        index = SentenceIndex(sentences)
        ranked = index.retrieve(
            claim["text"], k=5, exclude_ids={source_id} if source_id is not None else None
        )
        ranked_ids = [int(item["id"]) for item in ranked]
        hit_rank = (
            ranked_ids.index(expected_id) + 1
            if expected_id is not None and expected_id in ranked_ids
            else None
        )

        evidence = result.get("evidence") or []
        rows.append(
            {
                "id": case["id"],
                "file": Path(case["file"]).name,
                "claim": case["claim"],
                "gold": case["gold"],
                "predicted": result["verdict"],
                "method": (result.get("audit") or {}).get("method") or result.get("source"),
                "evidence_expected": expected_id is not None,
                "hit_rank": hit_rank,
                "recall": {
                    "at1": bool(hit_rank and hit_rank <= 1),
                    "at3": bool(hit_rank and hit_rank <= 3),
                    "at5": bool(hit_rank and hit_rank <= 5),
                },
                "citation": bool(evidence and all("page" in item for item in evidence)),
                "latency_ms": elapsed_ms,
            }
        )

    gold = [row["gold"] for row in rows]
    predicted = [row["predicted"] for row in rows]
    n = len(rows)
    correct = sum(1 for g, p in zip(gold, predicted) if g == p)

    per_class = {label: _prf(gold, predicted, label) for label in LABELS}
    macro_f1 = round(sum(per_class[label]["f1"] for label in LABELS) / len(LABELS), 3)

    with_evidence = [row for row in rows if row["evidence_expected"]]
    retrieval = {
        "n": len(with_evidence),
        **{
            key: (
                round(sum(1 for row in with_evidence if row["recall"][key]) / len(with_evidence), 3)
                if with_evidence
                else None
            )
            for key in ("at1", "at3", "at5")
        },
    }

    non_abstained = [row for row in rows if row["predicted"] != "insufficient"]
    coverage = (
        round(sum(1 for row in non_abstained if row["citation"]) / len(non_abstained), 3)
        if non_abstained
        else None
    )

    confusion = {
        f"gold {SHORT[g]} -> predicted {SHORT[p]}": sum(
            1 for gg, pp in zip(gold, predicted) if gg == g and pp == p
        )
        for g in LABELS
        for p in LABELS
    }
    confusion = {key: value for key, value in confusion.items() if value}

    return {
        "manifest": str(Path(manifest_path).relative_to(ROOT)).replace("\\", "/"),
        "mode": "nli" if use_nli else "lexical-fallback",
        "rows": rows,
        "summary": {
            "n": n,
            "accuracy": round(correct / n, 3) if n else None,
            "macro_f1": macro_f1,
            "per_class": per_class,
            "retrieval": retrieval,
            "citation_coverage": coverage,
            "latency_mean_ms": round(statistics.mean(row["latency_ms"] for row in rows), 1)
            if rows
            else None,
            "latency_max_ms": max((row["latency_ms"] for row in rows), default=None),
            "confusion": confusion,
        },
    }


def analyze_corpus(manifest_path: Path = DEFAULT_MANIFEST, rate: float = 0.05) -> dict:
    """Time the full pipeline once per distinct file (fallback tier unless models exist)."""
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    files = sorted({case["file"] for case in manifest["cases"]})
    rows = []
    tracemalloc.start()
    for relative in files:
        path = ROOT / relative
        started = time.perf_counter()
        result = analyze_document(path, path.name, use_nli=False)
        wall_ms = round((time.perf_counter() - started) * 1000, 1)
        rows.append(
            {
                "file": Path(relative).name,
                "pipeline_ms": int(result["timings"].get("total_ms", wall_ms)),
                "wall_ms": wall_ms,
                "claims": len(result.get("claims") or []),
                "trl": result.get("trl", {}).get("level"),
            }
        )
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    mean_ms = statistics.mean(row["pipeline_ms"] for row in rows) if rows else 0
    return {
        "n": len(rows),
        "rows": rows,
        "mean_pipeline_ms": round(mean_ms, 1),
        "peak_python_mb": round(peak / (1024 * 1024), 1),
        "assumed_rate_usd_per_cpu_hour": rate,
        "assumed_cost_per_paper_usd": round(mean_ms / 3_600_000 * rate, 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--nli", action="store_true", help="use the NLI cross-encoder")
    parser.add_argument("--analyze", action="store_true", help="also time the full pipeline")
    parser.add_argument("--rate", type=float, default=0.05, help="assumed USD per CPU-hour")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = evaluate(Path(args.manifest), use_nli=args.nli)
    if args.analyze:
        report["pipeline"] = analyze_corpus(Path(args.manifest), rate=args.rate)

    if args.json:
        print(json.dumps(report, indent=2))
        return

    summary = report["summary"]
    print(f"# ThesisTrace evaluation — {report['mode']}")
    print()
    print(f"Seed set: {report['manifest']} · N={summary['n']} · developer-labelled, not independent raters.")
    print()
    print("| case | gold | predicted | method | recall@5 |")
    print("|---|---|---|---|---|")
    for row in report["rows"]:
        recall = "—" if not row["evidence_expected"] else ("hit" if row["recall"]["at5"] else "miss")
        print(
            f"| {row['id']} | {SHORT[row['gold']]} | {SHORT[row['predicted']]} | "
            f"{row['method']} | {recall} |"
        )
    print()
    print(f"**Verdict accuracy:** {summary['accuracy']} (N={summary['n']}) · "
          f"**macro-F1:** {summary['macro_f1']}")
    print()
    print("| class | support | precision | recall | F1 |")
    print("|---|---|---|---|---|")
    for label in LABELS:
        metrics = summary["per_class"][label]
        print(
            f"| {SHORT[label]} | {metrics['support']} | {metrics['precision']} | "
            f"{metrics['recall']} | {metrics['f1']} |"
        )
    retrieval = summary["retrieval"]
    print()
    print(
        f"**Retrieval recall** (N={retrieval['n']}): "
        f"@1 {retrieval['at1']} · @3 {retrieval['at3']} · @5 {retrieval['at5']}"
    )
    print(f"**Citation coverage:** {summary['citation_coverage']} of non-abstained verdicts carry a page.")
    print(
        f"**Verdict latency:** mean {summary['latency_mean_ms']} ms · "
        f"max {summary['latency_max_ms']} ms"
    )
    if summary["confusion"]:
        print()
        print("Confusion:")
        for key, value in summary["confusion"].items():
            print(f"  {key}: {value}")

    if "pipeline" in report:
        pipeline = report["pipeline"]
        print()
        print(f"**Full pipeline** (N={pipeline['n']} papers, fallback tier):")
        print("| file | pipeline ms | claims | TRL |")
        print("|---|---|---|---|")
        for row in pipeline["rows"]:
            print(f"| {row['file']} | {row['pipeline_ms']} | {row['claims']} | {row['trl']} |")
        print()
        print(
            f"Mean {pipeline['mean_pipeline_ms']} ms/paper · peak Python allocation "
            f"{pipeline['peak_python_mb']} MB · assumed cost "
            f"${pipeline['assumed_cost_per_paper_usd']:.8f}/paper at "
            f"${pipeline['assumed_rate_usd_per_cpu_hour']}/CPU-hour (assumption, not a quote)."
        )

    print()
    print(
        "Caveats: seed labels only; lexical-fallback tier unless --nli ran with models; "
        "cost uses an assumed CPU rate."
    )


if __name__ == "__main__":
    main()
