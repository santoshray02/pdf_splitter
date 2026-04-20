"""Build, serialize, and read Manifest instances."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pdf_splitter.core.models import (
    Boundary,
    BoundaryDecision,
    Manifest,
    Mode,
    Segment,
    Status,
)


def _source_stem(source: str) -> str:
    return Path(source).stem


def build_manifest(
    *,
    source: str,
    mode: Mode,
    model: str,
    config: dict[str, Any],
    cost_usd: float,
    page_count: int,
    decisions: list[BoundaryDecision],
) -> Manifest:
    boundaries: list[Boundary] = [
        Boundary(page_index=0, confidence=1.0, reason="first page", forced=True)
    ]
    for d in decisions:
        if d.is_boundary and not d.is_error:
            boundaries.append(
                Boundary(
                    page_index=d.page_index,
                    confidence=d.confidence,
                    reason=d.reason,
                )
            )

    stem = _source_stem(source)
    segments: list[Segment] = []
    for i, b in enumerate(boundaries):
        start = b.page_index
        end = (boundaries[i + 1].page_index - 1) if i + 1 < len(boundaries) else (page_count - 1)
        segments.append(
            Segment(
                index=i,
                start=start,
                end=end,
                suggested_filename=f"{stem}_doc_{i + 1:03d}.pdf",
            )
        )

    has_errors = any(d.is_error for d in decisions)
    status: Status = "partial" if has_errors else "ok"

    return Manifest(
        source=source,
        mode=mode,
        model=model,
        config=config,
        cost_usd=cost_usd,
        page_count=page_count,
        boundaries=boundaries,
        segments=segments,
        status=status,
    )


def write_manifest(path: Path, manifest: Manifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")


def read_manifest(path: Path) -> Manifest:
    return Manifest.model_validate_json(path.read_text(encoding="utf-8"))
