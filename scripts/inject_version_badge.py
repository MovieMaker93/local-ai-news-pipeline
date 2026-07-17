#!/usr/bin/env python3
"""
inject_version_badge.py — Inject version selector (DS/K3) into Lux newspaper HTML.

Injects a small badge row between the dateline and the devocracy-credit line.
Each version marks itself as "current" (inactive badge) and links to the other.

Usage:
    python3 inject_version_badge.py <input.html> <mode> --output <output.html>

Modes:
    ds   — DeepSeek V4 Flash is the current page (links to k3/)
    k3   — Kimi K3 is the current page (links to ../)
"""

import sys
import os
import re
import argparse

def build_badge_html(mode: str) -> str:
    """Build the version selector HTML block."""
    if mode == "ds":
        # DeepSeek is current, link to k3/
        return (
            '<div class="version-selector">\n'
            '  <span class="vs-badge vs-badge-current vs-badge-ds">\U0001f40b DeepSeek V4 Flash</span>\n'
            '  <a href="k3/index.html" class="vs-badge vs-badge-k3">\U0001f52e Kimi K3 Edition (The Lens)</a>\n'
            '</div>'
        )
    elif mode == "k3":
        # Kimi is current, link to ../ (parent = deepseek default)
        return (
            '<div class="version-selector">\n'
            '  <a href="../index.html" class="vs-badge vs-badge-ds">\U0001f40b DeepSeek V4 Flash</a>\n'
            '  <span class="vs-badge vs-badge-current vs-badge-k3">\U0001f52e Kimi K3 Edition (The Lens)</span>\n'
            '</div>'
        )
    else:
        raise ValueError(f"Unknown mode: {mode}")


CSS = """<style>
.version-selector {
  display: flex;
  gap: 0.75rem;
  justify-content: center;
  align-items: center;
  margin: 0.5rem 0 0.75rem 0;
}
.vs-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-family: var(--sans);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  text-decoration: none;
  border: 1px solid;
  transition: background 0.2s, color 0.2s;
  line-height: 1.5;
}
.vs-badge-ds {
  color: var(--lux);
  border-color: var(--lux-soft);
  background: transparent;
}
.vs-badge-ds:hover {
  background: rgba(240, 162, 60, 0.08);
  color: var(--lux);
}
.vs-badge-k3 {
  color: var(--ember);
  border-color: var(--ember);
  background: transparent;
}
.vs-badge-k3:hover {
  background: rgba(255, 107, 53, 0.08);
  color: var(--ember);
}
.vs-badge-current {
  opacity: 0.5;
  cursor: default;
  pointer-events: none;
}
.vs-badge-current:hover {
  background: transparent;
}
</style>"""


def inject(html: str, mode: str) -> str:
    badge_html = build_badge_html(mode)

    # Fix CSS path for subdirectory versions (k3 is in k3/ subdir)
    if mode == "k3":
        html = html.replace('href="style.css"', 'href="../style.css"', 1)
        html = html.replace('href="fonts/', 'href="../fonts/', 1)
        html = html.replace('src="images/', 'src="../images/', 1)
        html = html.replace('src="podcasts/', 'src="../podcasts/', 1)

    # Insert CSS before </head>
    html = html.replace("</head>", CSS + "\n</head>", 1)

    # Insert badge AFTER the dateline closing </div>, before devocracy-credit
    # This ensures badge sits between dateline and credit, not inside dateline
    html = re.sub(
        r'(</div>)(\s*\n\s*<div class="devocracy-credit")',
        "\\1\n" + badge_html + "\\2",
        html,
        count=1,
    )

    # If template has different spacing, try a more general fallback
    if badge_html not in html:
        # Try with minimal whitespace between tags
        html = re.sub(
            r'(</div>)(\s*<div class="devocracy-credit")',
            "\\1\n" + badge_html + "\\2",
            html,
            count=1,
        )

    return html


def main():
    ap = argparse.ArgumentParser(description="Inject version badge into Lux newspaper")
    ap.add_argument("input", help="Path to input HTML file")
    ap.add_argument("mode", choices=["ds", "k3"], help="Which version is this page")
    ap.add_argument("--output", required=True, help="Path to output HTML file")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        html = f.read()

    result = inject(html, args.mode)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(result)

    print(json.dumps({"status": "ok", "output": args.output, "mode": args.mode}))


if __name__ == "__main__":
    import json
    main()