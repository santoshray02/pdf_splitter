# PDF Splitter — Core Library + CLI (v1) Design

**Date:** 2026-04-19
**Status:** Design approved; plan pending
**Scope:** First sub-project of a three-part effort (core library + CLI → FastAPI service → web UI). This document covers only the core library and CLI.

---

## 1. Motivation & Goals

The repo `github.com/santoshray02/pdf_splitter` is a 2019 Cookiecutter scaffold with ~40 lines of real code that splits every PDF in a folder into single-page files using the deprecated PyPDF2 API. It is effectively a blank slate.

We are repurposing it as a modern, 2026-stack, AI-powered PDF splitter that detects **logical document boundaries** in packets that contain multiple concatenated documents — including scanned image-only PDFs (the concrete near-term use case: Chhindwara MP land records — Khasra/B1 packets) and born-digital PDFs (the portfolio / general-purpose story).

### Goals

1. Given a multi-document PDF, detect where each inner document begins.
2. Work on both scanned and born-digital PDFs without requiring the user to pre-classify.
3. Default to fully automatic detection; accept optional overrides (natural-language prompt, named profile, few-shot examples) for accuracy-critical runs.
4. Emit both split PDFs and a detailed `manifest.json` so the result is auditable and QC-reviewable.
5. Ship as a PyPI-publishable package usable as a CLI and as an importable library.
6. Be model-agnostic via a router (LiteLLM); users pick the model via config/env.

### Non-goals (v1)

- HTTP service or web UI (planned as separate sub-projects).
- Auto-repair of corrupt PDFs.
- Training or fine-tuning a custom boundary model.
- Any kind of content extraction beyond boundary detection (no OCR-as-output, no entity extraction).

---

## 2. Architecture

### Package layout

```
pdf_splitter/
├── src/pdf_splitter/
│   ├── __init__.py
│   ├── cli.py              # Typer-based CLI, thin wrapper over core
│   ├── core/
│   │   ├── pipeline.py     # orchestrator: load → detect → (split|report)
│   │   ├── input.py        # PDF open, mode detection (scanned vs text)
│   │   ├── rendering.py    # page → image (PyMuPDF); text extraction
│   │   ├── detector.py     # sliding-window boundary detection (async)
│   │   ├── prompts.py      # default + override prompt assembly
│   │   ├── profiles.py     # profile load/resolve (YAML files)
│   │   ├── manifest.py     # build/read/validate manifest.json
│   │   ├── splitter.py     # apply boundaries → write output PDFs
│   │   └── models.py       # pydantic types: Boundary, Manifest, Config…
│   └── providers/
│       └── llm.py          # LiteLLM call wrapper, retries, cost accounting
├── tests/
├── pyproject.toml          # uv, ruff, pyright, pytest-asyncio
└── README.md
```

### Boundaries

- `cli.py` contains no business logic — it parses flags, builds a `Config`, and calls `pipeline.run(...)`.
- `core/` is pure Python and fully usable as an importable library.
- `providers/llm.py` is the **only** module that knows LiteLLM exists. Every other module sees the interface `async def classify(prompt, images, text) -> BoundaryDecision`.
- `models.py` holds every pydantic v2 type so all modules speak the same shapes.

### Stack decisions (2026 defaults)

| Concern | Choice |
|---|---|
| Python floor | 3.12 |
| Build / env | `uv` |
| Lint / format | `ruff` (replaces black, isort, flake8) |
| Type checking | `pyright` (strict on `core/` and `providers/`) |
| PDF read/render | `pymupdf` |
| PDF write/split | `pypdf` |
| CLI | `typer` |
| Schemas | `pydantic` v2 |
| Async | `anyio` |
| HTTP / retries | `httpx`, `tenacity` |
| Model routing | `litellm` |
| Logging | `structlog` (JSON default, text via flag) |
| Tests | `pytest`, `pytest-asyncio` |

---

## 3. Data flow

One file through the pipeline:

```
CLI flags / library call: run(path, config)
        │
        ▼
input.open(path)
  └─ Returns (PdfDoc, mode)
     mode = "text" if extracted text exceeds a char threshold AND passes
                        a garbage-ratio check
            else "scanned"
     `--force-mode` overrides
        │
        ▼
rendering.prepare(doc, mode)
  ├─ mode="scanned"  → render each page to PNG at DPI=150 (configurable)
  └─ mode="text"     → extract text per page (layout-aware)
        │
        ▼
detector.detect(pages, config)
  ├─ Assemble effective prompt =
  │     system template + (profile? + user_prompt? + few_shot examples?)
  ├─ For i in 1..N-1 (page 0 is always a boundary, forced=True):
  │     async classify(page[i-1], page[i])
  │       → BoundaryDecision(is_boundary, confidence, reason)
  ├─ anyio semaphore caps concurrency (default 8)
  └─ Returns List[BoundaryDecision] aligned to page indices
        │
        ▼
manifest.build(doc, decisions)
  └─ Manifest { source, mode, model, created_at, cost_usd,
                boundaries[...], segments[...] }
        │
        ▼
branch on config:
  ├─ report_only → write manifest.json, exit
  └─ else        → splitter.apply(doc, manifest) → write N PDFs + manifest.json
```

