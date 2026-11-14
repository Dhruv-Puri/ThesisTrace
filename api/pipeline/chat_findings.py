"""Pipeline outputs as citable chat context ("findings").

The Ask tab used to answer only from retrieved paper sentences, so "is the main claim
supported?" or "why is this TRL 4?" made Gemini re-derive things the pipeline had
already checked.  Now each pipeline output (claim verdicts with their evidence, the TRL
result, the reproducibility checklist, extracted datasets/metrics, the summary, caveats)
becomes a short *finding* with an id (``F1``, ``F2`` ...).  The model is told to relay
findings as given - it never assigns or changes a verdict, TRL or score - and to cite
them as ``[F3]`` next to the usual ``[p.N]`` page tags.  Findings the model cites that
were not in its context are removed afterwards, exactly like invented pages.

Findings contain text copied from the uploaded paper (claims, evidence quotes), so any
finding with an instruction-like line is dropped before it can reach a prompt.
"""

from __future__ import annotations

import re
from typing import Any

from . import config
from .textutils import clip, detect_instruction_lines, normalize_ws, strip_control_chars

MAX_FINDING_CHARS = 700
MAX_CLAIM_FINDINGS = 10

# Question wording that should pull a whole family of findings into the prompt even
# when the TF-IDF overlap is small ("Is it ready for production?" has no word in common
# with the TRL finding).
_ROUTES: list[tuple[str, re.Pattern[str]]] = [
    ("trl", re.compile(
        r"\b(trl|readiness|ready|maturity|mature|deploy\w*|production|pilot|prototype|"
        r"commerciali[sz]\w*|field|operational|artifacts?)\b", re.I)),
    ("repro", re.compile(
        r"\b(reproduc\w*|replicat\w*|seeds?|hyper-?param\w*|code|github|open[- ]source|"
        r"checklist|install\w*|docker|licen[cs]e|split|environment)\b", re.I)),
    ("claim", re.compile(
        r"\b(claims?|claimed|support\w*|prov(?:e|es|en|ed)|verif\w*|verdicts?|valid\w*|"
        r"evidence|insufficient|contradict\w*|trust\w*|reliable|credible)\b", re.I)),
    ("concepts", re.compile(
        r"\b(datasets?|models?|metrics?|benchmarks?|algorithms?|baselines?|measured|score)\b", re.I)),
    ("summary", re.compile(
        r"\b(summar\w*|overview|tl;?dr|contribution|about|main idea|what (?:is|does) (?:this|the) paper)\b", re.I)),
]
_BASELINE_KINDS = {"summary", "doc"}


def _clean(value: Any) -> str:
    return normalize_ws(strip_control_chars(str(value if value is not None else "")))


def _pages(*values: Any) -> list[int]:
    found: set[int] = set()
    for value in values:
        if isinstance(value, (list, tuple, set)):
            found.update(_pages(*value))
        elif isinstance(value, str):
            found.update(int(match) for match in re.findall(r"p\.(\d+)", value))
        else:
            try:
                page = int(value)
            except (TypeError, ValueError):
                continue
            if page > 0:
                found.add(page)
    return sorted(found)


def _finding(kind: str, label: str, text: str, pages: list[int]) -> dict[str, Any]:
    return {"kind": kind, "label": label, "text": clip(_clean(text), MAX_FINDING_CHARS), "pages": pages}


def _quote(text: Any, width: int = 150) -> str:
    return f"\u201c{clip(_clean(text), width)}\u201d"


