# Ticker Injection Pattern — `inject_wire_ticker.py`

## Injection targets

| Element | Injection point | Regex | Notes |
|---------|----------------|-------|-------|
| CSS | Before `</head>` | `re.sub(r'</head>', '<style>CSS</style></head>', ...)` | Production Lux uses `<link rel="stylesheet" href="style.css">` — NO inline `<style>` tag |
| Ticker HTML | After `</header>` | `re.sub(r'</header>', '</header>TICKER', ...)` | Between masthead and lead-zone |
| Modal HTML | Before `</body>` | `re.sub(r'</body>', 'MODAL</body>', ...)` | |
| JS | Before `</body>` | `re.sub(r'</body>', 'JS</body>', ...)` | |

## CSS variable alignment

The injected CSS uses the EXACT variables from `style.css`:

- `--ink`, `--type`, `--type-dim`, `--muted`
- `--lux`, `--lux-soft`, `--ember`
- `--rule`, `--rule-strong`
- `--serif`, `--sans`

Do NOT use shortened aliases (`--ru`, `--se`, `--sa`).

## data-b newline escaping

The `data-b` HTML attribute contains the article body with literal `\n` (backslash + n) instead of real newlines, because real newlines would break the HTML attribute.

**Python (building the HTML):**
```python
bd = html.escape(body).replace('\n', '\\n')
```
In Python, `'\\n'` produces a string with literal backslash + n.

**JavaScript (reading the HTML):**
```javascript
el.getAttribute('data-b').split('\\n').join('<br>')
```
In a JS string literal, `'\\n'` is backslash + n — matches the literal `\n` from the HTML attribute.

## AI signature parsing

The body field contains `*— Written by AI (model_name)*` as last line (em dash U+2014).
JS parses it with:
```javascript
var idx = b.indexOf('*— Written by AI (');
var model = b.substring(idx + aiSig.length).split(')')[0];
```

**Offset must be exactly `+ aiSig.length`** — don't add extra characters for
the space/paren the search string already includes. A past bug added `+3`
on top of a shorter search string (`'*— Written by AI'` without the
trailing `(`), which truncated the first character of the model name:

```javascript
// Correct:
var aiS='*— Written by AI (';
var i=b.indexOf(aiS);
var mdl=b.substring(i+aiS.length).split(')')[0];

// Wrong (truncates first letter of the model name):
var aiS='*— Written by AI';
var mdl=b.substring(i+aiS.length+3).split(')')[0];
```

## Operational pitfalls

- **Deploy dir may have stale uncommitted changes.** `~/ai-news-deploy/index.html`
  on disk may differ from `git HEAD:index.html` (overwritten by external
  tools/scripts). Before injecting, verify with `git show HEAD:index.html`
  or `git checkout HEAD -- index.html`. After injection, `git status`
  showing `M index.html` is the expected uncommitted change.
- **Duplicate injection from re-running.** The injector looks for
  `</header>` to insert the ticker. If the page already has a ticker from a
  previous injection, re-running adds a SECOND ticker after the same
  `</header>`. Always restore from a clean copy before re-injecting.
