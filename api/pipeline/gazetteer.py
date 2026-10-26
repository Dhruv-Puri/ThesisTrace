"""Stage 4a - scientific gazetteer.

A transformer NER model knows Person/Organisation/Location; a scientific paper is
mostly about *datasets, metrics, models and algorithms*.  This hand-built gazetteer
fills that gap and acts as the low-RAM fallback when the NER model is unavailable.

Syllabus link: Named Entity Recognition / information extraction, word classes, and
rule-based NLP (regex + curated lexicons).
"""

from __future__ import annotations

import re

from .ingest import Document
from .textutils import normalize_ws

# ---------------------------------------------------------------------------
# Lexicons.  Keep entries unambiguous; a noisy gazetteer is worse than none.
# ---------------------------------------------------------------------------

_MODEL_TERMS = [
    "BERT", "RoBERTa", "DistilBERT", "ALBERT", "XLNet", "ELECTRA", "DeBERTa",
    "GPT-2", "GPT-3", "GPT-4", "ChatGPT", "LLaMA", "Mistral", "Gemini", "Claude",
    "T5", "FLAN-T5", "BART", "DistilBART", "Pegasus", "Transformer", "ViT", "CLIP",
    "ResNet", "VGG", "Inception", "EfficientNet", "MobileNet", "U-Net", "YOLO",
    "Mask R-CNN", "Faster R-CNN", "Stable Diffusion", "Whisper", "wav2vec",
    "XGBoost", "LightGBM", "CatBoost",
]

_ALGORITHM_TERMS = [
    "random forest", "support vector machine", "logistic regression", "naive bayes",
    "k-means", "k-nearest neighbours", "k-nearest neighbors", "PCA", "LDA",
    "LSTM", "GRU", "CNN", "RNN", "MLP", "attention", "self-attention",
    "beam search", "dropout", "batch normalization", "layer normalization",
    "gradient descent", "Adam", "SGD", "TF-IDF", "BM25", "cosine similarity",
]

_DATASET_TERMS = [
    "ImageNet", "CIFAR-10", "CIFAR-100", "MNIST", "Fashion-MNIST", "SQuAD",
    "GLUE", "SuperGLUE", "CoNLL-2003", "MS MARCO", "COCO", "ADE20K", "Cityscapes",
    "LibriSpeech", "WikiText-103", "Penn Treebank", "IMDb", "AG News", "MIMIC-III",
    "PhysioNet", "WMT14", "WMT16", "WMT19", "IWSLT", "Natural Questions",
    "HotpotQA", "BEIR", "UCI", "Kaggle",
]

_METRIC_TERMS = [
    "accuracy", "top-1 accuracy", "top-5 accuracy", "precision", "recall",
    "F1", "F1-score", "macro-F1", "BLEU", "ROUGE", "ROUGE-L", "METEOR",
    "perplexity", "AUC", "AUC-ROC", "ROC-AUC", "MSE", "RMSE", "MAE",
    "p-value", "confidence interval", "Cohen's kappa", "IoU", "mAP", "WER",
]

_TYPE_BY_TERM: list[tuple[str, str, str]] = []
for _term in _MODEL_TERMS:
    _TYPE_BY_TERM.append((_term, "MODEL", _term))
for _term in _ALGORITHM_TERMS:
    _TYPE_BY_TERM.append((_term, "ALGORITHM", _term.title() if _term.islower() else _term))
for _term in _DATASET_TERMS:
    _TYPE_BY_TERM.append((_term, "DATASET", _term))
for _term in _METRIC_TERMS:
    _TYPE_BY_TERM.append((_term, "METRIC", _term))


def _compile_term(term: str) -> re.Pattern[str]:
    parts = [re.escape(part) for part in term.split()]
    body = r"\s+".join(parts)
    return re.compile(r"(?<![A-Za-z0-9])" + body + r"s?(?![A-Za-z0-9])", re.IGNORECASE)


_GAZETTEER = sorted(
    (
        (_compile_term(term), entity_type, canonical)
        for term, entity_type, canonical in _TYPE_BY_TERM
    ),
    key=lambda item: len(item[0].pattern),
    reverse=True,
)

_ORG_RE = re.compile(
    r"(?<![A-Za-z])(?:[A-Z][A-Za-z&.\-']+(?:\s+[A-Z][A-Za-z&.\-']+){0,4})\s+"
    r"(?:University|Institute|Laboratory|Lab|Corporation|Corp\.?|Inc\.?|Ltd\.?|"
    r"GmbH|Foundation|Center|Centre|College|Hospital)\b"
)
_PERSON_RE = re.compile(
    r"\b(?:Dr|Prof|Professor|Mr|Ms|Mrs)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b"
)


def find_entities(document: Document) -> list[dict]:
    """Return every gazetteer/organisation/person mention with a page number."""
    entities: list[dict] = []
    for page in document.pages:
        text = page.text
        candidates: list[tuple[int, int, str, str]] = []

        for pattern, entity_type, canonical in _GAZETTEER:
            for match in pattern.finditer(text):
                candidates.append((match.start(), match.end(), entity_type, canonical))

        for match in _ORG_RE.finditer(text):
            candidates.append((match.start(), match.end(), "ORG", normalize_ws(match.group(0))))
        for match in _PERSON_RE.finditer(text):
            candidates.append((match.start(), match.end(), "PER", normalize_ws(match.group(0))))

        # Keep the longest span when two lexicon entries overlap (e.g. GPT-3 / GPT).
        candidates.sort(key=lambda item: (item[0], -(item[1] - item[0])))
        accepted: list[tuple[int, int, str, str]] = []
        for start, end, entity_type, canonical in candidates:
            if any(not (end <= other_start or start >= other_end)
                   for other_start, other_end, _, _ in accepted):
                continue
            accepted.append((start, end, entity_type, canonical))

        for start, end, entity_type, canonical in sorted(accepted):
            surface = text[start:end].strip()
            if not surface:
                continue
            entities.append(
                {
                    "text": surface,
                    "type": entity_type,
                    "start": start,
                    "end": end,
                    "page": page.number,
                    "source": "gazetteer",
                    "canonical": canonical,
                }
            )
    return entities


def key_concepts(entities: list[dict]) -> dict:
    """Group mentions into models / datasets / metrics / other for the UI."""
    groups: dict[str, dict[str, dict]] = {
        "models": {},
        "datasets": {},
        "metrics": {},
        "others": {},
    }
    type_to_group = {
        "MODEL": "models",
        "ALGORITHM": "models",
        "DATASET": "datasets",
        "METRIC": "metrics",
        "PER": "others",
        "ORG": "others",
    }
    for entity in entities:
        group = type_to_group.get(entity["type"])
        if not group:
            continue
        canonical = entity.get("canonical") or entity["text"]
        key = canonical.lower()
        bucket = groups[group].setdefault(
            key, {"name": canonical, "type": entity["type"], "count": 0, "pages": set()}
        )
        bucket["count"] += 1
        bucket["pages"].add(int(entity["page"]))

    result: dict[str, list[dict]] = {}
    for group, buckets in groups.items():
        items = sorted(buckets.values(), key=lambda item: (-item["count"], item["name"].lower()))
        result[group] = [
            {
                "name": item["name"],
                "type": item["type"],
                "count": item["count"],
                "pages": sorted(item["pages"])[:8],
            }
            for item in items[:12]
        ]
    return result


def count_matches(entities: list[dict]) -> int:
    """Occurrences, not distinct terms - used for technical-term density."""
    return len(entities)
