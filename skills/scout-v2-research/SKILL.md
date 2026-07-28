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
- If you know a paper exists but haven't fetched its URL, **drop it**. Do not
  emit `null`, `""` or `"#"` — the renderer discards items without a valid URL,
  so an unlinked item is wasted work, not a partial win.
- Broken-end URLs are worse than missing links.
- Only items dated [yesterday, today] OR the most recent available batch if arXiv lag applies (max 4 days back).
- Return `[]` if nothing found. All content in ENGLISH.

## 🔴 FALLBACK — when web_search / web_extract fail

When web tools fail (Payment Required, tool unavailable, ddgs missing, network error):

### ⚠️ Security-scanner-safe approach (preferred)
Environments with TIRITH or similar scanners BLOCK `curl | python3` pipes. Use two-step: save to file first, then parse.

### 1. HuggingFace Daily Papers via curl (two-step)

```bash
# Step 1: save page
curl -sL "https://huggingface.co/papers" -o /tmp/hf_papers.html

# Step 2: extract paper IDs
# NOTE: HF date-specific URLs (/papers/date/YYYY-MM-DD) ALL return identical content.
# Use the main /papers page — it shows the latest batch.
python3 -c "
import re
with open('/tmp/hf_papers.html') as f:
    html = f.read()
aids = re.findall(r'/papers/(\d+\.\d+)\"', html)
for aid in sorted(set(aids))[:20]:
    print(f'https://huggingface.co/papers/{aid} | https://arxiv.org/abs/{aid}')
"
```

### 2. arXiv recent submissions via API (free, two-step)

```bash
# Step 1: save XML (use HTTPS)
curl -sL "https://export.arxiv.org/api/query?search_query=cat:cs.AI+AND+cat:cs.LG&sortBy=submittedDate&sortOrder=descending&max_results=50" -o /tmp/arxiv_raw.xml

# Step 2: parse with a saved script (write_file, then terminal)
```

**arXiv API quirks (essential):**
- Use **HTTPS** (`https://export.arxiv.org/`) — plain HTTP works but is less reliable.
- **Date filter (`submittedDate:[...]` range query) returns 0 results** — do not use it. Use `sortBy=submittedDate&sortOrder=descending` with `max_results=50` and filter dates in your script.
- **Date lag**: arXiv's `published` field lags the current date by 1-2 days. Accept items from the last 2-4 days, not [yesterday, today].
- **ID version suffix**: arXiv IDs in `<id>` end with `v1`, `v2`, etc. Strip with regex: `re.sub(r'v\d+$', '', aid)`.
- Use the `published` field (submission date). Ignore `updated`.

**Parse script template — save to file, then run:**

Save as Python file (use write_file), then `python3 /tmp/parse_arxiv.py`:
```python
import xml.etree.ElementTree as ET, json, re
tree = ET.parse('/tmp/arxiv_raw.xml')
root = tree.getroot()
ns = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
notable_keywords = [
    'llm', 'large language model', 'reasoning', 'agent', 'multimodal',
    'alignment', 'reinforcement learning', 'transformer', 'attention',
    'diffusion', 'benchmark', 'chain-of-thought', 'moe', 'fine-tuning',
    'quantization', 'distillation', 'rag', 'vision language', 'vlm',
    'pretraining', 'scaling law', 'world model', 'safety', 'sft',
    'rlhf', 'dpo', 'grpo', 'kv-cache', 'instruction tuning',
    'self-improving', 'coding agent', 'spatial reasoning'
]
papers = []
for entry in root.findall('atom:entry', ns):
    title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
    summary = entry.find('atom:summary', ns).text.strip().replace('\n', ' ')
    aid_text = entry.find('atom:id', ns).text.strip()
    aid = re.sub(r'v\d+$', '', aid_text.split('/')[-1]) if 'arxiv' in aid_text else aid_text
    pub = entry.find('atom:published', ns).text[:10]
    cats = [c.get('term') for c in entry.findall('atom:category', ns)]
    if not any(c in cats for c in ['cs.AI','cs.LG','cs.CL','cs.CV','cs.MA','cs.RO','cs.MM']):
        continue
    score = sum(1 for kw in notable_keywords if kw in f'{title} {summary}'.lower())
    if score == 0:
        continue
    papers.append({
        'title': title[:200], 'summary': summary[:300], 'source': 'arXiv',
        'url': f'https://arxiv.org/abs/{aid}', 'date': pub, 'beat': 'research',
        'signal': min(score + 1, 5)
    })
print(json.dumps(papers, indent=2))
```

### 3. Fetching summaries for HF-listed papers

Once you have arXiv IDs from HuggingFace, batch-fetch their summaries:
```bash
curl -sL "https://export.arxiv.org/api/query?id_list=ID1,ID2,ID3" -o /tmp/hf_abstracts.xml
# Then parse with the same XML approach as above
```

### 4. If ALL fallbacks fail, return `[]`.

### 5. Pitfalls
- arXiv API rate-limits: stay under ~1 req/sec. A single `max_results=50` query is fine.
- `max_results` caps at 2000 per query, but 50 is plenty for a daily sweep.
- Papers from HF's daily page may be 2-5 days old — always check `published` date.
- The arXiv `updated` date resets when metadata changes. Do not use it for date filtering.

## Link-Source Validation (MANDATORY — run before writing final JSON)

After gathering all items but BEFORE writing the final JSON, validate EVERY item:

1. **Domain consistency:** Extract the domain from `url`. The `source` field and the URL domain must be aligned:
   - ✓ source="arXiv", url="https://arxiv.org/abs/..." — "arxiv" in both
   - ✓ source="HuggingFace", url="https://huggingface.co/papers/..." — "huggingface" in URL
   - ✗ source="arXiv", url="https://huggingface.co/..." — domain doesn't match

2. **Auto-fix on mismatch (max 3 attempts per item):** If source and URL domain don't align, use `web_search` with the article title + source name to find the real URL.

3. **Discard unfixable items:** After 3 failed attempts, REMOVE the item from your array.

4. **No placeholder URLs:** Never use "#", empty strings, or null as URLs.
