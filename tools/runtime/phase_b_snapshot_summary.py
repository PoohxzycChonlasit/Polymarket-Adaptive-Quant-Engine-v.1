#!/usr/bin/env python3
"""
tools/phase_b_snapshot_summary.py
Helper tool producing a rolling 7-day snapshot summary of Phase B telemetry.
"""

import os
import sys
import json
from pathlib import Path

# Worst-case rank mapping
STATUS_RANKS = {
    "NOT_READY": 0,
    "WATCHLIST": 1,
    "CANDIDATE": 2,
    "PROMOTION_REVIEW": 3
}

def determine_worst_case_status(statuses: list[str]) -> str:
    if not statuses:
        return "NOT_READY"
    min_rank = min(STATUS_RANKS.get(s, 0) for s in statuses)
    rank_to_status = {v: k for k, v in STATUS_RANKS.items()}
    return rank_to_status.get(min_rank, "NOT_READY")

def generate_7day_summary() -> None:
    index_path = Path("runtime/quant_data/reports/phase_b_daily_snapshots/phase_b_snapshot_index.json").resolve()
    output_md_path = Path("scratch/phase_b_7day_snapshot_summary.md").resolve()

    if not index_path.exists():
        print(f"Error: Index file not found at {index_path}. Run archiver first.", file=sys.stderr)
        sys.exit(1)

    with open(index_path, "r", encoding="utf-8") as f:
        try:
            index_data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error: Malformed index file: {e}", file=sys.stderr)
            sys.exit(1)

    if not index_data:
        print("Error: Index is empty.", file=sys.stderr)
        sys.exit(1)

    # Sort dates and slice last 7
    sorted_dates = sorted(index_data.keys())
    last_7_dates = sorted_dates[-7:]
    
    summary_entries = [index_data[d] for d in last_7_dates]

    # Calculate aggregate metrics
    overall_statuses = [e["overall_status"] for e in summary_entries]
    worst_overall_status = determine_worst_case_status(overall_statuses)

    total_joined_trades = sum(e.get("joined_trades", 0) for e in summary_entries)
    avg_join_coverage = sum(e.get("join_coverage_pct", 100.0) for e in summary_entries) / len(summary_entries)
    total_exceptions = sum(e.get("exception_count", 0) for e in summary_entries)

    # Render stdout text display
    print(f"==================================================")
    print(f"       PHASE B 7-DAY SNAPSHOT ROLLING SUMMARY     ")
    print(f"==================================================")
    print(f"Start Date:         {last_7_dates[0]}")
    print(f"End Date:           {last_7_dates[-1]}")
    print(f"Days Summarized:    {len(summary_entries)}")
    print(f"Overall Status:     {worst_overall_status}")
    print(f"Total Joined:       {total_joined_trades} trades")
    print(f"Avg Join Coverage:  {avg_join_coverage:.2f}%")
    print(f"Total Exceptions:   {total_exceptions}")
    print(f"--------------------------------------------------")
    print(f"{'Date':<12} | {'Status':<16} | {'Joined':<6} | {'Coverage':<8} | {'Exc':<4}")
    print(f"--------------------------------------------------")
    for e in summary_entries:
        age_sec = e.get("heartbeat_age_seconds")
        age_str = f"{age_sec:.1f}s" if age_sec is not None else "unknown"
        print(f"{e['date']:<12} | {e['overall_status']:<16} | {e['joined_trades']:<6} | {e['join_coverage_pct']:>7.1f}% | {e['exception_count']:<4}")
    print(f"==================================================")

    # Write Markdown file
    md_content = f"""# Phase B 7-Day Rolling Snapshot Summary Report
**Summary Range**: {last_7_dates[0]} to {last_7_dates[-1]} ({len(summary_entries)} calendar days)  
**Worst-Case Governance Status**: **{worst_overall_status}**  

---

## 1. 7-Day Rolling Performance & Health Metrics
* **Total Joined Trades**: {total_joined_trades} trades
* **Average Join Coverage**: {avg_join_coverage:.2f}%
* **Aggregate Exception Count**: {total_exceptions} exceptions

---

## 2. Daily Snapshot Timeline

| Date | Overall Status | Joined Trades | Join Coverage | System Exceptions | Heartbeat Age |
| :--- | :---: | :---: | :---: | :---: | :---: |
"""
    for e in summary_entries:
        age_sec = e.get("heartbeat_age_seconds")
        age_str = f"{age_sec:.1f}s" if age_sec is not None else "unknown"
        md_content += f"| {e['date']} | **{e['overall_status']}** | {e['joined_trades']} | {e['join_coverage_pct']:.1f}% | {e['exception_count']} | {age_str} |\n"

    md_content += """
---

## 3. Governance Alert Panel
* **Actionable State**: The worst-case governance rule requires a status of **NOT_READY** unless all days in the rolling period meet WATCHLIST or CANDIDATE criteria.
"""

    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"7-Day Summary markdown report successfully written to: {output_md_path}")

def main() -> None:
    generate_7day_summary()

if __name__ == "__main__":
    main()
