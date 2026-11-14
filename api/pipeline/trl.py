"""Stage 10 - Technology Readiness Level (TRL 1-9) with cited evidence.

A deterministic rubric over signals the paper actually states about *its own*
work.  The model never invents a TRL: each level requires a matched phrase in a
role-appropriate section, and the evidence list carries the page.

Design (v2 - see documentation/Evaluation.md, "TRL detection"):

* **Two evidence tracks.**  The *evaluation* track (method -> experiment ->
  baseline) gives TRL 1-4.  The *environment* track (relevant -> field ->
  operational -> certified/proven) gives TRL 5-9 and does **not** require a
  baseline comparison - deployed systems often report none.  The final level is
  the higher of the two, and the environment track only counts when the paper
  also contains an experimental evaluation.
* **Scoped negation and hedging.**  Only the clause around the matched phrase is
  checked (not the whole sentence), so one unrelated "not" or "will" no longer
  deletes a signal.  Environment signals additionally reject hedged or future
  wording ("can be deployed", "may", "we plan to"), sentences that cite other
  work ("Smith et al. deployed ... [12]"), and sentences that are not about the
  authors' own system.
* **Section roles.**  Related work, future work/limitations, references and
  acknowledgements never count as evidence; introductions count only for
  problem/method signals.
* **Tight patterns.**  "real-world datasets", "large-scale ImageNet" and
  "certified robustness" are not evidence of a real-world environment or of
  certification.
* **Optional NLI check.**  For levels 5+ the matched sentence can be confirmed
  with the same NLI cross-encoder used by ClaimCheck; with no model the regex
  result stands and ``nli_checked`` is false.
* **Honest uncertainty.**  The result carries a confidence, a plausible level
  range, and the "near misses" that were ignored and why.
* Reviews/surveys are capped because TRL is about a specific technology, not a
  literature overview - but "we survey 200 students" is not a review.
"""

from __future__ import annotations

import re
from typing import Callable

from .ingest import Document, Section, abstract_text, norm_heading
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

# --------------------------------------------------------------------------- #
# Section roles
# --------------------------------------------------------------------------- #

