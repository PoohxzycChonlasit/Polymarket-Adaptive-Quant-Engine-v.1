from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from polymarket.trader import PolymarketTrader
import tools.session_runtime_evaluator as session_runtime_evaluator
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
        "adaptive_cutoff_denied_reasons": [["hard_close_zone", 27], ["spread_too_wide", 17]],
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


class _FakeAnalyzerReport:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def to_dict(self) -> dict:
        return dict(self.payload)

    def __getattr__(self, name: str):
        if name == "market_data_quality":
            return self.payload.get("market_data_quality", {})
        if name == "recommendations":
            return self.payload.get("recommendations", [])
        return self.payload.get(name, 0)


def _write_execution_log(base_dir: Path, events: list[dict], *, flat_name: bool = False) -> None:
    lines = [json.dumps({"payload": event}) for event in events]
    if flat_name:
        base_dir.mkdir(parents=True)
        path = base_dir / f"execution_log_{DATE}.jsonl"
    else:
        execution_dir = base_dir / "execution_log"
        execution_dir.mkdir(parents=True)
        path = execution_dir / f"{DATE}.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_decision_log(base_dir: Path, events: list[dict]) -> None:
    decision_dir = base_dir / "decision_log"
    decision_dir.mkdir(parents=True)
    lines = [json.dumps(event) for event in events]
    (decision_dir / f"{DATE}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _decision_event(timestamp: str, skip_reason: str) -> dict:
    return {
        "timestamp_utc": timestamp,
        "event_type": "decision",
        "mode": "paper",
        "payload": {
            "decision_type": "skipped",
            "decision": "skip",
            "skipped": True,
            "skip_reason": skip_reason,
            "seconds_remaining": 180,
        },
    }


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
    assert ["hard_close_zone", 27] in evaluation.cutoff_behavior["adaptive_cutoff_denied_reasons"]
    assert evaluation.orderbook_readiness["orderbook_unavailable_count"] == 42
    assert evaluation.risk_blocks["risk_plan_zero_count"] == 11
    assert evaluation.timing_quality["average_decision_latency_ms"] == pytest.approx(993.22)


def test_session_evaluator_reports_micro_survival_bankroll_mode() -> None:
    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(
            bankroll_tier_id="T0_MICRO_SEED",
            bankroll_tier_name="Micro Seed",
            bankroll_family="MICRO",
            bankroll_risk_profile="seed_protection",
            bankroll_tier_locked=False,
            bankroll_hysteresis_active=False,
            bankroll_mode="MICRO_SURVIVAL",
            micro_survival_active=True,
            micro_position_size=0.05,
        ),
        replay_report=_replay_report(),
        date=DATE,
        load_offline_reports=False,
    )

    lines = format_terminal_summary(evaluation)

    assert evaluation.risk_blocks["bankroll_mode"] == "MICRO_SURVIVAL"
    assert evaluation.risk_blocks["micro_survival_active"] is True
    assert evaluation.risk_blocks["micro_position_size"] == pytest.approx(0.05)
    assert evaluation.risk_blocks["bankroll_tier_id"] == "T0_MICRO_SEED"
    assert evaluation.risk_blocks["bankroll_tier_name"] == "Micro Seed"
    assert evaluation.risk_blocks["bankroll_family"] == "MICRO"
    assert evaluation.risk_blocks["bankroll_risk_profile"] == "seed_protection"
    assert any("bankroll_mode=MICRO_SURVIVAL" in line for line in lines)
    assert any("micro_survival_active=true" in line for line in lines)
    assert any("tier_id=T0_MICRO_SEED" in line for line in lines)
    assert any("family=MICRO" in line for line in lines)


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


