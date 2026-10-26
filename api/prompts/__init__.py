"""Prompt templates live here - one source of truth for every model call.

A template file contains optional ``[sys]`` and ``[user]`` sections and uses
``{{placeholder}}`` markers.  Double braces are used so JSON examples inside the
template do not need escaping.
"""

from __future__ import annotations

import re
from pathlib import Path

_DIR = Path(__file__).resolve().parent
_SECTION_RE = re.compile(r"^\s*\[(sys|user)\]\s*$", re.MULTILINE | re.IGNORECASE)


def load(name: str) -> dict[str, str]:
    path = _DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Unknown prompt template: {name}")
    text = path.read_text(encoding="utf-8")
    parts: dict[str, str] = {}
    matches = list(_SECTION_RE.finditer(text))
    if not matches:
        return {"system": "", "user": text.strip()}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        parts[match.group(1).lower()] = text[start:end].strip()
    return {"system": parts.get("sys", ""), "user": parts.get("user", "")}


def render(name: str, **values: object) -> dict[str, str]:
    sections = load(name)
    for key, value in values.items():
        marker = "{{" + key + "}}"
        sections["system"] = sections["system"].replace(marker, str(value))
        sections["user"] = sections["user"].replace(marker, str(value))
    return sections
