"""Render pages to PNG bytes and extract per-page text."""

from __future__ import annotations

from typing import cast

import pymupdf


def render_page_png(doc: pymupdf.Document, page_index: int, *, dpi: int) -> bytes:
    page = doc[page_index]
    zoom = dpi / 72.0
    matrix = pymupdf.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, alpha=False)  # type: ignore[reportUnknownMemberType]
    return pix.tobytes("png")  # type: ignore[reportUnknownMemberType]


def extract_text_per_page(doc: pymupdf.Document) -> list[str]:
    return [
        cast(str, page.get_text("text"))  # type: ignore[reportUnknownMemberType]
        for page in doc
    ]
