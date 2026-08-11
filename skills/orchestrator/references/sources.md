# Lux in Tenebris — Source Inventory

Tutti gli scout V2 con le loro fonti attuali. Aggiungi/modifica qui quando espandi le fonti.

---

## Scout X (`scout-x`)
**Cerca su X/Twitter** con query predefinite su un set di handle fissi.

**Handle attuali:**
`OpenAI`, `AnthropicAI`, `GoogleDeepMind`, `xai`, `NousResearch`, `sama`, `karpathy`, `huggingface`, `DeepLearningAI`, `ylecun`, `simonw`, `swyx`, `_philschmid`, `omarsar0`, `_akhaliq`, `lmsysorg`

**Espansioni possibili:**
- Aziende: `@Cohere`, `@Replit`, `@StabilityAI`, `@Midjourney`, `@Cursor_ai`, `@GitHubCopilot`
- Accademici: `@StanfordHAI`, `@MIT_AI`, `@erichorvitz`, `@demishassabis`, `@andrewyng`
- Media: `@TechCrunch`, `@TheVerge`, `@WIRED`, `@MIT_TechnologyReview`
- Open source: `@ollama`, `@LocalLLaMA`

---

## Scout Official Blogs (`scout-official`)
**Scrape direttamente** i blog ufficiali dei lab AI. Solo annunci (high signal).

**URL attuali:**
```
https://www.anthropic.com/news
https://openai.com/blog
https://deepmind.google/discover/blog/
https://ai.meta.com/blog/
https://mistral.ai/news/
https://x.ai/news
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

**Metodo:** `web_search` con query su arXiv + HF daily papers.

---

## Scout Open Source (`scout-opensource`)
**Cerca modelli open-weight** su GitHub Trending + HuggingFace Trending.

**Metodo:** `web_search` + `x_search`.

---

## Scout Tools (`scout-tools`)
**Cerca tool e prodotti AI** — Product Hunt, Hacker News "Show HN", web search.

**Metodo:** `web_fetch` di producthunt.com e news.ycombinator.com + `web_search` site-scoped.

---

## Scout Funding (`scout-funding`)
**Cerca round di finanziamento** — TechCrunch, Crunchbase, web search.

**Metodo:** `web_search` con query su funding rounds, M&A, IPO.

---

## Scout Hardware (`scout-hardware`)
**Cerca chip, robot, datacenter** — Tom's Hardware, NVIDIA blog, web search.

**Metodo:** `web_search` + `x_search`.

---

## Wire Articles (`wire-articles`)
**Feed RSS diretti** — deterministici, senza LLM per lo stage 1.

**Feed attuali:**
```
Ars Technica
TechCrunch
Wired
The Verge
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
**Ibrido:** Python script (`youtube_scout.py`) fetcha video via RSS + LLM (DeepSeek V4 Flash) scrive articoli.

**Canali attuali (10 hardcoded):**
```
The AI Daily Brief    → UCKelCK4ZaO6HeEI1KQjqzWA
Bloomberg Technology  → UCrM7B7SL_g1edFOnmj-SDKg
Theo - t3.gg         → UCbRP3c757lWg9M-U7TyEkXA
Matt Wolfe           → UChpleBmo18P08aKCIgti38g
Two Minute Papers    → UCbfYPyITQ-7l4upoX8nvctg
Sabine Hossenfelder  → UC1yNl2E66ZzKApQdRuTQ4tw
Fireship             → UCsBjURrPoezykLs9EqgamOA
AI Explained         → UCNJ1Ymd5yFuUPtn21xtRbbw
AI Tool Report       → UCmeU2DYiVy80wMBGZzEWnbw
Beyond AI News       → UC5l7RouTQ60oUjLjt1Nh-UQ
```

**Espansioni possibili:**
```
Yannic Kilcher (posting infrequente, valutare)
David Shapiro AI (posting infrequente, valutare)
AI Revolution / AI News (daily)
```

**Modello dedicato:** `deepseek/deepseek-v4-flash` su OpenRouter (non il default del profilo).

---

## Riassunto — Tipi di fonte

| Tipo | Esempi | Hardcoded? | Aggiornamento |
|------|--------|:----------:|:-------------:|
| Handle X | 16 handle fissi | Sì | Modifica SKILL.md scout-x |
| Blog URL | 6 URL fissi | Sì | Modifica SKILL.md scout-official |
| Feed RSS | 4 feed | Sì (in wire_articles.py) | Modifica wire_articles.py |
| Query web | Template query | Sì (nel prompt scout) | Modifica run.sh prompt |
| Risultati concreti | Paper, post, funding | **No** — trovati al volo dal LLM | Automatico |

Per espandere le fonti, **modifica il file `.md` della skill scout corrispondente**, non `run.sh`.