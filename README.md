# Token Monitor

Track Claude Code daily token usage with GitHub-style contribution matrix.

## Usage

```bash
# Update usage data and visualizations
python monitor.py

# Or run directly
./monitor.py
```

The script will:
1. Fetch latest usage data from `ccusage`
2. Save to `data/usage.json`
3. Generate contribution matrix SVGs
4. Update this README

## Last 14 Days

![Last 14 Days](assets/recent.svg)

## Daily Cost

![Daily Cost](assets/cost.svg)

## Daily Tokens

![Daily Tokens](assets/tokens.svg)

## Past 6 Months

| Month | Cost | Tokens | Active Days |
|-------|------|--------|-------------|
| 2025-10 | $0.00 | 0 | 0 |
| 2025-11 | $0.00 | 0 | 0 |
| 2025-12 | $0.00 | 0 | 0 |
| 2026-01 | $27.55 | 44.4M | 10 |
| 2026-02 | $98.71 | 125.3M | 13 |
| 2026-03 | $1,073 | 1.47B | 22 |
| **Total** | **$1,199** | **1.64B** | **45** |

## Data

Raw usage data is stored in [`data/usage.json`](data/usage.json).

## Setup

Requires [ccusage](https://github.com/anthropics/ccusage) to be installed and configured.

```bash
# Install ccusage if not already installed
npm install -g ccusage

# Run the monitor
python monitor.py
```

Commit and push to GitHub to update your contribution wall:

```bash
git add -A && git commit -m "update usage $(date +%Y-%m-%d)" && git push
```
