#!/usr/bin/env python3
"""archive_issue.py — Archive the current issue before deploy.

Creates a self-contained snapshot of the current edition in archive/YYYY-MM-DD/
and regenerates the archive index page.

Usage:
    python3 archive_issue.py <deploy-dir>

What it does:
    1. Reads issue_no + date from the current index.html
    2. Saves a complete self-contained copy to archive/YYYY-MM-DD/:
       - index.html  (frozen snapshot of the issue)
       - style.css
       - fonts/
       - images/
    3. Regenerates archive/index.html with the chronological listing
"""

import sys
import os
import re
import json
import shutil
from datetime import datetime
from pathlib import Path


# ── Archive URL paths (hosted on GitHub Pages via luxintenebris.news) ──
ARCHIVE_URL = "/archive/"
HOME_URL = "/"

# Shared reference patterns: an asset is only ever copied/kept if some HTML
# page actually links to it. Prevents images/podcasts from accumulating
# forever in the deploy root and in every archive snapshot (see
# extract_referenced_images / extract_referenced_audio).
IMAGE_SRC_RE = re.compile(r'src="(images/[^"]+\.(?:jpg|jpeg|png|webp))"')
AUDIO_SRC_RE = re.compile(r'(?:src|href)="((?:podcasts/)?[^"]+\.ogg)"')


def extract_referenced_images(html_text: str) -> set[str]:
    """Return the 'images/<file>' paths this HTML actually <img src="">s."""
    return set(IMAGE_SRC_RE.findall(html_text))


def extract_referenced_audio(html_text: str) -> set[str]:
    """Return the audio filenames (no 'podcasts/' prefix) this HTML plays."""
    return {ref.replace("podcasts/", "") for ref in AUDIO_SRC_RE.findall(html_text)}


def extract_issue_no(html_path: str) -> int | None:
    """Extract the issue number from the masthead."""
    try:
        text = Path(html_path).read_text(encoding="utf-8")
        m = re.search(r'No\.\s*(\d+)', text)
        if m:
            return int(m.group(1))
    except (FileNotFoundError, OSError):
        pass
    return None


def extract_issue_date(html_path: str) -> str:
    """Extract the issue date from the title tag, fallback to today."""
    try:
        text = Path(html_path).read_text(encoding="utf-8")
        m = re.search(r'·\s*(.+?)</title>', text)
        if m:
            raw = m.group(1).strip()
            for fmt in ("%B %d, %Y", "%B %d %Y"):
                try:
                    return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue
    except (FileNotFoundError, OSError):
        pass
    return datetime.now().strftime("%Y-%m-%d")


def copy_dir_contents(src: Path, dst: Path, globs: list[str]):
    """Copy all files matching any of the glob patterns into dst."""
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for g in globs:
        for f in src.glob(g):
            if f.is_file():
                shutil.copy2(str(f), str(dst / f.name))


def archive_issue(deploy_dir: str) -> dict:
    """Archive the current edition as a self-contained snapshot."""
    deploy = Path(deploy_dir)
    current_html = deploy / "index.html"

    if not current_html.exists():
        return {"status": "nothing_to_archive", "reason": "no index.html"}

    issue_no = extract_issue_no(str(current_html))
    date_iso = extract_issue_date(str(current_html))
    slug = date_iso

    archive_dir = deploy / "archive" / slug
    if archive_dir.exists():
        # If already archived today, re-archive (overwrite)
        shutil.rmtree(str(archive_dir))
    archive_dir.mkdir(parents=True)

    # ── Copy every resource to make the archive self-contained ──

    # 1. index.html
    shutil.copy2(str(current_html), str(archive_dir / "index.html"))

    # 2. style.css (static, at deploy root)
    css_src = deploy / "style.css"
    if css_src.exists():
        shutil.copy2(str(css_src), str(archive_dir / "style.css"))

    # 3. fonts/
    copy_dir_contents(deploy / "fonts", archive_dir / "fonts", ["*.woff2", "*.woff", "*.ttf"])

    # 4. edition.json — structured data for future analysis
    src_edition = deploy / "edition.json"
    if src_edition.exists():
        shutil.copy2(str(src_edition), str(archive_dir / "edition.json"))

    # 4b. making-of.html — each issue keeps its own "how this was made" replay,
    # so browsing the archive shows how the pipeline looked on that day rather
    # than today. Optional by design: the step that builds it is non-fatal.
    src_making = deploy / "making-of.html"
    if src_making.exists():
        shutil.copy2(str(src_making), str(archive_dir / "making-of.html"))

    # 5. Rewrite internal links inside the archived HTML to keep them working
    #    from the subdirectory. We use ARCHIVE_URL for the ⌂ link and HOME_URL
    #    for the masthead source link.
    archived_html = (archive_dir / "index.html").read_text(encoding="utf-8")

    # Replace relative 'archive/' link in the ⌂ with an absolute path
    archived_html = archived_html.replace(
        'href="archive/"',
        f'href="{ARCHIVE_URL}"'
    )
    # Also fix the "source" link in the colophon if still relative
    # (source link is already absolute: https://github.com/..., no action needed)

    (archive_dir / "index.html").write_text(archived_html, encoding="utf-8")

    # 6. images/ — ONLY the images this issue's own HTML references. Copying
    #    the whole deploy/images/ dir (as before) meant every snapshot dragged
    #    along every image ever generated, since that folder is never pruned —
    #    it made each archive grow roughly with total site age, not issue size.
    for ref in extract_referenced_images(archived_html):
        src_img = deploy / ref
        if src_img.exists():
            dst_img = archive_dir / ref
            dst_img.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src_img), str(dst_img))

    # 7. podcasts/ (audio for podcast pill — only those referenced in the HTML)
    for ref_path in extract_referenced_audio(archived_html):
        src_ogg = deploy / "podcasts" / ref_path
        if src_ogg.exists():
            (archive_dir / "podcasts").mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src_ogg), str(archive_dir / "podcasts" / ref_path))

    # Regenerate archive/index.html
    regenerate_archive_index(deploy)

    # Prune the deploy-root images/podcasts to what's still actually linked
    # from a live page. Nothing is lost: each past issue keeps its own copy
    # under archive/<date>/ from the steps above.
    pruned = prune_unused_assets(deploy)

    return {
        "status": "ok",
        "archived_to": str(archive_dir),
        "issue_no": issue_no,
        "date": date_iso,
        "pruned": pruned,
    }


