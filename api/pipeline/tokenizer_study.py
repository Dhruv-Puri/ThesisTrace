"""Practical 1 - compare tokenization techniques.

The same document and the same scientific terms are tokenized with BPE (GPT-2),
WordPiece (BERT) and SentencePiece (T5).  The table reports vocabulary size, token
count, tokens-per-word and how technical terms shatter into subwords.

Syllabus: Key NLP tasks - tokenization; Word Level; Practical 1 and the tokenization
half of Practical 7.  HF tokenizers are imported lazily; a whitespace/regex baseline
always works and makes the comparison meaningful even without downloads.
"""

from __future__ import annotations

import re

from . import config
from .textutils import clip, word_tokens

_BASELINE_RE = re.compile(r"\w+|[^\w\s]")


def _baseline_tokens(text: str) -> list[str]:
    return _BASELINE_RE.findall(text)


def _short_error(exc: Exception) -> str:
    message = str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__
    return clip(message, 160)


def study(text: str, terms: list[str], max_chars: int = 20_000) -> dict:
    sample = clip(text, max_chars)
    words = word_tokens(sample)
    word_total = max(1, len(words))
    unique_terms = []
    seen: set[str] = set()
    for term in terms:
        clean = term.strip()
        key = clean.lower()
        if clean and key not in seen:
            seen.add(key)
            unique_terms.append(clean)
    unique_terms = unique_terms[:6]

    baseline_tokens = _baseline_tokens(sample)
    baseline_vocab = len({token.lower() for token in baseline_tokens})
    results: list[dict] = [
        {
            "name": "Whitespace + punctuation (baseline)",
            "model": "builtin",
            "available": True,
            "tokens": len(baseline_tokens),
            "vocab_size": baseline_vocab,
            "tokens_per_word": round(len(baseline_tokens) / word_total, 2),
            "unk_rate": 0.0,
            "note": "Classical word-level tokenization; vocabulary counted from this document.",
        }
    ]

    term_counts: dict[str, dict[str, int | None]] = {
        term: {label: None for label, _ in config.TOKENIZER_MODELS}
        for term in unique_terms
    }
    tokenizer_failures = 0

    try:
        from transformers import AutoTokenizer
    except Exception as exc:  # ImportError or broken torch/transformers install
        AutoTokenizer = None  # type: ignore[assignment]
        for label, model in config.TOKENIZER_MODELS:
            results.append(
                {
                    "name": label,
                    "model": model,
                    "available": False,
                    "tokens": None,
                    "vocab_size": None,
                    "tokens_per_word": None,
                    "unk_rate": None,
                    "note": f"transformers unavailable: {_short_error(exc)}",
                }
            )
        tokenizer_failures = len(config.TOKENIZER_MODELS)
    else:
        for label, model in config.TOKENIZER_MODELS:
            try:
                tokenizer = AutoTokenizer.from_pretrained(model, use_fast=True)
                ids = tokenizer.encode(sample, add_special_tokens=False)
                vocab_size = int(tokenizer.vocab_size)
                unk_id = tokenizer.unk_token_id
                unk_rate = 0.0
                if unk_id is not None and ids:
                    unk_rate = round(ids.count(int(unk_id)) / len(ids), 4)
                for term in unique_terms:
                    term_counts[term][label] = len(
                        tokenizer.tokenize(term, add_special_tokens=False)
                    )
                results.append(
                    {
                        "name": label,
                        "model": model,
                        "available": True,
                        "tokens": len(ids),
                        "vocab_size": vocab_size,
                        "tokens_per_word": round(len(ids) / word_total, 2),
                        "unk_rate": unk_rate,
                        "note": "",
                    }
                )
            except Exception as exc:
                tokenizer_failures += 1
                results.append(
                    {
                        "name": label,
                        "model": model,
                        "available": False,
                        "tokens": None,
                        "vocab_size": None,
                        "tokens_per_word": None,
                        "unk_rate": None,
                        "note": f"could not load tokenizer: {_short_error(exc)}",
                    }
                )

    term_splits = [
        {"term": term, **term_counts[term]} for term in unique_terms
    ]

    if tokenizer_failures == 0:
        note = "BPE, WordPiece and SentencePiece tokenizers were all available."
    elif tokenizer_failures == len(config.TOKENIZER_MODELS):
        note = (
            "Hugging Face tokenizers were unavailable, so only the classical baseline "
            "is shown. Inside Docker the full BPE/WordPiece/SentencePiece table is produced."
        )
    else:
        note = "Some Hugging Face tokenizers could not be loaded; unavailable rows say why."

    return {"tokenizers": results, "term_splits": term_splits, "note": note}
