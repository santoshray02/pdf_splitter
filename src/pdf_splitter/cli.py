"""Typer CLI — thin wrapper over pdf_splitter.core.pipeline."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer

from pdf_splitter.core.manifest import read_manifest
from pdf_splitter.core.models import Config, Mode
from pdf_splitter.core.pipeline import run as run_pipeline
from pdf_splitter.core.profiles import (
    ProfileNotFoundError,
    find_profile,
    load_profile,
    search_dirs,
)
from pdf_splitter.providers.llm import LLMClient

app = typer.Typer(add_completion=False, help="AI-powered PDF splitter.")
profiles_app = typer.Typer(help="Manage YAML profiles.")
manifest_app = typer.Typer(help="Inspect split manifests.")
app.add_typer(profiles_app, name="profiles")
app.add_typer(manifest_app, name="manifest")


@app.command()
def split(
    paths: list[Path] = typer.Argument(..., exists=False, help="PDF files or dirs"),  # noqa: B008
    report_only: bool = typer.Option(False, "--report-only"),
    no_manifest: bool = typer.Option(False, "--no-manifest"),
    output_dir: Path | None = typer.Option(None, "--output-dir"),  # noqa: B008
    profile: str | None = typer.Option(None, "--profile"),
    prompt: str | None = typer.Option(None, "--prompt"),
    force_mode: str | None = typer.Option(None, "--force-mode"),
    model: str = typer.Option(
        ..., "--model", help="LiteLLM model id, e.g. anthropic/claude-opus-4-7"
    ),
    concurrency: int = typer.Option(8, "--concurrency"),
    batch_concurrency: int = typer.Option(1, "--batch-concurrency"),
    dpi: int = typer.Option(150, "--dpi"),
    no_cache: bool = typer.Option(False, "--no-cache"),
    max_cost_usd: float | None = typer.Option(None, "--max-cost-usd"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Detect boundaries and (by default) split each input PDF."""
    if profile is not None and find_profile(profile) is None:
        typer.echo(f"error: profile not found: {profile}", err=True)
        raise typer.Exit(code=2)

    mode: Mode | None = None
    if force_mode is not None:
        if force_mode not in ("scanned", "text"):
            typer.echo("error: --force-mode must be 'scanned' or 'text'", err=True)
            raise typer.Exit(code=2)
        mode = force_mode  # type: ignore[assignment]

    config = Config(
        inputs=[str(p) for p in paths],
        output_dir=output_dir,
        report_only=report_only,
        no_manifest=no_manifest,
        profile=profile,
        prompt=prompt,
        force_mode=mode,
        model=model,
        concurrency=concurrency,
        batch_concurrency=batch_concurrency,
        dpi=dpi,
        no_cache=no_cache,
        max_cost_usd=max_cost_usd,
        dry_run=dry_run,
    )

    client = LLMClient(model=model)
    report = asyncio.run(run_pipeline(config=config, client=client))

    if report.halted_cost_cap:
        raise typer.Exit(code=3)
    if report.failed > 0:
        raise typer.Exit(code=1)


@profiles_app.command("list")
def profiles_list() -> None:
    seen: set[str] = set()
    for d in search_dirs():
        if d.exists():
            for f in sorted(d.glob("*.yaml")):
                if f.stem not in seen:
                    seen.add(f.stem)
                    typer.echo(f.stem)


@profiles_app.command("show")
def profiles_show(name: str) -> None:
    try:
        p = load_profile(name)
    except ProfileNotFoundError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(p.model_dump_json(indent=2))


@manifest_app.command("show")
def manifest_show(path: Path) -> None:
    if not path.exists():
        typer.echo(f"error: no such file: {path}", err=True)
        raise typer.Exit(code=2)
    manifest = read_manifest(path)
    typer.echo(json.dumps(manifest.model_dump(mode="json"), indent=2, default=str))


if __name__ == "__main__":
    app()
