# Lux in Tenebris — Source Inventory

Single file, single source of truth: the *why* (which sources, and what to
add next) sits next to the *what* (the actual lists). Each scout's fixed
list — handles, URLs, feeds, channels — lives in a fenced `json` block right
under a `<!-- sources:... -->` anchor comment. Edit the list in place here;
nothing else needs touching.

`youtube_scout.py` and `wire_articles.py` parse this file directly (find the
anchor, read the JSON block under it — see either script's `SOURCES_FILE`
loader for the exact regex). The `scout-x`, `scout-official`, and
`scout-italia` skills read it with `read_file` the same way a human would:
find their section, use the list in the `json` block.

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

## Scout Official Blogs (`scout-official`)
**Scrapes official AI lab blogs directly.** Announcements only (high signal).

<!-- sources:scout-official:blogs -->
```json
[
  "https://www.anthropic.com/news",
  "https://openai.com/blog",
  "https://deepmind.google/discover/blog/",
  "https://ai.meta.com/blog/",
  "https://mistral.ai/news/",
  "https://x.ai/news"
]
```

**Possible expansions:**
```
https://cohere.com/blog
https://blog.replit.com
https://ai.googleblog.com
https://machinelearning.apple.com/blog
https://cursor.sh/blog
https://www.microsoft.com/en-us/research/blog
https://huggingface.co/blog
https://stability.ai/blog
https://blog.google/technology/ai/
```

---

## Scout Research (`scout-research`)
**Searches papers** on arXiv and HuggingFace daily papers with predefined queries.

**Method:** `web_search` with queries against arXiv + HF daily papers. No fixed source list — query strategy, not in this file.

---

## Scout Open Source (`scout-opensource`)
**Searches open-weight models** on GitHub Trending + HuggingFace Trending.

**Method:** `web_search` + `x_search`. No fixed source list — query strategy, not in this file. (The trending endpoints used by the `fetch_trending.py` fallback are hardcoded there instead: they're the two platforms' canonical URLs, not an editorial list to maintain.)

---

## Scout Tools (`scout-tools`)
**Searches AI tools and products** — Product Hunt, Hacker News "Show HN", web search.

**Method:** `web_fetch` on producthunt.com and news.ycombinator.com + site-scoped `web_search`. Query strategy, not in this file.

---

## Scout Funding (`scout-funding`)
**Searches funding rounds** — TechCrunch, Crunchbase, web search.

**Method:** `web_search` with queries on funding rounds, M&A, IPOs. Query strategy, not in this file.

---

## Scout Hardware (`scout-hardware`)
**Searches chips, robots, datacenters** — Tom's Hardware, NVIDIA blog, web search.

**Method:** `web_search` + `x_search`. Query strategy, not in this file.

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

## Wire Articles (`wire-articles`)
**Direct RSS feeds** — deterministic, no LLM for stage 1.

<!-- sources:wire-articles:feeds -->
```json
[
  "https://feeds.arstechnica.com/arstechnica/index",
  "https://techcrunch.com/feed/",
  "https://www.wired.com/feed/rss",
  "https://www.theverge.com/rss/index.xml"
]
```

**Possible expansions:**
```
MIT Technology Review (feed)
VentureBeat (feed)
The Next Web
The Information
Reuters Technology
Bloomberg AI
Axios
```

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
| X handles | 16 fixed handles | Yes | `scout-x` section above |
| Blog URLs | 6 fixed URLs | Yes | `scout-official` section above |
| RSS feeds (Italy) | 2 feeds | Yes | `scout-italia` section above |
| RSS feeds (wire) | 4 feeds | Yes | `wire-articles` section above |
| YouTube channels | 10 channels | Yes | `scout-youtube` section above |
| Web/x_search queries | Template queries | No — in the skill's prompt | Edit that scout's `SKILL.md` |
| Trending endpoints | GitHub/HF trending | No — canonical, not editorial | `fetch_trending.py` |
| Concrete results | Papers, posts, funding | No — found live by the LLM | Automatic |
