import json
import os
import sys
import argparse
from typing import List, Dict, Any, Tuple

def is_safe_scratch_path(path_str: str) -> bool:
    """
    Validates that the resolved absolute path resides under the project's scratch/ directory.
    Case-insensitive check for cross-platform robustness.
    """
    abs_path = os.path.abspath(path_str)
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_root = os.path.dirname(tools_dir)
    scratch_dir = os.path.abspath(os.path.join(workspace_root, "scratch"))
    try:
        common = os.path.commonpath([scratch_dir, abs_path])
        return common.lower() == scratch_dir.lower()
    except Exception:
        return False

def evaluate_filter(record: Dict[str, Any], filter_name: str) -> Dict[str, Any]:
    """
    Evaluates a single record against the named shadow filter.
    Handles missing fields according to safe default specifications.
    """
    asset = record.get("asset")
    edge = record.get("edge")
    volatility_regime = record.get("volatility_regime")
    
    shadow_pass = True
    shadow_reject_reason = None
    
    if filter_name == "block_btc_shadow":
        # pass if asset != BTC. Missing asset defaults to pass.
        if asset == "BTC":
            shadow_pass = False
            shadow_reject_reason = "REJECT_BTC_ASSET"
            
    elif filter_name == "block_edge_lt_005_shadow":
        # pass if edge >= 0.05. Missing edge defaults to reject.
        if edge is None:
            shadow_pass = False
            shadow_reject_reason = "MISSING_EDGE"
        elif edge < 0.05:
            shadow_pass = False
            shadow_reject_reason = "REJECT_EDGE_LT_005"
            
    elif filter_name == "block_normal_vol_shadow":
        # pass if volatility_regime != NORMAL_VOL. Missing volatility_regime defaults to reject.
        if volatility_regime is None:
            shadow_pass = False
            shadow_reject_reason = "MISSING_VOLATILITY_REGIME"
        elif volatility_regime == "NORMAL_VOL":
            shadow_pass = False
            shadow_reject_reason = "REJECT_NORMAL_VOL"
            
    elif filter_name == "combined_conservative_shadow":
        # pass if asset == ETH AND edge >= 0.05 AND edge < 0.15. Missing fields default to reject.
        if asset != "ETH":
            shadow_pass = False
            shadow_reject_reason = "REJECT_NOT_ETH"
        elif edge is None:
            shadow_pass = False
            shadow_reject_reason = "MISSING_EDGE"
        elif edge < 0.05 or edge >= 0.15:
            shadow_pass = False
            shadow_reject_reason = "REJECT_EDGE_OUT_OF_BOUNDS"
            
    elif filter_name == "combined_broad_shadow":
        # pass if asset == ETH AND edge >= 0.05. Missing fields default to reject.
        if asset != "ETH":
            shadow_pass = False
            shadow_reject_reason = "REJECT_NOT_ETH"
        elif edge is None:
            shadow_pass = False
            shadow_reject_reason = "MISSING_EDGE"
        elif edge < 0.05:
            shadow_pass = False
            shadow_reject_reason = "REJECT_EDGE_LT_005"
    else:
        raise ValueError(f"Unknown filter: {filter_name}")
        
    return {
        "shadow_filter_name": filter_name,
        "shadow_pass": shadow_pass,
        "shadow_reject_reason": shadow_reject_reason
    }

def get_pnl(record: Dict[str, Any]) -> float:
    """
    Safely resolves trade PnL from available metadata fields.
    """
    for key in ("execution_pnl_5_share_model", "execution_pnl", "pnl"):
        val = record.get(key)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                pass
    return 0.0

