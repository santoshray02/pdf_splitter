"""Compose the final classifier system prompt from overrides."""

from __future__ import annotations

from pdf_splitter.core.models import FewShotExample, ProfileConfig

DEFAULT_SYSTEM_PROMPT = """\
You are a document-boundary classifier. Given two consecutive pages from a \
PDF packet (the previous page and the current page), decide whether the \
current page is the FIRST page of a NEW logical document inside the packet, \
or a continuation of the previous document.

Signals that usually indicate a new document:
- A clear cover-page layout, form header, or title block
- Page numbering resets (e.g. page 1 of N appearing)
- A sudden change in template, letterhead, or layout family

Respond with a single JSON object:
{"is_boundary": bool, "confidence": float between 0 and 1, "reason": short string}
"""


def compose_prompt(
    *,
    profile: ProfileConfig | None,
    user_prompt: str | None,
    examples: list[FewShotExample],
) -> str:
    parts: list[str] = [DEFAULT_SYSTEM_PROMPT]
    if profile is not None and profile.prompt:
        parts.append("\nAdditional context from profile:\n" + profile.prompt.rstrip())
    if user_prompt:
        parts.append("\nAdditional user instructions:\n" + user_prompt.rstrip())
    if examples:
        parts.append("\nExamples:")
        for i, ex in enumerate(examples, start=1):
            label = "is_boundary=true" if ex.is_boundary else "is_boundary=false"
            parts.append(f"  Example {i}: {ex.before.name} → {ex.after.name} ({label})")
    return "\n".join(parts)
