---
name: orchestrator-v2
description: "Lux in Tenebris V2 production pipeline. Bash orchestrator with fire-and-forget cron, 8 atomic scouts + 1 Python/LLM hybrid, dual-model editor, image-gen, render, podcast pill, wire articles, version badge, deploy to GitHub Pages."
---

# Orchestrator V2 — Production Pipeline

## Purpose
Daily AI news production: 9 scouts → dual-model editor (DS + K3) → image generation → HTML render → version badge → podcast pill → wire articles → deploy to GitHub Pages.

## Architecture — Dual-Model Pipeline

**Core principle:** Cron is a scheduler, not a state manager. Scouts run once; editor, render, wire articles, and badge injection run per-model for each edition.

Since 2026-07-17, the pipeline produces **two editions** per run: DeepSeek (default, `index.html`) and Kimi K3 / The Lens (`k3/index.html`).

```
Cron (08:00, no_agent=true, fire-and-forget)
  ↓
cron_wrapper.sh (nohup bash run_v2.sh &)
  ↓
run_v2.sh (bash orchestrator)
  ↓
Phase 1-5: 9 scouts (once, parallel within phases)
  ↓
── DUAL MODEL BRANCH ──
  │
  ├─ Editor DS (editor-v2, deepseek)  → edition.json
  ├─ Editor K3 (editor-v2-k3, kimi-k3) → edition_k3.json
  │
  ├─ Image-gen (once, shared)
  ├─ Render DS  → index.html
  ├─ Render K3  → k3/index.html
  ├─ Badge DS   → badge inactive (amber)
  ├─ Badge K3   → badge active (ember) + paths fixed to ../
  ├─ Layout K3  → transform_layout_k3.py (White Edition)
  ├─ Wire DS    → scout_wire_ds.json (deepseek)
  └─ Wire K3    → scout_wire_k3.json (kimi-k3)
  ↓
Podcast Pill (shared, injected into both)
  ↓
Git sync → Archive → Copy → git add → commit → push
```

## Key Scripts (post-render transforms)

### inject_version_badge.py
- `python3 inject_version_badge.py <input.html> <mode> --output <output.html>`
- Modes: `ds` (links to `k3/`), `k3` (links to `../`, also rewrites paths to `../`)
- Injects inline CSS before `</head>`, badge HTML between dateline `</div>` and devocracy-credit
- Colors: DS = `var(--lux)` amber, K3 = `var(--ember)` hot orange. On K3 White Edition, badges become black `#1a1a1a`.
- **CRITICAL:** Run ONCE per file. Re-running duplicates the badge.

### transform_layout_k3.py
- `python3 transform_layout_k3.py <input.html> --output <output.html>`
- Transforms K3 edition into "White Edition" layout: white/cream bg, black text, Lux dark header
- Uses **nuclear CSS approach**: `h1, h2, h3, h4, h5, p, a, span, div, article, section { color: #000 !important; }` to override ALL Lux CSS text colors
- CSS ordering in the injected style block is CRITICAL: general `a, a:link` rule BEFORE header/badge exceptions, hover rules AFTER nuclear rule
- Wire news container excluded from white bg via `[class*="wire"] { background-color: var(--ink) !important; }`

### wire_articles.py
- `--model`, `--provider` args for per-edition model selection
- Each edition gets its own wire articles written by its respective model
- **CRITICAL:** `build_prompt` uses `os.environ.get('WIRE_MODEL', MODEL)`. If `MODEL` global is overridden via `--model`, the prompt's `model_name` follows correctly. Was `deepseek/deepseek-v4-flash` hardcoded (fix applied 2026-07-17).

### fetch_trending.py
- `python3 fetch_trending.py [--output-json PATH]`
- Fetches GitHub Trending (15 repos) and HuggingFace Trending (10 models) via **curl** (bypasses Firecrawl/Tavily)
- Used as auto-fallback when the opensource scout fails (web_extract connection errors)
- Outputs JSON matching the scout-v2-opensource `trending` contract
- **Location:** `~/.hermes/profiles/luke/scripts/v2/fetch_trending.py`

### fix_archive_issue_numbers.py
- `python3 fix_archive_issue_numbers.py`
- Fixes incorrect issue numbers in archived HTML files and regenerates the archive listing
- Also sets `.issue` to the correct value for the next pipeline run
- **Location:** `~/.hermes/profiles/luke/scripts/v2/fix_archive_issue_numbers.py`

## Per-model components

| Component | DeepSeek | Kimi K3 |
|-----------|----------|---------|
| Editor skill | `editor-v2` | `editor-v2-k3` |
| Model | `deepseek-v4-flash` | `kimi-k3` |
| Edition file | `edition.json` | `edition_k3.json` |
| Output path | `index.html` | `k3/index.html` |
| Badge mode | `ds` (amber, inactive, links to k3/) | `k3` (active, paths fixed to ../) |
| Layout | Lux dark (unchanged) | White Edition (transform_layout_k3.py) |
| Wire articles | `scout_wire_ds.json` | `scout_wire_k3.json` |
| Wire model | default (deepseek-v4-flash) | `--model kimi-k3 --provider localAIServer` |

