"""Small, dependency-free text utilities used across the pipeline.

CSR322 tie-in: sentence segmentation, tokenisation and normalisation are the
*Word Level* / preprocessing topics.  Everything here is plain Python so the
pipeline can be unit-tested without installing a model.
"""

from __future__ import annotations

import re
import unicodedata

# Characters that must never be sent to a model or rendered in the UI.
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WS_RE = re.compile(r"\s+")
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9'\-]*")
_NUM_RE = re.compile(r"(?<![A-Za-z0-9-])\d+(?:[.,]\d+)*(?:\s*[%％])?")
_CITATION_RE = re.compile(r"\[p\.(\d+)\]")
_PROTECT = "\u2024"  # temporary stand-in for a period inside an abbreviation

_ABBREVIATIONS = [
    "e.g.", "i.e.", "et al.", "fig.", "figs.", "eq.", "eqs.", "dr.", "prof.",
    "vs.", "approx.", "no.", "mr.", "mrs.", "ms.", "sec.", "ref.", "refs.",
    "al.", "cf.", "resp.", "incl.", "max.", "min.", "std.", "tab.",
]

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "also", "am",
    "an", "and", "any", "are", "as", "at", "be", "because", "been", "before",
    "being", "below", "between", "both", "but", "by", "can", "could", "did",
    "do", "does", "doing", "down", "during", "each", "few", "for", "from",
    "further", "had", "has", "have", "having", "he", "her", "here", "hers",
    "herself", "him", "himself", "his", "how", "however", "i", "if", "in",
    "into", "is", "it", "its", "itself", "just", "may", "me", "might", "more",
    "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on",
    "once", "only", "or", "other", "our", "ours", "ourselves", "out", "over",
    "own", "same", "she", "should", "so", "some", "such", "than", "that",
    "the", "their", "theirs", "them", "themselves", "then", "there", "these",
    "they", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "we", "were", "what", "when", "where", "which", "while",
    "who", "whom", "why", "will", "with", "would", "you", "your", "yours",
    "yourself", "yourselves", "using", "used", "use", "based", "et", "al",
    "one", "two", "three", "first", "second", "new", "study", "paper",
    "results", "result", "show", "shows", "shown", "propose", "proposed",
}


def normalize_ws(text: str) -> str:
    """Collapse every whitespace run (including newlines) to one space."""
    return _WS_RE.sub(" ", text or "").strip()


def strip_control_chars(text: str) -> str:
    return _CONTROL_RE.sub("", text or "")


def split_sentences(text: str) -> list[str]:
    """Deterministic sentence splitter that survives scientific writing.

    Protects common abbreviations (``et al.``, ``e.g.``), decimals (``95.5``) and
    author initials before splitting on sentence-final punctuation.
    """
    if not text:
        return []

    text = normalize_ws(strip_control_chars(text))
    if not text:
        return []

    protected = text
    for abbr in sorted(_ABBREVIATIONS, key=len, reverse=True):
        pattern = re.compile(r"(?i)(?<![A-Za-z])" + re.escape(abbr))
        protected = pattern.sub(lambda m: m.group(0)[:-1] + _PROTECT, protected)
    protected = re.sub(r"(\d)\.(?=\d)", rf"\1{_PROTECT}", protected)
    protected = re.sub(r"\b([A-Z])\.(?=\s+[A-Z][a-z])", rf"\1{_PROTECT}", protected)

    parts = re.split(r"(?<=[.!?])\s+(?=[\"'(\[]?[A-Z0-9])", protected)
    sentences: list[str] = []
    for part in parts:
        sentence = part.replace(_PROTECT, ".").strip()
        if sentence and re.search(r"[A-Za-z0-9]", sentence):
            sentences.append(sentence)
    return sentences


def normalize_for_match(text: str) -> str:
    """Case/quote/dash-insensitive form used for verbatim checks."""
    text = unicodedata.normalize("NFKC", text or "")
    text = (
        text.replace("\u2018", "'").replace("\u2019", "'")
        .replace("\u201c", '"').replace("\u201d", '"')
        .replace("\u2013", "-").replace("\u2014", "-")
        .replace("\u00ad", "")
    )
    return normalize_ws(text).lower()


