# Lux in Tenebris — Pipeline

Pipeline components for the daily AI news newspaper **LVX IN TENEBRIS**.

Live at: [luxintenebris.news](https://luxintenebris.news)


## Repo structure

```
lux-in-tenebris-pipeline/
├── scripts/          ← Pipeline engine (bash orchestrator + Python helpers)
│   ├── run_v2.sh               Main orchestrator (bash)
│   ├── cron_wrapper.sh         Cron fire-and-forget launcher
│   ├── archive_issue.py        Archive previous edition
│   ├── fetch_trending.py       GitHub/HuggingFace trending via curl fallback
│   ├── fix_archive_issue_numbers.py
│   ├── inject_podcast_pill.py  Inline audio player for podcast
│   ├── inject_wire_ticker.py   Scrolling news ticker + modal
│   ├── render.py               HTML renderer from edition.json
│   ├── update_headlines_history.py  Cross-day dedup store
│   ├── wire_articles.py        RSS → AI article writer (2-stage)
│   └── youtube_scout.py        YouTube data fetcher
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
└── docs/
    ├── ARCHITETTURA.md
    └── SETUP.md
```

## Related repos

- **Deploy (output):** [NTTLuke/luxintenebris-ai-news](https://github.com/NTTLuke/luxintenebris-ai-news) — published HTML/images/podcasts/archive
- **Pipeline (this):** [NTTLuke/lux-in-tenebris-pipeline](https://github.com/NTTLuke/lux-in-tenebris-pipeline) — code, skills, templates

## How it works

Cron triggers `cron_wrapper.sh` → `run_v2.sh`, a bash orchestrator that chains **LLM agents** (each one a `SKILL.md` invoked as `hermes chat -s <skill>`, for anything requiring judgment) and **plain scripts** (for anything mechanical), talking to each other only through JSON files on disk — no step calls another directly:

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
All LLM steps run against a single self-hosted inference server (`localAIServer`), pinned explicitly via `PIPELINE_PROVIDER` in `run_v2.sh` — never the Hermes profile default, which is whatever the operator happens to chat on.

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
~/.hermes/profiles/luke/scripts/v2   →  ~/lux-in-tenebris-pipeline/scripts
~/.hermes/profiles/luke/skills/ai-news-v2 → ~/lux-in-tenebris-pipeline/skills
```
Edits committed to this repo are live immediately through the symlink — no restart, no separate publish step. `git commit`/`push` here is for history and backup, not for activation.

See [docs/ARCHITETTURA.md](docs/ARCHITETTURA.md) for the full pipeline map, the agent responsibility table, and known limitations, and [docs/SETUP.md](docs/SETUP.md) for installation instructions.