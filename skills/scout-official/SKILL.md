---
name: scout-official
description: "Scout: official blogs of labs that ship open-weight models. Returns JSON array."
---

# Scout — Model Makers (Official Blogs)

## Focus
Official announcements from the labs whose models you can actually download
and run: open-weight releases, quantized editions, licensing changes, model
deprecations, local-runtime news (Ollama library additions, llama.cpp
compatibility notes).
NOT: pure API/cloud product news with no downloadable artifact.

## Sources
Read `skills/_shared/sources.md` with `read_file`, find the
`## Scout Official Blogs (\`scout-official\`)` section, and take the array
from the `json` code block right under it — that's the current list (single
source of truth; don't hardcode it here, it drifts out of sync with the
file otherwise).

## Method
web_fetch each URL from that list. Scan for posts dated within [yesterday, today].

## Output contract
Return ONLY a JSON array (no prose, no fences). Each element:
```json
{"title":"…","summary":"1–2 factual sentences","source":"Lab name",
 "url":"https://…","date":"YYYY-MM-DD","beat":"official","signal":1-5}
```

## Signal guide
- Official blog posts are HIGH signal by default (3+). These are announcements, not rumours.
- Major open-weight model releases / licensing changes: 4–5
- Minor feature updates / small model refreshes: 3

## Rules
- Every `url` MUST come from the actual fetched page. Never synthesize URLs.
- If a blog is unreachable, skip it silently.
- Return `[]` if nothing found in-window. All content in ENGLISH.

## Link-Source Validation (MANDATORY — run before writing final JSON)

After gathering all items but BEFORE writing the final JSON, validate EVERY item:

1. **Domain consistency:** Extract the domain from `url`. The `source` field and the URL domain must be aligned:
   - ✓ source="Qwen", url="https://qwenlm.github.io/blog/..." — domain matches
   - ✓ source="Meta AI", url="https://ai.meta.com/blog/..." — domain matches
   - ✗ source="Qwen", url="https://someblog.com/..." — domain doesn't match

2. **Auto-fix on mismatch (max 3 attempts per item):** If source and URL domain don't align, use `web_search` with the article title + source name to find the real URL. Each attempt = one search cycle.

3. **Discard unfixable items:** After 3 failed attempts, REMOVE the item from your array. Do NOT keep items with mismatched source↔url.

4. **No placeholder URLs:** Never use "#", empty strings, or null as URLs. If a real URL can't be found after 3 attempts, discard the item entirely.