def is_verbatim(fragment: str, document: str, min_chars: int = 12) -> bool:
    """True when *fragment* occurs in *document* (normalised, ignoring case)."""
    frag = normalize_for_match(fragment)
    if len(frag) < min_chars:
        return False
    return frag in normalize_for_match(document)


def word_tokens(text: str) -> list[str]:
    return _WORD_RE.findall(text or "")


def content_tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in word_tokens(text)
        if len(token) > 2 and token.lower() not in STOPWORDS
    }


def jaccard(a: str, b: str) -> float:
    left, right = content_tokens(a), content_tokens(b)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def numbers_in(text: str) -> list[str]:
    """Numeric tokens with thousands separators and percent spacing normalised."""
    values: list[str] = []
    for match in _NUM_RE.finditer(text or ""):
        token = match.group(0).replace(" ", "").replace("％", "%")
        token = re.sub(r"(?<=\d),(?=\d{3}(?:\D|$))", "", token)
        values.append(token)
    return values


def citation(page: int | str) -> str:
    return f"[p.{int(page)}]"


def citation_pages(text: str) -> list[int]:
    return [int(value) for value in _CITATION_RE.findall(text or "")]


def clip(text: str, max_chars: int, marker: str = "…") -> str:
    """Word-boundary truncation (used before every model/LLM call)."""
    text = normalize_ws(text)
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    cut = text[: max_chars - len(marker)]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:") + marker


# ---------------------------------------------------------------------------
# Prompt-injection detection (CO4)
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ignore_previous", re.compile(r"\bignore\s+(?:all\s+|any\s+|the\s+)?(?:previous|prior|above|earlier)\s+(?:instructions?|prompts?|rules?|directions?)", re.I)),
    ("disregard_previous", re.compile(r"\bdisregard\s+(?:all\s+|any\s+|the\s+)?(?:previous|prior|above|earlier)\s+(?:instructions?|prompts?|rules?)", re.I)),
    ("role_override", re.compile(r"\byou\s+are\s+now\b|\bfrom\s+now\s+on\s+you\b", re.I)),
    ("fake_system_tag", re.compile(r"<\s*/?\s*system\s*>|\[\s*/?\s*(?:INST|SYS)\s*\]|^\s*system\s*:", re.I)),
    ("new_instructions", re.compile(r"\bnew\s+instructions?\s*:", re.I)),
    ("verdict_injection", re.compile(r"\bmark\s+(?:this|the)\s+claim\s+as\b|\breturn\s+(?:the\s+)?(?:answer|verdict)\s+as\b|\boverride\s+(?:the|your)\s+(?:instructions?|verdict)\b", re.I)),
    ("role_play", re.compile(r"\bact\s+as\s+(?:an?|the)\s+(?:assistant|ai|model|system|expert)\b", re.I)),
    ("do_not_follow", re.compile(r"\bdo\s+not\s+(?:follow|obey)\b", re.I)),
    ("prompt_injection", re.compile(r"\bprompt\s+injection\b|\bjailbreak\b", re.I)),
]


def detect_instruction_lines(text: str) -> list[dict]:
    """Return instruction-like lines found in untrusted document text.

    The uploaded paper is data, never a source of instructions.  We detect hostile
    lines so they can be (a) reported in ``warnings`` and (b) removed from any
    context sent to an LLM.  Verdicts never depend on prompts, so even an
    undetected injection cannot change a claim's verdict.
    """
    findings: list[dict] = []
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        for name, pattern in _INJECTION_PATTERNS:
            if pattern.search(line):
                findings.append({"pattern": name, "line": clip(line, 240)})
                break
    return findings


def sanitize_untrusted(text: str, max_chars: int = 12_000) -> tuple[str, int]:
    """Strip hostile instruction lines and clip text before prompt insertion.

    Returns ``(clean_text, removed_line_count)``.  The caller still wraps the
    result in delimiters and tells the model that the block is *data*.
    """
    kept: list[str] = []
    removed = 0
    for line in (text or "").splitlines():
        if detect_instruction_lines(line):
            removed += 1
            continue
        kept.append(strip_control_chars(line))
    return clip("\n".join(kept), max_chars), removed
