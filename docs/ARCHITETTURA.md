# Architettura — Lux in Tenebris V2 Pipeline

## Panoramica

Pipeline quotidiana che produce un giornale AI in stile dark broadsheet.
Cron → wrapper → bash orchestrator → 8 scouts + wire → editor → immagini
→ render HTML → podcast → deploy.

## Diagramma flusso

```
Cron (07:00, no_agent=true)
  │
  ▼
cron_wrapper.sh (nohup → run_v2.sh &)
  │
  ▼
run_v2.sh
  │
  ├─ Step 0:  Cleanup /tmp/v2/
  ├─ Step 1:  Metadata (date window, issue #)
  │
  ├─ Step 2:  Scouts (4 fasi parallele)
  │   ├─ Phase 1: X, Research, Official        (3 in parallelo)
  │   ├─ Phase 2: OpenSource, Tools, Funding    (3 in parallelo)
  │   ├─ Phase 3: Hardware                      (1)
  │   └─ Phase 4: YouTube (Python + LLM scout)  (1 ibrido)
  │
  ├─ Step 3:  Validate 8 scout JSON
  ├─ Step 4:  Editor → edition.json
  ├─ Step 5:  Image gen (Grok Imagine)          [non-fatal]
  ├─ Step 6:  Render → index.html
  ├─ Step 7:  Podcast Pill (Castor/Luna)        [non-fatal]
  ├─ Step 8:  Wire Articles (RSS → AI)          [non-fatal]
  ├─ Step 9:  Inject Wire Ticker in HTML
  │
  └─ Step 10: Deploy
      ├─ git fetch + reset --hard
      ├─ archive_issue.py (salva edizione precedente)
      ├─ Copia nuovi files
      ├─ git add → commit → push
      └─ Report finale
```

## Path critici

| Path | Descrizione |
|------|-------------|
| `~/.hermes/profiles/luke/scripts/v2/` | Script pipeline (bash + Python) |
| `/tmp/v2/` | Workdir temporaneo (scout JSON, immagini, output) |
| `~/ai-news-deploy/` | Deploy repo (output pubblicato) |
| `~/.hermes/profiles/luke/skills/ai-news-v2/` | 13 SKILL.md (istruzioni LLM) |

## Modelli

| Step | Modello | Provider |
|------|---------|----------|
| Scout (x, research, official, opensource, tools, funding, hardware) | default profilo | default profilo |
| Scout YouTube | deepseek/deepseek-v4-flash | openrouter |
| Editor | default profilo | default profilo |
| Image gen (orchestratore) | default profilo | default profilo |
| Image gen (generazione) | grok-imagine-image | xAI (Grok) |
| Wire articles | deepseek/deepseek-v4-flash | openrouter |
| Podcast pill | default profilo | default profilo |

## Non-fatal steps

I passi marcati `[non-fatal]` usano `|| echo "..."` — se falliscono, la pipeline continua.

## Dedup cross-day

L'editor legge `headlines_history.json` (salvato nel deploy repo) per evitare titoli
già pubblicati nei giorni precedenti.

## Cron

- **Pipeline:** `29fa53d809c4` — 07:00 daily, no_agent=true
- **Watchdog:** `369c43cef23d` — 07:45 daily, verifica deploy riuscito