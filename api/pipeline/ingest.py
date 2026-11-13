"""Stage 1 - document ingest.

PDF (PyMuPDF) or plain text -> pages with stable page numbers -> detected sections
-> a sentence index used by every later stage.  Page numbers are preserved because
*every* output of this project must be citable (``[p.N]``).

Syllabus link: Introduction to NLP (pipelines, preprocessing), Word Level (regex for
headings/references), and the corpus-construction idea behind the evaluation set.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import config
from .textutils import clip, normalize_for_match, normalize_ws, split_sentences, strip_control_chars


class IngestError(RuntimeError):
    """A user-fixable ingest failure (better than a stack trace in the UI)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class Page:
    number: int
    text: str


@dataclass
class Section:
    heading: str
    text: str
    page: int


@dataclass
class Document:
    filename: str
    title: str
    pages: list[Page]
    sections: list[Section]
    meta: dict = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        return "\n\n".join(page.text for page in self.pages)


_NAMED_SECTIONS = {
    "abstract", "introduction", "related work", "related works", "background",
    "motivation", "problem statement", "method", "methods", "methodology",
    "approach", "proposed method", "proposed approach", "materials and methods",
    "experimental setup", "experimental setup and results", "experiments",
    "experiment", "evaluation", "results", "results and discussion",
    "results and analysis", "analysis", "discussion", "limitations",
    "conclusion", "conclusions", "concluding remarks", "future work",
    "references", "bibliography", "acknowledgements", "acknowledgments",
    "appendix", "data availability", "availability of data", "supplementary material",
}

_NAMED_RE = re.compile(
    r"^(?:(?:\d+(?:\.\d+)*|[IVX]+)\.?\s*)?("
    + "|".join(re.escape(name) for name in sorted(_NAMED_SECTIONS, key=len, reverse=True))
    + r")\s*:?\s*$",
    re.IGNORECASE,
)
_NAMED_INLINE_RE = re.compile(
    r"^(?:(?:\d+(?:\.\d+)*|[IVX]+)\.?\s*)?("
    + "|".join(re.escape(name) for name in sorted(_NAMED_SECTIONS, key=len, reverse=True))
    + r")\s*[:\-—]\s*(.+)$",
    re.IGNORECASE,
)
_NUMBERED_RE = re.compile(r"^\d{1,2}(?:\.\d{1,2}){0,2}\.?\s+[A-Z][A-Za-z0-9 ,:&/\-]{2,70}$")

