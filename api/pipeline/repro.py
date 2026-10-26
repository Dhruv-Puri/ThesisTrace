"""Stage 9 - reproducibility checklist (light, evidence-cited).

We read what the paper *states*; we deliberately do not execute any code.  Each of
twelve signals is yes / partial / no with a page citation when present, then a
weighted score is computed.  This is the honest version of the "reproducibility"
idea from the project brief: a text-level audit, not automated re-execution.

Syllabus: information extraction + evidence citation; supports the evaluation and
error-analysis story (CO4/CO6).
"""

from __future__ import annotations

import re

from .ingest import Document, norm_heading
from .textutils import normalize_ws

_METHOD_SECTIONS = ("method", "methods", "methodology", "approach", "proposed method", "experimental setup")
_DATA_SECTIONS = ("data", "availability", "experiments", "experimental setup", "results")
_RESULT_SECTIONS = ("results", "experiment", "experiments", "evaluation", "discussion", "analysis")


def _sections(doc: Document, names: tuple[str, ...]) -> list:
    picked = [
        section for section in doc.sections
        if any(name in norm_heading(section.heading) for name in names)
    ]
    return picked or doc.sections


def _quote(text: str, start: int, end: int, width: int = 90) -> str:
    left = text.rfind(" ", 0, max(0, start - width))
    right = text.find(" ", min(len(text), end + width))
    snippet = text[max(0, left + 1): right if right != -1 else len(text)]
    return normalize_ws(snippet)[:260]


def _search(sections: list, patterns: list[str]) -> tuple[int, str] | None:
    for section in sections:
        for pattern in patterns:
            match = re.search(pattern, section.text, re.IGNORECASE)
            if match:
                return section.page, _quote(section.text, match.start(), match.end())
    return None


def _count_patterns(sections: list, patterns: list[str]) -> tuple[int, int, str] | None:
    matched: list[tuple[int, str]] = []
    seen: set[str] = set()
    for section in sections:
        for pattern in patterns:
            match = re.search(pattern, section.text, re.IGNORECASE)
            if match and pattern not in seen:
                seen.add(pattern)
                matched.append((section.page, _quote(section.text, match.start(), match.end())))
    if not matched:
        return None
    return len(matched), matched[0][0], matched[0][1]


def _item(key: str, name: str, weight: int, status: str, evidence: str) -> dict:
    points = {"yes": 1.0, "partial": 0.5, "no": 0.0}.get(status, 0.0)
    return {
        "key": key,
        "name": name,
        "weight": weight,
        "status": status,
        "points": points,
        "evidence": evidence,
    }


def _yes_no(
    key: str,
    name: str,
    weight: int,
    sections: list,
    strong: list[str],
    partial: list[str] | None = None,
    missing_text: str = "Not reported in the extracted text.",
) -> dict:
    found = _search(sections, strong)
    if found:
        return _item(key, name, weight, "yes", f"p.{found[0]} - \u201c{found[1]}\u201d")
    if partial:
        soft = _search(sections, partial)
        if soft:
            return _item(key, name, weight, "partial", f"p.{soft[0]} - \u201c{soft[1]}\u201d")
    return _item(key, name, weight, "no", missing_text)