### Notable subtleties

- **Mode detection is per-file, not per-batch** — a directory can mix scanned and born-digital; each file picks its own path.
- **Page 0 is always a segment start** — no model call is wasted on it; marked `forced=True` in the manifest.
- **Confidence lives in the manifest, not in the filename** — downstream QC workflows can filter / re-review low-confidence boundaries without renaming files.
- **Cost accounting is per-run**, written into the manifest. Audit-friendly.
- **Caching**: `classify()` is pure over `(prompt, images|text)`. A disk cache keyed on `sha256(prompt_payload)` makes re-runs on the same inputs free — critical while tuning prompts/profiles.

---

## 4. Interfaces

### 4.1 CLI

Single main command with subcommands (Typer):

```
pdf-splitter split <path>...
  --report-only                 # write manifest.json only, no split files
  --no-manifest                 # split without writing manifest
  --output-dir <dir>            # default: <input>/out/
  --profile <name>              # e.g., khasra-b1
  --prompt "<text>"             # free-form override (stacks on profile)
  --examples <path>             # few-shot dir: {before.png,after.png,label.json}
  --force-mode {scanned,text}   # skip auto-detect
  --model <litellm-model-id>    # override env default
  --concurrency <int>           # per-file page-classification concurrency; default 8
  --batch-concurrency <int>     # parallel files in a batch; default 1 (safe)
  --dpi <int>                   # default 150
  --no-cache                    # bypass classify cache
  --max-cost-usd <float>        # opt-in hard stop
  --dry-run                     # resolve config + show plan, do nothing
  --log-level <lvl>
  --log-format {json,text}

pdf-splitter profiles list
pdf-splitter profiles show <name>
pdf-splitter manifest show <path>    # pretty-print for QC review
```

**Batch semantics:** `<path>...` accepts files and directories (recursive). Each input file gets its own output subdir and its own manifest. A failure in one file does not abort the batch.

### 4.2 Profiles

YAML files. Search order (first match wins):

```
./pdf_splitter.profiles/<name>.yaml
$XDG_CONFIG_HOME/pdf_splitter/profiles/<name>.yaml
<package>/profiles/<name>.yaml   # built-ins shipped with the package
```

Example:

```yaml
# khasra-b1.yaml
name: khasra-b1
description: Chhindwara MP land records (Form P-II cover, B1 register)
mode_hint: scanned            # optional; overrides auto-detect
dpi: 200                      # profile can tune rendering
prompt: |
  A new document starts when a page shows the "Form P-II" header
  or a Khasra register title block. Ignore intermediate register pages.
few_shot:                     # optional inline examples
  - before: examples/p2_prev.png
    after:  examples/p2_cover.png
    is_boundary: true
```

**Override composition** (lowest to highest priority): built-in default prompt → profile → `--prompt` → `--examples`. All stack into the final system prompt sent via LiteLLM.

### 4.3 Manifest schema

Pydantic v2 model, serialized as JSON:

```json
{
  "schema_version": "1",
  "source": "lot_3756/packet_017.pdf",
  "mode": "scanned",
  "model": "anthropic/claude-opus-4-7",
  "created_at": "2026-04-19T14:02:11Z",
  "config": { "dpi": 200, "profile": "khasra-b1", "concurrency": 8 },
  "cost_usd": 0.42,
  "page_count": 64,
  "boundaries": [
    { "page_index": 0,  "confidence": 1.0,  "reason": "first page", "forced": true },
    { "page_index": 12, "confidence": 0.94, "reason": "Form P-II header detected" },
    { "page_index": 29, "confidence": 0.71, "reason": "page-number reset + cover block" }
  ],
  "segments": [
    { "index": 0, "start": 0,  "end": 11, "suggested_filename": "packet_017_doc_001.pdf" },
    { "index": 1, "start": 12, "end": 28, "suggested_filename": "packet_017_doc_002.pdf" },
    { "index": 2, "start": 29, "end": 63, "suggested_filename": "packet_017_doc_003.pdf" }
  ],
  "status": "ok"
}
```

`status` values: `"ok"`, `"partial"` (some pages errored), `"halted_cost_cap"`.

**`suggested_filename` pattern:** `{source_stem}_doc_{NNN}.pdf`, where `NNN` is 3-digit zero-padded and 1-based. Collisions on write get `_NNN_v2`, `_v3`, etc.

---

## 5. Error handling & failure isolation

