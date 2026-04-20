from __future__ import annotations

import pytest
from pydantic import ValidationError

from pdf_splitter.core.models import (
    Boundary,
    BoundaryDecision,
    Config,
    FewShotExample,
    Manifest,
    ProfileConfig,
    Segment,
)


def test_boundary_round_trip():
    b = Boundary(page_index=12, confidence=0.94, reason="Form P-II header detected")
    dumped = b.model_dump_json()
    assert Boundary.model_validate_json(dumped) == b


def test_boundary_forced_flag_default_false():
    b = Boundary(page_index=0, confidence=1.0, reason="first page")
    assert b.forced is False


def test_segment_validates_start_end_order():
    with pytest.raises(ValidationError):
        Segment(index=0, start=5, end=2, suggested_filename="x.pdf")


def test_boundary_decision_error_shape():
    d = BoundaryDecision(
        page_index=3, is_boundary=False, confidence=0.0, reason="", error="timeout"
    )
    assert d.is_error is True


def test_boundary_decision_ok_shape():
    d = BoundaryDecision(page_index=3, is_boundary=True, confidence=0.88, reason="header")
    assert d.is_error is False


def test_manifest_schema_version_is_1():
    m = Manifest(
        source="p.pdf",
        mode="scanned",
        model="anthropic/claude-opus-4-7",
        config={"dpi": 200},
        cost_usd=0.0,
        page_count=1,
        boundaries=[Boundary(page_index=0, confidence=1.0, reason="first", forced=True)],
        segments=[Segment(index=0, start=0, end=0, suggested_filename="p_doc_001.pdf")],
        status="ok",
    )
    assert m.schema_version == "1"


def test_config_defaults():
    c = Config(inputs=["a.pdf"])
    assert c.dpi == 150
    assert c.concurrency == 8
    assert c.batch_concurrency == 1
    assert c.report_only is False
    assert c.no_cache is False
    assert c.max_cost_usd is None


def test_profile_config_minimal():
    p = ProfileConfig(name="khasra-b1", description="x", prompt="custom prompt")
    assert p.few_shot == []
    assert p.mode_hint is None


def test_few_shot_example_requires_all_fields():
    with pytest.raises(ValidationError):
        FewShotExample()  # type: ignore[call-arg]
