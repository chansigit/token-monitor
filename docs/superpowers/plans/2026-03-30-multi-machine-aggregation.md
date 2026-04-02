# Multi-Machine Token Usage Aggregation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform token-monitor from single-machine to multi-machine usage aggregation, using GitHub repo as centralized data store.

**Architecture:** Each machine writes its own `data/usage-{name}.json` file. On each run, the script aggregates all machine files, generates charts from totals, and pushes. Machines are identified by env var `MONITOR_NAME` or hostname fallback.

**Tech Stack:** Python 3, ccusage CLI, git, bash

---

### Task 1: Add machine identity and per-machine data file

**Files:**
- Modify: `monitor.py:1-15` (imports and constants)
- Modify: `monitor.py:30-48` (fetch_usage)
- Modify: `monitor.py:51-61` (load/save)

- [ ] **Step 1: Add `get_machine_name()` and update imports/constants**

In `monitor.py`, add `import socket` to imports, then replace the `DATA_FILE` constant and add the machine name function:

```python
import socket

# Replace this line:
# DATA_FILE = BASE_DIR / "data" / "usage.json"
# With:
DATA_DIR = BASE_DIR / "data"

def get_machine_name() -> str:
    """Get machine identifier from env var or hostname."""
    import os
    name = os.environ.get("MONITOR_NAME", "").strip()
    if not name:
        name = socket.gethostname().split(".")[0]  # short hostname
    return name
```

- [ ] **Step 2: Update `load_existing()` and `save_data()` to use machine-specific file**

```python
def get_machine_data_file() -> Path:
    return DATA_DIR / f"usage-{get_machine_name()}.json"

def load_existing() -> dict:
    """Load existing usage data for this machine."""
    f = get_machine_data_file()
    if f.exists():
        return json.loads(f.read_text())
    return {}

def save_data(data: dict):
    """Save this machine's usage data."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    get_machine_data_file().write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
```

- [ ] **Step 3: Run script to verify it creates machine-specific file**

Run: `cd /scratch/users/chensj16/projects/token-monitor && python3 -c "from monitor import get_machine_name, get_machine_data_file; print(get_machine_name()); print(get_machine_data_file())"`

Expected: prints short hostname (e.g., `sh04-01n12`) and path `data/usage-sh04-01n12.json`

- [ ] **Step 4: Commit**

```bash
git add monitor.py
git commit -m "feat: add machine identity and per-machine data file"
```

---

### Task 2: Add migration from old `usage.json`

**Files:**
- Modify: `monitor.py` (add migrate function, call from main)

- [ ] **Step 1: Add migration function**

Add after `save_data()`:

```python
def migrate_legacy_data():
    """Migrate old usage.json to machine-specific file on first run."""
    legacy = DATA_DIR / "usage.json"
    target = get_machine_data_file()
    if legacy.exists() and not target.exists():
        legacy.rename(target)
        print(f"Migrated data/usage.json -> {target.name}")
```

- [ ] **Step 2: Call migration at the start of `main()`**

Add as the first line inside `main()`:

```python
def main():
    migrate_legacy_data()
    # ... rest of main
```

- [ ] **Step 3: Test migration manually**

Run: `python3 -c "from monitor import migrate_legacy_data, DATA_DIR, get_machine_name; print(f'Would migrate to: usage-{get_machine_name()}.json'); print(f'Legacy exists: {(DATA_DIR / \"usage.json\").exists()}')"`

- [ ] **Step 4: Commit**

```bash
git add monitor.py
git commit -m "feat: migrate legacy usage.json to per-machine file"
```

---

### Task 3: Add aggregation logic

**Files:**
- Modify: `monitor.py` (add `aggregate_all()`)

- [ ] **Step 1: Add `aggregate_all()` function**

Add after `migrate_legacy_data()`:

```python
def aggregate_all() -> dict:
    """Load all machine data files and aggregate by date (sum tokens/cost)."""
    aggregated = {}
    for f in sorted(DATA_DIR.glob("usage-*.json")):
        machine_data = json.loads(f.read_text())
        for date_str, entry in machine_data.items():
            if date_str not in aggregated:
                aggregated[date_str] = {
                    "date": date_str,
                    "inputTokens": 0,
                    "outputTokens": 0,
                    "cacheCreationTokens": 0,
                    "cacheReadTokens": 0,
                    "totalTokens": 0,
                    "totalCost": 0.0,
                    "modelsUsed": [],
                    "modelBreakdowns": [],
                }
            agg = aggregated[date_str]
            for field in ("inputTokens", "outputTokens", "cacheCreationTokens",
                          "cacheReadTokens", "totalTokens"):
                agg[field] += entry.get(field, 0)
            agg["totalCost"] += entry.get("totalCost", 0.0)
            # Union of models used
            for model in entry.get("modelsUsed", []):
                if model not in agg["modelsUsed"]:
                    agg["modelsUsed"].append(model)
            # Merge model breakdowns by modelName
            for bd in entry.get("modelBreakdowns", []):
                existing = next((b for b in agg["modelBreakdowns"]
                                 if b["modelName"] == bd["modelName"]), None)
                if existing:
                    for field in ("inputTokens", "outputTokens",
                                  "cacheCreationTokens", "cacheReadTokens", "cost"):
                        existing[field] = existing.get(field, 0) + bd.get(field, 0)
                else:
                    agg["modelBreakdowns"].append(dict(bd))
    return aggregated
```

