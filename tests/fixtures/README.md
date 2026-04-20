# Test fixtures

Committed sample PDFs used for manual smoke-testing the CLI against real inputs. Regenerate any time:

```bash
uv run python tests/fixtures/generate_samples.py
```

All three are born-digital (text layer present) and auto-detect as `mode=text`.

| Fixture | Pages | Documents | Expected boundaries | Expected segments |
|---|---|---|---|---|
| `multi_form_packet.pdf` | 8 | 3 (Invoice, PO, Certificate) | page 0 (forced), page 2, page 5 | [0-1], [2-4], [5-7] |
| `double_letter.pdf` | 4 | 2 (Alice's letter, Charlie's letter) | page 0 (forced), page 2 | [0-1], [2-3] |
| `single_report.pdf` | 3 | 1 (annual report) | page 0 (forced) only | [0-2] |

## Smoke test

With an Anthropic API key in the environment:

```bash
export ANTHROPIC_API_KEY=...

# Report-only — no split files written, manifest.json only.
# Pick one to keep cost tiny.
pdf-splitter split tests/fixtures/double_letter.pdf \
  --model anthropic/claude-opus-4-7 \
  --report-only \
  --max-cost-usd 0.20 \
  --output-dir /tmp/smoke

# Inspect the result:
pdf-splitter manifest show /tmp/smoke/double_letter/manifest.json
```

A correct run should produce `boundaries[0].page_index == 0` (forced) and `boundaries[1].page_index == 2` (Charlie's letter starts), giving two segments. Check the `reason` strings on each boundary — the model should cite the changed letterhead/salutation.

## What these don't cover

- **Scanned PDFs.** These are all text-bearing. Scanned-packet behavior is only exercised by the mocked integration tests in `tests/core/test_pipeline.py`, not by a real VLM call. For that, point the CLI at one of your actual Khasra/B1 packets.
- **Edge cases.** Corrupt inputs, out-of-order boundaries, cost-cap halts — all covered by mocked unit tests, not by these fixtures.
