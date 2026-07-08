#!/bin/bash
# ─────────────────────────────────────────────────────────────
# Lux in Tenebris V2 — Orchestrator Script
# Dumb executor: schedules atomic hermes chat -q calls.
# Each step is isolated, stateless, communicates via JSON files.
# ─────────────────────────────────────────────────────────────
set -euo pipefail

PROFILE="luke"
V2_DIR="/tmp/v2"
LOG_DIR="$V2_DIR/logs"
SCOUTS_DIR="$V2_DIR/scouts"
IMAGES_DIR="$V2_DIR/images"
OUTPUT_DIR="$V2_DIR/output"
HERMES_BIN="/home/nttluke/.local/bin/hermes"
RENDER_PY="/home/nttluke/.hermes/profiles/luke/skills/ai-news-24h/render.py"
SCRIPT_DIR="/home/nttluke/.hermes/profiles/luke/scripts/v2"
CLEANUP_SH="$V2_DIR/cleanup.sh"
DEPLOY_DIR="/home/nttluke/ai-news-deploy"
TIMEOUT_SECS=600  # 10 min per scout

# ── Setup ────────────────────────────────────────────────────
mkdir -p "$LOG_DIR" "$SCOUTS_DIR" "$IMAGES_DIR" "$OUTPUT_DIR"
TODAY=$(date +%Y-%m-%d)
LOGFILE="$LOG_DIR/run_${TODAY}.log"
exec > >(tee -a "$LOGFILE") 2>&1
echo "═══════════════════════════════════════════════"
echo "LUX IN TENEBRIS V2 — $(date '+%Y-%m-%d %H:%M:%S')"
echo "═══════════════════════════════════════════════"

# ── Step 0: Cleanup ─────────────────────────────────────────
echo "[step 0] cleanup..."
if [ -f "$CLEANUP_SH" ]; then
    bash "$CLEANUP_SH"
else
    find "$SCOUTS_DIR" -name 'scout_*.json' -delete 2>/dev/null || true
    find "$IMAGES_DIR" -type f -delete 2>/dev/null || true
    [ -f "$V2_DIR/edition.json" ] && rm -f "$V2_DIR/edition.json"
fi
echo "  ✓ cleanup done"

# ── Step 1: Metadata ────────────────────────────────────────
echo "[step 1] metadata..."
YESTERDAY=$(python3 -c "import datetime; print((datetime.date.today() - datetime.timedelta(days=1)).isoformat())")
TODAY_HUMAN=$(python3 -c "import datetime; print(datetime.date.today().strftime('%B %d, %Y'))")
cat > "$SCOUTS_DIR/_metadata.json" <<EOF
{"today":"$TODAY","yesterday":"$YESTERDAY","today_human":"$TODAY_HUMAN"}
EOF
echo "  ✓ window: $YESTERDAY → $TODAY"

# ── Step 2: Scouts (in parallel, 3 batches) ─────────────────
echo "[step 2] scouts phase 1 (parallel: x, research, official)..."

run_scout() {
    local name="$1"
    local skill="$2"
    local toolsets="$3"
    local prompt="$4"
    local outfile="$SCOUTS_DIR/scout_${name}.json"
    
    echo "  → starting scout $name ($skill)"
    timeout "$TIMEOUT_SECS" "$HERMES_BIN" chat -q "$prompt" \
        --profile "$PROFILE" \
        -s "$skill" \
        -t "$toolsets" \
        -Q --yolo \
        2>>"$LOG_DIR/scout_${name}_${TODAY}.err" \
        >"$LOG_DIR/scout_${name}_${TODAY}.out"
    
    # Validate output exists and is valid JSON
    if [ -f "$outfile" ] && python3 -c "import json; json.load(open('$outfile'))" 2>/dev/null; then
        local count
        count=$(python3 -c "import json; d=json.load(open('$outfile')); print(len(d) if isinstance(d, list) else len(d.get('editorial',[])))" 2>/dev/null || echo "0")
        echo "  ✓ scout $name done ($count items)"
    else
        echo "  ✗ scout $name FAILED — writing empty fallback"
        echo "[]" > "$outfile"
    fi
}

