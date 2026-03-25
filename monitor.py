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


def quantize(values: list[float]) -> tuple[list[int], list[float]]:
    """Assign each value to a level (0 = no data, 1-4 = quartiles).
    Returns (levels, thresholds) where thresholds = [q25, q50, q75, max]."""
    nonzero = [v for v in values if v > 0]
    if not nonzero:
        return [0] * len(values), [0, 0, 0, 0]
    sorted_nz = sorted(nonzero)
    n = len(sorted_nz)
    thresholds = [
        sorted_nz[min(int(n * p), n - 1)]
        for p in [0.25, 0.5, 0.75]
    ] + [sorted_nz[-1]]
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
    return result, thresholds


def format_cost(value: float) -> str:
    if value >= 1000:
        return f"${value:,.0f}"
    return f"${value:.2f}"


def format_tokens(value: float) -> str:
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(int(value))


def generate_svg(dates: list[str], data: dict, field: str, title: str, is_cost: bool) -> str:
    """Generate a GitHub-style contribution matrix SVG with interactive hover tooltip."""
    values = [data.get(d, {}).get(field, 0) for d in dates]
    levels, thresholds = quantize(values)

    # Calculate grid
    first_date = datetime.fromisoformat(dates[0]).date()
    start_weekday = first_date.weekday()

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
    legend_height = 60
    height = MARGIN_TOP + 7 * CELL_STEP + legend_height

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
                    month_positions.setdefault((d.year, d.month), wi)

    for (year, month), wi in month_positions.items():
        t = ET.SubElement(svg, "text", {
            "x": str(MARGIN_LEFT + wi * CELL_STEP),
            "y": str(MARGIN_TOP - 6),
            "font-family": "Arial, sans-serif", "font-size": "10",
            "fill": "#57606a",
        })
        t.text = MONTH_LABELS[month - 1]

    # Cells with hover tooltips
    fmt = format_cost if is_cost else format_tokens
    unit = "" if is_cost else " tokens"

    for wi, week in enumerate(weeks):
        for di, cell in enumerate(week):
            x = MARGIN_LEFT + wi * CELL_STEP
            y = MARGIN_TOP + di * CELL_STEP

            if cell is None:
                ET.SubElement(svg, "rect", {
                    "x": str(x), "y": str(y),
                    "width": str(CELL_SIZE), "height": str(CELL_SIZE),
                    "rx": "2", "ry": "2", "fill": COLOR_EMPTY,
                })
                continue

            date_str, val, level = cell
            color = COLORS_GREEN[level]
            formatted = fmt(val)

            # Cell rect with native tooltip (works on GitHub)
            cell_rect = ET.SubElement(svg, "rect", {
                "x": str(x), "y": str(y),
                "width": str(CELL_SIZE), "height": str(CELL_SIZE),
                "rx": "2", "ry": "2", "fill": color,
            })
            tip = ET.SubElement(cell_rect, "title")
            tip.text = f"{formatted}{unit} on {date_str}"

    # Colorbar legend with value ranges
    bar_w = 50  # width per color segment
    bar_h = 12
    total_bar_w = bar_w * 5
    bar_x = MARGIN_LEFT
    bar_y = MARGIN_TOP + 7 * CELL_STEP + 10

    # Draw color segments
    for i, c in enumerate(COLORS_GREEN):
        ET.SubElement(svg, "rect", {
            "x": str(bar_x + i * bar_w), "y": str(bar_y),
            "width": str(bar_w), "height": str(bar_h),
            "fill": c,
        })

    # Border around the whole bar
    ET.SubElement(svg, "rect", {
        "x": str(bar_x), "y": str(bar_y),
        "width": str(total_bar_w), "height": str(bar_h),
        "fill": "none", "stroke": "#d0d7de", "stroke-width": "0.5", "rx": "2",
    })

    # Tick labels below bar (centered under each segment)
    nonzero_vals = [v for v in values if v > 0]
    if nonzero_vals:
        bar_labels = ["0", fmt(thresholds[0]), fmt(thresholds[1]),
                       fmt(thresholds[2]), fmt(thresholds[3])]
    else:
        bar_labels = ["0", "0", "0", "0", "0"]

    for i, label in enumerate(bar_labels):
        tx = bar_x + i * bar_w + bar_w // 2
        t = ET.SubElement(svg, "text", {
            "x": str(tx), "y": str(bar_y + bar_h + 12),
            "font-family": "Arial, sans-serif", "font-size": "9",
            "fill": "#57606a", "text-anchor": "middle",
        })
        t.text = label

    # Colorbar title
    bar_title = ET.SubElement(svg, "text", {
        "x": str(bar_x), "y": str(bar_y - 4),
        "font-family": "Arial, sans-serif", "font-size": "9",
        "fill": "#57606a",
    })
    bar_title.text = "Cost per day" if is_cost else "Tokens per day"

    ET.indent(svg)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(svg, encoding="unicode")


