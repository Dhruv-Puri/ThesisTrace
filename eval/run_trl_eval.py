"""Evaluate TRL detection against human labels.

    python eval/run_trl_eval.py                 # regex rubric only
    python eval/run_trl_eval.py --nli           # plus NLI confirmation (needs models)
    python eval/run_trl_eval.py --manifest eval/gold/trl_gold.json --json

Metrics (TRL is ordinal, so plain accuracy is not enough):
  exact     prediction equals any rater's label
  within1   prediction is within +/-1 of any rater's label
  MAE       mean |prediction - mean(rater labels)|
Synthetic seed cases and real papers are reported separately.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.pipeline.ingest import ingest_file  # noqa: E402
from api.pipeline.trl import assess_trl  # noqa: E402

DEFAULT_MANIFEST = ROOT / "eval" / "gold" / "trl_gold.json"


def evaluate(manifest_path: Path = DEFAULT_MANIFEST, use_nli: bool = False) -> dict:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    rows = []
    for entry in manifest["papers"]:
        path = ROOT / entry["file"]
        document = ingest_file(path, path.name)
        result = assess_trl(document, [], None, use_nli=use_nli)
        labels = [int(value) for value in entry["human"]]
        predicted = int(result["level"])
        rows.append(
            {
                "file": entry["file"],
                "source": entry.get("source", "real"),
                "labels": labels,
                "predicted": predicted,
                "confidence": result["confidence"],
                "range": result["level_range"],
                "exact": predicted in labels,
                "within1": any(abs(predicted - value) <= 1 for value in labels),
                "abs_error": abs(predicted - sum(labels) / len(labels)),
            }
        )
    return {"rows": rows, "summary": {group: _summarise([r for r in rows if r["source"] == group])
                                       for group in sorted({r["source"] for r in rows})}}


def _summarise(rows: list[dict]) -> dict:
    n = len(rows)
    confusion = Counter((round(sum(r["labels"]) / len(r["labels"])), r["predicted"]) for r in rows)
    return {
        "n": n,
        "exact": round(sum(r["exact"] for r in rows) / n, 3) if n else None,
        "within1": round(sum(r["within1"] for r in rows) / n, 3) if n else None,
        "mae": round(sum(r["abs_error"] for r in rows) / n, 3) if n else None,
        "confusion": {f"human {h} -> predicted {p}": c for (h, p), c in sorted(confusion.items())},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--nli", action="store_true", help="confirm TRL 5+ evidence with the NLI model")
    parser.add_argument("--json", action="store_true", help="print raw JSON")
    args = parser.parse_args()
    report = evaluate(Path(args.manifest), use_nli=args.nli)
    if args.json:
        print(json.dumps(report, indent=2))
        return
    print("| file | source | human | predicted | confidence | range | within1 |")
    print("|---|---|---|---|---|---|---|")
    for row in report["rows"]:
        print(
            f"| {Path(row['file']).name} | {row['source']} | {row['labels']} | {row['predicted']} | "
            f"{row['confidence']} | {row['range'][0]}-{row['range'][1]} | {'yes' if row['within1'] else 'NO'} |"
        )
    print()
    for group, summary in report["summary"].items():
        print(f"{group}: N={summary['n']} exact={summary['exact']} within1={summary['within1']} MAE={summary['mae']}")
        for key, count in summary["confusion"].items():
            print(f"    {key}: {count}")


if __name__ == "__main__":
    main()