def build_findings(analysis: dict | None) -> list[dict[str, Any]]:
    """Turn a finished analysis into ordered, citable findings (ids ``F1``..)."""
    if not isinstance(analysis, dict):
        return []
    raw: list[dict[str, Any]] = []

    doc = analysis.get("doc") or {}
    stats = analysis.get("stats") or {}
    if doc:
        text = (
            f"Document: {_quote(doc.get('title') or doc.get('filename'), 120)}, {doc.get('pages', '?')} page(s), "
            f"about {stats.get('words', '?')} words, {stats.get('sections', '?')} detected sections, "
            f"{stats.get('references', '?')} references."
        )
        if doc.get("truncated"):
            text += (
                f" Only the first {doc.get('pages')} of {doc.get('page_count_total')} pages were analysed."
            )
        raw.append(_finding("doc", "Document", text, []))

    bullets = (analysis.get("summary") or {}).get("bullets") or []
    if bullets:
        raw.append(_finding(
            "summary", "Pipeline summary",
            "Summary produced by the pipeline: " + " ".join(f"({i}) {clip(_clean(b), 230)}" for i, b in enumerate(bullets[:4], 1)),
            [],
        ))

    trl = analysis.get("trl") or {}
    if trl.get("level"):
        range_ = trl.get("level_range") or []
        extra = ""
        if trl.get("confidence"):
            extra += f" Confidence: {trl['confidence']}."
        if len(range_) == 2 and range_[0] != range_[1]:
            extra += f" Plausible range: TRL {range_[0]}-{range_[1]}."
        raw.append(_finding(
            "trl", "TRL rubric",
            f"Technology readiness: TRL {trl['level']}/9 ({trl.get('label', '')}).{extra} {trl.get('why', '')}",
            _pages(trl.get("evidence", []) and [e.get("page") for e in trl["evidence"]], trl.get("why", "")),
        ))
        evidence = trl.get("evidence") or []
        if evidence:
            lines = "; ".join(
                f"{e.get('signal', 'signal')} (level {e.get('level', '?')}, p.{e.get('page', '?')}) {_quote(e.get('quote'), 110)}"
                for e in evidence[:6]
            )
            raw.append(_finding(
                "trl", "TRL evidence", "Quotes the TRL rubric used as evidence: " + lines,
                _pages([e.get("page") for e in evidence]),
            ))
        near = trl.get("near_misses") or []
        if near:
            lines = "; ".join(
                f"{n.get('signal', '')} (p.{n.get('page', '?')}, ignored because {n.get('reason', 'not evidence')}) "
                f"{_quote(n.get('quote'), 100)}"
                for n in near[:3]
            )
            raw.append(_finding(
                "trl", "TRL near misses",
                "Statements the rubric saw but did not count as evidence for a higher level: " + lines,
                _pages([n.get("page") for n in near]),
            ))
        artifacts = trl.get("artifacts") or {}
        if artifacts:
            got = ", ".join(artifacts.get("available") or []) or "none"
            promised = ", ".join(artifacts.get("promised") or [])
            raw.append(_finding(
                "trl", "Software artifacts",
                f"Software artifacts the paper states it ships: {got}."
                + (f" Promised but not counted: {promised}." if promised else "")
                + f" {artifacts.get('note', '')}",
                _pages([c.get("page") for c in artifacts.get("classes", []) if c.get("status") == "available"]),
            ))

    claims = analysis.get("claims") or []
    if claims:
        counts: dict[str, int] = {}
        for claim in claims:
            counts[str(claim.get("verdict", "unknown"))] = counts.get(str(claim.get("verdict", "unknown")), 0) + 1
        tally = ", ".join(f"{n} {verdict}" for verdict, n in sorted(counts.items()))
        raw.append(_finding(
            "claim", "Claim check summary",
            f"Claim check: {len(claims)} claims extracted - {tally}. A verdict of 'insufficient' means the "
            "retrieved text did not support the claim; it does not mean the claim is false.",
            [],
        ))
        for claim in claims[:MAX_CLAIM_FINDINGS]:
            evidence = claim.get("evidence") or []
            ev_text = " ".join(
                f"Evidence p.{e.get('page', '?')}: {_quote(e.get('text'), 140)}"
                + (f" [{e.get('nli')} {e.get('nli_score')}]" if e.get("nli") else "")
                for e in evidence[:2]
            ) or "No supporting passage was retrieved."
            confidence = claim.get("confidence")
            raw.append(_finding(
                "claim", f"Claim {claim.get('id', '')}".strip(),
                f"Claim {claim.get('id', '')} ({claim.get('claim_type', 'claim')}, p.{claim.get('page', '?')}): "
                f"{_quote(claim.get('text'), 170)} Pipeline verdict: {claim.get('verdict', 'unknown')}"
                + (f" (confidence {float(confidence):.2f})" if isinstance(confidence, (int, float)) else "")
                + f". {ev_text} {_clean(claim.get('note'))}",
                _pages(claim.get("page"), [e.get("page") for e in evidence[:2]]),
            ))

    repro = analysis.get("reproducibility") or {}
    if repro.get("items"):
        raw.append(_finding(
            "repro", "Reproducibility audit",
            f"Reproducibility audit (text-level, no code executed): score {repro.get('score', '?')}/100 - "
            f"{repro.get('summary', '')}",
            [],
        ))
        for item in repro["items"]:
            raw.append(_finding(
                "repro", f"Reproducibility: {item.get('name', '')}",
                f"Reproducibility check '{item.get('name', '')}': {item.get('status', '?')}. "
                f"{_clean(item.get('evidence'))}",
                _pages(item.get("evidence")),
            ))

    concepts = analysis.get("key_concepts") or {}
    if isinstance(concepts, dict):
        for group, items in concepts.items():
            if not items:
                continue
            names = ", ".join(
                f"{_clean(i.get('name'))}" + (f" (p.{','.join(str(p) for p in i.get('pages', [])[:3])})" if i.get("pages") else "")
                for i in items[:10]
            )
            raw.append(_finding(
                "concepts", f"Extracted {group}", f"Extracted {group} (named-entity pass): {names}.",
                _pages([i.get("pages") for i in items[:10]]),
            ))

    signals = analysis.get("signals") or {}
    parts = []
    if signals.get("metric_mentions"):
        parts.append("Metric values: " + "; ".join(
            f"{m.get('metric')} = {m.get('value')} (p.{m.get('page')})" for m in signals["metric_mentions"][:8]))
    if signals.get("p_values"):
        parts.append("Statistical tests: " + "; ".join(
            f"{p.get('value')} (p.{p.get('page')})" for p in signals["p_values"][:5]))
    if signals.get("percentages"):
        parts.append("Percentages: " + "; ".join(
            f"{p.get('value')} (p.{p.get('page')}) {_quote(p.get('context'), 70)}" for p in signals["percentages"][:5]))
    if signals.get("links"):
        parts.append("Links: " + "; ".join(f"{l.get('url')} (p.{l.get('page')})" for l in signals["links"][:5]))
    if parts:
        raw.append(_finding(
            "concepts", "Numbers and links", "Numbers and links extracted by regex: " + " | ".join(parts),
            _pages([m.get("page") for key in ("metric_mentions", "p_values", "percentages", "links")
                    for m in signals.get(key, [])]),
        ))

    warnings = [w for w in (analysis.get("warnings") or []) if isinstance(w, str)]
    if warnings:
        raw.append(_finding("caveats", "Analysis caveats", "Caveats from the analysis run: " + " ".join(warnings), []))

    findings: list[dict[str, Any]] = []
    for item in raw:
        if not item["text"] or detect_instruction_lines(item["text"]):
            continue  # never put hostile paper text into a prompt
        item["id"] = f"F{len(findings) + 1}"
        findings.append(item)
    return findings


