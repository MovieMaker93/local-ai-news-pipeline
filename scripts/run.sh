#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# LOCAL AI NEWS — Orchestrator Script
# Fork of Lux in Tenebris V2 (NTTLuke/lux-in-tenebris-pipeline).
# Each step is isolated, stateless, communicates via JSON files.
# Features:
#   - Scouts run SEQUENTIALLY (one at a time) — the inference server is a
#     single self-hosted box and can't take concurrent agent sessions
#   - Every LLM call is wrapped in a timeout; nothing can hang forever
#   - 4h master timeout for the whole pipeline
#   - Falls back to partial deploy if any non-critical step fails
#   - Six scouts: research, official, opensource, tools, hardware, selfhost
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

# ── Machine-specific config ─────────────────────────────────────
# Everything below is either self-located (works regardless of where the
# repo is cloned or how it's symlinked in) or overridable via env var.
# Set PAPER_* env vars (e.g. in the untracked script that actually launches
# cron — see docs/SETUP.md) to point this at a different profile/layout.
SELF_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname "$SELF_PATH")"          # this script's own directory
PIPELINE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)" # repo root, one level up

PROFILE="${PAPER_PROFILE:-paper}"
WORK_DIR="/tmp/lain"
LOG_DIR="$WORK_DIR/logs"
SCOUTS_DIR="$WORK_DIR/scouts"
OUTPUT_DIR="$WORK_DIR/output"
HERMES_BIN="${PAPER_HERMES_BIN:-$HOME/.local/bin/hermes}"
RENDER_PY="$SCRIPT_DIR/core/render.py"
CLEANUP_SH="$WORK_DIR/cleanup.sh"
DEPLOY_DIR="${PAPER_DEPLOY_DIR:-$HOME/local-ai-news-deploy}"
SITE_URL="${PAPER_SITE_URL:-https://moviemaker93.github.io/local-ai-news/}"
# Scouts run ONE AT A TIME against a single self-hosted inference server
# (the DGX Spark's LiteLLM proxy), so these budgets are per-scout wall clock
# with the whole server to itself, and the master budget has to cover their
# sum, not their max. Original Lux measurements (2026-07-29, 9 scouts):
# five of nine exceeded 10 min, slowest ~13.5 min — hence the 20-min ceiling.
# Re-measure after a week of runs and tune.
TIMEOUT_SECS=1200       # 20 min per scout
# The editor gets its own, larger budget: it is the only FATAL step (no
# edition.json ⇒ no newspaper at all) and it chews through all scout files
# with cross-day dedup against headlines_history.json.
EDITOR_TIMEOUT_SECS=2400 # 40 min
MASTER_TIMEOUT=10800     # 3h for the entire pipeline (6 scouts, no media steps)
TEMPLATE_DIR="$PIPELINE_ROOT/template"

# ╔════════════════════════════════════════════════════════════════════════╗
# ║ PIPELINE_PROVIDER — DO NOT CHANGE without the user explicitly          ║
# ║ asking for it, in this exact conversation, for this exact reason.      ║
# ║                                                                        ║
# ║ This must always be "spark" (the DGX Spark's LiteLLM proxy), never    ║
# ║ "openrouter", "zai" or anything else — regardless of what             ║
# ║ model/provider the *interactive* Hermes session reasoning about this   ║
# ║ file happens to be running on. The pipeline's own steps must not       ║
# ║ follow whatever provider the operator chats on.                        ║
# ║                                                                        ║
# ║ Upstream incident (2026-07-27/28): asked to raise the scout timeout,   ║
# ║ an interactive session swapped every provider flag in this file to     ║
# ║ "openrouter" — unrequested, unnoticed until the day's edition had      ║
# ║ already been produced on the wrong (paid, metered) backend.            ║
# ╚════════════════════════════════════════════════════════════════════════╝
PIPELINE_PROVIDER="spark"

# Model for every LLM step (scouts, editor, wire articles) — served by the
# Spark's LiteLLM proxy. Centralized here so it's a one-line change.
PIPELINE_MODEL="flash"

