# PDF Splitter Core Library + CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the 2019 scaffold at `github.com/santoshray02/pdf_splitter` into a 2026-stack, AI-powered PDF splitter that detects logical document boundaries in both scanned and born-digital PDFs, shipping as a PyPI-publishable library + CLI.

**Architecture:** Modern Python package (src layout). A thin Typer CLI wraps a pure-library core. The library pipeline detects mode per file (scanned vs born-digital), renders pages or extracts text, runs sliding-window async boundary classification through a LiteLLM-routed model, writes a `manifest.json` with per-boundary reasons and confidence, and optionally splits the PDF. A single provider module (`providers/llm.py`) isolates all LiteLLM usage.

**Tech Stack:** Python 3.12; `uv` (build/env), `ruff` (lint/format), `pyright` (types); `pymupdf` (render), `pypdf` (write/split); `typer` (CLI), `pydantic` v2 (schemas); `anyio` + `httpx` (async), `tenacity` (retries); `litellm` (model routing); `platformdirs` (cache dir); `structlog` (logging); `pytest` + `pytest-asyncio`.

**Reference:** `docs/superpowers/specs/2026-04-19-pdf-splitter-core-library-cli-design.md`

**Working branch:** `master` (per user preference — no worktree).

---

## File Structure

**Files to remove (2019 cookiecutter leftovers):**
- `pdf_splitter/pdf_splitter.py` (old PyPDF2 implementation)
- `pdf_splitter/cli.py`, `pdf_splitter/__init__.py` (old stubs)
- `setup.py`, `setup.cfg`, `tox.ini`, `Makefile`, `MANIFEST.in`, `requirements_dev.txt`
- `HISTORY.rst`, `AUTHORS.rst`, `CONTRIBUTING.rst`
- `docs/` (Sphinx scaffold; our new `docs/superpowers/` stays)
- `tests/test_pdf_splitter.py`, `tests/__init__.py` (old stubs)

**Files to keep:**
- `LICENSE` (MIT)
- `README.rst` → replaced by `README.md` in Task 14
- `docs/superpowers/` (our specs + this plan)

**Files to create (src layout):**

```
pyproject.toml
README.md
src/pdf_splitter/
├── __init__.py
├── cli.py
├── core/
│   ├── __init__.py
│   ├── cache.py
│   ├── detector.py
│   ├── input.py
│   ├── manifest.py
│   ├── models.py
│   ├── pipeline.py
│   ├── profiles.py
│   ├── prompts.py
│   ├── rendering.py
│   └── splitter.py
└── providers/
    ├── __init__.py
    └── llm.py
tests/
├── __init__.py
├── conftest.py
├── test_cli.py
├── core/
│   ├── __init__.py
│   ├── test_cache.py
│   ├── test_detector.py
│   ├── test_input.py
│   ├── test_manifest.py
│   ├── test_models.py
│   ├── test_pipeline.py
│   ├── test_profiles.py
│   ├── test_prompts.py
│   ├── test_rendering.py
│   └── test_splitter.py
└── providers/
    ├── __init__.py
    ├── _fixture_driver.py
    └── test_llm.py
.github/workflows/ci.yml
.github/workflows/release.yml
```

Each `core/` file has one clear responsibility. `providers/llm.py` is the only module that imports `litellm` — the rest speak through a narrow interface.

---

## Task 0: Remove 2019 scaffold and set up 2026 skeleton

**Files:**
- Remove: `pdf_splitter/pdf_splitter.py`, `pdf_splitter/cli.py`, `pdf_splitter/__init__.py`, `setup.py`, `setup.cfg`, `tox.ini`, `Makefile`, `MANIFEST.in`, `requirements_dev.txt`, `HISTORY.rst`, `AUTHORS.rst`, `CONTRIBUTING.rst`, `README.rst`, `docs/conf.py`, `docs/index.rst`, `docs/Makefile`, `docs/make.bat`, `docs/*.rst`, `tests/test_pdf_splitter.py`, `tests/__init__.py`
- Create: `pyproject.toml`, `src/pdf_splitter/__init__.py`, `src/pdf_splitter/core/__init__.py`, `src/pdf_splitter/providers/__init__.py`, `tests/__init__.py`, `tests/core/__init__.py`, `tests/providers/__init__.py`, `tests/conftest.py`, `.gitignore`

- [ ] **Step 1: Remove all 2019 scaffold files**

```bash
cd /c/Users/raysk/projects/experiments/pdf_splitter
git rm -r pdf_splitter/ setup.py setup.cfg tox.ini Makefile MANIFEST.in requirements_dev.txt HISTORY.rst AUTHORS.rst CONTRIBUTING.rst README.rst docs/conf.py docs/index.rst docs/Makefile docs/make.bat tests/
# re-create empty tests dir (git rm -r removed it)
mkdir -p tests/core tests/providers src/pdf_splitter/core src/pdf_splitter/providers
# Sphinx .rst files under docs/
git ls-files docs/ | grep '\.rst$' | xargs -r git rm
```

Do NOT touch `docs/superpowers/` (spec + plan live there).

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling>=1.27"]
build-backend = "hatchling.build"

[project]
name = "pdf-splitter"
version = "0.1.0"
description = "AI-powered PDF splitter that detects logical document boundaries in scanned and born-digital PDFs"
readme = "README.md"
requires-python = ">=3.12"
license = "MIT"
authors = [{ name = "Santosh Ray" }]
classifiers = [
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Operating System :: OS Independent",
]
dependencies = [
    "anyio>=4.3",
    "httpx>=0.27",
    "litellm>=1.55",
    "platformdirs>=4.2",
    "pydantic>=2.7",
    "pymupdf>=1.24",
    "pypdf>=5.1",
    "pyyaml>=6.0",
    "structlog>=24.1",
    "tenacity>=9.0",
    "typer>=0.12",
]

[project.optional-dependencies]
dev = [
    "pyright>=1.1.380",
    "pytest>=8.2",
    "pytest-asyncio>=0.23",
    "reportlab>=4.2",   # generating synthetic PDFs in tests
    "ruff>=0.6",
]

[project.scripts]
pdf-splitter = "pdf_splitter.cli:app"

[tool.hatch.build.targets.wheel]
packages = ["src/pdf_splitter"]

[tool.ruff]
target-version = "py312"
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM", "RUF"]

[tool.pyright]
include = ["src", "tests"]
strict = ["src/pdf_splitter/core", "src/pdf_splitter/providers"]
pythonVersion = "3.12"

[tool.pytest.ini_options]
asyncio_mode = "auto"
addopts = "-q --strict-markers"
testpaths = ["tests"]
```

- [ ] **Step 3: Create empty package init files**

Create these four files with exactly the content shown:

`src/pdf_splitter/__init__.py`:
```python
"""AI-powered PDF splitter — boundary detection + manifest."""

__version__ = "0.1.0"
```

`src/pdf_splitter/core/__init__.py`:
```python
```

`src/pdf_splitter/providers/__init__.py`:
```python
```

`tests/__init__.py`, `tests/core/__init__.py`, `tests/providers/__init__.py`: each is an empty file.

- [ ] **Step 4: Create `tests/conftest.py`**

```python
"""Shared test fixtures."""
from __future__ import annotations

import io
from pathlib import Path

