# Making Your Own Newspaper From This

The engine is topic-agnostic; the local-AI content is not. This file is the
map of which is which.

## What's the reusable engine vs what's local-AI content

**Engine — keep, don't rewrite:**
- `scripts/run.sh`'s mechanics: sequencing, timeouts, deploy ordering, the `run_scout()` helper.
- `scripts/core/`, `scripts/inject/` — template rendering, archiving, cross-day dedup, post-render injection.
- The agent/code boundary and `editor/SKILL.md`'s tiering mechanism (lead / top / sections / quick hits) and JSON contract shape.
- `skills/_shared/sources.md`'s *format* — anchor + fenced JSON block, parsed by regex. Reuse the mechanism, replace the content.

**Local-AI content — replace:**
- Every scout's actual search strategy (inside its own `SKILL.md`).
- `skills/_shared/sources.md`'s actual lists (blog URLs, feeds).
- `editor/SKILL.md`'s section list (`Research & Papers`, `Tools & Runtimes`, etc.) — these are local-AI beats; yours will be different.
- The name — "Local AI News" appears in `template/`, `scripts/content/make_making_of.py`, and the deploy repo. A `grep -ril "local ai news"` finds every spot.

## The actual process

1. **Ask the human what their beats are** before writing anything. 3-5 beats is a reasonable range; this pipeline runs 10 scouts, but that's a choice, not a requirement.
2. **Decide scout count.** To drop a scout: delete its `run_scout()` call in `run.sh`, remove it from the `SCOUT_NAMES` validation list in step 3, delete its `skills/<name>/` directory.
3. **Rewrite `skills/_shared/sources.md`** for the new beats — same anchor format, new content.
4. **Rewrite each scout's `SKILL.md`** — search strategy, what counts as signal, output contract (keep the JSON shape unless you're also changing the editor to match).
5. **Rewrite `editor/SKILL.md`'s section list** to match the new beats.
6. **Decide what to drop.** Wire articles are independent and non-fatal. The image/podcast steps were already removed in this fork.
7. **Rename the branding** — grep for "Local AI News", replace in the template, `make_making_of.py`, and anywhere else it turns up.
8. **Set up the infra** — LLM provider, cron. Follow [docs/SETUP.md](docs/SETUP.md).

## What not to touch regardless of topic

`run.sh`'s deploy ordering, the provider/model pinning pattern (keep the
pin-and-pass-explicitly design), and the editor/render JSON contract (change
its *content* freely, keep every consumer of `edition.json` in sync with
whatever shape you land on).

---

*This fork started from [NTTLuke/lux-in-tenebris-pipeline](https://github.com/NTTLuke/lux-in-tenebris-pipeline) — its FORKING.md guided this very transformation.*
