---
name: local-ai-news-status-reports
description: "Convention for reporting Local AI News pipeline status to Alfonso. TODAY ONLY compact format, no historical comparisons."
---

# Local AI News — Status Report Style (User Preference)

Load this skill when Alfonso asks for a pipeline or scout status update.

## Format Rules

- **TODAY ONLY.** Report *only* the current day's run. Never include a multi-day trend table, historical comparison table, or "last N days" recap unless he *explicitly* asks for it.
- **One compact block.** Scout name + status emoji + item count. No analysis, no commentary beyond what he asks for.
- **Running/live status.** If the pipeline is still in progress, say which scout is currently running. List which are still pending. Do NOT speculate on why it's slow.
- **No editorializing.** Don't flag patterns ("I notice X keeps failing"), suggest actions, or offer to investigate unless he asks. Just the state of today's release.

## Example

```
Today 30 July, Issue #35 — pipeline started 06:30, still running.

Scouts complete:
- Research ✅ 58 items
- Official ✅ 12 items
- OpenSource ❌ empty
- Tools 🔄 in progress (~8 min)
- Hardware ⏳ in queue
- Selfhost ⏳ in queue
```

## When to Load

- Alfonso says "stato della release", "come stanno andando gli scout", "aggiornamento pipeline"
- Any pipeline status question where the context is today's run specifically
