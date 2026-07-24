---
name: lux-v2-operations
description: "Lux in Tenebris V2 pipeline runtime operations, log paths, deploy destinations, and debugging procedures. Companion to orchestrator-v2."
---

# Lux V2 — Operations & Debugging

## Purpose
Runtime operational knowledge for the Lux in Tenebris V2 pipeline: where to find logs, how to check deploy status, pipeline URLs, and common troubleshooting procedures.

## Cron Job Chain

Pipeline triggered by a **no_agent cron job** at **06:30 daily**:

```
Cron (06:30, no_agent=true, fire-and-forget)
  ↓  ~/.hermes/profiles/luke/scripts/lux-v2-cron.sh
  ↓  exec → ~/lux-in-tenebris-pipeline/scripts/cron_wrapper.sh
  ↓  nohup → ~/.hermes/profiles/luke/scripts/v2/run_v2.sh &
  ↓  stdout → /tmp/v2/logs/cron_wrapper.log
  ↓  run log → /tmp/v2/logs/run_${DATE}.log
```

- **Cron job ID:** `29fa53d809c4`
- **Schedule:** `30 6 * * *` (every day at 06:30)
- **Cron output dir:** `~/.hermes/profiles/luke/cron/output/29fa53d809c4/` (contains only the launch message)

## Log Locations

All real pipeline logs live in `/tmp/v2/logs/`:

| File | Contains |
|------|----------|
| `cron_wrapper.log` | Wrapper nohup output |
| `run_${DATE}.log` | Main V2 pipeline orchestrator log |
| `editor_${DATE}.log` | DS editor (hermes CLI) log |
| `editor_k3_${DATE}.log` | K3 editor (hermes CLI) log |
| `imagegen_${DATE}.log` | Image generation log |
| `scout_${SCOPE}_${DATE}.out` | Per-scout stdout |
| `scout_${SCOPE}_${DATE}.err` | Per-scout stderr |

## Pipeline Working Directory

All pipeline state lives in `/tmp/v2/`:

- `/tmp/v2/scouts/` — scout JSON files (including `scout_wire_ds.json`, `scout_wire_k3.json`)
- `/tmp/v2/output/index.html` — DS edition HTML
- `/tmp/v2/output/k3/index.html` — K3 edition HTML
- `/tmp/v2/images/` — generated images (empty when xAI credits exhausted)
- `/tmp/v2/edition.json` — DS edition data
- `/tmp/v2/edition_k3.json` — K3 edition data
- `/tmp/v2/.issue` — current issue number
- `/tmp/v2/logs/` — all logs

## Deploy Destination

- **GitHub Pages URL:** `https://nttluke.github.io/luxintenebris-ai-news/`
- **K3 edition:** `https://nttluke.github.io/luxintenebris-ai-news/k3/`
- **Deploy repo:** `git@github.com:NTTLuke/luxintenebris-ai-news.git`
- **Deploy dir (local):** `/home/nttluke/ai-news-deploy/`
- **Deploy mechanism:** GitHub Actions workflow `.github/workflows/deploy.yml` — push to `main` triggers `deploy-pages` action
- **NOT the old `lux-in-tenebris` repo** — the live site is on `luxintenebris-ai-news`

## Checking Deploy Status

When Tavily is down (432 errors), use curl directly:

```bash
# Check if DS edition is live (should return 200)
curl -s -o /dev/null -w "%{http_code}" https://nttluke.github.io/luxintenebris-ai-news/

# Check K3 edition
curl -s -o /dev/null -w "%{http_code}" https://nttluke.github.io/luxintenebris-ai-news/k3/

# Verify today's date in the page title
curl -s https://nttluke.github.io/luxintenebris-ai-news/ | grep -oP '<title>[^<]+</title>'

# Check dateline date
curl -s https://nttluke.github.io/luxintenebris-ai-news/ | grep -oP 'dateline.*?>\K[^<]+' | head -3
```

## Pipeline Run Profile

- **Duration:** ~25 minutes (06:30 → ~06:55)
- **Typical scope:** 9 scouts, DS + K3 editions, wire articles, badge injection, layout transform
- **Images:** skipped when xAI credits exhausted (logged, non-blocking)
- **Podcast:** skipped when xAI TTS unavailable (logged, non-blocking)
- **Retry safety:** /tmp/v2/ directory is recreated each run. Safe to re-run if the pipeline fails mid-way.

## Issue Tracking

- Issue number persisted in `/tmp/v2/.issue` and `/home/nttluke/ai-news-deploy/.issue`
- Incremented daily by the archive step
- Archives stored in `/home/nttluke/ai-news-deploy/archive/YYYY-MM-DD/`

## Pitfalls

1. **Cron output is just the launch message** — The cron `no_agent` output only shows "V2 pipeline launched (PID X) at time". For real pipeline status, check `/tmp/v2/logs/run_${DATE}.log`.

2. **Tavily 432 errors** — Tavily extract frequently returns 432. Use curl directly to check GitHub Pages live status. This is a Tavily-side issue, not a pipeline failure.

3. **xAI credits exhaust** — When credits are zero, images and podcast are skipped. The pipeline logs this as a warning and continues. This is expected and non-blocking.

4. **GitHub Pages deploy delay** — After git push, GitHub Actions takes ~1-2 minutes to deploy. The site may briefly show the previous day's edition during this window.

5. **Symlinked skills** — The orchestrator-v2 skill is symlinked from `~/lux-in-tenebris-pipeline/skills/`. skill_manage cannot edit symlinked skills. To update, write directly to the symlink target path.