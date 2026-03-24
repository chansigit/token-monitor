#!/usr/bin/env python3
"""Token Monitor - Track Claude Code daily usage with GitHub-style contribution matrix."""

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "data" / "usage.json"
ASSETS_DIR = BASE_DIR / "assets"
README_FILE = BASE_DIR / "README.md"

# GitHub-style green colors (5 levels)
COLORS_GREEN = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]
COLOR_EMPTY = "#ebedf0"

CELL_SIZE = 13
CELL_GAP = 3
CELL_STEP = CELL_SIZE + CELL_GAP
MARGIN_LEFT = 40
MARGIN_TOP = 30
MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAY_LABELS = ["Mon", "", "Wed", "", "Fri", "", "Sun"]


def fetch_usage() -> list[dict]:
    """Fetch all daily usage data from ccusage."""
    result = subprocess.run(
        ["ccusage", "daily", "--json"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Error running ccusage: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    data = json.loads(result.stdout)
    return data.get("daily", data) if isinstance(data, dict) else data


def load_existing() -> dict:
    """Load existing usage data keyed by date."""
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return {}


def save_data(data: dict):
    """Save usage data to JSON file."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def merge_data(existing: dict, new_entries: list[dict]) -> dict:
    """Merge new entries into existing data, keyed by date."""
    for entry in new_entries:
        date = entry["date"]
        existing[date] = entry
    return existing


def get_last_365_days() -> list[str]:
    """Return list of date strings for the last 365 days."""
    today = datetime.now().date()
    return [(today - timedelta(days=i)).isoformat() for i in range(364, -1, -1)]


def quantize(values: list[float], levels: int = 5) -> list[int]:
    """Assign each value to a level (0 = no data, 1-4 = quartiles)."""
    nonzero = [v for v in values if v > 0]
    if not nonzero:
        return [0] * len(values)
    sorted_nz = sorted(nonzero)
    thresholds = [
        sorted_nz[int(len(sorted_nz) * p)] if int(len(sorted_nz) * p) < len(sorted_nz) else sorted_nz[-1]
        for p in [0.25, 0.5, 0.75]
    ]
    result = []
    for v in values:
        if v <= 0:
            result.append(0)
        elif v <= thresholds[0]:
            result.append(1)
        elif v <= thresholds[1]:
            result.append(2)
        elif v <= thresholds[2]:
            result.append(3)
        else:
            result.append(4)
    return result


def format_value(value: float, is_cost: bool) -> str:
    """Format a value for tooltip display."""
    if is_cost:
        return f"${value:.2f}"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(int(value))


def generate_svg(dates: list[str], data: dict, field: str, title: str, is_cost: bool) -> str:
    """Generate a GitHub-style contribution matrix SVG."""
    values = [data.get(d, {}).get(field, 0) for d in dates]
    levels = quantize(values)

    # Calculate grid: 7 rows (Mon-Sun), ~53 columns
    # First date's weekday determines starting row
    first_date = datetime.fromisoformat(dates[0]).date()
    start_weekday = first_date.weekday()  # 0=Mon, 6=Sun

    # Build week columns
    weeks = []
    current_week = [None] * start_weekday
    for i, date_str in enumerate(dates):
        current_week.append((date_str, values[i], levels[i]))
        if len(current_week) == 7:
            weeks.append(current_week)
            current_week = []
    if current_week:
        weeks.append(current_week + [None] * (7 - len(current_week)))

    num_weeks = len(weeks)
    width = MARGIN_LEFT + num_weeks * CELL_STEP + 10
    height = MARGIN_TOP + 7 * CELL_STEP + 25

    svg = ET.Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "width": str(width),
        "height": str(height),
        "viewBox": f"0 0 {width} {height}",
    })

    # Background
    ET.SubElement(svg, "rect", {
        "width": str(width), "height": str(height),
        "fill": "#ffffff", "rx": "6",
    })

    # Title
    title_el = ET.SubElement(svg, "text", {
        "x": str(MARGIN_LEFT), "y": "16",
        "font-family": "Arial, sans-serif", "font-size": "14",
        "fill": "#24292f", "font-weight": "bold",
    })
    title_el.text = title

    # Day labels
    for i, label in enumerate(DAY_LABELS):
        if label:
            t = ET.SubElement(svg, "text", {
                "x": str(MARGIN_LEFT - 8),
                "y": str(MARGIN_TOP + i * CELL_STEP + CELL_SIZE - 2),
                "font-family": "Arial, sans-serif", "font-size": "10",
                "fill": "#57606a", "text-anchor": "end",
            })
            t.text = label

    # Month labels
    month_positions = {}
    for wi, week in enumerate(weeks):
        for cell in week:
            if cell:
                d = datetime.fromisoformat(cell[0]).date()
                if d.day <= 7:
                    month_positions.setdefault(d.month, wi)

    for month, wi in month_positions.items():
        t = ET.SubElement(svg, "text", {
            "x": str(MARGIN_LEFT + wi * CELL_STEP),
            "y": str(MARGIN_TOP - 6),
            "font-family": "Arial, sans-serif", "font-size": "10",
            "fill": "#57606a",
        })
        t.text = MONTH_LABELS[month - 1]

    # Cells
    for wi, week in enumerate(weeks):
        for di, cell in enumerate(week):
            x = MARGIN_LEFT + wi * CELL_STEP
            y = MARGIN_TOP + di * CELL_STEP
            if cell is None:
                color = COLOR_EMPTY
                tooltip = "No data"
            else:
                date_str, val, level = cell
                color = COLORS_GREEN[level]
                formatted = format_value(val, is_cost)
                tooltip = f"{date_str}: {formatted}"

            rect = ET.SubElement(svg, "rect", {
                "x": str(x), "y": str(y),
                "width": str(CELL_SIZE), "height": str(CELL_SIZE),
                "rx": "2", "ry": "2", "fill": color,
            })
            title_tip = ET.SubElement(rect, "title")
            title_tip.text = tooltip

    # Legend
    legend_y = MARGIN_TOP + 7 * CELL_STEP + 8
    legend_x = width - 130
    t = ET.SubElement(svg, "text", {
        "x": str(legend_x), "y": str(legend_y + 9),
        "font-family": "Arial, sans-serif", "font-size": "10",
        "fill": "#57606a",
    })
    t.text = "Less"
    for i, c in enumerate(COLORS_GREEN):
        ET.SubElement(svg, "rect", {
            "x": str(legend_x + 30 + i * (CELL_SIZE + 2)),
            "y": str(legend_y),
            "width": str(CELL_SIZE), "height": str(CELL_SIZE),
            "rx": "2", "fill": c,
        })
    t2 = ET.SubElement(svg, "text", {
        "x": str(legend_x + 30 + 5 * (CELL_SIZE + 2) + 4),
        "y": str(legend_y + 9),
        "font-family": "Arial, sans-serif", "font-size": "10",
        "fill": "#57606a",
    })
    t2.text = "More"

    ET.indent(svg)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(svg, encoding="unicode")


def update_readme():
    """Update README.md with current SVG images."""
    content = f"""# Token Monitor

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

## Daily Cost

![Daily Cost](assets/cost.svg)

## Daily Tokens

![Daily Tokens](assets/tokens.svg)

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
"""
    README_FILE.write_text(content)


def main():
    print("Fetching usage data from ccusage...")
    new_entries = fetch_usage()

    existing = load_existing()
    merged = merge_data(existing, new_entries)
    save_data(merged)
    print(f"Saved {len(merged)} days of usage data.")

    dates = get_last_365_days()

    print("Generating cost matrix...")
    cost_svg = generate_svg(dates, merged, "totalCost", "Daily Cost", is_cost=True)
    (ASSETS_DIR / "cost.svg").write_text(cost_svg)

    print("Generating tokens matrix...")
    tokens_svg = generate_svg(dates, merged, "totalTokens", "Daily Tokens", is_cost=False)
    (ASSETS_DIR / "tokens.svg").write_text(tokens_svg)

    update_readme()
    print("Done! README.md and SVGs updated.")


if __name__ == "__main__":
    main()
