# pdf-splitter

AI-powered PDF splitter that detects **logical document boundaries** inside packets of concatenated documents. Works on both scanned, image-only PDFs and born-digital PDFs; auto-detects which path to use per file.

## How it works

For each input PDF, the tool detects whether the file is scanned or text-bearing, feeds consecutive page pairs to a vision-or-text LLM (routed through [LiteLLM](https://github.com/BerriAI/litellm), so any supported provider works), and asks "is this page the start of a new document?" A `manifest.json` records every boundary with confidence and reason; by default the source is then split into one PDF per segment. Boundary detection runs asynchronously with a bounded concurrency limit and a content-addressed disk cache so re-runs with tuned prompts are free.

## Install

Not yet published to PyPI. For now, install from source:

```bash
# From a clone:
pip install -e .
# Or directly from GitHub:
pip install git+https://github.com/santoshray02/pdf_splitter.git
```

## Quick start

```bash
# Set a LiteLLM-compatible API key for your chosen provider, e.g. Anthropic:
export ANTHROPIC_API_KEY=...

# Split every PDF in a directory, writing split files + manifest.json per file:
pdf-splitter split ./packets/ --model anthropic/claude-opus-4-7

# Review-first workflow: write only the manifest, inspect it, then split:
pdf-splitter split ./packets/ --model anthropic/claude-opus-4-7 --report-only
pdf-splitter manifest show ./packets/out/pkt_017/manifest.json
```

## Overrides: profile, prompt, few-shot

Profiles are user-authored YAML files searched in `./pdf_splitter.profiles/`, `$XDG_CONFIG_HOME/pdf_splitter/profiles/` (or the platform-native user config dir), and the package's built-in profile dir. Example:

```yaml
# ./pdf_splitter.profiles/my-forms.yaml
name: my-forms
description: Internal form packets with Form X-42 cover pages
prompt: |
  A new document starts when a page shows the "Form X-42" header block.
```

```bash
pdf-splitter split pkt.pdf \
  --model anthropic/claude-opus-4-7 \
  --profile my-forms \
  --prompt "Ignore surveyor stamps on continuation pages."

pdf-splitter profiles list        # enumerate available profiles
pdf-splitter profiles show <name> # print the resolved profile
```

## Library use

```python
import asyncio
from pdf_splitter.core.models import Config
from pdf_splitter.core.pipeline import run
from pdf_splitter.providers.llm import LLMClient

MODEL = "anthropic/claude-opus-4-7"
cfg = Config(inputs=["pkt.pdf"], model=MODEL)
asyncio.run(run(config=cfg, client=LLMClient(model=MODEL)))
```

## Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `--model` | *(required)* | LiteLLM model id, e.g. `anthropic/claude-opus-4-7` |
| `--output-dir` | `<input>/out/` | Where to write split files + manifest |
| `--report-only` | off | Write `manifest.json` only; skip splitting |
| `--no-manifest` | off | Split without writing the manifest |
| `--profile` | — | Named YAML profile to apply |
| `--prompt` | — | Free-form prompt override (stacks on profile) |
| `--force-mode` | — | `scanned` or `text` — bypass auto-detect |
| `--concurrency` | 8 | Parallel per-file page-pair classifications |
| `--batch-concurrency` | 1 | Parallel files in a batch |
| `--dpi` | 150 | Render DPI for scanned pages |
| `--no-cache` | off | Bypass the disk classification cache |
| `--max-cost-usd` | — | Hard stop; halts with exit code 3 when reached |
| `--dry-run` | off | Resolve config, do nothing |

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | All inputs processed cleanly (per-page errors surface as `status: "partial"` in the manifest but still exit 0) |
| 1 | One or more per-file failures (corrupt/unreadable PDFs) |
| 2 | Configuration / usage error (unknown profile, invalid flag) |
| 3 | Halted by `--max-cost-usd` |

## Design

See [`docs/superpowers/specs/2026-04-19-pdf-splitter-core-library-cli-design.md`](docs/superpowers/specs/2026-04-19-pdf-splitter-core-library-cli-design.md) for the full v1 design spec, and [`docs/superpowers/plans/`](docs/superpowers/plans/) for the implementation plan.

The core library + CLI is the first of three sub-projects. A FastAPI service and drag-and-drop web UI for manifest review are planned as separate releases.

## License

MIT.
