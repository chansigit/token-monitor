#!/usr/bin/env bash
# Auto-update token usage and push to GitHub every run.

set -euo pipefail

export PATH="/scratch/users/chensj16/venvs/dl2025/.venv/bin:/scratch/users/chensj16/.npm-global/bin:/share/software/user/open/git/2.45.1/bin:/share/software/user/open/nodejs/25.3.0/bin:$PATH"

cd "$(dirname "$0")"

LOG_FILE="auto-update.log"
MAX_RETRIES=3

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

log "Starting auto-update..."

# Pull latest data from other machines
if git pull --rebase >> "$LOG_FILE" 2>&1; then
    log "git pull --rebase succeeded"
else
    log "WARNING: git pull --rebase failed, continuing anyway"
fi

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

# Push with retry
for i in $(seq 1 $MAX_RETRIES); do
    if git push 2>> "$LOG_FILE"; then
        log "Pushed to GitHub successfully"
        exit 0
    fi
    log "Push failed (attempt $i/$MAX_RETRIES), pulling and retrying..."
    git pull --rebase >> "$LOG_FILE" 2>&1 || true
done

log "ERROR: Failed to push after $MAX_RETRIES attempts"
exit 1
