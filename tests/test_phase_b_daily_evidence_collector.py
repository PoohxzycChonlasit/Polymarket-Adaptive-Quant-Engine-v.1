from __future__ import annotations

import argparse
import json
import pytest
from pathlib import Path

from tools.phase_b_daily_evidence_collector import (
    check_schema_complete,
    calculate_max_drawdown,
    calculate_profit_factor,
    calculate_winrate,
    get_governance_status,
    compile_metrics,
    run_evidence_collector,
)


def test_scratch_output_guard():
    """Verify that output_dir must resolve under scratch/ or fail closed."""
    # Test path outside scratch
    args = argparse.Namespace(
        shadow_root="runtime/quant_data/signal_filter_shadow_phase_b",
        trade_journal_root="runtime/quant_data/trade_journal",
        system_health_root="runtime/quant_data/system_health",
        output_dir="tools/phase_b_daily_evidence/output",  # outside scratch/
        date="2026-06-21",
        rolling_days=7,
    )
    with pytest.raises(SystemExit) as exc_info:
        run_evidence_collector(args)
    assert exc_info.value.code == 1


def test_schema_completeness_detection():
    """Verify check_schema_complete flags missing required fields."""
    complete_payload = {
        "filter_name": "block_btc_shadow",
        "filter_version": "1.0.0",
        "filter_params": {},
        "shadow_pass": True,
        "shadow_reason": "none",
        "would_trade": True,
        "run_id": "run-1",
        "signal_id": "sig-1",
        "candidate_instance_id": "cand-1",
        "paper_trade_replay_key": "replay-1",
        "asset": "BTC",
        "side": "YES",
        "edge": 0.06,
        "ev": 0.05,
        "probability": 0.55,
        "entry_price": 0.50,
        "proposed_size_usd": 10.0,
    }
    assert check_schema_complete(complete_payload) is True

    incomplete_payload = complete_payload.copy()
    del incomplete_payload["filter_name"]
    assert check_schema_complete(incomplete_payload) is False


def test_primary_join():
    """Verify compile_metrics matches trades using run_id + candidate_instance_id."""
    shadow_events = [
        {
            "payload": {
                "filter_name": "block_btc_shadow",
                "filter_version": "1.0.0",
                "filter_params": {},
                "shadow_pass": False,
                "shadow_reason": "btc_price_drop",
                "would_trade": False,
                "run_id": "run-1",
                "signal_id": "sig-1",
                "candidate_instance_id": "cand-1",
                "paper_trade_replay_key": "replay-1",
                "asset": "BTC",
                "side": "YES",
                "edge": 0.06,
                "ev": 0.05,
                "probability": 0.55,
                "entry_price": 0.50,
                "proposed_size_usd": 10.0,
            }
        }
    ]
    # Trade closes matching primary keys (run_id + candidate_instance_id)
    closed_trades = [
        {
            "event_type": "trade_close",
            "run_id": "run-1",
            "payload": {
                "candidate_instance_id": "cand-1",
                "pnl": -5.0,
                "paper_trade_replay_key": "mismatched-replay-key",
            },
        }
    ]

    metrics = compile_metrics(
        filter_name="block_btc_shadow",
        shadow_events=shadow_events,
        closed_trades=closed_trades,
        total_closed_count=len(closed_trades),
        days_observed=1,
    )

    assert metrics["closed_candidates_seen"] == 1
    assert metrics["candidates_rejected"] == 1
    assert metrics["rejected_pnl"] == -5.0
    assert metrics["realized_pnl"] == 0.0


def test_fallback_join():
    """Verify compile_metrics falls back to paper_trade_replay_key when primary is missing or mismatched."""
    shadow_events = [
        {
            "payload": {
                "filter_name": "block_btc_shadow",
                "filter_version": "1.0.0",
                "filter_params": {},
                "shadow_pass": True,
                "shadow_reason": None,
                "would_trade": True,
                "run_id": "run-1",
                "signal_id": "sig-1",
                "candidate_instance_id": "cand-1",
                "paper_trade_replay_key": "replay-1",
                "asset": "BTC",
                "side": "YES",
                "edge": 0.06,
                "ev": 0.05,
                "probability": 0.55,
                "entry_price": 0.50,
                "proposed_size_usd": 10.0,
            }
        }
    ]
    # Trade closes with mismatched run_id/candidate_instance_id, but matching replay_key
    closed_trades = [
        {
            "event_type": "trade_close",
            "run_id": "run-mismatched",
            "payload": {
                "candidate_instance_id": "cand-mismatched",
                "pnl": 10.0,
                "paper_trade_replay_key": "replay-1",
            },
        }
    ]

    metrics = compile_metrics(
        filter_name="block_btc_shadow",
        shadow_events=shadow_events,
        closed_trades=closed_trades,
        total_closed_count=len(closed_trades),
        days_observed=1,
    )

    assert metrics["closed_candidates_seen"] == 1
    assert metrics["candidates_passed"] == 1
    assert metrics["realized_pnl"] == 10.0
    assert metrics["rejected_pnl"] == 0.0


