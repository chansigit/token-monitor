#!/usr/bin/env bash
# Auto-update token usage and push to GitHub every run.

set -euo pipefail

export PATH="/scratch/users/chensj16/venvs/dl2025/.venv/bin:/scratch/users/chensj16/.npm-global/bin:/share/software/user/open/git/2.45.1/bin:/share/software/user/open/nodejs/25.3.0/bin:$PATH"

cd "$(dirname "$0")"

LOG_FILE="auto-update.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

log "Starting auto-update..."

# Fetch and generate
if python3 monitor.py >> "$LOG_FILE" 2>&1; then
    log "monitor.py completed successfully"
else
    log "ERROR: monitor.py failed"
    exit 1
fi

# Check if there are changes to commit
if git diff --quiet data/ assets/ README.md 2>/dev/null; then
    log "No changes detected, skipping commit"
    exit 0
fi

git add data/ assets/ README.md
git commit -m "update usage $(date +%Y-%m-%d\ %H:%M)"
git push

log "Pushed to GitHub successfully"
