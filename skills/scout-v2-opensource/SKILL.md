---
name: scout-v2-opensource
description: "V2 scout: Open-weights models + GitHub/HuggingFace trending. Returns JSON object with editorial + trending."
---

# Scout V2 — Open Source

## Two outputs

**Part A — Editorial candidates** (new models, repos):
- x_search: `(Llama OR Mistral OR Qwen OR DeepSeek OR Gemma OR Phi OR "open weights" OR "new model") (release OR weights OR "open source" OR available)`
- from_date: <yesterday>, to_date: <today>
- allowed_x_handles: ["huggingface","_akhaliq","lmsysorg","togethercompute","NousResearch","xai","ylecun","karpathy"]
- Signal: genuinely new open-weights model = 4–5; minor update = 2–3

**Part B — Trending lists** (minimal sections):
- web_extract `https://github.com/trending` → top 15 repos
- web_extract `https://huggingface.co/models?sort=trending` → top 10 models

## Output contract
Return a JSON **object** (NOT array) with this shape:
```json
{
  "editorial": [ ...standard scout contract items... ],
  "trending": {
    "github": {
      "title": "GitHub Trending",
      "url": "https://github.com/trending",
      "link_label": "github.com/trending",
      "date": "<today>",
      "items": [
        {"name": "user/repo", "url": "https://github.com/user/repo", "meta": "Python · 12.3k ★ · +456 today"}
      ]
    },
    "huggingface": {
      "title": "Models Trending (Hugging Face)",
      "url": "https://huggingface.co/models?sort=trending",
      "link_label": "huggingface.co/models",
      "date": "<today>",
      "items": [
        {"name": "org/model-name", "url": "https://huggingface.co/org/model-name", "meta": "35B MoE, language world model"}
      ]
    }
  }
}
```

## GitHub trending extraction
For each top 15 repos from `https://github.com/trending`:
- `name`: user/repo
- `url`: https://github.com/user/repo
- `meta`: language + stars + today's delta (e.g. `"Python · 19.6k ★ · +3719 today"`)

## HuggingFace trending extraction
For each top 10 models from `https://huggingface.co/models?sort=trending`:
- `name`: org/model-name
- `url`: https://huggingface.co/org/model-name
- `meta`: short description (e.g. `"35B MoE, language world model"`)

If either fetch fails, set `"items": []` for that source.

## Rules
- Every `url` in editorial MUST come from real x_search result. Never synthesize.
- Trending URLs come from web_extract.
- All content in ENGLISH.

## Link-Source Validation (MANDATORY — run before writing final JSON)

After gathering all items but BEFORE writing the final JSON, validate EVERY item in the `editorial` array:

1. **Domain consistency:** Extract the domain from `url`. The `source` field and the URL domain must be aligned:
   - ✓ source="TechCrunch", url="https://techcrunch.com/..." — domain "techcrunch.com" matches
   - ✓ source="Hacker News", url="https://news.ycombinator.com/..." — "ycombinator" in URL
   - ✓ source="arXiv", url="https://arxiv.org/abs/..." — "arxiv" in both
   - ✓ source="@karpathy" / "Karpathy", url="https://x.com/..." — exception for X/Twitter users
   - ✗ source="Hacker News", url="https://medium.com/..." — domain doesn't match
   - ✗ source="TechCrunch", url="https://someothersite.com/..." — domain doesn't match

2. **Auto-fix on mismatch (max 3 attempts per item):** If source and URL domain don't align, use `web_search` with the article title + source name to find the real URL. Each attempt = one search cycle.

3. **Discard unfixable items:** After 3 failed attempts, REMOVE the item from the `editorial` array. Do NOT keep items with mismatched source↔url.

4. **No placeholder URLs:** Never use "#", empty strings, or null as URLs. If a real URL can't be found after 3 attempts, discard the item entirely.
