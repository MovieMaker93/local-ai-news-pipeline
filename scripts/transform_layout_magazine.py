#!/usr/bin/env python3
"""
transform_layout_magazine.py — Transform Lux newspaper HTML into 'The Magazine' layout.

Changes:
- 2-column flex grid for sections (instead of single column)
- Simpler item cards (no images, clean borders)
- Still uses Lux CSS variables — no style.css modifications

Usage:
    python3 transform_layout_magazine.py <input.html> --output <output.html>
"""

import sys
import os
import re
import argparse


MAGAZINE_CSS = """<style>
/* ── The Magazine layout for K3 edition ── */
.sections {
  display: flex !important;
  flex-wrap: wrap !important;
  gap: 1.5rem !important;
}
.section {
  flex: 1 1 45% !important;
  min-width: 320px !important;
  margin-bottom: 0 !important;
}
.section .items {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.section .item {
  border-bottom: 1px solid var(--rule);
  padding: 0.5rem 0;
}
.section .item:last-child {
  border-bottom: none;
}
.section .item h3 a {
  font-size: 0.95rem;
  line-height: 1.3;
}
.section .item .summary {
  font-size: 0.8rem;
  line-height: 1.35;
  margin-top: 0.15rem;
  color: var(--type-dim);
}
.section .item .byline {
  font-size: 0.7rem;
  margin-top: 0.1rem;
}
.section .section-hero,
.section .item img,
.section .section-hero-img {
  display: none !important;
}
/* Lead: more prominent */
.lead .lead-title {
  font-size: 2rem !important;
  line-height: 1.15 !important;
}
.lead .deck {
  font-size: 1.05rem !important;
  line-height: 1.4 !important;
}
</style>"""


def transform(html: str) -> str:
    # Add magazine CSS before </head>
    html = html.replace("</head>", MAGAZINE_CSS + "\n</head>", 1)
    return html


def main():
    ap = argparse.ArgumentParser(description="Transform Lux HTML to Magazine layout")
    ap.add_argument("input", help="Path to input HTML file")
    ap.add_argument("--output", required=True, help="Path to output HTML file")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        html = f.read()

    result = transform(html)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(result)

    print(f'{{"status":"ok","output":"{args.output}","layout":"magazine"}}')


if __name__ == "__main__":
    main()