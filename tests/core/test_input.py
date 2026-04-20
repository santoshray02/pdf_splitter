from __future__ import annotations

from pathlib import Path

import pytest

from pdf_splitter.core.input import InputError, _garbage_ratio, detect_mode, open_pdf


def test_text_pdf_detected_as_text(text_pdf_factory):
    # Each page must extract >100 chars to clear TEXT_CHAR_THRESHOLD. A single
    # drawString line of prose (~45 chars) doesn't; combining several sentences
    # into one drawString call yields ~175 chars as extracted by pymupdf.
    page_text = (
        "Hello world, this is a typical page of prose. "
        "It contains multiple sentences to ensure sufficient character count. "
        "This simulates a real document with meaningful text content."
    )
    path = text_pdf_factory([page_text] * 3)
    doc = open_pdf(path)
    assert detect_mode(doc) == "text"


def test_empty_text_pdf_detected_as_scanned(text_pdf_factory):
    # Empty pages (reportlab produces pages with no text)
    path = text_pdf_factory(["", "", ""])
    doc = open_pdf(path)
    assert detect_mode(doc) == "scanned"


def test_corrupt_pdf_raises_input_error(tmp_path: Path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not-a-pdf")
    with pytest.raises(InputError):
        open_pdf(bad)


def test_missing_file_raises_input_error(tmp_path: Path):
    with pytest.raises(InputError):
        open_pdf(tmp_path / "nope.pdf")


def test_garbage_text_layer_detected_as_scanned():
    # Neither reportlab nor pymupdf preserves \ufffd through a PDF round-trip,
    # so we test _garbage_ratio directly as a pure-function unit test.
    # A string dominated by replacement chars must return ratio > GARBAGE_RATIO_THRESHOLD.
    garbage = "\ufffd" * 500
    assert _garbage_ratio(garbage) > 0.20
    # And a normal string must be well below the threshold.
    normal = "Hello world, this is ordinary prose text."
    assert _garbage_ratio(normal) < 0.20
