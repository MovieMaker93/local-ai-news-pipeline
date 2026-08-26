---
name: scout-opensource
description: "Scout: open-weight model releases + GitHub/HuggingFace trending, filtered for local-AI relevance. Returns JSON object with editorial + trending."
---

# Scout — Open Source & Open Weights

## Two outputs

**Part A — Editorial candidates** (new models, repos):
- web_search: `(Llama OR Mistral OR Qwen OR DeepSeek OR Gemma OR Phi OR SmolLM OR "open weights" OR "new model") (release OR weights OR GGUF OR quantized OR "open source" OR available) <yesterday>`
- web_search: `site:huggingface.co new model <yesterday>`
- Signal: genuinely new open-weights model = 4–5; minor update/quant variant = 2–3

**Part B — Trending lists** (minimal sections):
- web_extract `https://github.com/trending` → top 15 repos, then **keep only
  the ones that are AI/LLM/inference-related** (name or description mentions
  ai, llm, ml, model, inference, agent, rag, embedding, tts, asr, vision).
  Cap at 10. If fewer than 3 qualify, keep what qualifies.
- web_extract `https://huggingface.co/models?sort=trending` → top 10 models (all qualify)

## Output contract
Return a JSON **object** (NOT array) with this shape:
```json
{
  "editorial": [ ...standard scout contract items... ],
  "trending": {
    "github": {
      "title": "GitHub Trending · AI",
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
- **Filter:** keep only AI/LLM/inference-related repos, max 10. This is a
  local-AI paper — a random web framework trending #1 is noise here, not news.

## HuggingFace trending extraction
For each top 10 models from `https://huggingface.co/models?sort=trending`:
- `name`: org/model-name
- `url`: https://huggingface.co/org/model-name
- `meta`: short description (e.g. `"35B MoE, language world model"`)

If either fetch fails, set `"items": []` for that source.

## Rules
- Every `url` in editorial MUST come from a real web_search/web_extract result. Never synthesize.
- Trending URLs come from web_extract.
- All content in ENGLISH.

## Link-Source Validation (MANDATORY — run before writing final JSON)

After gathering all items but BEFORE writing the final JSON, validate EVERY item in the `editorial` array:

1. **Domain consistency:** Extract the domain from `url`. The `source` field and the URL domain must be aligned:
   - ✓ source="HuggingFace", url="https://huggingface.co/..." — "huggingface" in URL
   - ✓ source="GitHub", url="https://github.com/..." — "github" in URL
   - ✗ source="HuggingFace", url="https://medium.com/..." — domain doesn't match

2. **Auto-fix on mismatch (max 3 attempts per item):** If source and URL domain don't align, use `web_search` with the article title + source name to find the real URL. Each attempt = one search cycle.

3. **Discard unfixable items:** After 3 failed attempts, REMOVE the item from the `editorial` array. Do NOT keep items with mismatched source↔url.

4. **No placeholder URLs:** Never use "#", empty strings, or null as URLs. If a real URL can't be found after 3 attempts, discard the item entirely.
