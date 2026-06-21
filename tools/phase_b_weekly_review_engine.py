#!/usr/bin/env python3
"""
tools/phase_b_weekly_review_engine.py
Weekly review engine for Phase B governance - snapshot-only source of truth.
"""

import os
import sys
import json
import math
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Add project root to sys.path if not present
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Seed filter PF thresholds
CANDIDATE_PF_THRESHOLDS = {
    "combined_conservative_shadow": 1.25,
    "combined_broad_shadow": 1.10,
    "block_normal_vol_shadow": 1.15,
    "block_btc_shadow": 1.00,
}

PROMO_PF_THRESHOLDS = {
    "combined_conservative_shadow": 1.35,
    "combined_broad_shadow": 1.15,
    "block_normal_vol_shadow": 1.20,
    "block_btc_shadow": 1.00,
}

STATUS_RANKINGS = {
    "NOT_READY": 0,
    "WATCHLIST": 1,
    "CANDIDATE": 2,
    "PROMOTION_REVIEW": 3
}

def get_candidate_pf_threshold(filter_name: str) -> float:
    return CANDIDATE_PF_THRESHOLDS.get(filter_name, 1.10)

def get_promo_pf_threshold(filter_name: str) -> float:
    return PROMO_PF_THRESHOLDS.get(filter_name, 1.20)

def map_pf_to_float(pf: Any) -> float:
    if pf in ("INF", "INFINITY", float('inf')):
        return 10.0
    if pf in ("UNDERPOWERED", "UNDEFINED", None):
        return 0.0
    try:
        val = float(pf)
        return val if not math.isnan(val) else 0.0
    except (ValueError, TypeError):
        return 0.0

def calculate_mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)

def calculate_std(values: List[float], mean_val: float) -> float:
    if len(values) <= 1:
        return 0.0
    variance = sum((x - mean_val) ** 2 for x in values) / len(values)
    return math.sqrt(variance)

def calculate_max_drawdown(pnls: List[float]) -> float:
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
    non_flat = [t for t in passed_trades if t["pnl"] != 0]
    if not non_flat:
        return 0.0
    winners = [t for t in non_flat if t["pnl"] > 0]
    return len(winners) / len(non_flat)

