---
name: orchestrator-v2
description: "Lux in Tenebris V2 production pipeline. Bash orchestrator with fire-and-forget cron, 8 atomic scouts + 1 Python/LLM hybrid, editor, image-gen, render, podcast pill, wire articles, deploy to GitHub Pages."
---

# Orchestrator V2 — Production Pipeline

## Purpose
## Purpose
Daily AI news production: 8 atomic scouts + 1 hybrid → editor → image generation → HTML render → podcast pill → wire articles → deploy to GitHub Pages.

## Architecture — Cron is a Dumb Scheduler

**Core principle:** Cron is a scheduler, not a state manager. Each step is an isolated `hermes chat -q` invocation that reads/writes JSON files. No state flows through the agent — the bash script orchestrates everything.

```
Cron (08:00, no_agent=true, fire-and-forget)
  ↓
cron_wrapper.sh (nohup bash run_v2.sh &)
  ↓
run_v2.sh (bash orchestrator)
  ↓
Phase 1: 3 scouts in parallel (x, research, official)
Phase 2: 3 scouts in parallel (opensource, tools, funding)
Phase 3: 1 scout (hardware)
Phase 4: YouTube (Python RSS fetch + dedicated LLM scout)
  ↓
Editor (merge 8 scout JSONs → edition.json)
  ↓
Image-gen (lead + section images via xAI Grok)
  ↓
Render (Python → index.html)
  ↓
Podcast Pill (agent: generate Castor vs Luna dialogue from lead → 2× TTS → ffmpeg concat → inject into HTML)
  ↓
Wire Articles (RSS → AI → scout_wire.json)
  ↓
Inject ticker (post-process index.html)
  ↓
Git sync (fetch + reset to clean state)   ← ORDERED: reset BEFORE archive
  ↓
Archive current edition (self-contained snapshot)    ← AFTER reset, BEFORE copy
  ↓
Copy new files → save edition.json → update headline history → git add → commit → push
```

Each step is **stateless** — reads/writes JSON files in `/tmp/v2/`.

## Implementation

**Script location:** `~/.hermes/profiles/luke/scripts/v2/run_v2.sh`
**Cron wrapper:** `~/.hermes/profiles/luke/scripts/v2/cron_wrapper.sh`
**Headline history:** `~/.hermes/profiles/luke/scripts/v2/update_headlines_history.py` (extracts headlines from edition.json and appends to `headlines_history.json` in deploy dir — used by editor for cross-day dedup)
**Podcast injector:** `~/.hermes/profiles/luke/scripts/v2/inject_podcast_pill.py` (post-processes rendered HTML to add the podcast pill under the lead article)
**Cron job ID:** `29fa53d809c4` (08:00 daily, no_agent=true)
**Watchdog:** `369c43cef23d` (07:45 daily, checks deploy success)

## Cron Configuration — Fire-and-Forget Pattern

The cron system has a **120s hard timeout** per tick. To bypass:

1. **cron_wrapper.sh** — creates log dir, launches pipeline in background:
```bash
#!/bin/bash
# MUST create log dir BEFORE nohup redirect — /tmp is volatile
mkdir -p /tmp/v2/logs
nohup bash ~/.hermes/profiles/luke/scripts/v2/run_v2.sh >> /tmp/v2/logs/cron_wrapper.log 2>&1 &
echo "V2 pipeline launched (PID $!) at $(date)"
```

2. **Cron config** — `no_agent=true`, script mode:
```json
{
  "job_id": "29fa53d809c4",
  "script": "v2/cron_wrapper.sh",
  "no_agent": true,
  "schedule": "0 8 * * *"
}
```

**How it works:** cron executes wrapper (finishes <1s), wrapper spawns pipeline via nohup, cron tick succeeds. Pipeline runs autonomously in background for ~20 minutes.

## Full Pipeline Step Map

Current step numbering in `run_v2.sh`:

| Step | Component | Description | Non-fatal? |
|------|-----------|-------------|------------|
| 0 | Cleanup | Delete old scouts, images, output | No |
| 1 | Metadata | Compute date window, issue number | No |
| 2 | Scouts x4 | 8 scouts in 4 phases (parallel within phase) | No |
| 3 | Validation | Check all 8 scout files exist | No |
| 4 | Editor | `editor-v2` skill → edition.json | No |
| 5 | Image gen | `image-gen-v2` skill → lead + section images | **Yes** |
| 6 | Render | `render.py` → index.html | No |
| 7 | Podcast Pill | `podcast-pill` skill → dialogue + TTS + concat + inject | **Yes** |
| 8 | Wire Articles | `wire_articles.py` → scout_wire.json | **Yes** |
| 9 | Inject Ticker | `inject_wire_ticker.py` → add ticker to HTML | **Yes** |
| 10 | Deploy | git fetch → reset → archive → copy → commit → push | No |