# Common scout brief template
SCOUT_DATE_BRIEF="Window: from $YESTERDAY to $TODAY. Today is $TODAY, yesterday is $YESTERDAY."

# --- Phase 1: 3 scouts in parallel ---
run_scout "x" "scout-v2-x" "x_search,file" \
    "You are the X Scout for Lux in Tenebris. $SCOUT_DATE_BRIEF
Load skill scout-v2-x and follow it exactly. Use from_date=$YESTERDAY to_date=$TODAY in x_search calls.
Write the JSON array to $SCOUTS_DIR/scout_x.json using write_file. ENGLISH ONLY." &
PID_X=$!

run_scout "research" "scout-v2-research" "web,file" \
    "You are the Research Scout for Lux in Tenebris. $SCOUT_DATE_BRIEF
Load skill scout-v2-research and follow it exactly. Search arXiv and HuggingFace daily papers.
Write the JSON array to $SCOUTS_DIR/scout_research.json using write_file. ENGLISH ONLY." &
PID_RESEARCH=$!

run_scout "official" "scout-v2-official" "web,file" \
    "You are the Official Scout for Lux in Tenebris. $SCOUT_DATE_BRIEF
Load skill scout-v2-official and follow it exactly. Scrape official AI lab blogs.
Write the JSON array to $SCOUTS_DIR/scout_official.json using write_file. ENGLISH ONLY." &
PID_OFFICIAL=$!

# Wait for phase 1
wait $PID_X $PID_RESEARCH $PID_OFFICIAL
echo "  ✓ phase 1 complete"

# --- Phase 2: 3 scouts in parallel ---
echo "[step 2] scouts phase 2 (parallel: opensource, tools, funding)..."

run_scout "opensource" "scout-v2-opensource" "web,x_search,file" \
    "You are the Open Source Scout for Lux in Tenebris. $SCOUT_DATE_BRIEF
Load skill scout-v2-opensource and follow it exactly. Search GitHub Trending and HuggingFace Trending.
Write the JSON object (with editorial array + trending object) to $SCOUTS_DIR/scout_opensource.json using write_file. ENGLISH ONLY." &
PID_OS=$!

run_scout "tools" "scout-v2-tools" "web,file" \
    "You are the Tools Scout for Lux in Tenebris. $SCOUT_DATE_BRIEF
Load skill scout-v2-tools and follow it exactly. Search Product Hunt, Hacker News, tool launches.
Write the JSON array to $SCOUTS_DIR/scout_tools.json using write_file. ENGLISH ONLY." &
PID_TOOLS=$!

run_scout "funding" "scout-v2-funding" "web,file" \
    "You are the Funding Scout for Lux in Tenebris. $SCOUT_DATE_BRIEF
Load skill scout-v2-funding and follow it exactly. Search TechCrunch, Crunchbase for AI funding.
Write the JSON array to $SCOUTS_DIR/scout_funding.json using write_file. ENGLISH ONLY." &
PID_FUNDING=$!

wait $PID_OS $PID_TOOLS $PID_FUNDING
echo "  ✓ phase 2 complete"

# --- Phase 3: 1 scout ---
echo "[step 2] scouts phase 3 (hardware)..."

run_scout "hardware" "scout-v2-hardware" "web,x_search,file" \
    "You are the Hardware Scout for Lux in Tenebris. $SCOUT_DATE_BRIEF
Load skill scout-v2-hardware and follow it exactly. Search for robots, chips, datacenter hardware news.
Write the JSON array to $SCOUTS_DIR/scout_hardware.json using write_file. ENGLISH ONLY."
echo "  ✓ phase 3 complete"

