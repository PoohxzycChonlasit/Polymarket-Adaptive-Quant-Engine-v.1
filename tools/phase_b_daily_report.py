#!/usr/bin/env python3
"""
tools/phase_b_daily_report.py
Daily reporting tool wrapping the Phase B daily evidence collector to generate dashboard reports.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project root to sys.path if not present
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tools.phase_b_daily_evidence_collector import run_evidence_collector, load_jsonl_file

STATUS_RANKS = {
    "NOT_READY": 0,
    "WATCHLIST": 1,
    "CANDIDATE": 2,
    "PROMOTION_REVIEW": 3
}

def determine_worst_case_status(filter_statuses: list[str]) -> str:
    """Returns the overall system status using the worst-case governance rule."""
    if not filter_statuses:
        return "NOT_READY"
    min_rank = min(STATUS_RANKS.get(status, 0) for status in filter_statuses)
    # Map back to string status
    rank_to_status = {v: k for k, v in STATUS_RANKS.items()}
    return rank_to_status.get(min_rank, "NOT_READY")

def main() -> None:
    parser = argparse.ArgumentParser(description="Phase B Daily Automated Report Dashboard.")
    parser.add_argument("--shadow-root", default="runtime/quant_data/signal_filter_shadow_phase_b", help="Path to shadow logs.")
    parser.add_argument("--trade-journal-root", default="runtime/quant_data/trade_journal", help="Path to trade journals.")
    parser.add_argument("--system-health-root", default="runtime/quant_data/system_health", help="Path to system health logs.")
    parser.add_argument("--output-dir", default="scratch/phase_b_daily_reports", help="Output folder (must be under scratch/).")
    parser.add_argument("--date", help="Optional override target YYYY-MM-DD date. Defaults to current UTC date.")
    parser.add_argument("--rolling-days", type=int, default=7, help="Number of rolling days.")

    args = parser.parse_args()

    # Path safety check
    output_dir = Path(args.output_dir).resolve()
    scratch_dir = Path("scratch").resolve()
    try:
        output_dir.relative_to(scratch_dir)
    except ValueError:
        print("Error: Output directory must be located inside the scratch/ folder.", file=sys.stderr)
        sys.exit(1)

    # Date handling
    if args.date:
        target_date_str = args.date
    else:
        target_date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"Running Phase B Daily Automated Report for target date: {target_date_str} (rolling: {args.rolling_days} days)")

    # Construct arguments for evidence collector
    collector_args = argparse.Namespace(
        shadow_root=args.shadow_root,
        trade_journal_root=args.trade_journal_root,
        system_health_root=args.system_health_root,
        output_dir=args.output_dir,
        date=target_date_str,
        rolling_days=args.rolling_days
    )

    # Run the collector (creates phase_b_daily_evidence_<date>.json and .md)
    run_evidence_collector(collector_args)

    # Read the produced json output to compile dashboard
    json_report_path = output_dir / f"phase_b_daily_evidence_{target_date_str}.json"
    if not json_report_path.exists():
        print(f"Error: Collector did not produce expected file: {json_report_path}", file=sys.stderr)
        sys.exit(1)

    with open(json_report_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Global variables from JSON report
    days_observed = data.get("days_observed", 0)
    runtime_health_data = data.get("runtime_health", {})
    active_run_id = runtime_health_data.get("active_run_id", "unknown")
    active_pid = runtime_health_data.get("active_pid", "unknown")
    heartbeat_fresh = runtime_health_data.get("heartbeat_fresh", False)
    total_closed_trades = runtime_health_data.get("total_closed_trades", 0)

    # Parse exceptions & heartbeat age from system health log directly
    system_root = Path(args.system_health_root)
    health_events_today = load_jsonl_file(system_root / f"{target_date_str}.jsonl")
    
    exception_count = 0
    heartbeat_age_seconds = -1.0
    
    if health_events_today:
        # Count exception types
        exception_count = sum(1 for event in health_events_today if "exception" in event.get("event_type", "").lower() or "error" in event.get("event_type", "").lower())
        
        last_health = health_events_today[-1]
        ts_str = last_health.get("timestamp_utc")
        if ts_str:
            try:
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                now_utc = datetime.now(timezone.utc)
                heartbeat_age_seconds = (now_utc - dt).total_seconds()
            except Exception:
                pass

    # Extract filter status
    filters_data = data.get("filters", {})
    filter_statuses = [f_data.get("status", "NOT_READY") for f_data in filters_data.values()]
    overall_system_status = determine_worst_case_status(filter_statuses)

    # Accumulate telemetry exception counts from all filters
    telemetry_exception_count = sum(f_data.get("exception_count", 0) for f_data in filters_data.values())

    # Build Dashboard JSON structure
    dashboard_json = {
        "report_date": target_date_str,
        "rolling_days": args.rolling_days,
        "days_observed": days_observed,
        "overall_system_status": overall_system_status,
        "global_metrics": {
            "active_run_id": active_run_id,
            "active_pid": active_pid,
            "runtime_health": "HEALTHY" if (heartbeat_fresh and exception_count == 0) else "UNHEALTHY",
            "heartbeat_age_seconds": heartbeat_age_seconds if heartbeat_age_seconds >= 0 else None,
            "heartbeat_fresh": heartbeat_fresh,
            "exception_count": exception_count,
            "telemetry_exception_count": telemetry_exception_count,
            "total_closed_trades": total_closed_trades
        },
        "filters": {}
    }

    for fname, f_data in filters_data.items():
        pass_rate = f_data.get("pass_rate", 0.0)
        block_rate = 1.0 - pass_rate if f_data.get("candidates_seen", 0) > 0 else 0.0
        
        dashboard_json["filters"][fname] = {
            "telemetry_rows": f_data.get("candidates_seen", 0),
            "joined_trades": f_data.get("closed_candidates_seen", 0),
            "join_coverage_pct": f_data.get("join_coverage_pct", 100.0),
            "pass_rate": pass_rate,
            "block_rate": block_rate,
            "net_pnl": f_data.get("realized_pnl", 0.0),
            "profit_factor": f_data.get("profit_factor", "UNDEFINED"),
            "max_drawdown": f_data.get("max_drawdown", 0.0),
            "governance_status": f_data.get("status", "NOT_READY")
        }

    # Write dashboard.json
    dash_json_path = output_dir / "phase_b_dashboard.json"
    with open(dash_json_path, "w", encoding="utf-8") as f:
        json.dump(dashboard_json, f, indent=2)

    # Write dashboard.md
    dash_md_path = output_dir / "phase_b_dashboard.md"
    
    # Format age display
    age_display = f"{heartbeat_age_seconds:.1f}s" if heartbeat_age_seconds >= 0 else "unknown"

    md_content = f"""# Phase B Telemetry Automated Report & Dashboard