**Non-fatal steps** (marked Yes) use `|| echo "...non-fatal"` — if they fail, the pipeline continues.
The podcast pill step is non-fatal because TTS or ffmpeg may fail without blocking the release.

## Production Deploy — Steps 10-13

4. **Step 10 — Sync deploy repo:** `git fetch origin && git reset --hard origin/main` to get clean state.
5. **Step 11 — Archive:** `archive_issue.py` saves the previous edition as a self-contained snapshot in `archive/YYYY-MM-DD/` (includes `index.html` + `style.css` + `fonts/` + `images/` + `edition.json`). **Runs AFTER git reset but BEFORE overwriting files**, so the regenerated `archive/index.html` listing is captured in the commit. See [archive-system reference](references/archive-system.md).
6. **Step 12 — Deploy:** Copy rendered HTML/images to deploy dir.
7. **Step 12b — Save edition.json:** Copy `edition.json` from `/tmp/v2/` to deploy dir root (persisted in git for historical analysis and headline dedup).
8. **Step 12c — Update headline history:** Run `update_headlines_history.py` to extract all headlines from the new edition and append to `headlines_history.json` (persisted in git). This file is read by the editor on the next run for cross-day dedup (see `editor-v2` skill, step 4b).
9. **Step 12d — Copy podcast audio:** Podcast .ogg from `/tmp/v2/podcasts/` is copied to deploy dir. The `podcasts/` directory is created in the deploy dir.
10. **Step 12e — Git:** `git add -A`, `git commit`, `git push origin main`.
11. **Step 13 — Report:** Output summary (scouts, wire, images, podcast, issue #).

**Script:** `~/.hermes/profiles/luke/scripts/v2/run_v2.sh` orchestrates Steps 10-13:
1. Step 10: `git fetch + git reset --hard origin/main` to clean state
2. Step 11: `archive_issue.py` to snapshot previous edition + regenerate listing
3. Step 12: Copy files, `git add -A && git commit && git push`
4. Step 13: Report summary (scouts, wire, images, issue #)

**Pre-requisites checked before deploy:**
- `edition.json` exists and is valid JSON
- At least 3 scout files have content (not empty arrays)
- `index.html` was successfully generated

**Watchdog verification:** At 07:45, an LLM-driven agent (cron job `369c43cef23d`) checks if the deploy was updated today. If something failed, it auto-fixes:
- **Deploy missing** → re-runs the pipeline
- **Podcast missing** → regenerates with Castor/Luna
- **Pill not injected** → runs injector, commits, pushes
See cron job `369c43cef23d` for the full prompt.

## Critical Rules

- **Each step is atomic and stateless.** Read from `/tmp/v2/scouts/`, write to `/tmp/v2/`. No state in agent context.
- **Scouts HAVE `write_file` tool.** They persist their own JSON. Parent does not need to receive and write.
- **Image-gen needs `terminal` tool** to copy images from Hermes cache to `/tmp/v2/images/`. Without it, images are generated but never reach the deploy directory. See `image-gen-v2` skill for details.
- **Content MUST be in ENGLISH.**
- **Cleanup happens at start** — `/tmp/v2/cleanup.sh` deletes old scout JSONs, images, HTML, ensuring each run starts fresh.
- **Never modify `run_v2.sh` (model flags, toolsets, step parameters, provider overrides, or any production config) without explicit user instruction.** Unsolicited changes to the orchestrator script are treated as mistakes — always explain the current configuration first and wait for a directive. See Pitfall #14.
- **Wire articles: post-process render output** — the wire ticker is injected via `inject_wire_ticker.py` AFTER `render.py` finishes, NOT by modifying `render.py`. The injector adds CSS (before `</head>`), ticker HTML (after `</header>`), modal + JS (before `</body>`).
- **Podcast Pill: standalone agent, post-process injector** — the podcast pill is generated by a separate `podcast-pill` skill (not part of editor or render). The audio is injected into the HTML by `inject_podcast_pill.py` AFTER render, same pattern as wire ticker. The skill is loaded via `hermes chat -q -s podcast-pill` with `-t file,terminal` toolset. See `podcast-pill` skill for details.
- **Editor receives DEPLOY_DIR path in prompt** — the editor invocation in `run_v2.sh` now passes `$DEPLOY_DIR/headlines_history.json` so the editor can read the headline history for cross-day dedup (step 4b in `editor-v2`). If the path ever changes, update it in both the script AND the scoped variables.
- **Nameplate template must match the HTML** — the `newspaper.html` template controls the nameplate text (`LVX IN <span class="lux">TENEBRIS</span>` — all caps, Latin). Changes to the HTML by hand get lost on the next pipeline run because `render.py` regenerates from the template. Always fix BOTH the template AND the current `index.html` on disk.

## Watchdog Timing

**07:30 is too early** — the pipeline needs ~25 minutes (cleanup + 8 scouts + editor + image-gen + render + podcast + wire + deploy). Watchdog is at **07:45** to give the pipeline time to complete before verification.

If watchdog triggers too early, it reports false failures because deploy hasn't happened yet.

## Pitfalls

### 0. `cron_wrapper.sh` MUST create log dir before redirecting
The wrapper launches the pipeline via `nohup ... >> /tmp/v2/logs/cron_wrapper.log 2>&1 &`. If the parent directory `/tmp/v2/logs/` doesn't exist, **the redirect fails silently** — `run_v2.sh` never starts, the wrapper exits 0 after the fallthrough `echo`, and cron reports `status: ok`.

**Why this happens:** `/tmp/` is volatile (cleaned on WSL restarts, tmpfs reboots, or `/tmp` cleanup scripts). If the machine restarted between runs, `/tmp/v2/logs/` is gone. `run_v2.sh` itself creates the directory at startup (`mkdir -p "$LOG_DIR"`), but the redirect in the **wrapper** happens before the pipeline script starts — chicken-and-egg.

**Symptoms:**
- Cron reports `last_status: "ok"` (wrapper exits 0)
- No `/tmp/v2/logs/` directory at all (not even empty)
- Deploy dir `index.html` is stale (yesterday's or older)
- No `.issue` file in `/tmp/v2/`

**Fix — always create the log dir in the wrapper, before the redirect:**
```bash
#!/bin/bash
mkdir -p /tmp/v2/logs
nohup bash /home/nttluke/.hermes/profiles/luke/scripts/v2/run_v2.sh >> /tmp/v2/logs/cron_wrapper.log 2>&1 &
echo "V2 pipeline launched (PID $!) at $(date)"
```

The `run_v2.sh` `mkdir -p "$LOG_DIR"` is still good practice (second safety net), but the wrapper is the only line of defence against a missing `/tmp/v2/logs/`.

**Verification after fix:**
```bash
# List all log dirs created during this run
ls /tmp/v2/logs/
# Should show: cron_wrapper.log, run_YYYY-MM-DD.log, scout_*.out, scout_*.err, etc.
```

### 1. Script path must be profile-relative
Cron looks for scripts in `~/.hermes/profiles/<profile>/scripts/`. Place both `run_v2.sh` and `cron_wrapper.sh` in `~/.hermes/profiles/luke/scripts/v2/`, not in `~/.hermes/scripts/v2/`.

### 2. cleanup.sh must actually DELETE, not just chmod
**Wrong:**
```bash
find /tmp/v2/scouts -type f -exec chmod 644 {} \;  # only changes permissions!
```

**Right:**
```bash
#!/bin/bash
find /tmp/v2/scouts /tmp/v2/images /tmp/v2/output -type f -delete 2>/dev/null
[ -f /tmp/v2/edition.json ] && rm -f /tmp/v2/edition.json
echo "cleanup done"
```

If cleanup only changes permissions but doesn't delete files, scouts from yesterday persist and poison today's run.

### 3. Scout JSON fallback on timeout
If a scout times out (600s) or fails, write empty fallback:
```bash
timeout 600 bash hermes chat ... > scout.json || echo "[]" > scout.json
```
Editor validates all 8 scout files exist. Empty array `[]` prevents validation failure.

### 4. Date window in scout prompts
Each scout call must include explicit date context:
```bash
"Today is $(date +%F), yesterday is $(date -d yesterday +%F). Window: from $(date -d yesterday +%F) to $(date +%F)."
```
Without this, scouts search wrong dates.

### 5. Nameplate template must match the HTML
The `newspaper.html` template (`~/.hermes/profiles/luke/skills/ai-news-24h/templates/newspaper.html`) controls the nameplate text (`LVX IN <span class="lux">TENEBRIS</span>` — all caps, Latin classic form). The pipeline's `render.py` generates `index.html` FROM this template. Fixing the nameplate by hand in the deployed HTML gets overwritten on the next pipeline run. Always fix BOTH the template AND the current `index.html`.

### 6. Git pull must happen BEFORE copy
Deploy step must `git pull --rebase` before copying `/tmp/v2/output/*` to avoid overwriting any manual changes. If pull fails (conflict), abort deploy and log error.

### 7. Archive step must run AFTER git reset but BEFORE git add
The archive step (Step 11) and the deploy sync (Step 10) have a **strict ordering**:
- ❌ **Wrong:** Archive → git reset → copy → add → commit  
  *git reset reverts the regenerated archive/index.html listing. The archive directory gets committed but the listing stays stale.*
- ✅ **Correct:** git reset → Archive → copy → add → commit  
  *Archive runs on the clean committed state, regenerates listing, both get captured in the commit.*

**Recovery from stale listing:** `python3 $SCRIPT_DIR/archive_issue.py $DEPLOY_DIR` re-reads all archive dirs and regenerates `archive/index.html`. Then `cd $DEPLOY_DIR && git add -A && git commit -m "fix: archive listing" && git push`.

**Symptoms of this bug:**
- New archive dir (`archive/YYYY-MM-DD/`) exists on disk and in git
- But `archive/index.html` listing is missing the latest entry

### 8. `$DEPLOY_DIR` (and all path variables) must be defined at the VERY TOP of the script
With `set -euo pipefail`, an **undefined variable causes immediate script abort** — no warning, no partial deploy.

**🔴 CRITICAL — the variable may be referenced far earlier than you think.** `DEPLOY_DIR` was initially defined at line 264 (inside Step 9 of the old script), but it was first referenced at line 183 (Step 4, for the issue counter). The `set -u` abort killed the entire pipeline silently — no deploy, no error in cron output except a glimpse in the cron_wrapper.log.

**The reliable fix: define EVERY path variable in the global section at the top of `run_v2.sh`**, alongside `PROFILE`, `V2_DIR`, `LOG_DIR`, `SCRIPT_DIR`, etc. Not "at the top of its section" — at the **file top**. This guarantees any step can reference them.

```bash
# ── at the top, right after PROFILE/V2_DIR/LOCATION/SCRIPT_DIR ──
DEPLOY_DIR="/home/nttluke/ai-news-deploy"
```

**Rule of thumb:** if a variable is a directory or file path, it goes in the global section (lines 9-19 of `run_v2.sh`). Only loop counters, per-step flags, and step-specific outputs belong inside a step block.

**Common sneaky references that cause `unbound` crashes:**
| Variable | First used at | Mistakenly defined at | Abort signal |
|----------|--------------|----------------------|-------------|
| `DEPLOY_DIR` | Step 4, line 183 (issue counter) | Step 9, line 264 | `unbound variable` at line 183 |

**Failure signature in cron:** cron reports `status: ok` (the wrapper `cron_wrapper.sh` finishes in <1s), but the nohup'd pipeline dies silently. No `/tmp/v2/logs/run_$(date +%Y-%m-%d).log` output for the deploy steps. Deploy dir `index.html` is stale.

**How to verify:**
```bash
# Check pipeline actually completed
tail -5 /tmp/v2/logs/cron_wrapper.log
# Look for "✅ V2 PIPELINE COMPLETE" — if missing, pipeline crashed.

# Check deploy dir freshness
date -r ~/ai-news-deploy/index.html
# Should be today.

# Check for shell errors
grep -i "unbound\|error\|exit" /tmp/v2/logs/cron_wrapper.log
```

### 9. YouTube Phase 4 uses a dedicated model (DeepSeek V4 Flash)
The YouTube scout is a **hybrid**: a Python script (`youtube_scout.py`) fetches video data via RSS + yt-dlp + youtube-transcript-api, then a dedicated LLM scout (`scout-v2-youtube` with `deepseek/deepseek-v4-flash`) writes articles. This is different from all other scouts that use the profile's default model. See [youtube-scout reference](references/youtube-scout.md) for channel list, adding channels, and known issues.

**The `hermes chat -q` call MUST include `-m deepseek/deepseek-v4-flash --provider openrouter`.** If omitted, the scout defaults to the profile's model (likely a different provider) and may fail or produce poor results.

### 10. YouTube scout validation loop must include "youtube"
The validation loop in Step 3 iterates `$SCOUT_NAMES` — when adding a new scout, append its name to the variable. Otherwise it silently gets an empty fallback JSON and the editor sees 0 YouTube articles. The report also needs updating (`SCOUT_COUNT/8` instead of `SCOUT_COUNT/7`).

### 11. YouTube section missing / in Quick Hits — check item count
If the YouTube section doesn't appear in the edition, check the youtube scout output count:
```bash
python3 -c "import json; print(len(json.load(open('/tmp/v2/scouts/scout_youtube.json'))))"
```
The editor-v2 skill requires **≥2 YouTube items** to create a dedicated section. With 0-1 items, they get merged into Quick Hits. This is by design — a single video doesn't warrant a full section card.

### 12. Issue counter must persist outside /tmp
The issue counter lives in `.issue` in the deploy dir (`~/ai-news-deploy/.issue`) and is committed to git. `/tmp/v2/.issue` is a secondary copy. **Why:** /tmp is volatile (cleaned on WSL restarts, tmpfs reboots). If the counter lives only in `/tmp/v2/.issue`, a reboot resets it to #1, corrupting the archive numbering.

**Fix applied 2026-07-05:** `run_v2.sh` now reads from `$DEPLOY_DIR/.issue` first, falls back to `$V2_DIR/.issue`, then writes to BOTH. The deploy dir copy is in git and survives reboots.

**Recovery if the counter was reset:** Check the archive listing for the last correct issue number:
```bash
grep 'No\.' ~/ai-news-deploy/archive/index.html | head -1
# e.g. "No. 9" → next should be 10
echo "10" > ~/ai-news-deploy/.issue
echo "10" > /tmp/v2/.issue
```
Then update the deployed HTML's `No. 1` → `No. 10` and the archive listing, commit, push.

### 13. Podcast Pill: non-fatal but SILENT failure — can block pipeline

The podcast pill step is marked non-fatal (`|| echo "non-fatal"`). However, on
2026-07-08 the agent hung indefinitely writing a Python sub-script instead of
using the `text_to_speech` tool directly. The `hermes chat -q` call has no
timeout — it blocked for 30+ minutes, preventing ANY deploy that day.

**🔴 CRITICAL:** A non-fatal step that hangs (instead of exiting with error) is
worse than a fatal one. The `||` fallback never triggers because the process
never exits.

**Mitigations applied:**
- The `podcast-pill` skill now carries a "30 second budget" rule
- The skill has explicit pitfalls about using tools (not Python imports)
- The skill has duration limits to prevent overshoot (119s → capped at 75s)

**Failure symptoms:**
- Pipeline log shows `[step 7] podcast pill...` with nothing after it for 30+ min
- No deploy happened (git log shows yesterday's commit)
- No error messages — just silence

**To diagnose:**
```bash
# Check if pipeline is still running
ps aux | grep "run_v2.sh" | grep -v grep

# If running >25 minutes, it's stuck. Kill and complete manually:
# (see recovery script in podcast-pill/references/podcast-pill-production-fixes.md)
```

The podcast pill step is marked non-fatal (`|| echo "non-fatal"`). If it fails (TTS rate limit, ffmpeg not found, dialogue generation timeout), the pipeline continues and the release goes out without the pill.

**Failure symptoms:**
- Pipeline log shows `⚠ podcast pill returned non-zero (non-fatal)`
- Or `⚠ podcast meta not found, skipping injection`
- The release is published normally, just without the audio pill

**To debug a failed podcast step:**
```bash
# Check the podcast agent log
cat /tmp/v2/logs/podcast_$(date +%Y-%m-%d).log

# Check if metadata was generated
ls -la /tmp/v2/podcast_meta.json

# Check if audio was generated
ls -la /tmp/v2/podcasts/
```

### 14. Premature model changes to run_v2.sh — always ask first

**This session's error:** The user asked "which model does the editor use?" While answering, I proactively patched `run_v2.sh` to set Grok-4 as the editor's model. The user had NOT requested any change and corrected me immediately ("NON devi cambiare nulla").

**Rule:** When asked about model configuration, ANSWER the question with facts — do not act on the information until explicitly directed. Pointing out "the editor currently uses X, it could be changed to Y by adding `-m Z` to line N" is informative. Actually patching the file is a change that needs confirmation.

**Why this matters:** `run_v2.sh` is a production orchestrator. A wrong model flag can break the entire pipeline (invalid model ID, incompatible provider, rate-limit exhaustion, cost explosion). Changes must be deliberate and user-approved.

### 15. Re-deploy mid-day archives current issue under today's date
If the pipeline is re-run mid-day (e.g. manual force-run to fix an issue), the archive step runs against the already-deployed live issue — so today's issue gets archived under today's date. This is not the normal flow (normally yesterday's issue gets archived). The double-archive self-resolves on the next morning's run when the current live version overwrites the archive copy.

**Not a bug to fix** — just be aware that running `archive_issue.py` mid-day produces an archive entry that looks like today's issue was already archived. It gets corrected tomorrow.

### 16. Deploy dir index.html may be stale or corrupted between runs
The deploy dir's `index.html` on disk can differ from `git HEAD:index.html` (e.g. uncommitted overwrites from a manual test, or a stale version from a previous failed run). Before injecting any post-processor (wire ticker, podcast pill), always verify or restore from git:

```bash
cd ~/ai-news-deploy && git checkout index.html
```

This happened during the podcast pill preview: the deploy dir had a stale `lang="it"` generic HTML from an earlier version, not the Lux newspaper. The `git checkout` fixed it.

## Archive System

The pipeline archives the **previous** edition (the committed one) before overwriting it with the new one. The archive is called in `run_v2.sh` Step 11, AFTER `git fetch + git reset --hard origin/main` (Step 10) but BEFORE copying new files (Step 12).

**Critical ordering rule (fix applied 2026-07-04):** The archive step MUST run AFTER `git reset --hard origin/main` but BEFORE `git add -A`. Previously it ran before the reset, causing the regenerated `archive/index.html` listing to be reverted by the reset — only the new archive directory got committed, not the updated listing.

### Script

`~/.hermes/profiles/luke/scripts/v2/archive_issue.py`

### What it does

1. Reads `~/ai-news-deploy/index.html` to extract issue number + date
2. Creates `archive/YYYY-MM-DD/` in the deploy dir
3. Copies into it: `index.html` + `style.css` + `fonts/` + `images/` + **`edition.json`** — self-contained snapshot with both rendered HTML and structured data, fully renders standalone
4. Rewrites the ◆ Archive link inside the archived HTML from `archive/` to `/luxintenebris-ai-news/archive/` (absolute path) so it works from the subdirectory
5. Regenerates `archive/index.html` with a chronological listing of all past issues

### Archive link on the front page

Added in `newspaper.html` template alongside the issue number:

```html
<span class="right">No. {{ISSUE_NO}} <a href="/luxintenebris-ai-news/archive/" class="ar" title="Browse past issues">◆ Archive</a></span>
```

**CRITICAL — use absolute path, not relative:** `href="/luxintenebris-ai-news/archive/"` works from every page including archived copies. A relative `href="archive/"` breaks when navigating inside `archive/YYYY-MM-DD/` → resolves to `archive/YYYY-MM-DD/archive/` (404).

The archive listing page at `/luxintenebris-ai-news/archive/` also uses absolute path for the "← Current Issue" back link.

### Self-contained directory

Each archive directory needs these to render correctly:
```
archive/2026-07-02/
├── index.html    ← frozen snapshot (◆ Archive link rewritten to absolute path)
├── style.css     ← copied from deploy root
├── edition.json  ← structured data (headlines, sources, URLs)
├── fonts/*.woff2 ← copied from deploy root
└── images/*.jpg  ← copied from deploy root
```

Without `style.css` and `fonts/`, the archived page renders unstyled (plain white background, serif text, broken layout). The archive script copies these automatically.

### Pitfalls — Archive

#### a) Archive step runs before git add — listing must survive commit
The archive step runs AFTER `git reset --hard origin/main` but BEFORE `git add -A`. This is intentional: the regenerated `archive/index.html` listing must be included in the commit. Moving the archive call before the reset causes the listing to be reverted silently.

**Recovery if listing is stale:** Run `python3 $SCRIPT_DIR/archive_issue.py $DEPLOY_DIR` to regenerate the listing from all archive directories on disk, then `cd $DEPLOY_DIR && git add -A && git commit -m "fix: archive listing" && git push`.

## Monitoring

### First Response — "Why didn't today's release go up?"

```bash
# 1. Check if the pipeline even started
tail -5 /tmp/v2/logs/cron_wrapper.log
# Look for "✅ V2 PIPELINE COMPLETE" — if missing, pipeline crashed.

# 2. Check the run log for bash errors (set -u kills silently)
grep -i "unbound\|error\|exit\|traceback" /tmp/v2/logs/run_$(date +%Y-%m-%d).log 2>/dev/null || echo "No errors in run log"

# 3. Check deploy dir freshness
date -r ~/ai-news-deploy/index.html
# Should be today. If stale, pipeline never reached the deploy steps.

# 4. Check git
cd ~/ai-news-deploy && git log --oneline -1

# 5. Check the issue counter
cat ~/ai-news-deploy/.issue 2>/dev/null || echo "No issue file"
```

### Standard monitoring

After cron trigger:
```bash
# Pipeline running?
ps aux | grep "run_v2.sh" | grep -v grep

# Current step
tail -30 /tmp/v2/logs/cron_wrapper.log

# Scout files generated?
ls -lh /tmp/v2/scouts/scout_*.json

# Final outputs?
ls -lh /tmp/v2/edition.json /tmp/v2/output/index.html /tmp/v2/images/*.jpg /tmp/v2/podcasts/*.ogg
ls -lh ~/ai-news-deploy/index.html

# Archive created?
ls -ld ~/ai-news-deploy/archive/$(date +%Y-%m-%d)/
ls -lh ~/ai-news-deploy/archive/$(date +%Y-%m-%d)/*.{html,css,json}

# Headline history
ls -lh ~/ai-news-deploy/headlines_history.json
python3 -c "import json; d=json.load(open('$HOME/ai-news-deploy/headlines_history.json')); print(f'{len(d[\"headlines\"])} headlines in history')"

# Podcast pill
ls -lh ~/ai-news-deploy/podcasts/$(date +%Y-%m-%d).ogg 2>/dev/null || echo "No podcast for today"
```

## Post-Deploy QA

Run link validation after deploy to catch `href="#"` (self-links) and dead URLs. See `references/link-validation.md` for the full workflow — quick grep check + batch HTTP-status scan.

Also check the nameplate text is `LVX IN <span class="lux">TENEBRIS</span>` (all caps, Latin) — the template can revert on pipeline runs if someone edits the HTML directly without updating the template. See `references/injection-pitfalls.md` for details.

## What This Replaced

**V1 (deprecated):** Monolithic `ai-news-24h` skill with all logic in one agent, using `delegate_task` for scouts. Problems:
- Agent held state across entire pipeline
- If scout failed, agent tried to recover inline
- Impossible to test individual scouts
- Prompt grew to 500+ lines

**V2 (current):** Atomic steps + bash orchestration. Each scout is isolated, stateless, and can be run independently. Pipeline is deterministic and testable.

## When to Use This

- Daily production runs (cron handles scheduling)
- Debugging: run individual scouts via `hermes chat -q` with specific scout skill
- Testing new scouts: create `scout-v2-*` skill, add phase to `run_v2.sh`
- Switching models: edit toolset flags in `run_v2.sh` (e.g., change `-t x_search,file` to `-t x_search,file,web`)
- Understanding model topology: see `references/model-configuration.md` for where every step's model is specified.

## What This is NOT

- **Not a state manager** — bash script is orchestrator, agent just executes atomic steps
- **Not interactive** — no user input during pipeline execution
- **Not recoverable mid-run** — if a step fails, start over (stateless design)

## Extension: RSS Wire-Articles Scout

An alternative data-source pattern that feeds the V2 pipeline: **deterministic RSS fetch + LLM article writing** instead of LLM-driven web search. Useful for catching coverage the existing scouts might miss (cross-publisher, Google News aggregation).

### Architecture — Two Strictly Separated Stages

```
Stage 1 (DETERMINISTIC, pure Python — no LLM):
  RSS feed(s) → keyword filter → URL resolution → download source article
  → extract text → dedup → rank.
  Same input always yields the same selection.

Stage 2 (THE ONLY LLM CALL):
  For each selected item, call `hermes chat -q` ONCE with a tightly
  controlled prompt built from the facts fetched in Stage 1. The model
  writes an ORIGINAL article grounded in that text.
```

### Implementation

**Script:** `~/.hermes/profiles/luke/scripts/v2/wire_articles.py`
**Test pipeline:** `~/.hermes/profiles/luke/scripts/v2/test_wire_pipeline.sh`
**Test output:** `/tmp/v2/test-wire/index.html`

Run standalone (no production touch):
```bash
bash ~/.hermes/profiles/luke/scripts/v2/test_wire_pipeline.sh
```

### Wire Articles JSON Shape (output of stage 2)

```json
[
  {
    "headline": "…",
    "body": "…\n\n*editorial note in italics*\n*— Written by AI (deepseek/deepseek-v4-flash)*",
    "source": "The Verge",
    "source_url": "https://…",
    "original_title": "…",
    "published": "…",
    "generated_at": "…"
  }
]
```

### Critical styling rule — match production EXACTLY

When rendering wire articles into the Lux in Tenebris page:

1. **Use the EXACT production CSS variables** (`--ink`, `--type`, `--ember`, `--lux`, `--rule`, `--rule-strong`, `--muted`, `--serif`, `--sans`) — never introduce custom color values, new backgrounds, or different fonts.
2. **Ticker position:** between the masthead and the lead-zone (`<div class="lead-zone">`), NOT above the masthead and NOT inside the lead article.
3. **Label color:** `--ember` (hot accent), not custom burgundy/red.
4. **Do not change the existing production layout** — the masthead, lead story, sections, trending, and footer must render exactly as they do in production. Only add the ticker and the wire-cards section below the lead story.

### Injection technique — `inject_wire_ticker.py`

The ticker is added via a standalone post-processor, NOT by modifying `render.py`:

```bash
python3 ~/.hermes/profiles/luke/scripts/v2/inject_wire_ticker.py \
  /tmp/v2/output/index.html \
  /tmp/v2/scouts/scout_wire.json \
  --output /tmp/v2/output/index.html
```

**What it injects:**
- **CSS:** wrapped in `<style>` tags, inserted before `</head>`. Production Lux uses `link rel="stylesheet" href="style.css"`, NOT inline `<style>`, so the regex targets `</head>` not `</style>`.
- **Ticker HTML:** inserted after `</header>` (masthead close), immediately before `<div class="lead-zone">`.
- **Modal HTML:** before `</body>`.
- **JS:** before `</body>`.

**Critical — CSS variable names must match production:**
The injected CSS uses `var(--rule)`, `var(--serif)`, `var(--sans)`, `var(--muted)`, `var(--type-dim)`, `var(--lux-soft)`, `var(--ink)`, `var(--type)`, `var(--rule-strong)`, `var(--ember)`. These are the EXACT variable names defined in `style.css` — do NOT use shortened aliases (`--ru`, `--se`, `--sa`, `--mu`, `--td`, `--ls`).

### Pitfalls — wire articles

#### 1. hermes chat -q stdout pollution
`wire_articles.py` calls `hermes chat -q` via subprocess. Hermes writes warnings (`Warning: Unknown toolsets: messaging`) to stdout mixed with the LLM response. The `call_hermes()` function filters out lines starting with `Warning:` — if new warning prefixes appear, extend the filter.

#### 2. Google News RSS URL resolution is fragile
The `resolve_url()` function tries base64-decoding the Google article token (Google changes format periodically) then HTTP redirect. Fix: use direct publisher RSS feeds (TechCrunch, Ars Technica, Wired) instead of Google News.

#### 3. No trafilatura available (PEP 668)
The system is PEP 668-locked: `pip install` and `uv pip install --system` both fail. `python3 -m venv` also fails (ensurepip missing). The crude HTML stripper fallback is the only option. Use direct RSS feeds that have full-text content to compensate.

#### 4. Direct RSS feeds produce false positives
Publisher feeds include non-AI articles that mention "AI" incidentally ("Dyson AI-powered vacuum promo codes"). After each run, check `scout_wire.json` and extend the `DENY` list in `wire_articles.py` with the offending term.

#### 5. Ticker position: between masthead and lead image
The ticker sits between `</header>` and `<div class="lead-zone">`. NOT above the masthead, NOT inside the lead article. Visual hierarchy: masthead → ticker → lead image → lead headline/grid.

#### 6. Deploy dir may have stale index.html
`~/ai-news-deploy/index.html` on disk may differ from `git HEAD:index.html` (e.g. uncommitted overwrites from a different tool/script). Always verify with `git show HEAD:index.html` before injecting, or checkout the committed version first.

### When to Use

- Testing the RSS + LLM writing approach without breaking production
- Experimenting with new rendering patterns (scrolling ticker, modal articles)
- Evaluating Google News coverage vs the existing scout sources
- Benchmarking article quality from deterministic retrieval vs LLM-driven search