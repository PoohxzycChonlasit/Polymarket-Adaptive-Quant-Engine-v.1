from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tools.replay_analyzer import analyze_replay, main as replay_main


DATE = "2026-05-08"
NEXT_DATE = "2026-05-09"


def _event(event_type: str, timestamp: str, payload: dict) -> dict:
    return {
        "timestamp_utc": timestamp,
        "event_type": event_type,
        "mode": "paper",
        "run_id": "run-test",
        "source_module": "test",
        "schema_version": "1.0",
        "payload": payload,
    }


def _append_jsonl(base_dir: Path, category: str, date: str, events: list[dict | str]) -> None:
    path = base_dir / category / f"{date}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for event in events:
            if isinstance(event, str):
                handle.write(event + "\n")
            else:
                handle.write(json.dumps(event) + "\n")


def _write_sample_replay(base_dir: Path) -> None:
    _append_jsonl(base_dir, "decision_log", DATE, [
        _event("decision", f"{DATE}T00:00:00Z", {
            "decision_type": "approved",
            "ticker": "BTC",
            "decision": "buy",
            "confidence": 0.70,
            "seconds_remaining": 210,
            "orderbook_age_ms": 120,
            "oracle_age_ms": 900,
            "decision_latency_ms": 75,
            "cutoff_policy": "adaptive",
            "adaptive_cutoff_allowed": True,
            "adaptive_cutoff_reason": "healthy_late_entry",
        }),
        _event("decision", f"{DATE}T00:01:00Z", {
            "decision_type": "skipped",
            "skipped": True,
            "ticker": "ETH",
            "skip_reason": "confidence_too_low",
            "seconds_remaining": 95,
            "orderbook_age_ms": 180,
            "oracle_age_ms": 1100,
            "decision_latency_ms": 125,
        }),
        _event("decision", f"{DATE}T00:02:00Z", {
            "decision_type": "risk_rejected",
            "skipped": True,
            "ticker": "BTC",
            "skip_reason": "risk_mode_lockdown",
            "seconds_remaining": 80,
            "orderbook_age": 0.2,
            "oracle_age": 1.4,
            "decision_latency_ms": 150,
            "cutoff_block_seconds_remaining": 80,
            "cutoff_policy": "adaptive",
            "adaptive_cutoff_allowed": False,
            "adaptive_cutoff_denied_reason": "hard_close_zone",
            "late_entry_hard_block": True,
        }),
    ])
    _append_jsonl(base_dir, "market_snapshots", DATE, [
        _event("market_snapshot", f"{DATE}T00:02:30Z", {
            "ticker": "BTC",
            "seconds_remaining": 70,
            "orderbook_age_ms": 300,
            "oracle_age_ms": 1500,
        }),
    ])
    _append_jsonl(base_dir, "execution_log", DATE, [
        _event("execution", f"{DATE}T00:03:00Z", {"event": "order_submit_failed", "status": "failed"}),
    ])
    _append_jsonl(base_dir, "system_health", DATE, [
        _event("system_health", f"{DATE}T00:03:30Z", {"scan_cycle_duration_ms": 640}),
        _event("system_health", f"{DATE}T00:04:30Z", {"scan_cycle_duration_ms": 820}),
    ])
    _append_jsonl(base_dir, "trade_journal", DATE, [
        _event("trade_open", f"{DATE}T00:04:00Z", {
            "position_id": "p1",
            "market_id": "pm-5m-btc",
            "ticker": "BTC",
            "outcome": "YES",
            "side": "BUY",
            "entry_price": 0.50,
            "size": 10,
            "spread": 0.02,
            "confidence": 0.70,
        }),
        _event("trade_close", f"{DATE}T00:09:00Z", {
            "position_id": "p1",
            "market_id": "pm-5m-btc",
            "ticker": "BTC",
            "outcome": "YES",
            "side": "YES",
            "pnl": 1.5,
        }),
        _event("trade_open", f"{DATE}T00:10:00Z", {
            "position_id": "p2",
            "market_id": "pm-5m-eth",
            "ticker": "ETH",
            "outcome": "NO",
            "side": "BUY",
            "spread": 0.04,
            "confidence": 0.60,
        }),
        _event("trade_close", f"{DATE}T00:12:00Z", {
            "position_id": "p2",
            "market_id": "pm-5m-eth",
            "ticker": "ETH",
            "outcome": "NO",
            "side": "NO",
            "pnl": -0.5,
        }),
    ])


