from __future__ import annotations

from pathlib import Path

import pytest

from pdf_splitter.core.cache import DiskCache
from pdf_splitter.core.detector import detect_boundaries
from pdf_splitter.core.models import BoundaryDecision


class _FakeClient:
    """Records calls; returns scripted decisions keyed by page_index."""

    def __init__(self, scripted: dict[int, BoundaryDecision]):
        self._s = scripted
        self.calls: list[int] = []

    async def classify(self, *, page_index: int, **kwargs) -> tuple[BoundaryDecision, float]:
        self.calls.append(page_index)
        return self._s[page_index], 0.01


async def test_skips_page_zero(tmp_path: Path):
    client = _FakeClient(
        {
            1: BoundaryDecision(page_index=1, is_boundary=False, confidence=0.1, reason=""),
            2: BoundaryDecision(page_index=2, is_boundary=True, confidence=0.9, reason=""),
        }
    )
    pages = [b"p0", b"p1", b"p2"]
    decisions, cost = await detect_boundaries(
        pages=pages,
        mode="scanned",
        prompt="sys",
        client=client,
        cache=None,
        concurrency=2,  # type: ignore[arg-type]
    )
    assert 0 not in client.calls
    assert sorted(client.calls) == [1, 2]
    assert [d.page_index for d in decisions] == [1, 2]
    assert cost == pytest.approx(0.02)


async def test_uses_cache_on_hit(tmp_path: Path):
    client = _FakeClient({})  # should never be called
    cache = DiskCache(tmp_path / "c")
    # Pre-populate cache: cache key is computed by detector; we cheat by running
    # once with real client.
    primed = _FakeClient(
        {
            1: BoundaryDecision(page_index=1, is_boundary=True, confidence=0.8, reason="r"),
        }
    )
    pages = [b"p0", b"p1"]
    await detect_boundaries(
        pages=pages,
        mode="scanned",
        prompt="sys",
        client=primed,
        cache=cache,
        concurrency=1,  # type: ignore[arg-type]
    )
    # Now run with a client that would error if called:
    decisions, cost = await detect_boundaries(
        pages=pages,
        mode="scanned",
        prompt="sys",
        client=client,
        cache=cache,
        concurrency=1,  # type: ignore[arg-type]
    )
    assert decisions[0].is_boundary is True
    assert cost == 0.0
    assert client.calls == []


async def test_errors_pass_through():
    client = _FakeClient(
        {
            1: BoundaryDecision(
                page_index=1, is_boundary=False, confidence=0.0, reason="", error="x"
            ),
        }
    )
    decisions, _ = await detect_boundaries(
        pages=[b"p0", b"p1"],
        mode="scanned",
        prompt="sys",
        client=client,
        cache=None,
        concurrency=1,  # type: ignore[arg-type]
    )
    assert decisions[0].is_error
