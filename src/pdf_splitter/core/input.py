"""PDF open + scanned/text mode detection."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pymupdf

from pdf_splitter.core.models import Mode

TEXT_CHAR_THRESHOLD = 10  # min chars per page (averaged) to be considered text-bearing
GARBAGE_RATIO_THRESHOLD = 0.20  # fraction of chars that are replacement/control


class InputError(Exception):
    """Raised for unreadable, missing, or corrupt PDFs."""


def open_pdf(path: Path) -> pymupdf.Document:
    if not Path(path).exists():
        raise InputError(f"PDF not found: {path}")
    try:
        return pymupdf.open(path)
    except Exception as exc:  # pymupdf raises several types
        raise InputError(f"Cannot open {path}: {exc}") from exc


def _garbage_ratio(text: str) -> float:
    if not text:
        return 0.0
    bad = sum(1 for ch in text if ch == "\ufffd" or (ord(ch) < 32 and ch not in "\t\n\r"))
    return bad / len(text)


def detect_mode(doc: pymupdf.Document) -> Mode:
    pages_text: list[str] = [
        cast(str, page.get_text("text"))  # type: ignore[reportUnknownMemberType]
        for page in doc
    ]
    total_chars = sum(len(t) for t in pages_text)
    avg = total_chars / max(len(pages_text), 1)
    if avg < TEXT_CHAR_THRESHOLD:
        return "scanned"
    combined = "".join(pages_text)
    if _garbage_ratio(combined) > GARBAGE_RATIO_THRESHOLD:
        return "scanned"
    return "text"