import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def _make_pdf(pages: list[str]) -> bytes:
    """Build a text-layer PDF from a list of per-page strings."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    for text in pages:
        c.drawString(72, 720, text)
        c.showPage()
    c.save()
    return buf.getvalue()


@pytest.fixture
def text_pdf_factory(tmp_path: Path):
    """Factory: list[str] of page texts → path to a text-layer PDF."""
    counter = {"i": 0}

    def make(pages: list[str], name: str | None = None) -> Path:
        counter["i"] += 1
        path = tmp_path / (name or f"text_{counter['i']}.pdf")
        path.write_bytes(_make_pdf(pages))
        return path

    return make
```

- [ ] **Step 5: Create `.gitignore`**

```gitignore
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
.pyright/
.venv/
dist/
build/
*.egg-info/
.coverage
htmlcov/
```

- [ ] **Step 6: Install and verify the toolchain**

```bash
uv venv
uv pip install -e ".[dev]"
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```

Expected: ruff clean, pyright clean, pytest collects 0 tests and reports "no tests ran" (exit 5 is acceptable for an empty suite — we'll fix in Task 1).

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore: reset 2019 scaffold, scaffold 2026 src-layout package"
```

---

## Task 1: Pydantic models

**Files:**
- Create: `src/pdf_splitter/core/models.py`
- Test: `tests/core/test_models.py`

These types are the shared language of every later module. Defined first so every subsequent task imports stable shapes.

- [ ] **Step 1: Write the failing tests**

`tests/core/test_models.py`:
```python
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
```

- [ ] **Step 2: Run the tests — expect failure**

```bash
uv run pytest tests/core/test_models.py -v
```

Expected: `ModuleNotFoundError: No module named 'pdf_splitter.core.models'`.

- [ ] **Step 3: Implement `src/pdf_splitter/core/models.py`**

```python
"""Pydantic v2 schemas shared across the pipeline."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

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
    def _check_order(self) -> "Segment":
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
    few_shot: list[FewShotExample] = Field(default_factory=list)


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
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    config: dict
    cost_usd: float
    page_count: int
    boundaries: list[Boundary]
    segments: list[Segment]
    status: Status = "ok"
```

- [ ] **Step 4: Run the tests — expect pass**

```bash
uv run pytest tests/core/test_models.py -v
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add src/pdf_splitter/core/models.py tests/core/test_models.py
git commit -m "feat(core): add pydantic models for pipeline"
```

---

## Task 2: Manifest builder

**Files:**
- Create: `src/pdf_splitter/core/manifest.py`
- Test: `tests/core/test_manifest.py`

Derives `Segments` from a list of `Boundary`s, composes the full `Manifest`, and writes/reads JSON.

- [ ] **Step 1: Write the failing tests**

`tests/core/test_manifest.py`:
```python
from __future__ import annotations

import json
from pathlib import Path

from pdf_splitter.core.manifest import build_manifest, write_manifest, read_manifest
from pdf_splitter.core.models import Boundary, BoundaryDecision, Manifest


def _decisions(*triples: tuple[int, bool, float]) -> list[BoundaryDecision]:
    return [
        BoundaryDecision(page_index=i, is_boundary=b, confidence=c, reason="test")
        for (i, b, c) in triples
    ]


def test_build_manifest_forces_page_zero_boundary():
    m = build_manifest(
        source="pkt.pdf",
        mode="scanned",
        model="anthropic/claude-opus-4-7",
        config={"dpi": 200},
        cost_usd=0.0,
        page_count=5,
        decisions=_decisions((1, False, 0.1), (2, True, 0.9), (3, False, 0.2), (4, False, 0.2)),
    )
    assert m.boundaries[0].page_index == 0
    assert m.boundaries[0].forced is True
    assert [b.page_index for b in m.boundaries] == [0, 2]


def test_build_manifest_segments():
    m = build_manifest(
        source="pkt.pdf",
        mode="scanned",
        model="m",
        config={},
        cost_usd=0.0,
        page_count=5,
        decisions=_decisions((1, False, 0.1), (2, True, 0.9), (3, False, 0.2), (4, False, 0.2)),
    )
    assert [(s.start, s.end) for s in m.segments] == [(0, 1), (2, 4)]
    assert m.segments[0].suggested_filename == "pkt_doc_001.pdf"
    assert m.segments[1].suggested_filename == "pkt_doc_002.pdf"


def test_build_manifest_errors_become_status_partial():
    decisions = [
        BoundaryDecision(page_index=1, is_boundary=False, confidence=0.0, reason="", error="x"),
        BoundaryDecision(page_index=2, is_boundary=True, confidence=0.9, reason="ok"),
    ]
    m = build_manifest(
        source="p.pdf",
        mode="scanned",
        model="m",
        config={},
        cost_usd=0.0,
        page_count=3,
        decisions=decisions,
    )
    assert m.status == "partial"


def test_build_manifest_single_segment_when_no_inner_boundaries():
    m = build_manifest(
        source="p.pdf", mode="text", model="m", config={}, cost_usd=0.0,
        page_count=3, decisions=_decisions((1, False, 0.1), (2, False, 0.1)),
    )
    assert len(m.segments) == 1
    assert m.segments[0].start == 0 and m.segments[0].end == 2


def test_write_and_read_round_trip(tmp_path: Path):
    m = build_manifest(
        source="p.pdf", mode="text", model="m", config={}, cost_usd=0.0,
        page_count=2, decisions=_decisions((1, True, 0.8),),
    )
    out = tmp_path / "manifest.json"
    write_manifest(out, m)
    loaded = read_manifest(out)
    assert loaded == m

    raw = json.loads(out.read_text())
    assert raw["schema_version"] == "1"
```

- [ ] **Step 2: Run the tests — expect failure**

```bash
uv run pytest tests/core/test_manifest.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `src/pdf_splitter/core/manifest.py`**

```python
"""Build, serialize, and read Manifest instances."""
from __future__ import annotations

from pathlib import Path

from pdf_splitter.core.models import (
    Boundary,
    BoundaryDecision,
    Manifest,
    Mode,
    Segment,
)


def _source_stem(source: str) -> str:
    return Path(source).stem


def build_manifest(
    *,
    source: str,
    mode: Mode,
    model: str,
    config: dict,
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
    status = "partial" if has_errors else "ok"

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
    path.write_text(manifest.model_dump_json(indent=2))


def read_manifest(path: Path) -> Manifest:
    return Manifest.model_validate_json(path.read_text())
```

- [ ] **Step 4: Run the tests — expect pass**

```bash
uv run pytest tests/core/test_manifest.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/pdf_splitter/core/manifest.py tests/core/test_manifest.py
git commit -m "feat(core): build/serialize Manifest with segment derivation"
```

---

## Task 3: PDF input + mode detection

**Files:**
- Create: `src/pdf_splitter/core/input.py`
- Test: `tests/core/test_input.py`

Opens a PDF (pymupdf), inspects the extracted text to classify as `scanned` or `text`, and surfaces a narrow domain exception for corrupt inputs.

- [ ] **Step 1: Write the failing tests**

`tests/core/test_input.py`:
```python
from __future__ import annotations

from pathlib import Path

import pytest

from pdf_splitter.core.input import InputError, detect_mode, open_pdf


def test_text_pdf_detected_as_text(text_pdf_factory):
    path = text_pdf_factory(["Hello world, this is a typical page of prose."] * 3)
    doc = open_pdf(path)
    assert detect_mode(doc) == "text"


def test_empty_text_pdf_detected_as_scanned(text_pdf_factory):
    # Empty pages (reportlab produces pages with no text)
    path = text_pdf_factory(["", "", ""])
    doc = open_pdf(path)
    assert detect_mode(doc) == "scanned"


def test_corrupt_pdf_raises_input_error(tmp_path: Path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not-a-pdf")
    with pytest.raises(InputError):
        open_pdf(bad)


def test_missing_file_raises_input_error(tmp_path: Path):
    with pytest.raises(InputError):
        open_pdf(tmp_path / "nope.pdf")


def test_garbage_text_layer_detected_as_scanned(text_pdf_factory):
    # A lot of replacement chars should flag as scanned.
    path = text_pdf_factory(["\ufffd" * 500] * 2)
    doc = open_pdf(path)
    assert detect_mode(doc) == "scanned"
```