**Report Date**: {target_date_str} (UTC)  
**Overall System State**: **{overall_system_status}**  

---

## 1. Global Metrics
* **Active Run ID**: `{active_run_id}`
* **Active PID**: `{active_pid}`
* **Runtime Health Status**: `{dashboard_json['global_metrics']['runtime_health']}`
* **Heartbeat Fresh**: `{heartbeat_fresh}` (Age: {age_display})
* **Global System Exception Count**: {exception_count}
* **Telemetry Exception Count**: {telemetry_exception_count}
* **Total Closed Trades Today**: {total_closed_trades}
* **Calendar Days Observed**: {days_observed} days

---

## 2. Shadow Filter Evidence Summary

| Filter Name | Governance Status | Telemetry Rows | Joined Trades | Join Coverage | Pass Rate | Block Rate | Net PnL | Profit Factor | Max DD |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    for fname in sorted(dashboard_json["filters"]):
        f_val = dashboard_json["filters"][fname]
        pf_display = f"{f_val['profit_factor']:.2f}" if isinstance(f_val['profit_factor'], float) else str(f_val['profit_factor'])
        md_content += f"| `{fname}` | **{f_val['governance_status']}** | {f_val['telemetry_rows']} | {f_val['joined_trades']} | {f_val['join_coverage_pct']:.1f}% | {f_val['pass_rate']:.1%} | {f_val['block_rate']:.1%} | ${f_val['net_pnl']:.2f} | {pf_display} | ${f_val['max_drawdown']:.2f} |\n"

    md_content += f"""
---

## 3. Governance Alert Panel
* **System Health State**: {"SYSTEM_OPERATIONAL" if (heartbeat_fresh and exception_count == 0) else "SYSTEM_DEGRADED_OR_STALE"}
* **Governance Status Target**: {overall_system_status} (Controlled under the worst-case governance rule).
"""

    with open(dash_md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"Automated Dashboard successfully compiled:")
    print(f"- JSON: {dash_json_path}")
    print(f"- Markdown: {dash_md_path}")
    print(f"OVERALL_SYSTEM_STATE: {overall_system_status}")

if __name__ == "__main__":
    main()
