---
name: scout-selfhost
description: "Scout: self-hosted AI stack news — r/LocalLLaMA, r/selfhosted, Open WebUI, n8n, Home Assistant, privacy. Returns JSON array."
---

# Scout — Self-Hosted Stack

## Focus
The software stack around locally-run models: Open WebUI and alternative
frontends, n8n/automation with local models, Home Assistant + LLM
integrations, privacy-focused setups (no telemetry, airgapped), homelab
inference patterns (Docker, Compose, GPU passthrough), sync/backup of local
knowledge bases, community wisdom worth elevating (a r/LocalLLaMA thread
that changes how people run things counts as news here).
NOT: pure model releases (official/opensource scouts), hardware (own scout),
generic self-hosted apps with no AI angle.

## Sources
- web_search: `site:reddit.com r/LocalLLaMA <yesterday>` — top threads by discussion volume
- web_search: `site:reddit.com r/selfhosted AI <yesterday>`
- web_search: `Open WebUI release <yesterday>`, `n8n AI node <yesterday>`, `Home Assistant LLM <yesterday>`
- web_fetch `https://openwebui.com/blog` (Open WebUI release notes)
- web_fetch `https://blog.n8n.io/` (n8n releases with AI features)

## Output contract
Return ONLY a JSON array (no prose, no fences). Each element:
```json
{"title":"…","summary":"1–2 factual sentences","source":"Site or community name",
 "url":"https://…","date":"YYYY-MM-DD","beat":"selfhost","signal":1-5}
```

## Signal guide
- Major release of a core stack component (Open WebUI, n8n AI features): 4
- A community finding that changes practice (config, quant choice, bug workaround): 3–4
- Minor integration/update: 2

## Rules
- Every `url` MUST come from real web_search/web_extract result. Never synthesize.
- Reddit threads: only ones with substantial engagement (100+ upvotes or an
  active discussion) and a durable insight — not drama or beginner questions.
- Return `[]` if nothing found. All content in ENGLISH.

## Link-Source Validation (MANDATORY — run before writing final JSON)

After gathering all items but BEFORE writing the final JSON, validate EVERY item:

1. **Domain consistency:** Extract the domain from `url`. The `source` field and the URL domain must be aligned:
   - ✓ source="r/LocalLLaMA", url="https://www.reddit.com/r/LocalLLaMA/..." — "reddit" in URL
   - ✓ source="Open WebUI", url="https://openwebui.com/blog/..." — domain matches
   - ✗ source="Open WebUI", url="https://reddit.com/..." — domain doesn't match

2. **Auto-fix on mismatch (max 3 attempts per item):** If source and URL domain don't align, use `web_search` with the article title + source name to find the real URL. Each attempt = one search cycle.

3. **Discard unfixable items:** After 3 failed attempts, REMOVE the item from your array. Do NOT keep items with mismatched source↔url.

4. **No placeholder URLs:** Never use "#", empty strings, or null as URLs. If a real URL can't be found after 3 attempts, discard the item entirely.
