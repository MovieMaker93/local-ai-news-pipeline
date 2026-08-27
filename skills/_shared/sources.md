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

## Summary — Source types

| Type | Examples | In this file? | How to update |
|------|--------|:----------:|:-------------:|
| Blog URLs | 6 fixed URLs | Yes | `scout-official` section above |
| Research blog URLs | 1 URL | Yes | `scout-research` section above |
| RSS feeds (wire) | 4 feeds | Yes | `wire-articles` section above |
| Web search queries | Template queries | No — in the skill's prompt | Edit that scout's `SKILL.md` |
| Trending endpoints | GitHub/HF trending | No — canonical, not editorial | `fetch_trending.py` |
| Concrete results | Papers, releases, tools | No — found live by the LLM | Automatic |
