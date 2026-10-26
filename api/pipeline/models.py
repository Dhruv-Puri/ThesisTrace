"""Lazy Hugging Face model registry.

Models are loaded once per process (never per request) and cached.  Every failure is
recorded instead of raised, so the pipeline can continue with its classical/fallback
tiers.  This is the honest CO6 story: no model, no crash - a warning and a simpler
path.

Syllabus: Transformers and Hugging Face Workflows (``pipeline`` usage, encoder-only
vs encoder-decoder models); Practical 2.
"""

from __future__ import annotations

import importlib.util
import threading
from typing import Any

from . import config
from .textutils import clip

_PIPELINES: dict[str, Any] = {}
_LOADED: dict[str, str] = {}
_ERRORS: dict[str, str] = {}
_LOCK = threading.Lock()

_TASK_LABEL = {
    "token-classification": "ner",
    "text-classification": "nli",
    "summarization": "summarizer",
    "text2text-generation": "eli5",
}


def _key(task: str, model: str) -> str:
    return f"{task}::{model}"


def get_pipeline(task: str, model: str | None):
    """Return a cached transformers pipeline, or ``None`` if it cannot be built."""
    if not model:
        return None
    key = _key(task, model)

    with _LOCK:
        if key in _PIPELINES:
            return _PIPELINES[key]
        if key in _ERRORS:
            return None

    try:
        from transformers import pipeline  # imported lazily; heavy

        pipe = pipeline(task, model=model, tokenizer=model, device=-1)
    except Exception as exc:  # missing package, no network, OOM, bad checkpoint...
        with _LOCK:
            _ERRORS[key] = clip(f"{exc.__class__.__name__}: {exc}", 300)
        return None

    with _LOCK:
        _PIPELINES[key] = pipe
        _LOADED[_TASK_LABEL.get(task, task)] = model
    return pipe


def loaded_models() -> list[str]:
    with _LOCK:
        return list(_LOADED.keys())


def model_status() -> dict:
    """Public status for /api/health and /api/config (never includes secrets)."""
    dependencies = {}
    for name in ("transformers", "torch", "spacy", "sklearn", "fitz"):
        try:
            dependencies[name] = importlib.util.find_spec(name) is not None
        except (ImportError, ValueError):
            dependencies[name] = False

    with _LOCK:
        loaded = dict(_LOADED)
        errors = dict(_ERRORS)

    return {
        "loaded": loaded,
        "errors": errors,
        "dependencies": dependencies,
        "configured": {
            "ner": config.NER_MODEL or None,
            "nli": config.NLI_MODEL,
            "summarizer": config.SUMMARIZER_MODEL,
            "eli5": config.ELI5_MODEL,
        },
    }


def reset() -> None:
    """Test helper - drop cached pipelines and errors."""
    with _LOCK:
        _PIPELINES.clear()
        _LOADED.clear()
        _ERRORS.clear()
