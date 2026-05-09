from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from polymarket.trader import PolymarketTrader
from tools.paper_evaluation_report import DECISION_CAUTION, DECISION_FAIL, DECISION_PASS
from tools.session_runtime_evaluator import (
    evaluate_session_runtime,
    format_terminal_summary,
    write_session_runtime_report,
)


DATE = "2026-05-09"


def _session_summary(**overrides) -> dict:
    summary = {
        "cycles_scanned": 50,
        "total_markets_scanned": 97,
        "total_opportunities_found": 0,
        "total_trades_simulated": 0,
        "paper_orders_created": 0,
        "paper_fills": 0,
        "paper_exits": 0,
        "simulated_pnl": 0.0,
        "max_drawdown": 0.0,
        "skipped_trade_reasons": {
            "Entry cutoff: 80s <= 90s": 44,
            "orderbook_unavailable": 42,
            "Risk plan returned zero position size -- skipping.": 11,
        },
        "top_skip_reasons": [],
        "risk_mode": "NORMAL",
        "risk_mode_allow_new_entries": True,
    }
    summary.update(overrides)
    return summary


def _replay_report(**overrides) -> dict:
    report = {
        "date_from": DATE,
        "date_to": DATE,
        "events_loaded": 120,
        "bad_json_lines": 0,
        "total_trades": 0,
        "skipped_decisions": 97,
        "top_skip_reasons": [["time_unsafe", 44], ["orderbook_unavailable", 42], ["risk_plan_zero", 11]],
        "approved_decisions": 0,
        "rejected_decisions": 97,
        "risk_reject_count": 11,
        "execution_failure_count": 0,
        "average_seconds_remaining": 187.68,
        "min_seconds_remaining": 34,
        "average_orderbook_age_ms": 4.71,
        "max_orderbook_age_ms": 25,
        "average_oracle_age_ms": 500,
        "max_oracle_age_ms": 900,
        "average_scan_cycle_duration_ms": 587.04,
        "average_decision_latency_ms": 993.22,
        "cutoff_block_count": 44,
        "adaptive_cutoff_allowed_count": 0,
        "adaptive_cutoff_denied_count": 44,
    }
    report.update(overrides)
    return report


def _no_entry_report(**overrides) -> dict:
    report = {
        "total_scanned": 130,
        "total_entered": 0,
        "total_skipped": 130,
        "skip_reason_counts": {
            "time_unsafe": 70,
            "orderbook_unavailable": 40,
            "risk_plan_zero": 20,
        },
        "execution_events_loaded": 0,
        "execution_failure_count": 0,
        "order_submit_attempt_count": 0,
        "paper_fill_count": 0,
        "market_data_quality": {},
    }
    report.update(overrides)
    return report


def test_session_evaluator_classifies_cutoff_primary_and_market_readiness_secondary() -> None:
    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(),
        replay_report=_replay_report(),
        date=DATE,
        load_offline_reports=False,
    )

    assert evaluation.session_status == DECISION_CAUTION
    assert evaluation.primary_bottleneck == "cutoff"
    assert evaluation.secondary_bottleneck == "market_readiness"
    assert evaluation.cutoff_behavior["time_unsafe_count"] == 44
    assert evaluation.orderbook_readiness["orderbook_unavailable_count"] == 42
    assert evaluation.risk_blocks["risk_plan_zero_count"] == 11
    assert evaluation.timing_quality["average_decision_latency_ms"] == pytest.approx(993.22)


def test_session_evaluator_fails_on_execution_failures() -> None:
    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(skipped_trade_reasons={"order_submit_failed": 1}),
        replay_report=_replay_report(
            execution_failure_count=1,
            top_skip_reasons=[["order_submit_failed", 1]],
            cutoff_block_count=0,
            adaptive_cutoff_denied_count=0,
        ),
        date=DATE,
        load_offline_reports=False,
    )

    assert evaluation.session_status == DECISION_FAIL
    assert evaluation.primary_bottleneck == "execution_failures"
    assert "execution_failures_present" in evaluation.fail_reasons


def test_session_evaluator_keeps_no_entry_safety_rejections_as_caution() -> None:
    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(skipped_trade_reasons={"order_intent:risk_not_approved": 8}),
        replay_report=_replay_report(
            top_skip_reasons=[["order_intent:risk_not_approved", 8]],
            execution_failure_count=0,
            cutoff_block_count=0,
            adaptive_cutoff_denied_count=0,
        ),
        no_entry_report={
            "total_scanned": 8,
            "total_entered": 0,
            "total_skipped": 8,
            "skip_reason_counts": {"order_intent:risk_not_approved": 8},
            "execution_failure_count": 0,
            "order_submit_attempt_count": 0,
            "paper_fill_count": 0,
            "market_data_quality": {},
        },
        date=DATE,
        load_offline_reports=False,
    )

    assert evaluation.session_status == DECISION_CAUTION
    assert evaluation.execution_summary["execution_failure_count"] == 0
    assert "execution_failures_present" not in evaluation.fail_reasons


def test_session_evaluator_does_not_use_total_execution_events_as_failures() -> None:
    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(
            total_markets_scanned=130,
            skipped_trade_reasons={"time_unsafe": 70, "orderbook_unavailable": 40, "risk_plan_zero": 20},
        ),
        replay_report=_replay_report(
            skipped_decisions=130,
            top_skip_reasons=[["time_unsafe", 70], ["orderbook_unavailable", 40], ["risk_plan_zero", 20]],
            execution_failure_count=0,
            cutoff_block_count=70,
            adaptive_cutoff_denied_count=70,
        ),
        no_entry_report=_no_entry_report(execution_events_loaded=170, execution_failure_count=0),
        date=DATE,
        load_offline_reports=False,
    )

    assert evaluation.session_status == DECISION_CAUTION
    assert evaluation.primary_bottleneck == "cutoff"
    assert evaluation.bottleneck_scores["execution_failures"] == 0
    assert evaluation.execution_summary["execution_events_loaded"] == 170
    assert evaluation.execution_summary["execution_failure_count"] == 0


