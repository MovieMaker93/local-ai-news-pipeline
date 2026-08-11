# Lux in Tenebris — Source Inventory

The **authoritative list** of handles/URLs/feeds/channels lives in
[`skills/_shared/sources.json`](../../_shared/sources.json) — both the
Python scripts and the scout `SKILL.md` files read from it, so it only needs
editing in one place. This doc is the companion: *why* each source was
picked, and ideas for what to add next. If you're expanding a source list,
edit the JSON; come back here only to also note the reasoning/idea.

---

## Scout X (`scout-x`)
**Cerca su X/Twitter** con query predefinite su un set di handle fissi (`sources.json` → `scout-x.handles`, 16 attuali).

**Espansioni possibili:**
- Aziende: `@Cohere`, `@Replit`, `@StabilityAI`, `@Midjourney`, `@Cursor_ai`, `@GitHubCopilot`
- Accademici: `@StanfordHAI`, `@MIT_AI`, `@erichorvitz`, `@demishassabis`, `@andrewyng`
- Media: `@TechCrunch`, `@TheVerge`, `@WIRED`, `@MIT_TechnologyReview`
- Open source: `@ollama`, `@LocalLLaMA`

---

## Scout Official Blogs (`scout-official`)
**Scrape direttamente** i blog ufficiali dei lab AI. Solo annunci (high signal). (`sources.json` → `scout-official.blogs`, 6 attuali.)

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

**Metodo:** `web_search` con query su arXiv + HF daily papers. Nessuna lista di fonti fisse — query strategy, non è nel JSON.

---

## Scout Open Source (`scout-opensource`)
**Cerca modelli open-weight** su GitHub Trending + HuggingFace Trending.

**Metodo:** `web_search` + `x_search`. Nessuna lista di fonti fisse — query strategy, non è nel JSON. (Gli endpoint di trending usati dal fallback `fetch_trending.py` sono invece hardcoded lì: sono gli URL canonici delle due piattaforme, non una lista editoriale da mantenere.)

---

## Scout Tools (`scout-tools`)
**Cerca tool e prodotti AI** — Product Hunt, Hacker News "Show HN", web search.

**Metodo:** `web_fetch` di producthunt.com e news.ycombinator.com + `web_search` site-scoped. Query strategy, non è nel JSON.

---

## Scout Funding (`scout-funding`)
**Cerca round di finanziamento** — TechCrunch, Crunchbase, web search.

**Metodo:** `web_search` con query su funding rounds, M&A, IPO. Query strategy, non è nel JSON.

---

## Scout Hardware (`scout-hardware`)
**Cerca chip, robot, datacenter** — Tom's Hardware, NVIDIA blog, web search.

**Metodo:** `web_search` + `x_search`. Query strategy, non è nel JSON.

---

## Scout Italia (`scout-italia`)
**Feed RSS + web search** per startup/finanziamenti/community AI italiane. (`sources.json` → `scout-italia.feeds`, 2 attuali: AI4Business, La Tech Made in Italy.)

Il resto della raccolta (web/x_search per startup specifiche, finanziamenti, spin-off) è query strategy, non è nel JSON.

---

## Wire Articles (`wire-articles`)
**Feed RSS diretti** — deterministici, senza LLM per lo stage 1. (`sources.json` → `wire-articles.feeds`, 4 attuali: Ars Technica, TechCrunch, Wired, The Verge.)

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
**Ibrido:** Python script (`youtube_scout.py`) fetcha video via RSS + LLM scrive articoli. (`sources.json` → `scout-youtube.channels`, 10 attuali con ID canale.)

**Espansioni possibili:**
```
Yannic Kilcher (posting infrequente, valutare)
David Shapiro AI (posting infrequente, valutare)
AI Revolution / AI News (daily)
```

---

## Riassunto — Tipi di fonte

| Tipo | Esempi | In sources.json? | Aggiornamento |
|------|--------|:----------:|:-------------:|
| Handle X | 16 handle fissi | Sì | `sources.json` → `scout-x.handles` |
| Blog URL | 6 URL fissi | Sì | `sources.json` → `scout-official.blogs` |
| Feed RSS (Italia) | 2 feed | Sì | `sources.json` → `scout-italia.feeds` |
| Feed RSS (wire) | 4 feed | Sì | `sources.json` → `wire-articles.feeds` |
| Canali YouTube | 10 canali | Sì | `sources.json` → `scout-youtube.channels` |
| Query web/x_search | Template query | No — nel prompt della skill | Modifica il `SKILL.md` dello scout |
| Endpoint trending | GitHub/HF trending | No — canonici, non editoriali | `fetch_trending.py` |
| Risultati concreti | Paper, post, funding | No — trovati al volo dal LLM | Automatico |
