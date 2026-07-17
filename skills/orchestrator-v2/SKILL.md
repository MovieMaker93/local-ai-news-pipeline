---
name: orchestrator-v2
description: "Lux in Tenebris V2 production pipeline. Bash orchestrator with fire-and-forget cron, 8 atomic scouts + 1 Python/LLM hybrid, dual-model editor, image-gen, render, podcast pill, wire articles, version badge, deploy to GitHub Pages."
---

# Orchestrator V2 — Production Pipeline

## Purpose
Daily AI news production: 9 scouts → dual-model editor (DS + K3) → image generation → HTML render → version badge → podcast pill → wire articles → deploy to GitHub Pages.

## Architecture — Dual-Model Pipeline

**Core principle:** Cron is a scheduler, not a state manager. Scouts run once; editor, render, wire articles, and badge injection run per-model for each edition.

Since 2026-07-17, the pipeline produces **two editions** per run: DeepSeek (default, `index.html`) and Kimi K3 / The Lens (`k3/index.html`).

```
Cron (08:00, no_agent=true, fire-and-forget)
  ↓
cron_wrapper.sh (nohup bash run_v2.sh &)
  ↓
run_v2.sh (bash orchestrator)
  ↓
Phase 1-5: 9 scouts (once, parallel within phases)
  ↓
── DUAL MODEL BRANCH ──
  │
  ├─ Editor DS (editor-v2, deepseek)  → edition.json
  ├─ Editor K3 (editor-v2-k3, kimi-k3) → edition_k3.json
  │
  ├─ Image-gen (once, shared)
  │
  ├─ Render DS  → index.html
  ├─ Render K3  → k3/index.html
  │
  ├─ Badge DS   → badge inactive (amber)
  ├─ Badge K3   → badge active (ember) + paths fixed to ../
  │
  ├─ Wire DS   → scout_wire_ds.json (deepseek)
  └─ Wire K3   → scout_wire_k3.json (kimi-k3)
  ↓
Podcast Pill (shared, injected into both)
  ↓
Git sync → Archive → Copy → git add → commit → push
```

## Key Scripts

### inject_version_badge.py
- `python3 inject_version_badge.py <input.html> <mode> --output <output.html>`
- Modes: `ds` (links to `k3/`), `k3` (links to `../`, also rewrites paths to `../`)
- Injects inline CSS before `</head>`, badge HTML between dateline `</div>` and devocracy-credit
- Colors: DS = `var(--lux)` amber, K3 = `var(--ember)` hot orange

### wire_articles.py
- `--model`, `--provider` args for per-edition model selection
- Each edition gets its own wire articles written by its respective model

## Per-model components

| Component | DeepSeek | Kimi K3 |
|-----------|----------|---------|
| Editor skill | `editor-v2` | `editor-v2-k3` |
| Model | `deepseek-v4-flash` | `kimi-k3` |
| Edition file | `edition.json` | `edition_k3.json` |
| Output path | `index.html` | `k3/index.html` |
| Badge mode | `ds` (amber, inactive) | `k3` (ember, active, paths fixed to ../) |
| Wire articles | `scout_wire_ds.json` | `scout_wire_k3.json` |
| Wire model | default (deepseek-v4-flash) | `--model kimi-k3 --provider localAIServer` |

## editor-v2-k3 sections (different from standard editor-v2)
- Deep Dives (research + long-form)
- Open Pulse (opensource + tools)
- The Edge (hardware + funding)
- YouTube Signals (video)
- Italia Front (Italian AI)
- Quick hits: 5-7 with brief context

## Pitfalls

1. **Badge injector duplica** — Non eseguire `inject_version_badge.py` due volte sullo stesso file. Rigenera da capo.
2. **K3 subdir paths** — `href="style.css"` → `../style.css`. Anche fonts, images, podcasts. La badge injection in modalità `k3` lo fa automaticamente.
3. **Badge position** — Deve stare TRA la chiusura del dateline (`</div>`) e il devocracy-credit. Regex: `(</div>)(\s*\n\s*<div class="devocracy-credit")` → `\1\n` + badge + `\2`.
4. **Wire articles per-edizione** — DS wire usa deepseek, K3 wire usa kimi-k3. File separati: `scout_wire_ds.json` e `scout_wire_k3.json`.
5. **Image path copy** — Le immagini dalla DS edition vengono copiate nella K3 via Python (step 6b). Match per section title. Se i nomi sezione differiscono, le immagini non vengono copiate.