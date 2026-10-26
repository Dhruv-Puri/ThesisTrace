"""Pre-download every configured model/tokenizer into the HF cache.

Run once before the demo, inside Docker::

    docker compose run --rm api python -m api.pipeline.warmup

Exit code 0 means every configured component loaded; 1 means at least one failed
(the API still starts and degrades gracefully).
"""

from __future__ import annotations

import json
import sys

from . import config, models


def warmup() -> dict:
    results: dict[str, str] = {}
    errors: dict[str, str] = {}

    tasks: list[tuple[str, str]] = []
    if config.NER_MODEL:
        tasks.append(("token-classification", config.NER_MODEL))
    tasks.append(("text-classification", config.NLI_MODEL))
    if config.SUMMARIZER_MODEL == config.ELI5_MODEL:
        tasks.append(("text2text-generation", config.ELI5_MODEL))
    else:
        tasks.append(("summarization", config.SUMMARIZER_MODEL))
        tasks.append(("text2text-generation", config.ELI5_MODEL))

    for task, model in tasks:
        pipe = models.get_pipeline(task, model)
        if pipe is not None:
            results[task] = model
        else:
            status = models.model_status()["errors"]
            errors[task] = status.get(f"{task}::{model}", "unknown error")

    tokenizers: dict[str, str] = {}
    try:
        from transformers import AutoTokenizer

        for label, model in config.TOKENIZER_MODELS:
            try:
                AutoTokenizer.from_pretrained(model, use_fast=True)
                tokenizers[label] = model
            except Exception as exc:
                tokenizers[label] = f"FAILED: {exc.__class__.__name__}"
    except Exception as exc:
        tokenizers["transformers"] = f"unavailable: {exc.__class__.__name__}"

    return {
        "status": "ok" if not errors else "partial",
        "loaded": results,
        "errors": errors,
        "tokenizers": tokenizers,
    }


def main() -> int:
    report = warmup()
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
