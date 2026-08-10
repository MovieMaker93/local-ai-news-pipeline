---
name: scout-x
description: "V2 scout: X/Twitter AI news. Returns JSON array of candidates."
---

# Scout V2 — X/Twitter

## When to use
Called by orchestrator during the daily pipeline. Can also be run standalone for testing.

## Output contract
Return ONLY a JSON array (no prose, no fences). Each element:
```json
{"title":"…","summary":"1–2 factual sentences","source":"Handle or name",
 "url":"https://x.com/…","date":"YYYY-MM-DD","beat":"x","signal":1-5}
```

## Queries
Use `x_search` with EXPLICIT from_date/to_date (never `since:` in query):

**Pass 1 — Tech:**
```
(AI OR LLM OR "AI agent" OR "open source model") (release OR launch OR paper OR breakthrough)
```
from_date: <yesterday>, to_date: <today>
allowed_x_handles: ["OpenAI","AnthropicAI","GoogleDeepMind","xai","NousResearch","sama","karpathy","huggingface","DeepLearningAI","ylecun","simonw","swyx","_philschmid","omarsar0","_akhaliq","lmsysorg"]

**Pass 2 — Business:**
```
(AI OR "artificial intelligence") (company OR startup OR funding OR regulation OR layoff OR acquisition)
```
Same handles and dates.

## 🔴 FALLBACK — when x_search and web tools fail

If `x_search` is unavailable (no OAuth) AND `web_search`/`web_extract` fail for
**any** reason — rate limiting, `ddgs` missing/broken, network error, timeout,
or "Payment Required". Don't wait specifically for a credit error: the extract
backend is `ddgs` now, so that message may never appear.

⚠️ Both commands below build the query from **today's date**, passed in the
prompt. Substitute it — do not paste a hardcoded month/year, or the fallback
will keep searching for a date in the past forever.

1. **Search X via DuckDuckGo (site-scoped):**
```bash
# replace <MONTH> <YEAR> with today's, e.g. "July 2026"
curl -sL "https://html.duckduckgo.com/html/?q=site%3Ax.com+AI+<MONTH>+<YEAR>" | python3 -c "
import sys, re; html = sys.stdin.read()
for m in re.findall(r'<a[^>]*class=\"result__a\"[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>', html, re.DOTALL):
    u = m[0]; t = re.sub(r'<[^>]+>', '', m[1]).strip()
    print(f'{t} | {u}')
" 2>/dev/null | head -20
```

2. **Search via Bing (free):**
```bash
# replace <YEAR> with today's year
curl -sL "https://www.bing.com/search?q=site%3Ax.com+AI+news+<YEAR>" | python3 -c "
import sys, re; html = sys.stdin.read()
for m in re.findall(r'<h2><a[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a></h2>', html, re.DOTALL):
    u = m[0]; t = re.sub(r'<[^>]+>', '', m[1]).strip()
    print(f'{t} | {u}')
" 2>/dev/null | head -20
```

3. If ALL fallbacks fail, return `[]`.

## Rules
- Every `url` MUST come from a real x_search result permalink. Never synthesize URLs.
- `signal`: 5=field-shifting, 1=minor. Honest assessment.
- Only items dated within [yesterday, today].
- Deduplicate within your list.
- Return `[]` if nothing found. Never return prose.
- All content in ENGLISH.

## Link-Source Validation (MANDATORY — run before writing final JSON)

After gathering all items but BEFORE writing the final JSON, validate EVERY item:

1. **Real permalink check:** Every URL MUST be a real `x_search` result permalink starting with `https://x.com/`. Never synthesize or reconstruct URLs from text snippets.

2. **Auto-fix on mismatch (max 3 attempts per item):** If a URL is not a real X permalink, use `x_search` with the post's key content to find the correct permalink.

3. **Discard unfixable items:** After 3 failed attempts, REMOVE the item from your array. Do NOT keep items with broken or synthetic URLs.

4. **No placeholder URLs:** Never use "#", empty strings, or null.
