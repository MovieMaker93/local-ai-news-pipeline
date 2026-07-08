#!/bin/bash
# ─────────────────────────────────────────────────────────────
# test_wire_pipeline.sh — Standalone test of wire-articles pipeline
# Runs: wire_articles.py (fetch + LLM) → render_wire_test.py
# Output: /tmp/v2/test-wire/index.html
# DOES NOT touch the production deploy directory or run_v2.sh
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT_DIR="/tmp/v2/test-wire"
LOG_DIR="/tmp/v2/logs"
mkdir -p "$OUT_DIR" "$LOG_DIR"
TODAY=$(date +%Y-%m-%d)
LOGFILE="$LOG_DIR/wire_test_${TODAY}.log"

echo "═══════════════════════════════════════════════"
echo "WIRE ARTICLES TEST — $(date '+%Y-%m-%d %H:%M:%S')"
echo "═══════════════════════════════════════════════"
echo ""

# Clean old wire output
rm -f "${OUT_DIR}/index.html" 2>/dev/null || true

# Step 1: Fetch + LLM write
echo "[1/2] wire_articles.py (fetch RSS → AI writing)..."
python3 "${SCRIPT_DIR}/wire_articles.py" --max 5 --out "${OUT_DIR}/wire_articles.json" 2>"${LOG_DIR}/wire_stage1_${TODAY}.log"
echo "  ✓ done"

# Step 2: Render test page
echo "[2/2] render_wire_test.py..."
python3 "${SCRIPT_DIR}/render_wire_test.py" "${OUT_DIR}/wire_articles.json" 2>&1
echo "  ✓ done"

echo ""
echo "═══════════════════════════════════════════════"
echo "TEST PAGE: file://${OUT_DIR}/index.html"
echo "═══════════════════════════════════════════════"