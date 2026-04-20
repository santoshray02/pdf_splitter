"""Lightweight fake for litellm.acompletion in tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class FakeResponse:
    content: str
    cost_usd: float = 0.001

    def model_dump(self) -> dict[str, Any]:
        # Mimic the litellm response shape we actually read.
        return {
            "choices": [{"message": {"content": self.content}}],
            "_hidden_params": {"response_cost": self.cost_usd},
        }


class FakeDriver:
    """Scripted replies: each call pops the next scripted response (or exception)."""

    def __init__(self, scripted: list[FakeResponse | Exception]):
        self._scripted = list(scripted)
        self.calls: list[dict[str, Any]] = []

    async def acompletion(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        nxt = self._scripted.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt.model_dump()
