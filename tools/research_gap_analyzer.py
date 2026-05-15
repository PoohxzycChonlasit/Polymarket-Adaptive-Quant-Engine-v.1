from __future__ import annotations

import json
import os
import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
import numpy as np

def _calculate_percentiles(data: list[float]) -> dict[str, float]:
    """Calculates min, p50, p90, max for a list of values."""
    if not data:
        return {"min": 0.0, "p50": 0.0, "p90": 0.0, "max": 0.0}
    return {
        "min": float(np.min(data)),
        "p50": float(np.percentile(data, 50)),
        "p90": float(np.percentile(data, 90)),
        "max": float(np.max(data)),
    }

def analyze_research_log(file_path: str | Path) -> dict[str, Any]:
    """Analyzes a research_log JSONL file for Readiness Regression Analysis v1."""
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}

    # Tracking by market/window grouping for high-level stats
    market_windows = set()

    stats = {
        "total_snapshots": 0,
        "tickers": Counter(),
        "lifecycle_phases": Counter(),
        "actual_decisions": Counter(),
        "theoretical_decisions": Counter(),
        "skip_reasons": Counter(),
        "cutoff_skips": 0,
        "stale_feed_skips": 0,
        "shadow_opportunities": 0,
        "opportunity_phases": Counter(),
        "empty_book_phases": Counter(),
        "stale_feed_phases": Counter(),
        
        # Readiness Distributions
        "first_seen_seconds": [],
        "first_evaluable_seconds": [],
        "first_tradable_seconds": [],
        "first_min_depth_seconds": [],
        "token_id_delays": [],
        "orderbook_warmup_delays": [],
        "time_to_min_depth_seconds": [],
        
        # Liquidity Depth Stats
        "liquidity_depth_states": Counter(),
        "tradable_but_thin_total": 0,
        "depth_oscillation_total": 0,
        "spread_oscillation_total": 0,
        "executable_book_states": Counter(),
        "readiness_bottlenecks": Counter(),
        
        # Compact cases
        "late_ready_cases": [],  # (market_id, ticker, reason)
        "empty_book_durations": [],
    }

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    payload = event.get("payload", {})
                    if not payload:
                        payload = event
                    
                    if "event_type" in payload and payload.get("event_type") != "research_snapshot":
                         if "payload" not in event:
                             continue

                    stats["total_snapshots"] += 1
                    ticker = payload.get("ticker", "UNKNOWN")
                    stats["tickers"][ticker] += 1
                    
                    phase = payload.get("lifecycle_phase", "UNKNOWN")
                    stats["lifecycle_phases"][phase] += 1
                    
                    actual = payload.get("actual_decision", "UNKNOWN")
                    stats["actual_decisions"][actual] += 1
                    
                    shadow = payload.get("shadow_inventory", {})
                    theoretical = shadow.get("theoretical_decision", "UNKNOWN")
                    stats["theoretical_decisions"][theoretical] += 1
                    
                    reason = payload.get("actual_skip_reason", "")
                    if actual == "skip" and reason:
                        stats["skip_reasons"][reason] += 1
                        if "cutoff" in reason.lower() or "hard_close" in reason.lower():
                            stats["cutoff_skips"] += 1
                        if "stale" in reason.lower() or "feed" in reason.lower():
                            stats["stale_feed_skips"] += 1
                            stats["stale_feed_phases"][phase] += 1
                        if "empty_book" in reason.lower():
                            stats["empty_book_phases"][phase] += 1
                    
                    if actual == "skip" and theoretical in {"WOULD_OPEN", "WOULD_RELOAD"}:
                        stats["shadow_opportunities"] += 1
                        stats["opportunity_phases"][phase] += 1

                    # New Observability Fields v1
                    depth_state = payload.get("liquidity_depth_state", "UNKNOWN")
                    stats["liquidity_depth_states"][depth_state] += 1
                    
                    book_state = payload.get("executable_book_state", "UNKNOWN")
                    stats["executable_book_states"][book_state] += 1
                    
                    stats["tradable_but_thin_total"] += int(payload.get("tradable_but_thin_count", 0))
                    stats["depth_oscillation_total"] += int(payload.get("depth_oscillation_count", 0))
                    stats["spread_oscillation_total"] += int(payload.get("spread_oscillation_count", 0))

                    # Grouping for per-market window tracking
                    market_id = payload.get("market_id") or payload.get("condition_id", "GLOBAL")
                    window_key = market_id
                    if "epoch_start" in payload:
                        window_key = f"{market_id}_{payload['epoch_start']}"
                    market_windows.add(window_key)

                    # Latency tracking
                    first_seen = payload.get("first_discovered_seconds_remaining") or payload.get("first_seen_seconds_remaining") or payload.get("seconds_remaining")
                    if first_seen is not None:
                        stats["first_seen_seconds"].append(int(first_seen))
                    
                    first_eval = payload.get("first_token_ready_seconds_remaining") or payload.get("token_ready_seconds_remaining") or payload.get("first_evaluable_seconds_remaining")
                    if first_eval is not None:
                        stats["first_evaluable_seconds"].append(int(first_eval))
                        if first_seen is not None:
                            stats["token_id_delays"].append(max(0, int(first_seen) - int(first_eval)))

                    first_tradable = payload.get("first_tradable_seconds_remaining") or payload.get("orderbook_ready_seconds_remaining")
                    if first_tradable is not None:
                        stats["first_tradable_seconds"].append(int(first_tradable))
                        if first_eval is not None:
                            stats["orderbook_warmup_delays"].append(max(0, int(first_eval) - int(first_tradable)))
                        
                        # Late Ready Detection
                        cutoff = 35 # Default
                        if int(first_tradable) <= cutoff:
                            # Only add if not already added for this window to keep it compact
                            if not any(c[0] == market_id for c in stats["late_ready_cases"]):
                                stats["late_ready_cases"].append((
                                    market_id, 
                                    ticker, 
                                    f"Book ready at {first_tradable}s remaining (<= {cutoff}s cutoff)"
                                ))

                    first_min_depth = payload.get("first_min_depth_seconds_remaining")
                    if first_min_depth is not None:
                        stats["first_min_depth_seconds"].append(int(first_min_depth))
                        time_to_depth = payload.get("time_to_min_depth_seconds")
                        if time_to_depth is not None:
                            stats["time_to_min_depth_seconds"].append(int(time_to_depth))

                    if actual == "skip" and "empty_book" in reason.lower():
                        duration = payload.get("empty_book_recovery_duration_ms", 0)
                        stats["empty_book_durations"].append(float(duration) / 1000.0)

                    # Bottleneck Classification per Snapshot
                    if not payload.get("token_ids_ready", payload.get("token_ready", False)):
                        stats["readiness_bottlenecks"]["TOKEN_ID"] += 1
                    elif not payload.get("orderbook_ready", False):
                        stats["readiness_bottlenecks"]["ORDERBOOK_SYNC"] += 1
                    elif not payload.get("nonzero_bidask", False):
                        stats["readiness_bottlenecks"]["EMPTY_BOOK"] += 1
                    elif not payload.get("spread_ready", payload.get("spread_normalized", False)):
                        stats["readiness_bottlenecks"]["SPREAD_WIDE"] += 1
                    elif depth_state in {"EMPTY", "THIN"}:
                        stats["readiness_bottlenecks"]["LIQUIDITY_DEPTH"] += 1
                    elif int(payload.get("seconds_remaining", 300)) <= cutoff:
                        stats["readiness_bottlenecks"]["LATE_ZONE"] += 1

                except json.JSONDecodeError:
                    continue
    except Exception as e:
        return {"error": str(e)}

    # Aggregates
    stats["first_seen_s_dist"] = _calculate_percentiles(stats["first_seen_seconds"])
    stats["first_eval_s_dist"] = _calculate_percentiles(stats["first_evaluable_seconds"])
    stats["first_tradable_s_dist"] = _calculate_percentiles(stats["first_tradable_seconds"])
    
    stats["avg_token_id_delay"] = np.mean(stats["token_id_delays"]) if stats["token_id_delays"] else 0.0
    stats["avg_orderbook_warmup_delay"] = np.mean(stats["orderbook_warmup_delays"]) if stats["orderbook_warmup_delays"] else 0.0
    stats["avg_empty_book_duration"] = np.mean(stats["empty_book_durations"]) if stats["empty_book_durations"] else 0.0

    # Root Cause Classification
    total = stats["total_snapshots"]
    num_windows = len(market_windows) or 1
    if total < 5:
        root_cause = "INSUFFICIENT_DATA"
        recommendation = "KEEP_COLLECTING"
    elif stats["shadow_opportunities"] > (total * 0.1):
        root_cause = "SHADOW_INVENTORY_PROMISING"
        recommendation = "SHADOW_CUTOFF_EXPERIMENT"
    elif stats["first_seen_s_dist"]["p50"] < 280:
        root_cause = "DISCOVERY_LATE"
        recommendation = "PRELOAD_NEXT_MARKET"
    elif stats["avg_token_id_delay"] > 15:
        root_cause = "TOKEN_ID_DELAY"
        recommendation = "TOKEN_CACHE_IMPROVEMENT"
    elif stats["avg_orderbook_warmup_delay"] > 15:
        root_cause = "ORDERBOOK_WARMUP_DELAY"
        recommendation = "ORDERBOOK_WARMUP_RETRY_TUNING"
    elif stats["stale_feed_skips"] > (total * 0.1):
        root_cause = "FEED_STALENESS"
        recommendation = "STALE_FEED_FIX"
    elif len(stats["late_ready_cases"]) > (num_windows * 0.2):
        root_cause = "BOOK_REGRESSION_AFTER_READY"
        recommendation = "SHADOW_CUTOFF_EXPERIMENT"
    elif stats["cutoff_skips"] > (total * 0.2):
        root_cause = "CUTOFF_POLICY"
        recommendation = "SHADOW_CUTOFF_EXPERIMENT"
    else:
        root_cause = "OPTIMAL_READINESS"
        recommendation = "BOT_CORRECTLY_DEFENSIVE"

    stats["root_cause"] = root_cause
    stats["recommendation"] = recommendation
    return stats