def test_replay_metrics_are_correct(tmp_path: Path) -> None:
    base_dir = tmp_path / "runtime" / "quant_data"
    _write_sample_replay(base_dir)

    report = analyze_replay(base_dir=base_dir, date=DATE)

    assert report.total_trades == 2
    assert report.wins == 1
    assert report.losses == 1
    assert report.win_rate == pytest.approx(0.5)
    assert report.gross_pnl == pytest.approx(1.0)
    assert report.average_pnl == pytest.approx(0.5)
    assert report.max_win == pytest.approx(1.5)
    assert report.max_loss == pytest.approx(-0.5)
    assert report.average_holding_time_seconds == pytest.approx(210.0)
    assert report.skipped_decisions == 2
    assert report.top_skip_reasons == [("confidence_too_low", 1), ("risk_mode_lockdown", 1)]
    assert report.approved_decisions == 1
    assert report.rejected_decisions == 2
    assert report.approved_vs_rejected_ratio == pytest.approx(0.5)
    assert report.risk_reject_count == 1
    assert report.execution_failure_count == 1
    assert report.average_spread_at_entry == pytest.approx(0.03)
    assert report.average_confidence_at_entry == pytest.approx(0.65)
    assert report.average_seconds_remaining == pytest.approx((210 + 95 + 80 + 70) / 4)
    assert report.min_seconds_remaining == pytest.approx(70)
    assert report.average_orderbook_age_ms == pytest.approx((120 + 180 + 200 + 300) / 4)
    assert report.max_orderbook_age_ms == pytest.approx(300)
    assert report.average_oracle_age_ms == pytest.approx((900 + 1100 + 1400 + 1500) / 4)
    assert report.max_oracle_age_ms == pytest.approx(1500)
    assert report.average_scan_cycle_duration_ms == pytest.approx((640 + 820) / 2)
    assert report.max_scan_cycle_duration_ms == pytest.approx(820)
    assert report.average_decision_latency_ms == pytest.approx((75 + 125 + 150) / 3)
    assert report.max_decision_latency_ms == pytest.approx(150)
    assert report.cutoff_block_count == 1
    assert report.average_cutoff_block_seconds_remaining == pytest.approx(80)
    assert report.adaptive_cutoff_allowed_count == 1
    assert report.adaptive_cutoff_denied_count == 1
    assert report.late_entry_hard_block_count == 1
    assert ("healthy_late_entry", 1) in report.adaptive_cutoff_reasons
    assert ("hard_close_zone", 1) in report.adaptive_cutoff_reasons
    assert ("hard_close_zone", 1) in report.adaptive_cutoff_denied_reasons
    assert report.pnl_by_outcome == {"NO": -0.5, "YES": 1.5}
    assert report.pnl_by_asset == {"BTC": 1.5, "ETH": -0.5}


def test_replay_empty_dataset_produces_safe_zero_report(tmp_path: Path) -> None:
    report = analyze_replay(base_dir=tmp_path / "missing", date=DATE)

    assert report.events_loaded == 0
    assert report.total_trades == 0
    assert report.win_rate == 0.0
    assert report.gross_pnl == 0.0
    assert report.top_skip_reasons == []


def test_replay_filters_events_by_utc_time_window(tmp_path: Path) -> None:
    base_dir = tmp_path / "runtime" / "quant_data"
    _append_jsonl(base_dir, "decision_log", DATE, [
        _event("decision", f"{DATE}T17:42:59Z", {
            "decision_type": "skipped",
            "skipped": True,
            "skip_reason": "legacy_before_window",
        }),
        _event("decision", f"{DATE}T17:44:08Z", {
            "decision_type": "skipped",
            "skipped": True,
            "skip_reason": "fresh_window",
            "fair_value": None,
            "fair_value_available": False,
            "fair_value_null_reason": "no_orderbook",
        }),
        _event("decision", f"{DATE}T17:47:00Z", {
            "decision_type": "skipped",
            "skipped": True,
            "skip_reason": "legacy_after_window",
        }),
    ])

    report = analyze_replay(
        base_dir=base_dir,
        date=DATE,
        since_utc=datetime(2026, 5, 8, 17, 43, tzinfo=timezone.utc),
        until_utc=datetime(2026, 5, 8, 17, 47, tzinfo=timezone.utc),
    )

    assert report.events_loaded == 1
    assert report.skipped_decisions == 1
    assert report.top_skip_reasons == [("fresh_window", 1)]
    assert report.time_filter["applied"] is True
    assert report.phase2_coverage["ev_null_reason_coverage"]["fields"]["fair_value"]["null_reason_events"] == 1


