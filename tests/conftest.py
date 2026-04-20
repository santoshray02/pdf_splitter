"""Shared test fixtures."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def _make_pdf(pages: list[str]) -> bytes:
    """Build a text-layer PDF from a list of per-page strings."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    for text in pages:
        c.drawString(72, 720, text)
        c.showPage()
    c.save()
    return buf.getvalue()


@pytest.fixture
def text_pdf_factory(tmp_path: Path):
    """Factory: list[str] of page texts → path to a text-layer PDF."""
    counter = {"i": 0}

    def make(pages: list[str], name: str | None = None) -> Path:
        counter["i"] += 1
        path = tmp_path / (name or f"text_{counter['i']}.pdf")
        path.write_bytes(_make_pdf(pages))
        return path

    return make