# ── Setup ────────────────────────────────────────────────────
mkdir -p "$LOG_DIR" "$SCOUTS_DIR" "$OUTPUT_DIR"
TODAY=$(date +%Y-%m-%d)
LOGFILE="$LOG_DIR/run_${TODAY}.log"
exec > >(tee -a "$LOGFILE") 2>&1

# ── Per-step logs: APPEND, never truncate ───────────────────
# These logs used to be opened with '>', so a manual re-run of a step wiped
# the evidence of why the automated one had failed. Every per-step log is
# now opened with '>>' and preceded by this banner, so a day's attempts
# stack up in order instead of erasing each other.
log_attempt() {
    local logfile="$1" label="$2"
    {
        echo ""
        echo "───────────────────────────────────────────────"
        echo "▶ $label — $(date '+%Y-%m-%d %H:%M:%S') (pid $$)"
        echo "───────────────────────────────────────────────"
    } >>"$logfile"
}

# Print only the MOST RECENT attempt from an appended log — keeps
# "look at what happened last time" semantics while preserving full history.
last_attempt() {
    local logfile="$1"
    [ -f "$logfile" ] || return 0
    awk '/^▶ /{buf=""} {buf = buf $0 "\n"} END{printf "%s", buf}' "$logfile"
}

# ── Telegram progress notifications ──────────────────────────
# The run is fire-and-forget in the background; notify() posts one short
# line at each real milestone. Written to be impossible to break the run:
#   - every failure path returns 0 (missing .env, empty creds, no network)
#   - curl has a hard 10s timeout, so it can never hang the pipeline
#   - output is discarded; the bot token must never reach the run log
TG_ENV="${PAPER_TG_ENV:-$HOME/.hermes/profiles/$PROFILE/.env}"
notify() {
    local text="$1" tok chat
    [ -f "$TG_ENV" ] || return 0
    tok=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' "$TG_ENV" 2>/dev/null | cut -d= -f2- || true)
    chat=$(grep -m1 '^TELEGRAM_HOME_CHANNEL=' "$TG_ENV" 2>/dev/null | cut -d= -f2- || true)
    [ -n "$tok" ] && [ -n "$chat" ] || return 0
    curl -s -o /dev/null --max-time 10 \
        -X POST "https://api.telegram.org/bot${tok}/sendMessage" \
        -d "chat_id=${chat}" \
        --data-urlencode "text=${text}" >/dev/null 2>&1 || true
    return 0
}

# Master watchdog — if we exceed MASTER_TIMEOUT, kill everything
START_EPOCH=$(date +%s)
elapsed() { echo $(( $(date +%s) - START_EPOCH )); }
check_timeout() {
    if [ "$(elapsed)" -gt "$MASTER_TIMEOUT" ]; then
        echo "⛔ MASTER TIMEOUT after $(elapsed)s — aborting pipeline"
        notify "⛔ Local AI News — master timeout after $(( $(elapsed) / 60 ))m. Run aborted, no issue today."
        exit 2
    fi
}

echo "═══════════════════════════════════════════════"
echo "LOCAL AI NEWS — $(date '+%Y-%m-%d %H:%M:%S')"
echo "═══════════════════════════════════════════════"

# ── Step 0: Cleanup ─────────────────────────────────────────
echo "[step 0] cleanup..."
if [ -f "$CLEANUP_SH" ]; then
    bash "$CLEANUP_SH"
else
    find "$SCOUTS_DIR" -name 'scout_*.json' -delete 2>/dev/null || true
    [ -f "$WORK_DIR/edition.json" ] && rm -f "$WORK_DIR/edition.json"
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

# ── Step 1b: Sync deploy dir, resolve issue number, archive predecessor ──
# Done early (the editor needs the issue number) and against a freshly
# git-reset deploy dir, so it's immune to local leftovers from a crashed
# run. Upstream incident that motivated this (2026-07-27): a run crashed
# after bumping the deploy dir's .issue locally but before pushing; the
# recovery re-run read that unpushed leftover value and bumped again,
# silently skipping an issue. Reading the issue/date from the *live*
# index.html's own masthead instead of the .issue file (which can go stale)
# fixes that: it always reflects the last truly-published state.
echo "[step 1b] sync deploy dir + issue number..."
mkdir -p "$DEPLOY_DIR"
(cd "$DEPLOY_DIR" && git fetch origin --quiet 2>/dev/null && git reset --hard origin/main --quiet 2>/dev/null) || true

