"""Software-readiness artifacts the paper says it ships (evidence for TRL).

A released, installable, documented, served system is stronger readiness evidence
than prose alone.  We read what the paper *states* (we never fetch links or run
code) and classify ten kinds of artifact, each with a page citation and a status:

* ``available``  - stated as existing now ("code is available at github.com/..").
* ``promised``   - future/conditional ("will be released upon acceptance", "on
  request").  Promised artifacts are never counted as evidence; they only show up
  as a near miss.
* absent.

Artifacts are only credited when they are about the authors' own system: links in
references/related work, links to third-party code ("built on ... github.com/..",
"Smith et al. [12]") and negated sentences are rejected.  Title-block links and
page-1 footnotes are read too, because section detection drops text before the
first heading.

``level_hint`` is a conservative software-TRL heuristic and never exceeds 6:
operational use (TRL 7+) needs deployment evidence, not just a repository.
"""

from __future__ import annotations

import re

from .ingest import Document
from .scope import (
    CITES_OTHERS, NEG, OWN, PageLocator, ROLE_WEIGHT, front_matter, role_for_heading,
    window_after, window_before,
)
from .textutils import normalize_for_match, normalize_ws, split_sentences

_HOSTS = (
    r"(?:github\.com|gitlab\.com|bitbucket\.org|codeberg\.org|huggingface\.co|zenodo\.org|"
    r"sourceforge\.net|osf\.io|figshare\.com)"
)

# key -> (label, patterns, needs_own_marker)
_CLASSES: dict[str, tuple[str, list[str], bool]] = {
    "source_released": ("Source code released", [
        rf"(?:https?://)?(?:www\.)?{_HOSTS}/[\w.\-]+",
        r"\b(?:our|the) (?:code|source code|implementation|toolkit|library|package|repository|repo)\b"
        r"[^.]{0,60}\b(?:is|are|has been|have been|can be|will be|to be|shall be) "
        r"(?:publicly |freely |openly |made )?"
        r"(?:available|released|open[- ]sourced?|public)\b",
        r"\bwe (?:release|open[- ]source|publish|make (?:our )?(?:code|the code|it) (?:publicly )?available)\b",
        r"\b(?:code|implementation) (?:is )?(?:publicly )?available (?:at|on|from)\b",
    ], False),
    "installable": ("Installable package", [
        r"\bpip install\b", r"\bconda (?:install|create|env)\b", r"\bnpm install\b",
        r"\b(?:available|published|distributed) (?:on|via|through|as a) (?:PyPI|pip|conda|npm|CRAN|Maven|Homebrew)\b",
        r"\bpypi\.org\b|\bnpmjs\.com\b|\bcrates\.io\b", r"\brequirements\.txt\b",
        r"\binstallation (?:instructions|guide|script)\b", r"\b(?:pip[- ])?installable\b",
        r"\b(?:pip|pypi|conda|npm) (?:package|release|distribution)\b",
        r"\bsetup\.py\b|\bpyproject\.toml\b",
    ], False),
    "container": ("Container image / orchestration", [
        r"\bdocker (?:image|container|file|hub|compose)s?\b|\bdockerfile\b",
        r"\bhub\.docker\.com\b|\bghcr\.io\b", r"\bkubernetes\b|\bhelm chart\b",
        r"\bcontaineri[sz]ed\b",
    ], True),
    "api_service": ("API / SDK / service", [
        r"\b(?:REST(?:ful)?|gRPC|GraphQL) (?:API|endpoint|service|interface)s?\b",
        r"\b(?:public |web |python |http )?API (?:is )?(?:available|exposed|provided)\b",
        r"\bSDK\b",
        r"\bwe (?:expose|provide|offer|ship|publish) (?:a |an |the )?(?:\w+ ){0,2}(?:API|SDK|service|endpoint)\b",
    ], True),
    "live_demo": ("Live demo / hosted app", [
        r"\b(?:live|online|interactive|web|public) demo\b",
        r"\bdemo(?:nstration)? (?:is )?(?:available|hosted|accessible|at)\b",
        r"\bhuggingface\.co/spaces/", r"\b(?:hosted|deployed) (?:at|on) https?://",
        r"\bweb (?:app|application|interface|service) (?:is )?(?:available|hosted|accessible)\b",
        r"\bstreamlit\.app\b|\bgradio\.live\b|\bvercel\.app\b|\bherokuapp\.com\b|\bnetlify\.app\b|\bonrender\.com\b",
    ], False),
    "versioned_release": ("Versioned release", [
        r"\b(?:release|tag)\s+v?\d+\.\d+(?:\.\d+)?\b", r"\bv\d+\.\d+\.\d+\b",
        r"\bgithub releases?\b|\breleases? page\b", r"\bsemantic versioning\b", r"\bchangelog\b",
    ], False),
    "tests_ci": ("Tests / CI", [
        r"\bunit tests?\b", r"\bintegration tests?\b", r"\btest suite\b", r"\btest coverage\b",
        r"\b(?:continuous integration|CI/CD|CI pipeline|GitHub Actions|Travis CI|CircleCI)\b",
        r"\bpytest\b|\bunittest\b",
    ], True),
    "documentation": ("Documentation", [
        r"\b(?:documentation|docs)\b[^.]{0,40}\b(?:available|hosted|provided|planned|at)\b",
        r"\breadthedocs\b|\bread the docs\b", r"\bREADME\b",
        r"\btutorials?\b[^.]{0,30}\b(?:available|provided|included)\b",
        r"\bdeveloper (?:guide|documentation)\b|\buser (?:guide|manual)\b",
    ], True),
    "license": ("Open licence", [
        r"\b(?:MIT|Apache(?:[- ]2(?:\.0)?)?|BSD(?:[- ]\d-Clause)?|GPL(?:v?\d)?|LGPL|AGPL|MPL|CC[- ]BY(?:[- ]\w+)?|"
        r"Creative Commons)\s+(?:open[- ])?licen[cs]e[sd]?\b",
        r"\blicen[cs]ed under (?:the )?(?:MIT|Apache|BSD|GPL|LGPL|AGPL|MPL|CC)\b",
        r"\breleased under (?:the )?(?:\w+[- ]){0,2}licen[cs]e\b",
    ], False),
    "adoption": ("Reported adoption", [
        r"\b\d[\d,.]*[kKmM+]?\s+(?:stars|downloads|forks|installs|active users|users)\b",
        r"\b(?:downloaded|installed) (?:more than |over |about )?\d",
        r"\bin active use\b", r"\badopted by\b",
    ], True),
}
_COMPILED = {key: [re.compile(p, re.IGNORECASE) for p in spec[1]] for key, spec in _CLASSES.items()}

