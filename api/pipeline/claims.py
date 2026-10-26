"""Stage 6 - claim extraction (Practical 3 / Practical 5).

Primary path: few-shot instruction prompt (Gemini when a key exists).
Baseline path: a transparent heuristic over result-like sentences.
Every proposed claim is checked verbatim against the document - a claim that is not
in the source is rejected before the UI sees it.

Syllabus: text classification and generation; prompting (zero/few-shot, CO2/CO3);
Practical 3 (zero/few-shot classification) and Practical 5 (prompt-based vs
classical baseline).
"""

from __future__ import annotations

import json
import re

from .. import prompts
from . import config, llm
from .ingest import Document, abstract_text, conclusion_text, results_text, norm_heading
from .textutils import (
    clip, is_verbatim, jaccard, normalize_for_match, numbers_in, sanitize_untrusted,
)

_SECTION_PRIORITY = (
    ("abstract", 4.0),
    ("conclusion", 3.6),
    ("result", 3.2),
    ("experiment", 3.0),
    ("evaluation", 3.0),
    ("discussion", 2.6),
    ("introduction", 1.6),
    ("method", 1.2),
)

_EXCLUDED_SECTIONS = re.compile(
    r"(reference|bibliograph|acknowledg|appendix|supplementary|future work)", re.I
)
_BACKGROUND = re.compile(
    r"^(?:recent|prior|previous|earlier|existing|state-of-the-art)\b|"
    r"\b(?:has|have)\s+(?:emerged|shown|demonstrated)\b",
    re.I,
)
_WEAK_START = re.compile(r"^(?:however|although|we believe|we hope|future|limitation)", re.I)
_SUBJECT_VERB = re.compile(
    r"\b(?:we|our|this (?:paper|study|work|method|approach|system)|"
    r"the (?:proposed|presented|new) (?:method|model|approach|framework))\b"
    r"[^.]{0,100}\b(?:show|shows|demonstrate|demonstrates|find|finds|achieve|achieves|"
    r"outperform|outperforms|improve|improves|reduce|reduces|increase|increases|"
    r"enable|enables|predict|predicts|report|reports|confirm|confirms|suggest|suggests|"
    r"provide|provides)\b",
    re.I,
)
_RESULT_VERB = re.compile(
    r"\b(?:reduces?|improves?|outperforms?|achieves?|enables?|demonstrates?|shows?|"
    r"reports?|increases?|decreases?|cuts?|boosts?|yields?|attains?|maintains?)\b",
    re.I,
)
_COMPARATIVE = re.compile(
    r"\b(?:than|compared (?:with|to)|outperform|better|higher|lower|faster|slower|"
    r"reduc(?:e|es|ed|tion)|increas(?:e|es|ed)|improve(?:s|d)?)\b",
    re.I,
)
_FIGURE_TABLE = re.compile(r"^(?:figure|fig\.?|table)\s+\d+", re.I)
_URL_ONLY = re.compile(r"^https?://\S+$")

_FEW_SHOT = """Example 1
Excerpt: "We evaluate on ImageNet. Our model reaches 78.4% top-1 accuracy, outperforming the strongest baseline by 2.1 points."
JSON: {"claims":[{"text":"Our model reaches 78.4% top-1 accuracy, outperforming the strongest baseline by 2.1 points.","type":"quantitative","section":"Results"}]}

Example 2
Excerpt: "These results suggest that sparse routing is a practical alternative to dense attention for long documents."
JSON: {"claims":[{"text":"These results suggest that sparse routing is a practical alternative to dense attention for long documents.","type":"qualitative","section":"Conclusion"}]}"""


def _priority(section: str) -> float:
    heading = norm_heading(section or "")
    for needle, value in _SECTION_PRIORITY:
        if needle in heading:
            return value
    return 0.0


def _claim_type(text: str) -> str:
    if numbers_in(text) or re.search(r"\d", text):
        return "quantitative"
    if _COMPARATIVE.search(text):
        return "comparative"
    return "qualitative"


def _heuristic_claims(document: Document, sentences: list[dict]) -> list[dict]:
    candidates: list[tuple[float, dict]] = []
    for sentence in sentences:
        text = sentence["text"].strip()
        section = sentence.get("section", "")
        if len(text) < 30 or len(text) > 420:
            continue
        if _EXCLUDED_SECTIONS.search(section):
            continue
        if _FIGURE_TABLE.match(text) or _URL_ONLY.match(text):
            continue
        if text.endswith("?") or re.match(r"^\[\d+\]", text):
            continue
        if not re.search(r"[A-Za-z]", text):
            continue

        subject = bool(_SUBJECT_VERB.search(text))
        result = bool(_RESULT_VERB.search(text))
        numeric = bool(numbers_in(text))
        if not (subject or result or (numeric and _COMPARATIVE.search(text))):
            continue

        score = _priority(section)
        score += 2.0 if subject else 0.0
        score += 1.0 if result else 0.0
        score += 0.7 if numeric else 0.0
        if text.lower().startswith(("we ", "our ")):
            score += 0.4
        if _BACKGROUND.search(text):
            score -= 2.0
        if _WEAK_START.search(text):
            score -= 1.2
        if not (60 <= len(text) <= 300):
            score -= 0.4

        candidates.append(
            (
                score,
                {
                    "text": text,
                    "claim_type": _claim_type(text),
                    "section": section or "Body",
                    "page": int(sentence["page"]),
                    "sentence_id": int(sentence["id"]),
                    "extraction": "heuristic",
                },
            )
        )

    candidates.sort(key=lambda item: (-item[0], item[1]["sentence_id"]))
    claims: list[dict] = []
    for _, claim in candidates:
        if any(jaccard(claim["text"], existing["text"]) > 0.75 for existing in claims):
            continue
        claims.append(claim)
        if len(claims) >= config.MAX_CLAIMS:
            break
    return _assign_ids(claims)


