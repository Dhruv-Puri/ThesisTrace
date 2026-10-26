"""Stage 3b - the classical NLP tier.

* TF-IDF index (scikit-learn when available, deterministic pure-Python fallback)
* key-term extraction
* regex extraction of percentages, p-values, metric scores and links
* spaCy POS statistics (optional; neutral defaults when unavailable)

Syllabus links: Word Level (regex, word classes, POS), Text Classification /
Classical NLP Context (feature-based models, TF-IDF), Syntactic Analysis
(chunking/POS via spaCy).  Practical 1/7 use the tokenizer study, not this module.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from .ingest import Document
from .textutils import STOPWORDS, clip, normalize_ws, word_tokens

_TOKEN_RE = re.compile(r"[a-z][a-z0-9'\-]{1,}")
_LINK_RE = re.compile(r"https?://[^\s)\]>\"']+")
_PCT_RE = re.compile(r"(?<![\w.])(\d{1,3}(?:\.\d+)?)\s*%")
_P_RE = re.compile(r"\bp\s*[<=>]\s*0?\.\d+", re.IGNORECASE)
_METRIC_FWD_RE = re.compile(
    r"\b(accuracy|precision|recall|f1(?:-score)?|bleu|rouge(?:-l)?|auc(?:-roc)?|"
    r"map|iou|wer|perplexity)\b"
    r"(?:\s*(?:of|was|is|reached|achieved|=|:))?\s*"
    r"(\d{1,3}(?:\.\d+)?)\s*%?",
    re.IGNORECASE,
)
_METRIC_REV_RE = re.compile(
    r"(\d{1,3}(?:\.\d+)?)\s*%?\s*"
    r"(accuracy|precision|recall|f1(?:-score)?|bleu|rouge(?:-l)?|auc(?:-roc)?|map|iou|wer)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# TF-IDF
# ---------------------------------------------------------------------------

def _features(text: str) -> list[str]:
    tokens = [token for token in _TOKEN_RE.findall((text or "").lower()) if token not in STOPWORDS]
    unigrams = [token for token in tokens if len(token) >= 3]
    bigrams = [
        f"{left} {right}"
        for left, right in zip(tokens, tokens[1:])
        if left not in STOPWORDS and right not in STOPWORDS
    ]
    return unigrams + bigrams


class TfidfIndex:
    """Cosine-similarity index over a list of documents.

    Uses scikit-learn when installed (inside the Docker image) and a transparent
    TF-IDF implementation otherwise, so retrieval still works in a bare Python
    environment and in unit tests.
    """

    def __init__(self, docs: list[str], max_features: int = 4000):
        self.docs = [doc or "" for doc in docs]
        self.max_features = max_features
        self.backend = "pure-python"
        self._vectorizer = None
        self._matrix = None
        self._feature_weights: dict[str, float] = {}
        self._vectors: list[dict[str, float]] = []
        self._fit()

    def _fit(self) -> None:
        if not self.docs or not any(doc.strip() for doc in self.docs):
            return
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer

            vectorizer = TfidfVectorizer(
                stop_words="english",
                ngram_range=(1, 2),
                max_features=self.max_features,
                sublinear_tf=True,
                lowercase=True,
            )
            matrix = vectorizer.fit_transform(self.docs)
            if matrix.shape[1] == 0:
                raise ValueError("empty vocabulary")
            self._vectorizer = vectorizer
            self._matrix = matrix
            self.backend = "scikit-learn"
            return
        except Exception:
            pass
        self._fit_pure()

    def _fit_pure(self) -> None:
        features = [_features(doc) for doc in self.docs]
        document_frequency: Counter[str] = Counter()
        for tokens in features:
            document_frequency.update(set(tokens))

        total = max(1, len(features))
        idf = {
            term: math.log((1 + total) / (1 + frequency)) + 1.0
            for term, frequency in document_frequency.items()
        }

        vectors: list[dict[str, float]] = []
        for tokens in features:
            counts = Counter(tokens)
            vector = {
                term: (1.0 + math.log(count)) * idf.get(term, 1.0)
                for term, count in counts.items()
            }
            norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
            vectors.append({term: value / norm for term, value in vector.items()})
            for term, value in vector.items():
                self._feature_weights[term] = self._feature_weights.get(term, 0.0) + value / norm
        self._vectors = vectors

    def scores(self, query: str) -> list[float]:
        if not self.docs:
            return []
        if self._vectorizer is not None and self._matrix is not None:
            from sklearn.metrics.pairwise import cosine_similarity

            query_vector = self._vectorizer.transform([query or ""])
            return [float(value) for value in cosine_similarity(query_vector, self._matrix).ravel()]

        query_counts = Counter(_features(query or ""))
        if not query_counts or not self._vectors:
            return [0.0] * len(self.docs)
        idf = {
            term: math.log((1 + len(self.docs)) / (1 + sum(
                1 for tokens in self._vectors if term in tokens
            ))) + 1.0
            for term in query_counts
        }
        query_vector = {
            term: (1.0 + math.log(count)) * idf[term]
            for term, count in query_counts.items()
        }
        norm = math.sqrt(sum(value * value for value in query_vector.values())) or 1.0
        query_vector = {term: value / norm for term, value in query_vector.items()}
        return [
            sum(value * vector.get(term, 0.0) for term, value in query_vector.items())
            for vector in self._vectors
        ]

    def top_terms(self, k: int = 12) -> list[dict]:
        if self._vectorizer is not None and self._matrix is not None:
            names = self._vectorizer.get_feature_names_out()
            weights = self._matrix.sum(axis=0)
            values = weights.A1 if hasattr(weights, "A1") else weights
            pairs = sorted(zip(names, values), key=lambda item: float(item[1]), reverse=True)
        else:
            pairs = sorted(self._feature_weights.items(), key=lambda item: item[1], reverse=True)

        results: list[dict] = []
        seen: set[str] = set()
        for term, score in pairs:
            clean = str(term).strip()
            if not clean or clean in seen:
                continue
            if len(clean) < 3 or clean.isdigit():
                continue
            if all(part in STOPWORDS for part in clean.split()):
                continue
            seen.add(clean)
            results.append({"term": clean, "score": round(float(score), 3)})
            if len(results) >= k:
                break
        return results


def extract_key_terms(doc: Document, k: int = 12) -> tuple[list[dict], str]:
    docs = [section.text for section in doc.sections if len(section.text.split()) >= 25]
    if len(docs) < 2:
        docs = _chunks(doc.full_text, 1800)
    index = TfidfIndex(docs)
    return index.top_terms(k), index.backend


def _chunks(text: str, size: int) -> list[str]:
    words = normalize_ws(text).split()
    return [" ".join(words[start:start + size]) for start in range(0, len(words), size)] or [text]


# ---------------------------------------------------------------------------
# Regex facts
# ---------------------------------------------------------------------------

def _context(text: str, start: int, end: int, width: int = 90) -> str:
    left = text.rfind(" ", 0, max(0, start - width))
    right = text.find(" ", min(len(text), end + width))
    return clip(text[max(0, left + 1): right if right != -1 else len(text)], 220)


def extract_regex_facts(doc: Document) -> dict:
    percentages: list[dict] = []
    p_values: list[dict] = []
    metrics: list[dict] = []
    links: list[dict] = []
    seen_links: set[str] = set()

    for page in doc.pages:
        text = page.text
        for match in _PCT_RE.finditer(text):
            value = f"{match.group(1)}%"
            if any(item["value"] == value and item["page"] == page.number for item in percentages):
                continue
            percentages.append({
                "value": value, "page": page.number,
                "context": _context(text, match.start(), match.end()),
            })
        for match in _P_RE.finditer(text):
            value = normalize_ws(match.group(0))
            if any(item["value"] == value and item["page"] == page.number for item in p_values):
                continue
            p_values.append({
                "value": value, "page": page.number,
                "context": _context(text, match.start(), match.end()),
            })
        for match in _METRIC_FWD_RE.finditer(text):
            metrics.append({
                "metric": match.group(1).lower(),
                "value": match.group(2),
                "page": page.number,
                "context": _context(text, match.start(), match.end()),
            })
        for match in _METRIC_REV_RE.finditer(text):
            metrics.append({
                "metric": match.group(2).lower(),
                "value": match.group(1),
                "page": page.number,
                "context": _context(text, match.start(), match.end()),
            })
        for match in _LINK_RE.finditer(text):
            url = match.group(0).rstrip(".,;")
            if url in seen_links:
                continue
            seen_links.add(url)
            links.append({"url": url, "page": page.number})

    # De-duplicate metric mentions by (metric, value, page).
    unique_metrics: list[dict] = []
    seen_metrics: set[tuple[str, str, int]] = set()
    for item in metrics:
        key = (item["metric"], item["value"], item["page"])
        if key in seen_metrics:
            continue
        seen_metrics.add(key)
        unique_metrics.append(item)

    return {
        "percentages": percentages[:12],
        "p_values": p_values[:12],
        "metric_mentions": unique_metrics[:16],
        "links": links[:12],
    }


# ---------------------------------------------------------------------------
# POS features
# ---------------------------------------------------------------------------

_SPACY = None
_SPACY_LOADED = False
_SPACY_ERROR = ""


def _load_spacy():
    global _SPACY, _SPACY_LOADED, _SPACY_ERROR
    if _SPACY_LOADED:
        return _SPACY
    _SPACY_LOADED = True
    try:
        import spacy

        try:
            _SPACY = spacy.load("en_core_web_sm", disable=["ner", "parser", "lemmatizer"])
        except OSError:
            _SPACY_ERROR = "spaCy model en_core_web_sm is not installed"
    except ImportError:
        _SPACY_ERROR = "spaCy is not installed"
    return _SPACY


def pos_features(sentences: list[dict]) -> dict:
    nlp = _load_spacy()
    if nlp is None:
        return {
            "available": False,
            "reason": _SPACY_ERROR or "spaCy unavailable",
            "noun_ratio": 0.30,
            "verb_ratio": 0.16,
            "adj_ratio": 0.06,
            "tokens": 0,
        }

    texts = [sentence["text"][:500] for sentence in sentences[:250]]
    counts = Counter()
    total = 0
    try:
        for parsed in nlp.pipe(texts, batch_size=32):
            for token in parsed:
                if not token.is_alpha or token.is_stop:
                    continue
                total += 1
                counts[token.pos_] += 1
    except Exception as exc:  # pragma: no cover - model/runtime specific
        return {
            "available": False,
            "reason": f"spaCy inference failed: {exc}",
            "noun_ratio": 0.30,
            "verb_ratio": 0.16,
            "adj_ratio": 0.06,
            "tokens": 0,
        }

    denominator = max(1, total)
    return {
        "available": total > 0,
        "reason": "" if total else "no alphabetic tokens",
        "noun_ratio": round(counts["NOUN"] / denominator, 3),
        "verb_ratio": round(counts["VERB"] / denominator, 3),
        "adj_ratio": round(counts["ADJ"] / denominator, 3),
        "pron_ratio": round(counts["PRON"] / denominator, 3),
        "tokens": total,
    }


def token_count(text: str) -> int:
    return len(word_tokens(text))
