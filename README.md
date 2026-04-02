<p align="center">
  <img src="assets/logo.svg" width="120" alt="Token Monitor">
</p>

<h1 align="center">Token Monitor</h1>

<p align="center">Track Claude Code daily token usage with GitHub-style contribution matrix.</p>

## Last 14 Days

![Last 14 Days](assets/recent.svg)

## Daily Cost

![Daily Cost](assets/cost.svg)

## Daily Tokens

![Daily Tokens](assets/tokens.svg)

## Past 6 Months

| Month | Cost | Tokens | Active Days |
|-------|------|--------|-------------|
| 2025-11 | $0.00 | 0 | 0 |
| 2025-12 | $0.00 | 0 | 0 |
| 2026-01 | $82.64 | 133.3M | 10 |
| 2026-02 | $53.41 | 71.7M | 13 |
| 2026-03 | $4,113 | 6.14B | 28 |
| 2026-04 | $106.74 | 166.2M | 2 |
| **Total** | **$4,356** | **6.51B** | **53** |

## Multi-Machine Setup

Each machine writes its own data file (`data/usage-<name>.json`), then aggregates all machines' data to generate charts.

Machine name is determined by: `MONITOR_NAME` env var > short hostname.

### 1. Clone & Install

```bash
git clone <this-repo-url>
cd token-monitor
npm install -g ccusage
```

### 2. (Optional) Set machine name

```bash
export MONITOR_NAME=my-laptop  # defaults to hostname if not set
```

### 3a. One-shot run

```bash
git pull --rebase
python monitor.py
git add data/ assets/ README.md
git commit -m "update usage $(date +%Y-%m-%d)"
git push
```

### 3b. Auto-update (every 10 min)

```bash
# Start background loop
nohup ./auto-loop.sh &

# Check logs
tail -f auto-update.log

# Stop
kill $(cat .loop.pid)
```

The auto-loop handles `git pull --rebase` and push with retry automatically.

## Data

Per-machine usage files: `data/usage-*.json`

## Changelog

- **v2.0** (2026-03-30) — Multi-machine support: per-machine data files, aggregation across machines, auto pull/push with retry
- **v1.0** (2026-03-28) — Initial release: single-machine usage tracking with GitHub-style contribution matrix