- [ ] **Step 2: Run the tests — expect failure**

```bash
uv run pytest tests/core/test_input.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `src/pdf_splitter/core/input.py`**

```python
"""PDF open + scanned/text mode detection."""
from __future__ import annotations

from pathlib import Path

import pymupdf

from pdf_splitter.core.models import Mode

TEXT_CHAR_THRESHOLD = 100  # min chars per page (averaged) to be considered text-bearing
GARBAGE_RATIO_THRESHOLD = 0.20  # fraction of chars that are replacement/control


class InputError(Exception):
    """Raised for unreadable, missing, or corrupt PDFs."""


def open_pdf(path: Path) -> pymupdf.Document:
    if not Path(path).exists():
        raise InputError(f"PDF not found: {path}")
    try:
        return pymupdf.open(path)
    except Exception as exc:  # pymupdf raises several types
        raise InputError(f"Cannot open {path}: {exc}") from exc


def _garbage_ratio(text: str) -> float:
    if not text:
        return 0.0
    bad = sum(1 for ch in text if ch == "\ufffd" or (ord(ch) < 32 and ch not in "\t\n\r"))
    return bad / len(text)


def detect_mode(doc: pymupdf.Document) -> Mode:
    pages_text: list[str] = [page.get_text("text") for page in doc]
    total_chars = sum(len(t) for t in pages_text)
    avg = total_chars / max(len(pages_text), 1)
    if avg < TEXT_CHAR_THRESHOLD:
        return "scanned"
    combined = "".join(pages_text)
    if _garbage_ratio(combined) > GARBAGE_RATIO_THRESHOLD:
        return "scanned"
    return "text"
```

- [ ] **Step 4: Run the tests — expect pass**

```bash
uv run pytest tests/core/test_input.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/pdf_splitter/core/input.py tests/core/test_input.py
git commit -m "feat(core): open PDFs and classify scanned vs text mode"
```

---

## Task 4: Page rendering and text extraction

**Files:**
- Create: `src/pdf_splitter/core/rendering.py`
- Test: `tests/core/test_rendering.py`

Renders a page to PNG bytes at a target DPI; extracts per-page text.

- [ ] **Step 1: Write the failing tests**

`tests/core/test_rendering.py`:
```python
from __future__ import annotations

from pdf_splitter.core.input import open_pdf
from pdf_splitter.core.rendering import extract_text_per_page, render_page_png


def test_render_page_returns_png_bytes(text_pdf_factory):
    doc = open_pdf(text_pdf_factory(["hello"]))
    png = render_page_png(doc, 0, dpi=100)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_render_dpi_scales_output_size(text_pdf_factory):
    doc = open_pdf(text_pdf_factory(["hello"]))
    small = render_page_png(doc, 0, dpi=72)
    large = render_page_png(doc, 0, dpi=200)
    assert len(large) > len(small)


def test_extract_text_per_page_returns_one_entry_per_page(text_pdf_factory):
    doc = open_pdf(text_pdf_factory(["alpha page", "beta page", "gamma page"]))
    texts = extract_text_per_page(doc)
    assert len(texts) == 3
    assert "alpha" in texts[0]
    assert "beta" in texts[1]
    assert "gamma" in texts[2]
```

- [ ] **Step 2: Run the tests — expect failure**

```bash
uv run pytest tests/core/test_rendering.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `src/pdf_splitter/core/rendering.py`**

```python
"""Render pages to PNG bytes and extract per-page text."""
from __future__ import annotations

import pymupdf


def render_page_png(doc: pymupdf.Document, page_index: int, *, dpi: int) -> bytes:
    page = doc[page_index]
    zoom = dpi / 72.0
    matrix = pymupdf.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    return pix.tobytes("png")


def extract_text_per_page(doc: pymupdf.Document) -> list[str]:
    return [page.get_text("text") for page in doc]
```

- [ ] **Step 4: Run the tests — expect pass**

```bash
uv run pytest tests/core/test_rendering.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/pdf_splitter/core/rendering.py tests/core/test_rendering.py
git commit -m "feat(core): render page PNGs and extract per-page text"
```

---

## Task 5: Profiles

**Files:**
- Create: `src/pdf_splitter/core/profiles.py`
- Create: `src/pdf_splitter/profiles/__init__.py` (built-in profile dir marker)
- Test: `tests/core/test_profiles.py`

Loads YAML profile files with a documented search order.

- [ ] **Step 1: Write the failing tests**

`tests/core/test_profiles.py`:
```python
from __future__ import annotations

from pathlib import Path

import pytest

from pdf_splitter.core.profiles import ProfileNotFoundError, find_profile, load_profile


def _write_profile(path: Path, name: str, prompt: str) -> None:
    path.write_text(f"name: {name}\ndescription: d\nprompt: |\n  {prompt}\n")


def test_load_profile_from_local_dir(tmp_path: Path, monkeypatch):
    local = tmp_path / "pdf_splitter.profiles"
    local.mkdir()
    _write_profile(local / "foo.yaml", "foo", "hello")
    monkeypatch.chdir(tmp_path)
    p = load_profile("foo")
    assert p.name == "foo"
    assert "hello" in p.prompt


def test_load_profile_from_xdg(tmp_path: Path, monkeypatch):
    xdg = tmp_path / "xdg"
    (xdg / "pdf_splitter" / "profiles").mkdir(parents=True)
    _write_profile(xdg / "pdf_splitter" / "profiles" / "bar.yaml", "bar", "xdg")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.chdir(tmp_path)  # no local profile
    p = load_profile("bar")
    assert "xdg" in p.prompt


def test_local_shadows_xdg(tmp_path: Path, monkeypatch):
    local = tmp_path / "pdf_splitter.profiles"
    local.mkdir()
    _write_profile(local / "baz.yaml", "baz", "LOCAL")
    xdg = tmp_path / "xdg"
    (xdg / "pdf_splitter" / "profiles").mkdir(parents=True)
    _write_profile(xdg / "pdf_splitter" / "profiles" / "baz.yaml", "baz", "XDG")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.chdir(tmp_path)
    p = load_profile("baz")
    assert "LOCAL" in p.prompt


def test_missing_profile_raises(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "nope"))
    with pytest.raises(ProfileNotFoundError):
        load_profile("does-not-exist")


def test_find_profile_returns_none_for_missing(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "nope"))
    assert find_profile("does-not-exist") is None
```

- [ ] **Step 2: Run the tests — expect failure**

```bash
uv run pytest tests/core/test_profiles.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Create the built-in profiles dir marker**

`src/pdf_splitter/profiles/__init__.py`:
```python
"""Built-in YAML profiles ship here."""
```

- [ ] **Step 4: Implement `src/pdf_splitter/core/profiles.py`**

```python
"""Load YAML profile files, searching local → XDG → package builtins."""
from __future__ import annotations

import os
from importlib import resources
from pathlib import Path

import yaml

from pdf_splitter.core.models import ProfileConfig


class ProfileNotFoundError(Exception):
    """Raised when a named profile cannot be found in any search location."""


def _local_dir() -> Path:
    return Path.cwd() / "pdf_splitter.profiles"


def _xdg_dir() -> Path:
    root = os.environ.get("XDG_CONFIG_HOME")
    base = Path(root) if root else Path.home() / ".config"
    return base / "pdf_splitter" / "profiles"


def _builtin_dir() -> Path:
    return Path(str(resources.files("pdf_splitter.profiles")))


def _candidates(name: str) -> list[Path]:
    return [
        _local_dir() / f"{name}.yaml",
        _xdg_dir() / f"{name}.yaml",
        _builtin_dir() / f"{name}.yaml",
    ]