# Order matters: the first matching rule wins.
_ROLE_RULES: list[tuple[str, re.Pattern[str]]] = [
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

_ROLE_WEIGHT = {
    "results": 1.0, "method": 0.9, "abstract": 0.8, "discussion": 0.7,
    "other": 0.65, "conclusion": 0.6, "intro": 0.5,
    "future": 0.0, "related": 0.0, "excluded": 0.0,
}
_CORE_ROLES = {"abstract", "intro", "method", "results", "discussion", "conclusion"}


def _role(heading: str) -> str:
    name = norm_heading(heading or "")
    for role, pattern in _ROLE_RULES:
        if pattern.search(name):
            return role
    return "other"


def _classified(doc: Document) -> tuple[list[tuple[Section, str]], bool]:
    rows = [(section, _role(section.heading)) for section in doc.sections]
    if not rows:
        rows = [(Section(heading="", text=doc.full_text, page=1), "other")]
    recognised = sum(1 for _, role in rows if role in _CORE_ROLES) >= 2
    return rows, recognised


# --------------------------------------------------------------------------- #
# Signals
# --------------------------------------------------------------------------- #

_ENV_KEYS = ("relevant", "field", "operational", "certified", "proven")

_ALLOWED = {
    "problem": {"abstract", "intro", "other"},
    "method": {"abstract", "intro", "method", "other"},
    "experiment": {"abstract", "results", "other"},
    "baseline": {"abstract", "results", "discussion", "other"},
    **{key: {"abstract", "method", "results", "discussion", "conclusion", "other"} for key in _ENV_KEYS},
}

_MIN_WEIGHT = {"problem": 0.5, "method": 0.5, "experiment": 0.65, "baseline": 0.65,
               **{key: 0.6 for key in _ENV_KEYS}}

_RAW_PATTERNS = {
    "problem": [
        r"\bwe (?:address|study|investigate|tackle|consider|focus on|examine)\b",
        r"\b(?:challenge|problem|task|question) of\b",
        r"\bmotivated by\b",
        r"\bremains? (?:a )?(?:challenge|challenging|open problem|unsolved)\b",
    ],
    "method": [
        r"\bwe (?:propose|present|introduce|develop|design|build|implement|devise)\b",
        r"\b(?:our|the proposed|the presented|the developed) "
        r"(?:method|approach|framework|system|model|algorithm|architecture|tool|pipeline|prototype)\b",
    ],
    "experiment": [
        r"\bwe (?:evaluate|experiment|test|benchmark|validate|compare|measure)\b",
        r"\bexperiments? (?:on|with|show|shows|demonstrate|confirm|indicate)\b",
        r"\bresults? (?:show|shows|demonstrate|indicate|confirm|suggest|reveal)\b",
        r"\bevaluated (?:on|using|against|with)\b",
        r"\bachieves? (?:an? )?(?:accuracy|f1|bleu|rouge|auc|improvement|speed-?up|\d)",
    ],
    "baseline": [
        r"\bbaselines?\b", r"state[- ]of[- ]the[- ]art", r"\bcompared (?:with|to|against)\b",
        r"\boutperform\w*", r"\bimprovements? over\b", r"\bablations?\b",
    ],
    "relevant": [
        r"\breal[- ]world (?:deployment|environment|setting|settings|conditions|use|users?|trial|"
        r"testing|pilot|usage|operation)\b",
        r"\blarge[- ]scale (?:deployment|field|pilot|trial|user study|real[- ]world)\b",
        r"\bindustrial (?:partner|setting|environment|plant|site|deployment|case study|use case|testbed)s?\b",
        r"\b(?:working|hardware|physical|functional|integrated|full[- ]scale) prototype\b",
        r"\bprototype (?:was|were|has been) (?:tested|evaluated|validated|deployed|demonstrated)\b",
        r"\bclinical (?:setting|environment|validation|evaluation|study|trial|deployment|site|practice)s?\b",
        r"\brelevant (?:clinical |operational |real[- ]world |industrial )?(?:environment|setting)s?\b",
        r"\btest ?bed\b", r"\buser studies\b", r"\buser study\b",
        r"\bwith (?:real|actual) (?:users|patients|customers|operators)\b",
        r"\bpilot (?:study|test|deployment|program)\b",
    ],
    "field": [
        r"\bfield (?:test|trial|study|deployment|experiment|evaluation)s?\b",
        r"\bpilot (?:study|test|deployment|program|run|installation|phase)\b",
        r"\bclinical trials?\b",
        r"\btested (?:at|in|on) (?:a|an|the|our) "
        r"(?:hospital|factory|site|plant|farm|school|clinic|bank|airport|warehouse|campus)\b",
        r"\bdeployed (?:with|at|in) (?:a|an|the|our|one|two|three|\d+) (?:partner |pilot |external )?"
        r"(?:hospitals?|factory|factories|schools?|clinics?|banks?|sites?|customers?|compan(?:y|ies)|"
        r"farms?|warehouses?|campus)\b",
        r"\bon[- ]site (?:test|trial|evaluation|validation|deployment)s?\b",
        r"\bin[- ]situ (?:test|trial|evaluation|validation|deployment)s?\b",
        r"\bpartner (?:hospital|bank|company|site|school|clinic|organi[sz]ation)s?\b",
    ],
    "operational": [
        r"\b(?:deployed|used|running|operating|put|moved|pushed|rolled out|launched|released)\s+"
        r"(?:\w+\s+){0,3}(?:in|into) production\b",
        r"\b(?:in|into) (?:production|live) (?:use|environment|deployment|traffic|service|operation|systems?)\b",
        r"\blive (?:deployment|system|traffic|environment|users)\b",
        r"\boperational (?:environment|deployment|use|system|setting)s?\b",
        r"\bdeployed (?:at|across|in|to) (?:\w+[- ]){0,4}"
        r"(?:hospitals?|banks?|factories|plants?|sites?|customers?|stores|airports?|schools?|clinics?|"
        r"warehouses?|production|operation)\b",
    ],
    "certified": [
        r"\bregulatory (?:approval|clearance)\b",
        r"\b(?:FDA|CE|ISO|IEC|DO-178C?) (?:certif\w*|clearance|approv\w*|compliance|compliant|marked)\b",
        r"\bcertified (?:by|under|for (?:use|clinical use|flight|safety))\b",
        r"\bqualification (?:testing|tests?|campaign|process|program)\b",
        r"\bqualified (?:for|by) (?:flight|use|service|production|clinical use)\b",
        r"\bcompl(?:y|ies|ied|iant) with (?:ISO|IEC|FDA|MIL-STD)\b",
        r"\bTRL ?8\b",
    ],
    "proven": [
        r"\bproven in operation\b",
        r"\b(?:millions|thousands|hundreds of thousands|tens of thousands) of "
        r"(?:users|customers|transactions|patients|requests|queries)\b",
        r"\b\d+(?:\.\d+)?\s?[MK] (?:users|customers|transactions|patients|requests|queries)\b",
        r"\bin (?:commercial )?service since\b", r"\bin continuous (?:operation|use)\b",
        r"\bcommercially (?:available|deployed)\b",
    ],
}
_PATTERNS = {key: [re.compile(p, re.IGNORECASE) for p in value] for key, value in _RAW_PATTERNS.items()}

_LEVEL_SIGNAL = {
    1: "problem", 2: "method", 3: "experiment", 4: "baseline", 5: "relevant",
    6: "field", 7: "operational", 8: "certified", 9: "proven",
}
_SIGNAL_LEVEL = {signal: level for level, signal in _LEVEL_SIGNAL.items()}

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

_HYPOTHESES = {
    "relevant": "The authors tested their own system in a realistic, real-world environment.",
    "field": "The authors ran a field trial or pilot with their own system at an external site.",
    "operational": "The authors' system was deployed and running in a live operational environment.",
    "certified": "The authors' system received formal certification or regulatory approval.",
    "proven": "The authors' system has been used in sustained real-world operation at scale.",
}
_NLI_MIN_ENTAILMENT = 0.5

# --------------------------------------------------------------------------- #
# Scoped negation / hedging / attribution
# --------------------------------------------------------------------------- #

_NEG = re.compile(
    r"\b(?:no|not|never|without|neither|nor|none|lacks?|lacking|lacked|absence of|yet to|"
    r"unable to|cannot|fails? to|failed to|rather than|instead of)\b|n't\b",
    re.IGNORECASE,
)
_HEDGE = re.compile(
    r"\b(?:will|would|could|can|may|might|should|shall|plans?|planned|planning|intend(?:s|ed)?|"
    r"aims? to|aimed to|hopes? to|expects? to|expected to|future|potential(?:ly)?|possibl[ey]|"
    r"envision\w*|ideally|if|whether|suitable for|ready for|designed for|enabl\w+)\b",
    re.IGNORECASE,
)
_CITES_OTHERS = re.compile(
    r"\[\s*\d[\d,\s\u2013-]*\]|\bet al\b|\(\s*[A-Z][A-Za-z-]+(?: et al\.?)?,?\s*(?:19|20)\d{2}\s*\)|"
    r"\b(?:prior|previous|existing|related|earlier|other) (?:work|systems?|studies|approaches|methods)\b|"
    r"\b(?:they|their) (?:deployed|tested|ran|conducted)\b",
    re.IGNORECASE,
)
_OWN = re.compile(
    r"\b(?:we|our|ours|us)\b|"
    r"\b(?:this|the proposed|the presented|the developed|the) "
    r"(?:system|model|method|approach|tool|framework|prototype|pipeline|platform|device|algorithm|"
    r"solution|study|trial|deployment|work)\b|"
    r"\b(?:was|were|has been|have been|is|are) (?:successfully |also |then |later )?"
    r"(?:deployed|piloted|tested|evaluated|validated|trialled|trialed|installed|used|running|certified|"
    r"approved|rolled out|qualified)\b",
    re.IGNORECASE,
)
_CLAUSE_BREAK_BEFORE = re.compile(r"[;:,()]|\b(?:but|however|whereas|while|although|though|and)\b", re.IGNORECASE)
_CLAUSE_BREAK_AFTER = re.compile(r"[;:,()]|\b(?:but|however|whereas|while|although|though)\b", re.IGNORECASE)


def _window_before(sentence: str, start: int) -> str:
    clause = _CLAUSE_BREAK_BEFORE.split(sentence[:start])[-1]
    return " ".join(clause.split()[-7:])


def _window_after(sentence: str, end: int) -> str:
    clause = _CLAUSE_BREAK_AFTER.split(sentence[end:])[0]
    return " ".join(clause.split()[:5])


def _reject_reason(sentence: str, match: re.Match[str], env: bool) -> str | None:
    before = _window_before(sentence, match.start())
    after = _window_after(sentence, match.end())
    if _NEG.search(before) or _NEG.search(after):
        return "negated"
    if env:
        if _HEDGE.search(before) or _HEDGE.search(after):
            return "hedged or future wording"
        if _CITES_OTHERS.search(sentence):
            return "attributed to other work"
        if not _OWN.search(sentence):
            return "not stated about the authors' own system"
    return None


def _collect(rows: list[tuple[Section, str]], key: str) -> tuple[list[dict], list[dict]]:
    """Return (accepted, rejected) hits for one signal, best first."""
    accepted: list[dict] = []
    rejected: list[dict] = []
    allowed = _ALLOWED[key]
    env = key in _ENV_KEYS
    order = 0
    for section, role in rows:
        weight = _ROLE_WEIGHT.get(role, 0.0)
        if role not in allowed or weight <= 0:
            continue
        for sentence in split_sentences(section.text):
            order += 1
            for pattern in _PATTERNS[key]:
                match = pattern.search(sentence)
                if not match:
                    continue
                hit = {
                    "signal": key, "level": _SIGNAL_LEVEL[key], "page": section.page,
                    "quote": normalize_ws(sentence)[:240], "section": role,
                    "weight": weight, "order": order,
                }
                reason = _reject_reason(sentence, match, env)
                if reason:
                    rejected.append({**hit, "reason": reason})
                elif weight < _MIN_WEIGHT[key]:
                    rejected.append({**hit, "reason": f"mentioned only in the {role} section"})
                else:
                    accepted.append(hit)
                break
    accepted.sort(key=lambda hit: (-hit["weight"], hit["order"]))
    return accepted[:8], rejected[:8]


# --------------------------------------------------------------------------- #
# Optional NLI confirmation
# --------------------------------------------------------------------------- #

NLIScorer = Callable[[str, str], dict]


def _default_scorer() -> NLIScorer | None:
    try:
        from . import config, models
        from .evidence import _nli_scores
    except Exception:
        return None
    pipe = models.get_pipeline("text-classification", config.NLI_MODEL)
    if pipe is None:
        return None
    return lambda premise, hypothesis: _nli_scores(pipe, hypothesis, premise)


def _entailment(scorer: NLIScorer, key: str, hit: dict) -> float | None:
    try:
        scores = scorer(hit["quote"], _HYPOTHESES[key]) or {}
    except Exception:
        return None
    if not any(float(value or 0) for value in scores.values()):
        return None  # the scorer failed silently; treat as unavailable
    return float(scores.get("entailment", 0.0))


def _select(key: str, accepted: list[dict], scorer: NLIScorer | None) -> tuple[dict | None, list[dict], bool]:
    """Pick the evidence hit for a signal. Returns (hit, nli_rejected, nli_used)."""
    if not accepted:
        return None, [], False
    if scorer is None or key not in _ENV_KEYS:
        return accepted[0], [], False
    rejected: list[dict] = []
    for hit in accepted[:3]:
        score = _entailment(scorer, key, hit)
        if score is None:
            return accepted[0], rejected, bool(rejected)
        if score >= _NLI_MIN_ENTAILMENT:
            return {**hit, "nli": round(score, 3)}, rejected, True
        rejected.append({**hit, "reason": f"NLI entailment {score:.2f} below {_NLI_MIN_ENTAILMENT}"})
    return None, rejected, True


# --------------------------------------------------------------------------- #
# Review / survey detection
# --------------------------------------------------------------------------- #

_HUMAN_SURVEY = re.compile(
    r"\b(?:\d[\d,]*|participants?|respondents?|students?|users?|practitioners?|developers?|"
    r"clinicians?|patients?|employees?|teachers?|farmers?|engineers?|consumers?|customers?|"
    r"questionnaires?|interviews?)\b",
    re.IGNORECASE,
)
_LITERATURE_WORDS = re.compile(
    r"\b(?:literature|papers|approaches|methods|techniques|studies|research|works|advances|"
    r"developments|state of the art|progress|existing)\b",
    re.IGNORECASE,
)
_REVIEW_STRONG = re.compile(
    r"\b(?:systematic (?:literature )?review|literature review|meta[- ]analysis|scoping review)\b|"
    r"\bthis (?:survey|review)\b|\b(?:comprehensive|systematic|extensive|brief|critical) (?:survey|review)\b|"
    r"\bsurvey (?:paper|article)\b",
    re.IGNORECASE,
)
_REVIEW_TITLE = re.compile(r"\b(?:survey|review|overview|meta[- ]analysis|taxonomy)\b", re.IGNORECASE)
_WE_SURVEY = re.compile(r"\bwe (?:survey|review)\b(?P<tail>[^.]{0,80})", re.IGNORECASE)


def _is_review(doc: Document) -> bool:
    title = doc.title or ""
    abstract = abstract_text(doc)[:800]
    if _REVIEW_TITLE.search(title) and not _HUMAN_SURVEY.search(title):
        return True
    if _REVIEW_STRONG.search(f"{title}\n{abstract}"):
        return True
    for match in _WE_SURVEY.finditer(abstract):
        tail = match.group("tail")
        if _LITERATURE_WORDS.search(tail) and not _HUMAN_SURVEY.search(tail):
            return True
    return False


# --------------------------------------------------------------------------- #
# Assessment
# --------------------------------------------------------------------------- #

def assess_trl(
    doc: Document,
    claims: list[dict],
    reproducibility: dict | None = None,
    *,
    use_nli: bool = False,
    nli_scorer: NLIScorer | None = None,
) -> dict:
    rows, recognised = _classified(doc)
    scorer = nli_scorer or (_default_scorer() if use_nli else None)

    findings: dict[str, dict | None] = {}
    support: dict[str, int] = {}
    near_misses: list[dict] = []
    nli_checked = False
    for key in _PATTERNS:
        accepted, rejected = _collect(rows, key)
        hit, nli_rejected, used = _select(key, accepted, scorer)
        findings[key] = hit
        support[key] = len(accepted)
        nli_checked = nli_checked or used
        near_misses.extend(rejected)
        near_misses.extend(nli_rejected)
    review = _is_review(doc)

    # Evaluation track: TRL 1-4.
    eval_level = 1
    if findings["method"]:
        eval_level = 2
    if findings["experiment"] and findings["method"]:
        eval_level = 3
    if findings["baseline"] and findings["experiment"]:
        eval_level = 4

    # Environment track: TRL 5-9 (no baseline required).
    env_level = 0
    if findings["relevant"]:
        env_level = 5
    if findings["field"]:
        env_level = 6
    if findings["operational"]:
        env_level = 7
        if findings["certified"]:
            env_level = 8
        if findings["proven"]:
            env_level = 9

    cap_reasons: list[str] = []
    if env_level and not findings["experiment"]:
        cap_reasons.append(
            "Environment/deployment wording without an experimental evaluation is not counted."
        )
        env_level = 0
    level = max(eval_level, env_level)

    if review and level > 3:
        level = 3
        cap_reasons.append("The document looks like a review/survey, so TRL is capped at 3.")
    elif review:
        cap_reasons.append("The document looks like a review/survey, so TRL is capped at 3.")

    next_signal = _LEVEL_SIGNAL.get(level + 1)
    if cap_reasons:
        cap_reason = " ".join(dict.fromkeys(cap_reasons))
    elif next_signal and not findings.get(next_signal):
        cap_reason = f"No {_SIGNAL_PHRASE.get(next_signal, next_signal)} was found for the next level."
    else:
        cap_reason = "No cap applied; the next level lacked textual evidence."

    evidence: list[dict] = []
    for candidate_level in range(1, level + 1):
        key = _LEVEL_SIGNAL[candidate_level]
        finding = findings.get(key)
        if finding:
            item = {
                "signal": key, "level": candidate_level,
                "page": finding["page"], "quote": finding["quote"], "section": finding["section"],
            }
            if "nli" in finding:
                item["nli"] = finding["nli"]
            evidence.append(item)

    # Confidence and plausible range.
    deciding = _LEVEL_SIGNAL[level]
    deciding_hit = findings.get(deciding)
    if level == 1 or not deciding_hit or review:
        confidence = "low"
    elif (support[deciding] >= 2 or "nli" in deciding_hit) and recognised:
        confidence = "high"
    elif support[deciding] >= 2 or recognised:
        confidence = "medium"
    else:
        confidence = "low"
    # A hedged/vetoed mention of a higher level widens the range by one; an explicit
    # negation ("no field trial was conducted") does not.
    has_near_miss_above = any(
        item["level"] > level and item["reason"] != "negated" for item in near_misses
    )
    level_low = level if confidence != "low" or level == 1 else level - 1
    level_high = min(9, level + 1) if (has_near_miss_above and not review) else level

    near_misses.sort(key=lambda item: (-item["level"], item["order"]))
    near_out = [
        {"signal": item["signal"], "level": item["level"], "page": item["page"],
         "quote": item["quote"], "reason": item["reason"]}
        for item in near_misses if item["level"] >= 5 or item["level"] > level
    ][:5]

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
    explanation += f" Confidence: {confidence}"
    if level_low != level_high:
        explanation += f" (plausible range TRL {level_low}-{level_high})"
    explanation += "."
    if near_out:
        explanation += (
            f" {len(near_out)} higher-level mention(s) were ignored as non-evidence "
            f"(e.g. {near_out[0]['reason']})."
        )
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
        "confidence": confidence,
        "level_range": [level_low, level_high],
        "near_misses": near_out,
        "nli_checked": nli_checked,
        "sections_recognised": recognised,
    }
