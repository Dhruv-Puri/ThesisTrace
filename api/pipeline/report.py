"""Stage 11 - executive report.

The baseline report is assembled deterministically from the structured analysis;
no model is needed.  Every factual bullet carries a page citation.  When Gemini is
enabled, it may rewrite the "not proven" and "risks" sections, but the output is
filtered mechanically: a sentence without a valid [p.N] citation is dropped.

Syllabus: natural language generation, grounded generation (CO5), graceful
degradation (CO6), and hallucination control (CO4).
"""

from __future__ import annotations

import json
import re
from collections import Counter

from .. import prompts
from . import config, llm
from .ingest import Document
from .textutils import citation_pages, clip

_HEADING_RE = re.compile(r"(?m)^##\s+(.+?)\s*$")


def _clean(text: str, limit: int = 420) -> str:
    return clip(re.sub(r"\s+", " ", text or "").strip(), limit)


def _evidence_page(claim: dict) -> int:
    evidence = claim.get("evidence") or []
    if evidence:
        return int(evidence[0].get("page", claim.get("page", 1)))
    return int(claim.get("page", 1))


def _claim_bullet(claim: dict) -> str:
    text = _clean(claim.get("text", ""), 420)
    if text and text[-1] not in ".!?":
        text += "."
    return f"{text} [p.{_evidence_page(claim)}]"


def _missing_repro(reproducibility: dict) -> list[dict]:
    return [
        item for item in reproducibility.get("items", [])
        if item.get("status") != "yes"
    ]


def _build_lists(
    document: Document,
    stats: dict,
    summary: dict,
    key_concepts: dict,
    claims: list[dict],
    reproducibility: dict,
    trl: dict,
) -> dict:
    supported = [claim for claim in claims if claim.get("verdict") == "supported"]
    partial = [claim for claim in claims if claim.get("verdict") == "partially_supported"]
    insufficient = [claim for claim in claims if claim.get("verdict") == "insufficient"]

    concepts = []
    for group in ("datasets", "models", "metrics"):
        concepts.extend(item["name"] for item in key_concepts.get(group, [])[:2])
    concept_text = ", ".join(concepts) if concepts else "no scientific entities were found"

    trl_page = trl["evidence"][-1]["page"] if trl.get("evidence") else 1
    achieved = [
        f"Reports {stats.get('words', 0):,} words across {stats.get('sections', 0)} "
        f"detected sections; estimated reading time {stats.get('reading_minutes', 0)} min [p.1].",
        f"Key concepts extracted from the text include {concept_text}."
        + (f" [p.{key_concepts['datasets'][0]['pages'][0]}]" if key_concepts.get("datasets") else ""),
        f"{len(supported)} of {len(claims)} extracted claims cleared the evidence threshold; "
        f"{len(partial)} were partially supported and {len(insufficient)} remained unverified.",
        f"Reproducibility audit scored {reproducibility.get('score', 0)}/100 "
        f"({reproducibility.get('summary', 'no signals')}).",
        f"Readiness assessment: TRL {trl.get('level', 1)}/9 - {trl.get('label', '')} [p.{trl_page}].",
    ]

    proven = [_claim_bullet(claim) for claim in supported[:5]]
    not_proven = []
    for claim in (partial + insufficient)[:6]:
        note = _clean(claim.get("note", ""), 220)
        bullet = _claim_bullet(claim)
        if note:
            bullet += f" {note}"
        not_proven.append(bullet)

    risks: list[str] = []
    for item in _missing_repro(reproducibility)[:5]:
        if item.get("status") == "partial":
            risks.append(f"{item['name']} is only partially documented, which limits independent verification.")
        else:
            risks.append(f"{item['name']} is not reported in the extracted text, so independent reproduction is harder.")
    if partial:
        risks.append(
            f"{len(partial)} claim(s) are only partially supported; their wording is broader "
            "than the retrieved evidence."
        )
    if trl.get("level", 1) < 7:
        risks.append(
            f"Readiness stops at TRL {trl.get('level', 1)}; no field or operational "
            "evidence was found in the paper."
        )
    if reproducibility.get("score", 100) < 50:
        risks.append(
            f"The overall reproducibility score is {reproducibility.get('score', 0)}/100, "
            "so reported results should be treated as provisional."
        )
    if not risks:
        risks.append("No major textual risks were detected; this is not a guarantee of correctness.")

    next_steps: list[str] = []
    missing_keys = {item["key"] for item in _missing_repro(reproducibility)}
    if "dataset_available" in missing_keys or "code_available" in missing_keys:
        next_steps.append("Release the dataset and source code to enable independent reproduction.")
    if "hyperparameters" in missing_keys or "random_seed" in missing_keys:
        next_steps.append("Report full hyperparameters and random seeds so results can be repeated.")
    if "baseline" in missing_keys:
        next_steps.append("Add a comparison against a clear baseline to establish the claimed gain.")
    if "metrics" in missing_keys:
        next_steps.append("Report standard evaluation metrics with values and confidence intervals.")
    if trl.get("level", 1) < 7:
        next_steps.append(
            f"Run a field/pilot evaluation to move beyond TRL {trl.get('level', 1)}."
        )
    for claim in partial[:2]:
        next_steps.append(
            f"Clarify the scope of the partially supported claim with a direct experiment "
            f"[p.{_evidence_page(claim)}]."
        )
    if not next_steps:
        next_steps.append("Repeat the analysis after the evidence package is strengthened.")

    return {
        "achieved": achieved,
        "proven": proven,
        "not_proven": not_proven,
        "risks": risks,
        "next_steps": next_steps[:6],
    }


