#!/bin/bash
# Cron wrapper — launches V2 pipeline in background.
# The cron system has a 3-minute hard timeout,
# so we fire-and-forget the real script.
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
mkdir -p /tmp/v2/logs
nohup bash "$SCRIPT_DIR/run_v2.sh" >> /tmp/v2/logs/cron_wrapper.log 2>&1 &
echo "V2 pipeline launched (PID $!) at $(date)"