def test_missing_join_accounting():
    """Verify trades that fail to join are tracked and reduce join coverage."""
    shadow_events = [
        {
            "payload": {
                "filter_name": "block_btc_shadow",
                "filter_version": "1.0.0",
                "filter_params": {},
                "shadow_pass": True,
                "shadow_reason": None,
                "would_trade": True,
                "run_id": "run-1",
                "signal_id": "sig-1",
                "candidate_instance_id": "cand-1",
                "paper_trade_replay_key": "replay-1",
                "asset": "BTC",
                "side": "YES",
                "edge": 0.06,
                "ev": 0.05,
                "probability": 0.55,
                "entry_price": 0.50,
                "proposed_size_usd": 10.0,
            }
        }
    ]
    closed_trades = [
        # Matchable trade
        {
            "event_type": "trade_close",
            "run_id": "run-1",
            "payload": {
                "candidate_instance_id": "cand-1",
                "pnl": 10.0,
                "paper_trade_replay_key": "replay-1",
            },
        },
        # Unmatchable trade
        {
            "event_type": "trade_close",
            "run_id": "run-2",
            "payload": {
                "candidate_instance_id": "cand-2",
                "pnl": 5.0,
                "paper_trade_replay_key": "replay-2",
            },
        },
    ]

    metrics = compile_metrics(
        filter_name="block_btc_shadow",
        shadow_events=shadow_events,
        closed_trades=closed_trades,
        total_closed_count=len(closed_trades),
        days_observed=1,
    )

    # 1 out of 2 joined
    assert metrics["closed_candidates_seen"] == 1
    assert metrics["join_coverage_pct"] == 50.0


def test_profit_factor_calculation():
    """Verify calculate_profit_factor logic for underpowered, INF, undefined, and normal values."""
    # 1. Underpowered: less than 10 passed trades
    underpowered_trades = [{"pnl": 10.0}] * 9
    assert calculate_profit_factor(underpowered_trades) == "UNDERPOWERED"

    # 2. INF: gross profit > 0 and gross loss == 0 (with at least 10 trades)
    inf_trades = [{"pnl": 10.0}] * 10
    assert calculate_profit_factor(inf_trades) == "INF"

    # 3. UNDEFINED: gross profit == 0 and gross loss == 0 (with at least 10 trades)
    undefined_trades = [{"pnl": 0.0}] * 10
    assert calculate_profit_factor(undefined_trades) == "UNDEFINED"

    # 4. Normal calculation: profit / loss
    normal_trades = [{"pnl": 10.0}] * 8 + [{"pnl": -5.0}] * 2
    # 80 profit / 10 loss = 8.0
    assert calculate_profit_factor(normal_trades) == 8.0


def test_max_drawdown_calculation():
    """Verify peak-to-trough drawdown logic."""
    assert calculate_max_drawdown([]) == 0.0
    # Peak starts at 0. Cum PnL: [0.0, 10.0, 5.0, 25.0, 10.0, 40.0]
    # Drawdowns at each point:
    # 0.0: 0
    # 10.0: peak=10.0, dd=0
    # 5.0: peak=10.0, dd=5.0
    # 25.0: peak=25.0, dd=0
    # 10.0: peak=25.0, dd=15.0
    # 40.0: peak=40.0, dd=0
    # Max DD = 15.0
    assert calculate_max_drawdown([10.0, -5.0, 20.0, -15.0, 30.0]) == 15.0

    # Negative from the start. Cum PnL: [0.0, -5.0, -15.0]
    # Peak=0. Max DD = 15.0
    assert calculate_max_drawdown([-5.0, -10.0]) == 15.0


def test_not_ready_status():
    """Verify NOT_READY triggers under all governance failure conditions."""
    base_metrics = {
        "filter_name": "block_btc_shadow",
        "closed_candidates_seen": 20,
        "join_coverage_pct": 98.0,
        "schema_complete_rows": 1,
        "schema_incomplete_rows": 0,
        "exception_count": 0,
        "delta_vs_baseline": 1.0,
        "profit_factor": 1.5,
        "max_drawdown": 5.0,
        "baseline_max_drawdown": 10.0,
        "winrate": 0.6,
        "rejected_pnl": -2.0,
    }

    # Under 3 days
    assert get_governance_status(base_metrics, days_observed=2) == "NOT_READY"

    # Under 20 closed joined trades
    under_closed = base_metrics.copy()
    under_closed["closed_candidates_seen"] = 19
    assert get_governance_status(under_closed, days_observed=3) == "NOT_READY"

    # Under 95% join coverage
    low_join = base_metrics.copy()
    low_join["join_coverage_pct"] = 94.9
    assert get_governance_status(low_join, days_observed=3) == "NOT_READY"

    # Incomplete schema
    incomplete = base_metrics.copy()
    incomplete["schema_incomplete_rows"] = 1
    assert get_governance_status(incomplete, days_observed=3) == "NOT_READY"

    # Exception count > 0
    with_exc = base_metrics.copy()
    with_exc["exception_count"] = 1
    assert get_governance_status(with_exc, days_observed=3) == "NOT_READY"

    # Profit factor underpowered or undefined
    for pf in ["UNDERPOWERED", "UNDEFINED"]:
        bad_pf = base_metrics.copy()
        bad_pf["profit_factor"] = pf
        assert get_governance_status(bad_pf, days_observed=3) == "NOT_READY"


