"""Research gap analysis based on paper text, claims, and reproducibility."""

import re



AUTHOR_GAP_PATTERNS = [
    r"\b(future work|future research|further research|further work)\b",
    r"\b(remains to be explored|remains unexplored|not yet explored)\b",
    r"\b(limitation|limitations|drawback|drawbacks)\b",
    r"\b(out of scope|beyond the scope|left for future)\b",
    r"\b(further investigation|additional investigation)\b",
]

GAP_SECTION_NAMES = {
    "limitation",
    "limitations",
    "future work",
    "future research",
    "discussion",
    "conclusion",
}


def _split_sentences(text):
    """Split text into simple sentence-like passages."""
    if not text:
        return []

    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text)
        if len(sentence.strip()) >= 25
    ]


def _get_author_reported_gaps(document):
    """Extract limitations and future-work statements explicitly in the paper."""
    gaps = []
    seen = set()

    for section in getattr(document, "sections", []):
        heading = getattr(section, "heading", "") or ""
        normalized_heading = re.sub(r"^\d+[\.\s]*", "", heading.lower()).strip()

        for sentence in _split_sentences(getattr(section, "text", "")):
            matches = [
                pattern
                for pattern in AUTHOR_GAP_PATTERNS
                if re.search(pattern, sentence, re.IGNORECASE)
            ]

            if not matches:
                continue

            key = sentence.lower()
            if key in seen:
                continue
            seen.add(key)

            gaps.append({
                "category": "author_reported",
                "title": "Author-reported limitation or future direction",
                "description": sentence,
                "source": "paper_text",
                "section": heading or "Unknown",
                "page": getattr(section, "page", None),
                "confidence": "high",
            })

    return gaps


def _get_methodological_gaps(reproducibility):
    """Identify methodological details not clearly reported in the paper."""
    if not isinstance(reproducibility, dict):
        return []

    signals = reproducibility.get("signals", [])
    if not isinstance(signals, list):
        return []

    gaps = []

    for signal in signals:
        if not isinstance(signal, dict):
            continue

        status = str(signal.get("status", "")).lower()
        if status not in {"no", "partial"}:
            continue

        name = signal.get("name", signal.get("key", "Research detail"))
        evidence = signal.get("evidence", "")

        if status == "no":
            description = (
                f"The paper does not clearly report {name.lower()}."
            )
        else:
            description = (
                f"The reporting of {name.lower()} appears incomplete."
            )

        if evidence:
            description += f" Audit note: {evidence}"

        gaps.append({
            "category": "methodological",
            "title": f"Potential methodological gap: {name}",
            "description": description,
            "source": "reproducibility_audit",
            "section": None,
            "page": None,
            "confidence": "medium",
            "signal": signal.get("key"),
            "status": status,
        })

    return gaps


def _get_evidence_gaps(verified_claims):
    """Identify claims whose supporting evidence is limited or insufficient."""
    if not isinstance(verified_claims, list):
        return []

    gaps = []

    for claim in verified_claims:
        if not isinstance(claim, dict):
            continue

        verdict = str(claim.get("verdict", "")).lower()

        if verdict not in {"insufficient", "partially_supported"}:
            continue

        claim_text = claim.get("text", "")
        if not claim_text:
            continue

        if verdict == "insufficient":
            title = "Claim with insufficient supporting evidence"
            description = (
                "The analysis did not identify sufficient supporting "
                "evidence for this claim in the paper."
            )
            confidence = "medium"
        else:
            title = "Claim with partially supported evidence"
            description = (
                "The identified evidence provides only partial support "
                "for this claim."
            )
            confidence = "medium"

        gaps.append({
            "category": "evidence",
            "title": title,
            "description": description,
            "claim": claim_text,
            "source": "claim_verification",
            "section": claim.get("section"),
            "page": claim.get("page"),
            "confidence": confidence,
            "claim_id": claim.get("id"),
            "verdict": verdict,
            "evidence": claim.get("evidence", []),
        })

    return gaps


def analyze_research_gaps(document, verified_claims, reproducibility):
    """
    Analyze a paper for author-reported, methodological, and evidence gaps.

    This is a document-level analysis. It does not establish that a gap is
    novel across the wider research literature.
    """
    gaps = []

    gaps.extend(_get_author_reported_gaps(document))
    gaps.extend(_get_methodological_gaps(reproducibility))
    gaps.extend(_get_evidence_gaps(verified_claims))

    counts = {
        "author_reported": 0,
        "methodological": 0,
        "evidence": 0,
    }

    for gap in gaps:
        counts[gap["category"]] += 1

    return {
        "total_gaps": len(gaps),
        "category_counts": counts,
        "gaps": gaps,
        "limitations": [
            "Findings are based only on the analyzed paper.",
            "Missing methodological details are potential reporting gaps, not proof of flawed research.",
            "Insufficient evidence does not mean a claim is false.",
            "Novelty across the wider research literature has not been established.",
        ],
    }
