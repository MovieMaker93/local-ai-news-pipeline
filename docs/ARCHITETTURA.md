# Architecture — Lux in Tenebris V2 Pipeline

## Overview

Daily pipeline that produces an AI newspaper in dark broadsheet style.
Cron → wrapper → bash orchestrator → 9 scouts + wire → editor → image
generation → HTML render → podcast → deploy.

Every step is either an **LLM agent** (a `SKILL.md`, invoked as `hermes chat
-s <skill>`, used wherever the task needs judgment) or **plain code**
(Python/bash, used wherever the task is mechanical and must not depend on a
model's mood that day). Steps never call each other directly — they only
read/write JSON or HTML files under `/tmp/v2/`, which is what makes each one
independently retriable and lets a failure in one stay contained to that
stage. See [Agents & Responsibilities](#agents--responsibilities) for the
full breakdown of which is which.

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
  ├─ Step 1:  Metadata (date window)
  ├─ Step 1b: Sync deploy dir to origin (git reset --hard) — resolve issue #
  │            from the LIVE index.html's own masthead (not the .issue file,
  │            which a crashed run can leave stale/unpushed). Same date as
  │            today → reuse that issue number (same-day re-run). Different
  │            date → increment, and archive that predecessor edition NOW,
  │            before this run's files overwrite it.
  │
  ├─ Step 2:  Scouts (5 phases, parallel within each) — all LLM agents
  │   ├─ Phase 1: X, Research, Official        (3 in parallel)
  │   ├─ Phase 2: OpenSource, Tools, Funding    (3 in parallel)
  │   │            + fetch_trending.py curl fallback if trending < 3 items
  │   ├─ Phase 3: Hardware                      (1)
  │   ├─ Phase 4: YouTube (Python fetch + LLM scout)  (1 hybrid)
  │   └─ Phase 5: Italia AI Spotlight           (1)
  │
  ├─ Step 3:  Validate 9 scout JSON files (missing/invalid → empty [])
  ├─ Step 4:  Editor (DS) → edition.json                         — LLM agent
  ├─ Step 4b: Editor (K3) → edition_k3.json  [runs, but unused — see Known Idle Work]
  ├─ Step 5:  Image gen (Grok Imagine)          [non-fatal]      — LLM agent + xAI tool
  ├─ Step 6:  Render DS → index.html                             — pure code
  ├─ Step 6d: Inject version badge (DS only — K3 badge no-ops, no k3/index.html exists)
  ├─ Step 6e: K3 layout transform (no-ops — same reason)
  ├─ Step 7:  Podcast Pill (Castor/Luna)        [non-fatal]      — LLM agent + xAI TTS tool
  ├─ Step 8:  Wire Articles (DS + K3) + ticker injection [non-fatal]
  │            (K3 wire runs and is written, but never injected — no k3/index.html)
  └─ Step 9-11: Deploy
      ├─ git fetch + reset --hard (defensive re-sync; real sync was step 1b)
      ├─ Copy new files to deploy dir (today's edition overwrites yesterday's)
      ├─ update_headlines_history.py (cross-day dedup store)
      ├─ git add → commit → push
      └─ Final report
```

Archiving happens in step 1b now, **before** today's overwrite, not after —
see [Issue Numbering & Archiving](#issue-numbering--archiving) for why.

## Agents & Responsibilities

"Agent" = an LLM call via a `SKILL.md` (judgment: what matters, how to phrase
it, what to draw). "Code" = plain Python/bash, deterministic, no model in the
loop. Every model/provider below is read directly out of `run_v2.sh` — none
of these steps fall back to the Hermes profile default; every invocation
passes its model explicitly.

| Step | Kind | Model / Provider | Toolset | Reads | Writes |
|------|------|-------------------|---------|-------|--------|
| scout-v2-x | agent | deepseek-v4-flash / localAIServer | x_search, file, terminal | — | `scout_x.json` |
| scout-v2-research | agent | deepseek-v4-flash / localAIServer | web, file, terminal | — | `scout_research.json` |
| scout-v2-official | agent | deepseek-v4-flash / localAIServer | web, file, terminal | — | `scout_official.json` |
| scout-v2-opensource | agent | deepseek-v4-flash / localAIServer | web, x_search, file, terminal | — | `scout_opensource.json` (editorial + trending) |
| `fetch_trending.py` | code | — | curl (GitHub/HuggingFace) | — | merged into `scout_opensource.json`, only if the scout returned < 3 trending items |
| scout-v2-tools | agent | deepseek-v4-flash / localAIServer | web, file, terminal | — | `scout_tools.json` |
| scout-v2-funding | agent | deepseek-v4-flash / localAIServer | web, file, terminal | — | `scout_funding.json` |
| scout-v2-hardware | agent | deepseek-v4-flash / localAIServer | web, x_search, file, terminal | — | `scout_hardware.json` |
| `youtube_scout.py` | code | — | RSS + yt-dlp + youtube-transcript-api | 10 fixed channel IDs | `scout_youtube_raw.json` |
| scout-v2-youtube | agent | deepseek-v4-flash / localAIServer | file | `scout_youtube_raw.json` | `scout_youtube.json` |
| scout-v2-italia | agent | deepseek-v4-flash / localAIServer | web, file, terminal | — | `scout_italia.json` |
| editor-v2 | agent | deepseek-v4-flash / localAIServer | file | all `scout_*.json` + `headlines_history.json` | `edition.json` |
| editor-v2-k3 | agent | kimi-k3 / localAIServer | file | all `scout_*.json` + `headlines_history.json` | `edition_k3.json` — **unused, see below** |
| image-gen-v2 | agent + tool | deepseek-v4-flash / localAIServer (orchestrator) + xAI Grok Imagine (`image_generate` tool, OAuth) | file, image_gen, terminal | `edition.json` | `images/*.jpg`, updates `edition.json` |
| `render.py` | code | — | — | `edition.json` + `template/` | `index.html` |
| `inject_version_badge.py` | code | — | — | `index.html` | `index.html` (badge injected) |
| `transform_layout_k3.py` | code | — | — | `k3/index.html` | currently a no-op (that file never exists) |
| podcast-pill | agent + tool | deepseek-v4-flash / localAIServer (dialogue) + xAI TTS (Castor/Luna voices, OAuth) | file, terminal | `edition.json` | `podcast_meta.json`, `podcasts/*.ogg` |
| `inject_podcast_pill.py` | code | — | — | `index.html`, `podcast_meta.json` | `index.html` (pill injected) |
| `wire_articles.py` (DS) | code + 1 agent call/article | deepseek-v4-flash / localAIServer | curl (4 fixed RSS feeds) + `hermes chat` subprocess per article | RSS feeds | `scout_wire_ds.json` |
| `wire_articles.py` (K3) | code + 1 agent call/article | kimi-k3 / localAIServer | same | same | `scout_wire_k3.json` — **unused, see below** |
| `inject_wire_ticker.py` | code | — | — | `index.html`, `scout_wire_ds.json` | `index.html` (ticker injected) |
| `archive_issue.py` | code | — | — | `deploy/index.html` + the images/audio it actually references | `archive/YYYY-MM-DD/` snapshot; prunes deploy-root `images/`/`podcasts/` |
| `update_headlines_history.py` | code | — | — | `edition.json` | `headlines_history.json` |

### Meta / operator skills (not part of the daily run)

Four skills exist for humans (or Claude) working *on* the pipeline, not for
the pipeline itself — `run_v2.sh` never invokes them with `-s`:

- **orchestrator-v2** — describes the whole pipeline; loaded when someone needs to understand or modify `run_v2.sh`.
- **lux-v2-operations** — log paths, deploy destinations, debugging procedures.
- **lux-v2-domain** / **lux-v2-domain-reference** — custom-domain (Cloudflare/GitHub Pages) setup notes.

## Known Idle Work

Since K3 rendering was removed from `run_v2.sh` (2026-07-25), two steps still
run to completion every day but produce output nothing reads:

- **editor-v2-k3** (step 4b) — a full LLM call over every scout file, writing `edition_k3.json`.
- **`wire_articles.py --model kimi-k3`** (step 8) — up to 5 more LLM calls, writing `scout_wire_k3.json`.

Neither is wired to anything downstream — there is no `k3/index.html` to
inject them into. This costs real time and API spend for a discarded
result. It's left as-is deliberately (see the repo's commit history around
2026-07-26) pending a decision on whether K3 gets fully restored (re-add the
render step, these calls become useful again) or fully removed (delete these
two calls along with the badge/layout-transform no-ops).

## Critical Paths

| Path | Description |
|------|-------------|
| `~/lux-in-tenebris-pipeline/` | Source repo (pipeline code, skills, templates) |
| `~/.hermes/profiles/luke/scripts/v2/` | Symlink → pipeline scripts |
| `~/.hermes/profiles/luke/skills/ai-news-v2/` | Symlink → pipeline skills |
| `/tmp/v2/` | Working directory (scout JSON, images, output) |
| `~/ai-news-deploy/` | Deploy repo (published output) |

## Independent Credit Checks (image gen vs. podcast)

Image generation (Grok Imagine) and podcast TTS (Castor/Luna) both
authenticate against the same xAI OAuth account, so it's tempting to treat
one as a proxy for the other. They don't fail together reliably in
practice — archived issues for 2026-07-14 and 2026-07-24 both have zero
images yet a working podcast that same day. Until 2026-07-26, `run_v2.sh`
skipped the podcast step outright whenever image gen had failed on credits,
which meant podcast attempts were being preempted on days they'd likely have
succeeded. Each step now runs its own pre/post credit check against its own
log (`imagegen_${TODAY}.log` / `podcast_${TODAY}.log`) instead of one
inheriting the other's result.

## Issue Numbering & Archiving

Resolved in step 1b, against a deploy dir that was just `git reset --hard`
to `origin/main` — i.e. the last **truly published** state, not whatever a
previous crashed run happened to leave lying around locally.

- **Issue number**: read from the live `index.html`'s own masthead (`No. X`
  / the title's date), not from the `.issue` file. Same date as today → this
  is a same-day re-run, reuse that issue number. Earlier date → increment.
- **Archiving**: only on the increment path, and only *then* — the
  predecessor edition (whatever was live before this run) gets archived into
  `archive/<its own date>/` right now, before this run's files overwrite it.

Both fixes came from the same 2026-07-27 incident: a run crashed mid-deploy
after bumping `.issue` locally but before pushing anything. The recovery
re-run read that stale, unpushed `.issue` value and incremented again,
silently skipping issue #31 and publishing #32 instead — and `edition.json`
was left two issues behind since the manual recovery didn't update it
either. Reading state from the live HTML instead of `.issue`/`edition.json`
sidesteps both: it's always the actual last-published truth, immune to any
local mess a crash leaves behind.

This also fixes a standing gap: previously, each day archived *itself*
right after publishing (at the very end of that day's own run). If that
day's run never reached its own archive step — exactly what happened on
2026-07-26, which crashed at the editor step — that day's edition was never
archived, and got silently lost from `archive/` when the next successful
run overwrote it (its content survives only in the deploy repo's git
history, not under `archive/`). Archiving the predecessor *before*
overwriting it, on every run, means an edition gets archived at the latest
by the following day's run — it no longer depends on that edition's own run
having succeeded end-to-end.

## Asset Lifecycle (images / podcasts / archive)

`archive_issue.py` copies into `archive/YYYY-MM-DD/` **only** the images and
audio that edition's own `index.html` actually has an `<img src>` / `<audio
src>` for — never a blind copy of the whole `deploy/images/` or
`deploy/podcasts/` directory. It then prunes the deploy-root
`images/`/`podcasts/` folders down to whatever that same (about-to-be-
superseded) edition still references. Nothing is lost by this: that
edition's real usage was already captured in its own archive snapshot
first, in the same call.

Since archiving now runs in step 1b — on the *predecessor*, before step 10
copies in today's new images — there's a one-day lag in root cleanup
compared to before: today's images sit in `deploy/images/` until tomorrow's
step 1b prunes them (using tomorrow's predecessor check, i.e. today's own
references). Harmless, just a day later than the old same-day-cleanup
timing.

This matters because those root folders are otherwise never cleaned —
`run_v2.sh` only ever adds new files to them (`cp ... "$DEPLOY_DIR/images/"`)
and nothing used to remove old ones. Before this was fixed (2026-07-26),
every new archive snapshot picked up the entire accumulated history of
images/podcasts instead of just its own day, so archive size grew roughly
with total site age rather than with issue size (577MB across 24 days,
mostly orphaned files no page linked to, since image gen has been failing
intermittently since 2026-07-13).

## Non-Fatal Steps

Steps marked `[non-fatal]` use `|| echo "..."` / `|| true` — failure doesn't
block the pipeline; the day's edition still deploys without that piece.

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