def test_replay_filters_events_by_run_id_and_writes_run_scoped_report(tmp_path: Path) -> None:
    base_dir = tmp_path / "runtime" / "quant_data"
    report_dir = tmp_path / "runtime" / "reports"
    _append_jsonl(base_dir, "decision_log", DATE, [
        {
            **_event("decision", f"{DATE}T00:00:00Z", {
                "decision_type": "skipped",
                "skipped": True,
                "skip_reason": "target_run",
            }),
            "run_id": "run/target",
        },
        {
            **_event("decision", f"{DATE}T00:00:01Z", {
                "decision_type": "skipped",
                "skipped": True,
                "skip_reason": "other_run",
            }),
            "run_id": "run-other",
        },
        _event("decision", f"{DATE}T00:00:02Z", {
            "decision_type": "skipped",
            "skipped": True,
            "skip_reason": "missing_run_id",
        }),
    ])

    report = analyze_replay(
        base_dir=base_dir,
        date=DATE,
        report_dir=report_dir,
        write_reports=True,
        write_csv=True,
        run_id="run/target",
    )

    assert report.run_id == "run/target"
    assert report.events_loaded == 1
    assert report.top_skip_reasons == [("target_run", 1)]
    assert report.time_filter["run_id"] == "run/target"
    assert report.time_filter["run_id_applied"] is True
    assert (report_dir / f"replay_report_{DATE}_run_run_target.json").exists()
    assert (report_dir / f"replay_trades_{DATE}_run_run_target.csv").exists()


