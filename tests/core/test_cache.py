from __future__ import annotations

from pathlib import Path

from pdf_splitter.core.cache import DiskCache, make_cache_key
from pdf_splitter.core.models import BoundaryDecision


def test_cache_key_is_stable_for_same_inputs():
    k1 = make_cache_key(prompt="hello", payload=b"abc")
    k2 = make_cache_key(prompt="hello", payload=b"abc")
    assert k1 == k2


def test_cache_key_changes_with_prompt():
    k1 = make_cache_key(prompt="hello", payload=b"abc")
    k2 = make_cache_key(prompt="goodbye", payload=b"abc")
    assert k1 != k2


def test_cache_key_changes_with_payload():
    k1 = make_cache_key(prompt="hello", payload=b"abc")
    k2 = make_cache_key(prompt="hello", payload=b"xyz")
    assert k1 != k2


def test_disk_cache_set_and_get(tmp_path: Path):
    c = DiskCache(tmp_path / "cache")
    decision = BoundaryDecision(page_index=1, is_boundary=True, confidence=0.9, reason="r")
    c.set("k1", decision)
    assert c.get("k1") == decision


def test_disk_cache_miss_returns_none(tmp_path: Path):
    c = DiskCache(tmp_path / "cache")
    assert c.get("never-written") is None


def test_disk_cache_persists_across_instances(tmp_path: Path):
    path = tmp_path / "cache"
    d = BoundaryDecision(page_index=1, is_boundary=False, confidence=0.0, reason="r")
    DiskCache(path).set("k", d)
    assert DiskCache(path).get("k") == d
