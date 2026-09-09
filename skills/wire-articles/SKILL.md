---
name: wire-articles
description: "Wire-articles scout. Fetches RSS, picks AI news, calls LLM to write original grounded articles, saves JSON to /tmp/lain/scouts/scout_wire.json. Run by run.sh; no agent loads this directly."
---

# Wire Articles — RSS → AI Writing

## When to use
Called by the orchestrator (step 6), after the editor and render.
Deterministic RSS retrieval + LLM article writing. The output feeds the
scrolling news ticker on the front page — it is **not** part of `edition.json`.

## Files to write
- `/tmp/lain/scouts/scout_wire.json` — JSON array of wire articles

## Workflow

1. Run the deterministic retrieval script (run.sh does this):
```bash
python3 <repo>/scripts/content/wire_articles.py --max 5 \
  --out /tmp/lain/scouts/scout_wire.json \
  --model deepseek-v4-flash-0731 --provider litellm
```
⚠️ The provider is **`litellm`**, never anything else. `run.sh` passes it
explicitly (as `$PIPELINE_PROVIDER`) rather than relying on the script's own
defaults, so the backend is chosen in exactly one place.

2. Validate output:
```bash
python3 -c "import json; d=json.load(open('/tmp/lain/scouts/scout_wire.json')); print(f'{len(d)} wire articles')"
```

3. If empty → write `[]` and proceed. The run.sh guards with `WIRE_COUNT -gt 0`.

## Wire Articles JSON Shape

```json
[
  {
    "headline": "OpenAI Unveils o5...",
    "body": "Full article text...\n\n*Editorial note*\n*— Written by AI (flash)*",
    "source": "The Verge",
    "source_url": "https://...",
    "original_title": "Original RSS headline",
    "published": "Mon, 30 Jun 2025 14:00:00 GMT",
    "generated_at": "2025-06-30T14:30:00+00:00"
  }
]
```

## Ticker injection (post-render)

After render.py produces index.html, run.sh runs:
```bash
python3 <repo>/scripts/inject/inject_wire_ticker.py \
  /tmp/lain/output/index.html \
  /tmp/lain/scouts/scout_wire.json \
  --output /tmp/lain/output/index.html
```

This injects the scrolling banner between masthead and lead story — no other changes.

## All content MUST be in English.

## Pitfalls

### 1. Google News RSS resolution is fragile
If Google changes its URL token format, `resolve_url()` in `wire_articles.py` may fail. The script falls back to HTTP redirect but many CDNs block headless requests. **Fix:** add direct publisher RSS feeds instead of Google News, in `skills/_shared/sources.md` under the `## Wire Articles (\`wire-articles\`)` section's `json` block (that's what `wire_articles.py`'s `FEEDS` loads — not hardcoded in the script anymore).

### 2. No trafilatura available (PEP 668)
The system is PEP 668-locked: `pip install`, `uv pip install --system`, and `python3 -m venv` may all fail. Without `trafilatura`, the crude HTML stripper produces <200 chars for most pages. **Fix:** use direct publisher RSS feeds that include full article text, so the crude extractor has enough content to work with.

### 3. Long run time
Stage 1 makes ~50-80 HTTP requests to ground 5 articles. Direct feeds are faster than Google News (which requires URL resolution + redirect follow for every item).

### 4. Model / provider override
The script defaults to `deepseek-v4-flash-0731` via `litellm`, but `run.sh` passes
both explicitly anyway. To override for a manual run:
```bash
python3 wire_articles.py --max 5 --model <model> --provider <provider>
```