def test_session_evaluator_reports_orderbook_reason_breakdown_without_counting_warmup_as_unavailable() -> None:
    evaluation = evaluate_session_runtime(
        replay_report=_replay_report(
            top_skip_reasons=[["orderbook_unavailable", 12]],
            skipped_decisions=12,
            cutoff_block_count=0,
            adaptive_cutoff_denied_count=0,
            orderbook_readiness_reasons=[
                ["warmup_pending", 7],
                ["missing_token_id", 3],
                ["stale_book", 2],
                ["clob_rate_limited", 4],
            ],
            clob_error_categories=[["clob_rate_limited", 4]],
            clob_exception_types=[["HTTPError", 4]],
            clob_error_classes=[["rate_limited", 4]],
            clob_backoff_active_count=4,
            clob_circuit_open_count=2,
            max_clob_error_rate=0.75,
            clob_recovery_count=1,
        ),
        no_entry_report=_no_entry_report(
            total_scanned=12,
            total_skipped=12,
            skip_reason_counts={"orderbook_unavailable": 12},
            market_data_quality={},
        ),
        date=DATE,
        load_offline_reports=False,
    )

    assert evaluation.orderbook_readiness["warmup_pending_count"] == 7
    assert evaluation.orderbook_readiness["orderbook_unavailable_count"] == 7
    assert evaluation.orderbook_readiness["stale_data_count"] == 2
    assert ["warmup_pending", 7] in evaluation.orderbook_readiness["reason_breakdown"]
    assert ["clob_rate_limited", 4] in evaluation.orderbook_readiness["reason_breakdown"]
    assert ["clob_rate_limited", 4] in evaluation.orderbook_readiness["clob_error_categories"]
    assert ["HTTPError", 4] in evaluation.orderbook_readiness["clob_exception_types"]
    assert ["rate_limited", 4] in evaluation.orderbook_readiness["clob_error_classes"]
    assert evaluation.orderbook_readiness["clob_backoff_active_count"] == 4
    assert evaluation.orderbook_readiness["clob_circuit_open_count"] == 2
    assert evaluation.orderbook_readiness["max_clob_error_rate"] == pytest.approx(0.75)
    assert evaluation.orderbook_readiness["clob_recovery_count"] == 1
    assert evaluation.execution_summary["execution_failure_count"] == 0


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


