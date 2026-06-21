#!/usr/bin/env python3
"""
tests/test_phase_b_weekly_review_engine.py
Unit tests for tools/phase_b_weekly_review_engine.py
"""

import os
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import patch

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tools.phase_b_weekly_review_engine import (
    run_weekly_review_engine,
    calculate_max_drawdown,
    map_pf_to_float,
    STATUS_RANKINGS
)

@pytest.fixture
def mock_environment(tmp_path):
    """Sets up a temporary snapshot directory and index file."""
    snapshots_dir = tmp_path / "snapshots"
    snapshots_dir.mkdir()
    index_path = tmp_path / "phase_b_snapshot_index.json"
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    return {
        "snapshots_dir": snapshots_dir,
        "index_path": index_path,
        "output_dir": output_dir
    }

def test_drawdown_calculation():
    """Verify max drawdown math."""
    assert calculate_max_drawdown([]) == 0.0
    assert calculate_max_drawdown([1.0, 2.0, -1.0, 3.0]) == 1.0
    assert calculate_max_drawdown([-1.0, -2.0, -3.0]) == 6.0
    assert calculate_max_drawdown([1.0, -5.0, 2.0, -3.0]) == 6.0

def test_map_pf_to_float():
    """Verify profit factor mapping to float representation."""
    assert map_pf_to_float("INF") == 10.0
    assert map_pf_to_float("UNDERPOWERED") == 0.0
    assert map_pf_to_float("UNDEFINED") == 0.0
    assert map_pf_to_float(None) == 0.0
    assert map_pf_to_float(1.5) == 1.5
    assert map_pf_to_float("2.35") == 2.35

def write_mock_snapshot(snapshots_dir, date, filters_dict, global_metrics=None):
    """Helper to write mock phase_b_dashboard.json file."""
    date_dir = snapshots_dir / date
    date_dir.mkdir(parents=True, exist_ok=True)
    
    if global_metrics is None:
        global_metrics = {
            "active_run_id": f"run_{date}",
            "active_pid": "1234",
            "runtime_health": "HEALTHY",
            "heartbeat_age_seconds": 10.0,
            "heartbeat_fresh": True,
            "exception_count": 0,
            "telemetry_exception_count": 0,
            "total_closed_trades": 100
        }
        
    dashboard_data = {
        "report_date": date,
        "rolling_days": 7,
        "days_observed": 7,
        "overall_system_status": "NOT_READY",
        "global_metrics": global_metrics,
        "filters": filters_dict
    }
    
    with open(date_dir / "phase_b_dashboard.json", "w", encoding="utf-8") as f:
        json.dump(dashboard_data, f)

def write_mock_index(index_path, dates):
    """Helper to write mock index data."""
    index_data = {}
    for d in dates:
        index_data[d] = {
            "date": d,
            "overall_status": "NOT_READY",
            "joined_trades": 50,
            "join_coverage_pct": 99.0,
            "exception_count": 0,
            "heartbeat_age_seconds": 10.0
        }
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f)

def test_dynamic_discovery_and_rankings(mock_environment):
    """Verify that filters are dynamically discovered and ranked."""
    env = mock_environment
    dates = ["2026-06-15", "2026-06-16", "2026-06-17", "2026-06-18", "2026-06-19", "2026-06-20", "2026-06-21"]
    write_mock_index(env["index_path"], dates)
    
    filter_a_data = {
        "telemetry_rows": 100,
        "joined_trades": 40,
        "join_coverage_pct": 98.0,
        "pass_rate": 0.5,
        "block_rate": 0.5,
        "net_pnl": 0.05,
        "rejected_pnl": -0.05,
        "profit_factor": 1.5,
        "max_drawdown": 0.02,
        "baseline_max_drawdown": 0.02,
        "winrate": 0.5,
        "baseline_winrate": 0.5,
        "schema_completeness_pct": 100.0,
        "exception_count": 0,
        "governance_status": "CANDIDATE"
    }
    
    filter_b_data = {
        "telemetry_rows": 200,
        "joined_trades": 60,
        "join_coverage_pct": 99.0,
        "pass_rate": 0.3,
        "block_rate": 0.7,
        "net_pnl": 0.15,
        "rejected_pnl": -0.10,
        "profit_factor": 2.5,
        "max_drawdown": 0.01,
        "baseline_max_drawdown": 0.01,
        "winrate": 0.6,
        "baseline_winrate": 0.5,
        "schema_completeness_pct": 100.0,
        "exception_count": 0,
        "governance_status": "PROMOTION_REVIEW"
    }

    for d in dates:
        write_mock_snapshot(env["snapshots_dir"], d, {
            "custom_filter_a": filter_a_data,
            "custom_filter_b": filter_b_data
        })
    
    report = run_weekly_review_engine(
        index_path=env["index_path"],
        snapshots_dir=env["snapshots_dir"],
        output_dir=env["output_dir"],
        target_date_str="2026-06-21",
        window_days=7
    )
    
    assert "custom_filter_a" in report["filters"]
    assert "custom_filter_b" in report["filters"]
    
    summary = report["weekly_summary"]
    assert summary["top_candidate_filter"] == "custom_filter_b"
    assert summary["highest_pf_filter"] == "custom_filter_b"
    assert summary["highest_drawdown_filter"] == "custom_filter_a"
    assert summary["most_stable_filter"] in ("custom_filter_a", "custom_filter_b")

