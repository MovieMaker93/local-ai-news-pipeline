#!/usr/bin/env python3
"""youtube_scout.py — Fetch recent AI video data from YouTube channels.

Uses YouTube RSS feeds for video listings + yt-dlp for descriptions.
Uses youtube-transcript-api for transcripts.

Usage:
    python3 youtube_scout.py [--hours 24] [--max 10]

Output: /tmp/v2/scouts/scout_youtube_raw.json
"""

import sys, os, json, subprocess, time, re, html
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests, xml.etree.ElementTree as ET
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound


# ── Channel list (hardcoded channel IDs, resolved once) ─────
CHANNELS = [
    {"id": "UCKelCK4ZaO6HeEI1KQjqzWA", "name": "The AI Daily Brief"},
    {"id": "UCrM7B7SL_g1edFOnmj-SDKg", "name": "Bloomberg Technology"},
    {"id": "UCbRP3c757lWg9M-U7TyEkXA", "name": "Theo - t3.gg"},
    {"id": "UChpleBmo18P08aKCIgti38g", "name": "Matt Wolfe"},
    {"id": "UCbfYPyITQ-7l4upoX8nvctg", "name": "Two Minute Papers"},
    {"id": "UC1yNl2E66ZzKApQdRuTQ4tw", "name": "Sabine Hossenfelder"},
    {"id": "UCsBjURrPoezykLs9EqgamOA", "name": "Fireship"},
    {"id": "UCNJ1Ymd5yFuUPtn21xtRbbw", "name": "AI Explained"},
    {"id": "UCmeU2DYiVy80wMBGZzEWnbw", "name": "AI Tool Report"},
    {"id": "UC5l7RouTQ60oUjLjt1Nh-UQ", "name": "Beyond AI News"},
]

OUTPUT_DIR = Path("/tmp/v2/scouts")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "scout_youtube_raw.json"
YTDLP = "yt-dlp"
NS = {"atom": "http://www.w3.org/2005/Atom"}


def run_ytdlp(*args, timeout=20):
    """Run yt-dlp, return stdout lines."""
    try:
        result = subprocess.run([YTDLP, *args], capture_output=True, text=True, timeout=timeout)
        return [l.strip() for l in result.stdout.strip().split("\n") if l.strip()] if result.returncode == 0 else []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def fetch_rss_videos(cid, channel_name, hours=24):
    """Fetch recent videos from a channel via YouTube RSS."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    try:
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code != 200:
            return []
        root = ET.fromstring(r.content)
        yt_ns = "http://www.youtube.com/xml/schemas/2015"
        videos = []
        for entry in root.findall("atom:entry", NS):
            pub_str = entry.find("atom:published", NS)
            if pub_str is None:
                continue
            pub = datetime.fromisoformat(pub_str.text.replace("Z", "+00:00"))
            if pub < cutoff:
                continue
            vid_elem = entry.find(f"{{{yt_ns}}}videoId")
            title_elem = entry.find("atom:title", NS)
            if vid_elem is None or title_elem is None:
                continue
            vid = vid_elem.text
            videos.append({
                "video_id": vid,
                "channel": channel_name,
                "title": title_elem.text.strip(),
                "url": f"https://www.youtube.com/watch?v={vid}",
                "published": pub.isoformat(),
            })
        return videos
    except Exception:
        return []


def get_description(video_id):
    """Get video description via yt-dlp."""
    lines = run_ytdlp("--print", "description",
                       f"https://www.youtube.com/watch?v={video_id}", timeout=15)
    text = "\n".join(lines) if lines else ""
    return text[:1000]


def fetch_transcript(video_id):
    """Fetch English transcript."""
    try:
        tl = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
        return " ".join(item["text"] for item in tl)[:2000]
    except (TranscriptsDisabled, NoTranscriptFound):
        return None
    except Exception:
        return None


def main():
    hours = 24
    max_videos = 10
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--hours" and i + 1 < len(args):
            hours = int(args[i + 1])
        elif a == "--max" and i + 1 < len(args):
            max_videos = int(args[i + 1])

    print(f"YouTube Scout — last {hours}h, {len(CHANNELS)} channels", file=sys.stderr)

    all_videos = []
    for ch in CHANNELS:
        print(f"  ▶ {ch['name']}...", file=sys.stderr)
        vids = fetch_rss_videos(ch["id"], ch["name"], hours)
        print(f"    → {len(vids)} videos", file=sys.stderr)
        all_videos.extend(vids)
        time.sleep(0.3)

    print(f"  Total: {len(all_videos)} videos", file=sys.stderr)
    all_videos.sort(key=lambda v: v.get("published", ""), reverse=True)
    all_videos = all_videos[:max_videos]

    enriched = []
    for v in all_videos:
        print(f"  Enrich: {v['title'][:50]}...", file=sys.stderr)
        desc = get_description(v["video_id"])
        transcript = fetch_transcript(v["video_id"])
        preview = desc.split("\n")[0].strip()[:200] if desc else v["title"]
        enriched.append({
            "video_id": v["video_id"],
            "channel": v["channel"],
            "title": v["title"],
            "preview": preview,
            "description": desc[:500],
            "transcript": transcript,
            "url": v["url"],
            "published": v["published"],
        })
        time.sleep(0.5)

    OUTPUT_FILE.write_text(json.dumps({
        "count": len(enriched),
        "generated_at": datetime.now().isoformat(),
        "videos": enriched,
    }, indent=2), encoding="utf-8")

    print(f"\n  ✅ Written {len(enriched)} videos", file=sys.stderr)
    for v in enriched:
        print(f"    • {v['channel']}: {v['title'][:60]}", file=sys.stderr)
    print(json.dumps({"status": "ok", "count": len(enriched)}))


if __name__ == "__main__":
    main()