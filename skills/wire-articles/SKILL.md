---
name: wire-articles
description: "V2 wire-articles scout. Fetches RSS, picks 5 random AI news, calls LLM to write original grounded articles, saves JSON to /tmp/v2/scouts/scout_wire.json."
---

# Wire Articles V2 — RSS → AI Writing Scout

## When to use
Called by orchestrator as step 8, after all 9 scouts and the editor have run.
Deterministic RSS retrieval + LLM article writing. The output feeds the
scrolling news ticker on the front page — it is **not** part of `edition.json`.

## Files to write
- `/tmp/v2/scouts/scout_wire.json` — JSON array of wire articles

## Workflow

1. Run the deterministic retrieval script:
```bash
python3 ~/.hermes/profiles/luke/scripts/v2/wire_articles.py --max 5 \
  --out /tmp/v2/scouts/scout_wire.json \
  --model deepseek-v4-flash --provider localAIServer
```
⚠️ The provider is **`localAIServer`**, never `openrouter`. `run_v2.sh` passes it
explicitly (as `$PIPELINE_PROVIDER`) rather than relying on the script's own
defaults, so the backend is chosen in exactly one place.

2. Validate output:
```bash
python3 -c "import json; d=json.load(open('/tmp/v2/scouts/scout_wire.json')); print(f'{len(d)} wire articles')"
```

3. If empty → write `[]` and proceed. The run_v2.sh guards with `WIRE_COUNT -gt 0`.

## Wire Articles JSON Shape

```json
[
  {
    "headline": "OpenAI Unveils o5...",
    "body": "Full article text...\n\n*Editorial note*\n*— Written by AI (deepseek/deepseek-v4-flash)*",
    "source": "The Verge",
    "source_url": "https://...",
    "original_title": "Original RSS headline",
    "published": "Mon, 30 Jun 2025 14:00:00 GMT",
    "generated_at": "2025-06-30T14:30:00+00:00"
  }
]
```

## Ticker injection (post-render)

After render.py produces index.html, run:
```bash
python3 ~/.hermes/profiles/luke/scripts/v2/inject_wire_ticker.py \
  /tmp/v2/output/index.html \
  /tmp/v2/scouts/scout_wire.json \
  --output /tmp/v2/output/index.html
```

This injects the scrolling banner between masthead and lead story — no other changes.

## All content MUST be in English.

## Pitfalls

### 1. Google News RSS resolution is fragile
If Google changes its URL token format, `resolve_url()` in `wire_articles.py` may fail. The script falls back to HTTP redirect but many CDNs block headless requests. **Fix:** add direct publisher RSS feeds (TechCrunch, Ars Technica, Wired, The Verge) to the `FEEDS` array instead of Google News.

### 2. No trafilatura available (PEP 668)
The system is PEP 668-locked: `pip install`, `uv pip install --system`, and `python3 -m venv` all fail. Without `trafilatura`, the crude HTML stripper produces <200 chars for most pages. **Fix:** use direct publisher RSS feeds that include full article text, so the crude extractor has enough content to work with.

### 3. Long run time
Stage 1 makes ~50-80 HTTP requests to ground 5 articles. Direct feeds are faster than Google News (which requires URL resolution + redirect follow for every item).

### 4. Model / provider override
The script defaults to `deepseek-v4-flash` via `localAIServer`, but `run_v2.sh` passes
both explicitly anyway. To override for a manual run:
```bash
python3 wire_articles.py --max 5 --model <model> --provider <provider>
```
`WIRE_MODEL` env var only changes the attribution line in the article footer,
not the model actually called — see pitfall 8.

### 5. hermes chat -q stdout pollution
`call_hermes()` uses `subprocess.run(capture_output=True)` but `hermes chat -q` writes warnings to stdout (e.g. `Warning: Unknown toolsets: messaging`). These get mixed into the LLM output. **Fix:** filter lines starting with `Warning:` in `call_hermes()`. Extend the filter if new warning prefixes appear.