def _assign_ids(claims: list[dict]) -> list[dict]:
    for index, claim in enumerate(claims, start=1):
        claim["id"] = f"c{index}"
    return claims


def _match_sentence(claim_text: str, sentences: list[dict]) -> dict | None:
    needle = normalize_for_match(claim_text)
    best: dict | None = None
    for sentence in sentences:
        haystack = normalize_for_match(sentence["text"])
        if needle in haystack or (len(haystack) > 20 and haystack in needle):
            if best is None or len(sentence["text"]) < len(best["text"]):
                best = sentence
    return best


def _locate_page(document: Document, claim_text: str) -> int:
    needle = normalize_for_match(claim_text)
    for page in document.pages:
        if needle in normalize_for_match(page.text):
            return page.number
    return 1


def _parse_json_object(text: str) -> dict | None:
    value = (text or "").strip()
    value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.I)
    value = re.sub(r"\s*```$", "", value)
    start = value.find("{")
    end = value.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(value[start:end + 1])
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _llm_claims(
    document: Document, sentences: list[dict]
) -> tuple[list[dict], list[str]]:
    warnings: list[str] = []
    context_parts = []
    for label, text in (
        ("ABSTRACT", abstract_text(document)),
        ("RESULTS", results_text(document)),
        ("CONCLUSION", conclusion_text(document)),
    ):
        if text:
            context_parts.append(f"{label}\n{text}")
    context = clip("\n\n".join(context_parts), config.MAX_CONTEXT_CHARS)
    clean_context, removed = sanitize_untrusted(context, config.MAX_CONTEXT_CHARS)
    if removed:
        warnings.append(
            f"{removed} instruction-like line(s) were removed from the claim-extraction "
            "context (prompt-injection defense)."
        )

    template = prompts.render(
        "claims", examples_block=_FEW_SHOT, context=clean_context
    )
    try:
        raw = llm.generate(
            template["user"],
            system=template["system"],
            max_tokens=900,
            temperature=0.1,
        )
    except llm.LLMError as exc:
        warnings.append(
            f"Gemini claim extraction unavailable ({exc.message}); heuristic fallback used."
        )
        return [], warnings

    parsed = _parse_json_object(raw)
    items = parsed.get("claims") if parsed else None
    if not isinstance(items, list):
        warnings.append("Gemini returned invalid claim JSON; heuristic fallback used.")
        return [], warnings

    claims: list[dict] = []
    rejected = 0
    for item in items:
        if not isinstance(item, dict):
            rejected += 1
            continue
        text = str(item.get("text", "")).strip().strip('"“”')
        claim_type = str(item.get("type", "qualitative")).lower()
        if claim_type not in {"quantitative", "qualitative", "comparative"}:
            claim_type = _claim_type(text)
        if not (20 <= len(text) <= 600) or not is_verbatim(text, document.full_text, 20):
            rejected += 1
            continue
        sentence = _match_sentence(text, sentences)
        claims.append(
            {
                "text": text,
                "claim_type": claim_type,
                "section": (sentence or {}).get("section") or str(item.get("section") or "Body"),
                "page": int((sentence or {}).get("page") or _locate_page(document, text)),
                "sentence_id": (sentence or {}).get("id"),
                "extraction": "llm",
            }
        )
        if len(claims) >= config.MAX_CLAIMS:
            break

    if rejected:
        warnings.append(
            f"{rejected} LLM claim(s) failed the verbatim/format check and were rejected "
            "(hallucination guard, CO4)."
        )
    if not claims:
        warnings.append("Gemini produced no verifiable claims; heuristic fallback used.")
        return [], warnings
    return _assign_ids(claims), warnings


def extract_claims(
    document: Document,
    sentences: list[dict],
    use_llm: bool | None = None,
) -> tuple[list[dict], list[str]]:
    """Return ``(claims, warnings)``; always returns a usable list."""
    warnings: list[str] = []
    if use_llm is None:
        use_llm = config.LLM_CLAIMS_ENABLED and llm.enabled()

    if use_llm:
        claims, llm_warnings = _llm_claims(document, sentences)
        warnings.extend(llm_warnings)
        if claims:
            return claims, warnings

    claims = _heuristic_claims(document, sentences)
    if not claims:
        warnings.append(
            "No result-like claim sentences were detected; ClaimCheck will be empty. "
            "The document may be a review, a dataset paper, or mostly background."
        )
    return claims, warnings
