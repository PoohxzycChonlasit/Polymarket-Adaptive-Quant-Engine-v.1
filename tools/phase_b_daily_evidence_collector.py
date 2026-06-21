#!/usr/bin/env python3
"""
tools/phase_b_daily_evidence_collector.py
Offline tool for gathering Phase B daily and rolling 7-day shadow telemetry evidence metrics.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Active governance filters
ACTIVE_FILTERS = {
    "block_btc_shadow",
    "block_normal_vol_shadow",
    "combined_broad_shadow",
    "combined_conservative_shadow"
}

# Monitored schema fields for completeness check
REQUIRED_SCHEMA_KEYS = {
    "filter_name", "filter_version", "filter_params", "shadow_pass",
    "shadow_reason", "would_trade", "run_id", "signal_id",
    "candidate_instance_id", "paper_trade_replay_key", "asset",
    "side", "edge", "ev", "probability", "entry_price", "proposed_size_usd"
}

def check_schema_complete(payload: Dict[str, Any]) -> bool:
    """Returns True if all required keys are present in the payload."""
    return all(k in payload for k in REQUIRED_SCHEMA_KEYS)

def calculate_max_drawdown(pnls: List[float]) -> float:
    """Calculates max peak-to-trough drawdown of cumulative PnL series."""
    if not pnls:
        return 0.0
    cum_pnl = [0.0]
    for p in pnls:
        cum_pnl.append(cum_pnl[-1] + p)
    
    max_dd = 0.0
    peak = -float('inf')
    for val in cum_pnl:
        if val > peak:
            peak = val
        dd = peak - val
        if dd > max_dd:
            max_dd = dd
    return max_dd

def calculate_profit_factor(passed_trades: List[Dict[str, Any]]) -> Any:
    """Calculates profit factor based on trade PnLs."""
    if len(passed_trades) < 10:
        return "UNDERPOWERED"
    
    gross_profit = sum(t["pnl"] for t in passed_trades if t["pnl"] > 0)
    gross_loss = sum(t["pnl"] for t in passed_trades if t["pnl"] < 0)
    
    if gross_profit > 0 and gross_loss == 0:
        return "INF"
    if gross_profit == 0 and gross_loss == 0:
        return "UNDEFINED"
    return gross_profit / abs(gross_loss)

def calculate_winrate(passed_trades: List[Dict[str, Any]]) -> float:
    """Calculates win rate as winning / non-flat trades."""
    non_flat = [t for t in passed_trades if t["pnl"] != 0]
    if not non_flat:
        return 0.0
    winners = [t for t in non_flat if t["pnl"] > 0]
    return len(winners) / len(non_flat)

def load_jsonl_file(path: Path) -> List[Dict[str, Any]]:
    """Loads all valid JSON lines from a file, returning a list of dicts."""
    records = []
    if not path.exists():
        return records
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records

def collect_records_for_dates(root_dir: Path, dates: List[str]) -> List[Dict[str, Any]]:
    """Accumulates all records across multiple daily JSONL files."""
    all_records = []
    for d in dates:
        path = root_dir / f"{d}.jsonl"
        all_records.extend(load_jsonl_file(path))
    return all_records

def get_governance_status(metrics: Dict[str, Any], days_observed: int) -> str:
    """Determines the governance promotion state status for the filter."""
    total_closed = metrics["closed_candidates_seen"]
    join_cov = metrics["join_coverage_pct"]
    schema_complete = metrics["schema_complete_rows"]
    schema_incomplete = metrics["schema_incomplete_rows"]
    exceptions = metrics["exception_count"]
    delta = metrics["delta_vs_baseline"]
    pf = metrics["profit_factor"]
    max_dd = metrics["max_drawdown"]
    base_dd = metrics["baseline_max_drawdown"]
    wr = metrics["winrate"]
    base_wr = metrics.get("baseline_winrate", 0.0)
    rejected_pnl = metrics["rejected_pnl"]
    
    # 1. NOT_READY triggers
    schema_ok = (schema_incomplete == 0 and schema_complete > 0)
    if (
        days_observed < 3 or
        total_closed < 20 or
        join_cov < 95.0 or
        not schema_ok or
        exceptions > 0 or
        pf == "UNDEFINED" or
        pf == "UNDERPOWERED"
    ):
        return "NOT_READY"
        
    # 2. WATCHLIST triggers
    try:
        pf_val = float(pf) if pf not in ("INF", "UNDEFINED", "UNDERPOWERED") else float('inf')
    except (ValueError, TypeError):
        pf_val = 0.0
        
    watchlist_ok = (
        days_observed >= 3 and
        total_closed >= 20 and
        join_cov >= 95.0 and
        exceptions == 0 and
        delta > 0.0 and
        pf_val >= 1.00 and
        max_dd <= base_dd * 1.10
    )
    
    # 3. CANDIDATE triggers
    filter_name = metrics["filter_name"]
    candidate_pf_thresholds = {
        "block_btc_shadow": 1.00,
        "block_normal_vol_shadow": 1.15,
        "combined_broad_shadow": 1.10,
        "combined_conservative_shadow": 1.25
    }
    cand_threshold = candidate_pf_thresholds.get(filter_name, 1.00)
    
    candidate_ok = (
        watchlist_ok and
        days_observed >= 5 and
        total_closed >= 35 and
        join_cov >= 97.0 and
        delta > 0.0 and
        pf_val >= cand_threshold and
        wr >= base_wr - 0.05 and
        max_dd <= base_dd and
        rejected_pnl <= 0.0
    )
    
    # 4. PROMOTION_REVIEW triggers
    promo_pf_thresholds = {
        "block_btc_shadow": 1.00,
        "block_normal_vol_shadow": 1.20,
        "combined_broad_shadow": 1.15,
        "combined_conservative_shadow": 1.35
    }
    promo_threshold = promo_pf_thresholds.get(filter_name, 1.00)
    
    promotion_ok = (
        candidate_ok and
        days_observed >= 7 and
        total_closed >= 50 and
        join_cov >= 98.0 and
        delta > 0.0 and
        rejected_pnl < 0.0 and
        max_dd <= base_dd and
        wr >= base_wr and
        pf_val >= promo_threshold
    )
    
    if promotion_ok:
        return "PROMOTION_REVIEW"
    if candidate_ok:
        return "CANDIDATE"
    if watchlist_ok:
        return "WATCHLIST"
    return "NOT_READY"

def compile_metrics(
    filter_name: str,
    shadow_events: List[Dict[str, Any]],
    closed_trades: List[Dict[str, Any]],
    total_closed_count: int,
    days_observed: int
) -> Dict[str, Any]:
    """Compiles daily and rolling metrics for a given shadow filter."""
    filter_events = [e for e in shadow_events if e.get("payload", {}).get("filter_name") == filter_name]
    
    complete_count = 0
    incomplete_count = 0
    exception_count = 0
    
    primary_map = {}
    fallback_map = {}
    reject_reasons = {}
    
    for event in filter_events:
        payload = event.get("payload", {})
        
        if check_schema_complete(payload):
            complete_count += 1
        else:
            incomplete_count += 1
            
        run_id = payload.get("run_id")
        candidate_instance_id = payload.get("candidate_instance_id")
        replay_key = payload.get("paper_trade_replay_key")
        shadow_pass = payload.get("shadow_pass", True)
        shadow_reason = payload.get("shadow_reason")
        
        if run_id and candidate_instance_id:
            primary_map[(run_id, candidate_instance_id)] = shadow_pass
        if replay_key:
            fallback_map[replay_key] = shadow_pass
            
        if not shadow_pass and shadow_reason:
            reject_reasons[shadow_reason] = reject_reasons.get(shadow_reason, 0) + 1
            
    baseline_trades = []
    passed_trades = []
    rejected_trades = []
    
    for t in closed_trades:
        payload = t.get("payload", {})
        run_id = t.get("run_id")
        candidate_instance_id = payload.get("entry_attribution", {}).get("candidate_instance_id") or payload.get("candidate_instance_id")
        replay_key = payload.get("paper_trade_replay_key")
        
        shadow_pass = None
        if run_id and candidate_instance_id and (run_id, candidate_instance_id) in primary_map:
            shadow_pass = primary_map[(run_id, candidate_instance_id)]
        elif replay_key and replay_key in fallback_map:
            shadow_pass = fallback_map[replay_key]
            
        if shadow_pass is not None:
            trade_info = {
                "pnl": payload.get("pnl", 0.0),
                "shadow_pass": shadow_pass
            }
            baseline_trades.append(trade_info)
            if shadow_pass:
                passed_trades.append(trade_info)
            else:
                rejected_trades.append(trade_info)
                
    max_dd = calculate_max_drawdown([t["pnl"] for t in passed_trades])
    baseline_max_dd = calculate_max_drawdown([t["pnl"] for t in baseline_trades])
    
    realized_pnl = sum(t["pnl"] for t in passed_trades)
    rejected_pnl = sum(t["pnl"] for t in rejected_trades)
    baseline_pnl = realized_pnl + rejected_pnl
    delta_vs_baseline = realized_pnl - baseline_pnl
    
    candidates_seen = len(filter_events)
    candidates_passed = sum(1 for e in filter_events if e.get("payload", {}).get("shadow_pass", True))
    candidates_rejected = candidates_seen - candidates_passed
    pass_rate = candidates_passed / candidates_seen if candidates_seen > 0 else 0.0
    
    closed_candidates_seen = len(baseline_trades)
    join_coverage_pct = (closed_candidates_seen / total_closed_count * 100.0) if total_closed_count > 0 else 100.0
    
    pf = calculate_profit_factor(passed_trades)
    winrate = calculate_winrate(passed_trades)
    baseline_winrate = calculate_winrate(baseline_trades)
    
    top_reject_reason = None
    if reject_reasons:
        top_reject_reason = max(reject_reasons, key=reject_reasons.get)
        
    metrics = {
        "filter_name": filter_name,
        "filter_version": "1.0.0",
        "candidates_seen": candidates_seen,
        "candidates_passed": candidates_passed,
        "candidates_rejected": candidates_rejected,
        "pass_rate": pass_rate,
        "closed_candidates_seen": closed_candidates_seen,
        "passed_closed_count": len(passed_trades),
        "join_coverage_pct": join_coverage_pct,
        "realized_pnl": realized_pnl,
        "rejected_pnl": rejected_pnl,
        "baseline_pnl": baseline_pnl,
        "delta_vs_baseline": delta_vs_baseline,
        "profit_factor": pf,
        "winrate": winrate,
        "baseline_winrate": baseline_winrate,
        "max_drawdown": max_dd,
        "baseline_max_drawdown": baseline_max_dd,
        "top_reject_reason": top_reject_reason,
        "schema_complete_rows": complete_count,
        "schema_incomplete_rows": incomplete_count,
        "exception_count": exception_count,
    }
    
    metrics["status"] = get_governance_status(metrics, days_observed)
    return metrics

def run_evidence_collector(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir).resolve()
    scratch_dir = Path("scratch").resolve()
    try:
        output_dir.relative_to(scratch_dir)
    except ValueError:
        print("Error: Output directory must be located inside the scratch/ folder.", file=sys.stderr)
        sys.exit(1)
        
    shadow_root = Path(args.shadow_root)
    trade_root = Path(args.trade_journal_root)
    system_root = Path(args.system_health_root)
    
    target_date_str = args.date
    rolling_days = args.rolling_days
    
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
    except ValueError:
        print("Error: Date must be YYYY-MM-DD format.", file=sys.stderr)
        sys.exit(1)
        
    rolling_dates = [(target_date - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(rolling_days)]
    
    health_events_today = load_jsonl_file(system_root / f"{target_date_str}.jsonl")
    active_pid = "unknown"
    active_run_id = "unknown"
    heartbeat_fresh = False
    
    if health_events_today:
        last_health = health_events_today[-1]
        active_run_id = last_health.get("run_id", "unknown")
        payload = last_health.get("payload", {})
        active_pid = payload.get("owner_pid", "unknown")
        
        ts_str = last_health.get("timestamp_utc")
        if ts_str:
            try:
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                now_utc = datetime.now(timezone.utc)
                age_seconds = (now_utc - dt).total_seconds()
                heartbeat_fresh = (age_seconds < 300)
            except Exception:
                pass

    shadow_events = collect_records_for_dates(shadow_root, rolling_dates)
    trade_journal = collect_records_for_dates(trade_root, rolling_dates)
    
    days_observed = 0
    for d in rolling_dates:
        if (shadow_root / f"{d}.jsonl").exists():
            days_observed += 1
            
    closed_trades = [t for t in trade_journal if t.get("event_type") == "trade_close"]
    total_closed_count = len(closed_trades)
    
    filter_metrics = {}
    for filter_name in ACTIVE_FILTERS:
        filter_metrics[filter_name] = compile_metrics(
            filter_name=filter_name,
            shadow_events=shadow_events,
            closed_trades=closed_trades,
            total_closed_count=total_closed_count,
            days_observed=days_observed
        )
        
    output_dir.mkdir(parents=True, exist_ok=True)
    
    json_output_path = output_dir / f"phase_b_daily_evidence_{target_date_str}.json"
    md_output_path = output_dir / f"phase_b_daily_evidence_{target_date_str}.md"
    
    report_json = {
        "date": target_date_str,
        "rolling_days": rolling_days,
        "days_observed": days_observed,
        "runtime_health": {
            "active_run_id": active_run_id,
            "active_pid": active_pid,
            "heartbeat_fresh": heartbeat_fresh,
            "total_closed_trades": total_closed_count
        },
        "filters": filter_metrics
    }
    
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(report_json, f, indent=2)
        
    md_content = f"""# Daily Evidence Metrics Report: Phase B Passive Shadow Telemetry