### 6. False positives from broad AI keyword filter
Publisher feeds contain non-AI articles that mention "AI" incidentally ("AI-powered vacuum cleaner promo codes"). **Fix:** add terms to the `DENY` array. Known offenders: "promo code", "discount", "cat litter", "tender offer" (when the article is about employee equity, not AI). Review output after each run.

### 7. Prompt output format must match JS expectations
The injector's JS (`inject_wire_ticker.py` / `build_js()`) searches for `*— Written by AI (` (em dash U+2014) to split body from AI signature. The `wire_articles.py` prompt in `build_prompt()` MUST produce this exact format:
```
*Editorial note in italics*
*— Written by AI (deepseek-v4-flash)*
```

If the prompt format changes (e.g. different dash character, different spacing, extra text), the JS silently fails to split and renders the entire body as plain text with no AI signature block. See `references/injection-pattern.md` for the injection architecture.

### 8. JS: avoid `replace(/regex/g)` — use `split().join()` instead
To avoid Python-JS escape fighting inside f-strings, replace:
```javascript
// AVOID: regex backslash hell in Python f-strings
body.replace(/\n/g, '<br>')

// PREFER: no escape issues
body.split('\\n').join('<br>')
```

### 9. Ticker injection via post-processing (safer than modifying render.py)
The injector (`inject_wire_ticker.py`) adds the ticker AFTER `render.py` finishes. It NEVER modifies `render.py`. Injection targets:

| Element | Injection point | Regex |
|---------|---------------|-------|
| CSS | Before `</head>` | `re.sub(r'</head>', '<style>CSS</style></head>', ...)` |
| Ticker HTML | After `</header>` | `re.sub(r'</header>', '</header>TICKER', ...)` |
| Modal HTML | Before `</body>` | `re.sub(r'</body>', 'MODAL</body>', ...)` |
| JS | Before `</body>` | `re.sub(r'</body>', 'JS</body>', ...)` |

Production Lux uses `<link rel="stylesheet" href="style.css">` (external), so CSS injection targets `</head>`, not `</style>`.

**data-b newline escaping:** Article body text has `\n`. HTML attributes break on real newlines. Fix:
```python
# Python: escape newlines for HTML attribute
bd = html.escape(body).replace('\n', '\\n')
```
```javascript
// JS: restore line breaks
el.getAttribute('data-b').split('\\n').join('<br>')
```

### 10. CSS variable names must match production EXACTLY
The injector's CSS MUST use the EXACT variable names from `style.css`. Using shortened aliases causes the ticker to render as an unstyled list.

**Correct:** `var(--rule)`, `var(--serif)`, `var(--sans)`, `var(--muted)`, `var(--type-dim)`, `var(--lux-soft)`, `var(--ink)`, `var(--type)`, `var(--rule-strong)`, `var(--ember)`

**Wrong (short aliases):** `--ru`, `--se`, `--sa`, `--mu`, `--td`, `--ls`, `--rs`

### 11. Template nameplate must stay in sync — and edit the RIGHT template
The nameplate must be `LVX IN <span class="lux">TENEBRIS</span>` (all caps,
Latin). Same for the `<title>` tag. Editing the deployed `index.html` by hand
gets overwritten on the next run — fix the **template**, then re-render.

⚠️ **The live template is `~/lux-in-tenebris-pipeline/template/newspaper.html`**
(that's what `$TEMPLATE_DIR` in `run_v2.sh` points at, and what `render.py`
loads). An old v1 copy still exists at
`~/.hermes/profiles/luke/skills/ai-news-24h/templates/newspaper.html` — it is
**not read by anything** and has already diverged from the real one. Editing it
does nothing. This doc used to point at that stale copy.

### 12. Deploy dir may have stale index.html
`~/ai-news-deploy/index.html` on disk may differ from `git HEAD` (uncommitted overwrites). Verify with `git show HEAD:index.html` before injecting, or checkout the committed version first.