## editor-v2-k3 sections (different from standard editor-v2)
- Deep Dives (research + long-form, 3-5 items)
- Open Pulse (opensource + tools, 3-5 items)
- The Edge (hardware + funding, 3-5 items)
- YouTube Signals (video, 2-3 items, show if ≥2)
- Italia Front (Italian AI, 2-3 items, show if ≥2)
- Quick hits: 5-7 with brief context (2-5 words)
- Trending: SKIP (null) — shown in DeepSeek edition only

## 🔴 FIRECRAWL FALLBACK — when web_search/web_extract fail

### Root cause
`web_search` uses `search_backend: ddgs` (DuckDuckGo, free).  
`web_extract` uses `extract_backend: firecrawl` (paid API with credit limits).

When Firecrawl credits are exhausted, `web_extract` returns `"Payment Required"`.  
In some sessions DuckDuckGo may also be rate-limited, causing `web_search` to cascade to Firecrawl and fail too.

### Solution — curl-based fallback
Each scout skill now includes a **🔴 FIRECRAWL FALLBACK** section with `terminal` + `curl` commands that bypass Firecrawl entirely.

Key free API fallbacks used across scouts:
- **TechCrunch**: WordPress JSON API (`wp-json/wp/v2/posts`)
- **HuggingFace Papers**: direct HTML scraping via `curl`
- **arXiv**: `export.arxiv.org/api/query` (free XML API)
- **Hacker News**: `hn.algolia.com/api/v1` (free JSON API)
- **Product Hunt**: HTML regex parsing from Next.js props
- **DuckDuckGo / Bing**: direct HTML search via `curl`
- **Generic page fetch**: `curl` + regex title/body extraction

### When to use
If a scout returns `[]` and the pipeline log shows Firecrawl/credit errors, the scout agent will automatically attempt the curl fallbacks described in its skill before emitting `[]`.

## Pitfalls

1. **Badge injector duplicates** — Do NOT run `inject_version_badge.py` twice on the same file. Re-render with `render.py` first, then inject ONCE.

2. **K3 White Edition CSS ordering** — CSS rule order in `transform_layout_k3.py` is critical. Correct sequence:
   1. Backgrounds (html/body/container white)
   2. Wire dark override (early to win against white bg)
   3. General `a, a:link { color: #000 !important; }` (all links black)
   4. Header exceptions (ears, devocracy) — override general rule
   5. Nuclear text color: `h1, h2, h3, h4, h5, p, a, span, div, article, section { color: #000 !important; }`
   6. Hover rules: `a:hover { color: #f0a23c !important; }` — must be AFTER nuclear rule
   7. Badge rules — override general/hover with own colors

3. **Wire articles model_name** — `build_prompt()` in `wire_articles.py` uses `os.environ.get('WIRE_MODEL', MODEL)`. With `--model kimi-k3`, the `MODEL` global is updated but `model_name` used a hardcoded fallback (`deepseek/deepseek-v4-flash`). Fixed 2026-07-17: changed to `os.environ.get('WIRE_MODEL', MODEL)`.

4. **K3 subdir paths** — `href="style.css"` → `../style.css`. Also fonts, images, podcasts. The badge injection in `k3` mode does this automatically.

5. **Image path copy** — Images from DS edition are copied to K3 via Python (step 6b). Matches by section title. If section names differ (e.g. "Research & Papers" vs "Deep Dives"), images are NOT copied (logged but non-blocking).

6. **Dual wire articles** — DS wire uses deepseek, K3 wire uses kimi-k3. Separate files: `scout_wire_ds.json` and `scout_wire_k3.json`. Each injected into its respective edition. Report shows both counts.

7. **Badge position** — Must sit BETWEEN the dateline closing `</div>` and the devocracy-credit. Regex: `(</div>)(\s*\n\s*<div class="devocracy-credit")` → `\1\n` + badge + `\2`. Do NOT use the regex that matches the entire `</div>...<div class="devocracy-credit"` as one group — the badge ends up inside the dateline div.

8. **Issue number stuck at previous value** — The `.issue` read/increment MUST happen AFTER `git reset --hard origin/main` (step 9). If it runs before, the git reset reverts `$DEPLOY_DIR/.issue` to the committed value. Fixed 2026-07-24: write to `$DEPLOY_DIR/.issue` moved to after the reset.

9. **Trending fallback (fetch_trending.py)** — The opensource scout uses `web_extract` (Firecrawl) which can fail with `Connection error`. The pipeline auto-fallback calls `fetch_trending.py` via curl when trending data is missing (<3 items). To manually re-run: `python3 ~/.hermes/profiles/luke/scripts/v2/fetch_trending.py --output-json /tmp/v2/scouts/scout_opensource.json`