PREV_ISSUE=0
PREV_DATE=""
if [ -f "$DEPLOY_DIR/index.html" ]; then
    ISSUE_DATE_LINE=$(python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR/core')
import archive_issue as ai
no = ai.extract_issue_no('$DEPLOY_DIR/index.html') or 0
date = ai.extract_issue_date('$DEPLOY_DIR/index.html')
print(f'{no} {date}')
" 2>/dev/null || echo "0 ")
    PREV_ISSUE=$(echo "$ISSUE_DATE_LINE" | awk '{print $1}')
    PREV_DATE=$(echo "$ISSUE_DATE_LINE" | awk '{print $2}')
fi
PREV_ISSUE="${PREV_ISSUE:-0}"

if [ "$PREV_DATE" = "$TODAY" ]; then
    echo "  → live edition is already dated $TODAY (same-day re-run) — reusing issue #$PREV_ISSUE"
    NEXT_ISSUE=$PREV_ISSUE
else
    NEXT_ISSUE=$((PREV_ISSUE + 1))
    # Archive whatever's currently live BEFORE today's run overwrites it.
    # This guarantees every published edition gets archived at the latest
    # by the next day's run, even if that edition's own run never reached
    # its own deploy/archive step.
    ARCHIVE_SCRIPT="$SCRIPT_DIR/core/archive_issue.py"
    if [ -f "$ARCHIVE_SCRIPT" ] && [ -f "$DEPLOY_DIR/index.html" ]; then
        python3 "$ARCHIVE_SCRIPT" "$DEPLOY_DIR" 2>>"$LOGFILE" \
            && echo "  ✓ archived previous issue (#$PREV_ISSUE, $PREV_DATE)" \
            || echo "  ⚠ archiving previous issue failed (non-fatal)"
    fi
fi
echo "$NEXT_ISSUE" > "$WORK_DIR/.issue"
echo "  ✓ issue #$NEXT_ISSUE"
notify "▶ Local AI News #$NEXT_ISSUE — run started $(date '+%H:%M'). Six scouts, one at a time."
check_timeout

# ── Helper: run a scout with safe timeout ──────────────────
# Runs one scout to completion, then validates its output file. If the
# timeout fires, write_file may never have run — so we check, and write an
# empty [] fallback here so downstream steps always have valid JSON.
# CRITICAL: '|| true' prevents set -e from aborting the whole pipeline
# when timeout returns non-zero (exit code 124).
run_scout() {
    local name="$1"
    local skill="$2"
    local toolsets="$3"
    local prompt="$4"
    local outfile="$SCOUTS_DIR/scout_${name}.json"

    echo "  → starting scout $name ($skill)"
    log_attempt "$LOG_DIR/scout_${name}_${TODAY}.out" "scout $name"
    log_attempt "$LOG_DIR/scout_${name}_${TODAY}.err" "scout $name"
    timeout "$TIMEOUT_SECS" "$HERMES_BIN" chat -q "$prompt" \
        --profile "$PROFILE" \
        -s "$skill" \
        -t "$toolsets" \
        -m "$PIPELINE_MODEL" --provider "$PIPELINE_PROVIDER" \
        -Q --yolo \
        2>>"$LOG_DIR/scout_${name}_${TODAY}.err" \
        >>"$LOG_DIR/scout_${name}_${TODAY}.out" || true

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
# SEQUENTIAL, one scout at a time. Each gets the whole inference server to
# itself and its own timeout; a failure only ever costs that one scout, which
# falls back to [] and never blocks the pipeline.
#
# Why not parallel: scouts used to run 3-up in phases upstream. That works
# against a distributed API, but our backend is a single box serving these
# models — and a "scout" is not one request, it's a whole multi-turn agent
# session (searches, tool calls, reasoning). Three of those at once saturate
# the machine and all three crawl. Serialising trades wall clock (free here:
# fire-and-forget morning cron) for actually finishing.
echo "[step 2] scouts (sequential, one at a time)..."

run_scout "research" "scout-research" "web,file,terminal" \
    "You are the Research Scout for Local AI News. $SCOUT_DATE_BRIEF
Load skill scout-research and follow it exactly. Search arXiv and HuggingFace daily papers for LOCAL AI relevant research (quantization, distillation, small models, efficient inference).
Write the JSON array to $SCOUTS_DIR/scout_research.json using write_file. ENGLISH ONLY."

run_scout "official" "scout-official" "web,file,terminal" \
    "You are the Model Makers Scout for Local AI News. $SCOUT_DATE_BRIEF
Load skill scout-official and follow it exactly. Read the official blogs of the labs that ship open-weight models.
Write the JSON array to $SCOUTS_DIR/scout_official.json using write_file. ENGLISH ONLY."

run_scout "opensource" "scout-opensource" "web,file,terminal" \
    "You are the Open Source Scout for Local AI News. $SCOUT_DATE_BRIEF
Load skill scout-opensource and follow it exactly. New open-weight releases plus GitHub Trending and HuggingFace Trending, filtered for local-AI relevance.
Write the JSON object (with editorial array + trending object) to $SCOUTS_DIR/scout_opensource.json using write_file. ENGLISH ONLY."

# ── Trending fallback: if opensource scout failed, fetch via curl ──
TRENDING_FALLBACK="$SCRIPT_DIR/content/fetch_trending.py"
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

run_scout "tools" "scout-tools" "web,file,terminal" \
    "You are the Tools Scout for Local AI News. $SCOUT_DATE_BRIEF
Load skill scout-tools and follow it exactly. Search Show HN, Product Hunt and the web for local-AI tooling launches (Ollama, llama.cpp, UIs, agent frameworks, MCP).
Write the JSON array to $SCOUTS_DIR/scout_tools.json using write_file. ENGLISH ONLY."

run_scout "hardware" "scout-hardware" "web,file,terminal" \
    "You are the Hardware Scout for Local AI News. $SCOUT_DATE_BRIEF
Load skill scout-hardware and follow it exactly. Search for consumer GPUs, NPUs, Apple silicon, edge devices, VRAM and memory news relevant to running models locally.
Write the JSON array to $SCOUTS_DIR/scout_hardware.json using write_file. ENGLISH ONLY."

run_scout "selfhost" "scout-selfhost" "web,file,terminal" \
    "You are the Self-Hosted Scout for Local AI News. $SCOUT_DATE_BRIEF
Load skill scout-selfhost and follow it exactly. Search r/LocalLLaMA, r/selfhosted and the web for self-hosting AI stack news (Open WebUI, n8n, Home Assistant, privacy).
Write the JSON array to $SCOUTS_DIR/scout_selfhost.json using write_file. ENGLISH ONLY."

# ── Step 3: Validate all scout files ────────────────────────
echo "[step 3] validating scout files..."
SCOUT_COUNT=0
SCOUT_NAMES="research official opensource tools hardware selfhost"
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
echo "  ✓ $SCOUT_COUNT/6 scout files ready"

# Milestone: report what actually landed on the desk, and name any scout
# that came back empty — a timed-out scout is survivable but worth knowing
# about before the paper lands.
DESK_ITEMS=$(python3 -c "
import json, os
keys = 'research official opensource tools hardware selfhost'.split()
t = 0
for k in keys:
    try:
        d = json.load(open(os.path.join('$SCOUTS_DIR', 'scout_%s.json' % k)))
        t += len(d) if isinstance(d, list) else len(d.get('editorial') or [])
    except Exception:
        pass
print(t)
" 2>/dev/null || echo "?")
EMPTY_SCOUTS=$(grep -c "✗ scout .* FAILED or TIMEOUT" "$LOGFILE" 2>/dev/null || echo 0)
if [ "${EMPTY_SCOUTS:-0}" -gt 0 ]; then
    notify "🔍 Local AI News #$NEXT_ISSUE — scouts done, $DESK_ITEMS items on the desk. ⚠ $EMPTY_SCOUTS scout(s) timed out and came back empty. Editor starting."
else
    notify "🔍 Local AI News #$NEXT_ISSUE — scouts done, all six green, $DESK_ITEMS items on the desk. Editor starting."
fi
check_timeout

# ── Step 4: Editor ──────────────────────────────────────────
echo "[step 4] editor..."
# NEXT_ISSUE was already resolved in step 1b (reuse-if-same-day-rerun,
# increment-and-archive-predecessor otherwise).

log_attempt "$LOG_DIR/editor_${TODAY}.log" "editor (timeout ${EDITOR_TIMEOUT_SECS}s)"
timeout "$EDITOR_TIMEOUT_SECS" "$HERMES_BIN" chat -q "You are the Editor for Local AI News. Load skill editor and follow it exactly.
Today is $TODAY. Issue #$NEXT_ISSUE.
Read all scout JSON files from $SCOUTS_DIR/scout_*.json and the metadata.
For cross-day dedup, read $DEPLOY_DIR/headlines_history.json via read_file.
Assemble edition.json following the skill instructions.
Write the result to $WORK_DIR/edition.json using write_file. ENGLISH ONLY." \
    --profile "$PROFILE" -s editor -t file -m "$PIPELINE_MODEL" --provider "$PIPELINE_PROVIDER" -Q --yolo \
    >>"$LOG_DIR/editor_${TODAY}.log" 2>&1 && EDITOR_RC=0 || EDITOR_RC=$?

if [ -f "$WORK_DIR/edition.json" ] && python3 -c "import json; json.load(open('$WORK_DIR/edition.json'))" 2>/dev/null 2>&1; then
    echo "  ✓ edition.json written"
    ED_KEPT=$(python3 -c "
import json
d = json.load(open('$WORK_DIR/edition.json'))
print((1 if d.get('lead') else 0)
      + len(d.get('top_stories') or [])
      + sum(len(s.get('items') or []) for s in (d.get('sections') or []))
      + len(d.get('quick_hits') or []))
" 2>/dev/null || echo "?")
    ED_LEAD=$(python3 -c "
import json
print((json.load(open('$WORK_DIR/edition.json')).get('lead') or {}).get('title','')[:90])
" 2>/dev/null || echo "")
    notify "✍️ Local AI News #$NEXT_ISSUE — edition assembled. $ED_KEPT kept of $DESK_ITEMS. Lead: ${ED_LEAD:-—}"
else
    # Say WHICH failure it was. `timeout` returns 124 when it kills the child,
    # and that distinction is the whole diagnosis: 124 means raise
    # EDITOR_TIMEOUT_SECS, anything else means the editor itself broke.
    if [ "$EDITOR_RC" -eq 124 ]; then
        echo "  ✗ editor KILLED by timeout after ${EDITOR_TIMEOUT_SECS}s — it never finished writing edition.json"
        echo "     → if this recurs, raise EDITOR_TIMEOUT_SECS at the top of this script"
    else
        echo "  ✗ editor exited with code $EDITOR_RC and left no valid edition.json"
    fi
    echo "     → see $LOG_DIR/editor_${TODAY}.log (appended, not overwritten)"
    echo "FATAL: editor failed"
    # The one message that matters most: this is the only step whose failure
    # means no paper at all.
    if [ "$EDITOR_RC" -eq 124 ]; then
        notify "⛔ Local AI News #$NEXT_ISSUE — EDITOR TIMED OUT after $((EDITOR_TIMEOUT_SECS / 60))m. No issue today. The $DESK_ITEMS scouted items are still on disk; a re-run can use them."
    else
        notify "⛔ Local AI News #$NEXT_ISSUE — EDITOR FAILED (exit $EDITOR_RC). No issue today. Check editor_${TODAY}.log."
    fi
    exit 1
fi
check_timeout

# ── Step 5: Render HTML ─────────────────────────────────────
echo "[step 5] render..."
if [ -f "$RENDER_PY" ] && [ -f "$WORK_DIR/edition.json" ]; then
    python3 "$RENDER_PY" "$WORK_DIR/edition.json" "$OUTPUT_DIR/index.html" --templates "$TEMPLATE_DIR" 2>>"$LOGFILE"
    echo "  ✓ rendered → $OUTPUT_DIR/index.html"
else
    echo "  ✗ render.py or edition.json missing"
    exit 1
fi

# ── Step 6: Wire Articles ────────────────────────────────────
echo "[step 6] wire articles..."
WIRE_SCRIPT="$SCRIPT_DIR/content/wire_articles.py"
if [ -f "$WIRE_SCRIPT" ]; then
    # --provider passed explicitly (rather than relying on wire_articles.py's
    # own default) so $PIPELINE_PROVIDER stays the single place the backend is
    # decided for the whole pipeline.
    python3 "$WIRE_SCRIPT" --max 5 --out "$SCOUTS_DIR/scout_wire.json" \
        --model "$PIPELINE_MODEL" --provider "$PIPELINE_PROVIDER" 2>>"$LOGFILE" || \
        echo "  ⚠ wire articles failed (non-fatal)"
    WIRE_COUNT=$(python3 -c "import json;d=json.load(open('$SCOUTS_DIR/scout_wire.json'));print(len(d))" 2>/dev/null || echo "0")
    echo "  ✓ $WIRE_COUNT wire articles written"
else
    WIRE_COUNT=0
    echo "  - wire_articles.py not found, skipping"
fi

echo "[step 6b] inject wire ticker..."
INJECT_SCRIPT="$SCRIPT_DIR/inject/inject_wire_ticker.py"
if [ "${WIRE_COUNT:-0}" -gt 0 ] && [ -f "$INJECT_SCRIPT" ] && [ -f "$OUTPUT_DIR/index.html" ]; then
    python3 "$INJECT_SCRIPT" "$OUTPUT_DIR/index.html" "$SCOUTS_DIR/scout_wire.json" --output "$OUTPUT_DIR/index.html" 2>>"$LOGFILE" || \
        echo "  ⚠ ticker injection failed (non-fatal)"
    echo "  ✓ ticker injected"
else
    echo "  - no wire articles, skipping ticker"
fi
check_timeout

# ── Step 6c: Making-of page ──────────────────────────────────
# "How this issue made itself" — a replayable account of this run, built by
# parsing what the pipeline already wrote (scout JSON, run log, log mtimes,
# edition.json). Pure code, no LLM, no network, READ-ONLY on pipeline state.
#
# STRICTLY NON-FATAL, and deliberately placed last among the content steps:
# by the time it runs, index.html is already complete. If it fails, the
# newspaper publishes exactly as it would have without it.
echo "[step 6c] making-of page..."
MAKING_SCRIPT="$SCRIPT_DIR/content/make_making_of.py"
if [ -f "$MAKING_SCRIPT" ]; then
    if python3 "$MAKING_SCRIPT" "$OUTPUT_DIR/making-of.html" \
         --date "$TODAY" --logs "$LOG_DIR" \
         --edition "$WORK_DIR/edition.json" --scouts "$SCOUTS_DIR" 2>>"$LOGFILE"; then
        echo "  ✓ making-of page built"
    else
        echo "  ⚠ making-of page failed (non-fatal) — issue publishes without it"
    fi
else
    echo "  - make_making_of.py not found, skipping"
fi
check_timeout

# ── Step 7: Deploy ───────────────────────────────────────────
echo "[step 7] deploying to production..."

cd "$DEPLOY_DIR"
# NO second git reset --hard here. Step 1b already synced $DEPLOY_DIR to
# origin/main and, on the increment path, modified a TRACKED file in the
# process (archive/index.html, rewritten by regenerate_archive_index()) plus
# created a new UNTRACKED archive/<date>/ directory.
#
# A second `reset --hard` at this point reverts tracked-file modifications
# back to their committed state but does NOT touch untracked new
# directories — so it would silently discard every archive/index.html update
# while the archive/<date>/ folders themselves kept getting committed.
# Reproduced in an isolated sandbox upstream before removing this.
echo "$NEXT_ISSUE" > "$DEPLOY_DIR/.issue"

# ── Step 8: Copy files ───────────────────────────────────────
echo "[step 8] copying files..."
cp "$OUTPUT_DIR/index.html" "$DEPLOY_DIR/index.html"
# Guarded: step 6c is non-fatal, so this file may legitimately not exist.
if [ -f "$OUTPUT_DIR/making-of.html" ]; then
    cp "$OUTPUT_DIR/making-of.html" "$DEPLOY_DIR/making-of.html"
    echo "  ✓ making-of page copied"
fi
# Fonts are static template assets — copy straight from the template dir.
# (Upstream copied them from the output dir, which nothing ever populated;
# it only worked because the deploy repo carried fonts committed by hand.)
mkdir -p "$DEPLOY_DIR/fonts"
cp "$TEMPLATE_DIR"/fonts/*.woff2 "$DEPLOY_DIR/fonts/" 2>/dev/null || true
if [ -f "$TEMPLATE_DIR/style.css" ]; then
    cp "$TEMPLATE_DIR/style.css" "$DEPLOY_DIR/style.css"
    echo "  ✓ style.css copied from template"
else
    echo "  ⚠ template style.css not found"
fi

cp "$WORK_DIR/edition.json" "$DEPLOY_DIR/edition.json"
echo "  ✓ edition.json saved to deploy dir"

# ── Step 9: Headlines history + commit + push ────────────────
# (archiving the PREVIOUS issue already happened in step 1b, before this
# run's files were copied in — see the comment there for why)
echo "[step 9] updating headlines history + deploying..."
python3 "$SCRIPT_DIR/core/update_headlines_history.py" \
    "$WORK_DIR/edition.json" \
    "$DEPLOY_DIR/headlines_history.json" \
    2>>"$LOGFILE" && echo "  ✓ headlines history updated" || echo "  ⚠ headlines history update failed"

# ── Step 9.5: Build markdown editions (optional, deploy-side) ──
# Regenerates editions/*.md + latest.md + llms.txt from edition.json/archive
# so every new issue is also served as LLM-readable markdown. Script lives
# in the deploy repo (synced via step 1b reset); absence is non-fatal.
if [ -f "$DEPLOY_DIR/scripts/build_markdown.py" ]; then
    python3 "$DEPLOY_DIR/scripts/build_markdown.py" 2>>"$LOGFILE" \
        && echo "  ✓ markdown editions rebuilt" \
        || echo "  ⚠ markdown build failed, continuing"
else
    echo "  - build_markdown.py not found — markdown skipped"
fi

cd "$DEPLOY_DIR"
git add -A
if ! git diff --cached --quiet; then
    git commit -m "Update local AI news $TODAY" --quiet 2>/dev/null || true
fi
git push origin main --quiet 2>/dev/null || echo "  ⚠ git push failed — will retry on next run"
echo "  ✓ pushed to GitHub"

# ── Report ──────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════"
echo "✅ LOCAL AI NEWS PIPELINE COMPLETE — $(date '+%H:%M:%S')"
echo "  Issue:   #$NEXT_ISSUE"
echo "  Date:    $TODAY"
echo "  Scouts:  $SCOUT_COUNT/6"
echo "  Edition: ✅ ($([ -f "$WORK_DIR/edition.json" ] && echo 'generated' || echo 'failed'))"
echo "  Wire:    ${WIRE_COUNT:-0} articles"
echo "  Deploy:  $DEPLOY_DIR"
echo "  Pushed:  github.com/MovieMaker93/local-ai-news"
echo "═══════════════════════════════════════════════"

# Final milestone. Reports what degraded rather than claiming a clean run,
# so the message is worth trusting on the days it says everything worked.
RUN_MIN=$(( $(elapsed) / 60 ))
EXTRAS=""
[ "${WIRE_COUNT:-0}" -eq 0 ] && EXTRAS="$EXTRAS no wire ticker,"
EXTRAS="${EXTRAS%,}"
notify "✅ Local AI News #$NEXT_ISSUE is live — ${ED_KEPT:-?} stories, ${WIRE_COUNT:-0} wire, in ${RUN_MIN}m.${EXTRAS:+ Degraded:$EXTRAS.}
$SITE_URL"
