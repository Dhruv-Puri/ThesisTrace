"""Stage 5 - summarization (Practical 4).

3-bullet summary + ELI5.  A local transformer is used when available
(DistilBART for bullets, FLAN-T5 for ELI5); otherwise a deterministic extractive
fallback runs.  Every number in generated text must already exist in the source,
which is our mechanical anti-hallucination check (CO4).

Syllabus: natural language generation; text summarization techniques; Practical 4.
"""

from __future__ import annotations

import re

from .. import prompts
from . import config, models
from .ingest import Document, abstract_text, conclusion_text
from .textutils import (
    clip, jaccard, normalize_ws, numbers_in, split_sentences,
)

_BAD_START = re.compile(r"^(?:summary|abstract|conclusion|in this paper|this paper)\s*[:\-]\s*", re.I)
_LEADING_NUMBER = re.compile(r"^\s*(?:\d+[\.\)]|[-•*])\s+")


def _num_key(value: str) -> str:
    raw = value.rstrip("%").replace(",", "")
    try:
        return f"{float(raw):g}"
    except ValueError:
        return raw


def _clean_bullet(text: str) -> str:
    text = normalize_ws(text)
    text = _LEADING_NUMBER.sub("", text)
    text = _BAD_START.sub("", text)
    text = text.strip(" -•\t")
    if not text:
        return ""
    text = text[0].upper() + text[1:]
    if text[-1] not in ".!?":
        text += "."
    return clip(text, 300)


def _extractive_bullets(text: str, count: int = 3) -> list[str]:
    sentences = [
        sentence.strip()
        for sentence in split_sentences(text)
        if 30 <= len(sentence) <= 380
        and not sentence.lower().startswith(("references", "figure", "table"))
    ]
    if not sentences:
        fallback = clip(text, 260)
        return [_clean_bullet(fallback)] if fallback else []

    total = len(sentences)
    scored: list[tuple[float, int, str]] = []
    for index, sentence in enumerate(sentences):
        centrality = 0.0
        if total > 1:
            centrality = sum(
                jaccard(sentence, other)
                for other_index, other in enumerate(sentences[:80])
                if other_index != index
            ) / min(total - 1, 79)
        numeric = 0.08 if numbers_in(sentence) else 0.0
        early = 0.25 * (1.0 - index / total)
        scored.append((centrality + numeric + early, index, sentence))

    scored.sort(key=lambda item: (-item[0], item[1]))
    chosen: list[tuple[int, str]] = []
    for _, index, sentence in scored:
        if any(jaccard(sentence, existing) > 0.62 for _, existing in chosen):
            continue
        chosen.append((index, sentence))
        if len(chosen) >= count:
            break
    if len(chosen) < count:
        for _, index, sentence in scored:
            if all(index != existing_index for existing_index, _ in chosen):
                chosen.append((index, sentence))
            if len(chosen) >= count:
                break

    chosen.sort(key=lambda item: item[0])
    bullets = [_clean_bullet(sentence) for _, sentence in chosen]
    return [bullet for bullet in bullets if bullet][:count]


def _number_ok(output: str, source: str) -> bool:
    source_numbers = {_num_key(number) for number in numbers_in(source)}
    return all(_num_key(number) in source_numbers for number in numbers_in(output))


