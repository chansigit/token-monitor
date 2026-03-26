#!/usr/bin/env bash
# Run auto-update.sh every 10 minutes in a loop.
# Usage:
#   nohup ./auto-loop.sh &          # start in background
#   kill $(cat .loop.pid)            # stop it

set -euo pipefail
cd "$(dirname "$0")"

echo $$ > .loop.pid
echo "Auto-loop started (PID $$), updating every 10 minutes. Stop with: kill \$(cat .loop.pid)"

while true; do
    ./auto-update.sh || true
    sleep 600
done
