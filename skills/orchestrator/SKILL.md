---
name: orchestrator
description: "Local AI News production pipeline. Bash orchestrator with fire-and-forget cron, 6 LLM scouts run sequentially, editor, render, wire articles, deploy to GitHub Pages."
---

# Orchestrator — Production Pipeline

## Purpose
Daily local-AI news production: 10 scouts → editor → HTML render → wire articles → deploy to GitHub Pages.

## Architecture

**Core principle:** Cron is a scheduler, not a state manager. Every step is
isolated and stateless, communicating only through JSON files in `/tmp/lain/`.

```
Cron (06:30, no_agent=true, fire-and-forget)
  ↓
cron_wrapper.sh (nohup bash run.sh &)
  ↓
run.sh (bash orchestrator)
  ↓
Sync deploy dir → resolve issue # → archive predecessor edition
  ↓
10 scouts, ONE AT A TIME (see "Why sequential" below)
  ↓
Editor (qwen-nvidia via spark) → edition.json
  ↓
Render → index.html → wire articles → ticker injection → making-of
  ↓
Copy → headlines history → git add → commit → push
```

## Why sequential scouts

A scout is not one request — it's a whole multi-turn agent session (searches,
tool calls, reasoning). The backend is the DGX Spark's LiteLLM proxy, a single
box. Concurrent sessions saturate it and every one crawls (proven upstream:
0 scouts completed across 3 days of 3-up parallel runs). Serialising trades
wall clock (free — fire-and-forget morning cron) for actually finishing.

**Do not re-parallelise** without first confirming the backend can take
concurrent agent sessions.

## Timeouts

Every LLM call is wrapped in `timeout`. Nothing may hang forever.

| Budget | Value | Applies to |
|--------|-------|------------|
| `TIMEOUT_SECS` | 20 min | each scout |
| `EDITOR_TIMEOUT_SECS` | 40 min | editor — its own, larger budget |
| `MASTER_TIMEOUT` | 3h | whole pipeline |

The editor is the only FATAL step and does the most work in one call, so it
gets 40 min (upstream it was killed by a shared 20-min ceiling once and took
the whole run down with it).

**Per-step logs are appended, never truncated** (`>>` + a `▶` banner per
attempt). A manual re-run must never overwrite the log of the automated
attempt that just failed.

`MASTER_TIMEOUT` must cover the **sum** of sequential scouts, not the max.

## Provider pinning

Every step passes `--provider "$PIPELINE_PROVIDER"` (= `spark`) explicitly.
The Hermes profile default is deliberately not used. See the warning block
at the top of `run.sh` before changing anything here — upstream, an
interactive session once silently swapped every provider flag to a paid
backend and a full edition was produced on it before anyone noticed.

### wire_articles.py
- `--model`, `--provider` args passed explicitly by run.sh so
  `$PIPELINE_PROVIDER` stays the single place the backend is decided.

### fetch_trending.py
- `python3 fetch_trending.py [--output-json PATH]`
- Fetches GitHub Trending + HuggingFace Trending via curl
- Used as auto-fallback when the opensource scout fails to produce trending data
- Outputs JSON matching the scout-opensource `trending` contract

### fetch_free_models.py
- `python3 fetch_free_models.py [--output-json PATH]`
- Fetches currently-free models from OpenRouter + OpenCode Zen via curl (no LLM)
- Runs as step 3b, non-fatal; writes `free_models.json`
- Outputs JSON matching the editor's `free_models` pass-through contract (see `editor` skill step 3b)

## Reference docs

For deep dives on a specific subsystem, load the matching reference under
`skills/orchestrator/references/`:

| When you need | Read |
|---|---|
| How archives + issue numbers work, or why a listing is stale | `archive-system.md` |
| Which model/provider each step uses, and how to change one | `model-configuration.md` |
| How RSS wire articles + the ticker are built | `wire-articles-scout.md` |
| How to batch-check links after a deploy | `link-validation.md` |

## The scouts

| # | name | beat |
|---|------|------|
| 1 | research | arXiv/HF papers with local relevance (quant, distill, efficiency) |
| 2 | official | labs that ship open-weight models |
| 3 | opensource | new open-weight releases + GitHub/HF trending (AI-filtered) |
| 4 | tools | runtimes & tooling (Ollama, llama.cpp, UIs, MCP) |
| 5 | hardware | consumer GPUs, NPUs, edge devices, VRAM |
| 6 | selfhost | self-hosted stack (Open WebUI, n8n, Home Assistant, r/LocalLLaMA) |

## Issue numbering & archiving

Resolved in step 1b, against a deploy dir that was just `git reset --hard`
to `origin/main` — the last truly published state. Issue number and date are
read from the live `index.html`'s own masthead, never from `.issue` (a
crashed run can leave that stale). Same date as today → same-day re-run,
reuse the number. Different date → increment, and archive the predecessor
BEFORE this run's files overwrite it.
