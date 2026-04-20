from __future__ import annotations

from pdf_splitter.core.input import open_pdf
from pdf_splitter.core.rendering import extract_text_per_page, render_page_png


def test_render_page_returns_png_bytes(text_pdf_factory):
    doc = open_pdf(text_pdf_factory(["hello"]))
    png = render_page_png(doc, 0, dpi=100)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_render_dpi_scales_output_size(text_pdf_factory):
    doc = open_pdf(text_pdf_factory(["hello"]))
    small = render_page_png(doc, 0, dpi=72)
    large = render_page_png(doc, 0, dpi=200)
    assert len(large) > len(small)


def test_extract_text_per_page_returns_one_entry_per_page(text_pdf_factory):
    doc = open_pdf(text_pdf_factory(["alpha page", "beta page", "gamma page"]))
    texts = extract_text_per_page(doc)
    assert len(texts) == 3
    assert "alpha" in texts[0]
    assert "beta" in texts[1]
    assert "gamma" in texts[2]
