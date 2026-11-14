"""Grounded Q&A over one uploaded paper (CO5 - RAG grounding).

question -> two kinds of context:

* **Pipeline findings** (``chat_findings``): the app's own outputs for this paper -
  claim verdicts with their evidence, the TRL result, the reproducibility checklist,
  extracted datasets/metrics, the summary and caveats - cited as ``[F3]``.
* **Paper passages**: TF-IDF retrieval over the paper's own sentence index, cited as
  ``[p.N]``.

Gemini writes the answer from *only* that context and must relay findings as given
(it never assigns or changes a verdict, TRL or score).  Afterwards any ``[p.N]`` or
``[F#]`` tag that does not match what was actually in the prompt is removed.

If the uploaded file has already been deleted by the retention policy, the answer is
still grounded in the stored pipeline findings (the response says so).

This reuses the same retrieval layer as ClaimCheck (``evidence.SentenceIndex``), so
instruction-like sentences are already excluded from what the model sees.  Gemini is
required for this feature; without ``GEMINI_API_KEY`` it fails with a clear message
instead of falling back to a fake answer.  The key is never returned to the browser.
"""

from __future__ import annotations

import re
import threading
from collections import OrderedDict
from pathlib import Path

from .. import prompts
from . import chat_findings, config, evidence, ingest, llm
from .textutils import clip, strip_control_chars, word_tokens

NO_KEY_MESSAGE = (
    "Chat is unavailable: no Gemini API key is configured. Add GEMINI_API_KEY to your "
    ".env file and restart the app to ask questions about this paper."
)

MAX_QUESTION_CHARS = 1000
MAX_HISTORY_TURNS = 6
MAX_HISTORY_CHARS = 1200
RETRIEVED_PASSAGES = 8
ABSTRACT_PASSAGES = 4
CACHE_SIZE = 8

_CITATION = re.compile(r"\[p\.(\d+)\]")
_FINDING_CITATION = re.compile(r"\[F(\d+)\]")
_MISSING_PAPER_CODES = {"FILE_NOT_FOUND", "PAPER_UNAVAILABLE"}
NO_PAPER_TEXT = (
    "(The original paper text is no longer stored on the server. Answer only from the "
    "pipeline findings above and say that the paper's own passages are unavailable.)"
)
_ABSTRACT_SECTION = re.compile(r"abstract", re.I)

_CACHE: "OrderedDict[str, tuple[evidence.SentenceIndex, str]]" = OrderedDict()
_LOCK = threading.Lock()


class ChatError(RuntimeError):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def reset_cache() -> None:
    with _LOCK:
        _CACHE.clear()


def _load_index(job_id: str, path: Path, filename: str) -> tuple[evidence.SentenceIndex, str]:
    """Rebuild (and cache) the sentence index from the stored upload."""
    with _LOCK:
        if job_id in _CACHE:
            _CACHE.move_to_end(job_id)
            return _CACHE[job_id]

    try:
        document = ingest.ingest_file(path, filename)
    except ingest.IngestError as exc:
        raise ChatError(exc.code, exc.message, 409) from exc
    except OSError as exc:
        raise ChatError(
            "PAPER_UNAVAILABLE", "The uploaded paper is no longer available.", 410
        ) from exc

    sentences = ingest.build_sentence_index(document)
    if not sentences:
        raise ChatError("NO_SENTENCES", "No searchable text was found in this paper.", 409)

    entry = (evidence.SentenceIndex(sentences), document.title or filename)
    with _LOCK:
        _CACHE[job_id] = entry
        while len(_CACHE) > CACHE_SIZE:
            _CACHE.popitem(last=False)
    return entry


def _clean_history(history: list[dict] | None) -> list[dict]:
    turns: list[dict] = []
    for item in history or []:
        role = item.get("role") if isinstance(item, dict) else None
        content = item.get("content") if isinstance(item, dict) else None
        if role not in {"user", "assistant"} or not isinstance(content, str):
            continue
        content = clip(strip_control_chars(content), MAX_HISTORY_CHARS)
        if content:
            turns.append({"role": role, "content": content})
    return turns[-MAX_HISTORY_TURNS:]


def _retrieval_query(question: str, history: list[dict]) -> str:
    """Short follow-ups ("why?") borrow the previous user question for retrieval."""
    if len(word_tokens(question)) >= 6:
        return question
    previous = [turn["content"] for turn in history if turn["role"] == "user"]
    return f"{previous[-1]} {question}" if previous else question


def _select_passages(index: evidence.SentenceIndex, query: str, budget: int | None = None) -> list[dict]:
    chosen: list[dict] = []
    seen: set[int] = set()

    # The abstract gives the model a baseline so "what is this paper about?" works
    # even though TF-IDF retrieval alone would match few sentences.
    abstract = [
        sentence
        for sentence in index.sentences
        if _ABSTRACT_SECTION.search(sentence.get("section", ""))
    ][:ABSTRACT_PASSAGES]
    for sentence in abstract:
        chosen.append({**sentence, "relevance": 0.0})
        seen.add(int(sentence["id"]))

    for hit in index.retrieve(query, k=RETRIEVED_PASSAGES):
        if hit["relevance"] <= 0 or int(hit["id"]) in seen:
            continue
        chosen.append(hit)
        seen.add(int(hit["id"]))

    # Respect the shared prompt budget.
    budget = config.MAX_CONTEXT_CHARS if budget is None else budget
    kept: list[dict] = []
    for passage in chosen:
        cost = len(passage["text"]) + 16
        if cost > budget:
            break
        budget -= cost
        kept.append(passage)
    return kept


