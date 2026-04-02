# Multi-Machine Token Usage Aggregation

## Problem

`ccusage` only reads local `~/.claude/` logs. A single user with multiple machines (e.g., lab server + laptop) has no way to see total usage across all machines. This project currently runs on one machine only.

## Solution

Use the GitHub repo as a centralized database. Each machine uploads its own usage data file, then aggregates all machines' data to generate unified charts.

## Architecture

```
Machine A (sherlock)                    Machine B (laptop)
  ccusage → data/usage-sherlock.json      ccusage → data/usage-laptop.json
  git pull --rebase                       git pull --rebase
  merge all data/usage-*.json             merge all data/usage-*.json
  generate SVG + README                   generate SVG + README
  git push (retry 3x)                     git push (retry 3x)
```

## Machine Identity

Priority:
1. Environment variable `MONITOR_NAME` (if set)
2. `socket.gethostname()` fallback

Data file: `data/usage-{name}.json`

## Data File Format

Each machine's file uses the same format as current `usage.json` — a dict keyed by date string. No changes to the per-entry schema.

## Aggregation Logic

`aggregate()` reads all `data/usage-*.json` files and merges by date:

- **Sum** these fields: `inputTokens`, `outputTokens`, `cacheCreationTokens`, `cacheReadTokens`, `totalTokens`, `totalCost`
- **Union** of `modelsUsed`
- **`modelBreakdowns`**: group by `modelName`, sum token/cost fields within each group

The aggregated data is used for chart generation and README. It is NOT written to a file — it's computed on the fly.

## Changes to `monitor.py`

1. Add `get_machine_name()` — reads `MONITOR_NAME` env var, falls back to hostname
2. Change `DATA_FILE` to `data/usage-{machine_name}.json`
3. Add `aggregate_all()` — glob `data/usage-*.json`, load each, merge by date with summation
4. `main()` flow:
   - Fetch local usage via ccusage → save to machine-specific file
   - Aggregate all machine files
   - Generate charts and README from aggregated data

## Changes to `auto-update.sh`

1. `git pull --rebase` before running `monitor.py`
2. `git add data/ assets/ README.md`
3. Push with retry loop (max 3 attempts):
   - On push failure: `git pull --rebase`, then retry push

## Deleted Files

- `data/usage.json` — replaced by per-machine files. Existing data migrated to `data/usage-{current_hostname}.json` on first run.

## Migration

On first run, if `data/usage.json` exists and the machine-specific file does not, rename it to `data/usage-{name}.json`.

## Unchanged

- SVG generation logic
- README template (still shows total usage)
- `auto-loop.sh`
- All chart types (heatmap, line chart, monthly table)
