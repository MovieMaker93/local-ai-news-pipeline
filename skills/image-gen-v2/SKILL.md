---
name: image-gen-v2
description: "V2 image generator. Creates ink/watercolor editorial illustrations for lead + sections. xAI Grok Imagine backend. Art direction: metaphor-driven, editorial illustration style (New Yorker cover logic), NOT literal/iconic."
---

# Image Gen V2 — Editorial Illustration Engine

## When to use
Called by orchestrator-v2 AFTER editor-v2 writes `/tmp/v2/edition.json`. Generates illustrations for the lead story and one per non-empty section.

## PHILOSOPHY — this is critical

These are **editorial illustrations**, NOT visual descriptions of the article content. Think *New Yorker* cover logic, not stock photo logic.

**WRONG** (literal/iconic — AVOID):
- "A stylized computer chip with neural network pathways"
- "A humanoid robot silhouette in a thoughtful pose"  
- "Abstract buildings with dollar signs morphing into circuits"
- "Three AI model icons orbiting a central point"

**RIGHT** (metaphorical/lateral — AIM FOR):
- "An astronomer peers through a brass telescope at a sky full of opening parentheses"
- "A single candle on a vast stone balcony, the only warm light in a cold city of towers"
- "A flock of origami cranes emerging from the pages of an open book, some still half-folded"
- "A watchmaker's hands assembling a gear train from translucent soap bubbles"

The image should make the reader pause and think "what does this mean?" — then realize it means everything about the story. The leap from image to idea is where the art lives.

## Image style (MANDATORY — always include this base)

```
Hand-painted watercolor tattoo style with hand-drawn ink outlines, infused with subtle street art urban energy.
Fluid spontaneous ink contour lines (not rigid or mechanical) with watercolor washes bleeding naturally.
Subtle street art texturing: light spray paint grain, occasional paint drips, soft splatter accents — but refined and elegant, not aggressive.
Multiple watercolor colors visible: deep blues, warm ambers, burnt sienna, muted greens, soft purples, ochres. Rich color palette — diverse hues blending and bleeding.
Composition fills 40-60% of space — balanced, not mostly empty.
Handmade aesthetic: visible brush strokes, imperfect organic ink lines, color transitions, urban texture overlays.
Think: watercolor tattoo meets Mr Brainwash light touch — colorful, raw, sophisticated, gallery-ready.
No digital polish, no photorealism, no 3D rendering.

AGED PAPER / SEPIA OVERLAY (CRITICAL — this defines the "tenebris" identity):
The overall image MUST feel like an antique artifact discovered in an old archive or manuscript.
Aged parchment texture subtly visible beneath the ink and watercolor — think foxed paper from the 1700s, warm ivory turning to ochre at the edges.
Soft sepia tonality layering the entire piece: shadows lean warm-brown rather than pure black.
Vignette darkening at corners and edges, as if the paper has darkened with age and handling.
Faint coffee-stain or foxing marks (tiny age spots) can appear in non-critical areas for authenticity.
The colors should feel muted and time-worn — not fresh and saturated, as if the illustration has been aging in a leather-bound book for centuries.
Overall mood: an ancient manuscript illustration reinterpreted through modern ink art — the bridge between old-world craftsmanship and contemporary street art sensibility.
```

Then append ONE of the metaphor prompts below. Rotate — never use the same approach twice in one run.

## THE APPROACH ROTATOR — pick one per image

Rotate through these. Each image in a run should use a DIFFERENT approach.

### A. Synecdoche — the tiny thing that holds the whole story
One hyper-specific, oddly mundane object that crystallizes the entire piece.
**Prompt pattern:** "A single [unusual object] on [unexpected surface/background], rendered as if studied by a 19th-century naturalist. The object contains within it, hinted at but not literal, the idea of [core concept]."
**Example for GPT-5.6 gated launch:** "A heavy brass keyhole plate mounted on a door made of cloud, rendered as a naturalist's specimen study. Only one tiny key exists. The surrounding paper is empty except for a small scale bar and a handwritten Latin label."

### B. Anachronism — old world meets new concept
A historical scene or setting where the anachronistic element is the AI concept, presented as completely normal.
**Prompt pattern:** "A [historical scene/era] where [AI concept] exists as a natural element, treated with the visual language of [period art style]. Figures behave as if this is entirely ordinary."
**Example for robotics:** "A Renaissance workshop where a humanoid figure is being fitted for armor, but its joints are visible ball-and-socket mechanisms. The artisan examines it with a calm professional expression, as if this were a Tuesday."

### C. Scale disorientation — the wrong-sized subject
Something enormous rendered as tiny, or something microscopic rendered as monumental.
**Prompt pattern:** "A [normally huge concept] rendered impossibly small in a [vast empty space] / A [tiny thing] rendered as a [monumental structure] filling the frame."
**Example for funding:** "A tiny seedling growing from a crack in an enormous stone cathedral floor, with a single drop of water falling from the vaulted ceiling above onto its leaf — the scale of the building makes the seedling feel both insignificant and profoundly important."