def run_weekly_review_engine(
    index_path: Path,
    snapshots_dir: Path,
    output_dir: Path,
    target_date_str: str = None,
    window_days: int = 7
) -> Dict[str, Any]:
    # 1. Load Snapshot Index
    if not index_path.exists():
        print(f"Warning: Index file not found at {index_path}. Using fallback.", file=sys.stderr)
        index_data = {}
    else:
        with open(index_path, "r", encoding="utf-8") as f:
            try:
                index_data = json.load(f)
            except json.JSONDecodeError:
                print(f"Error: Malformed index file: {index_path}", file=sys.stderr)
                index_data = {}

    # 2. Determine target date
    if not target_date_str:
        if index_data:
            target_date_str = max(index_data.keys())
        else:
            target_date_str = datetime.utcnow().strftime("%Y-%m-%d")

    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
    except ValueError:
        print(f"Error: Invalid date format: {target_date_str}. Must be YYYY-MM-DD.", file=sys.stderr)
        sys.exit(1)

    review_dates = [(target_date - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(window_days)]
    review_dates.reverse() # chronologically first

    # 3. Load daily snapshots in window
    valid_snapshots = []
    discovered_filters = set()
    malformed_snapshots = 0

    for d in review_dates:
        snap_json = snapshots_dir / d / "phase_b_dashboard.json"
        if not snap_json.exists():
            malformed_snapshots += 1
            continue
        try:
            with open(snap_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not data or "filters" not in data:
                    malformed_snapshots += 1
                    continue
                valid_snapshots.append(data)
                for f_key in data.get("filters", {}).keys():
                    discovered_filters.add(f_key)
        except Exception:
            malformed_snapshots += 1

    compiled_filter_metrics = {}
    global_missing_metrics = set()

    for f_name in discovered_filters:
        # Load daily series from snapshots for stability
        pf_series = []
        dd_series = []

        for snap in valid_snapshots:
            f_snap = snap.get("filters", {}).get(f_name, {})
            if f_snap:
                pf_val = f_snap.get("profit_factor")
                dd_val = f_snap.get("max_drawdown")
                if pf_val is not None:
                    pf_series.append(map_pf_to_float(pf_val))
                if dd_val is not None:
                    dd_series.append(float(dd_val))

        # Extract latest metrics
        sample_count = None
        joined_trade_count = None
        join_coverage_pct = None
        pass_rate = None
        block_rate = None
        allowed_pnl = None
        blocked_pnl = None
        shadow_pf = None
        max_drawdown = None
        baseline_max_drawdown = None
        exception_count = None
        schema_completeness_pct = None
        winrate = None
        baseline_winrate = None

        if valid_snapshots:
            latest_snap = valid_snapshots[-1]
            f_snap = latest_snap.get("filters", {}).get(f_name, {})
            if f_snap:
                sample_count = f_snap.get("telemetry_rows")
                joined_trade_count = f_snap.get("joined_trades")
                join_coverage_pct = f_snap.get("join_coverage_pct")
                pass_rate = f_snap.get("pass_rate")
                block_rate = f_snap.get("block_rate")
                allowed_pnl = f_snap.get("net_pnl")
                blocked_pnl = f_snap.get("rejected_pnl")
                shadow_pf = f_snap.get("profit_factor")
                max_drawdown = f_snap.get("max_drawdown")
                baseline_max_drawdown = f_snap.get("baseline_max_drawdown")
                winrate = f_snap.get("winrate")
                baseline_winrate = f_snap.get("baseline_winrate")
                schema_completeness_pct = f_snap.get("schema_completeness_pct")
                exception_count = f_snap.get("exception_count")

        # Track missing metrics
        local_missing = []
        metrics_check = {
            "telemetry_rows": sample_count,
            "joined_trades": joined_trade_count,
            "join_coverage_pct": join_coverage_pct,
            "pass_rate": pass_rate,
            "block_rate": block_rate,
            "net_pnl": allowed_pnl,
            "rejected_pnl": blocked_pnl,
            "profit_factor": shadow_pf,
            "max_drawdown": max_drawdown,
            "baseline_max_drawdown": baseline_max_drawdown,
            "winrate": winrate,
            "baseline_winrate": baseline_winrate,
            "schema_completeness_pct": schema_completeness_pct,
            "exception_count": exception_count
        }

        for m_name, m_val in metrics_check.items():
            if m_val is None:
                local_missing.append(m_name)
                global_missing_metrics.add(m_name)

        runtime_days = len(valid_snapshots)

        # 5. Stability Calculations
        cv_pf = 1.0
        if len(pf_series) > 1:
            mean_pf = calculate_mean(pf_series)
            std_pf = calculate_std(pf_series, mean_pf)
            if mean_pf > 0.0:
                cv_pf = std_pf / mean_pf
            else:
                cv_pf = 1.0

        cv_dd = 0.0
        if len(dd_series) > 1:
            mean_dd = calculate_mean(dd_series)
            std_dd = calculate_std(dd_series, mean_dd)
            if mean_dd > 0.0:
                cv_dd = std_dd / mean_dd
            else:
                cv_dd = 0.0

        # 6. Confidence Scoring
        sample_size_score = min(20.0, (joined_trade_count / 50.0) * 20.0) if joined_trade_count is not None else 0.0
        
        if join_coverage_pct is not None and join_coverage_pct >= 90.0:
            join_quality_score = min(20.0, ((join_coverage_pct - 90.0) / 10.0) * 20.0)
        else:
            join_quality_score = 0.0

        expected_days = float(window_days)
        consistency_score = 20.0 * (len(valid_snapshots) / expected_days) if expected_days > 0 else 0.0

        pf_stability_score = max(0.0, min(20.0, 20.0 * (1.0 - cv_pf)))
        dd_stability_score = max(0.0, min(20.0, 20.0 * (1.0 - cv_dd)))

        confidence_breakdown = {
            "sample_size": int(round(sample_size_score)),
            "join_quality": int(round(join_quality_score)),
            "pf_stability": int(round(pf_stability_score)),
            "drawdown_stability": int(round(dd_stability_score)),
            "runtime_days": int(round(consistency_score))
        }
        confidence_score = sum(confidence_breakdown.values())

        # 7. Status Engine
        failures = []
        if exception_count is not None and exception_count > 0:
            failures.append(f"Telemetry exceptions detected: {exception_count}")
        if malformed_snapshots > 0:
            failures.append(f"Malformed or missing daily snapshots: {malformed_snapshots}")
        if join_coverage_pct is not None and join_coverage_pct < 95.0:
            failures.append(f"Join coverage {join_coverage_pct:.2f}% is below 95%")
        if schema_completeness_pct is not None and schema_completeness_pct < 100.0:
            failures.append(f"Schema completeness {schema_completeness_pct:.2f}% is below 100%")
        if local_missing:
            failures.append(f"Missing snapshot metrics: {', '.join(local_missing)}")

        if allowed_pnl is not None and blocked_pnl is not None:
            delta_vs_baseline = allowed_pnl - (allowed_pnl + blocked_pnl)
        else:
            delta_vs_baseline = None

        if joined_trade_count is not None and joined_trade_count >= 20:
            if blocked_pnl is not None and blocked_pnl > 0.0:
                failures.append(f"Blocked profitable trades (positive rejected PnL: {blocked_pnl:.6f} USD)")
            if delta_vs_baseline is not None and delta_vs_baseline <= 0.0:
                failures.append(f"Negative or zero baseline delta: {delta_vs_baseline:.6f} USD")
            if max_drawdown is not None and baseline_max_drawdown is not None and max_drawdown > baseline_max_drawdown:
                failures.append(f"Drawdown worse than baseline: {max_drawdown:.6f} vs {baseline_max_drawdown:.6f}")

        # Status Logic
        status = "NOT_READY"
        shadow_pf_val = map_pf_to_float(shadow_pf)

        schema_ok = (schema_completeness_pct == 100.0) if schema_completeness_pct is not None else False

        not_ready_triggered = (
            runtime_days < 3 or
            joined_trade_count is None or
            joined_trade_count < 20 or
            join_coverage_pct is None or
            join_coverage_pct < 95.0 or
            not schema_ok or
            exception_count is None or
            exception_count > 0 or
            malformed_snapshots > 0 or
            shadow_pf in ("UNDEFINED", "UNDERPOWERED", None)
        )

        if not not_ready_triggered:
            watchlist_ok = (
                delta_vs_baseline is not None and delta_vs_baseline > 0.0 and
                shadow_pf_val >= 1.0 and
                max_drawdown is not None and baseline_max_drawdown is not None and
                max_drawdown <= baseline_max_drawdown * 1.10
            )
            if watchlist_ok:
                status = "WATCHLIST"
                
                cand_threshold = get_candidate_pf_threshold(f_name)
                candidate_ok = (
                    runtime_days >= 5 and
                    joined_trade_count >= 35 and
                    join_coverage_pct >= 97.0 and
                    shadow_pf_val >= cand_threshold and
                    winrate is not None and baseline_winrate is not None and
                    winrate >= baseline_winrate - 0.05 and
                    max_drawdown <= baseline_max_drawdown and
                    blocked_pnl is not None and blocked_pnl <= 0.0
                )
                if candidate_ok:
                    status = "CANDIDATE"

                    promo_threshold = get_promo_pf_threshold(f_name)
                    promotion_ok = (
                        runtime_days >= 7 and
                        joined_trade_count >= 50 and
                        join_coverage_pct >= 98.0 and
                        blocked_pnl is not None and blocked_pnl < 0.0 and
                        max_drawdown <= baseline_max_drawdown and
                        winrate is not None and baseline_winrate is not None and
                        winrate >= baseline_winrate and
                        shadow_pf_val >= promo_threshold and
                        not failures
                    )
                    if promotion_ok:
                        status = "PROMOTION_REVIEW"

        # 8. Recommendation Engine
        if failures:
            recommendation = "REJECT"
            reason = f"Governance failure: {'; '.join(failures)}"
        elif status == "PROMOTION_REVIEW":
            recommendation = "PROMOTE"
            reason = "Filter meets all Promotion Review sufficiency thresholds."
        elif status == "CANDIDATE":
            recommendation = "KEEP"
            reason = "Filter satisfies Candidate requirements; continue monitoring."
        elif status == "WATCHLIST":
            recommendation = "KEEP"
            reason = "Filter on watchlist; positive performance but insufficient volume."
        else:
            recommendation = "WATCH"
            reason = f"Filter not ready. Sufficiency bounds not met: {runtime_days}/3 days, {joined_trade_count}/20 trades."

        # 9. Promotion Freeze Layer
        promotion_allowed = True
        promotion_block_reason = None
        if runtime_days < 14:
            promotion_allowed = False
            promotion_block_reason = "Minimum 14-day evidence window not met."

        compiled_filter_metrics[f_name] = {
            "filter_name": f_name,
            "sample_count": sample_count,
            "joined_trade_count": joined_trade_count,
            "join_coverage_pct": join_coverage_pct,
            "pass_rate": pass_rate,
            "block_rate": block_rate,
            "allowed_pnl": allowed_pnl,
            "blocked_pnl": blocked_pnl,
            "shadow_pf": shadow_pf,
            "max_drawdown": max_drawdown,
            "exception_count": exception_count,
            "schema_completeness_pct": schema_completeness_pct,
            "runtime_days": runtime_days,
            "status": status,
            "reason": reason,
            "recommendation": recommendation,
            "confidence_score": confidence_score,
            "confidence_breakdown": confidence_breakdown,
            "promotion_allowed": promotion_allowed,
            "promotion_block_reason": promotion_block_reason,
            "delta_vs_baseline": delta_vs_baseline,
            "baseline_max_drawdown": baseline_max_drawdown,
            "winrate": winrate,
            "baseline_winrate": baseline_winrate
        }

    # 10. Weekly Summary Rankings
    top_candidate_filter = "None"
    worst_filter = "None"
    highest_pf_filter = "None"
    highest_drawdown_filter = "None"
    most_stable_filter = "None"

    if compiled_filter_metrics:
        # Top Candidate: status Candidate/Promotion with highest delta
        candidates = [
            f for f in compiled_filter_metrics.values()
            if f["status"] in ("CANDIDATE", "PROMOTION_REVIEW") and f["delta_vs_baseline"] is not None
        ]
        if candidates:
            candidates.sort(key=lambda x: (x["delta_vs_baseline"], map_pf_to_float(x["shadow_pf"])), reverse=True)
            top_candidate_filter = candidates[0]["filter_name"]

        # Worst Filter: lowest status rank, then lowest delta
        all_filters = list(compiled_filter_metrics.values())
        all_filters.sort(key=lambda x: (
            STATUS_RANKINGS.get(x["status"], 0),
            x["delta_vs_baseline"] if x["delta_vs_baseline"] is not None else -float('inf')
        ))
        worst_filter = all_filters[0]["filter_name"]

        # Highest PF
        all_filters.sort(key=lambda x: map_pf_to_float(x["shadow_pf"]), reverse=True)
        highest_pf_filter = all_filters[0]["filter_name"]

        # Highest Drawdown
        all_filters.sort(key=lambda x: x["max_drawdown"] if x["max_drawdown"] is not None else -float('inf'), reverse=True)
        highest_drawdown_filter = all_filters[0]["filter_name"]

        # Most Stable (Highest confidence score)
        all_filters.sort(key=lambda x: x["confidence_score"], reverse=True)
        most_stable_filter = all_filters[0]["filter_name"]

    review_report = {
        "review_date": target_date_str,
        "window_days": window_days,
        "valid_snapshots_loaded": len(valid_snapshots),
        "source_of_truth": "snapshot_archive",
        "source_integrity": {
            "raw_telemetry_used": False,
            "snapshot_days_loaded": len(valid_snapshots),
            "malformed_snapshots": malformed_snapshots,
            "missing_metrics": sorted(list(global_missing_metrics))
        },
        "filters": compiled_filter_metrics,
        "weekly_summary": {
            "top_candidate_filter": top_candidate_filter,
            "worst_filter": worst_filter,
            "highest_pf_filter": highest_pf_filter,
            "highest_drawdown_filter": highest_drawdown_filter,
            "most_stable_filter": most_stable_filter
        }
    }

    # Write Outputs
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / "phase_b_weekly_review.json", "w", encoding="utf-8") as f:
        json.dump(review_report, f, indent=2)

    # Compile MD report
    md_content = f"""# Phase B Weekly Evidence Review Report
**Report Date**: {target_date_str} (UTC)  
**Review Window**: Last {window_days} Days ({len(valid_snapshots)} snapshots loaded)  
**Source of Truth**: `snapshot_archive`  

---

## 1. Executive Summary
This report presents the weekly governance review of dynamically discovered shadow filters. This is an offline review layer only and does not modify runtime behavior.

---

## 2. Source Integrity
* **Raw Telemetry Logs Read**: `NO`
* **Snapshot Days Loaded**: {len(valid_snapshots)}
* **Malformed Snapshots Encountered**: {malformed_snapshots}
* **Missing Snapshot Metrics**: {', '.join(sorted(list(global_missing_metrics))) if global_missing_metrics else 'None'}

---

## 3. Weekly Summary rankings
* **Top Candidate Filter**: `{top_candidate_filter}`
* **Worst Filter**: `{worst_filter}`
* **Highest PF Filter**: `{highest_pf_filter}`
* **Highest Drawdown Filter**: `{highest_drawdown_filter}`
* **Most Stable Filter**: `{most_stable_filter}`

---

## 4. Filter Evidence Table

| Filter Name | Status | Recommendation | Joined Trades | Pass Rate | PF | Max DD | PnL Delta | Confidence | Promo Allowed | Block Reason |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
"""
    for fname in sorted(compiled_filter_metrics.keys()):
        f = compiled_filter_metrics[fname]
        pf_display = f"{f['shadow_pf']:.2f}" if isinstance(f['shadow_pf'], float) else str(f['shadow_pf'])
        promo_allowed_str = "YES" if f["promotion_allowed"] else "NO"
        block_reason_str = f["promotion_block_reason"] if f["promotion_block_reason"] else "-"
        
        trades_display = f["joined_trade_count"] if f["joined_trade_count"] is not None else "N/A"
        pass_display = f"{f['pass_rate']:.1%}" if f["pass_rate"] is not None else "N/A"
        dd_display = f"${f['max_drawdown']:.2f}" if f["max_drawdown"] is not None else "N/A"
        delta_display = f"${f['delta_vs_baseline']:.2f}" if f["delta_vs_baseline"] is not None else "N/A"

        md_content += f"| `{fname}` | **{f['status']}** | **{f['recommendation']}** | {trades_display} | {pass_display} | {pf_display} | {dd_display} | {delta_display} | {f['confidence_score']} | {promo_allowed_str} | {block_reason_str} |\n"

    md_content += """
---

## 5. Confidence Score Breakdown
"""
    for fname in sorted(compiled_filter_metrics.keys()):
        f = compiled_filter_metrics[fname]
        b = f["confidence_breakdown"]
        md_content += f"""
### `{fname}` (Score: {f['confidence_score']}/100)
* **Sample Size Score**: {b['sample_size']}/20
* **Join Quality Score**: {b['join_quality']}/20
* **PF Stability Score**: {b['pf_stability']}/20
* **Drawdown Stability Score**: {b['drawdown_stability']}/20
* **Runtime Days Consistency Score**: {b['runtime_days']}/20
"""

    md_content += """
---

## 6. Governance Decision Log & Notes
* All status assignments are derived from `PHASE_B_7DAY_EVIDENCE_COLLECTION_GOVERNANCE_001.md`.
* Promotion Freeze Layer is active: no promotions can be deployed to Phase C until `runtime_days >= 14` is achieved, regardless of candidate status.
"""

    with open(output_dir / "phase_b_weekly_review.md", "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"Weekly Review Report successfully written to:")
    print(f"- JSON: {output_dir / 'phase_b_weekly_review.json'}")
    print(f"- Markdown: {output_dir / 'phase_b_weekly_review.md'}")

    return review_report

def main() -> None:
    parser = argparse.ArgumentParser(description="Phase B Weekly Governance Review Engine.")
    parser.add_argument("--index-path", default="runtime/quant_data/reports/phase_b_daily_snapshots/phase_b_snapshot_index.json", help="Path to index.")
    parser.add_argument("--snapshots-dir", default="runtime/quant_data/reports/phase_b_daily_snapshots", help="Snapshots directory.")
    parser.add_argument("--output-dir", default="scratch/phase_b_weekly_review", help="Output directory.")
    parser.add_argument("--date", help="Optional override target date (YYYY-MM-DD).")
    parser.add_argument("--window-days", type=int, default=7, help="Rolling review window days.")

    args = parser.parse_args()

    run_weekly_review_engine(
        index_path=Path(args.index_path),
        snapshots_dir=Path(args.snapshots_dir),
        output_dir=Path(args.output_dir),
        target_date_str=args.date,
        window_days=args.window_days
    )

if __name__ == "__main__":
    main()