def _format_context(passages: list[dict]) -> str:
    lines = []
    for passage in passages:
        section = (passage.get("section") or "").strip()
        label = f"[p.{int(passage['page'])}]" + (f" ({section})" if section else "")
        lines.append(f"{label} {passage['text']}")
    return "\n".join(lines) if lines else "(no passages were retrieved)"


def _format_history(history: list[dict]) -> str:
    if not history:
        return "(none)"
    return "\n".join(
        f"{'User' if turn['role'] == 'user' else 'Assistant'}: {turn['content']}"
        for turn in history
    )


def _enforce_all(
    answer: str, allowed_pages: set[int], allowed_findings: set[str]
) -> tuple[str, set[int], set[str], int]:
    """Drop ``[p.N]`` / ``[F#]`` tags that do not match what was in the prompt."""
    cited_pages: set[int] = set()
    cited_findings: set[str] = set()
    removed = 0

    def check_page(match: re.Match[str]) -> str:
        nonlocal removed
        page = int(match.group(1))
        if page in allowed_pages:
            cited_pages.add(page)
            return match.group(0)
        removed += 1
        return ""

    def check_finding(match: re.Match[str]) -> str:
        nonlocal removed
        finding_id = f"F{int(match.group(1))}"
        if finding_id in allowed_findings:
            cited_findings.add(finding_id)
            return match.group(0)
        removed += 1
        return ""

    cleaned = _CITATION.sub(check_page, answer)
    cleaned = _FINDING_CITATION.sub(check_finding, cleaned)
    cleaned = re.sub(r"[ \t]+([.,;:])", r"\1", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip(), cited_pages, cited_findings, removed


def _enforce_citations(answer: str, allowed_pages: set[int]) -> tuple[str, set[int], int]:
    """Page-tag-only variant kept for callers that have no pipeline findings."""
    text, pages, _, removed = _enforce_all(answer, allowed_pages, set())
    return text, pages, removed


def answer(
    job_id: str,
    path: Path | None,
    filename: str,
    question: str,
    history: list[dict] | None = None,
    analysis: dict | None = None,
) -> dict:
    """Answer one question about the paper, or raise :class:`ChatError`.

    ``analysis`` is the finished job's result; it supplies the pipeline findings and
    keeps chat working after the uploaded file has been deleted.
    """
    if not llm.enabled():
        raise ChatError("CHAT_DISABLED", NO_KEY_MESSAGE, 503)

    question = clip(strip_control_chars(question or ""), MAX_QUESTION_CHARS).strip()
    if not question:
        raise ChatError("EMPTY_QUESTION", "Type a question first.", 400)

    turns = _clean_history(history)
    query = _retrieval_query(question, turns)

    all_findings = chat_findings.build_findings(analysis)
    index = None
    title = ((analysis or {}).get("doc") or {}).get("title") or filename
    try:
        if path is None:
            raise ChatError("PAPER_UNAVAILABLE", "The uploaded paper is no longer available.", 410)
        index, title = _load_index(job_id, path, filename)
    except ChatError as exc:
        # The retention policy may have removed the upload; the stored analysis can still answer.
        if not (all_findings and exc.code in _MISSING_PAPER_CODES):
            raise

    findings = chat_findings.select_findings(all_findings, query, chat_findings.findings_budget())
    used = sum(len(f["text"]) + len(f["label"]) + 12 for f in findings)
    passages = (
        _select_passages(index, query, budget=max(0, config.MAX_CONTEXT_CHARS - used))
        if index is not None
        else []
    )

    template = prompts.render(
        "chat",
        title=clip(title, 200),
        findings=chat_findings.format_findings(findings),
        context=_format_context(passages) if index is not None else NO_PAPER_TEXT,
        history=_format_history(turns),
        question=question,
    )
    try:
        raw = llm.generate(
            template["user"],
            system=template["system"],
            # Gemini 2.5 counts hidden "thinking" tokens against this limit.
            max_tokens=2048,
            temperature=0.2,
            timeout=config.GEMINI_CHAT_TIMEOUT,
        )
    except llm.LLMError as exc:
        if exc.code == "LLM_DISABLED":
            raise ChatError("CHAT_DISABLED", NO_KEY_MESSAGE, 503) from exc
        status = 429 if "rate limit" in exc.message.lower() else 502
        raise ChatError("CHAT_LLM_FAILED", f"{exc.message}. Please try again.", status) from exc

    allowed = {int(passage["page"]) for passage in passages}
    for finding in findings:  # a finding quotes evidence pages, so those tags are valid too
        allowed.update(int(page) for page in finding["pages"])
    text, cited_pages, cited_findings, removed = _enforce_all(
        raw, allowed, {finding["id"] for finding in findings}
    )
    if not text:
        raise ChatError("CHAT_LLM_FAILED", "Gemini returned an empty answer. Please try again.", 502)

    return {
        "answer": text,
        "sources": [
            {
                "id": int(passage["id"]),
                "page": int(passage["page"]),
                "section": passage.get("section", ""),
                "text": passage["text"],
                "relevance": passage.get("relevance", 0.0),
                "cited": int(passage["page"]) in cited_pages,
            }
            for passage in passages
        ],
        "findings": [
            {
                "id": finding["id"],
                "kind": finding["kind"],
                "label": finding["label"],
                "text": finding["text"],
                "pages": finding["pages"],
                "cited": finding["id"] in cited_findings,
            }
            for finding in findings
        ],
        "paper_text_available": index is not None,
        "model": config.GEMINI_MODEL,
        "removed_citations": removed,
    }