def assess_reproducibility(
    doc: Document,
    entities: list[dict] | None = None,
    facts: dict | None = None,
) -> dict:
    entities = entities or []
    facts = facts or {}
    methods = _sections(doc, _METHOD_SECTIONS)
    data_sections = _sections(doc, _DATA_SECTIONS)
    result_sections = _sections(doc, _RESULT_SECTIONS)

    items: list[dict] = []

    # Availability statements often live in Methods, so search every section after
    # the preferred data/experiments sections.
    dataset_sections = data_sections + [
        section for section in doc.sections if section not in data_sections
    ]
    items.append(
        _yes_no(
            "dataset_available", "Dataset availability", 2, dataset_sections,
            strong=[
                r"publicly available", r"available (?:at|from|on)\b",
                r"data (?:is|are) (?:released|available)",
                r"(?:github|kaggle|zenodo|figshare|doi\.org|osf\.io|huggingface\.co/datasets)",
            ],
            partial=[r"available (?:upon|on) request", r"proprietary", r"internal dataset"],
            missing_text="No public dataset or data-availability statement found.",
        )
    )

    items.append(
        _yes_no(
            "code_available", "Source code availability", 2, doc.sections,
            strong=[r"github\.com", r"gitlab\.com", r"code (?:is|will be) (?:available|released)"],
            partial=[r"code (?:is )?available (?:upon|on) request", r"implementation will be released"],
            missing_text="No source-code link or availability statement found.",
        )
    )

    model_entities = [entity for entity in entities if entity.get("type") in {"MODEL", "ALGORITHM"}]
    architecture_hint = _search(
        methods,
        [r"architecture", r"hidden (?:size|dimension)", r"number of layers", r"parameters",
         r"encoder", r"decoder", r"embedding dimension"],
    )
    if model_entities and architecture_hint:
        items.append(
            _item(
                "model_details", "Model architecture details", 1, "yes",
                f"p.{model_entities[0]['page']} - named model ({model_entities[0]['text']}); "
                f"p.{architecture_hint[0]} - \u201c{architecture_hint[1]}\u201d",
            )
        )
    elif model_entities:
        items.append(
            _item(
                "model_details", "Model architecture details", 1, "partial",
                f"p.{model_entities[0]['page']} - names {model_entities[0]['text']}, but no "
                "architecture/hyperparameter description was found.",
            )
        )
    else:
        items.append(
            _item("model_details", "Model architecture details", 1, "no",
                  "No named model or architecture description found.")
        )

    hyper = _count_patterns(
        methods,
        [r"learning rate", r"batch size", r"epochs?", r"optimizer", r"weight decay",
         r"dropout", r"warmup", r"gradient clipping"],
    )
    if hyper and hyper[0] >= 2:
        items.append(
            _item("hyperparameters", "Hyperparameters", 2, "yes",
                  f"p.{hyper[1]} - \u201c{hyper[2]}\u201d ({hyper[0]} hyperparameter signals found)")
        )
    elif hyper:
        items.append(
            _item("hyperparameters", "Hyperparameters", 2, "partial",
                  f"p.{hyper[1]} - only one hyperparameter signal found: \u201c{hyper[2]}\u201d")
        )
    else:
        items.append(
            _item("hyperparameters", "Hyperparameters", 2, "no",
                  "Learning rate, batch size, epochs and optimizer are not reported.")
        )

    items.append(
        _yes_no(
            "preprocessing", "Preprocessing", 1, methods,
            strong=[r"preprocess", r"tokeni[sz]", r"normaliz", r"data augmentation", r"cleaning"],
            partial=[r"we use standard", r"off-the-shelf"],
            missing_text="No preprocessing description found.",
        )
    )

    items.append(
        _yes_no(
            "random_seed", "Random seed", 1, doc.sections,
            strong=[r"random seed", r"\bseed\s*[=:]", r"fixed seed", r"set the seed"],
            missing_text="No random seed is reported.",
        )
    )

    items.append(
        _yes_no(
            "environment", "Software environment", 1, methods,
            strong=[r"requirements\.txt", r"\bconda\b", r"\bdocker\b", r"pytorch\s+\d",
                    r"tensorflow\s+\d", r"python\s+3\.\d"],
            missing_text="No environment, dependency or version information found.",
        )
    )

    procedure = _search(
        methods,
        [r"\bwe train\b", r"\balgorithm\s+\d", r"\bstep\s+1\b", r"\bfirst,? we\b",
         r"\bthen,? we\b", r"\bfinally,? we\b"],
    )
    method_words = sum(len(section.text.split()) for section in methods)
    if procedure and method_words >= 150:
        items.append(
            _item("procedure", "Experimental procedure", 1, "yes",
                  f"p.{procedure[0]} - \u201c{procedure[1]}\u201d")
        )
    elif method_words >= 150:
        items.append(
            _item("procedure", "Experimental procedure", 1, "partial",
                  f"A method section exists (~{method_words} words), but no explicit step sequence was found.")
        )
    else:
        items.append(
            _item("procedure", "Experimental procedure", 1, "no",
                  "No substantial method section was found.")
        )

    items.append(
        _yes_no(
            "data_split", "Train / validation / test split", 1, methods + result_sections,
            strong=[
                r"train(?:ing)?\s*[/,-]\s*(?:validation|dev|test)",
                r"\b(?:train|test|validation|dev) split\b",
                r"\b(?:\d{2,3}\s*[/-]\s*){2}\d{2,3}\b",
                r"held[- ]out",
            ],
            partial=[r"\bsplit\b", r"\bpartitioned\b"],
            missing_text="No train/validation/test split is described.",
        )
    )

    items.append(
        _yes_no(
            "sample_size", "Sample size", 1, result_sections + methods,
            strong=[r"\bN\s*=\s*\d", r"\b\d[\d,]*\s+(?:samples|examples|images|participants|patients|documents)\b",
                    r"\b(?:dataset|corpus) (?:contains|consists of) \d"],
            missing_text="No sample size (N) is stated.",
        )
    )

    items.append(
        _yes_no(
            "baseline", "Baseline comparison", 1, result_sections,
            strong=[r"\bbaseline", r"state[- ]of[- ]the[- ]art", r"compared (?:with|to)",
                    r"\bcontrol group\b", r"outperform"],
            missing_text="No baseline or comparison condition is described.",
        )
    )

    metric_mentions = facts.get("metric_mentions") or []
    if metric_mentions:
        first = metric_mentions[0]
        items.append(
            _item("metrics", "Evaluation metrics", 1, "yes",
                  f"p.{first['page']} - {first['metric']} = {first['value']}")
        )
    elif any(entity.get("type") == "METRIC" for entity in entities):
        entity = next(entity for entity in entities if entity.get("type") == "METRIC")
        items.append(
            _item("metrics", "Evaluation metrics", 1, "partial",
                  f"p.{entity['page']} - names {entity['text']}, but no metric value was extracted.")
        )
    else:
        items.append(
            _item("metrics", "Evaluation metrics", 1, "no",
                  "No evaluation metric or value was found.")
        )

    total_weight = sum(item["weight"] for item in items)
    earned = sum(item["weight"] * item["points"] for item in items)
    score = round(100 * earned / total_weight) if total_weight else 0
    yes_count = sum(1 for item in items if item["status"] == "yes")
    partial_count = sum(1 for item in items if item["status"] == "partial")

    return {
        "score": score,
        "items": items,
        "summary": f"{yes_count} present, {partial_count} partial, "
                   f"{len(items) - yes_count - partial_count} missing.",
        "note": "Text-level audit only; no code was executed.",
    }
