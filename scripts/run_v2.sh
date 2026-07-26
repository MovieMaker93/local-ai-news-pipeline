#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Lux in Tenebris V2 — Orchestrator Script (v2.1 robust)
# Each step is isolated, stateless, communicates via JSON files.
# Features:
#   - Process-group kill for stuck scouts (no zombie subagents)
#   - 90-min master timeout
#   - Auto-skip image gen when xAI credits exhausted
#   - Auto-skip podcast pill when xAI TTS unavailable
#   - Falls back to partial deploy if any non-critical step fails
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

PROFILE="luke"
V2_DIR="/tmp/v2"
LOG_DIR="$V2_DIR/logs"
SCOUTS_DIR="$V2_DIR/scouts"
IMAGES_DIR="$V2_DIR/images"
OUTPUT_DIR="$V2_DIR/output"
HERMES_BIN="/home/nttluke/.local/bin/hermes"
RENDER_PY="/home/nttluke/lux-in-tenebris-pipeline/scripts/render.py"
SCRIPT_DIR="/home/nttluke/.hermes/profiles/luke/scripts/v2"
CLEANUP_SH="$V2_DIR/cleanup.sh"
DEPLOY_DIR="/home/nttluke/ai-news-deploy"
TIMEOUT_SECS=600  # 10 min per scout
MASTER_TIMEOUT=5400  # 90 min for entire pipeline

# ── Setup ────────────────────────────────────────────────────
mkdir -p "$LOG_DIR" "$SCOUTS_DIR" "$IMAGES_DIR" "$OUTPUT_DIR"
TODAY=$(date +%Y-%m-%d)
LOGFILE="$LOG_DIR/run_${TODAY}.log"
exec > >(tee -a "$LOGFILE") 2>&1

# Master watchdog — if we exceed MASTER_TIMEOUT, kill everything
START_EPOCH=$(date +%s)
elapsed() { echo $(( $(date +%s) - START_EPOCH )); }
check_timeout() {
    if [ "$(elapsed)" -gt "$MASTER_TIMEOUT" ]; then
        echo "⛔ MASTER TIMEOUT after $(elapsed)s — aborting pipeline"
        exit 2
    fi
}

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

# ── Helper: run a scout with safe timeout ──────────────────
# Each scout runs in a background subshell with a 10-min timeout.
# If timeout fires, the subshell exits, write_file may not have
# completed — so we check and write empty fallback in the parent.
# CRITICAL: '|| true' prevents set -e from killing the subshell
# when timeout returns non-zero (exit code 124).
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
        -m deepseek-v4-flash --provider localAIServer \
        -Q --yolo \
        2>>"$LOG_DIR/scout_${name}_${TODAY}.err" \
        >"$LOG_DIR/scout_${name}_${TODAY}.out" || true
    
    # Validate output
    if [ -f "$outfile" ] && python3 -c "import json; json.load(open('$outfile'))" 2>/dev/null 2>&1; then
        local count=0
        count=$(python3 -c "import json; d=json.load(open('$outfile')); print(len(d) if isinstance(d, list) else len(d.get('editorial',[])))" 2>/dev/null || echo "0")
        echo "  ✓ scout $name done ($count items)"
    else
        echo "  ✗ scout $name FAILED or TIMEOUT — writing empty fallback"
        echo "[]" > "$outfile"
    fi
    check_timeout
}

SCOUT_DATE_BRIEF="Window: from $YESTERDAY to $TODAY. Today is $TODAY, yesterday is $YESTERDAY."

# ── Step 2: Scouts ───────────────────────────────────────────
# Each phase runs in parallel. Individual scouts have 10-min timeout.
# If a scout fails, it gets an empty [] fallback — never blocks the pipeline.

# --- Phase 1: 3 scouts in parallel ---
echo "[step 2] scouts phase 1 (parallel: x, research, official)..."
run_scout "x" "scout-v2-x" "x_search,file,terminal" \
    "You are the X Scout for Lux in Tenebris. $SCOUT_DATE_BRIEF
Load skill scout-v2-x and follow it exactly. Use from_date=$YESTERDAY to_date=$TODAY in x_search calls.
Write the JSON array to $SCOUTS_DIR/scout_x.json using write_file. ENGLISH ONLY." &
PID_X=$!