def _neural_bullets(source: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    if config.LOW_RAM:
        pipe = models.get_pipeline("text2text-generation", config.SUMMARIZER_MODEL)
        if pipe is None:
            warnings.append(
                "Small summarizer unavailable - extractive summary used. "
                f"({next(iter(models.model_status()['errors'].values()), 'model not loaded')})"
            )
            return "", warnings
        try:
            result = pipe(
                "summarize: " + clip(source, 2400),
                max_new_tokens=130,
                num_beams=4,
                do_sample=False,
            )
            return result[0].get("generated_text", ""), warnings
        except Exception as exc:
            warnings.append(f"Summarization failed ({exc.__class__.__name__}) - extractive fallback used.")
            return "", warnings

    pipe = models.get_pipeline("summarization", config.SUMMARIZER_MODEL)
    if pipe is not None:
        try:
            result = pipe(
                clip(source, 2400),
                max_length=160,
                min_length=45,
                num_beams=4,
                do_sample=False,
                truncation=True,
            )
            return result[0].get("summary_text", ""), warnings
        except Exception as exc:
            warnings.append(f"Summarization failed ({exc.__class__.__name__}) - trying FLAN-T5.")

    small = models.get_pipeline("text2text-generation", config.ELI5_MODEL)
    if small is not None:
        try:
            result = small(
                "summarize: " + clip(source, 2200),
                max_new_tokens=130,
                num_beams=4,
                do_sample=False,
            )
            warnings.append("DistilBART unavailable - FLAN-T5 produced the summary.")
            return result[0].get("generated_text", ""), warnings
        except Exception as exc:
            warnings.append(f"FLAN-T5 summarization failed ({exc.__class__.__name__}).")

    warnings.append("No summarization model could run - extractive summary used.")
    return "", warnings


def summarize(document: Document) -> tuple[dict, list[str]]:
    abstract = abstract_text(document)
    conclusion = conclusion_text(document)
    source = f"{abstract}\n\n{conclusion}".strip()
    if not source:
        source = clip(document.full_text, 2400)

    warnings: list[str] = []
    neural_text, neural_warnings = _neural_bullets(source)
    warnings.extend(neural_warnings)

    bullets: list[str] = []
    method = "extractive"
    abstractive_supported = True

    if neural_text:
        method = "abstractive"
        for sentence in split_sentences(neural_text):
            bullet = _clean_bullet(sentence)
            if bullet and all(jaccard(bullet, existing) < 0.75 for existing in bullets):
                bullets.append(bullet)
            if len(bullets) == 3:
                break

        checked: list[str] = []
        dropped = 0
        for bullet in bullets:
            if _number_ok(bullet, source):
                checked.append(bullet)
            else:
                dropped += 1
        if dropped:
            abstractive_supported = False
            warnings.append(
                f"{dropped} summary bullet(s) contained numbers not present in the source "
                "and were removed (numeric-hallucination check)."
            )
        bullets = checked

    if len(bullets) < 3:
        for bullet in _extractive_bullets(source, 3):
            if bullet and all(jaccard(bullet, existing) < 0.68 for existing in bullets):
                bullets.append(bullet)
            if len(bullets) == 3:
                break
    if method == "abstractive" and len(bullets) < 3:
        method = "mixed"

    if not bullets:
        bullets = ["The document did not contain enough prose to summarise."]

    eli5, eli5_method = _explain_simple(abstract or source, warnings)
    if eli5 and not _number_ok(eli5, source):
        warnings.append("ELI5 text contained an unsupported number and was replaced with an extractive explanation.")
        eli5, eli5_method = _plain_language(abstract or source), "extractive"

    return {
        "bullets": bullets[:3],
        "eli5": eli5,
        "abstractive_supported": abstractive_supported,
        "method": method,
        "eli5_method": eli5_method,
    }, warnings


def _plain_language(text: str) -> str:
    sentences = [s for s in split_sentences(text) if 20 <= len(s) <= 260][:2]
    if not sentences:
        return clip(text, 260)
    return "In simple terms: " + " ".join(sentences)


def _explain_simple(abstract: str, warnings: list[str]) -> tuple[str, str]:
    pipe = models.get_pipeline("text2text-generation", config.ELI5_MODEL)
    if pipe is None:
        return _plain_language(abstract), "extractive"
    template = prompts.render("eli5", abstract=clip(abstract, 1800))
    try:
        result = pipe(template["user"], max_new_tokens=160, num_beams=4, do_sample=False)
        text = normalize_ws(result[0].get("generated_text", ""))
        if text:
            return clip(text, 900), "abstractive"
    except Exception as exc:
        warnings.append(f"ELI5 generation failed ({exc.__class__.__name__}); extractive explanation used.")
    return _plain_language(abstract), "extractive"
