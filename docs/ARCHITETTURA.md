# Architecture — Local AI News Pipeline

## Overview

Daily pipeline that produces a local-AI newspaper in dark broadsheet style.
Cron → wrapper → bash orchestrator → 10 scouts + wire → editor → HTML render → deploy.

Every step is either an **LLM agent** (a `SKILL.md`, invoked as `hermes chat
-s <skill>`, used wherever the task needs judgment) or **plain code**
(Python/bash, used wherever the task is mechanical and must not depend on a
model's mood that day). Steps never call each other directly — they only
read/write JSON or HTML files under `/tmp/lain/`, which is what makes each one
independently retriable and lets a failure in one stay contained to that
stage.

## Flow Diagram

```
Hermes cron (06:30, no_agent=true, fire-and-forget)
  │
  ▼
cron_wrapper.sh (nohup → run.sh &, backgrounds it — cron has a 3-min
  │              hard timeout, the pipeline itself runs ~1.5-2.5h)
  ▼
run.sh
  │
  ├─ Step 0:  Cleanup /tmp/lain/
  ├─ Step 1:  Metadata (date window)
  ├─ Step 1b: Sync deploy dir to origin (git reset --hard) — resolve issue #
  │            from the LIVE index.html's own masthead (not the .issue file,
  │            which a crashed run can leave stale/unpushed). Same date as
  │            today → reuse that issue number (same-day re-run). Different
  │            date → increment, and archive that predecessor edition NOW,
  │            before this run's files overwrite it.
  │
  ├─ Step 2:  Scouts — ONE AT A TIME, all LLM agents, 20 min ceiling each
  │   ├─ research → official → opensource
  │   │     (+ fetch_trending.py curl fallback if trending < 3 items)
  │   ├─ tools
  │   ├─ hardware
  │   ├─ selfhost
  │   ├─ x (x_search, falls back to DuckDuckGo/Bing if no creds)
  │   ├─ funding
  │   ├─ youtube (youtube_scout.py Python fetch → LLM extraction)
  │   └─ italia
  │
  ├─ Step 3:  Validate 10 scout JSON files (missing/invalid → empty [])
  ├─ Step 3b: Free models (OpenRouter + OpenCode Zen) [non-fatal] — pure code, writes free_models.json
  ├─ Step 4:  Editor → edition.json                    — LLM agent, the only FATAL step
  ├─ Step 5:  Render → index.html                      — pure code
  ├─ Step 6:  Wire articles (RSS → LLM)  [non-fatal]   — code + 1 LLM call/article
  ├─ Step 6b: Inject wire ticker         [non-fatal]   — pure code
  ├─ Step 6c: Making-of page             [non-fatal]   — pure code, read-only on pipeline state
  └─ Step 7-9: Deploy (copy files, headlines history, git commit + push)
```

Archiving happens in step 1b, **before** today's overwrite, not after — an
edition is archived at the latest by the following day's run, even if that
edition's own run never reached its deploy step.

## Agents & Responsibilities

"Agent" = an LLM call via a `SKILL.md` (judgment: what matters, how to phrase
it). "Code" = plain Python/bash, deterministic, no model in the loop. Every
model/provider below is read directly out of `run.sh` — none of these steps
fall back to the Hermes profile default; every invocation passes its model
explicitly.

| Step | Kind | Model / Provider | Toolset | Reads | Writes |
|------|------|-------------------|---------|-------|--------|
| scout-research | agent | flash / spark | web, file, terminal | — | `scout_research.json` |
| scout-official | agent | flash / spark | web, file, terminal | `skills/_shared/sources.md` | `scout_official.json` |
| scout-opensource | agent | flash / spark | web, file, terminal | — | `scout_opensource.json` (editorial + trending) |
| `fetch_trending.py` | code | — | curl | — | merged into `scout_opensource.json` if trending < 3 |
| `fetch_free_models.py` | code | — | curl | OpenRouter + OpenCode Zen catalogs | `free_models.json` (step 3b) |
| scout-tools | agent | flash / spark | web, file, terminal | — | `scout_tools.json` |
| scout-hardware | agent | flash / spark | web, file, terminal | — | `scout_hardware.json` |
| scout-selfhost | agent | flash / spark | web, file, terminal | — | `scout_selfhost.json` |
| scout-x | agent | flash / spark | x_search, file, terminal | — | `scout_x.json` (falls back to DuckDuckGo/Bing if no X creds) |
| scout-funding | agent | flash / spark | web, file, terminal | — | `scout_funding.json` |
| scout-youtube | agent | flash / spark | file | `scout_youtube_raw.json` (from `youtube_scout.py` fetch) | `scout_youtube.json` |
| scout-italia | agent | flash / spark | web, file, terminal | `skills/_shared/sources.md` (Italia feeds) | `scout_italia.json` |
| `youtube_scout.py` | code | — | yt-dlp + YouTube RSS | `skills/_shared/sources.md` (channels) | `scout_youtube_raw.json` |
| image-gen (step 4b) | agent | flash / spark | file, image_gen, terminal | `edition.json` | `images/*.jpg` + updates `edition.json` — **non-fatal, skips on provider limit** |
| editor | agent | flash / spark | file | all `scout_*.json` + `headlines_history.json` + `free_models.json` | `edition.json` — **the only FATAL step** |
| `render.py` | code | — | — | `edition.json` + `template/` | `index.html` |
| `wire_articles.py` | code + 1 agent call/article | flash / spark | curl (RSS from `sources.md`) + hermes chat subprocess | RSS feeds | `scout_wire.json` |
| `inject_wire_ticker.py` | code | — | — | `index.html`, `scout_wire.json` | `index.html` (ticker injected) |
| `make_making_of.py` | code, read-only | — | — | scout JSON, run log, log mtimes, `edition.json` | `making-of.html` |
| `archive_issue.py` | code | — | — | `deploy/index.html` + assets it references | `archive/YYYY-MM-DD/` snapshot |
| `update_headlines_history.py` | code | — | — | `edition.json` | `headlines_history.json` |

## Scout Concurrency — why sequential

A scout is not a single API request — it's a full multi-turn agent session
(web searches, tool calls, reasoning, retries). The backend is one
self-hosted box. Concurrent agent sessions saturate it and every one of them
crawls. Upstream evidence (Lux in Tenebris, 2026-07-26/27/28): every 3-up
parallel phase ran to exactly the per-scout timeout ceiling and got killed —
0 scouts completed across those days; the same scouts against a distributed
backend finished in under 7 minutes. Serialising costs wall clock and buys
completion, and wall clock is free on a fire-and-forget morning cron.

**Before re-parallelising**, confirm the inference backend can actually take
concurrent agent sessions.

## Timeouts

Every LLM call is wrapped in `timeout`.

| Budget | Value | Covers |
|--------|-------|--------|
| `TIMEOUT_SECS` | 20 min | each scout |
| `EDITOR_TIMEOUT_SECS` | 40 min | editor (own budget) |
| `MASTER_TIMEOUT` | 3h | the whole pipeline |

The editor is the only **FATAL** step: no `edition.json` means no newspaper at
all, and it does the most work of any single call (10 scout files, cross-day
dedup against `headlines_history.json`), so it gets double budget. Re-measure
after a week of runs and tune.

## Provider Pinning

Every LLM step passes `--provider "$PIPELINE_PROVIDER"` (= `spark`)
explicitly. The Hermes profile default is deliberately unused. Pinned in one
variable with a warning block above it — see run.sh for the upstream incident
that motivates it.

## Critical Paths

| Path | Description |
|------|-------------|
| `~/local-ai-news-pipeline/` | Source repo (pipeline code, skills, templates) |
| `~/.hermes/profiles/paper/scripts/v2/` | Symlink → pipeline scripts |
| `~/.hermes/profiles/paper/skills/lain/` | Symlink → pipeline skills |
| `/tmp/lain/` | Working directory (scout JSON, output) |
| `~/local-ai-news-deploy/` | Deploy repo (published output) |

## Non-Fatal Steps

Steps marked `[non-fatal]` use `|| echo "..."` / `|| true` — failure doesn't
block the pipeline; the day's edition still deploys without that piece.

## Cross-Day Dedup

The editor reads `headlines_history.json` (stored in the deploy repo) to avoid
titles already published on previous days.

## Cron

- **Pipeline job:** 06:30 daily, `no_agent=true`, fire-and-forget
- A watchdog job (verify deploy succeeded ~3h later) is recommended but not included

## Symlink Architecture

The repo is the single source of truth. Hermes accesses pipeline code through
symlinks:

```bash
~/.hermes/profiles/paper/scripts/v2        →  ~/local-ai-news-pipeline/scripts
~/.hermes/profiles/paper/skills/lain       →  ~/local-ai-news-pipeline/skills
```

Changes pushed to the repo are immediately visible to the Hermes agent and
the cron pipeline on the next run.
