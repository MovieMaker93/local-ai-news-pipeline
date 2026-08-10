# Wire Articles Scout — RSS + LLM Writing

## Architecture

The wire-articles pattern adds a **new data-source type** to the V2 pipeline: deterministic RSS retrieval + LLM article writing. Unlike the existing scouts (which use LLM-driven web/x_search), this approach:

1. **Fetches RSS deterministically** — pure Python, no LLM, same input → same output
2. **Filters by keyword** — `ALLOW`/`DENY` lists, not model judgment
3. **Grounds in source text** — downloads the actual article, extracts readable text
4. **Writes grounded articles** — one `hermes chat -q` call per item, tightly controlled prompt

## Two-Stage Separation

### Stage 1 (Deterministic — Pure Code)

```
FEEDS (list of RSS URLs)
  ↓ http_get() + parse_feed()
RAW ITEMS (title, summary, link, published, source)
  ↓ is_ai_relevant() — keyword gate
AI-RELEVANT ITEMS
  ↓ norm_title() dedup
DEDUPED ITEMS
  ↓ sort by published date (newest first)
TOP CANDIDATES (up to MAX_ITEMS)
  ↓ resolve_url() — turn Google redirects into real URLs
  ↓ fetch_article_text() — download + extract readable body
GROUNDED ITEMS (with source_text)
```

**Key property:** deterministic. Same RSS feeds, same time window, same selection. Can be dry-run with `--dry-run` to preview without LLM cost.

### Stage 2 (The Only LLM Call)

```
For each grounded item:
  build_prompt() — instructions + source text only
  call_hermes() — `hermes chat -q` with timeout
  write_article() — parse headline + body from output
  → structured JSON article
```

**Key property:** the model sees ONLY the source text + instructions. No context from conversation, no tool access, no prior items. Each call is independent and stateless.

## Wire Articles JSON Shape

```json
{
  "headline": "OpenAI Unveils o5 Reasoning Model",
  "body": "Full article text here...\n\n*Editorial note in italics*\n*— Written by AI (deepseek/deepseek-v4-flash)*",
  "source": "The Verge",
  "source_url": "https://www.theverge.com/...",
  "original_title": "Original RSS headline",
  "published": "Mon, 30 Jun 2025 14:00:00 GMT",
  "generated_at": "2025-06-30T14:30:00+00:00"
}
```

**AI disclosure requirement:** the `body` field MUST end with `\n*— Written by AI (<model_name>)*` where `<model_name>` matches the model used to generate it. This is enforced in the build_prompt() function, which reads `WIRE_MODEL` env var (default: `deepseek/deepseek-v4-flash`).

## Google News RSS Pitfall

The Google News RSS feed URL structure:

```
https://news.google.com/rss/search?q=(...)when%3A1d&hl=en-US&gl=US&ceid=US:en
```

Google uses **base64-encoded article tokens** in the URL path (`/articles/CBMimAF...`). The `resolve_url()` function decodes these:

```python
m = re.search(r'/articles/([A-Za-z0-9_\-]+)', url)
if m:
    token = m.group(1)
    raw = base64.urlsafe_b64decode(token + '=' * (-len(token) % 4))
    found = re.search(rb'https?://[^\x00-\x1f"\\\s]+', raw)
```

**When this breaks:** Google periodically changes the token encoding format. When it does, the base64 decode either fails or produces garbage. The HTTP redirect fallback catches some cases but is slower.

**Signs it broke:** the script fetches 50+ items but "0 items grounded with source text".

**Fix:** bypass Google News entirely by adding direct publisher RSS feeds to the `FEEDS` array:

```python
FEEDS = [
    'https://www.marktechpost.com/feed/',
    'https://techcrunch.com/feed/',
    'https://www.wired.com/feed/rss',
    'https://arstechnica.com/feed/',
    # Google News as fallback only
    'https://news.google.com/rss/search?...',
]
```

## Test Renderer Pattern

`render_wire_test.py` follows the same stdout-JSON convention as the production `render.py`:

```python
print(json.dumps({'status': 'ok', 'output': '/tmp/v2/test-wire/index.html'}))
```

This means it can be called from bash and the orchestrator can check `$?` and parse the JSON status line.

### Scrolling Ticker CSS Architecture

The ticker uses the **exact production Lux in Tenebris CSS variables** (`--ink`, `--type`, `--ember`, `--lux`, `--rule`, `--rule-strong`, `--muted`, `--serif`, `--sans`) — never custom color values. Fonts are Newsreader (serif) and Inter (sans), copied from `~/ai-news-deploy/fonts/` for self-containment.

**Position:** BETWEEN the masthead and the lead-zone (`<div class="lead-zone">`), not above the masthead. The production layout puts the ticker right before the lead story image.

**Structure (no-label variant — preferred):**
```html
<div class="wire-ticker">
  <div class="wire-ticker-track">{items_duplicated}</div>
</div>
```

**Label variant (when explicitly requested):** add a `.wire-ticker-label` div before the track.

Luke prefers the **no-label** variant — just scrolling headlines.

The ticker uses a **pure CSS infinite scroll** with no JS:
```css
.wire-ticker {
    background: var(--ink);
    border-top: 1px solid var(--rule-strong);
    border-bottom: 1px solid var(--rule);
    height: 38px;
    overflow: hidden;
}
.wire-ticker-label {
    background: var(--ember);        /* production hot accent */
    color: #fff;
    font-family: var(--sans);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: .18em;
}
.wire-ticker-track {
    white-space: nowrap;
    animation: wireScroll 90s linear infinite;
    will-change: transform;
}
@keyframes wireScroll {
    0%   { transform: translateX(0); }
    100% { transform: translateX(-50%); }
}
.wire-ticker-track:hover {
    animation-play-state: paused;
}
```