run_scout "research" "scout-v2-research" "web,file,terminal" \
    "You are the Research Scout for Lux in Tenebris. $SCOUT_DATE_BRIEF
Load skill scout-v2-research and follow it exactly. Search arXiv and HuggingFace daily papers.
Write the JSON array to $SCOUTS_DIR/scout_research.json using write_file. ENGLISH ONLY." &
PID_RESEARCH=$!

run_scout "official" "scout-v2-official" "web,file,terminal" \
    "You are the Official Scout for Lux in Tenebris. $SCOUT_DATE_BRIEF
Load skill scout-v2-official and follow it exactly. Scrape official AI lab blogs.
Write the JSON array to $SCOUTS_DIR/scout_official.json using write_file. ENGLISH ONLY." &
PID_OFFICIAL=$!

wait $PID_X $PID_RESEARCH $PID_OFFICIAL 2>/dev/null || true
echo "  ✓ phase 1 complete"

# --- Phase 2: 3 scouts in parallel ---
echo "[step 2] scouts phase 2 (parallel: opensource, tools, funding)..."
run_scout "opensource" "scout-v2-opensource" "web,x_search,file,terminal" \
    "You are the Open Source Scout for Lux in Tenebris. $SCOUT_DATE_BRIEF
Load skill scout-v2-opensource and follow it exactly. Search GitHub Trending and HuggingFace Trending.
Write the JSON object (with editorial array + trending object) to $SCOUTS_DIR/scout_opensource.json using write_file. ENGLISH ONLY." &
PID_OS=$!

run_scout "tools" "scout-v2-tools" "web,file,terminal" \
    "You are the Tools Scout for Lux in Tenebris. $SCOUT_DATE_BRIEF
Load skill scout-v2-tools and follow it exactly. Search Product Hunt, Hacker News, tool launches.
Write the JSON array to $SCOUTS_DIR/scout_tools.json using write_file. ENGLISH ONLY." &
PID_TOOLS=$!

run_scout "funding" "scout-v2-funding" "web,file,terminal" \
    "You are the Funding Scout for Lux in Tenebris. $SCOUT_DATE_BRIEF
Load skill scout-v2-funding and follow it exactly. Search TechCrunch, Crunchbase for AI funding.
Write the JSON array to $SCOUTS_DIR/scout_funding.json using write_file. ENGLISH ONLY." &
PID_FUNDING=$!

wait $PID_OS $PID_TOOLS $PID_FUNDING 2>/dev/null || true
echo "  ✓ phase 2 complete"