def generate_line_chart(data: dict, title: str) -> str:
    """Generate a 14-day dual-axis line chart SVG (cost + tokens)."""
    today = datetime.now().date()
    dates = [(today - timedelta(days=i)).isoformat() for i in range(13, -1, -1)]
    costs = [data.get(d, {}).get("totalCost", 0) for d in dates]
    tokens = [data.get(d, {}).get("totalTokens", 0) for d in dates]

    # Chart dimensions
    chart_w, chart_h = 800, 200
    margin = {"top": 35, "right": 80, "bottom": 40, "left": 70}
    w = chart_w - margin["left"] - margin["right"]
    h = chart_h - margin["top"] - margin["bottom"]

    svg = ET.Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "width": str(chart_w), "height": str(chart_h),
        "viewBox": f"0 0 {chart_w} {chart_h}",
    })

    ET.SubElement(svg, "rect", {
        "width": str(chart_w), "height": str(chart_h),
        "fill": "#ffffff", "rx": "6",
    })

    # Title
    t = ET.SubElement(svg, "text", {
        "x": str(margin["left"]), "y": "20",
        "font-family": "Arial, sans-serif", "font-size": "14",
        "fill": "#24292f", "font-weight": "bold",
    })
    t.text = title

    # Scales
    max_cost = max(costs) or 1
    max_tokens = max(tokens) or 1

    def x_pos(i):
        return margin["left"] + i * w / 13

    def y_cost(v):
        return margin["top"] + h - (v / max_cost) * h

    def y_tokens(v):
        return margin["top"] + h - (v / max_tokens) * h

    # Grid lines
    for i in range(5):
        gy = margin["top"] + i * h / 4
        ET.SubElement(svg, "line", {
            "x1": str(margin["left"]), "y1": str(gy),
            "x2": str(margin["left"] + w), "y2": str(gy),
            "stroke": "#ebedf0", "stroke-width": "1",
        })

    # X-axis labels (dates)
    for i, d in enumerate(dates):
        if i % 2 == 0:  # every other day
            label = d[5:]  # MM-DD
            tx = ET.SubElement(svg, "text", {
                "x": str(x_pos(i)), "y": str(margin["top"] + h + 18),
                "font-family": "Arial, sans-serif", "font-size": "9",
                "fill": "#57606a", "text-anchor": "middle",
            })
            tx.text = label

    # Y-axis labels - cost (left)
    for i in range(5):
        val = max_cost * (4 - i) / 4
        yl = ET.SubElement(svg, "text", {
            "x": str(margin["left"] - 6),
            "y": str(margin["top"] + i * h / 4 + 4),
            "font-family": "Arial, sans-serif", "font-size": "9",
            "fill": "#30a14e", "text-anchor": "end",
        })
        yl.text = format_cost(val)

    # Y-axis labels - tokens (right)
    for i in range(5):
        val = max_tokens * (4 - i) / 4
        yr = ET.SubElement(svg, "text", {
            "x": str(margin["left"] + w + 6),
            "y": str(margin["top"] + i * h / 4 + 4),
            "font-family": "Arial, sans-serif", "font-size": "9",
            "fill": "#0969da",
        })
        yr.text = format_tokens(val)

    # Cost line (green)
    cost_points = " ".join(f"{x_pos(i)},{y_cost(v)}" for i, v in enumerate(costs))
    ET.SubElement(svg, "polyline", {
        "points": cost_points,
        "fill": "none", "stroke": "#30a14e", "stroke-width": "2",
    })

    # Cost dots
    for i, v in enumerate(costs):
        circle = ET.SubElement(svg, "circle", {
            "cx": str(x_pos(i)), "cy": str(y_cost(v)), "r": "3",
            "fill": "#30a14e",
        })
        tip = ET.SubElement(circle, "title")
        tip.text = f"{dates[i]}: {format_cost(v)}"

    # Tokens line (blue)
    token_points = " ".join(f"{x_pos(i)},{y_tokens(v)}" for i, v in enumerate(tokens))
    ET.SubElement(svg, "polyline", {
        "points": token_points,
        "fill": "none", "stroke": "#0969da", "stroke-width": "2",
        "stroke-dasharray": "6,3",
    })

    # Token dots
    for i, v in enumerate(tokens):
        circle = ET.SubElement(svg, "circle", {
            "cx": str(x_pos(i)), "cy": str(y_tokens(v)), "r": "3",
            "fill": "#0969da",
        })
        tip = ET.SubElement(circle, "title")
        tip.text = f"{dates[i]}: {format_tokens(v)}"

    # Legend
    lx = margin["left"] + w - 160
    ly = margin["top"] - 12
    ET.SubElement(svg, "line", {
        "x1": str(lx), "y1": str(ly), "x2": str(lx + 20), "y2": str(ly),
        "stroke": "#30a14e", "stroke-width": "2",
    })
    t1 = ET.SubElement(svg, "text", {
        "x": str(lx + 24), "y": str(ly + 4),
        "font-family": "Arial, sans-serif", "font-size": "10", "fill": "#30a14e",
    })
    t1.text = "Cost ($)"
    ET.SubElement(svg, "line", {
        "x1": str(lx + 80), "y1": str(ly), "x2": str(lx + 100), "y2": str(ly),
        "stroke": "#0969da", "stroke-width": "2", "stroke-dasharray": "6,3",
    })
    t2 = ET.SubElement(svg, "text", {
        "x": str(lx + 104), "y": str(ly + 4),
        "font-family": "Arial, sans-serif", "font-size": "10", "fill": "#0969da",
    })
    t2.text = "Tokens"

    ET.indent(svg)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(svg, encoding="unicode")


