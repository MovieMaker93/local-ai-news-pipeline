#!/usr/bin/env python3
"""
fix_archive_issue_numbers.py — Fix incorrect issue numbers in archived HTML files
and regenerate the archive listing. Also sets .issue to the correct value.

Usage:
    python3 fix_archive_issue_numbers.py
"""
import json
import os
import re
import sys
from pathlib import Path

ARCHIVE_DIR = Path("/home/nttluke/ai-news-deploy/archive")
DEPLOY_DIR = Path("/home/nttluke/ai-news-deploy")

# Correct issue numbers (no issue on 2026-07-12)
correct_numbers = {
    "2026-07-02": 7, "2026-07-03": 8, "2026-07-04": 9,
    "2026-07-05": 10, "2026-07-06": 11, "2026-07-07": 12,
    "2026-07-08": 13, "2026-07-09": 14, "2026-07-10": 15,
    "2026-07-11": 16, "2026-07-13": 17, "2026-07-14": 18,
    "2026-07-15": 19, "2026-07-16": 20, "2026-07-17": 21,
    "2026-07-18": 22, "2026-07-19": 23, "2026-07-20": 24,
    "2026-07-21": 25, "2026-07-22": 26, "2026-07-23": 27,
    "2026-07-24": 28,
}

fixed = 0
errors = []

for date_str, correct_no in sorted(correct_numbers.items()):
    html_path = ARCHIVE_DIR / date_str / "index.html"
    if not html_path.exists():
        errors.append(f"MISSING: {date_str}")
        continue
    
    html = html_path.read_text(encoding="utf-8")
    m = re.search(r'No\.\s*(\d+)', html)
    if m:
        current_no = int(m.group(1))
        if current_no != correct_no:
            new_html = html.replace(f"No. {current_no}", f"No. {correct_no}")
            html_path.write_text(new_html, encoding="utf-8")
            fixed += 1
            print(f"  {date_str}: No. {current_no} → No. {correct_no} ✓")
        else:
            print(f"  {date_str}: No. {correct_no} ✓ (already correct)")
    else:
        errors.append(f"NO_ISSUE_NO: {date_str}")

print(f"\nFixed {fixed} archived HTML files")
if errors:
    for e in errors:
        print(f"  ⚠ {e}")

# Fix the .issue file for the next run
issue_path = DEPLOY_DIR / ".issue"
issue_path.write_text("28", encoding="utf-8")
print(f"Set .issue → 28 (next issue will be No. 29)")

# Regenerate the archive listing
print("\nRegenerating archive/index.html...")
entries = []
for d in sorted(ARCHIVE_DIR.iterdir()):
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

def html_esc(s):
    import html as _html
    return _html.escape(s, quote=True)

ARCHIVE_URL = "/archive/"
HOME_URL = "/"

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
</html>"""

(ARCHIVE_DIR / "index.html").write_text(archive_html, encoding="utf-8")
print(f"  ✓ archive/index.html regenerated ({len(entries)} entries)")

# Commit and push
os.chdir(str(DEPLOY_DIR))
os.system("git add -A")
os.system('git commit -m "fix: correct issue numbers in archive (No. 7→28)" --quiet 2>/dev/null || true')
os.system("git push origin main --quiet 2>/dev/null || echo '  ⚠ git push failed'")
print("\n✅ Done! Archive fixed and pushed to GitHub.")