### D. Impossible object — the thing that shouldn't exist
A hybrid creature, structure, or scene that combines two categories that don't belong together.
**Prompt pattern:** "A [creature/object] made entirely of [unexpected material] in the act of [unexpected behavior]. No caption, no label, no explanation."
**Example for open-source models:** "A vast library whose books are all made of stained glass, light streaming through them casting colored patterns on the floor. A figure with no visible face stands reading one by holding it up to the window."

### E. Negative space / absence — what's NOT there
The illustration is about what's missing, implied, or about to happen.
**Prompt pattern:** "An otherwise [ordinary scene] with a conspicuous [absence/implied event]. Only ink outlines suggested, with watercolor suggesting the ghost of what was or will be."
**Example for AI safety/METR cheating findings:** "A classroom of empty desks, each with a perfectly sharpened pencil and a closed exam booklet. One desk has its booklet open and a small smear of wet ink on the page, still drying. No figures anywhere."

### F. Allegorical bestiary — the creature that represents the idea
An animal, plant, or organism that embodies the concept.
**Prompt pattern:** "A naturalist's illustration of [imaginary organism] whose anatomy encodes [concept]. Rendered with the clinical precision of an Audubon plate, but the subject is entirely invented."
**Example for multi-agent orchestration:** "Audubon-style plate of a creature with seven heads, each a different size and posture, all facing inward toward a small central light source. Tentacles extend from the base connecting to scattered objects in the margins. Ink wash with muted ochre and sienna watercolor."

## Aspect ratios
- Lead: `landscape` (16:9)
- Section hero: `landscape` (standard landscape)

## Process

1. Read `/tmp/v2/edition.json`.
2. For each image target (lead + each non-empty section):
   a. **Pick ONE** approach from the rotator (A-F). Each image in the same run MUST use a different approach.
   b. **Extract the core idea** of the article — NOT the subject, the IDEALITY (e.g., for "OpenAI launches restricted model" → the idea is *access*, *gatekeeping*, *scarcity of intelligence*).
   c. Build prompt = **style base** + **chosen approach pattern** + **specific details** tied to the article's ideality. Balanced composition (40-60% negative space). Multiple watercolor colors. Light street art texture (spray grain, drips, splatter) — refined, not aggressive.
   d. **CRITICAL**: Include ink outline contours (handmade, organic). Multiple watercolor hues. Light street art urban texturing (spray paint grain, subtle drips/splatter). Refined and elegant — gallery-ready.
   e. Call `image_generate` with the appropriate aspect_ratio.
   f. Copy to `/tmp/v2/images/` with deterministic name:
      ```bash
      cp "<tool-path>" /tmp/v2/images/lead_<date_iso>.jpg
      cp "<tool-path>" /tmp/v2/images/section_<slug>_<date_iso>.jpg
      ```
      Slug = lowercase hyphenated section title.
   g. Update edition.json — add `"image": "images/<filename>"` to lead or to first item in each section.

## Anti-patterns (NEVER do these)

- NO generic neural network visualizations (nodes/edges/graphs)
- NO robot heads, glowing brains, matrix code, circuit boards
- NO dollar signs, bar charts, growth arrows
- NO "AI" text or acronyms anywhere
- NO photorealistic faces
- NO 3D rendering look
- NO stock photo compositions
- NO literal translations of the headline into visual form
- NO same approach twice in one run
- NO monochromatic watercolor — use multiple distinct colors (blues, ambers, greens, purples, etc.)
- NO mostly empty composition — aim for 40-60% negative space, not 80%+
- NO rigid/mechanical ink lines — keep them organic, handmade, imperfect
- NO aggressive street art (heavy spray paint, graffiti tags, chaotic splatter) — keep it refined and gallery-ready
- NO complex scenes, busy textures, or patterns

## Fallback on failure
If `image_generate` errors for any item, OMIT the `image` field and continue. The newspaper never fails for a missing illustration.

## Lookbook (reference)
See `references/metaphor-lookbook.md` for:
- Anti-pattern catalog (literal AI clichés to avoid)
- Curated ideality → metaphor mappings from past runs
- Extended examples for each of the 6 approaches
- The ideality-extraction rule (always abstract the idea BEFORE choosing the image)

## Layout rule
Images render as **full-width banners ABOVE** the section's grid, NOT inside individual column items. One hero image per section.

## Toolset requirement (CRITICAL for cron/orchestrator)

When called as `hermes chat -q` from orchestrator-v2 or from a cron-triggered pipeline, the invocation MUST include **`terminal`** in the toolset alongside `file` and `image_gen`:

```bash
hermes chat -q "..." --profile luke -s image-gen-v2 -t file,image_gen,terminal -Q --yolo
```

**Why this matters:** `image_generate` returns a path inside the Hermes cache (e.g. `/home/nttluke/.hermes/profiles/luke/cache/images/xai_grok-*.jpg`). To copy it to `/tmp/v2/images/lead_<date>.jpg`, the agent needs `terminal` access. Without it, the agent cannot run `cp` — it will write a help script asking someone else to copy the files, and the images will be missing from the output. This happened in the 2026-06-28 test run: 5 images were generated correctly but never made it to `/tmp/v2/images/` because `terminal` was absent from the toolset.

**Rule:** any orchestration that calls image-gen-v2 outside interactive chat (bash orchestrator, cron, pipeline) must pass `-t file,image_gen,terminal` — NOT `-t file,image_gen`.
