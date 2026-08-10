---
name: lux-status-reports
description: "Convention for reporting Lux V2 pipeline status to Luke. TODAY ONLY compact format, no historical comparisons."
---

# Lux V2 — Status Report Style (User Preference)

Load this skill when Luke asks for a pipeline or scout status update.

## Format Rules

- **TODAY ONLY.** Report *only* the current day's run. Never include a multi-day trend table, historical comparison table, or "last N days" recap unless he *explicitly* asks for it.
- **One compact block.** Scout name + status emoji + item count. No analysis, no commentary beyond what he asks for.
- **Running/live status.** If the pipeline is still in progress, say which scout is currently running. List which are still pending. Do NOT speculate on why it's slow.
- **No editorializing.** Don't flag patterns ("I notice X keeps failing"), suggest actions, or offer to investigate unless he asks. Just the state of today's release.

## Example

```
Today 30 Luglio, Issue #35 — pipeline partita 06:30, ancora in esecuzione.

Scout completati:
- X/Twitter ✅ 14 items
- Research ✅ 58 items
- Official ❌ vuoto
- Funding 🔄 in corso (~8 min)
- Hardware ⏳ in coda
- ...
```

## When to Load

- Luke says "come stanno andando gli scout", "stato della release", "aggiornamento pipeline"
- Any pipeline status question where the context is today's run specifically