"""Multi-paper readiness portfolio.

This is deliberately a *screening* view, not a literature assistant: every paper keeps
its own audit, and only two things are compared across papers:

1. the readiness dimensions (TRL, reproducibility, artifacts, claim support), and
2. near-duplicate claims that the papers make about the same thing, scored with the
   same NLI cross-encoder used by ClaimCheck (both directions).

There is no cross-paper question answering here.  Breadth is added only where a
readiness decision actually needs it.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import PIPELINE_VERSION, config, models
from .classical import TfidfIndex
from .evidence import _nli_scores
from .textutils import clip

SIMILARITY_FLOOR = 0.45
MAX_LEDGER = 12
_ID_RE = re.compile(r"^[a-f0-9]{32}$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _claim_counts(claims: list[dict]) -> dict:
    total = len(claims)
    supported = sum(1 for claim in claims if claim.get("verdict") == "supported")
    partial = sum(1 for claim in claims if claim.get("verdict") == "partially_supported")
    insufficient = sum(1 for claim in claims if claim.get("verdict") == "insufficient")
    return {
        "total": total,
        "supported": supported,
        "partial": partial,
        "insufficient": insufficient,
        "support_rate": round(supported / total, 2) if total else 0.0,
    }


def _row(analysis: dict) -> dict:
    doc = analysis.get("doc") or {}
    trl = analysis.get("trl") or {}
    repro = analysis.get("reproducibility") or {}
    claims = analysis.get("claims") or []
    items = repro.get("items") or []
    artifacts = trl.get("artifacts") or {}
    missing = [item.get("name") for item in items if item.get("status") == "no"]
    partial = [item.get("name") for item in items if item.get("status") == "partial"]
    methods: dict[str, int] = {}
    for claim in claims:
        method = (claim.get("audit") or {}).get("method") or claim.get("source") or "unknown"
        methods[method] = methods.get(method, 0) + 1

    return {
        "job_id": analysis.get("job_id"),
        "title": doc.get("title") or doc.get("filename") or "Untitled paper",
        "filename": doc.get("filename") or "",
        "pages": int(doc.get("pages") or 0),
        "trl": {
            "level": trl.get("level"),
            "label": trl.get("label") or "",
            "confidence": trl.get("confidence") or "",
            "range": trl.get("level_range") or [],
            "cap_reason": trl.get("cap_reason") or "",
        },
        "reproducibility": {
            "score": repro.get("score"),
            "present": sum(1 for item in items if item.get("status") == "yes"),
            "partial": len(partial),
            "missing": len(missing),
        },
        "claims": _claim_counts(claims),
        "artifacts": {
            "available": list(artifacts.get("available") or []),
            "promised": list(artifacts.get("promised") or []),
        },
        "gaps": (missing + partial)[:4],
        "audit_methods": methods,
    }


def _stance(pipe, left: str, right: str) -> tuple[str, dict]:
    """Compare two claims about the same thing, in both directions."""
    if pipe is None:
        return "unscored", {}

    forward = _nli_scores(pipe, left, right)
    backward = _nli_scores(pipe, right, left)
    entailment = max(forward["entailment"], backward["entailment"])
    contradiction = max(forward["contradiction"], backward["contradiction"])

    if contradiction >= config.CONTRADICTION_SCORE and contradiction > entailment:
        stance = "conflict"
    elif (
        forward["entailment"] >= config.PARTIAL_ENTAILMENT
        and backward["entailment"] >= config.PARTIAL_ENTAILMENT
    ):
        stance = "agree"
    else:
        stance = "insufficient"

    return stance, {
        "forward": {key: round(float(value), 4) for key, value in forward.items()},
        "backward": {key: round(float(value), 4) for key, value in backward.items()},
    }


def build_portfolio(
    analyses: list[dict], *, name: str | None = None, use_nli: bool = True
) -> dict:
    """Build the readiness table and disagreement ledger from finished analyses."""
    cleaned: list[dict] = []
    seen: set[str] = set()
    for analysis in analyses:
        job_id = str(analysis.get("job_id") or "")
        if not job_id or job_id in seen:
            continue
        seen.add(job_id)
        cleaned.append(analysis)

    if len(cleaned) < 2:
        raise ValueError("A portfolio needs at least two finished analyses.")
    if len(cleaned) > config.MAX_PORTFOLIO_PAPERS:
        raise ValueError(
            f"A portfolio compares at most {config.MAX_PORTFOLIO_PAPERS} papers."
        )

    rows = [_row(analysis) for analysis in cleaned]

    entries: list[dict] = []
    for row, analysis in zip(rows, cleaned):
        for claim in analysis.get("claims") or []:
            text = str(claim.get("text") or "").strip()
            if not text:
                continue
            entries.append(
                {
                    "job_id": row["job_id"],
                    "title": row["title"],
                    "claim_id": claim.get("id"),
                    "text": text,
                    "page": int(claim.get("page") or 1),
                    "verdict": claim.get("verdict"),
                }
            )

    index = TfidfIndex([entry["text"] for entry in entries]) if entries else None
    pipe = models.get_pipeline("text-classification", config.NLI_MODEL) if use_nli else None

    ledger: list[dict] = []
    if index is not None:
        for left_index, left in enumerate(entries):
            scores = index.scores(left["text"])
            for right_index in range(left_index + 1, len(entries)):
                right = entries[right_index]
                if left["job_id"] == right["job_id"]:
                    continue
                similarity = float(scores[right_index]) if right_index < len(scores) else 0.0
                if similarity < SIMILARITY_FLOOR:
                    continue
                stance, nli = _stance(pipe, left["text"], right["text"])
                ledger.append(
                    {
                        "a": {
                            "job_id": left["job_id"],
                            "title": left["title"],
                            "claim_id": left["claim_id"],
                            "page": left["page"],
                            "verdict": left["verdict"],
                            "text": clip(left["text"], 300),
                        },
                        "b": {
                            "job_id": right["job_id"],
                            "title": right["title"],
                            "claim_id": right["claim_id"],
                            "page": right["page"],
                            "verdict": right["verdict"],
                            "text": clip(right["text"], 300),
                        },
                        "similarity": round(similarity, 3),
                        "stance": stance,
                        "nli": nli,
                    }
                )

    ledger.sort(key=lambda item: item["similarity"], reverse=True)
    ledger = ledger[:MAX_LEDGER]

    conflicts = sum(1 for item in ledger if item["stance"] == "conflict")
    agreements = sum(1 for item in ledger if item["stance"] == "agree")
    insufficient = sum(1 for item in ledger if item["stance"] == "insufficient")
    unscored = sum(1 for item in ledger if item["stance"] == "unscored")

    if conflicts:
        headline = f"{conflicts} shared claim{'s' if conflicts != 1 else ''} disagree across these papers."
    elif agreements:
        headline = f"{agreements} shared claim{'s' if agreements != 1 else ''} agree across these papers."
    else:
        headline = "No shared claims were found across these papers."

    return {
        "name": name or "",
        "papers": rows,
        "ledger": ledger,
        "summary": {
            "papers": len(rows),
            "claims": len(entries),
            "shared": len(ledger),
            "conflicts": conflicts,
            "agreements": agreements,
            "insufficient": insufficient,
            "unscored": unscored,
            "headline": headline,
            "nli_model": config.NLI_MODEL if pipe is not None else None,
            "similarity_floor": SIMILARITY_FLOOR,
        },
    }


def create(
    analyses: list[dict],
    *,
    name: str | None = None,
    directory: Path | str | None = None,
    use_nli: bool = True,
) -> dict:
    """Build a portfolio and persist it inside the project data directory."""
    payload = build_portfolio(analyses, name=name, use_nli=use_nli)
    portfolio_id = uuid.uuid4().hex
    payload.update(
        {
            "portfolio_id": portfolio_id,
            "created_at": _now(),
            "pipeline_version": PIPELINE_VERSION,
        }
    )

    target = Path(directory or config.PORTFOLIO_DIR)
    target.mkdir(parents=True, exist_ok=True)
    temporary = target / f"{portfolio_id}.tmp"
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(target / f"{portfolio_id}.json")
    return payload


def load(portfolio_id: str, directory: Path | str | None = None) -> dict | None:
    if not _ID_RE.fullmatch(str(portfolio_id or "")):
        return None
    target = Path(directory or config.PORTFOLIO_DIR) / f"{portfolio_id}.json"
    if not target.is_file():
        return None
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
