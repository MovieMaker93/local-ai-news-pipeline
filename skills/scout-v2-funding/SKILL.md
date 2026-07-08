---
name: scout-v2-funding
description: "V2 scout: AI funding rounds, VC, M&A, IPOs. Returns JSON array."
---

# Scout V2 — VC & Funding

## Focus
AI-focused funding rounds, VC deals, M&A, valuations, IPOs.
NOT tools, NOT hardware.

## Sources (free, dated, fetchable)
- Site-scoped web_search:
  - `site:techcrunch.com AI funding round <yesterday>`
  - `site:news.crunchbase.com AI raises <yesterday>`
  - `site:techstartups.com funding roundup <yesterday>`
  - `site:tech.eu OR site:eu-startups.com AI funding <yesterday>` (Europe)
  - `site:aifundingtracker.com <yesterday>`
- web_fetch the 2–3 best links to confirm amount + stage + lead investor
- Optional x_search on deal accounts: ["TechCrunch","crunchbase","StrictlyVC","axios"]

Skip paywalled sources (PitchBook, CB Insights, The Information) — they're not fetchable.

## Output contract
Return ONLY a JSON array (no prose, no fences). Each element:
```json
{"title":"…","summary":"amount, stage (seed/Series A/B/…), lead investor, sector",
 "source":"Site name","url":"https://…","date":"YYYY-MM-DD","beat":"funding","signal":1-5}
```

## Signal guide
- Round ≥ $100M or frontier-lab raise: 4–5
- Seed / Series A: 2–3
- Unconfirmed or no named investor: 1

## Rules
- Every `url` MUST come from real web_search/web_extract result. Never synthesize.
- Put key facts in summary: amount, stage, lead investor, sector.
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
