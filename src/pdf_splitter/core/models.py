"""Pydantic v2 schemas shared across the pipeline."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Mode = Literal["scanned", "text"]
Status = Literal["ok", "partial", "halted_cost_cap"]


class Boundary(BaseModel):
    """A detected document boundary, as recorded in the manifest."""

    model_config = ConfigDict(extra="forbid")

    page_index: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    forced: bool = False


class Segment(BaseModel):
    """A contiguous page range that becomes one output PDF."""

    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=0)
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    suggested_filename: str

    @model_validator(mode="after")
    def _check_order(self) -> Segment:
        if self.end < self.start:
            raise ValueError("Segment end must be >= start")
        return self


class BoundaryDecision(BaseModel):
    """The detector's per-page-pair output (transient, not persisted)."""

    model_config = ConfigDict(extra="forbid")

    page_index: int = Field(ge=0)
    is_boundary: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    error: str | None = None

    @property
    def is_error(self) -> bool:
        return self.error is not None


class FewShotExample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    before: Path
    after: Path
    is_boundary: bool


class ProfileConfig(BaseModel):
    """Shape of a YAML profile file."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str = ""
    mode_hint: Mode | None = None
    dpi: int | None = None
    prompt: str = ""
    few_shot: list[FewShotExample] = Field(default_factory=list[FewShotExample])


class Config(BaseModel):
    """Runtime configuration built from CLI args or library call kwargs."""

    model_config = ConfigDict(extra="forbid")

    inputs: list[str]
    output_dir: Path | None = None
    report_only: bool = False
    no_manifest: bool = False
    profile: str | None = None
    prompt: str | None = None
    examples: Path | None = None
    force_mode: Mode | None = None
    model: str | None = None
    concurrency: int = 8
    batch_concurrency: int = 1
    dpi: int = 150
    no_cache: bool = False
    max_cost_usd: float | None = None
    dry_run: bool = False


class Manifest(BaseModel):
    """Persisted per-file audit trail."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1"
    source: str
    mode: Mode
    model: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    config: dict[str, Any]
    cost_usd: float
    page_count: int
    boundaries: list[Boundary]
    segments: list[Segment]
    status: Status = "ok"
