# Lux in Tenebris — Pipeline

Pipeline components for the daily AI news newspaper **LVX IN TENEBRIS**.

Live at: [luxintenebris.news](https://luxintenebris.news)
K3 Edition (The Lens): [luxintenebris.news/k3/](https://luxintenebris.news/k3/)

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
│   ├── inject_version_badge.py DS/K3 version selector badges
│   ├── inject_wire_ticker.py   Scrolling news ticker + modal
│   ├── render.py               HTML renderer from edition.json
│   ├── transform_layout_k3.py  K3 White Edition layout transformation
│   ├── update_headlines_history.py  Cross-day dedup store
│   ├── wire_articles.py        RSS → AI article writer (2-stage)
│   └── youtube_scout.py        YouTube data fetcher
├── skills/           ← 18 SKILL.md files (LLM agent instructions)
│   ├── orchestrator-v2/
│   ├── editor-v2/
│   ├── editor-v2-k3/
│   ├── image-gen-v2/
│   ├── podcast-pill/
│   ├── wire-articles-v2/
│   ├── scout-v2-x/
│   ├── scout-v2-research/
│   ├── scout-v2-official/
│   ├── scout-v2-opensource/
│   ├── scout-v2-tools/
│   ├── scout-v2-funding/
│   ├── scout-v2-hardware/
│   ├── scout-v2-youtube/
│   ├── scout-v2-italia/
│   ├── lux-v2-operations/
│   ├── lux-v2-domain/
│   └── lux-v2-domain-reference/
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

Cron triggers `cron_wrapper.sh` → `run_v2.sh` (bash orchestrator):

```
9 scouts (3+3+1+1+1 phases, parallel within each)
  → Dual-model editor (DeepSeek V4 Flash + Kimi K3)
  → Image generation (Grok Imagine)
  → Render HTML (deterministic, no LLM)
  → Version badges (DS/K3 selector)
  → K3 White Edition layout transform
  → Podcast Pill (Castor/Luna TTS dialogue)
  → Wire articles (RSS → AI, 2-stage pipeline)
  → Scrolling ticker injection
  → Deploy (git commit + push to GitHub Pages)
```

## Key Design Decisions

### Dual-Model Architecture
Since July 2026, the pipeline produces **two editions** per run from the same scout data:
- **DeepSeek V4 Flash** (default, dark broadsheet) → `index.html`
- **Kimi K3** (White Edition "The Lens") → `k3/index.html`

### Deterministic Rendering
`render.py` never uses an LLM to write HTML. It does pure template substitution from a structured JSON edition. The editor (LLM) decides importance and wording; the renderer lays it out deterministically. The page can never break due to model output.

### 2-Stage Wire Articles
`wire_articles.py` separates LLM calls from retrieval:
- **Stage 1** (pure code): RSS fetch → keyword filter → URL resolution → article fetch → dedup → rank
- **Stage 2** (single LLM call per article): grounded writing from source text only, forbidden from inventing facts

### Graceful Degradation
- Scout failures → empty `[]` fallback JSON
- Image gen exhaustion → auto-skip, logged
- Podcast pill failure → skip, continue
- Wire article failure → skip ticker
- Master timeout (90 min) → kill entire pipeline

### Symlink Architecture
The repo is the single source of truth. Hermes accesses code via symlinks:
```
~/.hermes/profiles/luke/scripts/v2   →  ~/lux-in-tenebris-pipeline/scripts
~/.hermes/profiles/luke/skills/ai-news-v2 → ~/lux-in-tenebris-pipeline/skills
```

See [docs/ARCHITETTURA.md](docs/ARCHITETTURA.md) for the full pipeline map and [docs/SETUP.md](docs/SETUP.md) for installation instructions.