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
Hermes cron (06:30, no_agent=true, fire-and-forget)
  │
  ▼
lux-v2-cron.sh   outside this repo — a one-line stub Hermes requires
  │              (cron scripts must live under the profile's own
  │              scripts/ dir); execs straight into the repo below
  ▼
cron_wrapper.sh (nohup → run.sh &, backgrounds it — cron has a 3-min
  │              hard timeout, the pipeline itself runs ~2-3h)
  ▼
run.sh
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
  ├─ Step 2:  Scouts — ONE AT A TIME, all LLM agents, 20 min ceiling each
  │   ├─ X → Research → Official → OpenSource → Tools → Funding
  │   │     (+ fetch_trending.py curl fallback if trending < 3 items)
  │   ├─ Hardware
  │   ├─ YouTube (Python fetch, then LLM extraction over it)
  │   └─ Italia AI Spotlight
  │            see "Scout Concurrency" below for why this is not parallel
  │
  ├─ Step 3:  Validate 9 scout JSON files (missing/invalid → empty [])
  ├─ Step 4:  Editor → edition.json                              — LLM agent, the only FATAL step
  ├─ Step 5:  Image gen (Grok Imagine)          [non-fatal]      — LLM agent + xAI tool
  ├─ Step 6:  Render → index.html                                — pure code
  ├─ Step 7:  Podcast Pill (Castor/Luna)        [non-fatal]      — LLM agent + xAI TTS tool
  ├─ Step 8:  Wire articles (RSS → LLM)         [non-fatal]      — code + 1 LLM call/article
  ├─ Step 8b: Inject wire ticker                [non-fatal]      — pure code
  ├─ Step 8c: Inject one-shot banner            [non-fatal]      — pure code, marker-driven, self-consuming
  ├─ Step 8d: Making-of page                    [non-fatal]      — pure code, read-only on pipeline state
  └─ Step 9-11: Deploy
      ├─ Write .issue — deliberately NO second git reset here; step 1b
      │    already synced the deploy dir, and a second reset was found to
      │    silently discard the archive listing's own regeneration
      ├─ Copy new files (index.html, making-of.html, fonts, images,
      │    podcasts, style.css, edition.json) into the deploy dir
      ├─ update_headlines_history.py (cross-day dedup store)
      ├─ build_markdown.py — regenerates markdown editions; lives in the
      │    DEPLOY repo, not this one (see note in the table below)
      ├─ git add → commit → push
      └─ Final report + Telegram notify() at each milestone
