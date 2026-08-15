# Contributing

This repo runs unattended, every day, at 06:30, and publishes whatever
`main` produces to a live site. There's no staging environment and no way
for a contributor to run the pipeline end to end — the LLM backend and the
xAI keys are private. That shapes everything below: the goal isn't a long
checklist for its own sake, it's giving you (and whatever AI assistant
you're pairing with) enough of the real picture to make a change that's
actually safe to merge, and to be honest in the PR about what could and
couldn't be verified before it goes live.

Passing CI (`.github/workflows/validate.yml`) means your change didn't
break anything a computer can check without secrets — syntax, JSON
validity, a skill's name matching its own directory. It is not a claim
that the change is safe. Read on for the part CI can't do.

## Read this first

[docs/ARCHITETTURA.md](docs/ARCHITETTURA.md) has the full flow — every file
the daily run touches, in the order it touches them, and what each one
reads and writes. If you're about to change something, find it in that
table first and check what's upstream and downstream of it. Two sentences
of that table will tell you more about blast radius than reading the code.

The one idea that explains most of this repo's structure: every step is
either an **LLM agent** (`skills/*/SKILL.md`, judgment — what matters, how
to phrase it) or **plain code** (`scripts/`, deterministic, no model in the
loop). Code is testable in the normal way. Skills are prompts — a bad
change to one doesn't fail loudly, it just quietly produces worse output in
production for a day, with nothing to catch it before that happens. Keep
that distinction in mind for everything below.

## Safe to change with normal care

These have a contained blast radius — a mistake here degrades one thing,
not the whole run:

- **`skills/_shared/sources.md`** — adding/removing a handle, blog, or feed
  in an existing list. Worst case is a dead feed the relevant scout
  non-fatally skips, or a duplicate the editor's cross-day dedup already
  catches.
- **A single scout's search strategy**, inside its own `SKILL.md` (e.g.
  tightening `scout-hardware`'s query wording). Affects only that scout's
  output, which the editor already treats as one of nine independent,
  fallback-to-`[]` inputs.
- **`image-gen`'s lookbook** (`skills/image-gen/references/metaphor-lookbook.md`)
  — purely additive creative reference.
- **Documentation** — `docs/`, `scripts/README.md`, comments, this file.

## Needs real care — explain your reasoning in the PR, don't just diff it

These have a blast radius of "the whole rest of the pipeline," or are tied
to a documented past incident:

- **`scripts/run.sh`** — especially `PIPELINE_PROVIDER`, `PIPELINE_MODEL`,
  and the timeout constants. The provider pin exists because an interactive
  session once rewrote it "while fixing something unrelated" and a day's
  edition ran on the wrong, metered backend before anyone noticed — see the
  warning block directly above `PIPELINE_PROVIDER` in the file. Also: the
  deploy step ordering (git reset / add / commit) has bitten this pipeline
  before in ways that silently dropped data; if you're touching step
  9-11, read [Issue Numbering & Archiving](docs/ARCHITETTURA.md#issue-numbering--archiving)
  first.
- **`editor/SKILL.md`'s output contract** (`edition.json`'s shape) — every
  downstream step (`render.py`, `image-gen`, `podcast-pill`,
  `make_making_of.py`) depends on those exact field names and nesting.
  Changing the shape without checking every consumer breaks the rest of
  the run silently — nothing in CI catches a JSON shape mismatch between
  two files that both parse fine on their own.
- **`render.py`'s template contract** — what placeholders it expects in
  `template/newspaper.html`. Same reasoning: tightly coupled, not enforced
  by anything automatic.
- **The code/agent boundary itself** — turning a currently-deterministic
  script into something that calls an LLM, or vice versa. That split is
  the core design decision of this pipeline (see
  [Agent / Code Boundary](README.md#agent--code-boundary)); changing it is
  an architecture discussion, not a diff.

If you're not sure which category something falls into, say so in the PR
instead of guessing — "I think this is safe because X, but I couldn't
verify Y" is a genuinely useful sentence here.

## Reasoning about a skill change you can't run

You don't have the private backend, so you can't watch a scout actually
run against your prompt change. What you *can* do:

1. **Re-read the skill's own "Output contract" section** and confirm your
   change doesn't alter the JSON shape it promises downstream.
2. **Check the skill's "Pitfalls" / "🔴" sections** before touching related
   logic — most of them exist because something broke in production once;
   don't reintroduce a fixed bug by "simplifying" the workaround.
3. **Grep for who reads the file this skill writes.** `docs/ARCHITETTURA.md`'s
   table has this, but a quick `grep -rn scout_x.json` finds it directly.
4. **Prefer additive changes** (a new query pass, a new fallback) over
   rewriting existing wording that survived a past incident — if it's
   oddly specific, it's probably specific for a reason that's documented
   two lines above it.

## Using an AI assistant to prepare a PR

This is the intended way to contribute here, and it's worth doing
deliberately rather than just pasting a diff request at it:

1. **Give it this file and `docs/ARCHITETTURA.md` before it writes anything.**
   Don't let it infer the architecture from a fragment of one script — the
   agent/code boundary and the file-dependency chain aren't obvious from
   any single file in isolation.
2. **Ask it to identify blast radius before proposing a diff**: what else
   reads or writes the file(s) it's about to change, and does the change
   preserve every contract those consumers rely on.
3. **Run the verification checklist below and paste the output into the
   PR** — don't just claim it passes.
4. **Have it write the PR description honestly**, including what it
   *couldn't* verify (almost always true for skill changes) rather than
   a confident summary that implies it tested something it didn't.

## Verification checklist

Run before opening a PR — the same checks CI runs, plus the ones that need
a human/AI judgment call:

```bash
python3 .github/scripts/validate_repo.py
```

That covers: every changed `.py` parses, every changed `.sh` parses,
`skills/_shared/sources.md`'s JSON blocks are valid, and every skill's
frontmatter `name:` still matches its directory (this one actually breaks
things at runtime — `run.sh` invokes skills by that name).

Beyond what the script checks:

- [ ] If you changed a skill's output shape, checked every file that reads
      its output for a matching update.
- [ ] If you changed `run.sh`, re-read the comment block above whatever
      you touched — most of the constants and ordering in that file exist
      because of a specific past incident, documented right there.
- [ ] If you added a source to `sources.md`, confirmed the anchor format
      (`<!-- sources:key:field -->` immediately followed by a fenced
      ` ```json ` block) matches the existing entries exactly — the loaders
      in `youtube_scout.py` / `wire_articles.py` parse this with a regex,
      not a JSON parser, so the surrounding markdown has to match.

## PR description

Short is fine. Cover:

- **What changed and why** — one or two sentences.
- **What you verified** — the checklist above, plus anything specific to
  this change.
- **What you couldn't verify** — say it plainly if it's a skill/prompt
  change; there's no shame in "this should work, based on X, but I have no
  way to run it against the real pipeline."