def test_raw_telemetry_isolation(mock_environment, tmp_path):
    """Verify that raw telemetry folders are ignored entirely even if populated with different filters."""
    env = mock_environment
    dates = ["2026-06-15", "2026-06-16", "2026-06-17", "2026-06-18", "2026-06-19", "2026-06-20", "2026-06-21"]
    write_mock_index(env["index_path"], dates)

    # Write snapshot filter data (custom_filter_a)
    filter_data = {
        "telemetry_rows": 100,
        "joined_trades": 40,
        "join_coverage_pct": 98.0,
        "pass_rate": 0.5,
        "block_rate": 0.5,
        "net_pnl": 0.05,
        "rejected_pnl": -0.05,
        "profit_factor": 1.5,
        "max_drawdown": 0.02,
        "baseline_max_drawdown": 0.02,
        "winrate": 0.5,
        "baseline_winrate": 0.5,
        "schema_completeness_pct": 100.0,
        "exception_count": 0,
        "governance_status": "CANDIDATE"
    }
    for d in dates:
        write_mock_snapshot(env["snapshots_dir"], d, {
            "custom_filter_a": filter_data
        })

    # Create mock raw telemetry directory populated with a different filter (raw_filter_x)
    raw_shadow_dir = tmp_path / "runtime" / "quant_data" / "signal_filter_shadow_phase_b"
    raw_shadow_dir.mkdir(parents=True)
    for d in dates:
        with open(raw_shadow_dir / f"{d}.jsonl", "w") as f:
            f.write(json.dumps({"payload": {"filter_name": "raw_filter_x"}}) + "\n")

    # Run the engine
    report = run_weekly_review_engine(
        index_path=env["index_path"],
        snapshots_dir=env["snapshots_dir"],
        output_dir=env["output_dir"],
        target_date_str="2026-06-21",
        window_days=7
    )

    # Verify that raw_filter_x is NOT discovered, confirming isolation from raw logs
    assert "raw_filter_x" not in report["filters"]
    assert "custom_filter_a" in report["filters"]
    
    # Verify metadata fields
    assert report["source_of_truth"] == "snapshot_archive"
    assert report["source_integrity"]["raw_telemetry_used"] is False

def test_missing_metrics_reporting(mock_environment):
    """Verify that missing fields in snapshots are marked as None and reported in missing_metrics."""
    env = mock_environment
    dates = ["2026-06-15", "2026-06-16", "2026-06-17", "2026-06-18", "2026-06-19", "2026-06-20", "2026-06-21"]
    write_mock_index(env["index_path"], dates)

    # Snapshot is missing 'rejected_pnl' and 'winrate'
    incomplete_filter_data = {
        "telemetry_rows": 100,
        "joined_trades": 40,
        "join_coverage_pct": 98.0,
        "pass_rate": 0.5,
        "block_rate": 0.5,
        "net_pnl": 0.05,
        "profit_factor": 1.5,
        "max_drawdown": 0.02,
        "baseline_max_drawdown": 0.02,
        "baseline_winrate": 0.5,
        "schema_completeness_pct": 100.0,
        "exception_count": 0,
        "governance_status": "CANDIDATE"
    }
    
    for d in dates:
        write_mock_snapshot(env["snapshots_dir"], d, {
            "test_filter": incomplete_filter_data
        })

    report = run_weekly_review_engine(
        index_path=env["index_path"],
        snapshots_dir=env["snapshots_dir"],
        output_dir=env["output_dir"],
        target_date_str="2026-06-21",
        window_days=7
    )

    f_metrics = report["filters"]["test_filter"]
    # Check that they are None and not backfilled
    assert f_metrics["blocked_pnl"] is None
    assert f_metrics["winrate"] is None
    assert f_metrics["delta_vs_baseline"] is None

    # Check status is NOT_READY due to missing governance metrics
    assert f_metrics["status"] == "NOT_READY"

    # Check global integrity checks
    assert "rejected_pnl" in report["source_integrity"]["missing_metrics"]
    assert "winrate" in report["source_integrity"]["missing_metrics"]

