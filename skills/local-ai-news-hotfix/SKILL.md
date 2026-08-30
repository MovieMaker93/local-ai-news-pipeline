---
name: local-ai-news-hotfix
description: "Hotfix a published Local AI News edition without re-running the pipeline."
---

# Local AI News — Hotfix a Published Edition (deploy today, no re-run)

Companion to `orchestrator`. Use when Alfonso wants a change on the LIVE
site today (or for tomorrow's release) without bumping the issue number or
triggering a full pipeline run.

## Core rule: NEVER re-render index.html to apply a live change

`render.py` reads edition.json + template and outputs a **BARE page** — it strips
everything the pipeline injected afterwards: the **wire ticker** (`.wt`) and
**section images / interleaved elements**. Re-rendering on top of an
already-published edition silently DESTROYS that content. Confirmed upstream
2026-08-10 (credit edit wiped podcast pill + ticker; restored from backup).
The same trap applies here: `inject_wire_ticker.py` runs post-render.

**Correct hotfix = surgical string replacement** on the live HTML in the deploy dir
(`~/local-ai-news-deploy/`), never regeneration.

## The Devocracy credit lives in TWO places (not one)

- `template/newspaper.html` → drives the home `index.html` (via render.py)
- `scripts/content/make_making_of.py` → drives `making-of.html`, which has its OWN hardcoded
  header and does NOT load newspaper.html

A credit / model-name change must be applied to **BOTH**, or one page keeps the old
string. Do NOT remove the `ivanfioravanti` (Devocracy) mention when editing it.

For tomorrow's release: edit the two SOURCE files above; the cron uses them directly.
For today's live site (already published): edit the two live HTML files in the deploy dir.

## Safe hotfix procedure (live, today)

1. **Back up** the live files first: `cp index.html /tmp/index.html.bak.$(date +%H%M%S)`
   (same for making-of.html).
2. **Surgical replace** the exact string in `index.html` + `making-of.html`. Prefer a
   small python script in `/tmp/` over big inline `perl -i` one-liners — oversized
   inline payloads trip the terminal blocklist.
3. **Verify integrity** of the touched file — the injected content must still be
   present: `class="wt"` / wire-ticker, `images/*.jpg` counts.
4. **Keep `.issue` unchanged** (do not bump for a hotfix).
5. **`git add` ONLY the touched files** (never `git add -A` in the deploy dir — stray
   files can overwrite index.html).
6. Commit + push; GitHub Actions deploys in ~1-2 min.
7. **Verify on the LIVE domain** `https://moviemaker93.github.io/local-ai-news/` —
   grep the rendered credit text.

## Pitfalls

- `git add -A` in deploy dir picks up stray files → check diff before commit.
- This fork deploys to a GitHub Pages **project** URL (`/local-ai-news/`), not a custom
  domain root — verify links use the Pages-relative prefix, not absolute `/`.