def render_markdown(
    document: Document,
    stats: dict,
    summary: dict,
    key_concepts: dict,
    claims: list[dict],
    reproducibility: dict,
    trl: dict,
    lists: dict,
) -> str:
    supported = sum(1 for claim in claims if claim.get("verdict") == "supported")
    partial = sum(1 for claim in claims if claim.get("verdict") == "partially_supported")
    insufficient = sum(1 for claim in claims if claim.get("verdict") == "insufficient")
    methods = Counter(
        (claim.get("audit") or {}).get("method") or claim.get("source") or "unknown"
        for claim in claims
    )
    receipt_line = ", ".join(f"{count} {method}" for method, count in sorted(methods.items()))

    def bullets(items: list[str], empty: str) -> str:
        return "\n".join(f"- {item}" for item in items) if items else f"- {empty}"

    concept_lines = []
    for group, label in (("datasets", "Datasets"), ("models", "Models & methods"), ("metrics", "Metrics")):
        names = [item["name"] for item in key_concepts.get(group, [])[:5]]
        if names:
            concept_lines.append(f"- {label}: {', '.join(names)}")

    markdown = f"""# Executive Report - {document.title}

**Source:** `{document.filename}` - {len(document.pages)} pages - about {stats.get('reading_minutes', 0)} min read
**Readiness:** TRL {trl.get('level', 1)}/9 - {trl.get('label', '')}
**Reproducibility:** {reproducibility.get('score', 0)}/100 - {reproducibility.get('summary', '')}
**Claim check:** {supported} supported - {partial} partial - {insufficient} insufficient

## 1. What the paper achieved
{bullets(lists['achieved'], 'No summary could be produced.')}

## 2. What is proven
{bullets(lists['proven'], 'No extracted claim cleared the evidence threshold. Treat the paper as promising but unverified.')}

## 3. What is not proven
{bullets(lists['not_proven'], 'No partially supported or unverified claims were extracted.')}

## 4. Main risks
{bullets(lists['risks'], 'No major textual risks were detected.')}

## 5. Recommended next steps
{bullets(lists['next_steps'], 'No next steps were generated.')}

## Appendix - at a glance
{chr(10).join(concept_lines) if concept_lines else '- No scientific entities were extracted.'}
- Technical-term density: {stats.get('technical_term_density', 0)}
- Complexity score: {stats.get('complexity_score', 0)}/10
- Reproducibility note: {reproducibility.get('note', '')}
- TRL note: {trl.get('note', '')}
- Verdict receipts: {receipt_line or 'none'}; every verdict stores retrieval scores, NLI probabilities, thresholds and the pipeline version.

_Generated by ThesisTrace. Every verdict is based on retrieved passages from this document; the language model never assigns verdicts._
"""
    return markdown


