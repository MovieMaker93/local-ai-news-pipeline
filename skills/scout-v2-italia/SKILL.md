---
name: scout-v2-italia
description: "V2 scout: Italian AI startups, news, and community — RSS + web. Returns JSON array. Headline in English, link to Italian source."
---

# Scout V2 — Italia AI Spotlight

## Focus
Italian AI ecosystem: **startups, funding rounds, community projects, university spin-offs**.
NOT general business AI news from large corporations (IBM, Microsoft Italia, etc. — those are not startup news).
NOT general international AI news (those have their own scouts).

## Sources

### 📡 RSS feeds (fetch and scan for AI-related posts)
- `https://www.ai4business.it/feed/` — AI4Business (pick ONLY startup/innovation/funding articles)
- `https://www.latechmadeinitaly.com/` — La Tech Made in Italy (deep tech and startup focus)

### 🔍 Web Search (primary method — startup funding and launches)
- `web_search: "AI startup" Italy fundraise OR series OR seed OR round <recent>`
- `web_search: site:sifted.eu "Italy" startup "AI" <recent>`
- `web_search: site:techcrunch.com Italy startup AI <recent>`
- `web_search: "startup" "intelligenza artificiale" Italia round OR funding 2026`

### 💰 Funding rounds (specific Italian AI startups)
- Search for specific startups: iGenius, Aindo, MDOTM, Alia Mentis, Principled Intelligence, Domyn, Lexroom
- `web_search: "Italian AI startup" raises OR closes OR secures funding 2026`

### 🌐 Community & Spinoffs
- `web_search: "spin-off" OR "università" AI startup Italy 2026`
- `x_search: (from:AI4I_italy OR from:StartupItalia OR #AIitalia) funding OR round OR launch`
- `web_search: "Club degli Investitori" OR "Italian Founders Fund" AI startup`

## Method
1. Fetch RSS feeds and web search for Italian AI startup content
2. **Prefer startup-specific sources** over general business news
3. Exclude articles about large corporations (IBM, Microsoft, Google Italia, etc.)
4. Scan for Italian AI startup funding rounds, launches, and community projects
5. **Translate headline to English** — the source is Italian, the output MUST be English
6. Keep the link pointing to the original Italian source
7. Write a factual 1-2 sentence summary in English
8. If no startup-specific news is found, return `[]` rather than filling with general business articles

## Output contract
Return ONLY a JSON array (no prose, no fences). Each element:
```json
{
  "title": "English title translated from Italian source",
  "summary": "1-2 factual sentences in English",
  "source": "Name of Italian publication or source",
  "url": "https://original-italian-site.it/article/...",
  "date": "YYYY-MM-DD",
  "beat": "italia",
  "signal": 1-5
}
```

## Signal guide
- Major Italian AI startup funding round (€5M+): 4-5
- Notable Italian AI product launch / partnership: 3-4
- Italian institution/community AI event: 2-3
- Minor news or general AI article from Italian perspective: 1-2

## Rules
- Every `url` MUST come from a real Italian source URL (not synthesized).
- Title MUST be in ENGLISH (translated from the Italian original).
- Link MUST point to the ITALIAN source (the original article).
- Only items dated [yesterday, today].
- Return `[]` if nothing found. All content in ENGLISH.

## Link-Source Validation (MANDATORY — run before writing final JSON)

After gathering all items but BEFORE writing the final JSON, validate EVERY item:

1. **Domain consistency:** The `source` field and the URL domain must be aligned:
   - ✓ source="AI4Business", url="https://www.ai4business.it/..." — domain matches
   - ✓ source="StartupItalia", url="https://startupitalia.eu/..." — domain matches
   - ✓ source="Sifted", url="https://sifted.eu/..." — domain matches
   - ✗ source="AI4Business", url="https://someothersite.com/..." — domain doesn't match

2. **Auto-fix on mismatch (max 3 attempts per item):** If source and URL domain don't align, use `web_search` with the article title + source name to find the real URL.

3. **Discard unfixable items:** After 3 failed attempts, REMOVE the item from your array.

4. **No placeholder URLs:** Never use "#", empty strings, or null as URLs.

## Example output
```json
[
  {
    "title": "MDOTM Secures $27M to Scale AI-Powered Investment Platform",
    "summary": "Italian fintech MDOTM raised $27M in growth funding. Its Sphere AI platform now manages over $100B in assets across 60+ institutions including Morgan Stanley.",
    "source": "AI4Business",
    "url": "https://www.ai4business.it/intelligenza-artificiale/mdotm-27m-ai-investment-platform/",
    "date": "2026-07-10",
    "beat": "italia",
    "signal": 4
  }
]
```