def test_session_evaluator_prefers_corrected_replay_failure_count_over_no_entry_total_events_regression() -> None:
    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(
            total_markets_scanned=130,
            skipped_trade_reasons={"time_unsafe": 70, "orderbook_unavailable": 40, "risk_plan_zero": 20},
        ),
        replay_report=_replay_report(
            skipped_decisions=130,
            top_skip_reasons=[["time_unsafe", 70], ["orderbook_unavailable", 40], ["risk_plan_zero", 20]],
            execution_failure_count=0,
            cutoff_block_count=70,
            adaptive_cutoff_denied_count=70,
        ),
        no_entry_report=_no_entry_report(execution_events_loaded=170, execution_failure_count=170),
        date=DATE,
        load_offline_reports=False,
    )

    assert evaluation.session_status == DECISION_CAUTION
    assert evaluation.primary_bottleneck == "cutoff"
    assert evaluation.bottleneck_scores["execution_failures"] == 0
    assert evaluation.execution_summary["execution_failure_count"] == 0


def test_session_evaluator_regression_high_execution_events_zero_failures() -> None:
    evaluation = evaluate_session_runtime(
        no_entry_report=_no_entry_report(
            execution_events_loaded=170,
            execution_failure_count=0,
            skip_reason_counts={"orderbook_unavailable": 90, "risk_plan_zero": 40},
        ),
        date=DATE,
        load_offline_reports=False,
    )

    assert evaluation.session_status == DECISION_CAUTION
    assert evaluation.primary_bottleneck == "market_readiness"
    assert evaluation.bottleneck_scores["execution_failures"] == 0
    assert "execution_failures_present" not in evaluation.fail_reasons


def test_session_evaluator_no_entry_only_legacy_total_events_regression_is_caution() -> None:
    evaluation = evaluate_session_runtime(
        no_entry_report=_no_entry_report(
            execution_events_loaded=170,
            execution_failure_count=170,
            skip_reason_counts={"time_unsafe": 80, "risk_plan_zero": 50},
        ),
        date=DATE,
        load_offline_reports=False,
    )

    assert evaluation.session_status == DECISION_CAUTION
    assert evaluation.primary_bottleneck == "cutoff"
    assert evaluation.execution_summary["execution_failure_count"] == 0


def test_session_evaluator_still_fails_for_real_submit_cancel_or_system_execution_errors() -> None:
    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(skipped_trade_reasons={"order_submit_failed": 1}),
        replay_report=_replay_report(
            execution_failure_count=3,
            top_skip_reasons=[["order_submit_failed", 1]],
            cutoff_block_count=0,
            adaptive_cutoff_denied_count=0,
        ),
        no_entry_report=_no_entry_report(
            total_scanned=0,
            total_skipped=0,
            skip_reason_counts={},
            execution_events_loaded=3,
            execution_failure_count=3,
        ),
        date=DATE,
        load_offline_reports=False,
    )

    assert evaluation.session_status == DECISION_FAIL
    assert evaluation.primary_bottleneck == "execution_failures"
    assert evaluation.execution_summary["execution_failure_count"] == 3
    assert "execution_failures_present" in evaluation.fail_reasons


def test_session_evaluator_passes_healthy_session() -> None:
    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(
            total_markets_scanned=20,
            total_trades_simulated=5,
            paper_orders_created=5,
            paper_fills=5,
            skipped_trade_reasons={},
        ),
        replay_report=_replay_report(
            total_trades=5,
            skipped_decisions=0,
            top_skip_reasons=[],
            cutoff_block_count=0,
            adaptive_cutoff_denied_count=0,
        ),
        date=DATE,
        load_offline_reports=False,
    )

    assert evaluation.session_status == DECISION_PASS
    assert evaluation.primary_bottleneck == "healthy_no_signal"


def test_session_evaluator_formats_and_writes_report(tmp_path: Path) -> None:
    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(),
        replay_report=_replay_report(),
        date=DATE,
        load_offline_reports=False,
    )
    lines = format_terminal_summary(evaluation)
    report_path = write_session_runtime_report(evaluation, report_dir=tmp_path)

    assert any("SESSION_STATUS=CAUTION" in line for line in lines)
    assert any("PRIMARY_BOTTLENECK=cutoff" in line for line in lines)
    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved["primary_bottleneck"] == "cutoff"
    assert saved["session_status"] == DECISION_CAUTION
    assert evaluation.to_telegram_payload()["primary_bottleneck"] == "cutoff"


def test_trader_session_evaluator_hook_is_fail_soft(caplog: pytest.LogCaptureFixture) -> None:
    trader = PolymarketTrader.__new__(PolymarketTrader)
    trader.settings = SimpleNamespace(paper_trading=True, quant_data_dir="missing-quant-data")
    trader._paper_enabled = lambda: True
    trader.log_quant_summary = lambda force=False: None
    trader.paper_session_summary = lambda: _session_summary()
    emitted: list[dict] = []
    trader._emit_quant_event = lambda _method, payload: emitted.append(payload) or True
    trader._runtime_mode = lambda: "paper"

    with caplog.at_level("INFO"):
        trader.log_paper_session_summary()

    assert any("SESSION_STATUS=" in record.message for record in caplog.records)
    assert emitted and emitted[0]["event"] == "session_runtime_evaluation"
