import os
import json
import pytest
import shutil
from typing import Dict, Any, List

from tools.shadow_filter_evaluator import (
    evaluate_filter,
    calculate_metrics,
    get_pnl,
    is_safe_scratch_path,
    process_file
)

# 1. Test Filter Pass/Reject Logic and Missing Fields
def test_block_btc_shadow():
    # Pass if asset != BTC
    assert evaluate_filter({"asset": "ETH"}, "block_btc_shadow")["shadow_pass"] is True
    assert evaluate_filter({"asset": "BTC"}, "block_btc_shadow")["shadow_pass"] is False
    assert evaluate_filter({"asset": "BTC"}, "block_btc_shadow")["shadow_reject_reason"] == "REJECT_BTC_ASSET"
    # Default to pass if asset missing
    assert evaluate_filter({}, "block_btc_shadow")["shadow_pass"] is True

def test_block_edge_lt_005_shadow():
    # Pass if edge >= 0.05
    assert evaluate_filter({"edge": 0.05}, "block_edge_lt_005_shadow")["shadow_pass"] is True
    assert evaluate_filter({"edge": 0.049}, "block_edge_lt_005_shadow")["shadow_pass"] is False
    assert evaluate_filter({"edge": 0.049}, "block_edge_lt_005_shadow")["shadow_reject_reason"] == "REJECT_EDGE_LT_005"
    # Default to reject if edge missing
    assert evaluate_filter({}, "block_edge_lt_005_shadow")["shadow_pass"] is False
    assert evaluate_filter({}, "block_edge_lt_005_shadow")["shadow_reject_reason"] == "MISSING_EDGE"

def test_block_normal_vol_shadow():
    # Pass if volatility_regime != NORMAL_VOL
    assert evaluate_filter({"volatility_regime": "HIGH_VOL"}, "block_normal_vol_shadow")["shadow_pass"] is True
    assert evaluate_filter({"volatility_regime": "NORMAL_VOL"}, "block_normal_vol_shadow")["shadow_pass"] is False
    assert evaluate_filter({"volatility_regime": "NORMAL_VOL"}, "block_normal_vol_shadow")["shadow_reject_reason"] == "REJECT_NORMAL_VOL"
    # Default to reject if missing
    assert evaluate_filter({}, "block_normal_vol_shadow")["shadow_pass"] is False
    assert evaluate_filter({}, "block_normal_vol_shadow")["shadow_reject_reason"] == "MISSING_VOLATILITY_REGIME"

def test_combined_conservative_shadow():
    # Pass if asset == ETH AND edge >= 0.05 AND edge < 0.15
    assert evaluate_filter({"asset": "ETH", "edge": 0.08}, "combined_conservative_shadow")["shadow_pass"] is True
    assert evaluate_filter({"asset": "BTC", "edge": 0.08}, "combined_conservative_shadow")["shadow_pass"] is False
    assert evaluate_filter({"asset": "BTC", "edge": 0.08}, "combined_conservative_shadow")["shadow_reject_reason"] == "REJECT_NOT_ETH"
    assert evaluate_filter({"asset": "ETH", "edge": 0.04}, "combined_conservative_shadow")["shadow_pass"] is False
    assert evaluate_filter({"asset": "ETH", "edge": 0.04}, "combined_conservative_shadow")["shadow_reject_reason"] == "REJECT_EDGE_OUT_OF_BOUNDS"
    assert evaluate_filter({"asset": "ETH", "edge": 0.15}, "combined_conservative_shadow")["shadow_pass"] is False
    assert evaluate_filter({"asset": "ETH", "edge": 0.15}, "combined_conservative_shadow")["shadow_reject_reason"] == "REJECT_EDGE_OUT_OF_BOUNDS"
    # Default to reject if missing
    assert evaluate_filter({}, "combined_conservative_shadow")["shadow_pass"] is False
    assert evaluate_filter({}, "combined_conservative_shadow")["shadow_reject_reason"] == "REJECT_NOT_ETH"

def test_combined_broad_shadow():
    # Pass if asset == ETH AND edge >= 0.05
    assert evaluate_filter({"asset": "ETH", "edge": 0.05}, "combined_broad_shadow")["shadow_pass"] is True
    assert evaluate_filter({"asset": "BTC", "edge": 0.05}, "combined_broad_shadow")["shadow_pass"] is False
    assert evaluate_filter({"asset": "BTC", "edge": 0.05}, "combined_broad_shadow")["shadow_reject_reason"] == "REJECT_NOT_ETH"
    assert evaluate_filter({"asset": "ETH", "edge": 0.04}, "combined_broad_shadow")["shadow_pass"] is False
    assert evaluate_filter({"asset": "ETH", "edge": 0.04}, "combined_broad_shadow")["shadow_reject_reason"] == "REJECT_EDGE_LT_005"
    # Default to reject if missing
    assert evaluate_filter({}, "combined_broad_shadow")["shadow_pass"] is False
    assert evaluate_filter({}, "combined_broad_shadow")["shadow_reject_reason"] == "REJECT_NOT_ETH"