_TITLE_SKIP = re.compile(
    r"(arxiv|doi|preprint|proceedings|conference|journal|volume|issue|issn|"
    r"copyright|under review|submitted|accepted|published|www\.|https?://|@|"
    # Licence/attribution banners some publishers stamp above the real title,
    # e.g. arXiv reprints of corporate blog posts: "Provided proper attribution
    # is provided, Google hereby grants permission to reproduce the tables...".
    r"hereby grants|permission to reproduce|all rights reserved|"
    r"attribution is provided|licen[cs]e)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------

def _clean_page(raw: str) -> str:
    text = (raw or "").replace("\r\n", "\n").replace("\r", "\n")
    text = strip_control_chars(text)
    # Join hyphenated line breaks, keeping the hyphen: "energy-\nconsumption"
    # becomes "energy-consumption" (a dictionary check for removing the hyphen is
    # deliberately out of scope; keeping it is safer for technical terms).
    text = re.sub(r"(?<=\w)-[ \t]*\n[ \t]*(?=[a-z])", "-", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _remove_running_lines(raw_pages: list[str]) -> tuple[list[str], int]:
    """Drop headers/footers repeated on many pages and bare page numbers."""
    if len(raw_pages) < 3:
        return [_clean_page(page) for page in raw_pages], 0

    threshold = max(3, int(0.45 * len(raw_pages)))
    counts: dict[str, int] = {}
    for raw in raw_pages:
        seen = {
            line.strip()
            for line in raw.splitlines()
            if 3 <= len(line.strip()) <= 100
        }
        for line in seen:
            counts[line] = counts.get(line, 0) + 1

    repeated = {
        line for line, count in counts.items()
        if count >= threshold and not _looks_like_heading(line)
    }

    cleaned: list[str] = []
    removed = 0
    for raw in raw_pages:
        kept: list[str] = []
        for line in raw.splitlines():
            stripped = line.strip()
            if stripped in repeated or re.fullmatch(r"\d{1,4}", stripped):
                removed += 1
                continue
            kept.append(line)
        cleaned.append(_clean_page("\n".join(kept)))
    return cleaned, removed


def _looks_like_heading(line: str) -> bool:
    stripped = line.strip()
    if len(stripped) > 100:
        return False
    return bool(_NAMED_RE.match(stripped) or _NUMBERED_RE.match(stripped))


def _heading_match(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or len(stripped) > 140:
        return None

    match = _NAMED_INLINE_RE.match(stripped)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    match = _NAMED_RE.match(stripped)
    if match:
        return match.group(1).strip(), ""

    if _NUMBERED_RE.match(stripped) and len(stripped.split()) <= 10:
        return stripped, ""

    # ALL CAPS section names, e.g. "METHODS AND MATERIALS"
    if stripped.isupper() and 3 <= len(stripped) <= 60:
        if stripped.lower().strip(":") in _NAMED_SECTIONS:
            return stripped.title(), ""
    return None


def norm_heading(heading: str) -> str:
    """Lower-case a heading and strip numbering for robust matching.

    The whitespace after the number is required, otherwise "Introduction" loses
    its leading capital ``I`` to the Roman-numeral alternative.
    """
    value = re.sub(r"^(?:\d+(?:\.\d+)*\.?|[IVX]+\.)\s+", "", heading.strip())
    return value.strip().strip(":").lower()


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def _build_sections(pages: list[Page]) -> list[Section]:
    sections: list[Section] = []
    current_heading: str | None = None
    current_page = pages[0].number if pages else 1
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_heading, current_lines
        if current_heading:
            text = "\n".join(current_lines).strip()
            if text:
                sections.append(Section(current_heading, text, current_page))
        current_lines = []

    for page in pages:
        for line in page.text.splitlines():
            heading = _heading_match(line)
            if heading:
                flush()
                current_heading, inline = heading
                current_page = page.number
                if inline:
                    current_lines.append(inline)
            elif current_heading:
                current_lines.append(line)
    flush()
    return sections


def _regex_abstract(full_text: str) -> str:
    match = re.search(
        r"(?is)\babstract\b\s*[:.\-—]?\s*(.{100,3500}?)"
        r"(?=\n\s*(?:(?:\d+|[IVX]+)\.?\s*)?(?:introduction|keywords|index terms)\b)",
        full_text,
    )
    return match.group(1).strip() if match else ""


def _regex_conclusion(full_text: str) -> str:
    matches = list(
        re.finditer(
            r"(?is)\b(?:conclusions?|concluding remarks)\b\s*[:.\-—]?\s*(.{100,3000})",
            full_text,
        )
    )
    if not matches:
        return ""
    return matches[-1].group(1).strip()


def _fallback_sections(full_text: str, pages: list[Page]) -> list[Section]:
    # One section avoids duplicate sentences in the index; abstract/conclusion are
    # recovered separately by the regex fallbacks in abstract_text()/conclusion_text().
    return [Section("Body", full_text, pages[0].number if pages else 1)]


def find_section_text(doc: Document, names: list[str], max_chars: int = 12_000) -> str:
    wanted = [name.lower() for name in names]
    chunks: list[str] = []
    for section in doc.sections:
        heading = norm_heading(section.heading)
        if any(name == heading or name in heading for name in wanted):
            chunks.append(section.text)
    if chunks:
        return clip("\n\n".join(chunks), max_chars)

    full = doc.full_text
    if "abstract" in wanted:
        match = _regex_abstract(full)
        if match:
            return clip(match, max_chars)
    if any(name in {"conclusion", "conclusions", "concluding remarks"} for name in wanted):
        match = _regex_conclusion(full)
        if match:
            return clip(match, max_chars)
    return ""


def abstract_text(doc: Document) -> str:
    text = find_section_text(doc, ["abstract"], 4000)
    if text:
        return text
    match = _regex_abstract(doc.full_text)
    return match or clip(doc.full_text, 1400)


def conclusion_text(doc: Document) -> str:
    text = find_section_text(doc, ["conclusion", "conclusions", "concluding remarks"], 4000)
    if text:
        return text
    match = _regex_conclusion(doc.full_text)
    if match:
        return match
    return clip(doc.full_text[-2400:], 1600)


def results_text(doc: Document) -> str:
    text = find_section_text(
        doc, ["results", "experiments", "experiment", "evaluation", "analysis"], 7000
    )
    return text or clip(doc.full_text, 7000)


# ---------------------------------------------------------------------------
# Counts and title
# ---------------------------------------------------------------------------

def count_references(doc: Document) -> int:
    reference_sections = [
        section for section in doc.sections if "reference" in norm_heading(section.heading)
    ]
    count = 0
    for section in reference_sections:
        count += len(re.findall(r"(?m)^\s*\[\d+\]", section.text))
        count += len(re.findall(r"(?m)^\s*\d{1,3}\.\s+[A-Z]", section.text))
    if count == 0:
        count = len({int(n) for n in re.findall(r"\[(\d{1,3})\]", doc.full_text)})
    return min(count, 500)


def count_captions(full_text: str) -> tuple[int, int]:
    figures = {
        int(n) for n in re.findall(r"(?i)\b(?:figure|fig\.?)\s+(\d{1,3})", full_text)
    }
    tables = {
        int(n) for n in re.findall(r"(?i)\btable\s+(\d{1,3})", full_text)
    }
    return len(figures), len(tables)


def guess_title(filename: str, pages: list[Page]) -> str:
    if pages:
        for line in pages[0].text.splitlines()[:20]:
            candidate = normalize_ws(re.sub(r"^\s*(?:title|paper title)\s*[:\-]\s*", "", line, flags=re.I))
            if not (5 <= len(candidate) <= 300):
                continue
            if _TITLE_SKIP.search(candidate):
                continue
            # A wrapped banner/abstract continues in lower case; a title starts a
            # new sentence. This is what rejects "scholarly works." after the
            # banner above has been skipped.
            if candidate[:1].islower():
                continue
            if candidate.isdigit() or len(candidate.split()) < 2:
                continue
            return candidate.strip(" .;")
    stem = Path(filename).stem.replace("_", " ").replace("-", " ").strip()
    return stem or "Untitled document"


def _paginate_text(text: str, target_chars: int = 2800) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        return [text]
    pages: list[str] = []
    buffer: list[str] = []
    size = 0
    for paragraph in paragraphs:
        if buffer and size + len(paragraph) > target_chars:
            pages.append("\n\n".join(buffer))
            buffer, size = [], 0
        buffer.append(paragraph)
        size += len(paragraph) + 2
    if buffer:
        pages.append("\n\n".join(buffer))
    return pages or [text]


# ---------------------------------------------------------------------------
# Public ingest functions
# ---------------------------------------------------------------------------

def build_document(filename: str, raw_pages: list[str], *, source: str = "text") -> Document:
    cleaned, removed = _remove_running_lines(raw_pages)
    pages = [
        Page(number=index + 1, text=text)
        for index, text in enumerate(cleaned)
        if text.strip()
    ]
    if not pages:
        raise IngestError("EMPTY_DOCUMENT", "No extractable text was found in the document.")

    full_text = "\n\n".join(page.text for page in pages)
    if len(normalize_ws(full_text)) < 40:
        raise IngestError("EMPTY_DOCUMENT", "The document contains too little text to analyse.")

    sections = _build_sections(pages)
    if not sections:
        sections = _fallback_sections(full_text, pages)

    figures, tables = count_captions(full_text)
    doc = Document(
        filename=filename,
        title=guess_title(filename, pages),
        pages=pages,
        sections=sections,
        meta={
            "source": source,
            "page_count": len(pages),
            "characters": len(full_text),
            "removed_running_lines": removed,
            "figures": figures,
            "tables": tables,
        },
    )
    doc.meta["references"] = count_references(doc)
    return doc


def ingest_text(text: str, filename: str = "paper.txt") -> Document:
    text = (text or "").lstrip("\ufeff")
    if not text.strip():
        raise IngestError("EMPTY_DOCUMENT", "The uploaded file is empty.")
    return build_document(filename, _paginate_text(text), source="text")


def ingest_file(path: str | Path, filename: str | None = None) -> Document:
    path = Path(path)
    if not path.exists():
        raise IngestError("FILE_NOT_FOUND", "The uploaded file could not be read.")
    name = filename or path.name
    suffix = path.suffix.lower()

    if suffix in {".txt", ".md"}:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise IngestError("READ_FAILED", f"Could not read the file: {exc}") from exc
        return ingest_text(text, name)

    if suffix != ".pdf":
        raise IngestError(
            "UNSUPPORTED_FILE", "Only PDF and plain-text (.txt/.md) files are supported."
        )

    try:
        import fitz  # PyMuPDF, imported lazily so the rest of the pipeline stays testable
    except ImportError as exc:
        raise IngestError(
            "MISSING_DEPENDENCY",
            "PDF support needs PyMuPDF. Inside the Docker image it is installed; "
            "outside Docker upload a .txt file or run the API in its container.",
        ) from exc

    try:
        pdf = fitz.open(str(path))
    except Exception as exc:  # pragma: no cover - depends on malformed PDFs
        raise IngestError("INVALID_PDF", "The PDF could not be opened.") from exc

    try:
        if getattr(pdf, "needs_pass", False):
            raise IngestError("ENCRYPTED_PDF", "Password-protected PDFs are not supported.")
        total_pages = pdf.page_count
        limit = min(total_pages, config.MAX_PAGES)
        raw_pages: list[str] = []
        for index in range(limit):
            try:
                raw_pages.append(pdf.load_page(index).get_text("text") or "")
            except Exception:
                raw_pages.append("")
    finally:
        pdf.close()

    if sum(len(page.strip()) for page in raw_pages) < 100:
        raise IngestError(
            "NO_TEXT_LAYER",
            "This PDF has no text layer (likely a scan). OCR is out of scope - "
            "upload a text-based PDF or a .txt version.",
        )

    doc = build_document(name, raw_pages, source="pdf")
    doc.meta["page_count_total"] = total_pages
    doc.meta["truncated"] = total_pages > limit
    if doc.meta["truncated"]:
        doc.meta["analysed_pages"] = limit
    return doc


def build_sentence_index(doc: Document) -> list[dict]:
    """Global sentence ids from *section text*, so headings are not glued to sentences.

    Section text is authoritative (headings removed); the page is recovered by
    searching the sentence back in the page texts, which keeps citations accurate.
    """
    page_texts = [(page.number, normalize_for_match(page.text)) for page in doc.pages]
    seen: set[str] = set()
    sentences: list[dict] = []
    sentence_id = 0

    for section in doc.sections:
        for text in split_sentences(section.text):
            sentence = text.strip()
            if len(sentence) < 20 or not re.search(r"[A-Za-z]", sentence):
                continue
            key = normalize_for_match(sentence)
            if key in seen:
                continue
            seen.add(key)

            page_number = section.page
            for number, page_text in page_texts:
                if key in page_text:
                    page_number = number
                    break

            sentences.append(
                {
                    "id": sentence_id,
                    "text": sentence,
                    "page": page_number,
                    "section": section.heading,
                }
            )
            sentence_id += 1
            if len(sentences) >= config.MAX_EVIDENCE_SENTENCES:
                return sentences
    return sentences
