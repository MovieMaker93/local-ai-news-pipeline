# Podcast Pill — Production Fixes (2026-07-08)

## Incident Report: Pipeline Blocked by Podcast Agent

**Date:** 2026-07-08
**Symptoms:** Pipeline stuck at Step 7 for 30+ minutes. No deploy happened by 07:30.
Manual intervention required: kill the stuck process, complete steps 8-12 by hand.

### Root causes

#### 1. Agent wrote a Python sub-script instead of using tools directly

The `podcast-pill` agent created `/tmp/v2/generate_podcast_pill.py` that imported
`from tools.tts_tool import text_to_speech_tool` from the Hermes agent package.
This is NOT available inside a `hermes chat -q` subprocess — the Python
environment is isolated, the import fails silently or with an error that the
agent couldn't handle, and the agent hung indefinitely.

**Fix in skill:** Added a clear Pitfall section: "DO NOT call TTS via Python
imports — USE THE TOOL DIRECTLY". The `text_to_speech` tool is a first-class
Hermes tool available in the toolset. Use it directly for each dialogue line.

#### 2. Hardcoded issue number

The Python script had `ISSUE_NO = 11` hardcoded. The actual issue was #12.
This propagated to `podcast_meta.json` with wrong data.

**Fix in skill:** Added rule: "Read `issue_no` from `/tmp/v2/edition.json` with
`read_file` — never hardcode."

#### 3. Duration overshoot (119 seconds vs 75s target)

The generated dialogue was 119 seconds — nearly double the target. The agent
added 6 long exchanges (3 sentences each) without checking total length.

**Fix in skill:** Strengthened duration target to "50-75 seconds, not longer."
Added instruction: if text would produce >75s, reduce exchanges from 6 to 4
or trim each line to 1 sentence.

#### 4. No timeout on the `hermes chat -q` call

The `run_v2.sh` step 7 call uses the default timeout (none). The podcast agent
hung for 30+ minutes blocking the entire pipeline.

**Fix in skill:** Added a time budget: "30 seconds total. If a TTS call takes
longer, move on. If you cannot complete in 30 seconds, write what you have."

### Recovery procedure (for future incidents)

If the pipeline is stuck at Step 7 and the release hasn't deployed by 07:30:

```bash
# 1. Kill the stuck pipeline
ps aux | grep "run_v2.sh" | grep -v grep | awk '{print $2}' | xargs kill

# 2. Check if podcast was actually generated
ls -la /tmp/v2/podcasts/lead_$(date +%Y-%m-%d).ogg

# 3. If podcast exists, complete steps 8-12 manually:
cd ~/ai-news-deploy

# Step 10: git sync
git fetch origin --quiet 2>/dev/null || true
git reset --hard origin/main --quiet 2>/dev/null || true

# Step 11: archive
python3 ~/.hermes/profiles/luke/scripts/v2/archive_issue.py ~/ai-news-deploy

# Step 12: copy files
cp /tmp/v2/output/index.html ~/ai-news-deploy/index.html
cp -r /tmp/v2/output/fonts/* ~/ai-news-deploy/fonts/ 2>/dev/null || true
mkdir -p ~/ai-news-deploy/images ~/ai-news-deploy/podcasts
cp /tmp/v2/images/*.jpg ~/ai-news-deploy/images/ 2>/dev/null || true
cp /tmp/v2/podcasts/lead_$(date +%Y-%m-%d).ogg ~/ai-news-deploy/podcasts/ 2>/dev/null || true
cp /tmp/v2/edition.json ~/ai-news-deploy/edition.json

# Headline history
python3 ~/.hermes/profiles/luke/scripts/v2/update_headlines_history.py \
    /tmp/v2/edition.json ~/ai-news-deploy/headlines_history.json

# Update issue
echo "$(cat ~/ai-news-deploy/.issue)" > /tmp/v2/.issue

# Step 12e: git commit + push
cd ~/ai-news-deploy
git add -A
git diff --cached --quiet || git commit -m "Update AI news $(date +%Y-%m-%d) [recovered]"
git push origin main
```