# 2. Test Metrics and Drawdown Calculations
def test_metrics_calculation():
    # Base equity = 250.0
    passed_records = [
        {"timestamp_utc": "2026-06-21T03:01:00Z", "execution_pnl": 10.0},
        {"timestamp_utc": "2026-06-21T03:02:00Z", "pnl": -20.0},
        {"timestamp_utc": "2026-06-21T03:03:00Z", "execution_pnl_5_share_model": 30.0},
        {"timestamp_utc": "2026-06-21T03:04:00Z", "execution_pnl": -5.0}
    ]
    baseline_records = list(passed_records)
    
    metrics = calculate_metrics(passed_records, "combined_broad_shadow", baseline_records)
    
    assert metrics["candidates_evaluated"] == 4
    assert metrics["candidates_passed"] == 4
    assert metrics["candidates_rejected"] == 0
    assert metrics["pass_rate"] == 100.0
    assert metrics["wins"] == 2
    assert metrics["losses"] == 2
    assert metrics["WR"] == 0.5
    assert metrics["gross_profit"] == 40.0
    assert metrics["gross_loss"] == 25.0
    assert pytest.approx(metrics["PF"]) == 1.6
    assert metrics["net_pnl"] == 15.0
    assert metrics["avg_pnl"] == 3.75
    # Max DD checks:
    # E0 = 250.0
    # E1 = 260.0, Peak = 260.0, DD = 0
    # E2 = 240.0, Peak = 260.0, DD = 20.0, DD% = 7.6923%
    # E3 = 270.0, Peak = 270.0, DD = 0
    # E4 = 265.0, Peak = 270.0, DD = 5.0, DD% = 1.8518%
    assert metrics["max_drawdown"] == 20.0
    assert pytest.approx(metrics["max_drawdown_pct"], 0.001) == 7.6923
    assert metrics["longest_loss_streak"] == 1
    assert metrics["sample_confidence_label"] == "LOW_SAMPLE"
    assert metrics["trade_frequency_reduction"] == 0.0

def test_sample_confidence_labels():
    baseline = []
    # Test low sample (<30)
    metrics_low = calculate_metrics([{"pnl": 1.0}] * 29, "combined_broad_shadow", baseline)
    assert metrics_low["sample_confidence_label"] == "LOW_SAMPLE"
    # Test medium sample (30-100)
    metrics_med = calculate_metrics([{"pnl": 1.0}] * 30, "combined_broad_shadow", baseline)
    assert metrics_med["sample_confidence_label"] == "MEDIUM_SAMPLE"
    metrics_med_2 = calculate_metrics([{"pnl": 1.0}] * 100, "combined_broad_shadow", baseline)
    assert metrics_med_2["sample_confidence_label"] == "MEDIUM_SAMPLE"
    # Test high sample (>100)
    metrics_high = calculate_metrics([{"pnl": 1.0}] * 101, "combined_broad_shadow", baseline)
    assert metrics_high["sample_confidence_label"] == "HIGH_SAMPLE"

# 3. Test Path Safety Guard
def test_path_safety_guard():
    # Safe path check
    assert is_safe_scratch_path("scratch") is True
    assert is_safe_scratch_path("scratch/subfolder") is True
    assert is_safe_scratch_path("SCRATCH/subfolder/file.json") is True
    # Unsafe path check
    assert is_safe_scratch_path("tools") is False
    assert is_safe_scratch_path("polymarket") is False
    assert is_safe_scratch_path("config") is False
    assert is_safe_scratch_path(".") is False
    assert is_safe_scratch_path("..") is False

# 4. Test File Execution & Output (CLI Mock)
def test_process_file_execution(tmp_path):
    # Setup paths inside scratch
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_scratch_dir = os.path.join(workspace_root, "scratch", "test_shadow_eval_tmp")
    os.makedirs(test_scratch_dir, exist_ok=True)
    
    input_file = os.path.join(test_scratch_dir, "input.jsonl")
    output_dir = os.path.join(test_scratch_dir, "output")
    
    records = [
        {"timestamp_utc": "2026-06-21T03:00:00Z", "run_id": "r1", "asset": "ETH", "edge": 0.06, "volatility_regime": "HIGH_VOL", "pnl": 5.0},
        {"timestamp_utc": "2026-06-21T03:01:00Z", "run_id": "r1", "asset": "BTC", "edge": 0.08, "volatility_regime": "NORMAL_VOL", "pnl": -2.0},
        {"timestamp_utc": "2026-06-21T03:02:00Z", "run_id": "r1", "asset": "ETH", "edge": 0.04, "volatility_regime": "NORMAL_VOL", "pnl": -1.0}
    ]
    
    with open(input_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
            
    # Run the evaluator
    process_file(input_file, output_dir, "block_btc_shadow,combined_broad_shadow")
    
    # Verify outputs exist
    events_path = os.path.join(output_dir, "shadow_filter_events.jsonl")
    summary_path = os.path.join(output_dir, "shadow_filter_summary.json")
    
    assert os.path.exists(events_path) is True
    assert os.path.exists(summary_path) is True
    
    # Check summary values
    with open(summary_path, "r", encoding="utf-8") as f_sum:
        summary = json.load(f_sum)
        
    assert "block_btc_shadow" in summary
    assert "combined_broad_shadow" in summary
    
    # Clean up
    shutil.rmtree(test_scratch_dir, ignore_errors=True)

def test_process_file_unsafe_path_raises():
    with pytest.raises(ValueError, match="Output directory path is outside scratch/"):
        process_file("dummy.jsonl", "tools", "all")

def test_process_file_malformed_json_raises():
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_scratch_dir = os.path.join(workspace_root, "scratch", "test_shadow_eval_tmp")
    os.makedirs(test_scratch_dir, exist_ok=True)
    
    input_file = os.path.join(test_scratch_dir, "input.jsonl")
    with open(input_file, "w", encoding="utf-8") as f:
        f.write("invalid json line\n")
        
    with pytest.raises(ValueError, match="Unparseable JSON line 1"):
        process_file(input_file, os.path.join(test_scratch_dir, "output"), "all")
        
    shutil.rmtree(test_scratch_dir, ignore_errors=True)