# ── Trending fallback: if opensource scout failed, fetch via curl ──
TRENDING_FALLBACK="$SCRIPT_DIR/fetch_trending.py"
if [ -f "$TRENDING_FALLBACK" ]; then
    SCOUT_OS="$SCOUTS_DIR/scout_opensource.json"
    has_trending=$(python3 -c "
import json
try:
    d = json.load(open('$SCOUT_OS'))
    if isinstance(d, dict):
        gh = len(d.get('trending',{}).get('github',{}).get('items',[]))
        hf = len(d.get('trending',{}).get('huggingface',{}).get('items',[]))
        print(gh + hf)
    else:
        print(0)
except: print(0)
" 2>/dev/null || echo "0")
    if [ "$has_trending" -lt 3 ]; then
        echo "  → trending data missing (${has_trending} items), fetching via curl fallback..."
        TMP_TRENDING=$(mktemp)
        python3 "$TRENDING_FALLBACK" --output-json "$TMP_TRENDING" 2>>"$LOGFILE" || true
        if [ -f "$TMP_TRENDING" ] && python3 -c "import json; json.load(open('$TMP_TRENDING'))" 2>/dev/null 2>&1; then
            python3 -c "
import json
try:
    # Read existing scout file (may be [] or {editorial:..., trending:...})
    with open('$SCOUT_OS') as f:
        existing = json.load(f)
    if not isinstance(existing, dict):
        existing = {'editorial': []}
    # Read trending data
    with open('$TMP_TRENDING') as f:
        trending_data = json.load(f)
    existing['trending'] = trending_data.get('trending', {})
    with open('$SCOUT_OS', 'w') as f:
        json.dump(existing, f, indent=2)
    gh = len(existing['trending'].get('github',{}).get('items',[]))
    hf = len(existing['trending'].get('huggingface',{}).get('items',[]))
    print(f'  ✓ trending fallback: {gh} GitHub + {hf} HF items written')
except Exception as e:
    print(f'  ⚠ trending fallback failed: {e}')
" 2>>"$LOGFILE" || true
            rm -f "$TMP_TRENDING"
        else
            echo "  ⚠ trending fallback fetch failed"
            rm -f "$TMP_TRENDING"
        fi
    fi
fi

# --- Phase 3: 1 scout ---
echo "[step 2] scouts phase 3 (hardware)..."
run_scout "hardware" "scout-v2-hardware" "web,x_search,file,terminal" \
    "You are the Hardware Scout for Lux in Tenebris. $SCOUT_DATE_BRIEF
Load skill scout-v2-hardware and follow it exactly. Search for robots, chips, datacenter hardware news.
Write the JSON array to $SCOUTS_DIR/scout_hardware.json using write_file. ENGLISH ONLY."
echo "  ✓ phase 3 complete"

# --- Phase 4: YouTube Scout ---
echo "[step 2] scouts phase 4 (youtube)..."
echo "  → running youtube_scout.py (Python fetch)..."
python3 "$SCRIPT_DIR/youtube_scout.py" --max 10 2>>"$LOGFILE" || echo "  ⚠ youtube scout fetch failed (non-fatal)"
echo "  ✓ youtube_scout.py done"

echo "  → running scout-v2-youtube (GLM-5.2-openai)..."
timeout "$TIMEOUT_SECS" "$HERMES_BIN" chat -q 'Load scout-v2-youtube skill. Read /tmp/v2/scouts/scout_youtube_raw.json.
Extract newsworthy items from the video data.
Write the JSON array to /tmp/v2/scouts/scout_youtube.json using write_file.
ENGLISH ONLY. Today is '"$TODAY"' ('"$TODAY_HUMAN"'). Window: '"$YESTERDAY"' to '"$TODAY"'."' \
    --profile "$PROFILE" -s scout-v2-youtube -t file \
    -m deepseek-v4-flash --provider localAIServer \
    -Q --yolo >"$LOG_DIR/scout_youtube_${TODAY}.log" 2>&1 || true
echo "  ✓ phase 4 complete"
check_timeout

# --- Phase 5: Italia AI Spotlight ---
echo "[step 2] scouts phase 5 (italia)..."
"$HERMES_BIN" chat -q "You are the Italia AI Spotlight Scout for Lux in Tenebris. $SCOUT_DATE_BRIEF
Load skill scout-v2-italia and follow it exactly. Fetch AI4Business RSS, search web for Italian AI news.
Write the JSON array to $SCOUTS_DIR/scout_italia.json using write_file.
All titles in ENGLISH, links to Italian sources. ENGLISH ONLY." \
    --profile "$PROFILE" -s scout-v2-italia -t web,file,terminal -m deepseek-v4-flash --provider localAIServer -Q --yolo \
    >"$LOG_DIR/scout_italia_${TODAY}.log" 2>&1 || true
echo "  ✓ phase 5 complete"
check_timeout

# ── Step 3: Validate all scout files ────────────────────────
echo "[step 3] validating scout files..."
SCOUT_COUNT=0
SCOUT_NAMES="x research official opensource tools funding hardware youtube italia"
for scout in $SCOUT_NAMES; do
    f="$SCOUTS_DIR/scout_${scout}.json"
    if [ -f "$f" ] && python3 -c "import json; json.load(open('$f'))" 2>/dev/null 2>&1; then
        SCOUT_COUNT=$((SCOUT_COUNT + 1))
    else
        echo "  ✗ missing/invalid: scout_${scout}.json — writing empty"
        echo "[]" > "$f"
        SCOUT_COUNT=$((SCOUT_COUNT + 1))
    fi
done
echo "  ✓ $SCOUT_COUNT/9 scout files ready"
check_timeout

# ── Step 4: Editor ──────────────────────────────────────────
echo "[step 4] editor..."

PREV_ISSUE=0
if [ -f "$DEPLOY_DIR/.issue" ]; then
    PREV_ISSUE=$(cat "$DEPLOY_DIR/.issue" 2>/dev/null || echo 0)
elif [ -f "$V2_DIR/.issue" ]; then
    PREV_ISSUE=$(cat "$V2_DIR/.issue" 2>/dev/null || echo 0)
fi
NEXT_ISSUE=$((PREV_ISSUE + 1))
echo "$NEXT_ISSUE" > "$V2_DIR/.issue"
# NOTE: $DEPLOY_DIR/.issue is written AFTER git reset (step 9) to avoid revert

"$HERMES_BIN" chat -q "You are the Editor for Lux in Tenebris. Load skill editor-v2 and follow it exactly.
Today is $TODAY. Issue #$NEXT_ISSUE.
Read all scout JSON files from $SCOUTS_DIR/scout_*.json and the metadata.
For cross-day dedup (step 4b), read $DEPLOY_DIR/headlines_history.json via read_file.
Assemble edition.json following the skill instructions.
Write the result to $V2_DIR/edition.json using write_file. ENGLISH ONLY." \
    --profile "$PROFILE" -s editor-v2 -t file -m deepseek-v4-flash --provider localAIServer -Q --yolo \
    >"$LOG_DIR/editor_${TODAY}.log" 2>&1 || true

if [ -f "$V2_DIR/edition.json" ] && python3 -c "import json; json.load(open('$V2_DIR/edition.json'))" 2>/dev/null 2>&1; then
    echo "  ✓ edition.json written"
else
    echo "  ✗ edition.json MISSING or INVALID — cannot continue"
    echo "FATAL: editor failed"
    exit 1
fi
check_timeout

# ── Step 4b: Editor (Kimi K3 edition) ────────────────────────
echo "[step 4b] editor kimi-k3..."
ISSUE_DS=$(python3 -c "import json; print(json.load(open('$V2_DIR/edition.json')).get('issue_no','$NEXT_ISSUE'))" 2>/dev/null || echo "$NEXT_ISSUE")
"$HERMES_BIN" chat -q "You are the Editor for Lux in Tenebris. Load skill editor-v2-k3 and follow it exactly.
Today is $TODAY. Issue #$ISSUE_DS.
Read all scout JSON files from $SCOUTS_DIR/scout_*.json and the metadata.
For cross-day dedup (step 4b), read $DEPLOY_DIR/headlines_history.json via read_file.
Assemble edition.json following the skill instructions.
Write the result to $V2_DIR/edition_k3.json using write_file. ENGLISH ONLY." \
    --profile "$PROFILE" -s editor-v2-k3 -t file -m kimi-k3 --provider localAIServer -Q --yolo \
    >"$LOG_DIR/editor_k3_${TODAY}.log" 2>&1 || true

if [ -f "$V2_DIR/edition_k3.json" ] && python3 -c "import json; json.load(open('$V2_DIR/edition_k3.json'))" 2>/dev/null 2>&1; then
    echo "  ✓ edition_k3.json written"
else
    echo "  ✗ edition_k3.json MISSING or INVALID — k3 edition will be skipped"
    echo "{}" > "$V2_DIR/edition_k3.json"
fi
check_timeout

# ── Step 5: Image Gen (with pre-check for xAI credits) ──────
echo "[step 5] image gen..."
SKIP_IMAGES=false

# Check if xAI credits are available before even launching the agent
if grep -q "personal-team-blocked:spending-limit" "$LOG_DIR/imagegen_${TODAY}.log" 2>/dev/null; then
    SKIP_IMAGES=true
fi

if [ "$SKIP_IMAGES" = false ]; then
    "$HERMES_BIN" chat -q "You are the Image Generator for Lux in Tenebris. Load skill image-gen-v2.
Today is $TODAY. Read $V2_DIR/edition.json.
Generate images for lead + each non-empty section using image_generate tool.
Save images to $V2_DIR/images/. Update edition.json. ENGLISH ONLY." \
        --profile "$PROFILE" -s image-gen-v2 -t file,image_gen,terminal -m deepseek-v4-flash --provider localAIServer -Q --yolo \
        >"$LOG_DIR/imagegen_${TODAY}.log" 2>&1 || true
fi

# Check if it failed due to credits
if grep -q "spending-limit\|credits exhausted\|403" "$LOG_DIR/imagegen_${TODAY}.log" 2>/dev/null; then
    echo "  ⚠ xAI credits exhausted — will skip images for next runs too"
    SKIP_IMAGES=true
fi

echo "  ✓ image gen complete ($([ "$SKIP_IMAGES" = true ] && echo 'skipped - no credits' || echo 'done'))"
check_timeout

# ── Step 6: Render HTML ─────────────────────────────────────
echo "[step 6] render..."
if [ -f "$RENDER_PY" ] && [ -f "$V2_DIR/edition.json" ]; then
    python3 "$RENDER_PY" "$V2_DIR/edition.json" "$OUTPUT_DIR/index.html" --templates "$TEMPLATE_DIR" 2>>"$LOGFILE"
    echo "  ✓ rendered → $OUTPUT_DIR/index.html"
else
    echo "  ✗ render.py or edition.json missing"
    exit 1
fi

# K3 edition removed per user request (2026-07-25)

# ── Step 6d: Inject version badges ───────────────────────────
echo "[step 6d] injecting version badges..."
BADGE_SCRIPT="$SCRIPT_DIR/inject_version_badge.py"

# Inject DS badge into main index.html
if [ -f "$OUTPUT_DIR/index.html" ] && [ -f "$BADGE_SCRIPT" ]; then
    python3 "$BADGE_SCRIPT" "$OUTPUT_DIR/index.html" ds \
        --output "$OUTPUT_DIR/index.html" 2>>"$LOGFILE" || true
fi

# Inject K3 badge into k3/index.html
if [ -f "$K3_OUTPUT_DIR/index.html" ] && [ -f "$BADGE_SCRIPT" ]; then
    python3 "$BADGE_SCRIPT" "$K3_OUTPUT_DIR/index.html" k3 \
        --output "$K3_OUTPUT_DIR/index.html" 2>>"$LOGFILE" || true
fi
echo "  ✓ version badges injected"

# ── Step 6e: Transform K3 layout to White Edition ────────────
echo "[step 6e] transforming k3 layout to white edition..."
LAYOUT_SCRIPT="$SCRIPT_DIR/transform_layout_k3.py"
if [ -f "$K3_OUTPUT_DIR/index.html" ] && [ -f "$LAYOUT_SCRIPT" ]; then
    python3 "$LAYOUT_SCRIPT" "$K3_OUTPUT_DIR/index.html" \
        --output "$K3_OUTPUT_DIR/index.html" 2>>"$LOGFILE" || true
    echo "  ✓ k3 layout transformed to white edition"
fi

# ── Step 7: Podcast Pill ─────────────────────────────────────
echo "[step 7] podcast pill..."
SKIP_PODCAST=false

# Skip podcast if xAI credits are known exhausted
[ "$SKIP_IMAGES" = true ] && SKIP_PODCAST=true

if [ "$SKIP_PODCAST" = false ]; then
    PODCAST_META="$V2_DIR/podcast_meta.json"
    PODCAST_INJECT="$SCRIPT_DIR/inject_podcast_pill.py"
    mkdir -p "$V2_DIR/podcasts"
    
    "$HERMES_BIN" chat -q "You are the Podcast Pill generator. Load skill podcast-pill.
Today is $TODAY. Issue #$NEXT_ISSUE.
Read $V2_DIR/edition.json. Generate Castor/Luna dialogue from lead.
Produce TTS audio, concat with ffmpeg, write metadata to $V2_DIR/podcast_meta.json.
Use text_to_speech tool. Use terminal for ffmpeg. ENGLISH ONLY." \
        --profile "$PROFILE" -s podcast-pill -t file,terminal -m deepseek-v4-flash --provider localAIServer -Q --yolo \
        >"$LOG_DIR/podcast_${TODAY}.log" 2>&1 || true
    
    # Inject podcast pill into HTML (if metadata was generated)
    if [ -f "$V2_DIR/podcast_meta.json" ]; then
        META=$(python3 -c "
import json
with open('$V2_DIR/podcast_meta.json') as f:
    m = json.load(f)
print(m.get('ogg_rel_path', ''))
print(m.get('duration_sec', 0))
") 2>/dev/null || META=""
        OGG_REL=$(echo "$META" | sed -n '1p')
        DUR=$(echo "$META" | sed -n '2p')
        if [ -n "$OGG_REL" ] && [ "${DUR:-0}" -gt 0 ] 2>/dev/null; then
            python3 "$PODCAST_INJECT" \
                "$OUTPUT_DIR/index.html" \
                "$OGG_REL" \
                "$DUR" \
                --output "$OUTPUT_DIR/index.html" \
                2>>"$LOGFILE" && echo "  ✓ podcast pill injected" || echo "  ⚠ podcast pill injection failed"
            # Also inject into k3 version if it exists
            if [ -f "$K3_OUTPUT_DIR/index.html" ]; then
                python3 "$PODCAST_INJECT" \
                    "$K3_OUTPUT_DIR/index.html" \
                    "$OGG_REL" \
                    "$DUR" \
                    --output "$K3_OUTPUT_DIR/index.html" \
                    2>>"$LOGFILE" && echo "  ✓ podcast pill injected into k3" || echo "  ⚠ k3 podcast injection failed"
            fi
        else
            echo "  - podcast meta incomplete, skipping injection"
        fi
    else
        echo "  - podcast meta not found, skipping"
    fi
else
    echo "  - podcast pill skipped (xAI credits unavailable)"
fi
check_timeout

# ── Step 8: Wire Articles ────────────────────────────────────
echo "[step 8] wire articles..."
WIRE_SCRIPT="$SCRIPT_DIR/wire_articles.py"
if [ -f "$WIRE_SCRIPT" ]; then
    # Wire articles for DeepSeek edition
    python3 "$WIRE_SCRIPT" --max 5 --out "$SCOUTS_DIR/scout_wire_ds.json" 2>>"$LOGFILE" || \
        echo "  ⚠ wire articles DS failed (non-fatal)"
    WIRE_COUNT_DS=$(python3 -c "import json;d=json.load(open('$SCOUTS_DIR/scout_wire_ds.json'));print(len(d))" 2>/dev/null || echo "0")
    echo "  ✓ $WIRE_COUNT_DS wire articles (DS) written"
    
    # Wire articles for Kimi K3 edition
    python3 "$WIRE_SCRIPT" --max 5 --out "$SCOUTS_DIR/scout_wire_k3.json" --model kimi-k3 --provider localAIServer 2>>"$LOGFILE" || \
        echo "  ⚠ wire articles K3 failed (non-fatal)"
    WIRE_COUNT_K3=$(python3 -c "import json;d=json.load(open('$SCOUTS_DIR/scout_wire_k3.json'));print(len(d))" 2>/dev/null || echo "0")
    echo "  ✓ $WIRE_COUNT_K3 wire articles (K3) written"
else
    echo "  - wire_articles.py not found, skipping"
fi
# This step renamed because we numbered incorrectly
echo "[step 8] inject wire ticker..."
INJECT_SCRIPT="$SCRIPT_DIR/inject_wire_ticker.py"

# Inject DS wire into main index.html
if [ "${WIRE_COUNT_DS:-0}" -gt 0 ] && [ -f "$INJECT_SCRIPT" ] && [ -f "$OUTPUT_DIR/index.html" ]; then
    python3 "$INJECT_SCRIPT" "$OUTPUT_DIR/index.html" "$SCOUTS_DIR/scout_wire_ds.json" --output "$OUTPUT_DIR/index.html" 2>>"$LOGFILE" || \
        echo "  ⚠ DS ticker injection failed (non-fatal)"
    echo "  ✓ DS ticker injected"
else
    echo "  - no DS wire articles, skipping DS ticker"
fi

# Inject K3 wire into k3/index.html
if [ "${WIRE_COUNT_K3:-0}" -gt 0 ] && [ -f "$INJECT_SCRIPT" ] && [ -f "$K3_OUTPUT_DIR/index.html" ]; then
    python3 "$INJECT_SCRIPT" "$K3_OUTPUT_DIR/index.html" "$SCOUTS_DIR/scout_wire_k3.json" --output "$K3_OUTPUT_DIR/index.html" 2>>"$LOGFILE" || \
        echo "  ⚠ K3 ticker injection failed (non-fatal)"
    echo "  ✓ K3 ticker injected"
else
    echo "  - no K3 wire articles, skipping K3 ticker"
fi
check_timeout

# ── Step 9: Deploy ───────────────────────────────────────────
SSH_URL="git@github.com:NTTLuke/luxintenebris-ai-news.git"
echo "[step 9] deploying to production..."

cd "$DEPLOY_DIR"
git fetch origin --quiet 2>/dev/null || true
git reset --hard origin/main --quiet 2>/dev/null || true

# Write issue number AFTER git reset so it survives the commit
echo "$NEXT_ISSUE" > "$DEPLOY_DIR/.issue"

# ── Step 10: Copy files ───────────────────────────────────────
echo "[step 10] copying files..."
cp "$OUTPUT_DIR/index.html" "$DEPLOY_DIR/index.html"
if [ -d "$OUTPUT_DIR/k3" ]; then
    mkdir -p "$DEPLOY_DIR/k3"
    cp "$OUTPUT_DIR/k3/index.html" "$DEPLOY_DIR/k3/index.html"
    echo "  ✓ k3 edition copied"
fi
cp -r "$OUTPUT_DIR/fonts"/* "$DEPLOY_DIR/fonts/" 2>/dev/null || true
mkdir -p "$DEPLOY_DIR/images"
cp "$IMAGES_DIR"/*.jpg "$DEPLOY_DIR/images/" 2>/dev/null || true
mkdir -p "$DEPLOY_DIR/podcasts"
cp /tmp/v2/podcasts/*.ogg "$DEPLOY_DIR/podcasts/" 2>/dev/null || true
echo "  ✓ files copied to deploy dir"
TEMPLATE_DIR="/home/nttluke/lux-in-tenebris-pipeline/template"
if [ -f "$TEMPLATE_DIR/style.css" ]; then
    cp "$TEMPLATE_DIR/style.css" "$DEPLOY_DIR/style.css"
    echo "  ✓ style.css copied from template"
else
    echo "  ⚠ template style.css not found"
fi

cp "$V2_DIR/edition.json" "$DEPLOY_DIR/edition.json"
echo "  ✓ edition.json saved to deploy dir"
if [ -f "$V2_DIR/edition_k3.json" ]; then
    cp "$V2_DIR/edition_k3.json" "$DEPLOY_DIR/k3/edition.json"
    echo "  ✓ k3 edition.json saved to deploy dir"
fi

# ── Step 11: Archive ─────────────────────────────────────────
echo "[step 11] archiving current issue..."
ARCHIVE_SCRIPT="$SCRIPT_DIR/archive_issue.py"
if [ -f "$ARCHIVE_SCRIPT" ]; then
    python3 "$ARCHIVE_SCRIPT" "$DEPLOY_DIR" 2>>"$LOGFILE" || echo "  ⚠ archive failed (non-fatal)"
    echo "  ✓ archived"
fi

python3 "$SCRIPT_DIR/update_headlines_history.py" \
    "$V2_DIR/edition.json" \
    "$DEPLOY_DIR/headlines_history.json" \
    2>>"$LOGFILE" && echo "  ✓ headlines history updated" || echo "  ⚠ headlines history update failed"

cd "$DEPLOY_DIR"
git add -A
if ! git diff --cached --quiet; then
    git commit -m "Update AI news $TODAY" --quiet 2>/dev/null || true
fi
git push origin main --quiet 2>/dev/null || echo "  ⚠ git push failed — will retry on next run"
echo "  ✓ pushed to GitHub"

# ── Report ──────────────────────────────────────────────────
IMG_COUNT=$(find "$IMAGES_DIR" -name '*.jpg' 2>/dev/null | wc -l)
echo ""
echo "═══════════════════════════════════════════════"
echo "✅ V2 PIPELINE COMPLETE — $(date '+%H:%M:%S')"
echo "  Issue:   #$NEXT_ISSUE"
echo "  Date:    $TODAY"
echo "  Scouts:  $SCOUT_COUNT/9"
echo "  DS edition: ✅ ($([ -f "$V2_DIR/edition.json" ] && echo 'generated' || echo 'failed'))"
echo "  K3 edition: $([ -f "$V2_DIR/edition_k3.json" ] && [ -f "$OUTPUT_DIR/k3/index.html" ] && echo '✅ rendered' || echo '⏭ skipped')"
echo "  Wire:    DS:${WIRE_COUNT_DS:-0}  K3:${WIRE_COUNT_K3:-0} articles"
echo "  Images:  $IMG_COUNT ($([ "$SKIP_IMAGES" = true ] && echo 'skipped - no xAI credits' || echo 'generated'))"
echo "  Podcast: $([ "$SKIP_PODCAST" = true ] && echo 'skipped - no xAI credits' || echo 'attempted')"
echo "  Deploy:  $DEPLOY_DIR"
echo "  Pushed:  github.com/nttluke/luxintenebris-ai-news"
echo "═══════════════════════════════════════════════"
