# Making Your Own Newspaper From This

Written for the AI assistant doing this on someone's behalf, not the human who asked. The human wants a different topic, different sources, maybe a different name — not AI news, not "Lux in Tenebris." This repo is the engine; almost none of the AI-news content is load-bearing to the engine itself. Read this whole file before touching anything.

## What's the reusable engine vs what's AI-news content

**Engine — keep, don't rewrite:**
- `scripts/run.sh`'s mechanics: sequencing, timeouts, credit-exhaustion handling, deploy ordering, the `run_scout()` helper.
- `scripts/core/`, `scripts/inject/` — template rendering, archiving, cross-day dedup, post-render injection. All topic-agnostic.
- The agent/code boundary itself (see [README.md](README.md#agent--code-boundary)) and `editor/SKILL.md`'s tiering mechanism (lead / top / sections / quick hits) and JSON contract shape.
- `skills/_shared/sources.md`'s *format* — anchor + fenced JSON block, parsed by regex. Reuse the mechanism, replace the content.

**AI-news content — replace:**
- Every scout's actual search strategy (inside its own `SKILL.md`) — that's specific to what counts as AI news.
- `skills/_shared/sources.md`'s actual lists (handles, blogs, feeds, channels).
- `editor/SKILL.md`'s section list (`Research & Papers`, `Open Source & Models`, etc.) — these are AI-news beats; yours will be different.
- `image-gen`'s style/lookbook (ink-watercolor "tenebris" aesthetic) and `podcast-pill`'s Castor/Luna characters — cosmetic, keep or replace as the human wants.
- The name itself — "Lux in Tenebris" / "LVX IN TENEBRIS" appears in `template/`, `scripts/content/make_making_of.py`, and the deploy repo. A `grep -ril "lux in tenebris\|lvx in tenebris"` finds every spot.

## The actual process

1. **Ask the human what their beats are** before writing anything — this replaces "AI news" as the newspaper's subject, and everything else follows from it. 3-5 beats is a reasonable range; this pipeline runs 9 AI-news scouts, but that's a choice, not a requirement.
2. **Decide scout count.** You don't need one scout per beat if a beat's sources fit inside another scout's search — but one skill per beat is the pattern this repo uses and it's the easiest to reason about. To drop a scout entirely: delete its `run_scout()` call (or bespoke block) in `run.sh`, remove it from the `SCOUT_NAMES` validation list in step 3, delete its `skills/<name>/` directory.
3. **Rewrite `skills/_shared/sources.md`** for the new beats — same anchor format, new content. Nothing else needs to change for the scouts and scripts that read it to keep working, as long as the anchor keys match what each `SKILL.md` looks for.
4. **Rewrite each scout's `SKILL.md`** — search strategy, what counts as signal, output contract (keep the JSON shape unless you're also changing the editor to match).
5. **Rewrite `editor/SKILL.md`'s section list** to match the new beats, in the order they should appear.
6. **Decide what to drop.** Image generation, the podcast pill, and wire articles are independent, non-fatal features — not core to "produce a daily digest." Dropping one means removing its step in `run.sh` and, optionally, its `skills/` directory. The pipeline still runs without any of them.
7. **Rename the branding** — grep for "Lux in Tenebris" / "LVX IN TENEBRIS", replace in the template, `make_making_of.py`, and anywhere else it turns up. Point the deploy repo at wherever the human actually wants to publish.
8. **Set up the infra** — this repo's own infrastructure (LLM provider, xAI OAuth, cron) is unchanged by any of the above. Follow [docs/SETUP.md](docs/SETUP.md) for that part.

## What not to touch regardless of topic

The same things [CONTRIBUTING.md](CONTRIBUTING.md) flags as needing care apply here too, unchanged: `run.sh`'s deploy ordering, the provider/model pinning pattern (you'll set your own provider, but keep the pin-and-pass-explicitly design — see [Provider Pinning](docs/ARCHITETTURA.md#provider-pinning) for why), and the editor/render JSON contract (change its *content* freely, keep every consumer of `edition.json` in sync with whatever shape you land on).
