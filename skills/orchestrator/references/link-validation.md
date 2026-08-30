# Post-Deploy Link Validation (Local AI News)

After each deploy, verify no `href="#"` (self-link) placeholders slipped through.

## Quick Check

```bash
cd ~/local-ai-news-deploy
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
| 403/404 | paywall, region block, or dead link | verify manually; if a real source, keep; else find a working URL |
| 301/308 | redirect | follow it; keep if the target resolves |
| TIMEOUT | slow/unreachable | retry once; drop if it consistently fails |
