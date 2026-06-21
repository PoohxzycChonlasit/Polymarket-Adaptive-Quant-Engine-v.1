#!/usr/bin/env python3
"""
tools/phase_b_snapshot_archiver.py
Immutable daily report snapshot archiver for Phase B.
"""

import os
import sys
import json
import shutil
from pathlib import Path

def run_snapshot_archiver() -> None:
    source_dir = Path("scratch/phase_b_daily_reports").resolve()
    dest_root = Path("runtime/quant_data/reports/phase_b_daily_snapshots").resolve()

    src_json_path = source_dir / "phase_b_dashboard.json"
    src_md_path = source_dir / "phase_b_dashboard.md"

    if not src_json_path.exists() or not src_md_path.exists():
        print(f"Error: Source dashboard files not found in {source_dir}", file=sys.stderr)
        sys.exit(1)

    # 1. Retrieve date from JSON dashboard file
    with open(src_json_path, "r", encoding="utf-8") as f:
        try:
            dashboard = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error: Malformed source JSON dashboard: {e}", file=sys.stderr)
            sys.exit(1)

    report_date = dashboard.get("report_date")
    if not report_date:
        print("Error: JSON dashboard is missing 'report_date' field.", file=sys.stderr)
        sys.exit(1)

    # Destination folder YYYY-MM-DD
    dest_dir = dest_root / report_date
    dest_json_path = dest_dir / "phase_b_dashboard.json"
    dest_md_path = dest_dir / "phase_b_dashboard.md"

    # 2. Never overwrite previous day
    if dest_json_path.exists() or dest_md_path.exists():
        print(f"Error: Snapshot for {report_date} already exists in {dest_dir}. Overwrite prohibited.", file=sys.stderr)
        sys.exit(1)

    # Create destination directory
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Copy files
    shutil.copy2(src_json_path, dest_json_path)
    shutil.copy2(src_md_path, dest_md_path)

    # 3. Validate snapshot integrity
    if not dest_json_path.exists() or not dest_md_path.exists():
        print("Error: File copy failed. Snapshots not found in destination.", file=sys.stderr)
        sys.exit(1)

    if dest_json_path.stat().st_size == 0 or dest_md_path.stat().st_size == 0:
        print("Error: Copied snapshot files are empty.", file=sys.stderr)
        sys.exit(1)

    with open(dest_json_path, "r", encoding="utf-8") as f:
        try:
            copied_dashboard = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error: Copied JSON is invalid: {e}", file=sys.stderr)
            sys.exit(1)

    # 4. Generate/update index: phase_b_snapshot_index.json
    index_path = dest_root / "phase_b_snapshot_index.json"
    index_data = {}
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            try:
                index_data = json.load(f)
            except json.JSONDecodeError:
                pass

    # Extract metrics from dashboard
    overall_status = copied_dashboard.get("overall_system_status", "NOT_READY")
    global_metrics = copied_dashboard.get("global_metrics", {})
    exception_count = global_metrics.get("exception_count", 0) + global_metrics.get("telemetry_exception_count", 0)
    heartbeat_age_seconds = global_metrics.get("heartbeat_age_seconds")

    # Sum joined_trades and compute average join_coverage_pct across filters
    filters = copied_dashboard.get("filters", {})
    joined_trades = 0
    coverage_sum = 0.0
    filter_count = 0
    for f_data in filters.values():
        joined_trades += f_data.get("joined_trades", 0)
        coverage_sum += f_data.get("join_coverage_pct", 100.0)
        filter_count += 1

    join_coverage_pct = (coverage_sum / filter_count) if filter_count > 0 else 100.0

    index_data[report_date] = {
        "date": report_date,
        "overall_status": overall_status,
        "joined_trades": joined_trades,
        "join_coverage_pct": join_coverage_pct,
        "exception_count": exception_count,
        "heartbeat_age_seconds": heartbeat_age_seconds
    }

    # Write updated index
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2)

    print(f"Snapshot successfully archived under: {dest_dir}")
    print(f"Index updated at: {index_path}")

def main() -> None:
    run_snapshot_archiver()

if __name__ == "__main__":
    main()
