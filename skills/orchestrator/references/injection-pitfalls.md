# Wire Ticker Injection Pitfalls

## HTML data-b attribute: newlines break parsing
Ticker items store article body in `data-b`. The body contains `\n` newlines. Writing these directly into the HTML attribute value breaks HTML parsing because attributes cannot span multiple lines.

**Fix:** Replace `\n` with literal `\\n` before embedding in the attribute:
```python
b = H(body).replace('\n', '\\n')
```

## CSS variables must match production names
The production `style.css` defines:
- `--rule` NOT `--ru`
- `--serif` NOT `--se`
- `--sans` NOT `--sa`
- `--muted` NOT `--mu`
- `--type-dim` NOT `--td`
- `--lux-soft` NOT `--ls`
- `--rule-strong` NOT `--rs`

When injecting CSS into the production page, use the EXACT production variable names — the test page CSS may have used shortened aliases that don't exist in production.

## injection regex targets
- **CSS injection:** production Lux uses `<link rel="stylesheet" href="style.css">` NOT inline `<style>`. Target `</head>` not `</style>`.
- **Ticker position:** insert after `</header>`, which is immediately before `<div class="lead-zone">`.
- **Modal + JS:** insert before `</body>`.

## Model name truncation in AI signature
The body contains `*— Written by AI (deepseek/deepseek-v4-flash)*`. The JS extracts the model name by finding `'*— Written by AI ('` then splitting on `)`. The offset after the search string must be exactly `+ aiS.length` to point at the first character of the model name — don't add extra offset for the space/paren that `aiS` already includes.

**Correct:**
```javascript
var aiS='*\u2014 Written by AI (';
var i=b.indexOf(aiS);
var mdl=b.substring(i+aiS.length).split(')')[0];
```

**Wrong** (truncates first letter):
```javascript
var aiS='*\u2014 Written by AI';
var mdl=b.substring(i+aiS.length+3).split(')')[0];
// +3 skips \u2014 Written by AI (+3 chars beyond match) which includes the first char of the model
```

## Deploy dir may have stale uncommitted changes
`~/ai-news-deploy/index.html` on disk may differ from `git HEAD:index.html` (overwritten by external tools/scripts). Before injecting, verify with `git show HEAD:index.html` or `git checkout HEAD -- index.html`. After injection, `git status` will show `M index.html` — this is the expected uncommitted change.

## Duplicate injection from re-running
The injector looks for `</header>` to insert the ticker. If the page already has a ticker from a previous injection, re-running adds a SECOND ticker after the same `</header>`. Always restore from a clean copy before re-injecting.
