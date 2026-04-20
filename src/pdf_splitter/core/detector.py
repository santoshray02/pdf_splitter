"""Sliding-window boundary detection with bounded async concurrency."""

from __future__ import annotations

from typing import Protocol

import anyio

from pdf_splitter.core.cache import DiskCache, make_cache_key
from pdf_splitter.core.models import BoundaryDecision, Mode


class Classifier(Protocol):
    async def classify(
        self,
        *,
        page_index: int,
        prompt: str,
        prev_image: bytes | None = ...,
        curr_image: bytes | None = ...,
        prev_text: str | None = ...,
        curr_text: str | None = ...,
    ) -> tuple[BoundaryDecision, float]: ...


def _page_payload(mode: Mode, prev: bytes | str, curr: bytes | str) -> bytes:
    if mode == "scanned":
        assert isinstance(prev, bytes) and isinstance(curr, bytes)
        return prev + b"\x00" + curr
    assert isinstance(prev, str) and isinstance(curr, str)
    return (prev + "\x00" + curr).encode("utf-8")


async def detect_boundaries(
    *,
    pages: list[bytes] | list[str],
    mode: Mode,
    prompt: str,
    client: Classifier,
    cache: DiskCache | None,
    concurrency: int,
) -> tuple[list[BoundaryDecision], float]:
    n = len(pages)
    results: list[BoundaryDecision | None] = [None] * (n - 1)
    cost_total = 0.0
    sem = anyio.Semaphore(concurrency)
    cost_lock = anyio.Lock()

    async def worker(i: int) -> None:
        nonlocal cost_total
        prev, curr = pages[i], pages[i + 1]
        page_index = i + 1

        # Compute the cache key once if caching is active; re-used for the
        # write path on cache miss below.
        cache_key: str | None = None
        if cache is not None:
            payload = _page_payload(mode, prev, curr)
            cache_key = make_cache_key(prompt=prompt, payload=payload)
            hit = cache.get(cache_key)
            if hit is not None:
                results[i] = hit
                return

        async with sem:
            if mode == "scanned":
                decision, cost = await client.classify(
                    page_index=page_index,
                    prompt=prompt,
                    prev_image=prev,  # type: ignore[arg-type]
                    curr_image=curr,  # type: ignore[arg-type]
                )
            else:
                decision, cost = await client.classify(
                    page_index=page_index,
                    prompt=prompt,
                    prev_text=prev,  # type: ignore[arg-type]
                    curr_text=curr,  # type: ignore[arg-type]
                )
        results[i] = decision
        async with cost_lock:
            cost_total += cost
        if cache_key is not None and not decision.is_error:
            cache.set(cache_key, decision)  # type: ignore[union-attr]

    async with anyio.create_task_group() as tg:
        for i in range(n - 1):
            tg.start_soon(worker, i)

    out: list[BoundaryDecision] = [r for r in results if r is not None]
    return out, cost_total
