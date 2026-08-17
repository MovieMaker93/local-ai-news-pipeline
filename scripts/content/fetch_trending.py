#!/usr/bin/env python3
"""
fetch_trending.py — Fetch GitHub and HuggingFace trending.
Outputs JSON matching the scout-opensource trending contract.

Usage:
    python3 fetch_trending.py [--output-json PATH]

Strategy (2026-08-17):
- GitHub  : parse the /trending HTML with a whitespace-tolerant regex.
            No bs4 dependency. Handles the current markup where a
            data-hmac span sits BETWEEN <h2> and <a>, and where tags are
            spread across multiple lines.
- Hugging Face: use the OFFICIAL REST API (the /models page is
            client-rendered via JS, so curl on the HTML gives nothing).
            sort=trendingScore returns the same "Trending on HF" list.
"""
import json
import re
import subprocess
import sys
from datetime import date


def curl(url: str, timeout: int = 30) -> str | None:
    """Fetch a URL via curl. Returns None on failure."""
    try:
        result = subprocess.run(
            ["curl", "-sSL", "--max-time", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 10
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
        return None
    except (subprocess.TimeoutExpired, OSError):
        return None


def curl_json(url: str, timeout: int = 30):
    """Fetch a URL via curl and parse as JSON. Returns None on failure."""
    raw = curl(url, timeout)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _num(s: str) -> str:
    """Normalize a star/download counter ('1,945,635' / '4.1k') to a plain 'N' string."""
    s = s.strip()
    s = s.replace(",", "")
    if not s:
        return ""
    return s


def fetch_github_trending() -> list:
    """Fetch GitHub Trending repos. Whitespace-tolerant regex, no bs4."""
    html = curl("https://github.com/trending")
    if not html:
        return []

    # Latest markup (2026-08): one <article class="Box-row"> per repo.
    # Inside each: <h2 class="h3 lh-condensed"> ... <a href="/user/repo" data-hmac="...">…
    # The <a> may be separated from <h2> by newlines AND a data-hmac attribute.
    # So match the h2 header block broadly and pull href + text from within it.
    articles = re.split(r'<article class="Box-row">', html)[1:]

    repos = []
    seen = set()
    for art in articles:
        # The real repo link lives inside the h2 header block.
        # Tolerate: arbitrary whitespace/newlines between <h2> and <a>.
        # The <a> text may contain nested <svg> content — so take the repo
        # name from the href itself, not from the anchor's inner text.
        m = re.search(
            r'<h[23][^>]*>.*?href="/([\w.-]+/[\w.-]+)"',
            art, re.DOTALL
        )
        if not m:
            continue
        href = m.group(1).strip()
        # Skip auxiliary links (sponsors pages, sub-paths, etc.)
        if href.count("/") != 1 or href.startswith(("sponsors/", "settings/", "pulls")):
            continue
        if href in seen:
            continue
        seen.add(href)

        # Language
        lang = ""
        lm = re.search(r'itemprop="programmingLanguage">([^<]+)<', art)
        if lm:
            lang = lm.group(1).strip()

        # Star count (from the /stargazers link)
        stars = ""
        sm = re.search(r'href="/[^"]*/stargazers"[^>]*>\s*([\d,.]+)', art)
        if sm:
            stars = _num(sm.group(1))

        meta = " · ".join(p for p in (lang, (stars + " ★") if stars else "") if p)
        repos.append({
            "name": href,
            "url": f"https://github.com/{href}",
            "meta": meta,
        })

    return repos[:15]


def fetch_huggingface_trending() -> list:
    """Fetch HuggingFace trending models via the official REST API."""
    # The /models HTML is client-rendered (JS), so HTML parsing yields nothing.
    # The backend API supports sort=trendingScore — the same trending signal.
    data = curl_json("https://huggingface.co/api/models?sort=trendingScore&limit=15&direction=-1")
    if not isinstance(data, list):
        return []

    models = []
    for m in data:
        if not isinstance(m, dict):
            continue
        mid = m.get("id")
        if not mid or "/" not in mid:
            continue
        downloads = m.get("downloads", 0)
        likes = m.get("likes", 0)
        meta = " · ".join(p for p in (
            (f"{int(downloads):,} downloads") if downloads else "",
            (f"{int(likes):,} likes") if likes else "",
        ) if p)
        models.append({
            "name": mid,
            "url": f"https://huggingface.co/{mid}",
            "meta": meta,
        })
    return models[:10]


def main():
    today = date.today().isoformat()

    print("[fetch_trending] Fetching GitHub Trending...", file=sys.stderr)
    github = fetch_github_trending()
    print(f"[fetch_trending] GitHub: {len(github)} repos", file=sys.stderr)

    print("[fetch_trending] Fetching HuggingFace Trending...", file=sys.stderr)
    huggingface = fetch_huggingface_trending()
    print(f"[fetch_trending] HuggingFace: {len(huggingface)} models", file=sys.stderr)

    result = {
        "trending": {
            "github": {
                "title": "GitHub Trending",
                "url": "https://github.com/trending",
                "link_label": "github.com/trending",
                "date": today,
                "items": github
            },
            "huggingface": {
                "title": "Models Trending (Hugging Face)",
                "url": "https://huggingface.co/models?sort=trending",
                "link_label": "huggingface.co/models",
                "date": today,
                "items": huggingface
            }
        }
    }

    output_json = json.dumps(result, indent=2)

    if len(sys.argv) > 2 and sys.argv[1] == "--output-json":
        outpath = sys.argv[2]
        with open(outpath, "w") as f:
            f.write(output_json)
        print(f"[fetch_trending] Written to {outpath}", file=sys.stderr)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