# ── Phase 4: YouTube Scout (Python script + dedicated LLM model) ────
echo "[step 2] scouts phase 4 (youtube)..."
echo "  → running youtube_scout.py (Python fetch)..."
python3 "$SCRIPT_DIR/youtube_scout.py" --max 10 2>>"$LOGFILE"
echo "  ✓ youtube_scout.py done"

echo "  → running scout-v2-youtube (deepseek/deepseek-v4-flash)..."
"$HERMES_BIN" chat -q \
    "Load scout-v2-youtube skill. Read /tmp/v2/scouts/scout_youtube_raw.json.
Extract newsworthy items from the video data.
Write the JSON array to /tmp/v2/scouts/scout_youtube.json using write_file.
ENGLISH ONLY.
Today is $TODAY ($TODAY_HUMAN). Window: $YESTERDAY to $TODAY." \
    --profile "$PROFILE" \
    -s scout-v2-youtube \
    -t "file" \
    -m deepseek/deepseek-v4-flash \
    --provider openrouter \
    -Q --yolo \
    >"$LOG_DIR/scout_youtube_${TODAY}.log" 2>&1

echo "  ✓ phase 4 complete"

# ── Step 3: Validate all scout files ────────────────────────
echo "[step 3] validating scout files..."
SCOUT_COUNT=0
SCOUT_NAMES="x research official opensource tools funding hardware youtube"
for scout in $SCOUT_NAMES; do
    f="$SCOUTS_DIR/scout_${scout}.json"
    if [ -f "$f" ] && python3 -c "import json; json.load(open('$f'))" 2>/dev/null; then
        SCOUT_COUNT=$((SCOUT_COUNT + 1))
    else
        echo "  ✗ missing/invalid: scout_${scout}.json"
        echo "[]" > "$f"
        SCOUT_COUNT=$((SCOUT_COUNT + 1))
    fi
done
echo "  ✓ $SCOUT_COUNT/8 scout files ready"

# ── Step 4: Editor ──────────────────────────────────────────
echo "[step 4] editor..."

# Compute issue number from persistent store (deploy dir survives reboots)
PREV_ISSUE=0
if [ -f "$DEPLOY_DIR/.issue" ]; then
    PREV_ISSUE=$(cat "$DEPLOY_DIR/.issue" 2>/dev/null || echo 0)
elif [ -f "$V2_DIR/.issue" ]; then
    PREV_ISSUE=$(cat "$V2_DIR/.issue" 2>/dev/null || echo 0)
fi
NEXT_ISSUE=$((PREV_ISSUE + 1))
echo "$NEXT_ISSUE" > "$V2_DIR/.issue"
echo "$NEXT_ISSUE" > "$DEPLOY_DIR/.issue"

"$HERMES_BIN" chat -q \
    "You are the Editor for Lux in Tenebris. Load skill editor-v2 and follow it exactly.
Today is $TODAY ($TODAY_HUMAN). Issue #$NEXT_ISSUE.
Read all 7 scout JSON files from $SCOUTS_DIR/scout_*.json and the metadata.
For cross-day dedup (step 4b), read $DEPLOY_DIR/headlines_history.json via read_file.
Assemble edition.json following the skill instructions.
Write the result to $V2_DIR/edition.json using write_file. ENGLISH ONLY." \
    --profile "$PROFILE" \
    -s "editor-v2" \
    -t "file" \
    -Q --yolo \
    >"$LOG_DIR/editor_${TODAY}.log" 2>&1 || echo "  ⚠ editor returned non-zero"

if [ -f "$V2_DIR/edition.json" ] && python3 -c "import json; json.load(open('$V2_DIR/edition.json'))" 2>/dev/null; then
    echo "  ✓ edition.json written"
else
    echo "  ✗ edition.json MISSING or INVALID — aborting"
    echo "FATAL: editor failed" 
    exit 1
fi

# ── Step 5: Image Gen ───────────────────────────────────────
echo "[step 5] image gen..."

