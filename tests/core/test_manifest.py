from __future__ import annotations

import json
from pathlib import Path

from pdf_splitter.core.manifest import build_manifest, read_manifest, write_manifest
from pdf_splitter.core.models import BoundaryDecision


def _decisions(*triples: tuple[int, bool, float]) -> list[BoundaryDecision]:
    return [
        BoundaryDecision(page_index=i, is_boundary=b, confidence=c, reason="test")
        for (i, b, c) in triples
    ]


def test_build_manifest_forces_page_zero_boundary():
    m = build_manifest(
        source="pkt.pdf",
        mode="scanned",
        model="anthropic/claude-opus-4-7",
        config={"dpi": 200},
        cost_usd=0.0,
        page_count=5,
        decisions=_decisions((1, False, 0.1), (2, True, 0.9), (3, False, 0.2), (4, False, 0.2)),
    )
    assert m.boundaries[0].page_index == 0
    assert m.boundaries[0].forced is True
    assert [b.page_index for b in m.boundaries] == [0, 2]


def test_build_manifest_segments():
    m = build_manifest(
        source="pkt.pdf",
        mode="scanned",
        model="m",
        config={},
        cost_usd=0.0,
        page_count=5,
        decisions=_decisions((1, False, 0.1), (2, True, 0.9), (3, False, 0.2), (4, False, 0.2)),
    )
    assert [(s.start, s.end) for s in m.segments] == [(0, 1), (2, 4)]
    assert m.segments[0].suggested_filename == "pkt_doc_001.pdf"
    assert m.segments[1].suggested_filename == "pkt_doc_002.pdf"


def test_build_manifest_errors_become_status_partial():
    decisions = [
        BoundaryDecision(page_index=1, is_boundary=False, confidence=0.0, reason="", error="x"),
        BoundaryDecision(page_index=2, is_boundary=True, confidence=0.9, reason="ok"),
    ]
    m = build_manifest(
        source="p.pdf",
        mode="scanned",
        model="m",
        config={},
        cost_usd=0.0,
        page_count=3,
        decisions=decisions,
    )
    assert m.status == "partial"


def test_build_manifest_single_segment_when_no_inner_boundaries():
    m = build_manifest(
        source="p.pdf",
        mode="text",
        model="m",
        config={},
        cost_usd=0.0,
        page_count=3,
        decisions=_decisions((1, False, 0.1), (2, False, 0.1)),
    )
    assert len(m.segments) == 1
    assert m.segments[0].start == 0 and m.segments[0].end == 2


def test_write_and_read_round_trip(tmp_path: Path):
    m = build_manifest(
        source="p.pdf",
        mode="text",
        model="m",
        config={},
        cost_usd=0.0,
        page_count=2,
        decisions=_decisions(
            (1, True, 0.8),
        ),
    )
    out = tmp_path / "manifest.json"
    write_manifest(out, m)
    loaded = read_manifest(out)
    assert loaded == m

    raw = json.loads(out.read_text())
    assert raw["schema_version"] == "1"
