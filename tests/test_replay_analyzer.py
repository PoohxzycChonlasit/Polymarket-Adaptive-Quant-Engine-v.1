from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from tools.replay_analyzer import analyze_replay


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