"$HERMES_BIN" chat -q \
    "You are the Image Generator for Lux in Tenebris. Load skill image-gen-v2 and follow it exactly.
Today is $TODAY.
Read $V2_DIR/edition.json. Generate images for lead + each non-empty section.
Use image_generate tool. Save images to $IMAGES_DIR/ directory.
Update edition.json with image paths. ENGLISH ONLY." \
    --profile "$PROFILE" \
    -s "image-gen-v2" \
    -t "file,image_gen,terminal" \
    -Q --yolo \
    >"$LOG_DIR/imagegen_${TODAY}.log" 2>&1 || echo "  ⚠ image gen returned non-zero (non-fatal)"

echo "  ✓ image gen complete"

# ── Step 6: Render HTML ─────────────────────────────────────
echo "[step 6] render..."

if [ -f "$RENDER_PY" ] && [ -f "$V2_DIR/edition.json" ]; then
    python3 "$RENDER_PY" "$V2_DIR/edition.json" "$OUTPUT_DIR/index.html" 2>>"$LOGFILE"
    echo "  ✓ rendered → $OUTPUT_DIR/index.html"
else
    echo "  ✗ render.py or edition.json missing"
    exit 1
fi

# ── Step 7: Podcast Pill — The Divide ─────────────────────────
PODCAST_META="$V2_DIR/podcast_meta.json"
PODCAST_INJECT="$SCRIPT_DIR/inject_podcast_pill.py"
mkdir -p "$V2_DIR/podcasts"
echo "[step 7] podcast pill..."
"$HERMES_BIN" chat -q \
    "You are the Podcast Pill generator for Lux in Tenebris. Load skill podcast-pill and follow it exactly.
Today is $TODAY ($TODAY_HUMAN). Issue #$NEXT_ISSUE.
Read $V2_DIR/edition.json. Generate a Castor vs Luna dialogue from the lead story.
Produce TTS audio for both voices, concat with ffmpeg, write metadata to $PODCAST_META.
Use text_to_speech tool. Use terminal for ffmpeg and config switches. ENGLISH ONLY." \
    --profile "$PROFILE" \
    -s "podcast-pill" \
    -t "file,terminal" \
    -Q --yolo \
    >"$LOG_DIR/podcast_${TODAY}.log" 2>&1 || echo "  ⚠ podcast pill returned non-zero (non-fatal)"

