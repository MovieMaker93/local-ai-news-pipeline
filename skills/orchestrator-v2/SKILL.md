---
name: orchestrator-v2
description: "Lux in Tenebris V2 production pipeline. Bash orchestrator with fire-and-forget cron, 8 atomic scouts + 1 Python/LLM hybrid run sequentially, editor, image-gen, render, podcast pill, wire articles, deploy to GitHub Pages."
---

# Orchestrator V2 — Production Pipeline

## Purpose
Daily AI news production: 9 scouts → editor → image generation → HTML render → podcast pill → wire articles → deploy to GitHub Pages.

## Architecture

**Core principle:** Cron is a scheduler, not a state manager. Every step is
isolated and stateless, communicating only through JSON files in `/tmp/v2/`.

```
Cron (06:30, no_agent=true, fire-and-forget)
  ↓
cron_wrapper.sh (nohup bash run_v2.sh &)
  ↓
run_v2.sh (bash orchestrator)
  ↓
Sync deploy dir → resolve issue # → archive predecessor edition
  ↓
9 scouts, ONE AT A TIME (see "Why sequential" below)
  ↓
Editor (editor-v2, deepseek-v4-flash) → edition.json
  ↓
Image-gen → Render → index.html
  ↓
Podcast Pill → Wire articles → ticker injection
  ↓
Copy → headlines history → git add → commit → push
```

## Why sequential scouts (changed 2026-07-28)

Scouts used to run 3-up in parallel phases. That works against a distributed
API but not against `localAIServer`, which is a **single self-hosted box**. A scout is
not one request — it's a whole multi-turn agent session (searches, tool calls,
reasoning). Three concurrent sessions saturate the machine and all three crawl.

Evidence (logs, 2026-07-26/27/28): every 3-up phase ran exactly to the
per-scout ceiling and got killed — **0 scouts completed** across those runs.
The same scouts against a distributed provider finished a whole phase in
4.7-6.7 min. Serialising trades wall clock (free here — it's a fire-and-forget
06:30 cron) for actually finishing.

**Do not re-parallelise** without first confirming the inference backend can
take concurrent agent sessions.

## Timeouts

Every LLM call is wrapped in `timeout`. Nothing may hang forever — five calls
used to have no timeout at all (italia scout, editor, image-gen, podcast), and
they produced 40-minute stalls in the logs.

| Budget | Value | Applies to |
|--------|-------|------------|
| `TIMEOUT_SECS` | 20 min | each scout |
| `STEP_TIMEOUT_SECS` | 20 min | editor, italia scout |
| `MEDIA_TIMEOUT_SECS` | 15 min | image gen, podcast (xAI-bound) |
| `MASTER_TIMEOUT` | 4h | whole pipeline |

`MASTER_TIMEOUT` must cover the **sum** of sequential scouts, not the max. It
was 90 min while scouts ran in parallel; that is far too tight now.

## Provider pinning

Every step passes `--provider "$PIPELINE_PROVIDER"` (= `localAIServer`) explicitly.
The Hermes profile default is deliberately not used — the user chats on
openrouter, but the pipeline must stay on their friend's server. See the
comment block at the top of `run_v2.sh` before changing anything here.

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

## Edition components

Single edition. The K3 "The Lens" second edition was **fully removed on
2026-07-28** — it had been render-disabled since 07-25 while its editor and
wire steps still ran daily, burning LLM calls on output nothing consumed.
`editor-v2-k3`, `transform_layout_k3.py` and `inject_version_badge.py` are
deleted; there is no second version, so no version selector either.

| Component | Value |
|-----------|-------|
| Editor skill | `editor-v2` |
| Model | `deepseek-v4-flash` (provider `localAIServer`) |
| Edition file | `edition.json` |
| Output path | `index.html` |
| Wire articles | `scout_wire.json` |

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

1. **Do not re-parallelise the scouts** — see "Why sequential scouts" above.
   Running them 3-up against `localAIServer` produced 0 completed scouts across three
   consecutive days.

2. **Do not swap the provider** — every step must stay on `localAIServer` via
   `$PIPELINE_PROVIDER`. An interactive session silently rewrote all of them
   to `openrouter` on 2026-07-28 while doing an unrelated timeout change.

3. **Wire articles model_name** — `build_prompt()` in `wire_articles.py` uses
   `os.environ.get('WIRE_MODEL', MODEL)` so the attribution line follows
   `--model` instead of a hardcoded value. Fixed 2026-07-17.

4. **Issue number and archiving happen in step 1b**, before the scouts, against
   a freshly `git reset --hard` deploy dir. The issue number is read from the
   **live index.html masthead**, not `.issue` (a crashed run can leave that
   stale/unpushed — it silently burned issue #31 on 2026-07-27). Same date as
   today ⇒ same-day re-run ⇒ reuse the number. Different date ⇒ increment and
   archive the predecessor *before* this run overwrites it.

5. **Trending fallback (fetch_trending.py)** — The opensource scout uses `web_extract` (Firecrawl) which can fail with `Connection error`. The pipeline auto-fallback calls `fetch_trending.py` via curl when trending data is missing (<3 items). To manually re-run: `python3 ~/.hermes/profiles/luke/scripts/v2/fetch_trending.py --output-json /tmp/v2/scouts/scout_opensource.json`