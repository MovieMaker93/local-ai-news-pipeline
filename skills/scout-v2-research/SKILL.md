---
name: scout-v2-research
description: "V2 scout: arXiv + HuggingFace daily papers. Returns JSON array."
---

# Scout V2 — Research

## Sources
- arXiv (AI/ML papers from last 24h)
- HuggingFace Daily Papers

## Queries
- web_search: `arXiv AI paper <yesterday>`, `Hugging Face daily papers <yesterday>`
- web_extract: `https://huggingface.co/papers` — keep entries dated in-window

## Output contract
Return ONLY a JSON array (no prose, no fences). Each element:
```json
{"title":"…","summary":"1–2 factual sentences — clear result (benchmark, method, ablation)",
 "source":"arXiv or HuggingFace","url":"https://arxiv.org/abs/…","date":"YYYY-MM-DD","beat":"research","signal":1-5}
```

## Signal guide
- Papers with clear benchmark results / new SOTA: 4–5
- Solid methods papers: 3
- Plain preprints with no result: 1–2

## Rules
- Every `url` MUST come from real web_search result or web_extract. NEVER synthesize arXiv IDs.
- If you know a paper exists but haven't fetched its URL, set `"url": null`.
- Breakend URLs are worse than missing links.
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
