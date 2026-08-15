# Lux in Tenebris — Pipeline

Pipeline components for the daily AI news newspaper **LVX IN TENEBRIS**.

Live at: [luxintenebris.news](https://luxintenebris.news)


## Repo structure

```
lux-in-tenebris-pipeline/
├── scripts/          ← Pipeline engine (bash orchestrator + Python helpers)
│   ├── run.sh                  Main orchestrator (bash) — start here
│   ├── cron_wrapper.sh         Cron fire-and-forget launcher
│   ├── core/                   Runs every day, no exceptions
│   │   ├── render.py               HTML renderer from edition.json
│   │   ├── archive_issue.py        Archive previous edition
│   │   └── update_headlines_history.py  Cross-day dedup store
│   ├── content/                 Fetch/generate the day's content
│   │   ├── wire_articles.py        RSS → AI article writer (2-stage)
│   │   ├── youtube_scout.py        YouTube data fetcher
│   │   ├── fetch_trending.py       GitHub/HuggingFace trending via curl fallback
│   │   └── make_making_of.py       Builds the "making-of" replay page
│   ├── inject/                  Post-process the rendered HTML
│   │   ├── inject_podcast_pill.py  Inline audio player for podcast
│   │   └── inject_wire_ticker.py   Scrolling news ticker + modal
│   └── maintenance/              One-off / rescue tools, not called by run.sh
│       └── fix_archive_issue_numbers.py
├── skills/           ← 17 SKILL.md files (LLM agent instructions)
│   ├── orchestrator/            Meta: describes the whole pipeline
│   ├── editor/
│   ├── image-gen/
│   ├── podcast-pill/
│   ├── wire-articles/
│   ├── scout-x/
│   ├── scout-research/
│   ├── scout-official/
│   ├── scout-opensource/
│   ├── scout-tools/
│   ├── scout-funding/
│   ├── scout-hardware/
│   ├── scout-youtube/
│   ├── scout-italia/
│   ├── lux-hotfix/              Meta: live-HTML hotfix without a full re-run
│   ├── lux-status-reports/      Meta: status-update format convention
│   └── lux-image-pitfalls/      Meta: image-gen production-failure notes
├── template/         ← HTML template + CSS + fonts
│   ├── newspaper.html
│   ├── style.css
│   └── fonts/
├── docs/
│   ├── ARCHITETTURA.md
│   └── SETUP.md
└── requirements.txt  ← Python deps for the pure-code scripts
```

## Related repos

- **Deploy (output):** [NTTLuke/luxintenebris-ai-news](https://github.com/NTTLuke/luxintenebris-ai-news) — published HTML/images/podcasts/archive
- **Pipeline (this):** [NTTLuke/lux-in-tenebris-pipeline](https://github.com/NTTLuke/lux-in-tenebris-pipeline) — code, skills, templates

## Running this yourself (Hermes Agent)

Every step that needs judgment is a `SKILL.md`, and every "how do I set this
up" question is answered in [docs/SETUP.md](docs/SETUP.md) — which means the
fastest path is usually to let Hermes read it and do the work:

```bash
git clone git@github.com:NTTLuke/lux-in-tenebris-pipeline.git
cd lux-in-tenebris-pipeline
```

Then, in a Hermes chat:

> Read `docs/SETUP.md` in this repo and set the pipeline up for my profile —
> symlinks, cron job, and tell me what env vars and API keys I still need to
> provide.

That gets you the symlinks and cron job; you'll still need to supply your own
LLM provider (or point `localAIServer` at your own OpenAI-compatible endpoint) and,
optionally, xAI OAuth for images/podcast. None of that is bundled — see
**Prerequisites** in [docs/SETUP.md](docs/SETUP.md) for exactly what's
required vs. optional, and what happens if you skip a piece (short version:
scouts and the editor need an LLM provider to produce anything at all; image
generation and the podcast pill are non-fatal and just skip themselves if xAI
isn't connected).

First run bootstraps itself — there's no manual "seed issue #1" step, the
pipeline reads whatever's live in your deploy repo (nothing, the first time)
and starts numbering from there.

## How it works

Cron triggers `cron_wrapper.sh` → `run.sh`, a bash orchestrator that chains **LLM agents** (each one a `SKILL.md` invoked as `hermes chat -s <skill>`, for anything requiring judgment) and **plain scripts** (for anything mechanical), talking to each other only through JSON files on disk — no step calls another directly:

```
Sync deploy + resolve issue # + archive predecessor  — pure code
  → 9 scouts, ONE AT A TIME                          — LLM agents, gather raw items
  → Editor                                           — LLM agent, curates + assembles edition.json
  → Image generation                                 — LLM agent driving the xAI Grok Imagine tool
  → Render HTML                                      — pure code, deterministic, no LLM
  → Podcast Pill                                     — LLM agent (dialogue) + xAI TTS tool (Castor/Luna voices)
  → Wire articles                                    — pure-code retrieval + 1 LLM call per article
  → Ticker injection                                 — pure code
  → Deploy                                           — pure code (git commit + push to GitHub Pages)
```

Full per-agent detail — exact model, toolset, what it reads and writes — is in [Agents & Responsibilities](docs/ARCHITETTURA.md#agents--responsibilities).

## Key Design Decisions

### Agent / Code Boundary
Every step that needs judgment (what's newsworthy, how to phrase it, what an illustration should depict) is an LLM agent. Every step that's mechanical (templating, file copying, dedup, archiving, git operations) is plain Python/bash with **no LLM in the loop**. This is deliberate: it keeps the unpredictable part small and contained, and makes the predictable part impossible to break via a bad model response — see `render.py`'s own docstring for the canonical statement of this.

### Sequential Scouts, Pinned Provider
All LLM steps run against a single self-hosted inference server (`localAIServer`), pinned explicitly via `PIPELINE_PROVIDER` in `run.sh` — never the Hermes profile default, which is whatever the operator happens to chat on.

Because that server is one machine, scouts run **one at a time**. Each scout is a full multi-turn agent session, and three concurrent sessions saturate the box: across 2026-07-26/27/28, every 3-up phase ran to its timeout ceiling and *zero* scouts completed. Serialised, each scout gets the machine to itself. Wall clock is free here — it's a fire-and-forget 06:30 cron — so the master budget is 4h. See [Scout Concurrency](docs/ARCHITETTURA.md#scout-concurrency--why-sequential).

### Deterministic Rendering
`render.py` never uses an LLM to write HTML. It does pure template substitution from a structured JSON edition. The editor (LLM) decides importance and wording; the renderer lays it out deterministically. The page can never break due to model output.

### 2-Stage Wire Articles
`wire_articles.py` separates LLM calls from retrieval:
- **Stage 1** (pure code): RSS fetch → keyword filter → URL resolution → article fetch → dedup → rank
- **Stage 2** (single LLM call per article): grounded writing from source text only, forbidden from inventing facts

### Graceful Degradation
- Scout failures → empty `[]` fallback JSON, pipeline continues
- Image gen credit exhaustion → auto-skip, logged, retried fresh the next day
- Podcast pill credit exhaustion → auto-skip **independently of image gen**, on its own credit signal — the two don't always fail together (observed: images down, podcast still worked, on both 2026-07-14 and 2026-07-24), so one failing no longer preempts the other
- Wire article failure → skip ticker injection, continue
- Every LLM call wrapped in its own timeout (20 min scouts/editor, 15 min media) → nothing hangs forever
- Master timeout (4h) → kill entire pipeline

### Reference-Scoped Archiving
Each `archive/YYYY-MM-DD/` snapshot is self-contained (own HTML/CSS/fonts/images/podcast) so old issues keep rendering correctly forever, but `archive_issue.py` only copies the images/audio that day's own HTML actually links to — not the whole `images/`/`podcasts/` pool. The deploy-root `images/`/`podcasts/` folders are pruned after every archive run down to whatever the live page still references. This keeps each day's archive size proportional to that day's content instead of to the site's total age.

### Symlink Architecture
The repo is the single source of truth. Hermes accesses code via symlinks:
```
~/.hermes/profiles/<profile>/scripts/v2   →  ~/lux-in-tenebris-pipeline/scripts
~/.hermes/profiles/<profile>/skills/ai-news-v2 → ~/lux-in-tenebris-pipeline/skills
```
Edits committed to this repo are live immediately through the symlink — no restart, no separate publish step. `git commit`/`push` here is for history and backup, not for activation.

See [docs/ARCHITETTURA.md](docs/ARCHITETTURA.md) for the full pipeline map, the agent responsibility table, and known limitations, and [docs/SETUP.md](docs/SETUP.md) for installation instructions.

## Contributing

Opening a PR? See [CONTRIBUTING.md](CONTRIBUTING.md) — what's safe to change, what needs care, and how to use an AI assistant to prepare a change that's actually verifiable without access to the private backend this pipeline runs on.