def test_cli_recomputes_execution_failures_from_execution_jsonl(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    quant_dir = tmp_path / "quant_data"
    realtime_log_dir = tmp_path / "realtime_logs"
    _write_execution_log(
        quant_dir,
        (
            [{"event": "market_analysis_exception"} for _ in range(168)]
            + [{"event": "exit_submit_failed", "reason": "forced_exit"} for _ in range(2)]
        ),
        flat_name=True,
    )
    monkeypatch.setattr(
        session_runtime_evaluator,
        "_safe_analyze_replay",
        lambda **_: (
            _FakeAnalyzerReport(
                _replay_report(
                    skipped_decisions=130,
                    top_skip_reasons=[["time_unsafe", 70], ["orderbook_unavailable", 40], ["risk_plan_zero", 20]],
                    execution_failure_count=170,
                    cutoff_block_count=70,
                    adaptive_cutoff_denied_count=70,
                )
            ),
            None,
        ),
    )
    monkeypatch.setattr(
        session_runtime_evaluator,
        "_safe_analyze_no_entries",
        lambda **_: (
            _FakeAnalyzerReport(_no_entry_report(execution_events_loaded=170, execution_failure_count=170)),
            None,
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "session_runtime_evaluator",
            "--date",
            DATE,
            "--quant-data-dir",
            str(quant_dir),
            "--realtime-log-dir",
            str(realtime_log_dir),
        ],
    )

    exit_code = session_runtime_evaluator.main()
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "SESSION_STATUS=CAUTION PRIMARY_BOTTLENECK=cutoff" in output
    assert "execution_failures=0" in output
    assert "Execution failures were present" not in output


def test_cli_recomputed_execution_failures_still_counts_real_submit_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    quant_dir = tmp_path / "quant_data"
    realtime_log_dir = tmp_path / "realtime_logs"
    _write_execution_log(
        quant_dir,
        [{"event": "order_submit_failed", "error": "submit rejected by API"}],
        flat_name=True,
    )
    monkeypatch.setattr(
        session_runtime_evaluator,
        "_safe_analyze_replay",
        lambda **_: (
            _FakeAnalyzerReport(
                _replay_report(
                    skipped_decisions=0,
                    top_skip_reasons=[],
                    execution_failure_count=0,
                    cutoff_block_count=0,
                    adaptive_cutoff_denied_count=0,
                )
            ),
            None,
        ),
    )
    monkeypatch.setattr(
        session_runtime_evaluator,
        "_safe_analyze_no_entries",
        lambda **_: (
            _FakeAnalyzerReport(
                _no_entry_report(
                    total_scanned=0,
                    total_skipped=0,
                    skip_reason_counts={},
                    execution_events_loaded=1,
                    execution_failure_count=0,
                )
            ),
            None,
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "session_runtime_evaluator",
            "--date",
            DATE,
            "--quant-data-dir",
            str(quant_dir),
            "--realtime-log-dir",
            str(realtime_log_dir),
        ],
    )

    exit_code = session_runtime_evaluator.main()
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "SESSION_STATUS=FAIL PRIMARY_BOTTLENECK=execution_failures" in output
    assert "execution_failures=1" in output


def test_time_filter_since_excludes_earlier_events(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    _write_decision_log(
        quant_dir,
        [
            _decision_event(f"{DATE}T01:00:00Z", "clob_http_error"),
            _decision_event(f"{DATE}T02:00:00Z", "time_unsafe"),
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=quant_dir,
        realtime_log_dir=tmp_path / "realtime_logs",
        since="01:30",
    )

    assert evaluation.skip_summary["skip_reason_counts"] == {"time_unsafe": 1}
    assert evaluation.time_filter["range"] == f"{DATE}T01:30:00Z..{DATE}T23:59:59Z"
    assert evaluation.reports_used["no_entry_report"] is False


def test_time_filter_until_excludes_later_events(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    _write_decision_log(
        quant_dir,
        [
            _decision_event(f"{DATE}T01:00:00Z", "clob_http_error"),
            _decision_event(f"{DATE}T02:00:00Z", "time_unsafe"),
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=quant_dir,
        realtime_log_dir=tmp_path / "realtime_logs",
        until="01:30",
    )

    assert evaluation.skip_summary["skip_reason_counts"] == {"clob_http_error": 1}
    assert evaluation.orderbook_readiness["orderbook_unavailable_count"] == 1


def test_time_filter_since_until_together(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    _write_decision_log(
        quant_dir,
        [
            _decision_event(f"{DATE}T01:00:00Z", "clob_http_error"),
            _decision_event(f"{DATE}T02:00:00Z", "time_unsafe"),
            _decision_event(f"{DATE}T03:00:00Z", "risk_plan_zero"),
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=quant_dir,
        realtime_log_dir=tmp_path / "realtime_logs",
        since="01:30",
        until="02:30",
    )

    assert evaluation.skip_summary["skip_reason_counts"] == {"time_unsafe": 1}
    assert evaluation.time_filter["semantics"] == "half_open_since_inclusive_until_exclusive"


def test_time_filter_no_matching_events_returns_caution_no_data(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    _write_decision_log(
        quant_dir,
        [_decision_event(f"{DATE}T01:00:00Z", "clob_http_error")],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=quant_dir,
        realtime_log_dir=tmp_path / "realtime_logs",
        since="03:00",
        until="04:00",
    )

    assert evaluation.session_status == DECISION_CAUTION
    assert evaluation.primary_bottleneck == "no_data"
    assert "no_data_for_time_filter" in evaluation.caution_reasons
    assert evaluation.health_summary["skipped"] == 0


def test_cli_main_path_uses_time_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    quant_dir = tmp_path / "quant_data"
    report_dir = tmp_path / "reports"
    _write_decision_log(
        quant_dir,
        [
            _decision_event(f"{DATE}T01:00:00Z", "clob_http_error"),
            _decision_event(f"{DATE}T02:00:00Z", "time_unsafe"),
        ],
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "session_runtime_evaluator",
            "--date",
            DATE,
            "--quant-data-dir",
            str(quant_dir),
            "--realtime-log-dir",
            str(tmp_path / "realtime_logs"),
            "--report-dir",
            str(report_dir),
            "--since",
            "01:30",
            "--write-report",
        ],
    )

    exit_code = session_runtime_evaluator.main()
    output = capsys.readouterr().out
    report_path = report_dir / f"session_runtime_evaluation_{DATE}_0130_to_end.json"
    saved = json.loads(report_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert f"filter={DATE}T01:30:00Z..{DATE}T23:59:59Z" in output
    assert "top_skip_reasons=[['time_unsafe', 1]]" in output
    assert "clob_http_error" not in output
    assert saved["time_filter"]["since"] == "01:30"
    assert saved["time_filter"]["timezone"] == "UTC"


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
    assert any("deny_reasons=" in line for line in lines)
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
