# Local AI News — Source Inventory

Single file, single source of truth: the *why* (which sources, and what to add
next) sits next to the *what* (the actual lists). Each scout's fixed list —
URLs, feeds — lives in a fenced `json` block right under a
`<!-- sources:... -->` anchor comment. Edit the list in place here; nothing
else needs touching.

The `wire_articles.py` parses this file directly (find the anchor, read the JSON
block under it — see the script's `SOURCES_FILE` loader for the exact regex).
The `scout-official` skill reads it with `read_file` the same way a human
would: find its section, use the list in the `json` block.
The `scout-research` skill reads its research-blog list here the same way.

---

## Scout Official Blogs (`scout-official`)
**Scrapes the blogs of the labs that ship open-weight models directly.**
Release notes and model announcements only (high signal).

<!-- sources:scout-official:blogs -->
```json
[
  "https://huggingface.co/blog",
  "https://qwenlm.github.io/blog/",
  "https://www.mistral.ai/news/",
  "https://ai.meta.com/blog/",
  "https://blog.google/technology/ai/",
  "https://deepmind.google/discover/blog/"
]
```

**Possible expansions:**
```
https://www.anthropic.com/news
https://openai.com/blog
https://x.ai/news
https://cohere.com/blog
https://allenai.org/blog
https://stability.ai/blog
```

---

## Wire Articles (`wire-articles`)
**Direct RSS feeds** — deterministic, no LLM for stage 1. General tech feeds;
the script's keyword filter keeps only AI-relevant items.

<!-- sources:wire-articles:feeds -->
```json
[
  "https://feeds.arstechnica.com/arstechnica/index",
  "https://techcrunch.com/feed/",
  "https://www.theverge.com/rss/index.xml",
  "https://www.wired.com/feed/rss"
]
```

---

## Research Blogs (`scout-research`)
**First-party research blogs** — company/team research posts on local-AI-relevant
topics (quantization, KV cache, LoRA, distillation, efficient inference).
Fetched daily by the research scout; posting cadence is low (most days nothing
in-window, which is fine).

<!-- sources:scout-research:blogs -->
```json
[
  "https://www.baseten.co/research/"
]
```

**Possible expansions:**
```
https://blog.vllm.ai
https://huggingface.co/blog (already covered by scout-official)
```

---

## Scout X (`scout-x`)
**Searches X/Twitter** with predefined queries against a fixed set of handles.

<!-- sources:scout-x:handles -->
```json
[
  "OpenAI", "AnthropicAI", "GoogleDeepMind", "xai", "NousResearch",
  "sama", "karpathy", "huggingface", "DeepLearningAI", "ylecun",
  "simonw", "swyx", "_philschmid", "omarsar0", "_akhaliq", "lmsysorg"
]
```

**Possible expansions:**
- Companies: `@Cohere`, `@Replit`, `@StabilityAI`, `@Midjourney`, `@Cursor_ai`, `@GitHubCopilot`
- Academics: `@StanfordHAI`, `@MIT_AI`, `@erichorvitz`, `@demishassabis`, `@andrewyng`
- Media: `@TechCrunch`, `@TheVerge`, `@WIRED`, `@MIT_TechnologyReview`
- Open source: `@ollama`, `@LocalLLaMA`

---

## Scout Italia (`scout-italia`)
**RSS feeds + web search** for Italian AI startups/funding/community.

<!-- sources:scout-italia:feeds -->
```json
[
  "https://www.ai4business.it/feed/",
  "https://www.latechmadeinitaly.com/"
]
```

The rest of the collection (web/x_search for specific startups, funding, spin-offs) is query strategy, not in this file.

---

## YouTube Scout (`scout-youtube`)
**Hybrid:** Python script (`youtube_scout.py`) fetches videos via RSS + LLM writes articles. For selection methodology and frequency criteria, see [`scout-youtube/references/channels.md`](../scout-youtube/references/channels.md) — this section holds only the current list.

<!-- sources:scout-youtube:channels -->
```json
[
  {"id": "UCKelCK4ZaO6HeEI1KQjqzWA", "name": "The AI Daily Brief"},
  {"id": "UCrM7B7SL_g1edFOnmj-SDKg", "name": "Bloomberg Technology"},
  {"id": "UCbRP3c757lWg9M-U7TyEkXA", "name": "Theo - t3.gg"},
  {"id": "UChpleBmo18P08aKCIgti38g", "name": "Matt Wolfe"},
  {"id": "UCbfYPyITQ-7l4upoX8nvctg", "name": "Two Minute Papers"},
  {"id": "UC1yNl2E66ZzKApQdRuTQ4tw", "name": "Sabine Hossenfelder"},
  {"id": "UCsBjURrPoezykLs9EqgamOA", "name": "Fireship"},
  {"id": "UCNJ1Ymd5yFuUPtn21xtRbbw", "name": "AI Explained"},
  {"id": "UCmeU2DYiVy80wMBGZzEWnbw", "name": "AI Tool Report"},
  {"id": "UC5l7RouTQ60oUjLjt1Nh-UQ", "name": "Beyond AI News"}
]
```

**Possible expansions:**
```
Yannic Kilcher (posts infrequently, evaluate)
David Shapiro AI (posts infrequently, evaluate)
AI Revolution / AI News (daily)
```

---

## Summary — Source types

| Type | Examples | In this file? | How to update |
|------|--------|:----------:|:-------------:|
| Blog URLs | 6 fixed URLs | Yes | `scout-official` section above |
| Research blog URLs | 1 URL | Yes | `scout-research` section above |
| RSS feeds (wire) | 4 feeds | Yes | `wire-articles` section above |
| Web search queries | Template queries | No — in the skill's prompt | Edit that scout's `SKILL.md` |
| Trending endpoints | GitHub/HF trending | No — canonical, not editorial | `fetch_trending.py` |
| Concrete results | Papers, releases, tools | No — found live by the LLM | Automatic |