def test_status_assignment_and_rejection_routing(mock_environment):
    """Verify NOT_READY, WATCHLIST, CANDIDATE, PROMOTION_REVIEW, and REJECT routing."""
    env = mock_environment
    dates = ["2026-06-15", "2026-06-16", "2026-06-17", "2026-06-18", "2026-06-19", "2026-06-20", "2026-06-21"]
    write_mock_index(env["index_path"], dates)
    
    # 1. NOT_READY (underpowered PF)
    for d in dates:
        write_mock_snapshot(env["snapshots_dir"], d, {
            "test_filter": {
                "telemetry_rows": 10,
                "joined_trades": 5,
                "join_coverage_pct": 99.0,
                "pass_rate": 0.5,
                "block_rate": 0.5,
                "net_pnl": 0.0,
                "rejected_pnl": -0.01,
                "profit_factor": "UNDERPOWERED",
                "max_drawdown": 0.0,
                "baseline_max_drawdown": 0.0,
                "winrate": 0.5,
                "baseline_winrate": 0.5,
                "schema_completeness_pct": 100.0,
                "exception_count": 0,
                "governance_status": "NOT_READY"
            }
        })
    report = run_weekly_review_engine(
        index_path=env["index_path"],
        snapshots_dir=env["snapshots_dir"],
        output_dir=env["output_dir"],
        target_date_str="2026-06-21",
        window_days=7
    )
    assert report["filters"]["test_filter"]["status"] == "NOT_READY"
    assert report["filters"]["test_filter"]["recommendation"] == "WATCH"
    
    # 2. WATCHLIST
    for d in dates:
        write_mock_snapshot(env["snapshots_dir"], d, {
            "test_filter": {
                "telemetry_rows": 50,
                "joined_trades": 25,
                "join_coverage_pct": 96.0,
                "pass_rate": 0.5,
                "block_rate": 0.5,
                "net_pnl": 0.02, # allowed pnl
                "rejected_pnl": -0.02, # blocked pnl -> delta_vs_baseline = 0.02
                "profit_factor": 1.2,
                "max_drawdown": 0.01,
                "baseline_max_drawdown": 0.01,
                "winrate": 0.5,
                "baseline_winrate": 0.5,
                "schema_completeness_pct": 100.0,
                "exception_count": 0,
                "governance_status": "WATCHLIST"
            }
        })
    report = run_weekly_review_engine(
        index_path=env["index_path"],
        snapshots_dir=env["snapshots_dir"],
        output_dir=env["output_dir"],
        target_date_str="2026-06-21",
        window_days=7
    )
    assert report["filters"]["test_filter"]["status"] == "WATCHLIST"
    assert report["filters"]["test_filter"]["recommendation"] == "KEEP"

    # 3. REJECT (governance failure due to poor join quality)
    for d in dates:
        write_mock_snapshot(env["snapshots_dir"], d, {
            "test_filter": {
                "telemetry_rows": 50,
                "joined_trades": 25,
                "join_coverage_pct": 92.0, # < 95%
                "pass_rate": 0.5,
                "block_rate": 0.5,
                "net_pnl": 0.02,
                "rejected_pnl": -0.02,
                "profit_factor": 1.2,
                "max_drawdown": 0.01,
                "baseline_max_drawdown": 0.01,
                "winrate": 0.5,
                "baseline_winrate": 0.5,
                "schema_completeness_pct": 100.0,
                "exception_count": 0,
                "governance_status": "WATCHLIST"
            }
        })
    report = run_weekly_review_engine(
        index_path=env["index_path"],
        snapshots_dir=env["snapshots_dir"],
        output_dir=env["output_dir"],
        target_date_str="2026-06-21",
        window_days=7
    )
    assert report["filters"]["test_filter"]["recommendation"] == "REJECT"

