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
