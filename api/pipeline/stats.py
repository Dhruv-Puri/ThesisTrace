"""Stage 3a - document statistics and the complexity score.

Classical NLP features only: token counts, sentence length, technical-term density,
reference density and (when spaCy is available) part-of-speech mix.  The score is a
transparent weighted blend, never a black box - every component is returned so the
UI can show a radar chart and a judge can audit it.
"""

from __future__ import annotations

from .ingest import Document, norm_heading
from .textutils import word_tokens

_WEIGHTS = {
    "term_density": 0.30,
    "sentence_length": 0.20,
    "pos_mix": 0.10,
    "references": 0.15,
    "structure": 0.10,
    "lexical_variety": 0.15,
}


def _clamp(value: float, low: float = 0.0, high: float = 10.0) -> float:
    return max(low, min(high, value))


def compute_stats(
    doc: Document,
    sentences: list[dict],
    technical_term_hits: int = 0,
    pos: dict | None = None,
) -> dict:
    text = doc.full_text
    tokens = word_tokens(text)
    words = len(tokens)
    unique_words = len({token.lower() for token in tokens}) if tokens else 0
    avg_sentence = (words / len(sentences)) if sentences else 0.0

    content_sections = [
        section
        for section in doc.sections
        if norm_heading(section.heading) not in {"references", "bibliography", "appendix"}
    ]
    references = int(doc.meta.get("references", 0))
    figures = int(doc.meta.get("figures", 0))
    tables = int(doc.meta.get("tables", 0))

    term_density = technical_term_hits / words if words else 0.0
    type_token_ratio = unique_words / words if words else 0.0

    pos = pos or {}
    noun = float(pos.get("noun_ratio", 0.30))
    adj = float(pos.get("adj_ratio", 0.06))
    pos_mix_raw = noun + adj
    pos_mix = _clamp((pos_mix_raw - 0.20) / 0.035) if pos.get("available") else 5.0

    parts = {
        "term_density": round(_clamp(term_density * 70), 1),
        "sentence_length": round(_clamp((avg_sentence - 8) / 2.6), 1),
        "pos_mix": round(pos_mix, 1),
        "references": round(_clamp(references / 3.5), 1),
        "structure": round(_clamp(len(content_sections) * 1.1), 1),
        "lexical_variety": round(_clamp(type_token_ratio * 22), 1),
    }
    complexity = sum(parts[key] * weight for key, weight in _WEIGHTS.items())

    return {
        "words": words,
        "unique_words": unique_words,
        "reading_minutes": max(1, round(words / 220)) if words else 0,
        "sections": len(content_sections),
        "references": references,
        "figures": figures,
        "tables": tables,
        "technical_term_density": round(term_density, 3),
        "avg_sentence_length": round(avg_sentence, 1),
        "complexity_score": round(complexity, 1),
        "complexity_parts": parts,
        "pos": {
            "available": bool(pos.get("available")),
            "noun_ratio": round(noun, 3),
            "verb_ratio": round(float(pos.get("verb_ratio", 0.16)), 3),
            "adj_ratio": round(adj, 3),
        },
    }
