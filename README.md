# Lux in Tenebris — Pipeline

Pipeline components for the daily AI news newspaper **LVX IN TENEBRIS**.

## Repo structure

```
lux-in-tenebris-pipeline/
├── scripts/          ← Pipeline engine (bash orchestrator + Python helpers)
│   ├── run_v2.sh           Main orchestrator
│   ├── cron_wrapper.sh     Cron fire-and-forget launcher
│   ├── archive_issue.py    Archive previous edition
│   ├── inject_podcast_pill.py
│   ├── inject_wire_ticker.py
│   ├── update_headlines_history.py
│   ├── wire_articles.py    RSS → AI article writer
│   ├── youtube_scout.py    YouTube data fetcher
│   └── render.py           HTML renderer from edition.json
├── skills/           ← 13 SKILL.md (LLM agent instructions)
│   ├── orchestrator-v2/
│   ├── editor-v2/
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
│   └── scout-v2-youtube/
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

Cron triggers `cron_wrapper.sh` → `run_v2.sh`:

```
8 scouts (3+3+1+1 batches) → Editor → Image gen → Render → Podcast Pill
→ Wire articles → Inject ticker → Deploy (git push to deploy repo)
```

See [docs/ARCHITETTURA.md](docs/ARCHITETTURA.md) for the full pipeline map.