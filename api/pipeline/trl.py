"""Stage 10 - Technology Readiness Level (TRL 1-9) with cited evidence.

A deterministic rubric over signals the paper actually states.  The model never
invents a TRL: each level requires a matched phrase in a named section, and the
evidence list carries the page.  Reviews/surveys are capped because TRL is about a
specific technology, not a literature overview.

This is a differentiator for the project, not a syllabus task per se - but it is a
concrete demonstration of semantic analysis + evidence-grounded generation.
"""

from __future__ import annotations

import re

from .ingest import Document, abstract_text, norm_heading
from .textutils import normalize_ws, split_sentences

LABELS = {
    1: "Basic principles observed",
    2: "Technology concept formulated",
    3: "Experimental proof of concept",
    4: "Technology validated in lab",
    5: "Technology validated in relevant environment",
    6: "Technology demonstrated in relevant environment",
    7: "System prototype demonstrated in operational environment",
    8: "System complete and qualified",
    9: "Actual system proven in operational environment",
}

_GROUPS = {
    "problem": ("abstract", "introduction", "background", "motivation"),
    "method": ("abstract", "introduction", "method", "methods", "methodology", "approach"),
    "experiment": ("results", "experiments", "experiment", "evaluation", "analysis"),
    "baseline": ("results", "experiments", "experiment", "evaluation", "discussion"),
    "relevant": ("results", "experiments", "experiment", "evaluation", "discussion", "conclusion"),
    "field": ("results", "experiments", "experiment", "evaluation", "discussion", "conclusion"),
    "operational": ("results", "experiments", "evaluation", "discussion", "conclusion"),
    "certified": ("results", "evaluation", "discussion", "conclusion"),
    "proven": ("results", "evaluation", "discussion", "conclusion"),
}

_PATTERNS = {
    "problem": [
        r"\b(?:challenge|problem|limitation|need|gap)\b",
        r"\bwe (?:address|study|investigate|tackle)\b",
    ],
    "method": [
        r"\bwe (?:propose|present|introduce|develop|design|build)\b",
        r"\b(?:architecture|framework|algorithm|pipeline|prototype)\b",
    ],
    "experiment": [
        r"\b(?:experiment|experiments|evaluation|benchmark|we evaluate)\b",
        r"\bresults? (?:show|demonstrate|indicate)\b",
    ],
    "baseline": [
        r"\bbaseline\b", r"state[- ]of[- ]the[- ]art",
        r"compared (?:with|to)", r"\boutperform", r"improvement over",
    ],
    "relevant": [
        r"\breal[- ]world\b", r"\blarge[- ]scale\b", r"\bindustrial\b",
        r"\bprototype\b", r"\bpilot (?:study|test|deployment)\b",
        r"\bfield (?:test|study|trial)\b", r"\bclinical\b",
    ],
    "field": [
        r"\bfield (?:test|trial|study)\b", r"\bpilot (?:study|test|deployment)\b",
        r"\bin collaboration with\b", r"\bclinical trial\b",
        r"\btested (?:at|in) (?:a|the) (?:hospital|factory|site)\b",
    ],
    "operational": [
        r"\b(?:in|into) (?:production|operation)\b", r"\bdeployed (?:at|in|to)\b",
        r"\blive deployment\b", r"\boperational (?:environment|deployment)\b",
    ],
    "certified": [
        r"\bcertified\b", r"\bqualification\b", r"\bregulatory approval\b",
        r"\bstandard compliance\b", r"\bTRL 8\b",
    ],
    "proven": [
        r"\bproven in operation\b", r"\bused in production\b", r"\bmillions of users\b",
        r"\bin service since\b", r"\boperational deployment\b",
    ],
}

_LEVEL_SIGNAL = {
    1: "problem", 2: "method", 3: "experiment", 4: "baseline", 5: "relevant",
    6: "field", 7: "operational", 8: "certified", 9: "proven",
}

_SIGNAL_PHRASE = {
    "problem": "problem/motivation",
    "method": "method description",
    "experiment": "experimental evaluation",
    "baseline": "baseline comparison",
    "relevant": "relevant/real-world environment",
    "field": "field/pilot evidence",
    "operational": "operational-environment evidence",
    "certified": "certification/qualification evidence",
    "proven": "proven-in-operation evidence",
}

