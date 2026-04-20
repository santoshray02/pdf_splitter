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