**Date**: {target_date_str}  
**Rolling Window**: {rolling_days} Days (Observed: {days_observed} calendar days)  
**Run ID**: `{active_run_id}` (PID: `{active_pid}`)  
**Heartbeat Fresh**: {heartbeat_fresh}  

---

## 1. Filter Evidence Metrics Summary

| Filter Name | Status | Candidates Seen | Closed Trades | Pass Rate | Realized PnL | Rejected PnL | Delta vs Baseline | Profit Factor | Winrate | Max DD |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    for fname in sorted(ACTIVE_FILTERS):
        m = filter_metrics[fname]
        pf_display = f"{m['profit_factor']:.2f}" if isinstance(m['profit_factor'], float) else str(m['profit_factor'])
        md_content += f"| `{fname}` | **{m['status']}** | {m['candidates_seen']} | {m['closed_candidates_seen']} | {m['pass_rate']:.1%} | ${m['realized_pnl']:.2f} | ${m['rejected_pnl']:.2f} | ${m['delta_vs_baseline']:.2f} | {pf_display} | {m['winrate']:.1%} | ${m['max_drawdown']:.2f} |\n"
        
    md_content += """
---

## 2. Details & Integrity Metrics
"""
    for fname in sorted(ACTIVE_FILTERS):
        m = filter_metrics[fname]
        md_content += f"""
### Filter: `{fname}`
* **Governance Status**: `{m['status']}`
* **Schema Integrity**: Complete: {m['schema_complete_rows']} | Incomplete: {m['schema_incomplete_rows']}
* **Coverage**: Closed Joined: {m['closed_candidates_seen']} / {total_closed_count} ({m['join_coverage_pct']:.1f}%)
* **Exception Count**: {m['exception_count']}
* **Top Reject Reason**: `{m['top_reject_reason']}`
"""
    with open(md_output_path, "w", encoding="utf-8") as f:
        f.write(md_content)
        
    print(f"Reports successfully written to:\n- {json_output_path}\n- {md_output_path}")

def main() -> None:
    parser = argparse.ArgumentParser(description="Phase B daily evidence metrics collector.")
    parser.add_argument("--shadow-root", default="runtime/quant_data/signal_filter_shadow_phase_b", help="Path to shadow telemetry logs.")
    parser.add_argument("--trade-journal-root", default="runtime/quant_data/trade_journal", help="Path to trade journal logs.")
    parser.add_argument("--system-health-root", default="runtime/quant_data/system_health", help="Path to system health logs.")
    parser.add_argument("--output-dir", default="scratch/phase_b_daily_evidence/output", help="Output directory under scratch/.")
    parser.add_argument("--date", required=True, help="Target YYYY-MM-DD date.")
    parser.add_argument("--rolling-days", type=int, default=7, help="Number of rolling days.")
    
    args = parser.parse_args()
    run_evidence_collector(args)

if __name__ == "__main__":
    main()
