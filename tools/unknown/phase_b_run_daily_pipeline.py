#!/usr/bin/env python3
"""
tools/phase_b_run_daily_pipeline.py
One-command manual Phase B daily reporting and snapshot archiving pipeline runner.
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run manual Phase B daily evidence pipeline.")
    parser.add_argument("--date", help="Target date YYYY-MM-DD. Defaults to current UTC date.")
    return parser.parse_args()

def main() -> None:
    args = parse_args()

    # Default to current UTC date
    if args.date:
        target_date_str = args.date
    else:
        target_date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Validate date format
    try:
        datetime.strptime(target_date_str, "%Y-%m-%d")
    except ValueError:
        print(f"Error: Invalid date format '{target_date_str}'. Expected YYYY-MM-DD.", file=sys.stderr)
        sys.exit(1)

    print(f"==================================================")
    print(f"   STARTING PHASE B DAILY PIPELINE RUNNER         ")
    print(f"   Target Date: {target_date_str}                 ")
    print(f"==================================================")

    # Resolve paths
    project_root = Path(__file__).resolve().parent.parent
    daily_report_script = project_root / "tools" / "phase_b_daily_report.py"
    snapshot_archiver_script = project_root / "tools" / "phase_b_snapshot_archiver.py"
    snapshot_summary_script = project_root / "tools" / "phase_b_snapshot_summary.py"

    dashboard_dir = project_root / "scratch" / "phase_b_daily_reports"
    dash_json_path = dashboard_dir / "phase_b_dashboard.json"
    dash_md_path = dashboard_dir / "phase_b_dashboard.md"
    
    snapshot_root = project_root / "runtime" / "quant_data" / "reports" / "phase_b_daily_snapshots"
    snapshot_dir = snapshot_root / target_date_str
    snapshot_index_path = snapshot_root / "phase_b_snapshot_index.json"
    
    summary_path = project_root / "scratch" / "phase_b_7day_snapshot_summary.md"

    # Step A: Run daily report
    print(f"[Step 1/3] Compiling daily dashboard...")
    cmd_report = [sys.executable, str(daily_report_script), "--date", target_date_str]
    res_report = subprocess.run(cmd_report, capture_output=True, text=True, cwd=str(project_root))
    if res_report.returncode != 0:
        print(f"Error: Step A (daily report) failed with code {res_report.returncode}.", file=sys.stderr)
        print(res_report.stderr, file=sys.stderr)
        sys.exit(1)
    print("Dashboard generated successfully.")

    # Step B: Check snapshot folder to prevent duplicate overwrite
    snapshot_status = "failed"
    if snapshot_dir.exists():
        print(f"[Warning] Snapshot for {target_date_str} already exists at {snapshot_dir}.")
        print("Skipping archiver to prevent duplicate overwrite. Proceeding to summary.")
        snapshot_status = "already_exists"
    else:
        print(f"[Step 2/3] Archiving daily snapshot...")
        cmd_archive = [sys.executable, str(snapshot_archiver_script)]
        res_archive = subprocess.run(cmd_archive, capture_output=True, text=True, cwd=str(project_root))
        if res_archive.returncode != 0:
            print(f"Error: Step B (snapshot archiver) failed with code {res_archive.returncode}.", file=sys.stderr)
            print(res_archive.stderr, file=sys.stderr)
            sys.exit(1)
        snapshot_status = "created"
        print("Snapshot archived successfully.")

    # Step C: Run snapshot summary
    print(f"[Step 3/3] Generating rolling snapshot summary...")
    cmd_summary = [sys.executable, str(snapshot_summary_script)]
    res_summary = subprocess.run(cmd_summary, capture_output=True, text=True, cwd=str(project_root))
    if res_summary.returncode != 0:
        print(f"Error: Step C (snapshot summary) failed with code {res_summary.returncode}.", file=sys.stderr)
        print(res_summary.stderr, file=sys.stderr)
        sys.exit(1)
    print("Rolling summary generated successfully.")

    # Step D: Health checks
    print(f"\n[Health Checks] Verifying output integrity...")
    
    if not dash_json_path.exists():
        print(f"Error: Health Check Failed. Dashboard JSON does not exist at {dash_json_path}", file=sys.stderr)
        sys.exit(1)
        
    if not dash_md_path.exists():
        print(f"Error: Health Check Failed. Dashboard MD does not exist at {dash_md_path}", file=sys.stderr)
        sys.exit(1)

    if not summary_path.exists():
        print(f"Error: Health Check Failed. Snapshot summary does not exist at {summary_path}", file=sys.stderr)
        sys.exit(1)

    if not snapshot_index_path.exists():
        print(f"Error: Health Check Failed. Snapshot index JSON does not exist at {snapshot_index_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(snapshot_index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Health Check Failed. Index JSON at {snapshot_index_path} is malformed: {e}", file=sys.stderr)
        sys.exit(1)

    print("Health Checks: ALL PASSED")

    # Load dashboard data for operator display
    overall_status = "unknown"
    joined_trades = "unknown"
    join_coverage = "unknown"
    try:
        with open(dash_json_path, "r", encoding="utf-8") as f:
            dash_data = json.load(f)
            overall_status = dash_data.get("overall_system_status", "unknown")
            
            filters = dash_data.get("filters", {})
            if filters:
                joined_trades = sum(f_val.get("joined_trades", 0) for f_val in filters.values())
                covs = [f_val.get("join_coverage_pct", 100.0) for f_val in filters.values()]
                join_coverage = f"{sum(covs)/len(covs):.1f}%"
    except Exception:
        pass

    # Step E: Operator Summary
    print(f"==================================================")
    print(f"   PHASE B DAILY PIPELINE RUNNER SUMMARY          ")
    print(f"==================================================")
    print(f"Target Date:       {target_date_str}")
    print(f"Dashboard JSON:    {dash_json_path.relative_to(project_root)}")
    print(f"Dashboard MD:      {dash_md_path.relative_to(project_root)}")
    print(f"Snapshot Status:   {snapshot_status.upper()}")
    if snapshot_status in ("created", "already_exists"):
        print(f"Snapshot Path:     {snapshot_dir.relative_to(project_root) if snapshot_dir.exists() else 'N/A'}")
    print(f"Summary Path:      {summary_path.relative_to(project_root)}")
    print(f"--------------------------------------------------")
    print(f"Overall Status:    {overall_status}")
    print(f"Total Closed:      {joined_trades} trades")
    print(f"Avg Join Coverage: {join_coverage}")
    print(f"==================================================")

if __name__ == "__main__":
    main()
