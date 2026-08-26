# Local AI News — Pipeline

An AI newspaper about **local AI** — open weights, the tooling that runs them,
the hardware they run on, and the self-hosted stack around them — that
assembles itself once a day and publishes to GitHub Pages.

Fork of [NTTLuke/lux-in-tenebris-pipeline](https://github.com/NTTLuke/lux-in-tenebris-pipeline)
(re-engineered for 6 scouts, no media steps, GitHub Pages project URLs). All
credit for the architecture to the original — read its README for the design
philosophy; the agent/code boundary, the JSON-file isolation, and most of the
scar tissue in the comments come from there.

## How it works

Cron triggers `cron_wrapper.sh` → `run.sh`, a bash orchestrator that chains
**LLM agents** (each one a `SKILL.md`, for anything requiring judgment) and
**plain scripts** (for anything mechanical), talking to each other only
through JSON files on disk:

```
Sync deploy + resolve issue # + archive predecessor  — pure code
  → 6 scouts, ONE AT A TIME                          — LLM agents, gather raw items
  → Editor                                           — LLM agent, curates + assembles edition.json
  → Render HTML                                      — pure code, deterministic, no LLM
  → Wire articles                                    — pure-code retrieval + 1 LLM call per article
  → Ticker injection + making-of page                — pure code
  → Deploy                                           — pure code (git commit + push to GitHub Pages)
```

Every step that needs judgment (what's newsworthy, how to phrase it) is an
LLM agent. Every step that's mechanical (templating, dedup, archiving, git
operations) is plain Python/bash with no LLM in the loop — deliberately, so
the unpredictable part stays small and contained and the predictable part
can't break on a bad model response.

All inference runs on a self-hosted DGX Spark via a LiteLLM proxy,
configured as the `spark` custom provider in the Hermes profile. The editor
is the only FATAL step; wire articles, ticker, and making-of are non-fatal.

## The scouts

| Scout | Beat |
|---|---|
| research | arXiv/HF papers with local relevance: quantization, distillation, small models, efficient inference |
| official | blogs of labs that ship open-weight models (Qwen, Mistral, Meta, Google…) |
| opensource | new open-weight releases + GitHub/HF trending (AI-filtered) |
| tools | runtimes & tooling: Ollama, llama.cpp, vLLM, Open WebUI, MCP… |
| hardware | consumer GPUs, VRAM, NPUs, Apple silicon, edge devices |
| selfhost | self-hosted stack: Open WebUI, n8n, Home Assistant, r/LocalLLaMA |

## Repo structure

```
local-ai-news-pipeline/
├── scripts/          ← Pipeline engine (bash orchestrator + Python helpers)
│   ├── run.sh                  Main orchestrator (bash) — start here
│   ├── cron_wrapper.sh         Cron fire-and-forget launcher
│   ├── core/                   Runs every day, no exceptions
│   │   ├── render.py               HTML renderer from edition.json
│   │   ├── archive_issue.py        Archive previous edition
│   │   └── update_headlines_history.py  Cross-day dedup store
│   ├── content/                 Fetch/generate the day's content
│   │   ├── wire_articles.py        RSS → AI article writer (2-stage)
│   │   ├── fetch_trending.py       GitHub/HuggingFace trending via curl fallback
│   │   └── make_making_of.py       Builds the "making-of" replay page
│   ├── inject/                  Post-process the rendered HTML
│   │   └── inject_wire_ticker.py   Scrolling news ticker + modal
│   └── maintenance/              One-off / rescue tools, not called by run.sh
├── skills/           ← 8 SKILL.md files (LLM agent instructions)
│   ├── orchestrator/            Meta: describes the whole pipeline
│   ├── editor/
│   ├── scout-research/ … scout-selfhost/
│   └── _shared/sources.md       Single source of truth for fixed source lists
├── template/         ← HTML template + CSS + fonts
├── docs/             ← SETUP.md, ARCHITETTURA.md
└── requirements.txt  ← Python deps (optional: trafilatura)
```

## Related repos

* **Deploy (output):** [MovieMaker93/local-ai-news](https://github.com/MovieMaker93/local-ai-news) — published HTML/fonts/archive
* **Pipeline (this):** code, skills, templates

## Warning for AI assistants

One rule that matters more than any single file: **never change
`PIPELINE_PROVIDER` or `PIPELINE_MODEL` in `scripts/run.sh` without the human
explicitly asking for it, in this exact conversation, for this exact
reason.** Read the warning block directly above `PIPELINE_PROVIDER` in that
file — it documents a real incident where an interactive session silently
moved a production pipeline to a paid backend.
