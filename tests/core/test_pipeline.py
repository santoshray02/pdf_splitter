from __future__ import annotations

from pathlib import Path

import pytest  # noqa: F401

from pdf_splitter.core.manifest import read_manifest
from pdf_splitter.core.models import BoundaryDecision, Config
from pdf_splitter.core.pipeline import RunReport, run


class _ScriptedClient:
    def __init__(self, by_page: dict[int, BoundaryDecision]):
        self._by_page = by_page

    async def classify(self, *, page_index: int, **kwargs) -> tuple[BoundaryDecision, float]:
        return self._by_page[page_index], 0.005


async def test_pipeline_writes_manifest_and_split_files(
    tmp_path: Path, text_pdf_factory, monkeypatch
):
    src = text_pdf_factory(["first doc", "cont", "second doc", "cont"], name="pkt.pdf")
    out = tmp_path / "out"
    cfg = Config(inputs=[str(src)], output_dir=out, model="m")

    client = _ScriptedClient(
        {
            1: BoundaryDecision(page_index=1, is_boundary=False, confidence=0.1, reason=""),
            2: BoundaryDecision(page_index=2, is_boundary=True, confidence=0.9, reason="new doc"),
            3: BoundaryDecision(page_index=3, is_boundary=False, confidence=0.1, reason=""),
        }
    )

    report: RunReport = await run(config=cfg, client=client)

    assert report.succeeded == 1 and report.failed == 0
    manifest_path = out / "pkt" / "manifest.json"
    assert manifest_path.exists()
    manifest = read_manifest(manifest_path)
    assert manifest.page_count == 4
    assert len(manifest.segments) == 2
    # Split files exist
    split_files = sorted((out / "pkt").glob("pkt_doc_*.pdf"))
    assert [p.name for p in split_files] == ["pkt_doc_001.pdf", "pkt_doc_002.pdf"]


async def test_report_only_skips_splitting(tmp_path: Path, text_pdf_factory):
    src = text_pdf_factory(["a", "b"], name="pkt.pdf")
    out = tmp_path / "out"
    cfg = Config(inputs=[str(src)], output_dir=out, model="m", report_only=True)
    client = _ScriptedClient(
        {
            1: BoundaryDecision(page_index=1, is_boundary=False, confidence=0.1, reason=""),
        }
    )
    await run(config=cfg, client=client)
    assert (out / "pkt" / "manifest.json").exists()
    assert list((out / "pkt").glob("pkt_doc_*.pdf")) == []


async def test_dry_run_does_nothing(tmp_path: Path, text_pdf_factory):
    src = text_pdf_factory(["a", "b"], name="pkt.pdf")
    out = tmp_path / "out"
    cfg = Config(inputs=[str(src)], output_dir=out, model="m", dry_run=True)

    class _ShouldNotCall:
        async def classify(self, **kwargs):  # pragma: no cover - asserted not called
            raise AssertionError("dry_run should not call classifier")

    report = await run(config=cfg, client=_ShouldNotCall())
    assert report.succeeded == 0 and report.failed == 0
    assert not out.exists()


async def test_per_file_failure_does_not_abort_batch(tmp_path: Path, text_pdf_factory):
    good = text_pdf_factory(["a", "b"], name="good.pdf")
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    out = tmp_path / "out"
    cfg = Config(inputs=[str(good), str(bad)], output_dir=out, model="m")
    client = _ScriptedClient(
        {
            1: BoundaryDecision(page_index=1, is_boundary=False, confidence=0.1, reason=""),
        }
    )
    report = await run(config=cfg, client=client)
    assert report.succeeded == 1 and report.failed == 1
    assert (out / "good" / "manifest.json").exists()


async def test_cost_cap_halts_run(tmp_path: Path, text_pdf_factory):
    src = text_pdf_factory(["a", "b", "c"], name="pkt.pdf")
    out = tmp_path / "out"
    cfg = Config(inputs=[str(src)], output_dir=out, model="m", max_cost_usd=0.001)

    # Each call costs 0.005 — first call will already exceed the cap.
    client = _ScriptedClient(
        {
            1: BoundaryDecision(page_index=1, is_boundary=False, confidence=0.1, reason=""),
            2: BoundaryDecision(page_index=2, is_boundary=True, confidence=0.9, reason=""),
        }
    )
    await run(config=cfg, client=client)
    manifest = read_manifest(out / "pkt" / "manifest.json")
    assert manifest.status == "halted_cost_cap"
