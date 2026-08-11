# scripts/

## Entry points

- **`run.sh`** — the orchestrator. Everything starts here; it's what the
  cron actually runs (via `cron_wrapper.sh`). Self-locates its own paths, so
  it works regardless of where the repo is cloned or symlinked — see
  [docs/SETUP.md](../docs/SETUP.md) for the env vars that configure it.
- **`cron_wrapper.sh`** — fire-and-forget launcher (`nohup run.sh &`), exists
  only because the cron system has a 3-minute hard timeout and the pipeline
  itself takes hours.

## Everything else, by role

| Folder | What's in it | Called by `run.sh`? |
|---|---|---|
| `core/` | The mechanical steps that run every single day, no exceptions: rendering, archiving, cross-day dedup. | Yes, every run |
| `content/` | Fetches/generates the day's raw material: RSS, YouTube, trending repos, wire articles, the "making-of" replay page. | Yes, every run |
| `inject/` | Post-processes the already-rendered `index.html` — stitches in the podcast player and the news ticker. | Yes, every run |
| `maintenance/` | Standalone rescue tools for fixing things by hand after an incident. **Never** invoked by `run.sh`. | No — run manually if needed |

`fix_archive_issue_numbers.py` in `maintenance/` is a concrete example: it's
the repair script from a specific 2026-07 incident (wrong issue numbers in
the archive), kept around in case something similar happens again — not
part of the daily mechanism.

See [docs/ARCHITETTURA.md](../docs/ARCHITETTURA.md) for the full pipeline
flow and which steps are LLM agents (`skills/`) vs. plain code (here).