def prune_unused_assets(deploy: Path) -> dict:
    """Delete deploy-root images/podcasts the live index.html no longer
    references. Historical usage is preserved per-day under archive/."""
    referenced_images, referenced_audio = set(), set()
    html_path = deploy / "index.html"
    if html_path.exists():
        text = html_path.read_text(encoding="utf-8")
        referenced_images |= extract_referenced_images(text)
        referenced_audio |= extract_referenced_audio(text)

    removed = {"images": 0, "podcasts": 0}

    images_dir = deploy / "images"
    if images_dir.exists():
        keep = {Path(r).name for r in referenced_images}
        for f in images_dir.iterdir():
            if f.is_file() and f.name not in keep:
                f.unlink()
                removed["images"] += 1

    podcasts_dir = deploy / "podcasts"
    if podcasts_dir.exists():
        keep = {Path(r).name for r in referenced_audio}
        for f in podcasts_dir.iterdir():
            if f.is_file() and f.name not in keep:
                f.unlink()
                removed["podcasts"] += 1

    return removed


def regenerate_archive_index(deploy_dir: str):
    """Regenerate archive/index.html with the chronological listing."""
    deploy = Path(deploy_dir)
    archive_root = deploy / "archive"
    archive_root.mkdir(exist_ok=True)

    # Collect all archived editions (each is a subdirectory)
    entries = []
    for d in sorted(archive_root.iterdir()):
        if not d.is_dir():
            continue
        idx = d / "index.html"
        if not idx.exists():
            continue
        text = idx.read_text(encoding="utf-8")
        title_m = re.search(r'<title>(.+?)</title>', text)
        title = title_m.group(1) if title_m else f"LVX IN TENEBRIS — {d.name}"
        no_m = re.search(r'No\.\s*(\d+)', text)
        issue = no_m.group(1) if no_m else "—"
        entries.append((d.name, issue, title))

    entries.sort(key=lambda x: x[0], reverse=True)

    list_items = "\n".join(
        f'      <li>'
        f'<a href="{name}/">'
        f'<span class="date">{name}</span>'
        f'<span class="issue-no">No. {issue}</span>'
        f'<span class="title">{html_esc(title)}</span>'
        f'</a></li>'
        for name, issue, title in entries
    )

    archive_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LVX IN TENEBRIS — Archive</title>
  <link rel="alternate" type="application/rss+xml" title="Lux in Tenebris — AI dispatches" href="/rss.xml">
  <link rel="stylesheet" href="../style.css">
  <style>
    .arch-page{{padding:40px 0}}
    .arch-page h1{{font-family:var(--serif);font-size:32px;font-weight:700;color:var(--type);margin:0 0 6px}}
    .arch-page .sub{{font-family:var(--sans);font-size:10.5px;color:var(--muted);letter-spacing:.08em;text-transform:uppercase;margin:0 0 32px}}
    .arch-list{{list-style:none;padding:0;margin:0}}
    .arch-list li{{border-bottom:1px solid var(--rule);padding:12px 0}}
    .arch-list a{{font-family:var(--serif);font-size:16px;color:var(--type);text-decoration:none;display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}}
    .arch-list a:hover{{color:var(--lux)}}
    .arch-list .date{{font-family:var(--sans);font-size:10px;color:var(--muted);letter-spacing:.06em;text-transform:uppercase;min-width:90px}}
    .arch-list .issue-no{{font-family:var(--sans);font-size:10px;font-weight:600;color:var(--lux);letter-spacing:.04em;min-width:40px}}
    .arch-list .title{{font-size:15px;color:var(--type-dim)}}
    .arch-back{{color:var(--muted);text-decoration:none;font-family:var(--sans);font-size:10px;letter-spacing:.06em}}
    .arch-back:hover{{color:var(--lux)}}
  </style>
</head>
<body>
<div class="container">
  <header class="masthead">
    <div class="topline"></div>
    <div class="ears">
      <span class="left"><a href="{HOME_URL}" class="arch-back">← Current Issue</a></span>
      <span class="right">Archive · <a href="/rss.xml" class="arch-back" title="Subscribe via RSS">RSS</a></span>
    </div>
    <div class="nameplate" style="font-size:48px">LVX IN <span class="lux">TENEBRIS</span></div>
    <hr class="rule-double">
    <div class="dateline"><span>Past Issues</span></div>
    <hr class="rule-thin">
  </header>
  <div class="arch-page">
    <h1>All Issues</h1>
    <p class="sub">Every edition preserved.</p>
    <ul class="arch-list">
{list_items}
    </ul>
  </div>
  <footer class="colophon">
    <p class="mark">Per aspera ad astra</p>
  </footer>
</div>
</body>
</html>
"""

    (archive_root / "index.html").write_text(archive_html, encoding="utf-8")


def html_esc(s: str) -> str:
    import html as _html
    return _html.escape(s, quote=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error", "error": "Usage: archive_issue.py <deploy-dir>"}))
        sys.exit(1)
    result = archive_issue(sys.argv[1])
    print(json.dumps(result))