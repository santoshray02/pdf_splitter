from __future__ import annotations

from pathlib import Path

import pypdf

from pdf_splitter.core.manifest import build_manifest
from pdf_splitter.core.models import BoundaryDecision
from pdf_splitter.core.splitter import apply_split


def _pdf_page_count(path: Path) -> int:
    return len(pypdf.PdfReader(str(path)).pages)


def test_apply_split_writes_one_file_per_segment(tmp_path: Path, text_pdf_factory):
    src = text_pdf_factory(["p0", "p1", "p2", "p3", "p4"], name="pkt.pdf")
    manifest = build_manifest(
        source=str(src),
        mode="text",
        model="m",
        config={},
        cost_usd=0.0,
        page_count=5,
        decisions=[
            BoundaryDecision(page_index=1, is_boundary=False, confidence=0.1, reason=""),
            BoundaryDecision(page_index=2, is_boundary=True, confidence=0.9, reason=""),
            BoundaryDecision(page_index=3, is_boundary=False, confidence=0.1, reason=""),
            BoundaryDecision(page_index=4, is_boundary=False, confidence=0.1, reason=""),
        ],
    )
    out_dir = tmp_path / "out"
    written = apply_split(source_pdf=src, manifest=manifest, output_dir=out_dir)
    assert len(written) == 2
    assert _pdf_page_count(written[0]) == 2  # pages 0,1
    assert _pdf_page_count(written[1]) == 3  # pages 2,3,4
    assert written[0].name == "pkt_doc_001.pdf"
    assert written[1].name == "pkt_doc_002.pdf"


def test_apply_split_handles_collisions(tmp_path: Path, text_pdf_factory):
    src = text_pdf_factory(["a", "b"], name="pkt.pdf")
    manifest = build_manifest(
        source=str(src),
        mode="text",
        model="m",
        config={},
        cost_usd=0.0,
        page_count=2,
        decisions=[
            BoundaryDecision(page_index=1, is_boundary=False, confidence=0.1, reason=""),
        ],
    )
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "pkt_doc_001.pdf").write_bytes(b"already here")
    written = apply_split(source_pdf=src, manifest=manifest, output_dir=out_dir)
    assert written[0].name == "pkt_doc_001_v2.pdf"
