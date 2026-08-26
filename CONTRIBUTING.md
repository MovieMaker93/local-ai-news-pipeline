# Contributing

This repo is the pipeline that builds Local AI News daily. It runs unattended
every morning, so changes here are production changes the moment they land on
`main`.

## Ground rules

1. **Never change `PIPELINE_PROVIDER` or `PIPELINE_MODEL` in
   `scripts/run.sh` without an explicit human request.** The warning block
   above `PIPELINE_PROVIDER` documents why: upstream, an interactive session
   once silently swapped every provider flag to a paid backend and a full
   edition ran on it before anyone noticed.
2. **Keep the JSON contracts in sync.** `edition.json`'s shape is consumed by
   `render.py`, `inject_wire_ticker.py`, `make_making_of.py`, and
   `update_headlines_history.py`. Change the shape, change all consumers.
3. **A skill's directory name must match its frontmatter `name:`** — `run.sh`
   invokes skills by name (`-s <name>`), resolved from frontmatter. CI checks
   this.
4. **Keep steps isolated.** Steps communicate through JSON files under
   `/tmp/lain/` only. No step calls another directly.
5. **Explain your reasoning, don't just diff it.** The big comment blocks in
   `run.sh` (sequential scouts, timeouts, archive-before-overwrite,
   read-issue-from-live-HTML) each document a real production incident.
   Preserve them when editing nearby code; add a new one when you fix
   something that broke in production.

## Checks

CI runs `python3 .github/scripts/validate_repo.py` on every PR: Python
syntax, bash syntax, sources.md JSON blocks, skill name/dir invariant.
Passing means "nothing a computer can check without secrets is broken" — a
human (or paired AI) still reviews every PR.

## The daily run

`docs/ARCHITETTURA.md` is the map of what runs and in what order. If you
change behavior, update that doc in the same PR.
