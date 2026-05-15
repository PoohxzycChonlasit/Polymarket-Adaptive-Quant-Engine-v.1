import pytest
import json
import os
import numpy as np
from collections import defaultdict
from tools.research_gap_analyzer import analyze_research_log, _calculate_percentiles

def test_calculate_percentiles():
    data = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    result = _calculate_percentiles(data)
    assert result["min"] == 10.0
    assert result["p50"] == 55.0 # (50+60)/2
    assert result["p90"] == 91.0 # numpy default interpolation
    assert result["max"] == 100.0

    data_empty = []
    result_empty = _calculate_percentiles(data_empty)
    assert result_empty == {"min": 0.0, "p50": 0.0, "p90": 0.0, "max": 0.0}

def test_readiness_regression_analyzer_logic(tmp_path):
    """Verify analyzer correctly counts latency and regression fields."""
    log_file = tmp_path / "test_regression.jsonl"
    
    events = [
        # Market 1: Good discovery, good tradable, then empty book regression
        {"payload": {"market_id": "market_A", "epoch_start": 1000, "ticker": "BTC", "actual_decision": "skip", "actual_skip_reason": "empty_book", "shadow_inventory": {"theoretical_decision": "HOLD"}, "lifecycle_phase": "ACTIVE_INVENTORY_TRADING", "first_seen_seconds_remaining": 295, "token_ready_seconds_remaining": 280, "orderbook_ready_seconds_remaining": 270}},
        {"payload": {"market_id": "market_A", "epoch_start": 1000, "ticker": "BTC", "actual_decision": "skip", "actual_skip_reason": "empty_book_recovery", "shadow_inventory": {"theoretical_decision": "HOLD"}, "lifecycle_phase": "ACTIVE_INVENTORY_TRADING", "empty_book_recovery_duration_ms": 5000, "first_seen_seconds_remaining": 295, "token_ready_seconds_remaining": 280, "orderbook_ready_seconds_remaining": 270}},
        {"payload": {"market_id": "market_A", "epoch_start": 1000, "ticker": "BTC", "actual_decision": "skip", "actual_skip_reason": "cutoff: 30s", "shadow_inventory": {"theoretical_decision": "HOLD"}, "lifecycle_phase": "FINAL_DERISK", "first_seen_seconds_remaining": 295, "token_ready_seconds_remaining": 280, "orderbook_ready_seconds_remaining": 25}},
        # Market 2: Late discovery, late tradable
        {"payload": {"market_id": "market_B", "epoch_start": 2000, "ticker": "ETH", "actual_decision": "skip", "actual_skip_reason": "ev_too_low", "shadow_inventory": {"theoretical_decision": "HOLD"}, "lifecycle_phase": "ACTIVE_INVENTORY_TRADING", "first_seen_seconds_remaining": 200, "token_ready_seconds_remaining": 180, "orderbook_ready_seconds_remaining": 150}},
        # Market 3: Stale feed
        {"payload": {"market_id": "market_C", "epoch_start": 3000, "ticker": "BTC", "actual_decision": "skip", "actual_skip_reason": "stale_feed", "shadow_inventory": {"theoretical_decision": "HOLD"}, "lifecycle_phase": "OPENING_SCAN", "first_seen_seconds_remaining": 290, "token_ready_seconds_remaining": 280, "orderbook_ready_seconds_remaining": 270}},
        # Market 4: Shadow opportunity despite skip
        {"payload": {"market_id": "market_D", "epoch_start": 4000, "ticker": "ETH", "actual_decision": "skip", "actual_skip_reason": "ev_too_low", "shadow_inventory": {"theoretical_decision": "WOULD_OPEN"}, "lifecycle_phase": "ACTIVE_INVENTORY_TRADING", "first_seen_seconds_remaining": 290, "token_ready_seconds_remaining": 280, "orderbook_ready_seconds_remaining": 270}},
    ]
    
    with open(log_file, "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
            
    stats = analyze_research_log(str(log_file))
    
    assert stats["total_snapshots"] == 6
    assert stats["cutoff_skips"] == 1
    assert stats["stale_feed_skips"] == 1
    assert stats["empty_book_phases"]["ACTIVE_INVENTORY_TRADING"] == 2
    assert stats["stale_feed_phases"]["OPENING_SCAN"] == 1
    assert stats["shadow_opportunities"] == 1
    
    assert stats["first_seen_s_dist"]["min"] == 200
    assert stats["first_seen_s_dist"]["max"] == 295
    assert stats["first_tradable_s_dist"]["min"] == 25
    assert stats["first_tradable_s_dist"]["max"] == 270
    
    assert len(stats["late_ready_cases"]) == 1 # market_A with orderbook_ready_seconds_remaining: 25
    assert stats["late_ready_cases"][0][0] == "market_A"
    assert stats["late_ready_cases"][0][2] == "Book ready at 25s remaining (<= 35s cutoff)"

    # Test recommendation logic based on these specific numbers (may need tuning)
    # 1 shadow opportunity out of 6 snapshots is ~16%, which should trigger SHADOW_INVENTORY_PROMISING
    assert stats["root_cause"] == "SHADOW_INVENTORY_PROMISING"
    assert stats["recommendation"] == "SHADOW_CUTOFF_EXPERIMENT"

    # Test case for DISCOVERY_LATE (p50 < 280)
    late_discovery_events = [
        {"payload": {"market_id": "M1", "epoch_start": 1, "ticker": "T1", "actual_decision": "skip", "shadow_inventory": {"theoretical_decision": "HOLD"}, "first_seen_seconds_remaining": 270}},
        {"payload": {"market_id": "M2", "epoch_start": 2, "ticker": "T2", "actual_decision": "skip", "shadow_inventory": {"theoretical_decision": "HOLD"}, "first_seen_seconds_remaining": 260}},
        {"payload": {"market_id": "M3", "epoch_start": 3, "ticker": "T3", "actual_decision": "skip", "shadow_inventory": {"theoretical_decision": "HOLD"}, "first_seen_seconds_remaining": 290}},
        {"payload": {"market_id": "M4", "epoch_start": 4, "ticker": "T4", "actual_decision": "skip", "shadow_inventory": {"theoretical_decision": "HOLD"}, "first_seen_seconds_remaining": 285}},
        {"payload": {"market_id": "M5", "epoch_start": 5, "ticker": "T5", "actual_decision": "skip", "shadow_inventory": {"theoretical_decision": "HOLD"}, "first_seen_seconds_remaining": 275}},
        {"payload": {"market_id": "M6", "epoch_start": 6, "ticker": "T6", "actual_decision": "skip", "shadow_inventory": {"theoretical_decision": "HOLD"}, "first_seen_seconds_remaining": 270}},
        {"payload": {"market_id": "M7", "epoch_start": 7, "ticker": "T7", "actual_decision": "skip", "shadow_inventory": {"theoretical_decision": "HOLD"}, "first_seen_seconds_remaining": 265}},
        {"payload": {"market_id": "M8", "epoch_start": 8, "ticker": "T8", "actual_decision": "skip", "shadow_inventory": {"theoretical_decision": "HOLD"}, "first_seen_seconds_remaining": 280}},
        {"payload": {"market_id": "M9", "epoch_start": 9, "ticker": "T9", "actual_decision": "skip", "shadow_inventory": {"theoretical_decision": "HOLD"}, "first_seen_seconds_remaining": 270}},
        {"payload": {"market_id": "M10", "epoch_start": 10, "ticker": "T10", "actual_decision": "skip", "shadow_inventory": {"theoretical_decision": "HOLD"}, "first_seen_seconds_remaining": 270}},
    ]
    with open(log_file, "w") as f:
        for e in late_discovery_events:
            f.write(json.dumps(e) + "\n")
    stats_late_discovery = analyze_research_log(str(log_file))
    assert stats_late_discovery["total_snapshots"] == 10
    assert stats_late_discovery["first_seen_s_dist"]["p50"] <= 275 # p50 of 270, 270, 270, 270, 275, 280, 285, 290
    assert stats_late_discovery["root_cause"] == "DISCOVERY_LATE"
    assert stats_late_discovery["recommendation"] == "PRELOAD_NEXT_MARKET"