_PROMISE = re.compile(
    r"\b(?:will be|to be|going to be|shall be|upon (?:acceptance|publication)|"
    r"after (?:acceptance|publication|review)|soon|forthcoming|coming soon|in the (?:near )?future|"
    r"we (?:plan|intend|aim|will|would like) to|planned|(?:upon|on) request|by request|"
    r"available from the (?:authors|corresponding author))\b",
    re.IGNORECASE,
)
_THIRD_PARTY = re.compile(
    r"\b(?:built (?:on|upon)|based on|builds? on|adapted from|forked from|extends|following|"
    r"baselines?|re-?implementation of|official implementation of|reproduc\w+|provided by|"
    r"pre-?trained|checkpoints? (?:from|of)|the authors of)\b",
    re.IGNORECASE,
)
_OWN_RELEASE = re.compile(r"\b(?:our|we (?:release|open|publish|provide|make))\b", re.IGNORECASE)

_ALLOWED_ROLES = {"front", "abstract", "intro", "method", "results", "discussion", "conclusion", "other"}
_RUNNABLE = {"installable", "container"}
_SERVED = {"api_service", "live_demo"}


def _judge(key: str, sentence: str, match: re.Match[str], needs_own: bool) -> tuple[str, str | None]:
    """Return (status, reject_reason). status in available|promised|rejected."""
    before = window_before(sentence, match.start())
    after = window_after(sentence, match.end())
    if NEG.search(before) or NEG.search(after):
        return "rejected", "negated"
    if CITES_OTHERS.search(sentence):
        return "rejected", "attributed to other work"
    if _THIRD_PARTY.search(sentence) and not _OWN_RELEASE.search(sentence):
        return "rejected", "third-party code or baseline"
    if _PROMISE.search(sentence):
        return "promised", None
    if needs_own and not OWN.search(sentence):
        return "rejected", "not stated about the authors' own system"
    return "available", None


def collect_artifacts(doc: Document, locator: PageLocator | None = None) -> dict:
    locator = locator or PageLocator(doc.pages)
    units: list[tuple[str, str, int]] = []  # (role, text, page)
    front = front_matter(doc)
    if front:
        units.append(("front", front, 1))
    for section in doc.sections:
        role = role_for_heading(section.heading)
        if role in _ALLOWED_ROLES and ROLE_WEIGHT.get(role, 0) > 0:
            units.append((role, section.text, section.page))

    hits: dict[str, list[dict]] = {key: [] for key in _CLASSES}
    near: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for role, text, page in units:
        for sentence in split_sentences(text):
            norm = normalize_for_match(sentence)
            for key, (label, _, needs_own) in _CLASSES.items():
                if (key, norm) in seen:
                    continue
                for pattern in _COMPILED[key]:
                    match = pattern.search(sentence)
                    if not match:
                        continue
                    seen.add((key, norm))
                    status, reason = _judge(key, sentence, match, needs_own)
                    item = {
                        "key": key, "label": label, "status": status, "role": role,
                        "page": locator.locate(sentence, page),
                        "quote": normalize_ws(sentence)[:240],
                    }
                    if status == "rejected":
                        near.append({**item, "reason": reason})
                    else:
                        hits[key].append(item)
                    break

    classes: list[dict] = []
    for key, (label, _, _) in _CLASSES.items():
        available = [h for h in hits[key] if h["status"] == "available"]
        promised = [h for h in hits[key] if h["status"] == "promised"]
        chosen = (available or promised or [None])[0]
        classes.append({
            "key": key, "label": label,
            "status": "available" if available else ("promised" if promised else "absent"),
            "page": chosen["page"] if chosen else None,
            "quote": chosen["quote"] if chosen else "",
            "mentions": len(available),
        })

    by_key = {item["key"]: item for item in classes}
    got = {key for key, item in by_key.items() if item["status"] == "available"}
    counted = got - {"adoption"}
    level_hint = 0
    if "source_released" in got and (got & (_RUNNABLE | _SERVED)) and len(counted) >= 3:
        level_hint = 5
        if (got & _SERVED) and (got & _RUNNABLE) and len(counted) >= 4:
            level_hint = 6

    promised_keys = [key for key, item in by_key.items() if item["status"] == "promised"]
    if level_hint:
        note = (f"{len(counted)} artifact types available ({', '.join(sorted(counted))}); "
                f"software-readiness heuristic suggests TRL {level_hint}.")
    elif promised_keys:
        note = "Artifacts are promised but not available yet: " + ", ".join(promised_keys) + "."
    elif counted:
        note = "Some artifacts are available, but too few to raise the level."
    else:
        note = "No released, installable or hosted artifact was found in the paper."
    return {
        "classes": classes,
        "available": sorted(counted),
        "promised": promised_keys,
        "level_hint": level_hint,
        "rejected": near[:6],
        "note": note,
    }
