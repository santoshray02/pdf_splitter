"""LiteLLM-routed boundary classifier. Only module that imports litellm."""

from __future__ import annotations

import base64
import json
from typing import Any

import structlog
from litellm import (
    acompletion as _acompletion,  # pyright: ignore[reportUnknownVariableType]
)
from pydantic import ValidationError
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from pdf_splitter.core.models import BoundaryDecision

log = structlog.get_logger(__name__)


def _build_messages(
    *,
    prompt: str,
    prev_image: bytes | None,
    curr_image: bytes | None,
    prev_text: str | None,
    curr_text: str | None,
) -> list[dict[str, Any]]:
    user_content: list[dict[str, Any]] = []
    if prev_image is not None and curr_image is not None:
        for label, img in (("previous_page", prev_image), ("current_page", curr_image)):
            user_content.append({"type": "text", "text": label})
            b64 = base64.b64encode(img).decode("ascii")
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                }
            )
    elif prev_text is not None and curr_text is not None:
        user_content.append(
            {"type": "text", "text": f"previous_page:\n{prev_text}\n\ncurrent_page:\n{curr_text}"}
        )
    else:
        raise ValueError("classify() needs either both images or both texts")
    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_content},
    ]


def _parse_payload(content: str) -> dict[str, Any]:
    return json.loads(content)  # type: ignore[no-any-return]


class LLMClient:
    def __init__(self, *, model: str, max_attempts: int = 5, temperature: float = 0.0):
        self.model = model
        self.max_attempts = max_attempts
        self.temperature = temperature

    async def _raw_call(self, messages: list[dict[str, Any]]) -> tuple[str, float]:
        resp: dict[str, Any] = await _acompletion(  # type: ignore[assignment]
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            response_format={"type": "json_object"},
        )
        content: str = resp["choices"][0]["message"]["content"]  # type: ignore[index]
        cost = float(resp.get("_hidden_params", {}).get("response_cost") or 0.0)  # type: ignore[union-attr]
        return content, cost

    async def _call_with_retries(self, messages: list[dict[str, Any]]) -> tuple[str, float]:
        # With reraise=True, the last exception propagates directly after final
        # attempt — no RetryError wrapper. We let it bubble up to classify().
        # v2-TODO: narrow retry predicate from bare Exception to litellm's
        # transient-error hierarchy (RateLimitError, APIConnectionError,
        # Timeout, ServiceUnavailableError, InternalServerError) so that
        # programming bugs fail fast instead of burning N retries.
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self.max_attempts),
            wait=wait_exponential_jitter(initial=0.01, max=0.1),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        ):
            with attempt:
                return await self._raw_call(messages)
        raise RuntimeError("unreachable")  # pyright needs this; never hit at runtime

    async def classify(
        self,
        *,
        page_index: int,
        prompt: str,
        prev_image: bytes | None = None,
        curr_image: bytes | None = None,
        prev_text: str | None = None,
        curr_text: str | None = None,
    ) -> tuple[BoundaryDecision, float]:
        messages = _build_messages(
            prompt=prompt,
            prev_image=prev_image,
            curr_image=curr_image,
            prev_text=prev_text,
            curr_text=curr_text,
        )
        total_cost = 0.0
        try:
            content, cost = await self._call_with_retries(messages)
            total_cost += cost
        except Exception as exc:
            log.warning("classify.failed", page_index=page_index, error=str(exc))
            return (
                BoundaryDecision(
                    page_index=page_index,
                    is_boundary=False,
                    confidence=0.0,
                    reason="",
                    error=str(exc),
                ),
                total_cost,
            )

        try:
            parsed = _parse_payload(content)
            return (
                BoundaryDecision(
                    page_index=page_index,
                    is_boundary=bool(parsed["is_boundary"]),
                    confidence=float(parsed["confidence"]),
                    reason=str(parsed.get("reason", "")),
                ),
                total_cost,
            )
        except (ValueError, KeyError, ValidationError) as exc:
            # Log the original malformed content at debug level so that when the
            # repair path also fails we still have diagnostic breadcrumbs.
            log.debug(
                "classify.malformed_json_first_pass",
                page_index=page_index,
                error=str(exc),
                content_preview=content[:200],
            )

        # Repair retry: one more call, stricter instruction.
        repair_instruction = (
            "Respond with valid JSON ONLY: "
            '{"is_boundary": bool, "confidence": number, "reason": string}'
        )
        repair_messages = [
            *messages,
            {"role": "user", "content": repair_instruction},
        ]
        try:
            content2, cost2 = await self._call_with_retries(repair_messages)
            total_cost += cost2
            parsed2 = _parse_payload(content2)
            return (
                BoundaryDecision(
                    page_index=page_index,
                    is_boundary=bool(parsed2["is_boundary"]),
                    confidence=float(parsed2["confidence"]),
                    reason=str(parsed2.get("reason", "")),
                ),
                total_cost,
            )
        except Exception as exc:
            log.warning("classify.malformed_after_repair", page_index=page_index, error=str(exc))
            return (
                BoundaryDecision(
                    page_index=page_index,
                    is_boundary=False,
                    confidence=0.0,
                    reason="",
                    error=f"malformed response: {exc}",
                ),
                total_cost,
            )
