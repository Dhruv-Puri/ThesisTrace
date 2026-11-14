"""Shared text-scoping helpers: section roles, page lookup, scoped negation/hedging.

Used by the TRL rubric (``trl.py``) and the software-readiness artifact detector
(``artifacts.py``) so both treat "related work", "future work" and references the
same way, and both judge negation/hedging only in the clause around a match.
"""

from __future__ import annotations

import re

from .ingest import Document, Page, norm_heading, _heading_match
from .textutils import normalize_for_match

# --------------------------------------------------------------------------- #
# Section roles
# --------------------------------------------------------------------------- #

# Order matters: the first matching rule wins.
ROLE_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("excluded", re.compile(
        r"\b(?:references?|bibliograph\w*|acknowledg\w*|funding|author contributions?|"
        r"conflicts? of interest|declarations?|ethics)\b")),
    ("related", re.compile(r"\b(?:related work|related studies|prior work|previous work|literature review)\b")),
    ("conclusion", re.compile(r"\b(?:conclusions?|concluding|summary)\b")),
    ("future", re.compile(r"\b(?:future work|limitations?|threats to validity)\b")),
    ("discussion", re.compile(r"\bdiscussion\b")),
    ("abstract", re.compile(r"\babstract\b")),
    ("intro", re.compile(r"\b(?:introduction|background|motivation|problem (?:statement|definition))\b")),
    ("results", re.compile(
        r"\b(?:results?|experiments?|experimental|evaluation|analysis|deployment|case stud\w+|"
        r"pilot|field|user stud\w+|performance|findings|ablations?|benchmarks?)\b")),
    ("method", re.compile(
        r"\b(?:methods?|methodology|approach|design|architecture|implementation|system|model|"
        r"framework|materials|setup)\b")),
]

ROLE_WEIGHT = {
    "results": 1.0, "method": 0.9, "abstract": 0.8, "discussion": 0.7,
    "other": 0.65, "front": 0.65, "conclusion": 0.6, "intro": 0.5,
    "future": 0.0, "related": 0.0, "excluded": 0.0,
}
CORE_ROLES = {"abstract", "intro", "method", "results", "discussion", "conclusion"}


def role_for_heading(heading: str) -> str:
    name = norm_heading(heading or "")
    for role, pattern in ROLE_RULES:
        if pattern.search(name):
            return role
    return "other"


def front_matter(doc: Document) -> str:
    """Page-1 text before the first recognised heading (title block, footnotes, links).

    Section detection drops everything before the first heading, but code/demo links
    are often stamped there, so artifact detection reads it separately.
    """
    if not doc.pages:
        return ""
    lines: list[str] = []
    for line in doc.pages[0].text.splitlines():
        if _heading_match(line):
            break
        lines.append(line)
    return "\n".join(lines).strip()


# --------------------------------------------------------------------------- #
# Page lookup
# --------------------------------------------------------------------------- #

class PageLocator:
    """Find the page a sentence is really on (a section's ``page`` is where it *starts*)."""

    def __init__(self, pages: list[Page]):
        self._pages = [(page.number, normalize_for_match(page.text)) for page in pages]

    def locate(self, sentence: str, default: int) -> int:
        key = normalize_for_match(sentence)
        if len(key) >= 12:
            for number, text in self._pages:
                if key in text:
                    return number
        return default


# --------------------------------------------------------------------------- #
# Scoped negation / hedging / attribution
# --------------------------------------------------------------------------- #

NEG = re.compile(
    r"\b(?:no|not|never|without|neither|nor|none|lacks?|lacking|lacked|absence of|yet to|"
    r"unable to|cannot|fails? to|failed to|rather than|instead of)\b|n't\b",
    re.IGNORECASE,
)
HEDGE = re.compile(
    r"\b(?:will|would|could|can|may|might|should|shall|plans?|planned|planning|intend(?:s|ed)?|"
    r"aims? to|aimed to|hopes? to|expects? to|expected to|future|potential(?:ly)?|possibl[ey]|"
    r"envision\w*|ideally|if|whether|suitable for|ready for|designed for|enabl\w+)\b",
    re.IGNORECASE,
)
CITES_OTHERS = re.compile(
    r"\[\s*\d[\d,\s\u2013-]*\]|\bet al\b|\(\s*[A-Z][A-Za-z-]+(?: et al\.?)?,?\s*(?:19|20)\d{2}\s*\)|"
    r"\b(?:prior|previous|existing|related|earlier|other) (?:work|systems?|studies|approaches|methods)\b|"
    r"\b(?:they|their) (?:deployed|tested|ran|conducted)\b",
    re.IGNORECASE,
)
OWN = re.compile(
    r"\b(?:we|our|ours|us)\b|"
    r"\b(?:this|the proposed|the presented|the developed|the) "
    r"(?:system|model|method|approach|tool|framework|prototype|pipeline|platform|device|algorithm|"
    r"solution|study|trial|deployment|work|toolkit|library|package|repository|code)\b|"
    r"\b(?:was|were|has been|have been|is|are) (?:successfully |also |then |later )?"
    r"(?:deployed|piloted|tested|evaluated|validated|trialled|trialed|installed|used|running|certified|"
    r"approved|rolled out|qualified|released|available|hosted|provided|included)\b",
    re.IGNORECASE,
)
_CLAUSE_BREAK_BEFORE = re.compile(r"[;:,()]|\b(?:but|however|whereas|while|although|though|and)\b", re.IGNORECASE)
_CLAUSE_BREAK_AFTER = re.compile(r"[;:,()]|\b(?:but|however|whereas|while|although|though)\b", re.IGNORECASE)


def window_before(sentence: str, start: int) -> str:
    clause = _CLAUSE_BREAK_BEFORE.split(sentence[:start])[-1]
    return " ".join(clause.split()[-7:])


def window_after(sentence: str, end: int) -> str:
    clause = _CLAUSE_BREAK_AFTER.split(sentence[end:])[0]
    return " ".join(clause.split()[:5])