def enforce_citations(text: str, valid_pages: set[int]) -> tuple[str, int]:
    """Drop non-heading lines that lack a valid [p.N] citation."""
    kept: list[str] = []
    dropped = 0
    in_code = False
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            kept.append(line)
            continue
        if in_code or not stripped:
            kept.append(line)
            continue
        if stripped.startswith("#") or stripped.startswith("---") or stripped.startswith("|"):
            kept.append(line)
            continue
        pages = citation_pages(line)
        if pages and all(page in valid_pages for page in pages):
            kept.append(line)
        else:
            dropped += 1
    return "\n".join(kept).strip(), dropped


def _parse_sections(markdown: str) -> dict[str, str]:
    matches = list(_HEADING_RE.finditer(markdown or ""))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        sections[match.group(1).strip().lower()] = markdown[start:end].strip()
    return sections


def polish_markdown(
    markdown: str,
    analysis_payload: dict,
    valid_pages: set[int],
) -> tuple[str, list[str]]:
    """Optional grounded rewrite of the not-proven / risks sections."""
    warnings: list[str] = []
    if not (config.LLM_REPORT_ENABLED and llm.enabled()):
        return markdown, warnings
    template = prompts.render(
        "report",
        analysis_json=json.dumps(analysis_payload, indent=2)[: config.MAX_CONTEXT_CHARS],
    )
    try:
        raw = llm.generate(
            template["user"], system=template["system"], max_tokens=900, temperature=0.2
        )
    except llm.LLMError as exc:
        warnings.append(f"Gemini report polish skipped ({exc.message}); template report used.")
        return markdown, warnings

    filtered, dropped = enforce_citations(raw, valid_pages)
    if dropped:
        warnings.append(
            f"{dropped} uncited line(s) were removed from the Gemini report polish (CO4 check)."
        )
    if not filtered.strip():
        warnings.append("Gemini report polish produced no cited text; template report used.")
        return markdown, warnings

    polished = _parse_sections(filtered)
    replacements: dict[str, str] = {}
    for title, content in polished.items():
        if "not" in title and "proven" in title:
            replacements["3. what is not proven"] = content
        elif "risk" in title:
            replacements["4. main risks"] = content
    if not replacements:
        warnings.append("Gemini report polish did not match the expected sections; template report used.")
        return markdown, warnings

    result = markdown
    for target, content in replacements.items():
        matches = list(_HEADING_RE.finditer(result))
        for index, match in enumerate(matches):
            if not match.group(1).strip().lower().startswith(target.split(".", 1)[0] + "."):
                continue
            end = matches[index + 1].start() if index + 1 < len(matches) else len(result)
            result = result[:match.end()] + "\n\n" + content.strip() + "\n\n" + result[end:]
            break
    return result, warnings


def build_report(
    document: Document,
    stats: dict,
    summary: dict,
    key_concepts: dict,
    claims: list[dict],
    reproducibility: dict,
    trl: dict,
    analysis_payload: dict | None = None,
) -> tuple[dict, list[str]]:
    warnings: list[str] = []
    lists = _build_lists(document, stats, summary, key_concepts, claims, reproducibility, trl)
    markdown = render_markdown(
        document, stats, summary, key_concepts, claims, reproducibility, trl, lists
    )
    if analysis_payload is not None:
        markdown, polish_warnings = polish_markdown(
            markdown, analysis_payload, {page.number for page in document.pages}
        )
        warnings.extend(polish_warnings)
    return {**lists, "markdown": markdown}, warnings
