# Architecture — Lux in Tenebris V2 Pipeline

## Overview

Daily pipeline that produces an AI newspaper in dark broadsheet style.
Cron → wrapper → bash orchestrator → 9 scouts + wire → dual-model editor (DS + K3)
→ image generation → HTML render → podcast → deploy.

## Flow Diagram

```
Cron (06:30, no_agent=true, fire-and-forget)
  │
  ▼
cron_wrapper.sh (nohup → run_v2.sh &)
  │
  ▼
run_v2.sh
  │
  ├─ Step 0:  Cleanup /tmp/v2/
  ├─ Step 1:  Metadata (date window, issue #)
  │
  ├─ Step 2:  Scouts (5 phases, parallel within each)
  │   ├─ Phase 1: X, Research, Official        (3 in parallel)
  │   ├─ Phase 2: OpenSource, Tools, Funding    (3 in parallel)
  │   ├─ Phase 3: Hardware                      (1)
  │   ├─ Phase 4: YouTube (Python fetch + LLM scout)  (1 hybrid)
  │   └─ Phase 5: Italia AI Spotlight           (1)
  │
  ├─ Step 3:  Validate 9 scout JSON files
  ├─ Step 4:  Editor (DS) → edition.json
  ├─ Step 4b: Editor (K3) → edition_k3.json
  ├─ Step 5:  Image gen (Grok Imagine)          [non-fatal]
  ├─ Step 6:  Render DS → index.html
  ├─ Step 6b-c: Copy images to K3 + render K3
  ├─ Step 6d-e: Inject version badges + transform K3 layout
  ├─ Step 7:  Podcast Pill (Castor/Luna)        [non-fatal]
  ├─ Step 8:  Wire Articles + ticker injection  [non-fatal]
  └─ Step 9-11: Deploy
      ├─ git fetch + reset --hard
      ├─ archive_issue.py (save previous edition)
      ├─ Copy new files to deploy dir
      ├─ git add → commit → push
      └─ Final report
```

## Critical Paths

| Path | Description |
|------|-------------|
| `~/lux-in-tenebris-pipeline/` | Source repo (pipeline code, skills, templates) |
| `~/.hermes/profiles/luke/scripts/v2/` | Symlink → pipeline scripts |
| `~/.hermes/profiles/luke/skills/ai-news-v2/` | Symlink → pipeline skills |
| `/tmp/v2/` | Working directory (scout JSON, images, output) |
| `~/ai-news-deploy/` | Deploy repo (published output) |

## Models

| Step | Model | Provider |
|------|-------|----------|
| Scouts (X, research, official, opensource, tools, funding, hardware) | profile default | profile default |
| Scout YouTube | deepseek/deepseek-v4-flash | openrouter |
| Editor (DS) | deepseek-v4-flash | localAIServer (LiteLLM private server) |
| Editor (K3) | kimi-k3 | localAIServer (LiteLLM private server) |
| Image gen (orchestrator) | profile default | profile default |
| Image gen (generation) | grok-imagine-image | xAI (Grok) |
| Wire articles | deepseek-v4-flash | localAIServer |
| Podcast pill | profile default | profile default |

## Non-Fatal Steps

Steps marked `[non-fatal]` use `|| echo "..."` — failure doesn't block the pipeline.

## Cross-Day Dedup

The editor reads `headlines_history.json` (stored in the deploy repo) to avoid
titles already published on previous days.

## Cron

- **Pipeline job:** `29fa53d809c4` — 06:30 daily, no_agent=true, fire-and-forget
- **Watchdog:** `369c43cef23d` — 07:45 daily, verifies deploy succeeded

## Symlink Architecture

The repo is the single source of truth. Hermes accesses pipeline code through symlinks:

```bash
~/.hermes/profiles/luke/scripts/v2        →  ~/lux-in-tenebris-pipeline/scripts
~/.hermes/profiles/luke/skills/ai-news-v2  →  ~/lux-in-tenebris-pipeline/skills
```

This means changes pushed to the repo are immediately visible to the Hermes agent
and the cron pipeline on the next run.