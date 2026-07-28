---
name: lux-v2-domain
description: "Lux in Tenebris custom domain setup (luxintenebris.news), Cloudflare DNS proxy, GitHub Pages configuration, and post-deploy pitfalls."
---

# Lux V2 — Custom Domain Operations

## Purpose
Runtime knowledge for the Lux in Tenebris V2 custom domain `luxintenebris.news`, Cloudflare DNS configuration, and post-deploy troubleshooting.

## Live URLs

| Edition | URL |
|---------|-----|
| **DS edition** | `https://luxintenebris.news/` |
| **Archive** | `https://luxintenebris.news/archive/` |
| **Legacy (redirects)** | `https://nttluke.github.io/luxintenebris-ai-news/` |

## Cloudflare DNS Setup

- **Domain:** `luxintenebris.news` (registered via Cloudflare Registrar)
- **Record:** CNAME `@` → `nttluke.github.io`
- **Proxy:** Orange cloud (proxied) for CDN caching + DDoS protection
  - With proxy ON: GitHub Pages shows "improperly configured" warning — this is a false alarm, GitHub sees Cloudflare IPs instead of GitHub Pages IPs. Site works fine.
  - Switch to gray cloud (DNS only) temporarily if GitHub Pages needs to validate the domain for SSL cert issuance.
- **SSL/TLS mode:** Full (strict) — Cloudflare edge cert for browser, GitHub Pages cert for origin

## New Utility Scripts

### `fetch_trending.py`
- **Path:** `~/.hermes/profiles/luke/scripts/v2/fetch_trending.py`
- Fetches GitHub Trending (15 repos) + HuggingFace Trending (10 models) via **curl** (bypasses Firecrawl/Tavily)
- Used as auto-fallback in `run_v2.sh` phase 2 when opensource scout fails
- Manual re-run: `python3 ~/.hermes/profiles/luke/scripts/v2/fetch_trending.py --output-json /tmp/v2/scouts/scout_opensource.json`

### `fix_archive_issue_numbers.py`
- **Path:** `~/.hermes/profiles/luke/scripts/v2/fix_archive_issue_numbers.py`
- Fixes incorrect issue numbers in archived HTML files and regenerates the archive listing
- Sets `.issue` to the correct value for the next pipeline run

## Pitfalls

1. **Issue number stuck at same value** — The `.issue` write MUST happen AFTER `git reset --hard origin/main` (step 9 in run_v2.sh). If before, the reset reverts `$DEPLOY_DIR/.issue` to the committed value. Fixed 2026-07-24.

2. **Trending fallback triggers** — The opensource scout (`scout-v2-opensource`) uses `web_extract` (Firecrawl) which can fail with `Connection error`. The auto-fallback in `run_v2.sh` calls `fetch_trending.py` via curl when trending data has <3 items.

3. **Rogue files in deploy dir** — `git add -A` picks up ANY untracked file (e.g. `general.html`, `technical.html` from tests). A smaller file can replace the real `index.html` when committed. Always check `ls -la` for stray files before `git add -A`. Last seen 2026-07-24.

4. **GitHub Pages cache (Fastly)** — After pushing, GitHub Pages CDN caches for `max-age=600` (10 min). A fresh deploy shows `age: 0`, `last-modified` updated. Force-refresh or wait for cache expiry.

5. **GitHub Pages "improperly configured"** — With Cloudflare proxy ON (orange cloud), GitHub Pages sees Cloudflare IPs and warns the DNS is misconfigured. This is a false alarm — the site works. To silence it, switch to gray cloud (DNS only) temporarily.

6. **Old URL still redirects** — `https://nttluke.github.io/luxintenebris-ai-news/` returns 301 → `http://luxintenebris.news/` (or HTTPS). Legacy bookmarks still work.