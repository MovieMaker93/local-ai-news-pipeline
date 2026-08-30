# Wire Articles Scout — RSS + LLM Writing (Local AI News)

## Architecture

The wire-articles pattern adds a **new data-source type** to the pipeline: deterministic RSS retrieval + LLM article writing. Unlike the scouts (which use LLM-driven web search), this approach:

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
  ↓ resolve_url() — turn redirects into real URLs
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

See [`skills/wire-articles/SKILL.md`](../../wire-articles/SKILL.md#wire-articles-json-shape) for the shape — not duplicated here.

**AI disclosure requirement:** the `body` field MUST end with `\n*— Written by AI (<model_name>)*` where `<model_name>` matches the model used to generate it. This is enforced in `build_prompt()`, which reads `WIRE_MODEL` env var (default matches the pipeline model).

## Google News RSS Pitfall

The Google News RSS feed URL structure:

```
https://news.google.com/rss/search?q=(...)when%3A1d&hl=en-US&gl=US&ceid=US:en
```

Google uses **base64-encoded article tokens** in the URL path (`/articles/CBMimAF...`). `resolve_url()` decodes these:

```python
m = re.search(r'/articles/([A-Za-z0-9_\-]+)', url)
if m:
    token = m.group(1)
    raw = base64.urlsafe_b64decode(token + '=' * (-len(token) % 4))
    found = re.search(rb'https?://[^\x00-\x1f"\\\s]+', raw)
```

**When this breaks:** Google periodically changes the token encoding format. When it does, the base64 decode either fails or produces garbage. The HTTP redirect fallback catches some cases but is slower.

**Signs it broke:** the script fetches 50+ items but "0 items grounded with source text".

**Fix:** bypass Google News entirely by adding direct publisher RSS feeds. The list lives in `skills/_shared/sources.md`, under the `## Wire Articles (`wire-articles`)` section (not hardcoded in `wire_articles.py`).

## Scrolling Ticker CSS Architecture

The ticker uses the exact production CSS variables (`--ink`, `--type`, `--ember`, `--lux`, `--rule`, `--rule-strong`, `--muted`, `--serif`, `--sans`) — never custom color values. Fonts are Newsreader (serif) and Inter (sans).

**Position:** BETWEEN the masthead and the lead-zone (`<div class="lead-zone">`), not above the masthead.

**Structure (no-label variant — preferred):**
```html
<div class="wire-ticker">
  <div class="wire-ticker-track">{items_duplicated}</div>
</div>
```

**Label variant (when explicitly requested):** add a `.wire-ticker-label` div before the track.

The ticker uses a **pure CSS infinite scroll** with no JS. The HTML duplicates the items (`{ticker_html}` twice) so there's never a gap — seamless loop. At least 5 articles should populate the ticker.

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

When the article body contains `*— Written by AI (<model>)*`, the JS detects it via `indexOf()` (not regex) and renders it as a **visually distinct block** below the article.

**Design intent:** the AI disclosure is visually subordinate — smaller, sans-serif, muted, separated by a rule. The body text (Newsreader, serif) is the primary reading experience.

## Integration Points

### Into run.sh (DONE — step 6)
```bash
python3 "$WIRE_SCRIPT" --max 5 --out "$SCOUTS_DIR/scout_wire.json" \
    --profile "$PROFILE" \
    --model "$PIPELINE_MODEL" --provider "$PIPELINE_PROVIDER"
```
⚠️ `--profile "$PROFILE"` and `--provider "$PIPELINE_PROVIDER"` are passed explicitly rather than relying on `wire_articles.py`'s own defaults, so the subprocess lands on the same profile+backend as every other step. Observed 2026-08-27: without `--profile` it used the operator's DEFAULT profile (no `spark` provider), silently falling back to that profile's paid chain with fallback warnings pasted into the ticker.

The ticker is then injected into the rendered page by `inject_wire_ticker.py` (step 6b) — it is **not** part of `edition.json` and `render.py` knows nothing about it. Injection happens post-render, between the masthead and the lead-zone.

### Still open (not implemented)
- Editor-side selection: the editor could pick 3-5 wire articles and dedupe them against the main edition to avoid overlap. Today the ticker takes whatever `wire_articles.py` produced, independently of the edition.

## Files Reference

| File | Purpose |
|------|---------|
| `scripts/content/wire_articles.py` | RSS fetch + LLM write. Model: `flash` via `spark` (passed in from `run.sh`) |
| `scripts/inject/inject_wire_ticker.py` | Post-render injection of the ticker + modal into `index.html` |

## Pitfalls

### Google News URL resolution
The `resolve_url()` function in `wire_articles.py` tries two strategies... (see above)

### AI model disclosure is mandatory
The `build_prompt()` function appends `*— Written by AI (<model_name>)*` to every article. The model name comes from the `WIRE_MODEL` env var or the hardcoded default. Ensure the env var is set or the default matches the intended model.

### The ticker CSS never conflicts with production
It uses the **exact same CSS custom properties** as the production site. The only new CSS is the ticker layout classes (`.wire-ticker`, `.wi-item`, etc.) and the modal overlay — none of which conflict with production class names.

### JS regex inside Python f-strings causes SyntaxWarning
When JS regex patterns containing `\(`, `\)`, `\*`, or `\n` are embedded in Python f-strings, Python 3.12+ issues `SyntaxWarning: invalid escape sequence`.

**Fix:** avoid regex in JS code inside Python f-strings. Use simpler JS string methods instead. Alternatively, build the JS outside the f-string as a separate string and interpolate with `str.replace()` to avoid the escaping war entirely.

### CSS in Python f-strings needs doubled braces
All CSS `{ }` block delimiters inside an f-string must be `{{ }}`. Forgetting this causes `KeyError` or malformed CSS.
