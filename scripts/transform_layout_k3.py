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
/* Full page background: white */
html, body {
  background: #faf8f5 !important;
}
.container {
  background: #faf8f5 !important;
  border-left: 3px solid #e0dcd4 !important;
}
/* Header: white bg, black text */
header.masthead {
  background: #faf8f5 !important;
}
.masthead .topline {
  border-color: #d4d0c8 !important;
}
.ears .left, .ears .right, .ears a {
  color: #333 !important;
}
.nameplate {
  color: #000 !important;
}
.nameplate .lux {
  color: #000 !important;
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
.masthead .rule-thin {
  border-color: #d4d0c8 !important;
}
.masthead .rule-double {
  border-color: #ccc !important;
}
/* Wire widget: keep dark bg (override white) */
.wire-widget, .wire-widget *,
[class*="wire"], [class*="ticker"], [class*="breaking"] {
  background-color: var(--ink) !important;
  color: var(--type) !important;
}
/* Text colors — full black for readability */
.lead-story, .story, .top-story, .quick-hit, .section-content, .qh-item {
  color: #000 !important;
}
.lead a, .lead a:link, .lead h1, .lead a h1 {
  color: #000 !important;
}
.lead .kicker {
  color: #333 !important;
}
.lead .deck, .top-story .summary, .item .summary,
.section .item .summary, .lead-story .deck {
  color: #111 !important;
}
.lead a:hover h1 {
  color: #333 !important;
}
.top-story a, .top-story a:link, .top-story h3 a,
.item a, .item a:link, .item h3 a {
  color: #000 !important;
}
.section-header {
  color: #000 !important;
  border-bottom-color: #000 !important;
}
.byline, .item .byline, .meta-text, .qh-src {
  color: #555 !important;
}
a, a:link {
  color: #1a56db !important;
}
/* Version badges on white bg */
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
/* Article horizontal rules — consistent spacing */
.section .item {
  border-bottom: 1px solid #d4d0c8 !important;
  border-left: none !important;
  padding: 0.75rem 0 !important;
  margin: 0 !important;
}
.section .item:last-child {
  border-bottom: none !important;
}
/* Override Lux nth-child rules that create inconsistent borders */
.item:nth-child(3n+1), .item:nth-child(2n+1) {
  border-left: none !important;
  padding-left: 0 !important;
}
/* Top stories */
.topstories .story {
  border-left: none !important;
  border-top: 1px solid #d4d0c8 !important;
  padding: 0.75rem 0 !important;
}
.topstories .story:first-child {
  border-top: none !important;
}
/* Horizontal rules */
hr.rule-thin {
  border-color: #d4d0c8 !important;
}
hr.rule-double {
  border-color: #c8c4bc !important;
}
/* Remove images (not relevant for K3) */
.section-hero, .section-hero-img, .lead-image,
.item img, .top-story img {
  display: none !important;
}
/* Clean section headers */
.section-header {
  border-bottom: 2px solid #1a1a1a !important;
  color: #1a1a1a !important;
  margin-bottom: 0.75rem !important;
  padding-bottom: 0.25rem !important;
}
.section-header .count {
  color: #999 !important;
}
/* Quick hits */
.quick-hits a {
  color: #1a1a1a !important;
}
/* Colophon */
.colophon {
  color: #777 !important;
  border-top-color: #d4d0c8 !important;
}
.colophon a {
  color: #2563eb !important;
}
/* Topline (ember line at top of header) */
.topline {
  border-color: #e0dcd4 !important;
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