```

Archiving happens in step 1b now, **before** today's overwrite, not after —
see [Issue Numbering & Archiving](#issue-numbering--archiving) for why.

## Agents & Responsibilities

"Agent" = an LLM call via a `SKILL.md` (judgment: what matters, how to phrase
it, what to draw). "Code" = plain Python/bash, deterministic, no model in the
loop. Every model/provider below is read directly out of `run.sh` — none
of these steps fall back to the Hermes profile default; every invocation
passes its model explicitly.

| Step | Kind | Model / Provider | Toolset | Reads | Writes |
|------|------|-------------------|---------|-------|--------|
| scout-x | agent | deepseek-v4-flash / localAIServer | x_search, file, terminal | `skills/_shared/sources.md` | `scout_x.json` |
| scout-research | agent | deepseek-v4-flash / localAIServer | web, file, terminal | — | `scout_research.json` |
| scout-official | agent | deepseek-v4-flash / localAIServer | web, file, terminal | `skills/_shared/sources.md` | `scout_official.json` |
| scout-opensource | agent | deepseek-v4-flash / localAIServer | web, x_search, file, terminal | — | `scout_opensource.json` (editorial + trending) |
| `fetch_trending.py` | code | — | curl (GitHub/HuggingFace) | — | merged into `scout_opensource.json`, only if the scout returned < 3 trending items |
| scout-tools | agent | deepseek-v4-flash / localAIServer | web, file, terminal | — | `scout_tools.json` |
| scout-funding | agent | deepseek-v4-flash / localAIServer | web, file, terminal | — | `scout_funding.json` |
| scout-hardware | agent | deepseek-v4-flash / localAIServer | web, x_search, file, terminal | — | `scout_hardware.json` |
| `youtube_scout.py` | code | — | RSS + yt-dlp + youtube-transcript-api | `skills/_shared/sources.md` (channel list) | `scout_youtube_raw.json` |
| scout-youtube | agent | deepseek-v4-flash / localAIServer | file | `scout_youtube_raw.json` | `scout_youtube.json` |
| scout-italia | agent | deepseek-v4-flash / localAIServer | web, file, terminal | `skills/_shared/sources.md` | `scout_italia.json` |
| editor | agent | deepseek-v4-flash / localAIServer | file | all `scout_*.json` + `headlines_history.json` | `edition.json` — **the only FATAL step**: no output here means no issue at all |
| image-gen | agent + tool | deepseek-v4-flash / localAIServer (orchestrator) + xAI Grok Imagine (`image_generate` tool, OAuth) | file, image_gen, terminal | `edition.json` | `images/*.jpg`, updates `edition.json` |
| `render.py` | code | — | — | `edition.json` + `template/` | `index.html` |
| podcast-pill | agent + tool | deepseek-v4-flash / localAIServer (dialogue) + xAI TTS (Castor/Luna voices, OAuth) | file, terminal | `edition.json` | `podcast_meta.json`, `podcasts/*.ogg` |
| `inject_podcast_pill.py` | code | — | — | `index.html`, `podcast_meta.json` | `index.html` (pill injected) |
| `wire_articles.py` | code + 1 agent call/article | deepseek-v4-flash / localAIServer | curl (RSS feeds from `skills/_shared/sources.md`) + `hermes chat` subprocess per article | RSS feeds | `scout_wire.json` |
| `inject_wire_ticker.py` | code | — | — | `index.html`, `scout_wire.json` | `index.html` (ticker injected) |
| `inject_banner.py` | code | — | — | `index.html`, `scripts/banner.json` | `index.html` (banner injected); deletes `banner.json` after firing so it never runs twice |
| `archive_issue.py` | code | — | — | `deploy/index.html` + the images/audio it actually references | `archive/YYYY-MM-DD/` snapshot; prunes deploy-root `images/`/`podcasts/` |
| `make_making_of.py` | code, read-only | — | — | scout JSON, run log, log mtimes, `edition.json` | `making-of.html` — parses what the pipeline already wrote, never touches pipeline state |
| `update_headlines_history.py` | code | — | — | `edition.json` | `headlines_history.json` |
| `build_markdown.py` | code | — | — | `edition.json` + `archive/` | `editions/*.md`, `latest.md` — **lives in the deploy repo** (`~/ai-news-deploy/scripts/`), the one piece of processing code outside this repo. `run.sh` step 11.5 calls it conditionally (`if -f ... `) so its absence is non-fatal. It stays deploy-side deliberately: markdown regeneration is entirely a function of what's already in the deploy repo (`edition.json` + `archive/`), so keeping it there means that repo can regenerate its own markdown editions without needing the pipeline repo cloned alongside it. |

### Meta / operator skills (not part of the daily run)

These skills exist for humans (or Claude) working *on* the pipeline, not for
the pipeline itself — `run.sh` never invokes them with `-s`:

- **orchestrator** — describes the whole pipeline; loaded when someone needs to understand or modify `run.sh`.
- **lux-hotfix** — surgical live-HTML fixes without re-running the pipeline (re-rendering would strip the podcast pill / wire ticker).
- **lux-status-reports** — Luke's preferred format for pipeline/scout status updates.
- **lux-image-pitfalls** — production-failure knowledge for image generation, loaded after `image-gen`.

A few more (deploy/domain/log-verification operations) exist only in the
operator's local Hermes profile, outside this repo, since they're tied to
personal infra/paths rather than to the pipeline's actual mechanism.

## Scout Concurrency — why sequential

Scouts run **one at a time**. They used to run 3-up in parallel phases; that
was removed on 2026-07-28.

A scout is not a single API request — it's a full multi-turn agent session
(web searches, tool calls, reasoning, retries). All of them target `localAIServer`,
which is **one self-hosted machine**, not a distributed API. Three concurrent
agent sessions saturate it and every one of them crawls.

The logs are unambiguous. Across 2026-07-26, 27 and 28, every 3-up phase ran
to *exactly* the per-scout ceiling and got killed:

| Day | Provider | Phase durations | Scouts completed |
|-----|----------|-----------------|------------------|
| 07-26 | localAIServer, 3-up | 10.1, 10.1, 10.0, 10.1 min | 14 ok / 14 failed |
| 07-27 | localAIServer, 3-up | 10.0, 10.1 min | 1 ok / 6 failed |
| 07-28 | localAIServer, 3-up | 10.0, 10.1, 10.0 min | 0 ok / 10 failed |
| 07-28 | distributed API, 3-up | 4.7, 6.7 min | 14 ok / 0 failed |

The 10-minute figures were the timeout ceiling of the day, not real work
duration — the scouts never finished. Against a distributed backend the same
scouts cleared a whole phase in under 7 minutes, i.e. comfortably inside even
the old ceiling. The variable was concurrency-per-backend, not the timeout.

Serialising costs wall clock and buys completion. Wall clock is close to free
here — it's a fire-and-forget 06:30 cron and nobody is watching it run — hence
the 4h master budget.

**Before re-parallelising**, confirm the inference backend can actually take
concurrent agent sessions. If the pipeline ever moves to a distributed
provider, parallel phases become reasonable again.

## Timeouts

Every LLM call is wrapped in `timeout`. Until 2026-07-28, five of them weren't
(italia scout, both editors, image gen, podcast) and could hang indefinitely —
visible in the logs as 40-minute stalls with no output.

| Budget | Value | Covers |
|--------|-------|--------|
| `TIMEOUT_SECS` | 20 min | each scout |
| `STEP_TIMEOUT_SECS` | 20 min | italia scout |
| `EDITOR_TIMEOUT_SECS` | 40 min | editor (own budget — see below) |
| `MEDIA_TIMEOUT_SECS` | 15 min | image gen, podcast (xAI-bound, not localAIServer) |
| `MASTER_TIMEOUT` | 4h | the whole pipeline |

### Measured timings (2026-07-29, first fully-sequential run)

All 9 scouts completed — the first time that had happened since the switch:

| Scout | Duration | | Scout | Duration |
|---|---|---|---|---|
| x | 7m17 | | funding | **13m33** |
| research | 7m01 | | hardware | 10m33 |
| official | 12m12 | | youtube | 0m58 |
| opensource | 12m57 | | italia | ~13m |
| tools | 10m17 | | **total** | **~87 min** |

Five of nine exceeded 10 minutes, which is exactly why the old 600s ceiling
killed every scout regardless of concurrency. The slowest is ~13.5 min, so the
20-minute ceiling has real headroom.

### Why the editor has its own budget

The editor is the only **FATAL** step: no `edition.json` means no newspaper at
all, and the run stops before render, images, podcast and deploy. It also does
the most work of any single call — 9 scout files, ~80 items, plus cross-day
dedup against `headlines_history.json`.

On 2026-07-29 it hit the shared 20-minute ceiling at 08:17:48 to the second and
killed the run; a manual re-run immediately afterwards finished in ~11 minutes.
The ceiling, not the workload, was the problem — so the editor now gets 40
minutes of its own while the scouts keep theirs.

Budget check: 87 (scouts) + 40 (editor) + 15 + 15 (media) + ~10 (wire)
≈ 2h50m, comfortably inside the 4h master timeout.

`MASTER_TIMEOUT` has to cover the **sum** of the sequential scouts, not their
max. It was 90 min under the old parallel layout; 9 sequential scouts at a
20-minute ceiling can exceed that on their own, so leaving it at 90 min would
have had the pipeline abort itself mid-run.

## Provider Pinning

Every LLM step passes `--provider "$PIPELINE_PROVIDER"` (= `localAIServer`) explicitly.
The Hermes profile default is deliberately unused: the operator chats on
openrouter, but the pipeline must stay on the self-hosted server.

This is pinned in one variable, with a warning block above it, because on
2026-07-28 an interactive session asked to raise the scout timeout also
rewrote all 8 `--provider localAIServer` flags to `openrouter` — unrequested, and
unnoticed until the day's edition had already been produced on the wrong
(paid, metered) backend.

## Critical Paths

| Path | Description |
|------|-------------|
| `~/lux-in-tenebris-pipeline/` | Source repo (pipeline code, skills, templates) |
| `~/.hermes/profiles/<profile>/scripts/v2/` | Symlink → pipeline scripts |
| `~/.hermes/profiles/<profile>/skills/ai-news-v2/` | Symlink → pipeline skills |
| `/tmp/v2/` | Working directory (scout JSON, images, output) |
| `~/ai-news-deploy/` | Deploy repo (published output) |

## Independent Credit Checks (image gen vs. podcast)

Image generation (Grok Imagine) and podcast TTS (Castor/Luna) both
authenticate against the same xAI OAuth account, so it's tempting to treat
one as a proxy for the other. They don't fail together reliably in
practice — archived issues for 2026-07-14 and 2026-07-24 both have zero
images yet a working podcast that same day. Until 2026-07-26, `run.sh`
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
`run.sh` only ever adds new files to them (`cp ... "$DEPLOY_DIR/images/"`)
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

- **Pipeline job:** 06:30 daily, `no_agent=true`, fire-and-forget (see `hermes cron create` in [docs/SETUP.md](SETUP.md#5-cron-job))
- **Watchdog:** 07:45 daily, verifies deploy succeeded — a second, separate cron job pointed at a small check script, not included in this repo

## Symlink Architecture

The repo is the single source of truth. Hermes accesses pipeline code through symlinks:

```bash
~/.hermes/profiles/<profile>/scripts/v2        →  ~/lux-in-tenebris-pipeline/scripts
~/.hermes/profiles/<profile>/skills/ai-news-v2  →  ~/lux-in-tenebris-pipeline/skills
```

This means changes pushed to the repo are immediately visible to the Hermes agent
and the cron pipeline on the next run.
