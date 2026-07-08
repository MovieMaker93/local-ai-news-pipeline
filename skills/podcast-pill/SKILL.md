---
name: podcast-pill
description: "Generates the 'Podcast Pill: The Divide' — a short 2-voice debate on the lead story using Grok TTS voices. Runs after editor, before render."
---

# Podcast Pill — The Divide

## When to use
After the editor has written `edition.json` to `/tmp/v2/edition.json`. The lead story is already selected.

## What it does
1. Reads `/tmp/v2/edition.json` → extracts the lead story (kicker, title, summary)
2. Generates a **natural dialogue** between two characters:
   - **Castor** — the realist: pragmatic, grounded, skeptical of hype
   - **Luna** — the contrarian: optimistic, provocative, sees opportunity
3. The dialogue is ~4-5 exchanges (60-90 seconds total), each line 1-3 sentences
4. Calls `text_to_speech` for each voice (provider: xai), saves to temp files
5. Concatenates both audio files into one `.ogg` using `ffmpeg` via terminal
6. Copies the final `.ogg` to `/tmp/v2/podcasts/lead_<date_iso>.ogg`
7. Writes podcast metadata to `/tmp/v2/podcast_meta.json`:
   ```json
   {
     "ogg_rel_path": "podcasts/lead_<date_iso>.ogg",
     "duration_sec": 55,
     "date_iso": "<date_iso>",
     "issue_no": <from edition.json>
   }
   ```

## Characters

### Castor (realist)
- Voice: `castor` (xAI)
- Tone: Measured, slightly dry, fact-based. "The data says..."
- Always brings it back to reality: market impact, timelines, engineering challenges

### Luna (contrarian)
- Voice: `luna` (xAI)
- Tone: Warm, slightly playful, big-picture. "But what if..."
- Always finds the silver lining, the alternative angle, the long game

## Dialogue structure (template)

The dialogue MUST be a true back-and-forth, NOT two monologues. Each line is
generated as a separate TTS clip, then concatenated in alternation.

**Duration target: 50-75 seconds, not longer.** If the dialogue is over 75s, trim.
If shorter, add more exchanges or make each line 2-3 sentences.

```
Castor: [Facts the story — the concrete event, the delay/launch/problem]
Luna:   [Reframes it — sees the opportunity, the upside, the alternative]
Castor: [Pushes back — the risks, the downsides, the uncertainty]
Luna:   [Counters — broader trend, historical pattern, competitive angle]
Castor: [Concedes some ground but stays grounded]
Luna:   [Closes on a provocative or forward-looking note]
```

Natural language, not robotic. Each line should sound like a person talking, not
reading a script. Use contractions, occasional pauses, rhetorical questions.
Each exchange references what the other just said — "you say that, but...",
"maybe, but look at it this way..." — so it feels like a real conversation.

## Audio generation — line-by-line alternation (CRITICAL)

DO NOT generate one long Castor block then one long Luna block.
Generate each exchange AS A SEPARATE TTS CALL, alternating voices:

1. Set TTS provider to xai, voice castor → generate line 1 → save as temp1.ogg
2. Set TTS provider to xai, voice luna → generate line 2 → save as temp2.ogg
3. Set TTS provider to xai, voice castor → generate line 3 → save as temp3.ogg
4. Set TTS provider to xai, voice luna → generate line 4 → save as temp4.ogg
5. Set TTS provider to xai, voice castor → generate line 5 → save as temp5.ogg
6. Set TTS provider to xai, voice luna → generate line 6 → save as temp6.ogg

Then concat ALL temp files IN ORDER with ffmpeg to produce the final audio.
This creates the natural conversation rhythm: Castor says something, Luna
responds, Castor pushes back, Luna counters — each in their own voice.

## Critical rules

- **Read `issue_no` from edition.json** — never hardcode it. Use `read_file` to
  get `/tmp/v2/edition.json` and parse `data["issue_no"]` for the metadata.
- **Always set TTS provider to xai** before generating. Switch back to `edge` after done.
  Use `terminal` to run: `hermes config set tts.provider xai --profile luke`
- Generate 6 clips in alternating order, then concat with ffmpeg
- **Duration target: 50-75 seconds.** If longer than 75s, reduce dialogue lines.
- **Save ffmpeg output** to `/tmp/v2/podcasts/lead_<date_iso>.ogg`
- **Create dir** `/tmp/v2/podcasts/` before writing
- **After generation**, restore TTS provider: `hermes config set tts.provider edge --profile luke`
- **Write metadata** to `/tmp/v2/podcast_meta.json` with `ogg_rel_path` relative to deploy dir root (e.g. `"podcasts/lead_2026-07-08.ogg"`)
- **Duration from ffprobe:** after concat, get actual duration with:
  ```bash
  ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 /tmp/v2/podcasts/lead_<date_iso>.ogg | cut -d. -f1
  ```

