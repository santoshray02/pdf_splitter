from __future__ import annotations

import pytest

from pdf_splitter.providers import llm as llm_module
from pdf_splitter.providers.llm import LLMClient
from tests.providers._fixture_driver import FakeDriver, FakeResponse


@pytest.fixture
def fake_driver(monkeypatch):
    def _install(scripted: list) -> FakeDriver:
        drv = FakeDriver(scripted)
        monkeypatch.setattr(llm_module, "_acompletion", drv.acompletion)
        return drv

    return _install


async def test_happy_path_scanned(fake_driver):
    drv = fake_driver(
        [FakeResponse('{"is_boundary": true, "confidence": 0.91, "reason": "header"}')]
    )
    client = LLMClient(model="anthropic/claude-opus-4-7")
    decision, cost = await client.classify(
        page_index=5, prompt="sys", prev_image=b"PNG1", curr_image=b"PNG2"
    )
    assert decision.is_boundary is True
    assert decision.confidence == pytest.approx(0.91)
    assert cost == pytest.approx(0.001)
    # Verify the request carried both images.
    call = drv.calls[0]
    assert call["response_format"] == {"type": "json_object"}


async def test_happy_path_text(fake_driver):
    fake_driver(
        [FakeResponse('{"is_boundary": false, "confidence": 0.12, "reason": "continuation"}')]
    )
    client = LLMClient(model="anthropic/claude-opus-4-7")
    decision, _ = await client.classify(
        page_index=3, prompt="sys", prev_text="prev", curr_text="curr"
    )
    assert decision.is_boundary is False


async def test_malformed_json_triggers_repair_retry(fake_driver):
    fake_driver(
        [
            FakeResponse("not json"),
            FakeResponse('{"is_boundary": true, "confidence": 0.8, "reason": "ok"}'),
        ]
    )
    client = LLMClient(model="m")
    decision, _ = await client.classify(page_index=1, prompt="sys", prev_text="a", curr_text="b")
    assert decision.reason == "ok"


async def test_malformed_json_after_repair_records_error(fake_driver):
    fake_driver([FakeResponse("nope"), FakeResponse("still not json")])
    client = LLMClient(model="m")
    decision, _ = await client.classify(page_index=1, prompt="sys", prev_text="a", curr_text="b")
    assert decision.is_error
    assert decision.is_boundary is False


async def test_transient_error_retries_and_succeeds(fake_driver):
    fake_driver(
        [
            RuntimeError("429 rate limit"),
            FakeResponse('{"is_boundary": true, "confidence": 0.7, "reason": "ok"}'),
        ]
    )
    client = LLMClient(model="m", max_attempts=3)
    decision, _ = await client.classify(page_index=1, prompt="sys", prev_text="a", curr_text="b")
    assert decision.is_boundary is True


async def test_exhausted_retries_records_error(fake_driver):
    fake_driver(
        [
            RuntimeError("boom"),
            RuntimeError("boom"),
            RuntimeError("boom"),
        ]
    )
    client = LLMClient(model="m", max_attempts=3)
    decision, _ = await client.classify(page_index=1, prompt="sys", prev_text="a", curr_text="b")
    assert decision.is_error
    assert "boom" in (decision.error or "")
