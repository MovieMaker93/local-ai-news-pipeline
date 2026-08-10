#!/usr/bin/env python3
"""
fetch_trending.py — Fetch GitHub and HuggingFace trending via curl (no Firecrawl).
Outputs JSON matching the scout-opensource trending contract.

Usage:
    python3 fetch_trending.py [--output-json PATH]
    
If --output-json is provided, writes the JSON to that file.
Otherwise prints to stdout.
"""
import json
import os
import re
import subprocess
import sys
from datetime import date
from html.parser import HTMLParser


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


# ── GitHub Trending Parser ──────────────────────────────────────

class GitHubTrendingParser(HTMLParser):
    """Parse GitHub Trending page for repo name, language, stars, today-stars."""
    def __init__(self):
        super().__init__()
        self.items = []
        self._in_article = False
        self._in_h2 = False
        self._in_h3 = False
        self._in_lang = False
        self._in_stars = False
        self._in_today = False
        self._repo_name = ""
        self._lang = ""
        self._stars = ""
        self._today_stars = ""
        self._tag_stack = []
        self._skip_article = False

    def _current_tag(self):
        return self._tag_stack[-1] if self._tag_stack else ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self._tag_stack.append(tag)

        if tag == "article" and "class" in attrs_dict:
            classes = attrs_dict["class"].split()
            if any(c.startswith("Box-row") for c in classes):
                self._in_article = True
                self._repo_name = ""
                self._lang = ""
                self._stars = ""
                self._today_stars = ""
                self._skip_article = False

        if self._in_article:
            if tag == "h2":
                self._in_h2 = True
            elif tag == "h3":
                self._in_h3 = True
            elif tag == "span" and "itemprop" in attrs_dict and attrs_dict["itemprop"] == "programmingLanguage":
                self._in_lang = True
            elif tag == "a" and "class" in attrs_dict and "Link" in attrs_dict.get("class", ""):
                href = attrs_dict.get("href", "")
                if "/stargazers" in href:
                    self._in_stars = True
                else:
                    self._in_h3 = True

    def handle_data(self, data):
        if self._in_article:
            stripped = data.strip()
            if not stripped:
                return
            if self._in_h2 or self._in_h3:
                # Check if it looks like a repo name (user/repo)
                if "/" in stripped and len(stripped) < 60:
                    self._repo_name = stripped.strip()
                self._in_h2 = False
                self._in_h3 = False
            elif self._in_lang:
                self._lang = stripped.strip()
                self._in_lang = False
            elif self._in_stars:
                self._stars = stripped.strip().replace(",", "")
                self._in_stars = False

    def handle_endtag(self, tag):
        if self._tag_stack:
            self._tag_stack.pop()
        if tag == "article" and self._in_article:
            self._in_article = False
            if self._repo_name and "/" in self._repo_name:
                meta_parts = []
                if self._lang:
                    meta_parts.append(self._lang)
                if self._stars:
                    self._stars = self._stars.replace(",", "").strip()
                    try:
                        stars_k = int(float(self._stars))
                        meta_parts.append(f"{stars_k:,} ★")
                    except ValueError:
                        pass
                if self._today_stars:
                    meta_parts.append(f"+{self._today_stars.strip()} today")
                self.items.append({
                    "name": self._repo_name.strip(),
                    "url": f"https://github.com/{self._repo_name.strip()}",
                    "meta": " · ".join(meta_parts) if meta_parts else ""
                })


