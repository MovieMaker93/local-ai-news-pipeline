#!/usr/bin/env python3
"""archive_issue.py — Archivia il numero corrente prima del deploy.

Usage:
    python3 archive_issue.py <deploy-dir>

Cosa fa:
    1. Legge issue_no + data dall'index.html corrente
    2. Salva in archive/YYYY-MM-DD/ una copia completa self-contained:
       - index.html  (fotogramma congelato del numero)
       - style.css
       - fonts/
       - images/
    3. Rigenera archive/index.html con la lista cronologica
"""

import sys
import os
import re
import json
import shutil
from datetime import datetime
from pathlib import Path


# ── Percorso assoluto dell'archivio su GitHub Pages ──────────
# Il sito è hosted su https://nttluke.github.io/luxintenebris-ai-news/
ARCHIVE_URL = "/luxintenebris-ai-news/archive/"
HOME_URL = "/luxintenebris-ai-news/"


def extract_issue_no(html_path: str) -> int | None:
    """Estrae il numero di edizione dal masthead."""
    try:
        text = Path(html_path).read_text(encoding="utf-8")
        m = re.search(r'No\.\s*(\d+)', text)
        if m:
            return int(m.group(1))
    except (FileNotFoundError, OSError):
        pass
    return None


def extract_issue_date(html_path: str) -> str:
    """Estrae la data dal title tag, o fallback a oggi."""
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
    """Copia tutti i file che matchano i glob in dst."""
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for g in globs:
        for f in src.glob(g):
            if f.is_file():
                shutil.copy2(str(f), str(dst / f.name))


def archive_issue(deploy_dir: str) -> dict:
    """Archivia l'edizione corrente come fotogramma self-contained."""
    deploy = Path(deploy_dir)
    current_html = deploy / "index.html"

    if not current_html.exists():
        return {"status": "nothing_to_archive", "reason": "no index.html"}

    issue_no = extract_issue_no(str(current_html))
    date_iso = extract_issue_date(str(current_html))
    slug = date_iso

    archive_dir = deploy / "archive" / slug
    if archive_dir.exists():
        # Se già archiviato oggi, sovrascrivi (re-archive)
        shutil.rmtree(str(archive_dir))
    archive_dir.mkdir(parents=True)

    # ── Copia ogni risorsa per rendere l'archivio self-contained ──

    # 1. index.html
    shutil.copy2(str(current_html), str(archive_dir / "index.html"))

    # 2. style.css (statico, nella root del deploy)
    css_src = deploy / "style.css"
    if css_src.exists():
        shutil.copy2(str(css_src), str(archive_dir / "style.css"))

    # 3. fonts/
    copy_dir_contents(deploy / "fonts", archive_dir / "fonts", ["*.woff2", "*.woff", "*.ttf"])

    # 4. images/ (le immagini del numero corrente)
    copy_dir_contents(deploy / "images", archive_dir / "images", ["*.jpg", "*.png", "*.webp"])

    # 5. edition.json — dati strutturati per analisi future
    src_edition = deploy / "edition.json"
    if src_edition.exists():
        shutil.copy2(str(src_edition), str(archive_dir / "edition.json"))

    # 6. Rewrite internal links inside the archived HTML to keep them working
    #    from the subdirectory. We use ARCHIVE_URL for the ⌂ link and HOME_URL
    #    for the masthead source link.
    archived_html = (archive_dir / "index.html").read_text(encoding="utf-8")

    # Sostituisci il link relativo 'archive/' nell'⌂ con path assoluto
    archived_html = archived_html.replace(
        'href="archive/"',
        f'href="{ARCHIVE_URL}"'
    )
    # Fix anche il link "source" nel colophon se ancora usa path relativo
    # (il link source è già assoluto: https://github.com/..., non serve)

    (archive_dir / "index.html").write_text(archived_html, encoding="utf-8")

    # 7. podcasts/ (audio per il podcast pill — solo quelli referenziati nell'HTML)
    audio_refs = re.findall(r'src="((?:podcasts/)?[^"]+\.ogg)"', archived_html)
    for ref in audio_refs:
        ref_path = ref.replace("podcasts/", "")  # normalize path
        src_ogg = deploy / "podcasts" / ref_path
        if src_ogg.exists():
            (archive_dir / "podcasts").mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src_ogg), str(archive_dir / "podcasts" / ref_path))

    # Rigenera archive/index.html
    regenerate_archive_index(deploy)

    return {
        "status": "ok",
        "archived_to": str(archive_dir),
        "issue_no": issue_no,
        "date": date_iso,
    }


def regenerate_archive_index(deploy_dir: str):
    """Rigenera archive/index.html con la lista cronologica."""
    deploy = Path(deploy_dir)
    archive_root = deploy / "archive"
    archive_root.mkdir(exist_ok=True)

    # Raccogli tutte le edizioni archiviate (directory)
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
      <span class="right">Archive</span>
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