The HTML duplicates the items (`{ticker_html}` twice) so there's never a gap — seamless loop. At least 5 articles should populate the ticker.

**Item style:**
```css
.wi-item {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 0 22px;
    cursor: pointer;
    border-right: 1px solid var(--rule);
    height: 38px;
}
.wi-hl { font-family: var(--serif); font-size: 13px; color: var(--type); }
.wi-src { font-family: var(--sans); font-size: 9.5px; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; }
```

### Modal Overlay Pattern

Pure JS, no dependencies. Data lives in HTML attributes:

```html
<div class="ticker-item"
     onclick="openArticle(this)"
     data-headline="..."
     data-body="..."
     data-source="..."
     data-url="...">
```

Click → populates modal, adds `.active` class to overlay. ESC or click outside to close.

### AI Signature Styling

When the article body contains `*— Written by AI (<model>)*`, the JS detects it via `indexOf()` (not regex) and renders it as a **visually distinct block** below the article:

```html
<div class="as">
  <span class="al">⬥ AI-GENERATED</span><br>
  Model: deepseek/deepseek-v4-flash
</div>
```

CSS:
```css
.mbd .as {
  display: block; margin-top: 18px; padding-top: 14px;
  border-top: 1px solid var(--ru);               /* rule separator */
  font-family: var(--sa);                         /* Inter (sans-serif) — distinct from body */
  font-size: 11px; color: var(--mu);              /* muted color — de-emphasised */
}
.mbd .as .al {
  color: var(--ls);                               /* lux-soft amber accent */
  font-weight: 600; font-family: var(--sa);
  font-size: 10px; letter-spacing: .06em;
  text-transform: uppercase;
}
```

**Design intent:** the AI disclosure is visually subordinate — smaller, sans-serif, muted, separated by a rule. The body text (Newsreader, serif, 16.5px) is the primary reading experience. The signature is there for transparency without competing for attention.

## Integration Points

### Into run_v2.sh (DONE — step 8)
```bash
python3 "$WIRE_SCRIPT" --max 5 --out "$SCOUTS_DIR/scout_wire.json" \
    --model deepseek-v4-flash --provider "$PIPELINE_PROVIDER"
```
⚠️ `$PIPELINE_PROVIDER` is `localAIServer`, never `openrouter`. It's passed explicitly
here rather than relying on `wire_articles.py`'s own defaults so the backend is
decided in exactly one place for the whole pipeline.

The ticker is then injected into the rendered page by `inject_wire_ticker.py`
(step 8b) — it is **not** part of `edition.json` and `render.py` knows nothing
about it. Injection happens post-render, between the masthead and the
lead-zone.

### Still open (not implemented)
- Editor-side selection: the editor could pick 3-5 wire articles and dedupe
  them against the main edition to avoid overlap. Today the ticker takes
  whatever `wire_articles.py` produced, independently of the edition.

## Files Reference

| File | Purpose |
|------|---------|
| `~/.hermes/profiles/luke/scripts/v2/wire_articles.py` | RSS fetch + LLM write. Model: `deepseek-v4-flash` via `localAIServer` (passed in from `run_v2.sh`) |
| `~/.hermes/profiles/luke/scripts/v2/render_wire_test.py` | Test renderer (ticker + modal). Copies fonts from `~/ai-news-deploy/fonts/` for self-containment |
| `~/.hermes/profiles/luke/scripts/v2/test_wire_pipeline.sh` | Full test pipeline: wire_articles.py → render_wire_test.py |
| `/tmp/v2/test-wire/` | Test output directory (no deploy) |

## Pitfalls

### Google News URL resolution
The `resolve_url()` function in `wire_articles.py` tries two strategies... (see above)

### Fonts must exist for test page
`render_wire_test.py` copies fonts from `/home/nttluke/ai-news-deploy/fonts/` to the test output directory. If the production deploy dir doesn't have fonts (fresh clone), the test page renders with system fallbacks (Georgia + system sans-serif) — still functional but slightly different look.

### AI model disclosure is mandatory
The `build_prompt()` function appends `*— Written by AI (<model_name>)*` to every article. The model name comes from the `WIRE_MODEL` env var or the hardcoded default `deepseek/deepseek-v4-flash`. When running outside the test pipeline, ensure the env var is set or the default matches the intended model.

### Test renderer adds no new styles to production
The ticker CSS uses the **exact same CSS custom properties** as the production site. The only new CSS is the ticker layout classes (`.wire-ticker`, `.wi-item`, etc.) and the modal overlay — none of which conflict with production class names.

### JS regex inside Python f-strings causes SyntaxWarning
When JS regex patterns containing `\(`, `\)`, `\*`, or `\n` are embedded in Python f-strings, Python 3.12+ issues `SyntaxWarning: invalid escape sequence`. The f-string interprets `\\\(` etc. as invalid Python escapes.

**Fix:** avoid regex in JS code inside Python f-strings. Use simpler JS string methods instead:
```javascript
// BAD — Python SyntaxWarning:
body.replace(/\n/g, '<br>')
aiPart.replace(/^\*— Written by AI \((.*)\)\*$/gm, 'Model: $1')

// GOOD — no regex:
body.split('\n').join('<br>')
aiPart.substring(0, idx) + 'Model: ' + modelName
```

Alternatively, build the JS outside the f-string as a separate string and interpolate with `str.replace()` post-processing to avoid the escaping war entirely.

### CSS in Python f-strings needs doubled braces
All CSS `{ }` block delimiters inside an f-string must be `{{ }}`. Forgetting this causes `KeyError` or malformed CSS. Single `{ }` are only used for actual f-string variables (`{len(articles)}`, `{dh}`, etc.).