def generate_monthly_summary(data: dict) -> str:
    """Generate a markdown table of the past 6 months usage."""
    today = datetime.now().date()
    months = []
    for i in range(5, -1, -1):
        # Go back i months
        y = today.year
        m = today.month - i
        while m <= 0:
            m += 12
            y -= 1
        months.append((y, m))

    rows = []
    for y, m in months:
        month_label = f"{y}-{m:02d}"
        total_cost = 0.0
        total_tokens = 0
        days_active = 0
        for date_str, entry in data.items():
            d = datetime.fromisoformat(date_str).date()
            if d.year == y and d.month == m:
                total_cost += entry.get("totalCost", 0)
                total_tokens += entry.get("totalTokens", 0)
                if entry.get("totalCost", 0) > 0 or entry.get("totalTokens", 0) > 0:
                    days_active += 1
        rows.append((month_label, total_cost, total_tokens, days_active))

    lines = []
    lines.append("| Month | Cost | Tokens | Active Days |")
    lines.append("|-------|------|--------|-------------|")
    for month_label, cost, tokens, days in rows:
        lines.append(f"| {month_label} | {format_cost(cost)} | {format_tokens(tokens)} | {days} |")

    # Totals
    total_c = sum(r[1] for r in rows)
    total_t = sum(r[2] for r in rows)
    total_d = sum(r[3] for r in rows)
    lines.append(f"| **Total** | **{format_cost(total_c)}** | **{format_tokens(total_t)}** | **{total_d}** |")

    return "\n".join(lines)


def update_readme(data: dict):
    """Update README.md with current SVG images and monthly summary."""
    monthly_table = generate_monthly_summary(data)

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

## Last 14 Days

![Last 14 Days](assets/recent.svg)

## Daily Cost

![Daily Cost](assets/cost.svg)

## Daily Tokens

![Daily Tokens](assets/tokens.svg)

## Past 6 Months

{monthly_table}

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

    print("Generating 14-day line chart...")
    recent_svg = generate_line_chart(merged, "Last 14 Days — Cost & Tokens")
    (ASSETS_DIR / "recent.svg").write_text(recent_svg)

    print("Generating cost matrix...")
    cost_svg = generate_svg(dates, merged, "totalCost", "Daily Cost", is_cost=True)
    (ASSETS_DIR / "cost.svg").write_text(cost_svg)

    print("Generating tokens matrix...")
    tokens_svg = generate_svg(dates, merged, "totalTokens", "Daily Tokens", is_cost=False)
    (ASSETS_DIR / "tokens.svg").write_text(tokens_svg)

    update_readme(merged)
    print("Done! README.md and SVGs updated.")


if __name__ == "__main__":
    main()
