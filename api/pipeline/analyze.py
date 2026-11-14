"""End-to-end analysis orchestration.

    ingest -> sentence index -> classical features -> tokenizer study -> NER
    -> summary -> claims -> retrieval + NLI -> reproducibility -> TRL -> report

Every stage records latency, every model failure becomes a warning, and the output
is one JSON object (the ``PaperAnalysis`` contract in documentation/Architecture.md).
This module is intentionally free of FastAPI imports so it can be tested with the
standard library alone.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from . import (
    PIPELINE_VERSION,
    claims as claims_stage,
    classical,
    config,
    evidence,
    gazetteer,
    ingest,
    llm,
    models,
    ner,
    report as report_stage,
    repro,
    stats as stats_stage,
    summarize as summarize_stage,
    tokenizer_study,
    trl as trl_stage,
)
from .textutils import detect_instruction_lines, word_tokens

Progress = Callable[[int, str], None]


def _elapsed(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        clean = (item or "").strip()
        if clean and clean not in seen:
            seen.add(clean)
            output.append(clean)
    return output


def _tokenizer_terms(entities: list[dict], text: str) -> list[str]:
    seen: set[str] = set()
    terms: list[str] = []
    for entity in sorted(
        entities,
        key=lambda item: len(item.get("canonical") or item.get("text", "")),
        reverse=True,
    ):
        term = (entity.get("canonical") or entity.get("text") or "").strip()
        if len(term) >= 4 and term.lower() not in seen:
            seen.add(term.lower())
            terms.append(term)
        if len(terms) >= 6:
            break
    if not terms:
        words = sorted(
            {word for word in word_tokens(text) if len(word) >= 9},
            key=len,
            reverse=True,
        )
        terms = words[:6]
    return terms


def _scan_injection(document: ingest.Document) -> list[dict]:
    findings: list[dict] = []
    seen: set[str] = set()
    for page in document.pages:
        for finding in detect_instruction_lines(page.text):
            key = finding["line"].lower()
            if key in seen:
                continue
            seen.add(key)
            findings.append({**finding, "page": page.number})
    return findings


def analyze_document(
    path: str | Path,
    filename: str | None = None,
    progress: Progress | None = None,
    *,
    use_llm: bool | None = None,
    use_nli: bool = True,
) -> dict:
    started = time.perf_counter()
    timings: dict[str, int] = {}
    warnings: list[str] = []

    # --- Stage 1: ingest -----------------------------------------------------
    t0 = time.perf_counter()
    document = ingest.ingest_file(path, filename)
    timings["ingest_ms"] = _elapsed(t0)
    if progress:
        progress(8, "Document read")

    if document.meta.get("truncated"):
        warnings.append(
            f"Only the first {config.MAX_PAGES} pages were analysed "
            f"(the PDF has {document.meta.get('page_count_total', 'more')})."
        )

    sentences = ingest.build_sentence_index(document)
    if not sentences:
        raise ingest.IngestError(
            "NO_SENTENCES", "No sentence-like text was extracted from the document."
        )

    injections = _scan_injection(document)
    document.meta["injection_flags"] = len(injections)
    if injections:
        pages = sorted({finding["page"] for finding in injections})
        warnings.append(
            "Instruction-like text was detected on page(s) "
            + ", ".join(str(page) for page in pages)
            + " and excluded from prompts/evidence (prompt-injection defense)."
        )

    # --- Stage 2: classical tier --------------------------------------------
    t0 = time.perf_counter()
    gaz_entities = gazetteer.find_entities(document)
    facts = classical.extract_regex_facts(document)
    key_terms, tfidf_backend = classical.extract_key_terms(document, 12)
    pos = classical.pos_features(sentences)
    stats = stats_stage.compute_stats(
        document, sentences, technical_term_hits=len(gaz_entities), pos=pos
    )
    timings["classical_ms"] = _elapsed(t0)
    if progress:
        progress(20, "Classical features")

    if not pos.get("available"):
        warnings.append(
            "spaCy POS model unavailable - POS features use neutral defaults. "
            f"({pos.get('reason', 'not installed')})"
        )
    if pos.get("available") is False and tfidf_backend == "pure-python":
        warnings.append(
            "Classical tier is running in pure-Python fallback mode (no scikit-learn); "
            "TF-IDF retrieval is still active."
        )

    # --- Stage 3: tokenizer comparison (Practical 1) ------------------------
    t0 = time.perf_counter()
    if config.TOKENIZER_STUDY_ENABLED:
        tokenization = tokenizer_study.study(
            document.full_text, _tokenizer_terms(gaz_entities, document.full_text)
        )
        if not any(
            item.get("available") and item.get("model") != "builtin"
            for item in tokenization.get("tokenizers", [])
        ):
            warnings.append(
                "Hugging Face tokenizers unavailable - the table shows only the "
                "classical whitespace/punctuation baseline."
            )
    else:
        tokenization = {
            "tokenizers": [],
            "term_splits": [],
            "note": "Tokenizer study disabled (P2R_TOKENIZER_STUDY=0).",
        }
    timings["tokenizer_ms"] = _elapsed(t0)
    if progress:
        progress(28, "Tokenizer study")

    # --- Stage 4: NER --------------------------------------------------------
    t0 = time.perf_counter()
    entities, key_concepts, ner_warnings = ner.extract_entities(document, gaz_entities)
    warnings.extend(ner_warnings)
    timings["ner_ms"] = _elapsed(t0)
    if progress:
        progress(40, "Named entities")

    # --- Stage 5: summary ----------------------------------------------------
    t0 = time.perf_counter()
    summary, summary_warnings = summarize_stage.summarize(document)
    warnings.extend(summary_warnings)
    timings["summary_ms"] = _elapsed(t0)
    if progress:
        progress(58, "Summarising")

    # --- Stage 6: claims -----------------------------------------------------
    t0 = time.perf_counter()
    raw_claims, claim_warnings = claims_stage.extract_claims(
        document, sentences, use_llm=use_llm
    )
    warnings.extend(claim_warnings)
    timings["claims_ms"] = _elapsed(t0)
    if progress:
        progress(70, "Extracting claims")

    # --- Stages 7-8: retrieval + NLI ----------------------------------------
    t0 = time.perf_counter()
    verified_claims, evidence_warnings = evidence.verify_claims(
        raw_claims, sentences, use_nli=use_nli
    )
    warnings.extend(evidence_warnings)
    timings["evidence_ms"] = _elapsed(t0)
    if progress:
        progress(82, "Checking evidence")

    # --- Stage 9: reproducibility -------------------------------------------
    t0 = time.perf_counter()
    reproducibility = repro.assess_reproducibility(document, entities, facts)
    timings["repro_ms"] = _elapsed(t0)
    if progress:
        progress(90, "Reproducibility checklist")

    # --- Stage 10: TRL -------------------------------------------------------
    t0 = time.perf_counter()
    readiness = trl_stage.assess_trl(
        document, verified_claims, reproducibility, use_nli=use_nli
    )
    timings["trl_ms"] = _elapsed(t0)
    if progress:
        progress(94, "Readiness rubric")

    warnings.append(
        "No GEMINI_API_KEY set - claims use the heuristic extractor and the report "
        "uses local templates. The full pipeline still runs."
        if not llm.enabled()
        else "Gemini key detected; claim extraction may use the optional API, with local fallback."
    )
    if config.SEMANTIC:
        warnings.append(
            "SEMANTIC=1 was requested, but this MVP uses TF-IDF retrieval; "
            "semantic reranking is future work."
        )
    if document.meta.get("references", 0) == 0:
        warnings.append("No reference list was detected; citation counts may be incomplete.")
    if stats["words"] < 250:
        warnings.append("Very little text was extracted; results may be unreliable.")

    # --- Stage 11: report ----------------------------------------------------
    t0 = time.perf_counter()
    partial = {
        "doc": {
            "filename": document.filename,
            "pages": len(document.pages),
            "title": document.title,
            "words": stats["words"],
            "source": document.meta.get("source", "text"),
            "truncated": bool(document.meta.get("truncated")),
            "page_count_total": document.meta.get("page_count_total", len(document.pages)),
            "injection_flags": int(document.meta.get("injection_flags", 0)),
        },
        "stats": stats,
        "summary": summary,
        "entities": entities,
        "key_concepts": key_concepts,
        "claims": verified_claims,
        "reproducibility": reproducibility,
        "trl": readiness,
        "key_terms": key_terms,
        "signals": facts,
        "tokenization": tokenization,
        "warnings": _dedupe(warnings),
        "pipeline_version": PIPELINE_VERSION,
    }
    report_payload = partial if (
        use_llm is not False and config.LLM_REPORT_ENABLED and llm.enabled()
    ) else None
    executive_report, report_warnings = report_stage.build_report(
        document,
        stats,
        summary,
        key_concepts,
        verified_claims,
        reproducibility,
        readiness,
        analysis_payload=report_payload,
    )
    warnings.extend(report_warnings)
    timings["report_ms"] = _elapsed(t0)
    timings["total_ms"] = _elapsed(started)
    if progress:
        progress(100, "Report ready")

    result = {
        "status": "done",
        "doc": partial["doc"],
        "stats": stats,
        "summary": summary,
        "entities": entities,
        "key_concepts": key_concepts,
        "claims": verified_claims,
        "reproducibility": reproducibility,
        "trl": readiness,
        "report": executive_report,
        "tokenization": tokenization,
        "key_terms": key_terms,
        "signals": facts,
        "timings": timings,
        "warnings": _dedupe(warnings),
        "pipeline_version": PIPELINE_VERSION,
        "engine": {
            "tfidf": tfidf_backend,
            "pos": bool(pos.get("available")),
            "tokenizers": sum(
                1 for item in tokenization.get("tokenizers", []) if item.get("available")
            ),
            "gemini": llm.enabled(),
        },
    }
    return result
