"""Per-file pipeline orchestration and batch runner."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import structlog

from pdf_splitter.core.cache import DiskCache, default_cache_dir
from pdf_splitter.core.detector import Classifier, detect_boundaries
from pdf_splitter.core.input import InputError, detect_mode, open_pdf
from pdf_splitter.core.manifest import build_manifest, write_manifest
from pdf_splitter.core.models import BoundaryDecision, Config
from pdf_splitter.core.profiles import load_profile
from pdf_splitter.core.prompts import compose_prompt
from pdf_splitter.core.rendering import extract_text_per_page, render_page_png
from pdf_splitter.core.splitter import apply_split

log = structlog.get_logger(__name__)


@dataclass
class RunReport:
    succeeded: int = 0
    failed: int = 0
    halted_cost_cap: bool = False


def _expand_inputs(paths: Iterable[str]) -> list[Path]:
    out: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            out.extend(sorted(p.rglob("*.pdf")))
        elif p.exists():
            out.append(p)
    return out


def _resolve_output_dir(source: Path, config: Config) -> Path:
    base = config.output_dir if config.output_dir else source.parent / "out"
    return base / source.stem


async def _process_one(source: Path, config: Config, client: Classifier) -> bool:
    """Process one PDF. Returns `halted_by_cost_cap` flag."""
    profile = load_profile(config.profile) if config.profile else None
    effective_dpi = profile.dpi if (profile and profile.dpi) else config.dpi
    mode_override = config.force_mode or (profile.mode_hint if profile else None)
    prompt = compose_prompt(profile=profile, user_prompt=config.prompt, examples=[])

    doc = open_pdf(source)
    mode = mode_override or detect_mode(doc)
    page_count: int = cast(int, doc.page_count)  # type: ignore[reportUnknownMemberType]

    pages: list[bytes] | list[str]
    if mode == "scanned":
        pages = [render_page_png(doc, i, dpi=effective_dpi) for i in range(page_count)]
    else:
        pages = extract_text_per_page(doc)

    cache = None if config.no_cache else DiskCache(default_cache_dir())

    decisions: list[BoundaryDecision] = []
    total_cost = 0.0
    halted = False

    if config.max_cost_usd is None:
        decisions, total_cost = await detect_boundaries(
            pages=pages,
            mode=mode,
            prompt=prompt,
            client=client,
            cache=cache,
            concurrency=config.concurrency,
        )
    else:
        # Iterate pairs sequentially so we can halt mid-stream at the cost cap.
        # Call client.classify directly (instead of detect_boundaries on a 2-page
        # slice) so the absolute page_index reaches the LLM's positional context;
        # otherwise every pair would be labeled "page 1" regardless of position.
        # Cache is intentionally bypassed here: cached results return cost=0, so
        # honoring them could prevent the cap from ever firing on a previously-run
        # file. Users who want cached behavior can omit --max-cost-usd.
        for i in range(page_count - 1):
            abs_page_index = i + 1
            if mode == "scanned":
                decision, cost = await client.classify(
                    page_index=abs_page_index,
                    prompt=prompt,
                    prev_image=cast(bytes, pages[i]),
                    curr_image=cast(bytes, pages[i + 1]),
                )
            else:
                decision, cost = await client.classify(
                    page_index=abs_page_index,
                    prompt=prompt,
                    prev_text=cast(str, pages[i]),
                    curr_text=cast(str, pages[i + 1]),
                )
            decisions.append(decision)
            total_cost += cost
            if total_cost >= config.max_cost_usd:
                halted = True
                break

    manifest = build_manifest(
        source=str(source),
        mode=mode,
        model=config.model or "unknown",
        config=config.model_dump(mode="json", exclude={"inputs"}),
        cost_usd=total_cost,
        page_count=page_count,
        decisions=decisions,
    )
    if halted:
        manifest = manifest.model_copy(update={"status": "halted_cost_cap"})

    output_subdir = _resolve_output_dir(source, config)
    output_subdir.mkdir(parents=True, exist_ok=True)
    if not config.no_manifest:
        write_manifest(output_subdir / "manifest.json", manifest)
    if not config.report_only and not halted:
        apply_split(source_pdf=source, manifest=manifest, output_dir=output_subdir)
    return halted


async def run(*, config: Config, client: Classifier) -> RunReport:
    report = RunReport()
    if config.dry_run:
        log.info("dry_run.skip", inputs=config.inputs)
        return report

    files = _expand_inputs(config.inputs)
    sem = asyncio.Semaphore(config.batch_concurrency)

    async def one(src: Path) -> None:
        async with sem:
            try:
                halted = await _process_one(src, config, client)
                report.succeeded += 1
                if halted:
                    report.halted_cost_cap = True
            except InputError as exc:
                log.warning("pipeline.input_error", source=str(src), error=str(exc))
                report.failed += 1
            except Exception as exc:
                log.exception("pipeline.unexpected", source=str(src), error=str(exc))
                report.failed += 1

    await asyncio.gather(*(one(f) for f in files))
    return report
