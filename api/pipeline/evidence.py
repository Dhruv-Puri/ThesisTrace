"""Stages 7-8 - evidence retrieval and NLI verdicts (the RAG core).

claim -> TF-IDF retrieval over sentence-sized passages -> NLI cross-encoder
      -> supported / partially_supported / insufficient + cited evidence.

Two deliberate honesty rules:
1. A claim's *own sentence* is excluded from retrieval.  Otherwise the claim would
   "prove" itself and every verdict would be supported.
2. If retrieval finds nothing above the score floor, no NLI call is made and the
   verdict is ``insufficient`` - not "false".  Not asking the model is a feature.

Syllabus: feature-based models / TF-IDF (Stage 7), text classification and semantic
analysis (Stage 8), RAG grounding (CO5), hallucination evaluation (CO4).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from . import PIPELINE_VERSION, config, models
from .classical import TfidfIndex
from .textutils import detect_instruction_lines, numbers_in

_SKIP_SECTION = re.compile(r"(reference|bibliograph|acknowledg|appendix)", re.I)
_HEDGE = re.compile(r"\b(?:up to|may|might|can|could|potential(?:ly)?|approximately|about)\b", re.I)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _thresholds() -> dict:
    """The exact decision thresholds this verdict was produced with."""
    return {
        "supported_entailment": config.SUPPORTED_ENTAILMENT,
        "supported_relevance": config.SUPPORTED_RELEVANCE,
        "partial_entailment": config.PARTIAL_ENTAILMENT,
        "partial_relevance": config.PARTIAL_RELEVANCE,
        "contradiction": config.CONTRADICTION_SCORE,
    }


def _receipt(
    *,
    method: str,
    verdict: str,
    confidence: float,
    candidates: list[dict],
    ranked: list[dict] | None = None,
    nli: dict | None = None,
    abstain_reason: str = "",
) -> dict:
    """A machine-readable receipt behind one verdict (the Trust Ledger).

    The receipt is what separates a citation from an auditable judgement: it stores
    what was retrieved, which thresholds were applied, and whether a model was asked
    at all.  It contains no document text, so it is safe to export.
    """
    ordered = ranked if ranked is not None else candidates
    return {
        "receipt_version": 1,
        "pipeline_version": PIPELINE_VERSION,
        "checked_at": _utc_now(),
        "method": method,
        "verdict": verdict,
        "confidence": confidence,
        "retrieval": {
            "engine": "tf-idf",
            "k": config.RETRIEVAL_K,
            "floor": config.RETRIEVAL_FLOOR,
            "returned": len(candidates),
            "candidates": [
                {
                    "sentence_id": int(item["id"]),
                    "page": int(item["page"]),
                    "score": float(item["relevance"]),
                }
                for item in ordered[: config.RETRIEVAL_K]
            ],
        },
        "nli": nli,
        "abstained": bool(abstain_reason),
        "reason": abstain_reason,
    }


def _nli_receipt(best: dict, entailment: float, contradiction: float) -> dict:
    return {
        "model": config.NLI_MODEL,
        "max_candidates": config.NLI_MAX_CANDIDATES,
        "thresholds": _thresholds(),
        "best_sentence_id": int(best["id"]),
        "best_relevance": float(best["relevance"]),
        "entailment": round(float(entailment), 4),
        "contradiction": round(float(contradiction), 4),
        "margin": round(float(entailment) - float(contradiction), 4),
    }


class SentenceIndex:
    def __init__(self, sentences: list[dict]):
        usable = []
        for sentence in sentences:
            text = sentence["text"].strip()
            if not (20 <= len(text) <= 900):
                continue
            if _SKIP_SECTION.search(sentence.get("section", "")):
                continue
            if detect_instruction_lines(text):
                # Hostile sentence: never use it as evidence or prompt context.
                continue
            usable.append(sentence)
        self.sentences = usable
        self._tfidf = TfidfIndex([sentence["text"] for sentence in usable])

    def retrieve(
        self,
        query: str,
        k: int = config.RETRIEVAL_K,
        exclude_ids: set[int] | None = None,
    ) -> list[dict]:
        if not self.sentences:
            return []
        scores = self._tfidf.scores(query)
        exclude = exclude_ids or set()
        ranked = sorted(
            (
                (float(score), index)
                for index, score in enumerate(scores)
                if index < len(self.sentences)
                and int(self.sentences[index]["id"]) not in exclude
            ),
            reverse=True,
        )
        results = []
        for score, index in ranked[:k]:
            sentence = self.sentences[index]
            results.append({**sentence, "relevance": round(score, 3)})
        return results


def _normalise_label(label: str) -> str:
    value = str(label or "").lower()
    if "entail" in value:
        return "entailment"
    if "contradict" in value:
        return "contradiction"
    if "neutral" in value:
        return "neutral"
    return ""


def _label_hint(pipe, raw_label: str) -> str:
    mapped = _normalise_label(raw_label)
    if mapped:
        return mapped
    # Some checkpoints expose LABEL_0..2.  Use the model config if it is semantic.
    try:
        id2label = getattr(pipe.model.config, "id2label", {}) or {}
    except Exception:
        id2label = {}
    match = re.fullmatch(r"LABEL_(\d+)", str(raw_label), re.IGNORECASE)
    if match:
        mapped = _normalise_label(str(id2label.get(int(match.group(1)), "")))
        if mapped:
            return mapped
    return ""


def _nli_scores(pipe, claim: str, passage: str) -> dict[str, float]:
    scores = {"entailment": 0.0, "neutral": 0.0, "contradiction": 0.0}
    try:
        output = pipe(
            {"text": passage, "text_pair": claim},
            top_k=None,
            truncation=True,
        )
    except TypeError:
        # Older transformers: top_k must be a constructor argument.
        output = pipe({"text": passage, "text_pair": claim}, truncation=True)
    except Exception:
        return scores

    if isinstance(output, dict):
        output = [output]
    elif isinstance(output, list) and output and isinstance(output[0], list):
        output = output[0]
    for item in output or []:
        if not isinstance(item, dict):
            continue
        label = _label_hint(pipe, item.get("label", ""))
        if label in scores:
            scores[label] = max(scores[label], float(item.get("score", 0.0)))
    return scores


def _partial_note(claim: str, passage: str, page: int) -> str:
    claim_numbers = {value.rstrip("%") for value in numbers_in(claim)}
    passage_numbers = {value.rstrip("%") for value in numbers_in(passage)}
    missing = sorted(claim_numbers - passage_numbers)
    if missing:
        return (
            f"The evidence [p.{page}] does not report {', '.join(missing)}; "
            "the claim is broader than the measured result."
        )
    if _HEDGE.search(claim) and not _HEDGE.search(passage):
        return (
            f"The claim is hedged, while the evidence [p.{page}] reports a single "
            "measured condition; the scope is not identical."
        )
    return (
        f"The passage [p.{page}] is topically related but does not entail the "
        "complete claim as written."
    )


def _lexical_verdict(claim: str, candidates: list[dict]) -> tuple[str, float, dict | None]:
    from .textutils import content_tokens

    claim_tokens = content_tokens(claim)
    if not claim_tokens:
        return "insufficient", 0.2, None
    claim_numbers = {value.rstrip("%") for value in numbers_in(claim)}

    best = None
    best_overlap = 0.0
    for candidate in candidates:
        passage_tokens = content_tokens(candidate["text"])
        if not passage_tokens:
            continue
        overlap = len(claim_tokens & passage_tokens) / len(claim_tokens)
        passage_numbers = {value.rstrip("%") for value in numbers_in(candidate["text"])}
        numbers_ok = claim_numbers.issubset(passage_numbers) if claim_numbers else True
        score = overlap + (0.12 if numbers_ok else -0.15) + candidate["relevance"] * 0.2
        if score > best_overlap:
            best_overlap = score
            best = {**candidate, "overlap": overlap, "numbers_ok": numbers_ok}

    if best is None:
        return "insufficient", 0.2, None
    overlap = float(best["overlap"])
    if overlap >= 0.55 and best["numbers_ok"]:
        return "supported", round(min(0.82, 0.45 + overlap * 0.45), 2), best
    if overlap >= 0.28:
        return "partially_supported", round(min(0.72, 0.35 + overlap * 0.4), 2), best
    return "insufficient", 0.3, best


def verify_claims(
    claims: list[dict],
    sentences: list[dict],
    use_nli: bool = True,
) -> tuple[list[dict], list[str]]:
    warnings: list[str] = []
    index = SentenceIndex(sentences)
    pipe = models.get_pipeline("text-classification", config.NLI_MODEL) if use_nli else None
    if use_nli:
        if pipe is None:
            detail = next(iter(models.model_status()["errors"].values()), "model not loaded")
            warnings.append(
                "NLI model unavailable - verdicts use a conservative lexical-overlap "
                f"fallback. ({detail})"
            )
        else:
            warnings.append("NLI verdicts computed locally with " + config.NLI_MODEL + ".")

    verified: list[dict] = []
    for claim in claims:
        exclude = set()
        sentence_id = claim.get("sentence_id")
        if isinstance(sentence_id, int):
            exclude.add(sentence_id)
        candidates = index.retrieve(claim["text"], exclude_ids=exclude)

        if not candidates or candidates[0]["relevance"] < config.RETRIEVAL_FLOOR:
            searched = candidates[:2]
            note = (
                "No passage cleared the retrieval score floor "
                f"({config.RETRIEVAL_FLOOR}). The claim is marked insufficient evidence, "
                "not false; nothing was sent to the NLI model."
            )
            verified.append(
                {
                    **claim,
                    "verdict": "insufficient",
                    "confidence": 0.25,
                    "evidence": [
                        {
                            "page": item["page"],
                            "sentence_id": item["id"],
                            "text": item["text"][:600],
                            "relevance": item["relevance"],
                            "nli": "not_checked",
                            "nli_score": 0.0,
                        }
                        for item in searched
                    ],
                    "note": note,
                    "source": "retrieval-only",
                    "audit": _receipt(
                        method="retrieval-only",
                        verdict="insufficient",
                        confidence=0.25,
                        candidates=searched,
                        ranked=searched,
                        abstain_reason=note,
                    ),
                }
            )
            continue

        if pipe is None:
            verdict, confidence, best = _lexical_verdict(claim["text"], candidates)
            best_id = best.get("id") if best else None
            evidence = []
            for item in candidates[:3]:
                label = "entailment" if item["id"] == best_id and verdict == "supported" else "neutral"
                evidence.append(
                    {
                        "page": item["page"],
                        "sentence_id": item["id"],
                        "text": item["text"][:600],
                        "relevance": item["relevance"],
                        "nli": label,
                        "nli_score": 0.0,
                    }
                )
            note = "" if verdict == "supported" else (
                _partial_note(claim["text"], best["text"], best["page"])
                if best else "No passage could be compared with the claim."
            )
            verified.append(
                {
                    **claim,
                    "verdict": verdict,
                    "confidence": confidence,
                    "evidence": evidence,
                    "note": note,
                    "source": "lexical-fallback",
                    "audit": _receipt(
                        method="lexical-fallback",
                        verdict=verdict,
                        confidence=confidence,
                        candidates=candidates,
                        ranked=candidates[:3],
                        abstain_reason="NLI model unavailable; conservative lexical-overlap fallback used.",
                    ),
                }
            )
            continue

        classified = []
        for candidate in candidates[: config.NLI_MAX_CANDIDATES]:
            scores = _nli_scores(pipe, claim["text"], candidate["text"])
            if not any(scores.values()):
                continue
            choice = (
                scores["entailment"] * 0.6
                + candidate["relevance"] * 0.4
                - scores["contradiction"] * 0.1
            )
            classified.append({**candidate, "scores": scores, "choice": choice})

        if not classified:
            warnings.append(
                "NLI produced no readable labels for a claim; lexical fallback used for it."
            )
            verdict, confidence, best = _lexical_verdict(claim["text"], candidates)
            verified.append(
                {
                    **claim,
                    "verdict": verdict,
                    "confidence": confidence,
                    "evidence": [
                        {
                            "page": item["page"],
                            "sentence_id": item["id"],
                            "text": item["text"][:600],
                            "relevance": item["relevance"],
                            "nli": "neutral",
                            "nli_score": 0.0,
                        }
                        for item in candidates[:3]
                    ],
                    "note": (
                        "NLI labels could not be interpreted; the conservative lexical "
                        "fallback classified this claim."
                    ),
                    "source": "lexical-fallback",
                    "audit": _receipt(
                        method="lexical-fallback",
                        verdict=verdict,
                        confidence=confidence,
                        candidates=candidates,
                        ranked=candidates[:3],
                        abstain_reason="NLI labels could not be interpreted; lexical fallback used.",
                    ),
                }
            )
            continue

        classified.sort(key=lambda item: item["choice"], reverse=True)
        best = classified[0]
        best_rel = float(best["relevance"])
        entailment = max(item["scores"]["entailment"] for item in classified)
        contradiction = max(item["scores"]["contradiction"] for item in classified)

        if (
            contradiction >= config.CONTRADICTION_SCORE
            and contradiction > entailment
            and best_rel >= 0.15
        ):
            verdict = "insufficient"
            confidence = round(min(0.6, 0.3 + contradiction * 0.3), 2)
            note = (
                f"The closest passage [p.{best['page']}] appears to contradict the claim; "
                "the paper does not support it as stated."
            )
        elif entailment >= config.SUPPORTED_ENTAILMENT and best_rel >= config.SUPPORTED_RELEVANCE:
            verdict = "supported"
            confidence = round(
                min(0.99, 0.60 * entailment + 0.40 * min(1.0, best_rel / 0.60)), 2
            )
            note = ""
        elif entailment >= config.PARTIAL_ENTAILMENT and best_rel >= config.PARTIAL_RELEVANCE:
            verdict = "partially_supported"
            confidence = round(min(0.8, 0.35 + 0.45 * entailment), 2)
            note = _partial_note(claim["text"], best["text"], best["page"])
        else:
            verdict = "insufficient"
            confidence = 0.3
            note = (
                f"The retrieval step found related text [p.{best['page']}], but the NLI "
                "model did not find entailment; the claim is unverified rather than false."
            )

        evidence = [
            {
                "page": item["page"],
                "sentence_id": item["id"],
                "text": item["text"][:600],
                "relevance": item["relevance"],
                "nli": max(item["scores"], key=item["scores"].get),
                "nli_score": round(max(item["scores"].values()), 3),
            }
            for item in classified[:3]
        ]
        verified.append(
            {
                **claim,
                "verdict": verdict,
                "confidence": confidence,
                "evidence": evidence,
                "note": note,
                "source": "nli",
                "audit": _receipt(
                    method="nli",
                    verdict=verdict,
                    confidence=confidence,
                    candidates=classified,
                    ranked=classified,
                    nli=_nli_receipt(best, entailment, contradiction),
                    abstain_reason=note if verdict != "supported" else "",
                ),
            }
        )

    return verified, warnings