def test_replay_cli_lists_run_ids(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    base_dir = tmp_path / "runtime" / "quant_data"
    _append_jsonl(base_dir, "decision_log", DATE, [
        {
            **_event("decision", f"{DATE}T00:00:00Z", {"decision_type": "skipped"}),
            "run_id": "run-a",
        },
        {
            **_event("decision", f"{DATE}T00:01:00Z", {"decision_type": "skipped"}),
            "run_id": "run-a",
        },
        {
            **_event("decision", f"{DATE}T00:02:00Z", {"decision_type": "skipped"}),
            "run_id": "run-b",
            "mode": "paper",
        },
        {
            key: value
            for key, value in _event("decision", f"{DATE}T00:03:00Z", {"decision_type": "skipped"}).items()
            if key != "run_id"
        },
    ])
    monkeypatch.setattr("sys.argv", [
        "replay_analyzer",
        "--date",
        DATE,
        "--base-dir",
        str(base_dir),
        "--list-run-ids",
    ])

    assert replay_main() == 0

    output = capsys.readouterr().out
    assert "Available run IDs" in output
    assert "run_id=run-a event_count=2" in output
    assert "run_id=run-b event_count=1" in output
    assert "run_id=missing_run_id missing_run_id=true event_count=1" in output
    assert "categories=decision_log" in output
    assert "mode=paper" in output


def test_replay_does_not_count_rejected_decisions_or_order_intent_rejects_as_execution_failures(tmp_path: Path) -> None:
    base_dir = tmp_path / "runtime" / "quant_data"
    _append_jsonl(base_dir, "decision_log", DATE, [
        _event("decision", f"{DATE}T00:00:00Z", {
            "decision_type": "rejected",
            "skipped": True,
            "decision": "skip",
            "skip_reason": "order_intent:not_approved",
        }),
    ])
    _append_jsonl(base_dir, "execution_log", DATE, [
        _event("execution", f"{DATE}T00:00:01Z", {"event": "order_intent_reject", "reason": "risk_not_approved"}),
    ])

    report = analyze_replay(base_dir=base_dir, date=DATE)

    assert report.rejected_decisions == 1
    assert report.skipped_decisions == 1
    assert report.execution_failure_count == 0


def test_replay_still_counts_real_execution_errors(tmp_path: Path) -> None:
    base_dir = tmp_path / "runtime" / "quant_data"
    _append_jsonl(base_dir, "execution_log", DATE, [
        _event("execution", f"{DATE}T00:00:00Z", {"event": "order_submit_failed"}),
        _event("execution", f"{DATE}T00:00:01Z", {"event": "cancel_order", "status": "failed"}),
        _event("execution", f"{DATE}T00:00:02Z", {"event": "market_analysis_exception"}),
    ])

    report = analyze_replay(base_dir=base_dir, date=DATE)

    assert report.execution_failure_count == 3


def test_replay_reports_orderbook_readiness_reason_breakdown(tmp_path: Path) -> None:
    base_dir = tmp_path / "runtime" / "quant_data"
    _append_jsonl(base_dir, "decision_log", DATE, [
        _event("decision", f"{DATE}T00:00:00Z", {
            "decision_type": "skipped",
            "skipped": True,
            "skip_reason": "warmup_pending",
            "orderbook_unavailable_reason": "warmup_pending",
        }),
        _event("decision", f"{DATE}T00:00:01Z", {
            "decision_type": "skipped",
            "skipped": True,
            "skip_reason": "missing_token_id",
            "orderbook_unavailable_reason": "missing_token_id",
        }),
        _event("decision", f"{DATE}T00:00:02Z", {
            "decision_type": "skipped",
            "skipped": True,
            "skip_reason": "stale_book",
            "orderbook_readiness_reason": "stale_book",
        }),
        _event("decision", f"{DATE}T00:00:03Z", {
            "decision_type": "skipped",
            "skipped": True,
            "skip_reason": "clob_timeout",
            "clob_error_category": "clob_timeout",
            "clob_error_class": "transient_api_issue",
            "clob_exception_type": "TimeoutError",
            "clob_backoff_active": True,
            "clob_circuit_open": True,
            "clob_error_rate": 1.0,
            "clob_recovery_count": 2,
        }),
    ])

    report = analyze_replay(base_dir=base_dir, date=DATE)

    assert ("warmup_pending", 1) in report.orderbook_readiness_reasons
    assert ("missing_token_id", 1) in report.orderbook_readiness_reasons
    assert ("stale_book", 1) in report.orderbook_readiness_reasons
    assert ("clob_timeout", 1) in report.orderbook_readiness_reasons
    assert ("clob_timeout", 1) in report.clob_error_categories
    assert ("TimeoutError", 1) in report.clob_exception_types
    assert ("transient_api_issue", 1) in report.clob_error_classes
    assert report.clob_backoff_active_count == 1
    assert report.clob_circuit_open_count == 1
    assert report.max_clob_error_rate == pytest.approx(1.0)
    assert report.clob_recovery_count == 2


def test_replay_reports_early_window_alignment_diagnostics(tmp_path: Path) -> None:
    base_dir = tmp_path / "quant_data"
    _append_jsonl(base_dir, "decision_log", DATE, [
        _event("decision", f"{DATE}T00:00:00Z", {
            "decision_type": "skipped",
            "skipped": True,
            "skip_reason": "time_unsafe",
            "seconds_remaining": 44,
            "seconds_since_open": 256,
            "seconds_until_close": 44,
            "first_seen_seconds_remaining": 288,
            "first_evaluable_seconds_remaining": 240,
            "active_window_alignment_reason": "late_hard_close_zone",
        }),
    ])
    _append_jsonl(base_dir, "market_snapshots", DATE, [
        _event("market_snapshot", f"{DATE}T00:00:01Z", {
            "ticker": "BTC",
            "seconds_remaining": 240,
            "seconds_since_open": 60,
            "seconds_until_close": 240,
            "first_seen_seconds_remaining": 288,
            "first_evaluable_seconds_remaining": 240,
            "active_window_alignment_reason": "early_window_ready",
        }),
    ])

    report = analyze_replay(base_dir=base_dir, date=DATE)

    assert report.first_seen_seconds_remaining == pytest.approx(288)
    assert report.first_evaluable_seconds_remaining == pytest.approx(240)
    assert report.average_seconds_since_open == pytest.approx((256 + 60) / 2)
    assert report.average_seconds_until_close == pytest.approx((44 + 240) / 2)
    assert ("early_window_ready", 1) in report.active_window_alignment_reasons
    assert ("late_hard_close_zone", 1) in report.active_window_alignment_reasons


def test_replay_reports_empty_book_recovery_metrics(tmp_path: Path) -> None:
    base_dir = tmp_path / "quant_data"
    _append_jsonl(base_dir, "market_snapshots", DATE, [
        _event("market_snapshot", f"{DATE}T00:00:00Z", {
            "ticker": "BTC",
            "orderbook_readiness_reason": "",
            "empty_book_recovery_attempted": True,
            "empty_book_recovery_success": True,
            "empty_book_recovery_failed": False,
            "empty_book_recovery_retry_count": 1,
            "liquidity_state": "HEALTHY",
        }),
        _event("market_snapshot", f"{DATE}T00:01:00Z", {
            "ticker": "ETH",
            "orderbook_readiness_reason": "empty_book",
            "empty_book_recovery_attempted": True,
            "empty_book_recovery_success": False,
            "empty_book_recovery_failed": True,
            "empty_book_recovery_retry_count": 2,
            "liquidity_state": "EMPTY",
        }),
    ])

    report = analyze_replay(base_dir=base_dir, date=DATE)

    assert report.empty_book_recovery_attempted_count == 2
    assert report.empty_book_recovery_success_count == 1
    assert report.empty_book_recovery_failed_count == 1
    assert report.empty_book_recovery_retry_count == 3
    assert ("HEALTHY", 1) in report.liquidity_states
    assert ("EMPTY", 1) in report.liquidity_states


def test_replay_reports_phase2_inventory_coverage_from_synthetic_jsonl(tmp_path: Path) -> None:
    base_dir = tmp_path / "quant_data"
    _append_jsonl(base_dir, "decision_log", DATE, [
        _event("decision", f"{DATE}T00:00:00Z", {
            "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
            "token_ready_at": f"{DATE}T00:00:00Z",
            "orderbook_ready_at": f"{DATE}T00:00:01Z",
            "liquidity_ready_at": f"{DATE}T00:00:02Z",
            "spread_ready_at": f"{DATE}T00:00:03Z",
            "first_tradable_at": f"{DATE}T00:00:03Z",
            "first_evaluable_at": f"{DATE}T00:00:01Z",
            "first_evaluable_seconds_remaining": 244,
            "yes_token_id": "yes-token",
            "no_token_id": "no-token",
            "condition_id": "condition-1",
            "spread_normalized": True,
            "spread_gap_to_limit": -0.01,
            "liquidity_ready": True,
            "liquidity_state": "HEALTHY",
            "fair_value": 0.62,
            "market_price": 0.60,
            "true_probability": 0.62,
            "ev_after_spread": 0.04,
            "yes_bid": 0.58,
            "yes_ask": 0.60,
            "no_bid": 0.40,
            "no_ask": 0.42,
            "candidate_id": "candidate-1",
            "signal_id": "signal-1",
            "inventory_action": "OPEN",
            "starter_candidate": True,
            "reload_candidate": False,
            "unload_candidate": False,
            "final_derisk_candidate": False,
            "mfe_candidate_price": 0.60,
            "mae_candidate_price": 0.60,
            "candidate_peak_favorable": 0.0,
            "candidate_peak_adverse": 0.0,
            "exposure_before": 0.0,
            "exposure_after": 1.0,
            "risk_budget_used": 0.0,
            "remaining_risk_budget": 2.0,
            "current_exposure": 0.0,
            "target_exposure": 1.0,
            "seconds_remaining": 244,
        }),
    ])

    report = analyze_replay(base_dir=base_dir, date=DATE)
    coverage = report.phase2_coverage

    assert coverage["status"] == "READY_FOR_PHASE2_REPLAY_RESEARCH"
    assert coverage["coverage_gaps"] == []
    assert coverage["requirements"]["mfe_mae_support"]["status"] == "available"
    assert coverage["requirements"]["side_specific_yes_no_price_path"]["direct_events"] == 1


def test_replay_reports_phase2_ev_null_reason_coverage(tmp_path: Path) -> None:
    base_dir = tmp_path / "quant_data"
    _append_jsonl(base_dir, "decision_log", DATE, [
        _event("decision", f"{DATE}T00:00:00Z", {
            "decision_type": "skipped",
            "decision": "skip",
            "skipped": True,
            "normalized_skip_reason": "time_unsafe",
            "fair_value": None,
            "fair_value_available": False,
            "fair_value_null_reason": "time_unsafe",
            "market_price": None,
            "market_price_available": False,
            "market_price_null_reason": "time_unsafe",
            "true_probability": None,
            "true_probability_available": False,
            "true_probability_null_reason": "time_unsafe",
            "ev_after_spread": None,
            "ev_after_spread_available": False,
            "ev_after_spread_null_reason": "time_unsafe",
            "probability_model_stage": "pre_model_skip",
            "ev_calculation_stage": "pre_model_skip",
        }),
    ])

    report = analyze_replay(base_dir=base_dir, date=DATE)
    null_coverage = report.phase2_coverage["ev_null_reason_coverage"]

    assert null_coverage["status"] == "available"
    assert null_coverage["does_not_claim_ev_available"] is True
    assert null_coverage["fields"]["fair_value"]["null_reason_coverage_rate"] == pytest.approx(1.0)
    assert null_coverage["fields"]["ev_after_spread"]["null_reasons"] == [["time_unsafe", 1]]
    assert ["pre_model_skip", 1] in null_coverage["probability_model_stages"]
    assert ["pre_model_skip", 1] in null_coverage["ev_calculation_stages"]
    assert report.phase2_coverage["requirements"]["fair_value_ev_decay"]["status"] == "coverage_gap"


def test_replay_counts_market_snapshot_ev_null_reasons(tmp_path: Path) -> None:
    base_dir = tmp_path / "quant_data"
    _append_jsonl(base_dir, "market_snapshots", DATE, [
        _event("market_snapshot", f"{DATE}T00:00:00Z", {
            "ticker": "BTC",
            "orderbook_readiness_reason": "warmup_pending",
            "fair_value_available": False,
            "fair_value_null_reason": "no_orderbook",
            "market_price_available": False,
            "market_price_null_reason": "no_orderbook",
            "true_probability_available": False,
            "true_probability_null_reason": "no_orderbook",
            "ev_after_spread_available": False,
            "ev_after_spread_null_reason": "no_orderbook",
            "probability_model_stage": "pre_model_skip",
            "ev_calculation_stage": "pre_model_skip",
        }),
    ])

    report = analyze_replay(base_dir=base_dir, date=DATE)
    null_coverage = report.phase2_coverage["ev_null_reason_coverage"]

    assert null_coverage["events_checked"] == 1
    assert null_coverage["null_reason_coverage_rate"] == pytest.approx(1.0)
    assert null_coverage["fields"]["market_price"]["null_reasons"] == [["no_orderbook", 1]]
    assert ["pre_model_skip", 1] in null_coverage["probability_model_stages"]


def test_replay_builds_partial_lifecycle_replay_with_proxy_missed_starter(tmp_path: Path) -> None:
    base_dir = tmp_path / "quant_data"
    _append_jsonl(base_dir, "decision_log", DATE, [
        _event("decision", f"{DATE}T00:00:00Z", {
            "decision_type": "skipped",
            "decision": "skip",
            "skipped": True,
            "skip_reason": "ev_below_threshold",
            "market_id": "pm-5m-btc",
            "ticker": "BTC",
            "seconds_remaining": 180,
            "entry_cutoff_seconds": 90,
            "first_evaluable_seconds_remaining": 240,
            "yes_token_id": "yes-token",
            "no_token_id": "no-token",
            "spread": 0.03,
            "liquidity_state": "HEALTHY",
            "ev": 0.01,
            "yes_bid": 0.48,
            "yes_ask": 0.50,
            "no_bid": 0.50,
            "no_ask": 0.52,
        }),
    ])

    report = analyze_replay(base_dir=base_dir, date=DATE)
    replay = report.partial_lifecycle_replay

    assert replay["status"] == "PARTIAL_PROXY_REPLAY"
    assert report.lifecycle_replay_confidence in {"LOW_PROXY", "MEDIUM_PROXY"}
    assert report.missed_starter_candidates
    candidate = report.missed_starter_candidates[0]
    assert candidate["starter_replay_label"] == "missed_starter_proxy"
    assert candidate["starter_replay_inference"] == "proxy_inferred"
    assert any(item["section"] == "mfe_mae_support" for item in report.replay_unsupported_sections)
    assert report.timing_decay_summary["status"] == "proxy_inferred"
    assert report.spread_liquidity_readiness_summary["spread_events"] == 1


def test_replay_reports_micro_adaptive_timing_metrics(tmp_path: Path) -> None:
    base_dir = tmp_path / "quant_data"
    _append_jsonl(base_dir, "decision_log", DATE, [
        _event("decision", f"{DATE}T00:00:00Z", {
            "decision_type": "approved",
            "ticker": "BTC",
            "decision": "buy",
            "cutoff_policy": "micro_adaptive",
            "micro_timing_allowed": True,
            "micro_timing_branch_entered": True,
            "micro_timing_candidate": True,
            "effective_micro_cutoff_seconds": 35,
            "micro_cutoff_policy": "micro_adaptive",
        }),
        _event("decision", f"{DATE}T00:01:00Z", {
            "decision_type": "skipped",
            "skipped": True,
            "ticker": "ETH",
            "skip_reason": "Entry cutoff: 34s <= 35s",
            "cutoff_policy": "micro_adaptive",
            "micro_timing_allowed": False,
            "micro_timing_branch_entered": True,
            "micro_timing_candidate": True,
            "micro_timing_denied_reason": "hard_close_zone",
            "effective_micro_cutoff_seconds": 35,
            "micro_cutoff_policy": "micro_adaptive",
        }),
        _event("decision", f"{DATE}T00:02:00Z", {
            "decision_type": "skipped",
            "skipped": True,
            "ticker": "ETH",
            "skip_reason": "Entry cutoff: 40s <= 45s",
            "cutoff_policy": "adaptive",
            "micro_timing_allowed": False,
            "micro_timing_branch_entered": False,
            "micro_timing_candidate": False,
            "micro_timing_branch_skipped_reason": "non_micro_tier",
            "micro_cutoff_policy": "standard",
        }),
    ])

    report = analyze_replay(base_dir=base_dir, date=DATE)

    assert report.micro_timing_allowed_count == 1
    assert report.micro_timing_denied_count == 1
    assert report.micro_timing_branch_entered_count == 2
    assert report.micro_timing_candidate_count == 2
    assert ("hard_close_zone", 1) in report.micro_timing_denied_reasons
    assert ("non_micro_tier", 1) in report.micro_timing_branch_skipped_reasons


def test_replay_date_range_loading_counts_multiple_days(tmp_path: Path) -> None:
    base_dir = tmp_path / "runtime" / "quant_data"
    _append_jsonl(base_dir, "trade_journal", DATE, [
        _event("trade_close", f"{DATE}T00:00:00Z", {"position_id": "p1", "ticker": "BTC", "outcome": "YES", "pnl": 1.0}),
    ])
    _append_jsonl(base_dir, "trade_journal", NEXT_DATE, [
        _event("trade_close", f"{NEXT_DATE}T00:00:00Z", {"position_id": "p2", "ticker": "ETH", "outcome": "NO", "pnl": 2.0}),
    ])

    one_day = analyze_replay(base_dir=base_dir, date=DATE)
    range_report = analyze_replay(base_dir=base_dir, date_from=DATE, date_to=NEXT_DATE)

    assert one_day.total_trades == 1
    assert one_day.gross_pnl == pytest.approx(1.0)
    assert range_report.total_trades == 2
    assert range_report.gross_pnl == pytest.approx(3.0)


def test_replay_report_files_are_created(tmp_path: Path) -> None:
    base_dir = tmp_path / "runtime" / "quant_data"
    report_dir = tmp_path / "runtime" / "reports"
    _write_sample_replay(base_dir)

    report = analyze_replay(
        base_dir=base_dir,
        date=DATE,
        report_dir=report_dir,
        write_reports=True,
        write_csv=True,
    )

    json_path = report_dir / f"replay_report_{DATE}.json"
    csv_path = report_dir / f"replay_trades_{DATE}.csv"
    assert json_path.exists()
    assert csv_path.exists()
    assert json.loads(json_path.read_text(encoding="utf-8"))["total_trades"] == report.total_trades
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2


def test_replay_bad_json_lines_are_counted(tmp_path: Path) -> None:
    base_dir = tmp_path / "runtime" / "quant_data"
    _append_jsonl(base_dir, "decision_log", DATE, [
        "{bad-json",
        _event("decision", f"{DATE}T00:00:00Z", {"decision_type": "approved"}),
    ])

    report = analyze_replay(base_dir=base_dir, date=DATE)

    assert report.bad_json_lines == 1
    assert report.events_loaded == 1
