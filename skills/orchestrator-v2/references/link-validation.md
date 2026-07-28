# Post-Deploy Link Validation

After each deploy, verify no `href="#"` (self-link) placeholders slipped through.

## Quick Check

```bash
cd ~/luxintenebris-ai-news
grep -c 'href="#"' *.html
```

Count > 0 means articles with missing source URLs. Inspect:

```bash
grep -n 'href="#' *.html
```

## Full Batch Check — HTTP Status per Link

Extract every external URL, then verify in bulk:

```bash
# 1. Extract all href URLs
grep -roPh 'href="(https?://[^"]+)"' --include="*.html" . | \
  sed 's/href="//;s/"//' | sort -u > /tmp/all_links.txt

# 2. Check HTTP status for each (sequential loop — one request at a time)
while IFS= read -r url; do
  code=$(curl -s -o /dev/null -w "%{http_code}" \
    --max-time 10 --connect-timeout 5 "$url" 2>/dev/null || echo "TIMEOUT")
  echo "$code|$url"
done < /tmp/all_links.txt > /tmp/link_status.txt

# 3. Find problems (non-200, non-redirect)
grep -v '^200|' /tmp/link_status.txt | grep -v '^30[0-9]|'
```

## Common False Positives

| Status | Meaning | Action |
|--------|---------|--------|
| `403` | Bot block (Fortune, Medium, ProductHunt, CNBC) | Link works in browser. Ignore. |
| `301`/`302`/`307`/`308` | Redirect | Fine — curl without `-L` sees them. Ignore. |
| `000` | Connection timeout / DNS fail | Site may be temporarily down. Re-check later. |
| `404` | Genuinely broken | URL is dead or malformed. Fix in editor. |
| `href="#"` | Self-link (no source URL) | Root cause: editor left URL empty or `#`. Fix in editor-v2 step 7, re-render, re-deploy. |

## Finding the Correct URL

When a link turns out broken (404/timeout) or is `href="#"`, find the real URL:

1. **Search by exact title** — the article title is unique enough:
   ```bash
   # Use web_search with quoted title
   ```
   Wrap the full article title in quotes and add `arxiv` or the source domain.

2. **For arXiv papers** — search format `arxiv "Exact Title" 2026` usually returns the correct `arxiv.org/abs/26XX.XXXXX` on first hit.

3. **For HuggingFace papers** — same as arXiv but use `huggingface.co/papers/26XX.XXXXX`.

4. **For Product Hunt** — search `"product name" "Product Hunt" 2026` — Product Hunt blocks curl (403), so verify the URL renders in a browser.

5. **False positive: URL with `...` in appearance** — the terminal display truncates long lines with `...` but the actual file content is correct. Always verify with:
   ```bash
   python3 -c "
   with open('file.html', 'rb') as f:
       idx = f.read().find(b'sk-hyn')
       f.seek(idx)
       print(f.read(80))
   "
   ```
   This extracts raw bytes, eliminating display truncation artifacts.

## Bulk Patching

Once you have correct URLs for all broken links, fix them all at once:

```python
import re

fixes = [
    # (filename, old_string, new_string)
    ("index.html", 'href="#" ... unique context ...', 'href="https://..." ... same context ...'),
]

for fname, old, new in fixes:
    with open(fname, 'r') as f:
        content = f.read()
    content = content.replace(old, new, 1)
    with open(fname, 'w') as f:
        f.write(content)
```

Use **unique surrounding context** (include headline text, class names, span content) to ensure each match is unambiguous. Always set count=1 in replace() to avoid over-matching.

After patching, verify:
```bash
grep -c 'href="#"' *.html     # should be 0
```

## Post-Push Verification

After commit + push to GitHub Pages:
```bash
# Verify a few fixed URLs respond 200
curl -s -o /dev/null -w "%{http_code}" --max-time 8 "https://fixed-url.com"
```

Wait for GitHub Pages deploy (~1-2 min), then load the site and confirm the page renders with the correct links. Check the live site's extracted content with `web_extract`.

## When to Fix

Run this **before** deploy in the pipeline, or as a post-deploy QA check. If `href="#"` count > 0, the editor missed some — fix at the JSON source, re-render, then push again.

## Pipeline Integration

Add to `run_v2.sh` as a post-render step:

```bash
echo "=== Link validation ==="
cd ~/ai-news-deploy
broken=$(grep -c 'href="#' *.html 2>/dev/null || echo 0)
if [ "$broken" -gt 0 ]; then
  echo "WARNING: $broken self-links found. Editor step 7 may need attention."
fi
```
