---
name: scout-v2-tools
description: "V2 scout: New AI tools, product launches, dev tools. Returns JSON array."
---

# Scout V2 — Tools & Launches

## Focus
New AI products, developer tools, app launches, notable feature releases.
NOT funding, NOT hardware (those have their own scouts).

## Sources
- web_search: `new AI tool launch <yesterday>`, `AI product launch <yesterday>`
- Site-scoped: `site:techcrunch.com AI tool <yesterday>`, `site:theverge.com AI <yesterday>`
- web_fetch `https://www.producthunt.com/` — scan day's AI launches
- web_fetch `https://news.ycombinator.com/` — scan "Show HN" AI tools
- Optional x_search: `("introducing" OR launched OR "now available") (AI OR agent OR app)`
  from_date <yesterday>, to_date <today>

## Output contract
Return ONLY a JSON array (no prose, no fences). Each element:
```json
{"title":"…","summary":"1–2 factual sentences","source":"Site or product name",
 "url":"https://…","date":"YYYY-MM-DD","beat":"tools","signal":1-5}
```

## Signal guide
- Widely-adopted or first-of-its-kind tool: 3–4
- Minor feature bump / update: 1–2

## Rules
- Every `url` MUST come from real web_search/web_extract result or x_search permalink.
- Never synthesize URLs. Set `"url": null` if unknown.
- Only items dated [yesterday, today].
- Return `[]` if nothing found. All content in ENGLISH.

## Link-Source Validation (MANDATORY — run before writing final JSON)

After gathering all items but BEFORE writing the final JSON, validate EVERY item:

1. **Domain consistency:** Extract the domain from `url`. The `source` field and the URL domain must be aligned:
   - ✓ source="TechCrunch", url="https://techcrunch.com/..." — domain "techcrunch.com" matches
   - ✓ source="Hacker News", url="https://news.ycombinator.com/..." — "ycombinator" in URL
   - ✓ source="arXiv", url="https://arxiv.org/abs/..." — "arxiv" in both
   - ✓ source="@karpathy" / "Karpathy", url="https://x.com/..." — exception for X/Twitter users
   - ✗ source="Hacker News", url="https://medium.com/..." — domain doesn't match
   - ✗ source="TechCrunch", url="https://someothersite.com/..." — domain doesn't match

2. **Auto-fix on mismatch (max 3 attempts per item):** If source and URL domain don't align, use `web_search` with the article title + source name to find the real URL. Each attempt = one search cycle.

3. **Discard unfixable items:** After 3 failed attempts, REMOVE the item from your array. Do NOT keep items with mismatched source↔url.

4. **No placeholder URLs:** Never use "#", empty strings, or null as URLs. If a real URL can't be found after 3 attempts, discard the item entirely.