# Inject podcast pill into HTML (if metadata was generated)
if [ -f "$PODCAST_META" ]; then
    META=$(python3 -c "
import json
with open('$PODCAST_META') as f:
    m = json.load(f)
print(m.get('ogg_rel_path', ''))
print(m.get('duration_sec', 0))
")
    OGG_REL=$(echo "$META" | head -1)
    DUR=$(echo "$META" | tail -1)
    if [ -n "$OGG_REL" ] && [ "$DUR" -gt 0 ]; then
        python3 "$PODCAST_INJECT" \
            "$OUTPUT_DIR/index.html" \
            "$OGG_REL" \
            "$DUR" \
            --output "$OUTPUT_DIR/index.html" \
            2>>"$LOGFILE" && echo "  ✓ podcast pill injected" || echo "  ⚠ podcast pill injection failed"
    else
        echo "  - podcast meta incomplete, skipping injection"
    fi
else
    echo "  - podcast meta not found, skipping"
fi

# ── Step 8: Wire Articles (RSS → AI writing) ─────────────────
WIRE_SCRIPT="$SCRIPT_DIR/wire_articles.py"
echo "[step 7] wire articles..."
if [ -f "$WIRE_SCRIPT" ]; then
    python3 "$WIRE_SCRIPT" --max 5 --out "$SCOUTS_DIR/scout_wire.json" 2>>"$LOGFILE"
    WIRE_COUNT=$(python3 -c "import json;d=json.load(open('$SCOUTS_DIR/scout_wire.json'));print(len(d))" 2>/dev/null || echo "0")
    echo "  ✓ $WIRE_COUNT wire articles written"
else
    echo "  - wire_articles.py not found, skipping"
    WIRE_COUNT=0
fi

# ── Step 8: Inject Wire Ticker into HTML ────────────────────
INJECT_SCRIPT="$SCRIPT_DIR/inject_wire_ticker.py"
echo "[step 8] inject wire ticker..."
if [ "$WIRE_COUNT" -gt 0 ] && [ -f "$INJECT_SCRIPT" ] && [ -f "$OUTPUT_DIR/index.html" ]; then
    python3 "$INJECT_SCRIPT" "$OUTPUT_DIR/index.html" "$SCOUTS_DIR/scout_wire.json" --output "$OUTPUT_DIR/index.html" 2>>"$LOGFILE"
    echo "  ✓ ticker injected"
else
    echo "  - no wire articles or injector missing, skipping"
fi

# ── Step 9: Deploy to production ────────────────────────────
SSH_URL="git@github.com:NTTLuke/luxintenebris-ai-news.git"

echo "[step 9] deploying to production..."

# Sync deploy repo with remote
cd "$DEPLOY_DIR"
git fetch origin --quiet 2>/dev/null || true
git reset --hard origin/main --quiet 2>/dev/null || true

# ── Step 10: Archive current issue BEFORE overwriting it ────
echo "[step 10] archiving current issue..."
ARCHIVE_SCRIPT="$SCRIPT_DIR/archive_issue.py"
if [ -f "$ARCHIVE_SCRIPT" ]; then
    python3 "$ARCHIVE_SCRIPT" "$DEPLOY_DIR" 2>>"$LOGFILE"
    echo "  ✓ archived"
else
    echo "  - archive script not found, skipping"
fi

# Copy all files from V2 output to deploy dir
cp "$OUTPUT_DIR/index.html" "$DEPLOY_DIR/index.html"
cp -r "$OUTPUT_DIR/fonts"/* "$DEPLOY_DIR/fonts/" 2>/dev/null || true
mkdir -p "$DEPLOY_DIR/images"
cp "$IMAGES_DIR"/*.jpg "$DEPLOY_DIR/images/" 2>/dev/null || true
echo "  ✓ files copied to deploy dir"

# Save edition.json for archive & headline dedup
cp "$V2_DIR/edition.json" "$DEPLOY_DIR/edition.json"
echo "  ✓ edition.json saved to deploy dir"

# Update headline history for editor dedup
python3 "$SCRIPT_DIR/update_headlines_history.py" \
    "$V2_DIR/edition.json" \
    "$DEPLOY_DIR/headlines_history.json" \
    2>>"$LOGFILE" && echo "  ✓ headlines history updated" || echo "  ⚠ headlines history update failed"

# Git add + commit + push
cd "$DEPLOY_DIR"
git add -A
if ! git diff --cached --quiet; then
    git commit -m "Update AI news $TODAY" --quiet
fi
git push origin main --quiet 2>/dev/null
echo "  ✓ pushed to GitHub"

# ── Step 11: Report ─────────────────────────────────────────
IMG_COUNT=$(find "$IMAGES_DIR" -name '*.jpg' 2>/dev/null | wc -l)
echo ""
echo "═══════════════════════════════════════════════"
echo "✅ V2 PIPELINE COMPLETE — $(date '+%H:%M:%S')"
echo "  Issue:   #$NEXT_ISSUE"
echo "  Date:    $TODAY"
echo "  Scouts:  $SCOUT_COUNT/8"
echo "  Wire:    $WIRE_COUNT articles"
echo "  Images:  $IMG_COUNT"
echo "  Deploy:  $DEPLOY_DIR"
echo "  Pushed:  github.com/nttluke/luxintenebris-ai-news"
echo "═══════════════════════════════════════════════"