def _route(query: str) -> set[str]:
    return {kind for kind, pattern in _ROUTES if pattern.search(query or "")}


def select_findings(findings: list[dict[str, Any]], query: str, budget_chars: int) -> list[dict[str, Any]]:
    """Pick the findings most relevant to the question, within ``budget_chars``."""
    if not findings or budget_chars <= 0:
        return []
    from .evidence import SentenceIndex  # local import: evidence pulls in the retrieval stack

    index = SentenceIndex([
        {"id": i, "text": f"{f['label']}. {f['text']}", "page": 0, "section": "findings"}
        for i, f in enumerate(findings)
    ])
    relevance = {int(hit["id"]): hit["relevance"] for hit in index.retrieve(query, k=len(findings))}
    routed = _route(query)
    # Claim-family routing also covers the aggregate; "concepts" covers entity + number findings.
    scored = []
    for i, finding in enumerate(findings):
        score = relevance.get(i, 0.0)
        if finding["kind"] in routed:
            score += 1.0
        elif finding["kind"] in _BASELINE_KINDS:
            score += 0.05
        if score > 0:
            scored.append((score, -i, i))
    scored.sort(reverse=True)

    chosen: list[int] = []
    budget = budget_chars
    for _, _, i in scored:
        cost = len(findings[i]["text"]) + len(findings[i]["label"]) + 12
        if cost > budget:
            continue
        budget -= cost
        chosen.append(i)
    return [{**findings[i], "relevance": round(relevance.get(i, 0.0), 3)} for i in sorted(chosen)]


def format_findings(selected: list[dict[str, Any]]) -> str:
    if not selected:
        return "(no pipeline findings were selected for this question)"
    return "\n".join(f"[{f['id']}] ({f['label']}) {f['text']}" for f in selected)


def findings_budget() -> int:
    """Share of the prompt budget reserved for pipeline findings (the rest is paper text)."""
    return int(config.MAX_CONTEXT_CHARS * 0.45)