def find_profile(name: str) -> Path | None:
    for p in _candidates(name):
        if p.exists():
            return p
    return None


def load_profile(name: str) -> ProfileConfig:
    path = find_profile(name)
    if path is None:
        raise ProfileNotFoundError(f"Profile not found: {name}")
    data = yaml.safe_load(path.read_text()) or {}
    return ProfileConfig.model_validate(data)
```

- [ ] **Step 5: Run the tests — expect pass**

```bash
uv run pytest tests/core/test_profiles.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add src/pdf_splitter/core/profiles.py src/pdf_splitter/profiles/ tests/core/test_profiles.py
git commit -m "feat(core): load YAML profiles with local/XDG/builtin search"
```

---

## Task 6: Prompt composition

**Files:**
- Create: `src/pdf_splitter/core/prompts.py`
- Test: `tests/core/test_prompts.py`

Assembles the final classifier prompt from: default template → profile prompt → user prompt → few-shot. Deterministic, pure function.

- [ ] **Step 1: Write the failing tests**

`tests/core/test_prompts.py`:
```python
from __future__ import annotations

from pdf_splitter.core.models import FewShotExample, ProfileConfig
from pdf_splitter.core.prompts import DEFAULT_SYSTEM_PROMPT, compose_prompt


def test_default_only():
    prompt = compose_prompt(profile=None, user_prompt=None, examples=[])
    assert prompt == DEFAULT_SYSTEM_PROMPT


def test_profile_appended():
    p = ProfileConfig(name="p", prompt="look for Form P-II")
    prompt = compose_prompt(profile=p, user_prompt=None, examples=[])
    assert DEFAULT_SYSTEM_PROMPT in prompt
    assert "look for Form P-II" in prompt


def test_user_prompt_overrides_after_profile():
    p = ProfileConfig(name="p", prompt="profile text")
    prompt = compose_prompt(profile=p, user_prompt="user override", examples=[])
    # user prompt appears AFTER profile, winning precedence-wise
    assert prompt.index("user override") > prompt.index("profile text")


def test_few_shot_examples_appear_last(tmp_path):
    b = tmp_path / "before.png"; b.write_bytes(b"\x89PNG\r\n\x1a\n")
    a = tmp_path / "after.png"; a.write_bytes(b"\x89PNG\r\n\x1a\n")
    ex = [FewShotExample(before=b, after=a, is_boundary=True)]
    prompt = compose_prompt(profile=None, user_prompt="u", examples=ex)
    assert prompt.rindex("Example") > prompt.index("u")
```

- [ ] **Step 2: Run the tests — expect failure**

```bash
uv run pytest tests/core/test_prompts.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `src/pdf_splitter/core/prompts.py`**

```python
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
    parts: list[str] = [DEFAULT_SYSTEM_PROMPT.rstrip()]
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
```

- [ ] **Step 4: Run the tests — expect pass**

```bash
uv run pytest tests/core/test_prompts.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/pdf_splitter/core/prompts.py tests/core/test_prompts.py
git commit -m "feat(core): compose classifier prompt from default + profile + user + examples"
```

---

## Task 7: Disk cache

**Files:**
- Create: `src/pdf_splitter/core/cache.py`
- Test: `tests/core/test_cache.py`

Keyed disk cache for `(prompt, payload) → BoundaryDecision`. Pure content-addressed; no TTL.

- [ ] **Step 1: Write the failing tests**

`tests/core/test_cache.py`:
```python
from __future__ import annotations

from pathlib import Path

from pdf_splitter.core.cache import DiskCache, make_cache_key
from pdf_splitter.core.models import BoundaryDecision


def test_cache_key_is_stable_for_same_inputs():
    k1 = make_cache_key(prompt="hello", payload=b"abc")
    k2 = make_cache_key(prompt="hello", payload=b"abc")
    assert k1 == k2


def test_cache_key_changes_with_prompt():
    k1 = make_cache_key(prompt="hello", payload=b"abc")
    k2 = make_cache_key(prompt="goodbye", payload=b"abc")
    assert k1 != k2


def test_cache_key_changes_with_payload():
    k1 = make_cache_key(prompt="hello", payload=b"abc")
    k2 = make_cache_key(prompt="hello", payload=b"xyz")
    assert k1 != k2


def test_disk_cache_set_and_get(tmp_path: Path):
    c = DiskCache(tmp_path / "cache")
    decision = BoundaryDecision(page_index=1, is_boundary=True, confidence=0.9, reason="r")
    c.set("k1", decision)
    assert c.get("k1") == decision


def test_disk_cache_miss_returns_none(tmp_path: Path):
    c = DiskCache(tmp_path / "cache")
    assert c.get("never-written") is None


def test_disk_cache_persists_across_instances(tmp_path: Path):
    path = tmp_path / "cache"
    d = BoundaryDecision(page_index=1, is_boundary=False, confidence=0.0, reason="r")
    DiskCache(path).set("k", d)
    assert DiskCache(path).get("k") == d
```

- [ ] **Step 2: Run the tests — expect failure**

```bash
uv run pytest tests/core/test_cache.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `src/pdf_splitter/core/cache.py`**

```python
"""Simple content-addressed disk cache for BoundaryDecision records."""
from __future__ import annotations

import hashlib
from pathlib import Path

from platformdirs import user_cache_dir

from pdf_splitter.core.models import BoundaryDecision


def make_cache_key(*, prompt: str, payload: bytes) -> str:
    h = hashlib.sha256()
    h.update(prompt.encode("utf-8"))
    h.update(b"\x00")
    h.update(payload)
    return h.hexdigest()


def default_cache_dir() -> Path:
    return Path(user_cache_dir("pdf_splitter")) / "classify"


class DiskCache:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)

    def _file(self, key: str) -> Path:
        return self.path / f"{key}.json"

    def get(self, key: str) -> BoundaryDecision | None:
        f = self._file(key)
        if not f.exists():
            return None
        return BoundaryDecision.model_validate_json(f.read_text())

    def set(self, key: str, decision: BoundaryDecision) -> None:
        self._file(key).write_text(decision.model_dump_json())
```

- [ ] **Step 4: Run the tests — expect pass**

```bash
uv run pytest tests/core/test_cache.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/pdf_splitter/core/cache.py tests/core/test_cache.py
git commit -m "feat(core): disk cache for boundary decisions"
```

---

## Task 8: LLM provider wrapper

**Files:**
- Create: `src/pdf_splitter/providers/llm.py`
- Create: `tests/providers/_fixture_driver.py`
- Test: `tests/providers/test_llm.py`

This is the **only** module that imports `litellm`. It calls `litellm.acompletion(...)` with JSON mode, validates the response with pydantic, retries transients via `tenacity`, and one-shot-repairs malformed JSON. Also reports call cost.

Tests mock `litellm.acompletion` directly — no network.

- [ ] **Step 1: Write the failing tests**

`tests/providers/_fixture_driver.py`:
```python
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
```

`tests/providers/test_llm.py`:
```python
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
    drv = fake_driver([
        FakeResponse('{"is_boundary": true, "confidence": 0.91, "reason": "header"}')
    ])
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
    fake_driver([
        FakeResponse('{"is_boundary": false, "confidence": 0.12, "reason": "continuation"}')
    ])
    client = LLMClient(model="anthropic/claude-opus-4-7")
    decision, _ = await client.classify(
        page_index=3, prompt="sys", prev_text="prev", curr_text="curr"
    )
    assert decision.is_boundary is False