def print_summary(stats: dict[str, Any]):
    """Compact summary output."""
    if "error" in stats:
        print(f"Error: {stats['error']}")
        return

    print(f"--- Readiness Regression Analyzer v1 ---")
    print(f"Total Snapshots: {stats['total_snapshots']}")
    print(f"Tickers: {dict(stats['tickers'])}")
    print(f"Decisions: Actual={dict(stats['actual_decisions'])} | Shadow={dict(stats['theoretical_decisions'])}")
    
    print(f"\n--- Readiness Distributions (seconds remaining) ---")
    d_seen = stats['first_seen_s_dist']
    print(f"First Discovered: min={d_seen['min']:.1f} | p50={d_seen['p50']:.1f} | p90={d_seen['p90']:.1f} | max={d_seen['max']:.1f}")
    
    d_trade = stats['first_tradable_s_dist']
    print(f"First Tradable:   min={d_trade['min']:.1f} | p50={d_trade['p50']:.1f} | p90={d_trade['p90']:.1f} | max={d_trade['max']:.1f}")

    if stats["first_min_depth_seconds"]:
        d_depth = _calculate_percentiles(stats["first_min_depth_seconds"])
        print(f"First Min Depth:  min={d_depth['min']:.1f} | p50={d_depth['p50']:.1f} | p90={d_depth['p90']:.1f} | max={d_depth['max']:.1f}")

    print(f"\n--- Liquidity Depth Analysis ---")
    print(f"Depth States: {dict(stats['liquidity_depth_states'])}")
    print(f"Avg Time to Min Depth: {np.mean(stats['time_to_min_depth_seconds']):.1f}s" if stats["time_to_min_depth_seconds"] else "Avg Time to Min Depth: 0.0s")
    print(f"Tradable But Thin: {stats['tradable_but_thin_total']}")
    print(f"Oscillations: Depth={stats['depth_oscillation_total']} | Spread={stats['spread_oscillation_total']}")

    print(f"\n--- Readiness Bottlenecks (Snapshot Counts) ---")
    print(f"Bottlenecks: {dict(stats['readiness_bottlenecks'])}")
    if stats["readiness_bottlenecks"]:
        dominant = stats["readiness_bottlenecks"].most_common(1)[0][0]
        print(f"Dominant Bottleneck: {dominant}")

    print(f"\n--- Latency Bottlenecks ---")
    print(f"Avg Token ID Delay:   {stats['avg_token_id_delay']:.1f}s")
    print(f"Avg OB Warmup Delay:  {stats['avg_orderbook_warmup_delay']:.1f}s")
    print(f"Avg Empty Book Dur:   {stats['avg_empty_book_duration']:.1f}s")

    if stats["empty_book_phases"]:
        print(f"Empty Book by Phase: {dict(stats['empty_book_phases'])}")
    if stats["stale_feed_phases"]:
        print(f"Stale Feed by Phase: {dict(stats['stale_feed_phases'])}")

    if stats["late_ready_cases"]:
        print(f"\n--- Late Ready Cases (Top 10) ---")
        for case in stats["late_ready_cases"][:10]:
            print(f"  - {case[0]} ({case[1]}): {case[2]}")

    print(f"\n--- Analysis Summary ---")
    print(f"Shadow Opportunities: {stats['shadow_opportunities']}")
    print(f"ROOT CAUSE:     {stats['root_cause']}")
    print(f"RECOMMENDATION: {stats['recommendation']}")
    print(f"---------------------------------------")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file_path", help="Path to research_log JSONL file")
    args = parser.parse_args()
    
    results = analyze_research_log(args.file_path)
    print_summary(results)
