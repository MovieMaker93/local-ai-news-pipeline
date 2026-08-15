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
**Cerca su X/Twitter** con query predefinite su un set di handle fissi.

<!-- sources:scout-x:handles -->
```json
[
  "OpenAI", "AnthropicAI", "GoogleDeepMind", "xai", "NousResearch",
  "sama", "karpathy", "huggingface", "DeepLearningAI", "ylecun",
  "simonw", "swyx", "_philschmid", "omarsar0", "_akhaliq", "lmsysorg"
]
```

**Espansioni possibili:**
- Aziende: `@Cohere`, `@Replit`, `@StabilityAI`, `@Midjourney`, `@Cursor_ai`, `@GitHubCopilot`
- Accademici: `@StanfordHAI`, `@MIT_AI`, `@erichorvitz`, `@demishassabis`, `@andrewyng`
- Media: `@TechCrunch`, `@TheVerge`, `@WIRED`, `@MIT_TechnologyReview`
- Open source: `@ollama`, `@LocalLLaMA`

---

## Scout Official Blogs (`scout-official`)
**Scrape direttamente** i blog ufficiali dei lab AI. Solo annunci (high signal).

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

**Espansioni possibili:**
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
**Cerca paper** su arXiv e HuggingFace daily papers con query predefinite.

**Metodo:** `web_search` con query su arXiv + HF daily papers. Nessuna lista di fonti fisse — query strategy, non è in questo file.

---

## Scout Open Source (`scout-opensource`)
**Cerca modelli open-weight** su GitHub Trending + HuggingFace Trending.

**Metodo:** `web_search` + `x_search`. Nessuna lista di fonti fisse — query strategy, non è in questo file. (Gli endpoint di trending usati dal fallback `fetch_trending.py` sono invece hardcoded lì: sono gli URL canonici delle due piattaforme, non una lista editoriale da mantenere.)

---

## Scout Tools (`scout-tools`)
**Cerca tool e prodotti AI** — Product Hunt, Hacker News "Show HN", web search.

**Metodo:** `web_fetch` di producthunt.com e news.ycombinator.com + `web_search` site-scoped. Query strategy, non è in questo file.

---

## Scout Funding (`scout-funding`)
**Cerca round di finanziamento** — TechCrunch, Crunchbase, web search.

**Metodo:** `web_search` con query su funding rounds, M&A, IPO. Query strategy, non è in questo file.

---

## Scout Hardware (`scout-hardware`)
**Cerca chip, robot, datacenter** — Tom's Hardware, NVIDIA blog, web search.

**Metodo:** `web_search` + `x_search`. Query strategy, non è in questo file.

---

## Scout Italia (`scout-italia`)
**Feed RSS + web search** per startup/finanziamenti/community AI italiane.

<!-- sources:scout-italia:feeds -->
```json
[
  "https://www.ai4business.it/feed/",
  "https://www.latechmadeinitaly.com/"
]
```

Il resto della raccolta (web/x_search per startup specifiche, finanziamenti, spin-off) è query strategy, non è in questo file.

---

## Wire Articles (`wire-articles`)
**Feed RSS diretti** — deterministici, senza LLM per lo stage 1.

<!-- sources:wire-articles:feeds -->
```json
[
  "https://feeds.arstechnica.com/arstechnica/index",
  "https://techcrunch.com/feed/",
  "https://www.wired.com/feed/rss",
  "https://www.theverge.com/rss/index.xml"
]
```

**Espansioni possibili:**
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
**Ibrido:** Python script (`youtube_scout.py`) fetcha video via RSS + LLM scrive articoli. Per metodologia di selezione e criteri di frequenza vedi [`scout-youtube/references/channels.md`](../scout-youtube/references/channels.md) — qui c'è solo la lista attuale.

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

**Espansioni possibili:**
```
Yannic Kilcher (posting infrequente, valutare)
David Shapiro AI (posting infrequente, valutare)
AI Revolution / AI News (daily)
```

---

## Riassunto — Tipi di fonte

| Tipo | Esempi | In questo file? | Aggiornamento |
|------|--------|:----------:|:-------------:|
| Handle X | 16 handle fissi | Sì | Sezione `scout-x` sopra |
| Blog URL | 6 URL fissi | Sì | Sezione `scout-official` sopra |
| Feed RSS (Italia) | 2 feed | Sì | Sezione `scout-italia` sopra |
| Feed RSS (wire) | 4 feed | Sì | Sezione `wire-articles` sopra |
| Canali YouTube | 10 canali | Sì | Sezione `scout-youtube` sopra |
| Query web/x_search | Template query | No — nel prompt della skill | Modifica il `SKILL.md` dello scout |
| Endpoint trending | GitHub/HF trending | No — canonici, non editoriali | `fetch_trending.py` |
| Risultati concreti | Paper, post, funding | No — trovati al volo dal LLM | Automatico |