# A negated sentence is not evidence for a positive TRL signal.  "No field trial
# was conducted" must not be read as a field trial.
_NEGATION = re.compile(
    r"\b(?:no|not|never|without|neither|nor|future|will|would|could|plan|planned|"
    r"intend|intended)\b",
    re.IGNORECASE,
)


def _sections(doc: Document, names: tuple[str, ...]) -> list:
    picked = [
        section for section in doc.sections
        if any(name in norm_heading(section.heading) for name in names)
    ]
    return picked or doc.sections


def _search(doc: Document, key: str) -> dict | None:
    for section in _sections(doc, _GROUPS[key]):
        for sentence in split_sentences(section.text):
            if _NEGATION.search(sentence):
                continue
            for pattern in _PATTERNS[key]:
                if re.search(pattern, sentence, re.IGNORECASE):
                    return {"page": section.page, "quote": normalize_ws(sentence)[:240]}
    return None


def _is_review(doc: Document) -> bool:
    haystack = f"{doc.title}\n{abstract_text(doc)[:800]}"
    return bool(re.search(r"\b(?:survey|systematic review|meta[- ]analysis|literature review)\b", haystack, re.I))


def assess_trl(doc: Document, claims: list[dict], reproducibility: dict | None = None) -> dict:
    findings = {key: _search(doc, key) for key in _PATTERNS}
    review = _is_review(doc)

    level = 1
    if findings["method"]:
        level = 2
    if findings["experiment"] and findings["method"]:
        level = 3
    if findings["baseline"] and findings["experiment"]:
        level = 4
    if findings["relevant"] and findings["baseline"]:
        level = 5
    if findings["field"] and findings["relevant"]:
        level = 6
    if findings["operational"]:
        level = 7
    if findings["certified"] and findings["operational"]:
        level = 8
    if findings["proven"] and findings["operational"]:
        level = 9

    cap_reasons: list[str] = []
    if level >= 7 and not findings["experiment"]:
        level = 2
        cap_reasons.append("Operational wording without an experimental evaluation is not enough for TRL 7.")
    elif level >= 4 and not findings["baseline"]:
        level = 3
        cap_reasons.append("No baseline comparison was found.")
    elif level >= 5 and not findings["relevant"]:
        level = 4
        cap_reasons.append("No relevant/real-world environment evidence was found.")
    elif level >= 6 and not findings["field"]:
        level = 5
        cap_reasons.append("No field/pilot evidence was found.")

    if review:
        level = min(level, 3)
        cap_reasons.append("The document looks like a review/survey, so TRL is capped at 3.")

    next_signal = _LEVEL_SIGNAL.get(level + 1)
    if cap_reasons:
        cap_reason = " ".join(cap_reasons)
    elif next_signal and not findings.get(next_signal):
        cap_reason = f"No {_SIGNAL_PHRASE.get(next_signal, next_signal)} was found for the next level."
    else:
        cap_reason = "No cap applied; the next level lacked textual evidence."

    evidence: list[dict] = []
    for candidate_level in range(1, level + 1):
        key = _LEVEL_SIGNAL[candidate_level]
        finding = findings.get(key)
        if finding:
            evidence.append(
                {
                    "signal": key,
                    "level": candidate_level,
                    "page": finding["page"],
                    "quote": finding["quote"],
                }
            )

    supported = sum(1 for claim in claims if claim.get("verdict") == "supported")
    total = len(claims)
    explanation = (
        f"Level {level} ({LABELS[level]}) is the highest readiness level supported by "
        f"the paper's own wording."
    )
    if evidence:
        explanation += " Evidence: " + "; ".join(
            f"{item['signal']} [p.{item['page']}]" for item in evidence
        ) + "."
    if cap_reason:
        explanation += " " + cap_reason
    if total:
        explanation += (
            f" Of {total} extracted claims, {supported} cleared the evidence threshold; "
            "the rest should be read as unverified, not proven false."
        )
    if reproducibility and reproducibility.get("score", 100) < 50:
        explanation += (
            " Reproducibility is low, so the readiness level should be treated as "
            "indicative until the missing details are published."
        )

    return {
        "level": level,
        "label": LABELS[level],
        "evidence": evidence,
        "why": explanation,
        "signals": {key: bool(value) for key, value in findings.items()},
        "review_document": review,
        "note": cap_reason,
    }