def test_watchlist_status():
    """Verify WATCHLIST status requirements are correctly evaluated."""
    base_metrics = {
        "filter_name": "block_btc_shadow",
        "closed_candidates_seen": 20,
        "join_coverage_pct": 95.0,
        "schema_complete_rows": 20,
        "schema_incomplete_rows": 0,
        "exception_count": 0,
        "delta_vs_baseline": 0.01,
        "profit_factor": 1.00,
        "max_drawdown": 11.0,
        "baseline_max_drawdown": 10.0,  # 11.0 <= 10.0 * 1.10
        "winrate": 0.5,
        "rejected_pnl": -0.01,
    }

    # Watchlist conditions met
    assert get_governance_status(base_metrics, days_observed=3) == "WATCHLIST"

    # Drawdown too high (11.1 > 10.0 * 1.10)
    high_dd = base_metrics.copy()
    high_dd["max_drawdown"] = 11.1
    assert get_governance_status(high_dd, days_observed=3) == "NOT_READY"

    # Delta <= 0
    zero_delta = base_metrics.copy()
    zero_delta["delta_vs_baseline"] = 0.00
    assert get_governance_status(zero_delta, days_observed=3) == "NOT_READY"

    # PF < 1.00
    low_pf = base_metrics.copy()
    low_pf["profit_factor"] = 0.99
    assert get_governance_status(low_pf, days_observed=3) == "NOT_READY"


def test_worst_case_status_logic():
    """Verify worst-case governance status determination."""
    from tools.phase_b_daily_report import determine_worst_case_status
    assert determine_worst_case_status(["WATCHLIST", "CANDIDATE", "PROMOTION_REVIEW"]) == "WATCHLIST"
    assert determine_worst_case_status(["PROMOTION_REVIEW", "PROMOTION_REVIEW"]) == "PROMOTION_REVIEW"
    assert determine_worst_case_status(["NOT_READY", "PROMOTION_REVIEW"]) == "NOT_READY"
    assert determine_worst_case_status([]) == "NOT_READY"


def test_snapshot_archiver_and_summary(tmp_path, monkeypatch):
    """Test the archiver and summary helper tools using temporary directories."""
    # Setup source directory
    source_dir = tmp_path / "scratch" / "phase_b_daily_reports"
    source_dir.mkdir(parents=True)

    dashboard_content = {
        "report_date": "2026-06-21",
        "overall_system_status": "WATCHLIST",
        "global_metrics": {
            "exception_count": 0,
            "telemetry_exception_count": 0,
            "heartbeat_age_seconds": 12.5,
            "heartbeat_fresh": True,
            "total_closed_trades": 50
        },
        "filters": {
            "block_btc_shadow": {
                "joined_trades": 10,
                "join_coverage_pct": 98.0
            },
            "block_normal_vol_shadow": {
                "joined_trades": 15,
                "join_coverage_pct": 96.0
            }
        }
    }

    with open(source_dir / "phase_b_dashboard.json", "w", encoding="utf-8") as f:
        json.dump(dashboard_content, f)

    with open(source_dir / "phase_b_dashboard.md", "w", encoding="utf-8") as f:
        f.write("# Mock Dashboard")

    # Change working directory to tmp_path
    monkeypatch.chdir(tmp_path)

    # Import and run archiver
    from tools.phase_b_snapshot_archiver import run_snapshot_archiver
    run_snapshot_archiver()

    # Verify snapshot files were created
    dest_dir = tmp_path / "runtime" / "quant_data" / "reports" / "phase_b_daily_snapshots" / "2026-06-21"
    assert (dest_dir / "phase_b_dashboard.json").exists()
    assert (dest_dir / "phase_b_dashboard.md").exists()

    # Verify index was created
    index_path = tmp_path / "runtime" / "quant_data" / "reports" / "phase_b_daily_snapshots" / "phase_b_snapshot_index.json"
    assert index_path.exists()

    with open(index_path, "r", encoding="utf-8") as f:
        index_data = json.load(f)
    assert "2026-06-21" in index_data
    assert index_data["2026-06-21"]["overall_status"] == "WATCHLIST"
    assert index_data["2026-06-21"]["joined_trades"] == 25
    assert index_data["2026-06-21"]["join_coverage_pct"] == 97.0

    # Test summary generator
    from tools.phase_b_snapshot_summary import generate_7day_summary
    generate_7day_summary()

    summary_md_path = tmp_path / "scratch" / "phase_b_7day_snapshot_summary.md"
    assert summary_md_path.exists()
