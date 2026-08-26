#!/usr/bin/env python3
"""
update_headlines_history.py — Extract headlines from edition.json and append them
to the headline history for cross-day deduplication by the editor.

Usage:
    python3 update_headlines_history.py <edition.json> <headlines_history.json>
"""

import json
import sys
from pathlib import Path


def extract_headlines(edition: dict) -> list[dict]:
    """Extract all headlines from an edition.json dict."""
    today = edition.get("date_iso", "")
    issue = edition.get("issue_no", 0)
    entries = []

    if edition.get("lead"):
        entries.append({
            "text": edition["lead"]["title"],
            "source": edition["lead"].get("source", ""),
            "date": today,
            "issue": issue,
        })

    for s in edition.get("top_stories", []):
        entries.append({
            "text": s.get("title", ""),
            "source": s.get("source", ""),
            "date": today,
            "issue": issue,
        })

    for sec in edition.get("sections", []):
        for item in sec.get("items", []):
            entries.append({
                "text": item.get("title", ""),
                "source": item.get("source", ""),
                "date": today,
                "issue": issue,
            })

    for h in edition.get("quick_hits", []):
        text = h.get("headline") or h.get("title", "")
        entries.append({
            "text": text,
            "source": h.get("source", ""),
            "date": today,
            "issue": issue,
        })

    return entries


def main():
    if len(sys.argv) < 3:
        print(json.dumps({"status": "error", "error": "Usage: update_headlines_history.py <edition.json> <history.json>"}))
        sys.exit(1)

    edition_path = Path(sys.argv[1])
    history_path = Path(sys.argv[2])

    # Leggi edition.json
    if not edition_path.exists():
        print(json.dumps({"status": "error", "error": f"edition.json not found: {edition_path}"}))
        sys.exit(1)

    edition = json.loads(edition_path.read_text())

    # Read existing history or create new
    if history_path.exists():
        history = json.loads(history_path.read_text())
    else:
        history = {"meta": {"name": "LOCAL AI NEWS Headline History"}, "headlines": []}

    # Extract new headlines
    new_entries = extract_headlines(edition)
    history["headlines"].extend(new_entries)

    # Keep only the last 2000 entries (~2+ years of daily editions)
    history["headlines"] = history["headlines"][-2000:]

    # Write
    history_path.write_text(json.dumps(history, indent=2))
    print(json.dumps({"status": "ok", "added": len(new_entries), "total": len(history["headlines"])}))


if __name__ == "__main__":
    main()