async def test_malformed_json_triggers_repair_retry(fake_driver):
    fake_driver([
        FakeResponse("not json"),
        FakeResponse('{"is_boundary": true, "confidence": 0.8, "reason": "ok"}'),
    ])
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
    fake_driver([
        RuntimeError("429 rate limit"),
        FakeResponse('{"is_boundary": true, "confidence": 0.7, "reason": "ok"}'),
    ])
    client = LLMClient(model="m", max_attempts=3)
    decision, _ = await client.classify(page_index=1, prompt="sys", prev_text="a", curr_text="b")
    assert decision.is_boundary is True


async def test_exhausted_retries_records_error(fake_driver):
    fake_driver([
        RuntimeError("boom"), RuntimeError("boom"), RuntimeError("boom"),
    ])
    client = LLMClient(model="m", max_attempts=3)
    decision, _ = await client.classify(page_index=1, prompt="sys", prev_text="a", curr_text="b")
    assert decision.is_error
    assert "boom" in (decision.error or "")
```

- [ ] **Step 2: Run the tests — expect failure**

```bash
uv run pytest tests/providers/test_llm.py -v
```

Expected: `ModuleNotFoundError: No module named 'pdf_splitter.providers.llm'`.

- [ ] **Step 3: Implement `src/pdf_splitter/providers/llm.py`**

```python
"""LiteLLM-routed boundary classifier. Only module that imports litellm."""
from __future__ import annotations

import base64
import json
from typing import Any

import structlog
from litellm import acompletion as _acompletion
from pydantic import ValidationError
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from pdf_splitter.core.models import BoundaryDecision

log = structlog.get_logger(__name__)


class _ParsedDecision(BoundaryDecision):
    """Thin alias so we can validate model output without the page_index/error."""


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
    return json.loads(content)


