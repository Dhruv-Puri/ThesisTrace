"""Single source of truth for configuration.

Nothing here writes outside the project unless THESISTRACE_DATA_DIR explicitly points
elsewhere (Docker sets it to the mounted volume).  Model names are never hardcoded
in pipeline stages - change a model here and every stage follows.
"""

from __future__ import annotations

import os
from pathlib import Path

# repo root: api/pipeline/config.py -> api/pipeline -> api -> repo
ROOT = Path(__file__).resolve().parents[2]


_TRUE = {"1", "true", "yes", "on"}


def _flag(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in _TRUE


def _env(name: str, default: str = "") -> str:
    """Read ``THESISTRACE_<name>``; fall back to the legacy ``P2R_<name>`` (pre-rename).

    Existing ``.env`` files and Docker setups that still use the old ``P2R_`` prefix keep
    working; the new prefix wins when both are set.
    """
    value = os.getenv(f"THESISTRACE_{name}")
    if value is None:
        value = os.getenv(f"P2R_{name}")
    return value if value is not None else default


def _env_flag(name: str, default: str = "0") -> bool:
    return _env(name, default).strip().lower() in _TRUE


# ---------------------------------------------------------------------------
# Runtime switches
# ---------------------------------------------------------------------------
LOW_RAM = _flag("LOW_RAM")                 # small models / gazetteer-only NER
SEMANTIC = _flag("SEMANTIC")               # optional embedding rerank
TOKENIZER_STUDY_ENABLED = _env_flag("TOKENIZER_STUDY", "1")
LLM_CLAIMS_ENABLED = _env_flag("LLM_CLAIMS", "1")
LLM_REPORT_ENABLED = _env_flag("LLM_REPORT", "0")

# Gemini is optional.  With no key the whole app still works locally.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
GEMINI_TIMEOUT = float(os.getenv("GEMINI_TIMEOUT", "8"))
# Chat answers are longer than claim extraction, so they get a longer timeout.
GEMINI_CHAT_TIMEOUT = float(os.getenv("GEMINI_CHAT_TIMEOUT", "30"))

# ---------------------------------------------------------------------------
# Storage - project-local by default, so deleting the folder removes everything
# ---------------------------------------------------------------------------
DATA_DIR = Path(_env("DATA_DIR", str(ROOT / ".data"))).expanduser()
UPLOAD_DIR = DATA_DIR / "uploads"
MAX_UPLOAD_MB = int(_env("MAX_UPLOAD_MB", "30"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_PAGES = int(_env("MAX_PAGES", "60"))

# Keep Hugging Face downloads inside the project even in local (non-Docker) runs.
# Docker already sets HF_HOME=/models/hf; setdefault respects that.
os.environ.setdefault("HF_HOME", str(DATA_DIR / "hf"))

# ---------------------------------------------------------------------------
# Models (CPU-friendly; see documentation/Feasibility-Analysis.md section 3)
# ---------------------------------------------------------------------------
NER_MODEL = "" if LOW_RAM else _env(
    "NER_MODEL",
    "elastic/distilbert-base-uncased-finetuned-conll03-english",
)
NLI_MODEL = _env(
    "NLI_MODEL",
    "distilbert-base-uncased-mnli" if LOW_RAM else "cross-encoder/nli-deberta-v3-small",
)
SUMMARIZER_MODEL = "google/flan-t5-small" if LOW_RAM else "sshleifer/distilbart-cnn-12-6"
ELI5_MODEL = "google/flan-t5-small"

TOKENIZER_MODELS = [
    ("BPE (GPT-2)", "gpt2"),
    ("WordPiece (BERT)", "bert-base-uncased"),
    ("SentencePiece (T5)", "google/flan-t5-small"),
]

# ---------------------------------------------------------------------------
# Pipeline limits / thresholds
# ---------------------------------------------------------------------------
MAX_NER_PAGES = 15
MAX_EVIDENCE_SENTENCES = 1400
RETRIEVAL_K = 5
RETRIEVAL_FLOOR = 0.05          # below this nothing is sent to the NLI model
NLI_MAX_CANDIDATES = 3
MAX_CLAIMS = 8
MAX_ENTITIES = 90
MAX_CONTEXT_CHARS = 9000        # context handed to any LLM prompt

# Verdict thresholds (tuned on the gold set described in documentation/Evaluation.md)
SUPPORTED_ENTAILMENT = 0.60
SUPPORTED_RELEVANCE = 0.25
PARTIAL_ENTAILMENT = 0.40
PARTIAL_RELEVANCE = 0.12
CONTRADICTION_SCORE = 0.65


def ensure_dirs() -> None:
    """Create the local data directories (the only writes the API itself makes)."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def public_config() -> dict:
    """Configuration safe to send to the browser (never includes the API key)."""
    return {
        "gemini_enabled": bool(GEMINI_API_KEY),
        "gemini_model": GEMINI_MODEL if GEMINI_API_KEY else None,
        "low_ram": LOW_RAM,
        "semantic": SEMANTIC,
        "max_upload_mb": MAX_UPLOAD_MB,
        "tokenizer_study": TOKENIZER_STUDY_ENABLED,
    }