## 🔴 Pitfalls (from production failures)

### 1. DO NOT call TTS via Python imports — USE THE TOOL DIRECTLY
**What went wrong (2026-07-08):** The agent wrote a Python script that imported
`from tools.tts_tool import text_to_speech_tool` from Hermes internals. This
DOES NOT WORK inside `hermes chat -q` — the Python environment is isolated.

**Correct approach:** Call the `text_to_speech` tool DIRECTLY for each dialogue
line. The tool is available in the Hermes toolset alongside `terminal`,
`write_file`, `read_file`. Then use `terminal` to `cp` the output file to the
correct `/tmp/v2/podcasts/` path.

Do NOT write a Python sub-script to orchestrate TTS — orchestrate with the native tools.
### 2. No hard timeout → pipeline blocks for 30+ minutes  
**🔴 This is the #1 production risk.**  
The `run_v2.sh` step 7 call to `hermes chat -q` has no timeout wrapper.  
If the podcast agent hangs (e.g. stuck on a failing TTS call), the entire  
pipeline stalls and no deploy happens.

Be fast and decisive. Each TTS call should take ~3-5 seconds. If a call takes  
longer, move on and skip that line rather than hanging. 30 seconds total is the  
budget. If you cannot complete in 30 seconds, write what you have and move on.

If the pipeline is already stuck (podcast log shows only "[step 7] podcast pill..." for 15+ min):
- Kill the hanging `run_v2.sh` process
- Complete deploy manually — see `references/podcast-pill-production-fixes.md`

### 3. Issue counter from edition.json, not assumption
The metadata `issue_no` MUST come from `data["issue_no"]` in the current
`/tmp/v2/edition.json`. On 2026-07-08 the agent wrote `issue_no: 11` instead of
12 because it was hardcoded in the script, not read from the file.

### 4. Duration overshoot — cap at 75s
On 2026-07-08 the generated dialogue was 119 seconds — almost double the target.
If the dialogue text would produce >75s of audio, reduce exchanges from 6 to 4
or trim each line to 1 sentence. The pill is a teaser, not a full podcast.

## Injection (post-process)

The podcast pill is NOT part of the template or render.py. It is injected by a standalone script AFTER render:

```bash
python3 /home/nttluke/.hermes/profiles/luke/scripts/v2/inject_podcast_pill.py \
    /tmp/v2/output/index.html \
    "podcasts/lead_<date_iso>.ogg" \
    <duration_sec> \
    --output /tmp/v2/output/index.html
```

The injector:
- Adds **CSS** before `</head>` — uses ONLY Lux CSS variables (`--rule`, `--lux`, `--ember`, `--type`, `--type-dim`, `--muted`, `--sans`)
- Adds the **pill HTML** right before the lead article's `</article>` — sits under the lead title/summary. The pill is a `<button>` (NOT an `<a>` link), with a hidden `<audio>` element and minimal JS toggling play/pause inline.
- The pill includes: animated waveform SVG icon · "Podcast Pill" label · "·" · "The Divide" show name · duration string
- Click toggles playback in-page (no new tab). A thin progress bar slides under the pill during playback.
- CSS uses `<style>` tags injected before `</head>`; JS is injected before `</body>`.
- **Known compatibility:** the `timeupdate` event listener uses event delegation (`document.addEventListener('timeupdate', ..., true)`) — this works because the `<audio>` is in the DOM when created. If the audio element is added dynamically after page load, the listener still fires.

## Design constraints (non-negotiable)

The podcast pill must be **visible but not invasive**:
- **Use ONLY Lux CSS variables** — never custom colors, backgrounds, or fonts
- **Minimal footprint** — inline-flex, small font (10px), subtle border, rounded pill shape
- **No layout impact** — sits under the lead article without changing margins, padding, or flow
- **Hover effect only** — border and text color shift to `var(--lux)` on hover
- **No changes to any other page element** — masthead, lead zone, sections, trending, footer must render exactly as before

## Output
- `/tmp/v2/podcasts/lead_<date_iso>.ogg` — the audio file
- `/tmp/v2/podcast_meta.json` — metadata for the injector step