class LLMClient:
    def __init__(self, *, model: str, max_attempts: int = 5, temperature: float = 0.0):
        self.model = model
        self.max_attempts = max_attempts
        self.temperature = temperature

    async def _raw_call(self, messages: list[dict[str, Any]]) -> tuple[str, float]:
        resp = await _acompletion(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            response_format={"type": "json_object"},
        )
        content = resp["choices"][0]["message"]["content"]
        cost = float(resp.get("_hidden_params", {}).get("response_cost") or 0.0)
        return content, cost

    async def _call_with_retries(self, messages: list[dict[str, Any]]) -> tuple[str, float]:
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.max_attempts),
                wait=wait_exponential_jitter(initial=1, max=30),
                retry=retry_if_exception_type(Exception),
                reraise=True,
            ):
                with attempt:
                    return await self._raw_call(messages)
        except RetryError as exc:
            raise exc.last_attempt.exception() or RuntimeError("retry exhausted") from exc
        raise RuntimeError("unreachable")

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
        except (ValueError, KeyError, ValidationError):
            pass

        # Repair retry: one more call, stricter instruction.
        repair_messages = messages + [
            {"role": "user", "content": 'Respond with valid JSON ONLY: {"is_boundary": bool, "confidence": number, "reason": string}'}
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
```

- [ ] **Step 4: Run the tests — expect pass**

```bash
uv run pytest tests/providers/test_llm.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/pdf_splitter/providers/llm.py tests/providers/_fixture_driver.py tests/providers/test_llm.py
git commit -m "feat(providers): LiteLLM-backed async classifier with retries and repair"
```

---

## Task 9: Detector (sliding-window)

**Files:**
- Create: `src/pdf_splitter/core/detector.py`
- Test: `tests/core/test_detector.py`

Given a rendered/text-extracted document, runs per-page-pair `classify()` through a bounded `anyio` semaphore. Skips page 0 (forced boundary). Consults the disk cache.

- [ ] **Step 1: Write the failing tests**

`tests/core/test_detector.py`:
```python
from __future__ import annotations

from pathlib import Path

import pytest

from pdf_splitter.core.cache import DiskCache
from pdf_splitter.core.detector import detect_boundaries
from pdf_splitter.core.models import BoundaryDecision


class _FakeClient:
    """Records calls; returns scripted decisions keyed by page_index."""

    def __init__(self, scripted: dict[int, BoundaryDecision]):
        self._s = scripted
        self.calls: list[int] = []

    async def classify(self, *, page_index: int, **kwargs) -> tuple[BoundaryDecision, float]:
        self.calls.append(page_index)
        return self._s[page_index], 0.01


async def test_skips_page_zero(tmp_path: Path):
    client = _FakeClient({
        1: BoundaryDecision(page_index=1, is_boundary=False, confidence=0.1, reason=""),
        2: BoundaryDecision(page_index=2, is_boundary=True, confidence=0.9, reason=""),
    })
    pages = [b"p0", b"p1", b"p2"]
    decisions, cost = await detect_boundaries(
        pages=pages, mode="scanned", prompt="sys",
        client=client, cache=None, concurrency=2,  # type: ignore[arg-type]
    )
    assert 0 not in client.calls
    assert sorted(client.calls) == [1, 2]
    assert [d.page_index for d in decisions] == [1, 2]
    assert cost == pytest.approx(0.02)


async def test_uses_cache_on_hit(tmp_path: Path):
    client = _FakeClient({})  # should never be called
    cache = DiskCache(tmp_path / "c")
    # Pre-populate cache: cache key is computed by detector; we cheat by running once with real client.
    primed = _FakeClient({
        1: BoundaryDecision(page_index=1, is_boundary=True, confidence=0.8, reason="r"),
    })
    pages = [b"p0", b"p1"]
    await detect_boundaries(
        pages=pages, mode="scanned", prompt="sys",
        client=primed, cache=cache, concurrency=1,  # type: ignore[arg-type]
    )
    # Now run with a client that would error if called:
    decisions, cost = await detect_boundaries(
        pages=pages, mode="scanned", prompt="sys",
        client=client, cache=cache, concurrency=1,  # type: ignore[arg-type]
    )
    assert decisions[0].is_boundary is True
    assert cost == 0.0
    assert client.calls == []


async def test_errors_pass_through():
    client = _FakeClient({
        1: BoundaryDecision(
            page_index=1, is_boundary=False, confidence=0.0, reason="", error="x"
        ),
    })
    decisions, _ = await detect_boundaries(
        pages=[b"p0", b"p1"], mode="scanned", prompt="sys",
        client=client, cache=None, concurrency=1,  # type: ignore[arg-type]
    )
    assert decisions[0].is_error
```

- [ ] **Step 2: Run the tests — expect failure**

```bash
uv run pytest tests/core/test_detector.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `src/pdf_splitter/core/detector.py`**

```python
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

        if cache is not None:
            payload = _page_payload(mode, prev, curr)
            key = make_cache_key(prompt=prompt, payload=payload)
            hit = cache.get(key)
            if hit is not None:
                results[i] = hit
                return

        async with sem:
            if mode == "scanned":
                decision, cost = await client.classify(
                    page_index=page_index, prompt=prompt,
                    prev_image=prev, curr_image=curr,  # type: ignore[arg-type]
                )
            else:
                decision, cost = await client.classify(
                    page_index=page_index, prompt=prompt,
                    prev_text=prev, curr_text=curr,  # type: ignore[arg-type]
                )
        results[i] = decision
        async with cost_lock:
            cost_total += cost
        if cache is not None and not decision.is_error:
            payload = _page_payload(mode, prev, curr)
            key = make_cache_key(prompt=prompt, payload=payload)
            cache.set(key, decision)

    async with anyio.create_task_group() as tg:
        for i in range(n - 1):
            tg.start_soon(worker, i)

    out: list[BoundaryDecision] = [r for r in results if r is not None]
    return out, cost_total
```

- [ ] **Step 4: Run the tests — expect pass**

```bash
uv run pytest tests/core/test_detector.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/pdf_splitter/core/detector.py tests/core/test_detector.py
git commit -m "feat(core): sliding-window boundary detector with cache + semaphore"
```

---

## Task 10: Splitter (manifest → output PDFs)

**Files:**
- Create: `src/pdf_splitter/core/splitter.py`
- Test: `tests/core/test_splitter.py`

Given a `Manifest` and the source PDF, writes one output file per segment. Collisions get `_v2`, `_v3`, …

- [ ] **Step 1: Write the failing tests**

`tests/core/test_splitter.py`:
```python
from __future__ import annotations

from pathlib import Path

import pypdf

from pdf_splitter.core.manifest import build_manifest
from pdf_splitter.core.models import BoundaryDecision
from pdf_splitter.core.splitter import apply_split


def _pdf_page_count(path: Path) -> int:
    return len(pypdf.PdfReader(str(path)).pages)


def test_apply_split_writes_one_file_per_segment(tmp_path: Path, text_pdf_factory):
    src = text_pdf_factory(["p0", "p1", "p2", "p3", "p4"], name="pkt.pdf")
    manifest = build_manifest(
        source=str(src), mode="text", model="m", config={}, cost_usd=0.0, page_count=5,
        decisions=[
            BoundaryDecision(page_index=1, is_boundary=False, confidence=0.1, reason=""),
            BoundaryDecision(page_index=2, is_boundary=True, confidence=0.9, reason=""),
            BoundaryDecision(page_index=3, is_boundary=False, confidence=0.1, reason=""),
            BoundaryDecision(page_index=4, is_boundary=False, confidence=0.1, reason=""),
        ],
    )
    out_dir = tmp_path / "out"
    written = apply_split(source_pdf=src, manifest=manifest, output_dir=out_dir)
    assert len(written) == 2
    assert _pdf_page_count(written[0]) == 2  # pages 0,1
    assert _pdf_page_count(written[1]) == 3  # pages 2,3,4
    assert written[0].name == "pkt_doc_001.pdf"
    assert written[1].name == "pkt_doc_002.pdf"


def test_apply_split_handles_collisions(tmp_path: Path, text_pdf_factory):
    src = text_pdf_factory(["a", "b"], name="pkt.pdf")
    manifest = build_manifest(
        source=str(src), mode="text", model="m", config={}, cost_usd=0.0, page_count=2,
        decisions=[
            BoundaryDecision(page_index=1, is_boundary=False, confidence=0.1, reason=""),
        ],
    )
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "pkt_doc_001.pdf").write_bytes(b"already here")
    written = apply_split(source_pdf=src, manifest=manifest, output_dir=out_dir)
    assert written[0].name == "pkt_doc_001_v2.pdf"
```

- [ ] **Step 2: Run the tests — expect failure**

```bash
uv run pytest tests/core/test_splitter.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `src/pdf_splitter/core/splitter.py`**

```python
"""Apply a Manifest to a source PDF and write one file per segment."""
from __future__ import annotations

from pathlib import Path

import pypdf

from pdf_splitter.core.models import Manifest


def _unique_path(out_dir: Path, name: str) -> Path:
    candidate = out_dir / name
    if not candidate.exists():
        return candidate
    stem, suffix = Path(name).stem, Path(name).suffix
    i = 2
    while True:
        candidate = out_dir / f"{stem}_v{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def apply_split(
    *,
    source_pdf: Path,
    manifest: Manifest,
    output_dir: Path,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    reader = pypdf.PdfReader(str(source_pdf))
    written: list[Path] = []
    for segment in manifest.segments:
        writer = pypdf.PdfWriter()
        for p in range(segment.start, segment.end + 1):
            writer.add_page(reader.pages[p])
        out_path = _unique_path(output_dir, segment.suggested_filename)
        with out_path.open("wb") as f:
            writer.write(f)
        written.append(out_path)
    return written
```

- [ ] **Step 4: Run the tests — expect pass**

```bash
uv run pytest tests/core/test_splitter.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/pdf_splitter/core/splitter.py tests/core/test_splitter.py
git commit -m "feat(core): split source PDF per manifest segments with collision suffixing"
```

---

## Task 11: Pipeline orchestrator

**Files:**
- Create: `src/pdf_splitter/core/pipeline.py`
- Test: `tests/core/test_pipeline.py`

Ties everything together: open → detect mode → prepare pages → compose prompt → detect boundaries → build manifest → (split | report). Handles per-file isolation, cost cap, dry-run.

- [ ] **Step 1: Write the failing tests**

`tests/core/test_pipeline.py`:
```python
from __future__ import annotations

from pathlib import Path

import pytest

from pdf_splitter.core.manifest import read_manifest
from pdf_splitter.core.models import BoundaryDecision, Config
from pdf_splitter.core.pipeline import RunReport, run


class _ScriptedClient:
    def __init__(self, by_page: dict[int, BoundaryDecision]):
        self._by_page = by_page

    async def classify(self, *, page_index: int, **kwargs) -> tuple[BoundaryDecision, float]:
        return self._by_page[page_index], 0.005


async def test_pipeline_writes_manifest_and_split_files(
    tmp_path: Path, text_pdf_factory, monkeypatch
):
    src = text_pdf_factory(["first doc", "cont", "second doc", "cont"], name="pkt.pdf")
    out = tmp_path / "out"
    cfg = Config(inputs=[str(src)], output_dir=out, model="m")

    client = _ScriptedClient({
        1: BoundaryDecision(page_index=1, is_boundary=False, confidence=0.1, reason=""),
        2: BoundaryDecision(page_index=2, is_boundary=True, confidence=0.9, reason="new doc"),
        3: BoundaryDecision(page_index=3, is_boundary=False, confidence=0.1, reason=""),
    })

    report: RunReport = await run(config=cfg, client=client)

    assert report.succeeded == 1 and report.failed == 0
    manifest_path = out / "pkt" / "manifest.json"
    assert manifest_path.exists()
    manifest = read_manifest(manifest_path)
    assert manifest.page_count == 4
    assert len(manifest.segments) == 2
    # Split files exist
    split_files = sorted((out / "pkt").glob("pkt_doc_*.pdf"))
    assert [p.name for p in split_files] == ["pkt_doc_001.pdf", "pkt_doc_002.pdf"]


async def test_report_only_skips_splitting(tmp_path: Path, text_pdf_factory):
    src = text_pdf_factory(["a", "b"], name="pkt.pdf")
    out = tmp_path / "out"
    cfg = Config(inputs=[str(src)], output_dir=out, model="m", report_only=True)
    client = _ScriptedClient({
        1: BoundaryDecision(page_index=1, is_boundary=False, confidence=0.1, reason=""),
    })
    await run(config=cfg, client=client)
    assert (out / "pkt" / "manifest.json").exists()
    assert list((out / "pkt").glob("pkt_doc_*.pdf")) == []


async def test_dry_run_does_nothing(tmp_path: Path, text_pdf_factory):
    src = text_pdf_factory(["a", "b"], name="pkt.pdf")
    out = tmp_path / "out"
    cfg = Config(inputs=[str(src)], output_dir=out, model="m", dry_run=True)

    class _ShouldNotCall:
        async def classify(self, **kwargs):  # pragma: no cover - asserted not called
            raise AssertionError("dry_run should not call classifier")

    report = await run(config=cfg, client=_ShouldNotCall())
    assert report.succeeded == 0 and report.failed == 0
    assert not out.exists()


async def test_per_file_failure_does_not_abort_batch(tmp_path: Path, text_pdf_factory):
    good = text_pdf_factory(["a", "b"], name="good.pdf")
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    out = tmp_path / "out"
    cfg = Config(inputs=[str(good), str(bad)], output_dir=out, model="m")
    client = _ScriptedClient({
        1: BoundaryDecision(page_index=1, is_boundary=False, confidence=0.1, reason=""),
    })
    report = await run(config=cfg, client=client)
    assert report.succeeded == 1 and report.failed == 1
    assert (out / "good" / "manifest.json").exists()


async def test_cost_cap_halts_run(tmp_path: Path, text_pdf_factory):
    src = text_pdf_factory(["a", "b", "c"], name="pkt.pdf")
    out = tmp_path / "out"
    cfg = Config(inputs=[str(src)], output_dir=out, model="m", max_cost_usd=0.001)

    # Each call costs 0.005 — first call will already exceed the cap.
    client = _ScriptedClient({
        1: BoundaryDecision(page_index=1, is_boundary=False, confidence=0.1, reason=""),
        2: BoundaryDecision(page_index=2, is_boundary=True, confidence=0.9, reason=""),
    })
    await run(config=cfg, client=client)
    manifest = read_manifest(out / "pkt" / "manifest.json")
    assert manifest.status == "halted_cost_cap"
```

- [ ] **Step 2: Run the tests — expect failure**

```bash
uv run pytest tests/core/test_pipeline.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `src/pdf_splitter/core/pipeline.py`**

```python
"""Per-file pipeline orchestration and batch runner."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

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


async def _process_one(
    source: Path, config: Config, client: Classifier, cost_budget_left: float | None
) -> tuple[float, bool]:
    """Returns (cost_spent, halted_by_cost_cap)."""
    profile = load_profile(config.profile) if config.profile else None
    effective_dpi = profile.dpi if (profile and profile.dpi) else config.dpi
    mode_override = config.force_mode or (profile.mode_hint if profile else None)
    prompt = compose_prompt(profile=profile, user_prompt=config.prompt, examples=[])

    doc = open_pdf(source)
    mode = mode_override or detect_mode(doc)
    page_count = doc.page_count

    if mode == "scanned":
        pages: list[bytes] | list[str] = [
            render_page_png(doc, i, dpi=effective_dpi) for i in range(page_count)
        ]
    else:
        pages = extract_text_per_page(doc)

    cache = None if config.no_cache else DiskCache(default_cache_dir())

    decisions: list[BoundaryDecision] = []
    total_cost = 0.0
    halted = False
    # We emit cost-cap by iterating page pairs ourselves, not through detect_boundaries,
    # so that we can stop mid-stream. Reuse detect_boundaries for small docs when no cap.
    if config.max_cost_usd is None:
        decisions, total_cost = await detect_boundaries(
            pages=pages, mode=mode, prompt=prompt, client=client,
            cache=cache, concurrency=config.concurrency,
        )
    else:
        for i in range(page_count - 1):
            partial, cost = await detect_boundaries(
                pages=pages[i : i + 2], mode=mode, prompt=prompt, client=client,
                cache=cache, concurrency=1,
            )
            # detect_boundaries indexed partial from page_index=1; remap:
            if partial:
                d = partial[0]
                decisions.append(
                    BoundaryDecision(
                        page_index=i + 1,
                        is_boundary=d.is_boundary,
                        confidence=d.confidence,
                        reason=d.reason,
                        error=d.error,
                    )
                )
            total_cost += cost
            if total_cost >= config.max_cost_usd:
                halted = True
                break

    manifest = build_manifest(
        source=str(source), mode=mode,
        model=config.model or "unknown",
        config=config.model_dump(mode="json", exclude={"inputs"}),
        cost_usd=total_cost, page_count=page_count, decisions=decisions,
    )
    if halted:
        manifest = manifest.model_copy(update={"status": "halted_cost_cap"})

    output_subdir = _resolve_output_dir(source, config)
    output_subdir.mkdir(parents=True, exist_ok=True)
    if not config.no_manifest:
        write_manifest(output_subdir / "manifest.json", manifest)
    if not config.report_only and not halted:
        apply_split(source_pdf=source, manifest=manifest, output_dir=output_subdir)
    return total_cost, halted


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
                _, halted = await _process_one(src, config, client, None)
                report.succeeded += 1
                if halted:
                    report.halted_cost_cap = True
            except InputError as exc:
                log.warning("pipeline.input_error", source=str(src), error=str(exc))
                report.failed += 1
            except Exception as exc:  # pragma: no cover - defense in depth
                log.exception("pipeline.unexpected", source=str(src), error=str(exc))
                report.failed += 1

    await asyncio.gather(*(one(f) for f in files))
    return report
```

- [ ] **Step 4: Run the tests — expect pass**

```bash
uv run pytest tests/core/test_pipeline.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/pdf_splitter/core/pipeline.py tests/core/test_pipeline.py
git commit -m "feat(core): pipeline orchestrator with per-file isolation and cost cap"
```

---

## Task 12: CLI

**Files:**
- Create: `src/pdf_splitter/cli.py`
- Test: `tests/test_cli.py`

Typer app wiring `split`, `profiles`, `manifest` subcommands into the library. Instantiates the real `LLMClient` at the edge; library tests already cover core behavior.

- [ ] **Step 1: Write the failing tests**

`tests/test_cli.py`:
```python
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from pdf_splitter.cli import app
from pdf_splitter.core.models import BoundaryDecision


runner = CliRunner()


def _async_client(by_page: dict[int, BoundaryDecision]):
    client = AsyncMock()

    async def classify(*, page_index: int, **kwargs):
        return by_page[page_index], 0.0

    client.classify.side_effect = classify
    return client


def test_dry_run_exits_zero(text_pdf_factory):
    src = text_pdf_factory(["a", "b"], name="pkt.pdf")
    result = runner.invoke(app, ["split", str(src), "--dry-run", "--model", "m"])
    assert result.exit_code == 0


def test_profiles_list_runs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pdf_splitter.profiles").mkdir()
    (tmp_path / "pdf_splitter.profiles" / "demo.yaml").write_text(
        "name: demo\ndescription: d\nprompt: p\n"
    )
    result = runner.invoke(app, ["profiles", "list"])
    assert result.exit_code == 0
    assert "demo" in result.stdout


def test_manifest_show_pretty_prints(tmp_path):
    from pdf_splitter.core.manifest import build_manifest, write_manifest
    m = build_manifest(
        source="x.pdf", mode="text", model="m", config={}, cost_usd=0.0,
        page_count=1, decisions=[],
    )
    out = tmp_path / "manifest.json"
    write_manifest(out, m)
    result = runner.invoke(app, ["manifest", "show", str(out)])
    assert result.exit_code == 0
    assert "schema_version" in result.stdout


def test_split_invokes_pipeline(text_pdf_factory, tmp_path):
    src = text_pdf_factory(["a", "b"], name="pkt.pdf")
    with patch("pdf_splitter.cli.LLMClient") as mock_client_cls:
        mock_client_cls.return_value = _async_client({
            1: BoundaryDecision(page_index=1, is_boundary=False, confidence=0.1, reason=""),
        })
        result = runner.invoke(
            app, ["split", str(src), "--model", "m", "--output-dir", str(tmp_path / "out")]
        )
    assert result.exit_code == 0
    assert (tmp_path / "out" / "pkt" / "manifest.json").exists()


def test_unknown_profile_returns_exit_2(text_pdf_factory):
    src = text_pdf_factory(["a", "b"], name="pkt.pdf")
    result = runner.invoke(app, ["split", str(src), "--model", "m", "--profile", "nope"])
    assert result.exit_code == 2
```

- [ ] **Step 2: Run the tests — expect failure**

```bash
uv run pytest tests/test_cli.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `src/pdf_splitter/cli.py`**

```python
"""Typer CLI — thin wrapper over pdf_splitter.core.pipeline."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import typer

from pdf_splitter.core.manifest import read_manifest
from pdf_splitter.core.models import Config, Mode
from pdf_splitter.core.pipeline import run as run_pipeline
from pdf_splitter.core.profiles import ProfileNotFoundError, find_profile, load_profile
from pdf_splitter.providers.llm import LLMClient

app = typer.Typer(add_completion=False, help="AI-powered PDF splitter.")
profiles_app = typer.Typer(help="Manage YAML profiles.")
manifest_app = typer.Typer(help="Inspect split manifests.")
app.add_typer(profiles_app, name="profiles")
app.add_typer(manifest_app, name="manifest")


@app.command()
def split(
    paths: list[Path] = typer.Argument(..., exists=False, help="PDF files or dirs"),
    report_only: bool = typer.Option(False, "--report-only"),
    no_manifest: bool = typer.Option(False, "--no-manifest"),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir"),
    profile: Optional[str] = typer.Option(None, "--profile"),
    prompt: Optional[str] = typer.Option(None, "--prompt"),
    force_mode: Optional[str] = typer.Option(None, "--force-mode"),
    model: str = typer.Option(..., "--model", help="LiteLLM model id, e.g. anthropic/claude-opus-4-7"),
    concurrency: int = typer.Option(8, "--concurrency"),
    batch_concurrency: int = typer.Option(1, "--batch-concurrency"),
    dpi: int = typer.Option(150, "--dpi"),
    no_cache: bool = typer.Option(False, "--no-cache"),
    max_cost_usd: Optional[float] = typer.Option(None, "--max-cost-usd"),
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
    if report.failed > 0 and report.succeeded == 0:
        raise typer.Exit(code=1)
    if report.failed > 0:
        raise typer.Exit(code=1)


@profiles_app.command("list")
def profiles_list() -> None:
    seen: set[str] = set()
    import os
    search_dirs = [
        Path.cwd() / "pdf_splitter.profiles",
        Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
        / "pdf_splitter" / "profiles",
    ]
    for d in search_dirs:
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
```

- [ ] **Step 4: Run the tests — expect pass**

```bash
uv run pytest tests/test_cli.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Run the full suite and lints**

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

Expected: everything green. Fix any ruff/pyright warnings surfaced here.

- [ ] **Step 6: Commit**

```bash
git add src/pdf_splitter/cli.py tests/test_cli.py
git commit -m "feat(cli): Typer CLI for split, profiles, manifest subcommands"
```

---

## Task 13: GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create `.github/workflows/ci.yml`**

```yaml
name: ci

on:
  push:
    branches: [master]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - name: Set up Python ${{ matrix.python-version }}
        run: uv python install ${{ matrix.python-version }}
      - name: Sync
        run: uv sync --all-extras
      - name: Ruff check
        run: uv run ruff check .
      - name: Ruff format
        run: uv run ruff format --check .
      - name: Pyright
        run: uv run pyright
      - name: Pytest
        run: uv run pytest
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions matrix for 3.12 and 3.13"
```

---

## Task 14: README + PyPI release workflow

**Files:**
- Create: `README.md`
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Create `README.md`**

```markdown
# pdf-splitter

AI-powered PDF splitter that detects **logical document boundaries** inside packets of concatenated documents. Works on both scanned, image-only PDFs and born-digital PDFs; auto-detects which path to use per file.

## Install

```bash
pip install pdf-splitter
```

## Quick start

```bash
# Set a LiteLLM-compatible API key, e.g. for Anthropic:
export ANTHROPIC_API_KEY=...

# Split every PDF in a directory, writing split files + manifest.json per file:
pdf-splitter split ./packets/ --model anthropic/claude-opus-4-7

# Review-first workflow: write only the manifest, inspect it, then split:
pdf-splitter split ./packets/ --model anthropic/claude-opus-4-7 --report-only
pdf-splitter manifest show ./packets/out/pkt_017/manifest.json
```

## Overrides: profile, prompt, few-shot

```bash
pdf-splitter split pkt.pdf \
  --model anthropic/claude-opus-4-7 \
  --profile khasra-b1 \
  --prompt "Ignore surveyor stamps on continuation pages."
```

## Library use

```python
import asyncio
from pdf_splitter.core.models import Config
from pdf_splitter.core.pipeline import run
from pdf_splitter.providers.llm import LLMClient

cfg = Config(inputs=["pkt.pdf"], model="anthropic/claude-opus-4-7")
asyncio.run(run(config=cfg, client=LLMClient(model=cfg.model)))
```

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | All inputs processed cleanly |
| 1 | Some per-file or per-page failures |
| 2 | Configuration / usage error |
| 3 | Halted by `--max-cost-usd` |

## License

MIT.
```

- [ ] **Step 2: Create `.github/workflows/release.yml`**

```yaml
name: release

on:
  push:
    tags: ["v*"]

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv python install 3.12
      - run: uv build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

- [ ] **Step 3: Commit**

```bash
git add README.md .github/workflows/release.yml
git commit -m "docs: modern README; add PyPI release workflow"
```

---

## Task 15: Final verification

- [ ] **Step 1: Run the full local verification**

```bash
cd /c/Users/raysk/projects/experiments/pdf_splitter
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest -v
```

Expected: all four commands succeed with zero warnings or failures.

- [ ] **Step 2: Install-and-run smoke test**

```bash
uv run pdf-splitter --help
uv run pdf-splitter split --help
uv run pdf-splitter profiles list
```

Expected: help text prints for each; `profiles list` either lists something or prints nothing (both are fine; non-zero exit is a failure).

- [ ] **Step 3: End-to-end manual test with a real scanned PDF**

Pick one scanned land-record PDF from the user's existing lot directories, run:

```bash
export ANTHROPIC_API_KEY=...
uv run pdf-splitter split <path-to-one-pdf> \
  --model anthropic/claude-opus-4-7 \
  --output-dir ./_smoke \
  --report-only
```

Open `_smoke/<stem>/manifest.json` and eyeball the boundaries. If the model's reasons are coherent and the boundary count matches expectations, the MVP works.

- [ ] **Step 4: Commit any final fixes discovered during smoke testing**

```bash
git add -p
git commit -m "fix: <describe issue>"
```

- [ ] **Step 5: Tag v0.1.0 (optional — only when ready to publish)**

```bash
git tag -a v0.1.0 -m "v0.1.0: initial release"
git push origin v0.1.0
```

---

## Self-Review

**Spec coverage check:** every spec section mapped.

| Spec §                                   | Task(s)            |
|-----------------------------------------|--------------------|
| 2. Architecture / package layout        | 0, 1–12 by module  |
| 2. Stack decisions                      | 0                  |
| 3. Data flow (mode detect, rendering, detector, manifest, split) | 3, 4, 9, 2, 10, 11 |
| 4.1 CLI flags + subcommands             | 12                 |
| 4.2 Profiles (YAML, search order, overrides) | 5, 6          |
| 4.3 Manifest schema                     | 1, 2               |
| 5. Error handling (transient, malformed, corrupt, per-file, cost cap) | 7, 3, 11 |
| 5. Exit codes                           | 12                 |
| 5. Logging (structlog)                  | 7, 11              |
| 6.1 Unit tests                          | every core task    |
| 6.2 Integration tests (fixture driver)  | 7, 11              |
| 6.3 CLI smoke tests                     | 12                 |
| 6. CI                                   | 13                 |
| 7. Release                              | 14                 |

**Placeholder scan:** no "TBD", "TODO", "implement later", or hand-wave fragments remain. Each task has the full code it requires.

**Type consistency:** `BoundaryDecision` / `Manifest` / `Segment` / `Config` signatures used in every downstream task match the definitions in Task 1. `Classifier` protocol (Task 9) matches `LLMClient.classify` signature (Task 8). Cache `get/set` signatures in Task 7 match usage in Task 9. CLI flag names match `Config` field names.

Self-review passes; plan is ready.