def calculate_metrics(passed_records: List[Dict[str, Any]], filter_name: str, baseline_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes statistical metrics over passed records compared against a baseline dataset.
    Drawdown calculation uses a baseline peak equity model of 250.0 USD.
    """
    baseline_count = len(baseline_records)
    evaluated_count = len(baseline_records)
    passed_count = len(passed_records)
    rejected_count = evaluated_count - passed_count
    
    pass_rate = (passed_count / evaluated_count) * 100.0 if evaluated_count > 0 else 0.0
    freq_red = ((baseline_count - passed_count) / baseline_count) * 100.0 if baseline_count > 0 else 0.0
    
    wins = sum(1 for r in passed_records if get_pnl(r) > 0)
    losses = sum(1 for r in passed_records if get_pnl(r) < 0)
    total_outcome_trades = wins + losses
    wr = (wins / total_outcome_trades) if total_outcome_trades > 0 else 0.0
    
    gross_profit = sum(max(0.0, get_pnl(r)) for r in passed_records)
    gross_loss = sum(abs(min(0.0, get_pnl(r))) for r in passed_records)
    
    if gross_loss > 0.0:
        pf = gross_profit / gross_loss
    else:
        pf = float('inf') if gross_profit > 0.0 else 1.0
        
    net_pnl = sum(get_pnl(r) for r in passed_records)
    avg_pnl = net_pnl / passed_count if passed_count > 0 else 0.0
    
    # Calculate Max Drawdown
    # Sort by timestamp, fallback to sequence order
    sorted_passed = sorted(
        passed_records, 
        key=lambda x: x.get("timestamp_utc") or x.get("timestamp") or ""
    )
    
    equity = 250.0
    peak = equity
    max_dd = 0.0
    max_dd_pct = 0.0
    
    for r in sorted_passed:
        trade_pnl = get_pnl(r)
        equity += trade_pnl
        if equity > peak:
            peak = equity
        dd = peak - equity
        dd_pct = (dd / peak) * 100.0 if peak > 0.0 else 0.0
        if dd > max_dd:
            max_dd = dd
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct
            
    # Longest loss streak
    longest_loss_streak = 0
    curr_streak = 0
    for r in sorted_passed:
        if get_pnl(r) < 0:
            curr_streak += 1
            longest_loss_streak = max(longest_loss_streak, curr_streak)
        else:
            curr_streak = 0
            
    # Sample confidence label
    if passed_count < 30:
        sample_label = "LOW_SAMPLE"
    elif passed_count <= 100:
        sample_label = "MEDIUM_SAMPLE"
    else:
        sample_label = "HIGH_SAMPLE"
        
    # Baseline comparison metrics
    baseline_gp = sum(max(0.0, get_pnl(r)) for r in baseline_records)
    baseline_gl = sum(abs(min(0.0, get_pnl(r))) for r in baseline_records)
    if baseline_gl > 0.0:
        baseline_pf = baseline_gp / baseline_gl
    else:
        baseline_pf = float('inf') if baseline_gp > 0.0 else 1.0
        
    baseline_net_pnl = sum(get_pnl(r) for r in baseline_records)
    
    delta_pf = pf - baseline_pf if (pf != float('inf') and baseline_pf != float('inf')) else 0.0
    delta_net_pnl = net_pnl - baseline_net_pnl
    
    return {
        "candidates_evaluated": evaluated_count,
        "candidates_passed": passed_count,
        "candidates_rejected": rejected_count,
        "pass_rate": pass_rate,
        "wins": wins,
        "losses": losses,
        "WR": wr,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "PF": pf,
        "net_pnl": net_pnl,
        "avg_pnl": avg_pnl,
        "max_drawdown": max_dd,
        "max_drawdown_pct": max_dd_pct,
        "longest_loss_streak": longest_loss_streak,
        "sample_confidence_label": sample_label,
        "delta_pf_vs_baseline": delta_pf,
        "delta_net_pnl_vs_baseline": delta_net_pnl,
        "trade_frequency_reduction": freq_red
    }

def process_file(input_file: str, output_dir: str, filter_selection: str) -> None:
    """
    Main evaluation pipeline: loads JSONL input, runs filters, calculates metrics,
    and outputs results safely into the target scratch directory.
    """
    # Enforce safe scratch path for outputs
    if not is_safe_scratch_path(output_dir):
        raise ValueError(f"Output directory path is outside scratch/: {output_dir}")
        
    os.makedirs(output_dir, exist_ok=True)
    
    # Load and validate joined records
    records = []
    with open(input_file, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            try:
                rec = json.loads(line_stripped)
                # Validation checks for valid record structure
                if not isinstance(rec, dict):
                    print(f"Skipping line {idx}: Row is not a JSON object.", file=sys.stderr)
                    continue
                records.append(rec)
            except json.JSONDecodeError as e:
                # Fail-closed validation logic
                raise ValueError(f"Unparseable JSON line {idx}: {str(e)}")
                
    # Determine which filters to evaluate
    all_available_filters = [
        "block_btc_shadow",
        "block_edge_lt_005_shadow",
        "block_normal_vol_shadow",
        "combined_conservative_shadow",
        "combined_broad_shadow"
    ]
    
    if filter_selection == "all":
        filters_to_run = all_available_filters
    else:
        filters_to_run = [f.strip() for f in filter_selection.split(",") if f.strip()]
        for f in filters_to_run:
            if f not in all_available_filters:
                raise ValueError(f"Unknown filter request: {f}")
                
    events = []
    summary = {}
    
    for filt in filters_to_run:
        passed_records = []
        for rec in records:
            eval_res = evaluate_filter(rec, filt)
            shadow_pass = eval_res["shadow_pass"]
            
            # Emit runtime-like event log schema
            event_log = {
                "timestamp_utc": rec.get("timestamp_utc") or rec.get("timestamp"),
                "run_id": rec.get("run_id") or rec.get("source_run_id"),
                "asset": rec.get("asset"),
                "side/outcome": rec.get("side") or rec.get("outcome") or rec.get("side/outcome"),
                "edge": rec.get("edge"),
                "ev": rec.get("ev") or rec.get("ev_after_spread"),
                "volatility_regime": rec.get("volatility_regime"),
                "trend_regime": rec.get("trend_regime"),
                "shadow_filter_name": filt,
                "shadow_pass": shadow_pass,
                "shadow_reject_reason": eval_res["shadow_reject_reason"],
                "execution_pnl_5_share_model": get_pnl(rec),
                "source_event_ref": rec.get("source_event_ref") or "shadow_filter_evaluator_ref"
            }
            events.append(event_log)
            
            if shadow_pass:
                passed_records.append(rec)
                
        # Calculate summary statistics for this filter
        summary[filt] = calculate_metrics(passed_records, filt, records)
        
    # Write output event logs to scratch
    events_path = os.path.join(output_dir, "shadow_filter_events.jsonl")
    with open(events_path, "w", encoding="utf-8") as f_out:
        for ev in events:
            f_out.write(json.dumps(ev) + "\n")
            
    # Write summary stats JSON file to scratch
    summary_path = os.path.join(output_dir, "shadow_filter_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f_out:
        json.dump(summary, f_out, indent=2)
        
    print(f"Shadow evaluation completed. Events: {len(events)}, Filters Run: {len(summary)}")
    print(f"Outputs written to: {output_dir}")

def main() -> None:
    parser = argparse.ArgumentParser(description="Offline Shadow Filter Evaluator")
    parser.add_argument("--input", required=True, help="Path to input joined records JSONL file")
    parser.add_argument("--output-dir", required=True, help="Path to target output directory (must resolve under scratch/)")
    parser.add_argument("--filters", default="all", help="Comma-separated filters to evaluate or 'all'")
    
    args = parser.parse_args()
    
    try:
        process_file(args.input, args.output_dir, args.filters)
    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
