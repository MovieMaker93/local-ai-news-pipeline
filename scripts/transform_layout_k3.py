#!/usr/bin/env python3
"""
transform_layout_k3.py — Transform K3 Lux HTML into 'White Edition' layout.

Changes:
- White/cream background (body stays dark Lux, content area is light)
- Lux header (masthead, nameplate, dateline) stays dark
- Consistent border lines between articles
- Clean, readable typography on light background

Usage:
    python3 transform_layout_k3.py <input.html> --output <output.html>
"""

import sys
import argparse


WHITE_CSS = """<style>
/* ── K3 White Edition ── */

/* 1. BACKGROUNDS */
html, body {
  background: #faf8f5 !important;
}
.container {
  background: #faf8f5 !important;
  border-left: 3px solid #e0dcd4 !important;
}
header.masthead {
  background: #faf8f5 !important;
}

/* 2. WIRE NEWS — keep dark (AFTER nuclear override) */
/* moved to after section 5 below */

/* 3. ALL LINKS BLACK by default */
a, a:link {
  color: #000 !important;
}

/* 4. HEADER exceptions (override general) */
.masthead .topline {
  border-color: #d4d0c8 !important;
}
.ears .left, .ears .right, .ears a {
  color: #333 !important;
}
.ears a:hover {
  color: #333 !important;
}
.nameplate {
  color: #000 !important;
}
.nameplate .lux {
  color: #f0a23c !important;
}
.dateline, .dateline span, .dateline .tag {
  color: #333 !important;
}
.dateline .dot {
  color: #999 !important;
}
.devocracy-credit, .devocracy-credit a {
  color: #666 !important;
}
.devocracy-credit a:hover {
  color: #666 !important;
}
.masthead .rule-thin {
  border-color: #d4d0c8 !important;
}
.masthead .rule-double {
  border-color: #ccc !important;
}

/* 5. ALL ARTICLE TEXT BLACK — nuclear */
.lead, .lead *, .lead a, .lead a:link, .lead a:visited, .lead h1, .lead a h1,
.topstories, .topstories *, .top-stories, .top-story,
.story, .story *, .story p, .story h3,
.section, .section *, .section .item, .section .items,
.item, .item *, .item p, .item a, .item a:link, .item h3, .item h3 a,
.section-content, .section-header, .section-head, .section-head h2,
.quick-hits, .quick-hits *, .quick-hit, .quick-hit *,
.qh-item, .qh-item *, .qh-title, .qh-src,
.byline, .byline *, .byline .src, .meta-text,
.inbrief, .inbrief *, .inbrief a, .inbrief h2,
.sections, .sections *, .lead-head, .lead-body, .lead-grid,
.colophon, .colophon *, .colophon p, .colophon .meta, .colophon a,
h1, h2, h3, h4, h5, p, a, span, div, article, section {
  color: #000 !important;
}
/* Hover: amber like Lux (AFTER nuclear rule) */
.lead a:hover h1, .lead a:hover .lead-title,
.top-story a:hover h3, .top-story a:hover .top-title,
.item a:hover h3, .item a:hover .item-title,
.quick-hit a:hover, .qh-item a:hover,
a:hover, a:focus, a:active {
  color: #f0a23c !important;
}

/* Wire news: keep dark (AFTER nuclear, overrides it) */
.wt, .wt *,
.wtt, .wtt *,
.ti, .tih, .tis,
.wt a, .wtt a, .ti a, .ti a:link,
[class*="wire"], [class*="ticker"], [class*="breaking"] {
  background-color: var(--ink) !important;
  color: var(--type) !important;
}
.section-header {
  color: #000 !important;
  border-bottom-color: #000 !important;
}
.byline, .item .byline, .meta-text, .qh-src {
  color: #000 !important;
}

/* 6. VERSION BADGES (after general a rule) */
.vs-badge-ds {
  color: #1a1a1a !important;
  border-color: #1a1a1a !important;
  background: transparent !important;
}
.vs-badge-ds:hover {
  background: rgba(0,0,0,0.05) !important;
  color: #000 !important;
}
.vs-badge-k3 {
  color: #1a1a1a !important;
  border-color: #1a1a1a !important;
  background: transparent !important;
}
.vs-badge-k3:hover {
  background: rgba(0,0,0,0.05) !important;
  color: #000 !important;
}
.vs-badge-current {
  opacity: 0.4 !important;
}
.vs-badge-current:hover {
  color: #1a1a1a !important;
}

/* 7. ARTICLE RULES */
.section .item {
  border-bottom: 1px solid #d4d0c8 !important;
  border-left: none !important;
  padding: 0.75rem 0 !important;
  margin: 0 !important;
}
.section .item:last-child {
  border-bottom: none !important;
}
.item:nth-child(3n+1), .item:nth-child(2n+1) {
  border-left: none !important;
  padding-left: 0 !important;
}
.topstories .story {
  border-left: none !important;
  border-top: 1px solid #d4d0c8 !important;
  padding: 0.75rem 0 !important;
}
.topstories .story:first-child {
  border-top: none !important;
}
hr.rule-thin {
  border-color: #d4d0c8 !important;
}
hr.rule-double {
  border-color: #c8c4bc !important;
}

/* 8. REMOVE IMAGES */
.section-hero, .section-hero-img, .lead-image,
.item img, .top-story img {
  display: none !important;
}

/* 9. SECTION HEADERS */
.section-header {
  border-bottom: 2px solid #1a1a1a !important;
  color: #1a1a1a !important;
  margin-bottom: 0.75rem !important;
  padding-bottom: 0.25rem !important;
}
.section-header .count {
  color: #999 !important;
}

/* 10. QUICK HITS + COLOPHON */
.quick-hits a {
  color: #000 !important;
}
.colophon {
  color: #000 !important;
  border-top-color: #d4d0c8 !important;
}
.colophon a {
  color: #000 !important;
  border-bottom-color: #d4d0c8 !important;
}
</style>"""


def transform(html: str) -> str:
    # Add white edition CSS before </head>
    html = html.replace("</head>", WHITE_CSS + "\n</head>", 1)
    return html


def main():
    ap = argparse.ArgumentParser(description="Transform Lux HTML to K3 White Edition")
    ap.add_argument("input", help="Path to input HTML file")
    ap.add_argument("--output", required=True, help="Path to output HTML file")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        html = f.read()

    result = transform(html)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(result)

    print(f'{{"status":"ok","output":"{args.output}","layout":"white-edition"}}')


if __name__ == "__main__":
    main()