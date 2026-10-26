"""Stage 4b - hybrid NER.

A small DistilBERT CoNLL model finds Person/Organisation/Location; the gazetteer
adds the scientific entity types a general NER model does not know (datasets,
metrics, models, algorithms).  Merge rule: model wins token boundaries, gazetteer
wins the type of a known term, and every entity records its source.

Syllabus: Named Entity Recognition / information extraction; Practical 2 (Hugging
Face transformer models for basic NLP tasks).  LOW_RAM=1 uses the gazetteer only.
"""

from __future__ import annotations

import re

from . import config, gazetteer, models
from .ingest import Document
from .textutils import normalize_ws

_LABEL_MAP = {
    "PER": "PER", "PERSON": "PER",
    "ORG": "ORG", "ORGANIZATION": "ORG",
    "LOC": "LOC", "LOCATION": "LOC", "GPE": "LOC",
}
_TYPE_PRIORITY = {
    "DATASET": 0, "MODEL": 1, "ALGORITHM": 2, "PER": 3,
    "ORG": 4, "LOC": 5, "METRIC": 6,
}


def _chunks(text: str, size: int = 900, overlap: int = 80):
    text = text or ""
    if len(text) <= size:
        yield text, 0
        return
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            space = text.rfind(" ", start + 200, end)
            if space != -1:
                end = space
        yield text[start:end], start
        if end >= len(text):
            break
        start = max(0, end - overlap)


def _model_entities(document: Document) -> tuple[list[dict], list[str]]:
    warnings: list[str] = []
    if config.LOW_RAM:
        warnings.append("LOW_RAM=1: NER runs in gazetteer-only mode (no transformer model).")
        return [], warnings

    pipe = models.get_pipeline("token-classification", config.NER_MODEL)
    if pipe is None:
        status = models.model_status()["errors"]
        detail = next(iter(status.values()), "model could not be loaded")
        warnings.append(
            f"NER model unavailable - gazetteer-only mode. ({detail})"
        )
        return [], warnings

    entities: list[dict] = []
    for page in document.pages[: config.MAX_NER_PAGES]:
        for chunk, offset in _chunks(page.text):
            if not chunk.strip():
                continue
            try:
                results = pipe(chunk, aggregation_strategy="simple")
            except Exception as exc:
                warnings.append(f"NER failed on p.{page.number}: {exc.__class__.__name__}.")
                continue
            for item in results or []:
                entity_type = _LABEL_MAP.get(str(item.get("entity_group", "")).upper())
                if not entity_type:
                    continue
                if float(item.get("score", 0.0)) < 0.55:
                    continue
                start = offset + int(item.get("start", 0))
                end = offset + int(item.get("end", 0))
                raw = chunk[int(item.get("start", 0)): int(item.get("end", 0))]
                leading = len(raw) - len(raw.lstrip())
                start += leading
                surface = normalize_ws(raw)
                if not surface:
                    continue
                entities.append(
                    {
                        "text": surface,
                        "type": entity_type,
                        "start": start,
                        "end": end - (len(raw) - len(raw.rstrip())),
                        "page": page.number,
                        "source": "model",
                    }
                )
    return _dedupe(entities), warnings


def _dedupe(entities: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    unique: list[dict] = []
    for entity in entities:
        key = (entity["page"], entity["start"], entity["end"], entity["type"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(entity)
    return unique


def _merge(model_entities: list[dict], gaz_entities: list[dict]) -> list[dict]:
    merged: list[dict] = []
    used_gazetteer: set[int] = set()

    for entity in model_entities:
        overlapping = [
            (index, candidate)
            for index, candidate in enumerate(gaz_entities)
            if candidate["page"] == entity["page"]
            and not (entity["end"] <= candidate["start"] or entity["start"] >= candidate["end"])
        ]
        if overlapping:
            index, known = overlapping[0]
            for other_index, _ in overlapping:
                used_gazetteer.add(other_index)
            merged.append(
                {
                    **entity,
                    "type": known["type"],
                    "source": "model+gazetteer",
                    "canonical": known.get("canonical") or known["text"],
                }
            )
        else:
            merged.append(entity)

    for index, candidate in enumerate(gaz_entities):
        if index not in used_gazetteer:
            merged.append(candidate)

    merged = _dedupe(merged)
    merged.sort(
        key=lambda item: (
            _TYPE_PRIORITY.get(item["type"], 9),
            int(item["page"]),
            int(item["start"]),
        )
    )
    return merged


def extract_entities(document: Document, gaz_entities: list[dict]) -> tuple[list[dict], dict, list[str]]:
    """Return (entities for UI, key concepts, warnings).

    Key concepts are computed *before* the UI cap so counts remain meaningful.
    """
    model_entities, warnings = _model_entities(document)
    merged = _merge(model_entities, gaz_entities)
    concepts = gazetteer.key_concepts(merged)
    capped = merged[: config.MAX_ENTITIES]
    capped.sort(key=lambda item: (int(item["page"]), int(item["start"])))
    return capped, concepts, warnings


def summarise_entity_types(entities: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entity in entities:
        counts[entity["type"]] = counts.get(entity["type"], 0) + 1
    return dict(sorted(counts.items(), key=lambda item: -item[1]))


def looks_like_entity(text: str) -> bool:
    return bool(re.search(r"[A-Za-z]", text))
