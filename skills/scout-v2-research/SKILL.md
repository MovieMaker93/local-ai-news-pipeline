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

## 🔴 FIRECRAWL FALLBACK — when web tools fail with "Payment Required"

If `web_search` or `web_extract` fail with "Payment Required" / "Insufficient credits":

1. **HuggingFace Daily Papers via curl:**
```bash
curl -sL "https://huggingface.co/papers" | python3 -c "
import sys, re; html = sys.stdin.read()
# Extract paper cards from HF papers page
papers = re.findall(r'<article[^>]*>.*?<h3[^>]*>(.*?)</h3>.*?href=\"(/(?:papers|papers)/[^\"]+)\".*?<p>(.*?)</p>', html, re.DOTALL)
for title, path, desc in papers[:15]:
    t = re.sub(r'<[^>]+>', '', title).strip()
    d = re.sub(r'<[^>]+>', '', desc).strip()[:200]
    print(f'{t} | https://huggingface.co{path} | {d}')
" 2>/dev/null
```

2. **arXiv recent submissions via API (free):**
```bash
curl -s "http://export.arxiv.org/api/query?search_query=cat:cs.AI+AND+cat:cs.LG&sortBy=submittedDate&sortOrder=descending&max_results=30" | python3 -c "
import sys, re; data = sys.stdin.read()
for m in re.finditer(r'<entry>.*?<title>(.*?)</title>.*?<id>(.*?)</id>.*?<summary>(.*?)</summary>', data, re.DOTALL):
    t = re.sub(r'\s+', ' ', m.group(1)).strip()
    u = m.group(2).strip().rstrip('v1')
    s = re.sub(r'\s+', ' ', m.group(3)).strip()[:200]
    print(f'{t} | {u} | {s}')
" 2>/dev/null
```

3. **Generic site fetch (replaces web_extract):**
```bash
curl -sL "URL" | python3 -c "
import sys, re; html = sys.stdin.read()
m = re.search(r'<title>(.*?)</title>', html, re.DOTALL)
print('TITLE:', m.group(1).strip() if m else 'N/A')
text = re.sub(r'<[^>]+>', ' ', html); text = re.sub(r'\s+', ' ', text).strip()[:3000]
print('BODY:', text)
"
```

4. If ALL fallbacks fail, return `[]`.

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