def test_confidence_breakdown_and_score(mock_environment):
    """Verify confidence score ranges between 0-100 and sums matching breakdown."""
    env = mock_environment
    dates = ["2026-06-15", "2026-06-16", "2026-06-17", "2026-06-18", "2026-06-19", "2026-06-20", "2026-06-21"]
    write_mock_index(env["index_path"], dates)
    
    for d in dates:
        write_mock_snapshot(env["snapshots_dir"], d, {
            "test_filter": {
                "telemetry_rows": 100,
                "joined_trades": 50,
                "join_coverage_pct": 98.0,
                "pass_rate": 0.5,
                "block_rate": 0.5,
                "net_pnl": 0.05,
                "rejected_pnl": -0.05,
                "profit_factor": 2.0,
                "max_drawdown": 0.02,
                "baseline_max_drawdown": 0.02,
                "winrate": 0.5,
                "baseline_winrate": 0.5,
                "schema_completeness_pct": 100.0,
                "exception_count": 0,
                "governance_status": "CANDIDATE"
            }
        })
    
    report = run_weekly_review_engine(
        index_path=env["index_path"],
        snapshots_dir=env["snapshots_dir"],
        output_dir=env["output_dir"],
        target_date_str="2026-06-21",
        window_days=7
    )
    
    f_metrics = report["filters"]["test_filter"]
    assert 0 <= f_metrics["confidence_score"] <= 100
    
    breakdown = f_metrics["confidence_breakdown"]
    total_breakdown = sum(breakdown.values())
    assert f_metrics["confidence_score"] == total_breakdown
    assert "sample_size" in breakdown
    assert "join_quality" in breakdown
    assert "pf_stability" in breakdown
    assert "drawdown_stability" in breakdown
    assert "runtime_days" in breakdown

def test_promotion_freeze_logic(mock_environment):
    """Verify promotion_allowed becomes False when runtime_days < 14."""
    env = mock_environment
    dates = ["2026-06-20", "2026-06-21"]
    write_mock_index(env["index_path"], dates)
    
    for d in dates:
        write_mock_snapshot(env["snapshots_dir"], d, {
            "block_btc_shadow": {
                "telemetry_rows": 100,
                "joined_trades": 60,
                "join_coverage_pct": 99.0,
                "pass_rate": 0.3,
                "block_rate": 0.7,
                "net_pnl": 0.10,
                "rejected_pnl": -0.05,
                "profit_factor": 1.5,
                "max_drawdown": 0.01,
                "baseline_max_drawdown": 0.01,
                "winrate": 0.5,
                "baseline_winrate": 0.5,
                "schema_completeness_pct": 100.0,
                "exception_count": 0,
                "governance_status": "PROMOTION_REVIEW"
            }
        })
    
    report = run_weekly_review_engine(
        index_path=env["index_path"],
        snapshots_dir=env["snapshots_dir"],
        output_dir=env["output_dir"],
        target_date_str="2026-06-21",
        window_days=7
    )
    
    f_metrics = report["filters"]["block_btc_shadow"]
    assert f_metrics["promotion_allowed"] is False
    assert f_metrics["promotion_block_reason"] == "Minimum 14-day evidence window not met."

def test_empty_and_malformed_snapshots(mock_environment):
    """Verify empty or malformed snapshots are handled gracefully without crashing and reported in integrity."""
    env = mock_environment
    dates = ["2026-06-20", "2026-06-21"]
    write_mock_index(env["index_path"], dates)
    
    # 2026-06-20 is empty
    date_dir = env["snapshots_dir"] / "2026-06-20"
    date_dir.mkdir(parents=True, exist_ok=True)
    with open(date_dir / "phase_b_dashboard.json", "w") as f:
        f.write("")
        
    # 2026-06-21 is malformed JSON
    date_dir = env["snapshots_dir"] / "2026-06-21"
    date_dir.mkdir(parents=True, exist_ok=True)
    with open(date_dir / "phase_b_dashboard.json", "w") as f:
        f.write("{invalid json: ")
        
    report = run_weekly_review_engine(
        index_path=env["index_path"],
        snapshots_dir=env["snapshots_dir"],
        output_dir=env["output_dir"],
        target_date_str="2026-06-21",
        window_days=2
    )
    
    assert report["filters"] == {}
    assert report["valid_snapshots_loaded"] == 0
    assert report["source_integrity"]["malformed_snapshots"] == 2