| Surface | Handling |
|---|---|
| Transient LLM errors (rate limits, 5xx, timeouts) | `tenacity` exponential backoff with jitter: 5 tries, 1s→30s. Final failure → record `BoundaryDecision(error=…, confidence=0, is_boundary=False)`; pipeline continues. |
| Malformed model output | LiteLLM JSON mode + pydantic validation on every response. Parse failure → one repair-prompt retry → then same error path. No silent coercion. |
| Corrupt / unreadable PDFs | `input.open()` catches and skips; run continues; exit code reflects partial failure. No auto-repair. |
| Ambiguous mode detection | Char-count threshold AND garbage-ratio check; if ambiguous, default to `scanned`. `--force-mode` overrides. |
| Per-file failures in batch mode | Each file runs in its own pipeline task; one file's crash never aborts the batch. Final summary reports `N succeeded, M failed`. |
| Cost safety | `--max-cost-usd <float>` is **opt-in**. LiteLLM reports per-call cost; we accumulate and hard-stop with a partial manifest (`status: "halted_cost_cap"`). Without the flag, cost is tracked and printed but not capped. |
| Profile / prompt / example validation | Profiles validated against pydantic schema at load time. Few-shot example images validated (exist, loadable, size). Bad inputs → usage error before any LLM call. |

### CLI exit codes

- `0` — all inputs processed cleanly
- `1` — one or more per-file or per-page failures (manifest written for what succeeded)
- `2` — configuration / usage error (no work attempted)
- `3` — halted by `--max-cost-usd`

### Logging

`structlog` JSON output by default; `--log-level` and `--log-format text` flags. Every LLM call logged with: file, page pair, model, tokens, cost, latency, cache hit/miss.

---

## 6. Testing strategy

Three layers. All CI runs are offline, no network, no API keys.

### 6.1 Unit tests (fast, deterministic)

Per-module, mocked boundaries:

- `input.py` — mode detection on synthetic PDFs (text-only, scanned-only, mixed, garbage text layer, corrupt).
- `rendering.py` — page-to-image at various DPIs; text extraction order; empty pages.
- `prompts.py` — override composition order; snapshot the final assembled prompt.
- `profiles.py` — YAML load, schema validation, precedence, bad-YAML errors.
- `manifest.py` — build from decisions; round-trip serialize/parse; segment derivation; schema versioning.
- `splitter.py` — apply a known boundary list; assert output page counts and order.
- `models.py` — pydantic edge cases.

### 6.2 Integration tests (LLM-mocked, wired)

End-to-end pipeline with `providers/llm.py` patched to a **recorded-response fixture driver**:

- Fixture set: real `(prompt, page_images) → BoundaryDecision` recordings, committed as JSON; tests replay them deterministically.
- Covers: scanned path, text path, mixed-mode batch, profile override, few-shot override, cost accounting, cache hits on re-run, `--report-only`, `--max-cost-usd` halt, partial-batch failure, malformed-response repair path.
- `record_fixtures.py` dev script regenerates fixtures against the real API, gated by `ANTHROPIC_API_KEY` + explicit `--record` flag. Never runs in CI.

### 6.3 CLI smoke tests

Typer's `CliRunner`: every documented command + flag combo invoked; exit codes and output files asserted. Catches argument-parsing regressions without touching core logic.

### Coverage

Target: 85%+ on `core/`, 70%+ overall. Not religious — the rule is every bug fix adds a regression test.

### Dev loop (pyproject.toml)

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
addopts = "-q --strict-markers"

[tool.ruff]
target-version = "py312"

[tool.pyright]
strict = ["src/pdf_splitter/core", "src/pdf_splitter/providers"]
```

### CI

GitHub Actions matrix on 3.12 / 3.13:
`uv sync → ruff check → ruff format --check → pyright → pytest`.
Separate `release` workflow builds and publishes to PyPI on tagged commits.

### Regression benchmark (manual, pre-release)

A separate private fixtures repo contains a small set of real land-records PDFs with human-verified boundary ground truth. A `benchmark.py` runs the pipeline against them and reports precision/recall per boundary. Used before releases to catch model drift.

---

## 7. Open items deferred to implementation plan

- Exact pydantic schema for `BoundaryDecision`, `Config`, `Manifest` (tightened while writing `models.py`).
- Concrete default system prompt text (iterate during integration-test fixture recording).
- Cache directory location (platform-appropriate via `platformdirs`).
- Thumbnails alongside the manifest: **not written in v1**; the future UI sub-project renders on demand.

---

## 8. Out of scope for this spec

The following are explicitly for later sub-projects, tracked separately:

- **FastAPI service** wrapping this library (HTTP endpoints, jobs, uploads).
- **Web UI** for drag-and-drop + manifest review + split approval.
- **Non-PDF inputs** (TIFFs, image folders).
- **Content extraction** beyond boundary detection.
