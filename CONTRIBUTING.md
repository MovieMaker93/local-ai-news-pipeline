# Contributing

Written for the AI assistant preparing this change, not the human who asked for it. If that's you, read this whole file before writing a diff.

This pipeline runs unattended every morning and pushes straight to a live site. There's no staging environment, and you don't have the private LLM backend or xAI keys it runs on — you can verify a code change actually works; you can only *reason about* whether a skill/prompt change will. Say which kind of confidence you have in the PR. Don't imply you tested something you couldn't run.

## Before you write anything

Read [docs/ARCHITETTURA.md](docs/ARCHITETTURA.md) — every file the daily run touches, in order, with what each reads and writes. Find the file you're about to change in that table and check what's upstream and downstream of it before proposing a diff. That's the actual point of this file: don't guess blast radius, look it up.

## Safe to change on your own judgment

- `skills/_shared/sources.md` — add/remove a handle, blog, or feed in an existing list.
- A scout's search strategy, inside its own `SKILL.md` — affects only that scout's output; the editor already treats all nine as independent, fallback-to-`[]` inputs.
- `skills/image-gen/references/metaphor-lookbook.md` — purely additive.
- `docs/`, comments, this file.

## Explain your reasoning instead of just diffing it

- **`scripts/run.sh`**, especially `PIPELINE_PROVIDER` / `PIPELINE_MODEL` / the timeout constants. Read the warning block directly above `PIPELINE_PROVIDER` before touching it — an interactive session once changed it "while fixing something unrelated" and a day's edition ran on the wrong backend before anyone noticed. **Never touch this without the human explicitly asking, in this exact conversation, for this exact reason.**
- **`editor/SKILL.md`'s output shape** (`edition.json`) — `render.py`, `image-gen`, `podcast-pill`, and `make_making_of.py` all depend on its exact fields. Check every consumer before changing the shape; nothing catches a mismatch between two files that each parse fine alone.
- **`render.py`'s template contract** — same reasoning, coupled to `template/newspaper.html`.
- **The agent/code boundary itself** — see [Agent / Code Boundary](README.md#agent--code-boundary). Moving judgment into code, or code into a prompt, is an architecture decision, not a diff.

If you're not sure which category something falls into, say so in the PR instead of guessing.

## Before you open the PR

```bash
python3 .github/scripts/validate_repo.py
```

Paste the output into the PR. It checks: every changed `.py`/`.sh` parses, `sources.md`'s JSON blocks are valid, every skill's frontmatter `name:` matches its directory (this one breaks things at runtime — `run.sh` invokes skills by that name). A pass means none of that is broken. It is not a claim that the change is safe.

If you changed `sources.md`, confirm the anchor format matches existing entries exactly — `<!-- sources:key:field -->` immediately followed by a fenced ` ```json ` block. The loaders in `youtube_scout.py` / `wire_articles.py` parse this with a regex, not a JSON parser.

## PR description

Three things: what changed and why, what you verified, what you couldn't verify. Name the last one plainly for any skill/prompt change — there's no way around it, and "this should work, based on X, but I have no way to run it against the real pipeline" is a genuinely useful sentence here.
