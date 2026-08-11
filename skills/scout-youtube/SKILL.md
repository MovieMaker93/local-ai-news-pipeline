---
name: scout-youtube
description: "V2 scout: YouTube AI video analysis. Reads the raw JSON produced by youtube_scout.py and returns a JSON array of candidates."
---

# Scout V2 — YouTube

## When to use
Called by orchestrator during the daily pipeline. Runs AFTER `youtube_scout.py` has populated `/tmp/v2/scouts/scout_youtube_raw.json`.

## Prerequisites
The script `youtube_scout.py` in scripts/v2/ must have run first.

## How it works
1. The Python script `youtube_scout.py` fetches recent videos from 10 AI-focused YouTube channels via RSS
2. It extracts video title, description, preview snippet, and transcript (first 2000 chars)
3. Saves raw data to `/tmp/v2/scouts/scout_youtube_raw.json`
4. This LLM scout reads the raw data and writes articles for genuinely newsworthy items

## Task
Read `/tmp/v2/scouts/scout_youtube_raw.json`. Each entry contains:
- `channel`: YouTube channel name
- `title`: video title
- `preview`: one-line summary / first sentence of description
- `description`: truncated description
- `transcript`: first 2000 chars of transcript (or null)
- `url`: video URL
- `published`: date

Select items that contain genuine AI news — model releases, breakthroughs, research findings, policy changes, major tool launches.

**DO NOT include:**
- Clickbait / opinion pieces with no factual news
- Tutorials or "how to" content unless announcing a major new tool
- Speculative predictions without substance
- Gaming/entertainment content that only tangentially mentions AI

## Output contract
Return ONLY a JSON array (no prose, no fences). Each element:

```json
{
  "title": "Catchy, factual headline capturing the news value",
  "summary": "1–2 factual sentences summarizing what the video reveals",
  "source": "YouTube — Channel Name",
  "url": "https://youtube.com/watch?v=VIDEO_ID",
  "date": "YYYY-MM-DD",
  "beat": "youtube",
  "signal": 1-5
}
```

## Signal guide
- 5 = Field-shifting breakthrough, major model release, unprecedented research
- 4 = Significant advancement, important policy change, notable tool launch
- 3 = Incremental improvement, useful analysis, interesting demo
- 2 = Minor update, opinion, speculation
- 1 = Not newsworthy (skip these)

## Rules
- Every `url` MUST come from the raw data. Never synthesize URLs.
- All content in ENGLISH.
- Only items dated within [yesterday, today].
- Deduplicate within your list.
- Return `[]` if nothing genuinely newsworthy found. Never return prose.
- **Critical: do NOT use x_search or web_search.** All data comes from the raw JSON file and your own knowledge.
- The `preview` field is a short summary — use it for a quick assessment of each video's relevance.

## Integration in run.sh
The orchestrator calls this skill AFTER the Python script has completed. It is
the 8th of the 9 scouts, which run **one at a time** (see orchestrator), and
comes before Step 3 (validation).

```bash
# Step: Python script fetches raw data
python3 "$SCRIPT_DIR/youtube_scout.py" --max 10

# Step: LLM writes articles
timeout "$TIMEOUT_SECS" "$HERMES_BIN" chat -q "Load scout-youtube skill. Read /tmp/v2/scouts/scout_youtube_raw.json. Extract newsworthy items, write JSON to /tmp/v2/scouts/scout_youtube.json using write_file." \
  --profile "$PROFILE" \
  -s scout-youtube \
  -t "file" \
  -m deepseek-v4-flash \
  --provider "$PIPELINE_PROVIDER"
```

⚠️ **The provider is `$PIPELINE_PROVIDER` (= `localAIServer`), never `openrouter`.**
This snippet used to say `openrouter`, and on 2026-07-28 an interactive session
asked to change an unrelated timeout "helpfully" rewrote every provider flag in
`run.sh` to match these docs. Keep snippets here consistent with the script.

## Channels monitored
The authoritative list (with channel IDs) is `skills/_shared/sources.json`,
key `scout-youtube.channels` — that's what `youtube_scout.py` actually reads.
This skill itself never needs to read it (it only reads the raw JSON the
Python step already produced), but if you're deciding whether a channel is
worth adding, this doc's job (not this skill's) is to know what's monitored:
The AI Daily Brief (daily AI news), Bloomberg Technology (daily tech news),
Theo - t3.gg (AI coding, nearly daily), Matt Wolfe (AI tools, 3-4/week), Two
Minute Papers (research highlights, 2/week), Sabine Hossenfelder
(science/AI, 2-3/week), Fireship (AI dev, 1-2/week), AI Explained (deep
analysis, 1/week), AI Tool Report (AI news, 5/week), Beyond AI News (AI
news, daily).

## Pitfalls
- The script runs BEFORE the LLM call in the pipeline. Never skip the Python step.
- If the raw JSON is empty (no videos in 24h), write `[]` and move on.
- The preview field is NOT the full article — it's a one-liner. Use the transcript + description for article content.
- Some videos may have `transcript: null` (auto-captions disabled) — still include them if title+description indicate news value, just write a shorter article.