- [ ] **Step 2: Verify aggregation works with current data**

Run: `cd /scratch/users/chensj16/projects/token-monitor && python3 -c "from monitor import aggregate_all; d = aggregate_all(); print(f'Dates: {len(d)}'); print(list(d.keys())[:3])"`

Expected: prints the number of dates and first 3 date keys.

- [ ] **Step 3: Commit**

```bash
git add monitor.py
git commit -m "feat: add multi-machine data aggregation"
```

---

### Task 4: Update `main()` to use aggregation

**Files:**
- Modify: `monitor.py:538-568` (main function)

- [ ] **Step 1: Rewrite `main()` to use aggregation**

Replace the current `main()` with:

```python
def main():
    migrate_legacy_data()

    print("Fetching usage data from ccusage...")
    new_entries = fetch_usage()

    existing = load_existing()
    merged = merge_data(existing, new_entries)
    save_data(merged)
    print(f"Saved {len(merged)} days to {get_machine_data_file().name}")

    print("Aggregating all machines...")
    aggregated = aggregate_all()
    print(f"Aggregated {len(aggregated)} days from {len(list(DATA_DIR.glob('usage-*.json')))} machine(s)")

    today = datetime.now().date()
    dates = get_last_365_days(today)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    print("Generating 14-day line chart...")
    recent_svg = generate_line_chart(aggregated, "Last 14 Days — Cost & Tokens", today)
    (ASSETS_DIR / "recent.svg").write_text(recent_svg)

    print("Generating cost matrix...")
    cost_svg = generate_svg(dates, aggregated, "totalCost", "Daily Cost", is_cost=True)
    (ASSETS_DIR / "cost.svg").write_text(cost_svg)

    print("Generating tokens matrix...")
    tokens_svg = generate_svg(dates, aggregated, "totalTokens", "Daily Tokens", is_cost=False)
    (ASSETS_DIR / "tokens.svg").write_text(tokens_svg)

    update_readme(aggregated, today)
    print("Done! README.md and SVGs updated.")
```

- [ ] **Step 2: Run full script**

Run: `cd /scratch/users/chensj16/projects/token-monitor && python3 monitor.py`

Expected: completes successfully, prints "Aggregated N days from 1 machine(s)"

- [ ] **Step 3: Commit**

```bash
git add monitor.py
git commit -m "feat: use aggregated data for chart generation"
```

---

### Task 5: Update `auto-update.sh` with pull-before-push and retry

**Files:**
- Modify: `auto-update.sh`

- [ ] **Step 1: Rewrite `auto-update.sh`**

Replace the full content with:

```bash
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
```

- [ ] **Step 2: Verify syntax**

Run: `bash -n /scratch/users/chensj16/projects/token-monitor/auto-update.sh && echo "OK"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add auto-update.sh
git commit -m "feat: add pull-before-push and retry logic for multi-machine sync"
```

---

### Task 6: Clean up and verify end-to-end

**Files:**
- Modify: `README.md` (auto-generated by script)

- [ ] **Step 1: Run full pipeline end-to-end**

Run: `cd /scratch/users/chensj16/projects/token-monitor && python3 monitor.py`

Verify output shows:
- Migration message (first run only)
- "Saved N days to usage-{hostname}.json"
- "Aggregated N days from 1 machine(s)"
- "Done! README.md and SVGs updated."

- [ ] **Step 2: Verify data file was created correctly**

Run: `ls data/usage-*.json`

Expected: `data/usage-sh04-01n12.json` (or similar hostname), and `data/usage.json` should no longer exist.

- [ ] **Step 3: Test with MONITOR_NAME env var**

Run: `MONITOR_NAME=test-machine python3 -c "from monitor import get_machine_name; print(get_machine_name())"`

Expected: `test-machine`

- [ ] **Step 4: Final commit**

```bash
git add data/ assets/ README.md
git commit -m "feat: complete multi-machine aggregation support"
```
