# YouTube Channel Selection — Methodology & Maintenance

## How channels were selected (04 July 2026)

### Criteria

1. **AI/tech content** — channel must produce videos about AI research, tools, models, business, or policy
2. **Minimum 1 video/week** — too infrequent channels (<1/week) generate 0 hits most days
3. **English language** — all content must be in English for the newspaper
4. **RSS-accessible** — channel must have a working YouTube RSS feed
5. **Verified by 7-day frequency check**

### Current channels & 7-day frequency (verified 04 July 2026)

The authoritative list (with channel IDs) is in
[`skills/_shared/sources.md`](../../_shared/sources.md), under the
`## YouTube Scout (\`scout-youtube\`)` section. The frequency numbers below
are from the original selection pass and won't auto-update if a channel's
posting habits change — re-verify with the RSS check in step 3 below before
trusting them.

| Channel | Videos/7d | Expected daily |
|---------|:---------:|:--------------:|
| Bloomberg Technology | 15 | 1-3 |
| Beyond AI News | 6 | 1-2 |
| Theo - t3.gg | 8 | 1-2 |
| Matt Wolfe | 7 | 1-2 |
| AI Tool Report | 5 | 1 |
| The AI Daily Brief | 3 | 0-1 |
| Sabine Hossenfelder | 3 | 0-1 |
| Two Minute Papers | 2 | 0-1 |
| Fireship | 1 | 0-1 |
| AI Explained | 1 | 0-1 |

**Expected total: 4-10 videos/day.**

## Adding a new channel

1. Find the handle (e.g. `@ChannelName` from YouTube URL)
2. Resolve the channel ID via yt-dlp:
   ```bash
   timeout 45 yt-dlp --print channel_id "https://www.youtube.com/@Handle"
   ```
3. Verify via RSS:
   ```bash
   curl "https://www.youtube.com/feeds/videos.xml?channel_id=UC..."
   ```
   Should return Atom XML with recent video entries.
4. Check 7-day frequency before adding (should have ≥2 videos in last 7 days).
5. Add `{"id": "UC...", "name": "Channel Display Name"}` to the `json`
   block under the `scout-youtube` section in `skills/_shared/sources.md`
   — that's the only place it needs to change; `youtube_scout.py` reads it
   from there.

## Known issues

- **RSS limit** — YouTube RSS returns at most 15 entries per channel. For channels that post 5+/day, some videos may be missed. This is a YouTube limitation.
- **youtube-transcript-api** fetches from a third-party service — if down, transcript is `null`. The LLM still works from title + description.
- **Rate limiting** — keep 0.3s delay between RSS channel fetches to avoid IP blocks.
- **Channel ID is stable** — even if a channel renames, the `UC...` ID stays the same.
- **yt-dlp is slow without JS runtime** — only used for description fetching (1 per video). RSS is used for video listing.