def fetch_github_trending() -> list:
    """Fetch GitHub Trending repos via curl."""
    html = curl("https://github.com/trending")
    if not html:
        return []

    # First try: find all h2/h3 with repo links
    repos = []
    # Pattern: <h2><a href="/user/repo">user/repo</a></h2>
    # Or: <h3><a href="/user/repo">user/repo</a></h3>
    patterns = [
        r'<h[23]>\s*<a\s+href="/([^"]+)"[^>]*>([^<]+)</a>',
        r'data-hpc\s*[^>]*>\s*<a\s+href="/([^"]+)"[^>]*>([^<]+)</a>',
        r'<article[^>]*>.*?<h[23]>\s*<a\s+href="/([^"]+)"[^>]*>\s*([^<]+?)\s*</a>',
    ]
    
    for pattern in patterns:
        found = re.findall(pattern, html, re.DOTALL)
        if found:
            for href, name in found:
                name = name.strip()
                if "/" in name and name not in [r["name"] for r in repos]:
                    repos.append({"name": name, "url": f"https://github.com/{name}"})
            if len(repos) >= 5:
                break

    # Fallback: try a simpler approach with BeautifulSoup
    if len(repos) < 5:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            articles = soup.find_all("article")
            repos = []
            for art in articles:
                h2 = art.find("h2")
                h3 = art.find("h3")
                header = h2 or h3
                if header:
                    a = header.find("a")
                    if a and a.get("href"):
                        href = a["href"].strip("/")
                        if "/" in href:
                            # Get language
                            lang_span = art.find("span", itemprop="programmingLanguage")
                            lang = lang_span.get_text(strip=True) if lang_span else ""
                            # Get stars
                            star_links = art.find_all("a", href=lambda h: h and "/stargazers" in h)
                            stars = ""
                            if star_links:
                                star_text = star_links[0].get_text(strip=True)
                                stars = star_text.replace(",", "").strip()
                            meta_parts = []
                            if lang:
                                meta_parts.append(lang)
                            if stars:
                                try:
                                    stars_k = int(float(stars))
                                    meta_parts.append(f"{stars_k:,} ★")
                                except ValueError:
                                    pass
                            repos.append({
                                "name": href,
                                "url": f"https://github.com/{href}",
                                "meta": " · ".join(meta_parts) if meta_parts else ""
                            })
        except ImportError:
            pass

    return repos[:15]


# ── HuggingFace Trending Parser ─────────────────────────────────

def fetch_huggingface_trending() -> list:
    """Fetch HuggingFace trending models via curl."""
    html = curl("https://huggingface.co/models?sort=trending")
    if not html:
        return []

    models = []
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        
        # Look for model cards/links
        # Pattern 1: article tags with model links
        articles = soup.find_all("article")
        for art in articles:
            a = art.find("a", href=lambda h: h and h.startswith("/") and not h.startswith("/?") and not h.startswith("#"))
            if a:
                href = a["href"].strip("/")
                if "/" in href and not href.endswith("/tree/main") and not href.endswith("/resolve/main"):
                    # Get description
                    desc = ""
                    for p in art.find_all(["p", "div"]):
                        text = p.get_text(strip=True)
                        if len(text) > 10 and len(text) < 200:
                            desc = text
                            break
                    models.append({
                        "name": href,
                        "url": f"https://huggingface.co/{href}",
                        "meta": desc[:120] if desc else ""
                    })
        
        # If no articles found, try div-based layout
        if not models:
            for a in soup.find_all("a", href=re.compile(r"^/[^/]+/[^/]+$")):
                href = a["href"].strip("/")
                if href not in [m["name"] for m in models]:
                    parent = a.find_parent(["div", "article"])
                    desc = ""
                    if parent:
                        for p_tag in parent.find_all(["p", "div"]):
                            text = p_tag.get_text(strip=True)
                            if 10 < len(text) < 200:
                                desc = text
                                break
                    models.append({
                        "name": href,
                        "url": f"https://huggingface.co/{href}",
                        "meta": desc[:120] if desc else ""
                    })
    except ImportError:
        # Fallback: regex-based extraction
        pattern = r'<a[^>]*href="/([^"]+/[^"]+)"[^>]*>([^<]+)</a>'
        found = re.findall(pattern, html)
        seen = set()
        for href, text in found:
            if "/" in href and href not in seen:
                seen.add(href)
                models.append({
                    "name": href,
                    "url": f"https://huggingface.co/{href}",
                    "meta": ""
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