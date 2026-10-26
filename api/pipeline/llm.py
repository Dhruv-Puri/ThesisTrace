"""Optional Gemini layer (CO2/CO3/CO5).

Uses the REST endpoint directly through ``urllib`` so the project needs no extra
SDK.  If the key is absent, or the network/quota fails, callers fall back to local
templates and heuristics.  The key is never logged or returned to the browser.

Model-agnostic note: prompt files contain no provider-specific syntax, so the same
templates can be sent to a local instruction model by swapping this adapter.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from urllib.parse import quote

from . import config
from .textutils import clip

LAST_ERROR = ""


class LLMError(RuntimeError):
    def __init__(self, message: str, code: str = "LLM_ERROR"):
        super().__init__(message)
        self.code = code
        self.message = message


def enabled() -> bool:
    return bool(config.GEMINI_API_KEY)


def status() -> dict:
    return {
        "enabled": enabled(),
        "model": config.GEMINI_MODEL if enabled() else None,
        "last_error": LAST_ERROR,
    }


def generate(
    prompt: str,
    system: str = "",
    *,
    max_tokens: int = 700,
    temperature: float = 0.2,
    model: str | None = None,
    timeout: float | None = None,
) -> str:
    """Return generated text or raise :class:`LLMError`."""
    global LAST_ERROR

    if not config.GEMINI_API_KEY:
        LAST_ERROR = "GEMINI_API_KEY is not set"
        raise LLMError(LAST_ERROR, "LLM_DISABLED")
    if not (prompt or "").strip():
        raise LLMError("Empty prompt", "LLM_EMPTY_PROMPT")

    chosen_model = model or config.GEMINI_MODEL
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + quote(chosen_model, safe="")
        + ":generateContent"
    )
    body: dict = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": max(0.0, min(1.0, float(temperature))),
            "maxOutputTokens": max(32, min(4096, int(max_tokens))),
        },
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}

    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": config.GEMINI_API_KEY,
        },
    )

    try:
        with urllib.request.urlopen(
            request, timeout=timeout or config.GEMINI_TIMEOUT
        ) as response:
            payload = json.loads(response.read(2_000_000).decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        code = int(exc.code)
        if code == 429:
            message = "Gemini free-tier rate limit reached (HTTP 429)"
        elif code in {401, 403}:
            message = "Gemini rejected the API key"
        elif code == 400:
            message = "Gemini rejected the request (HTTP 400)"
        elif code >= 500:
            message = "Gemini service error"
        else:
            message = f"Gemini request failed (HTTP {code})"
        LAST_ERROR = message
        raise LLMError(message, "LLM_HTTP_ERROR") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        LAST_ERROR = "Gemini request timed out or the network is unavailable"
        raise LLMError(LAST_ERROR, "LLM_NETWORK") from None
    except ValueError:
        LAST_ERROR = "Gemini returned invalid JSON"
        raise LLMError(LAST_ERROR, "LLM_BAD_RESPONSE") from None

    feedback = payload.get("promptFeedback") or {}
    if feedback.get("blockReason"):
        LAST_ERROR = f"Gemini blocked the prompt ({feedback['blockReason']})"
        raise LLMError(LAST_ERROR, "LLM_BLOCKED")

    try:
        candidates = payload.get("candidates") or []
        text = "".join(
            part.get("text", "")
            for part in candidates[0]["content"]["parts"]
            if isinstance(part, dict)
        )
    except (KeyError, IndexError, TypeError):
        LAST_ERROR = "Gemini response had no text"
        raise LLMError(LAST_ERROR, "LLM_EMPTY_RESPONSE") from None

    text = clip(text, 20_000)
    if not text.strip():
        LAST_ERROR = "Gemini response had no text"
        raise LLMError(LAST_ERROR, "LLM_EMPTY_RESPONSE")
    LAST_ERROR = ""
    return text
