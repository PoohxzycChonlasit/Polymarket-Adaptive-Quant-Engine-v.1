from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from polymarket.risk_modes import RiskModeState
from polymarket.trader import PolymarketTrader, TradeOutcome
from tools.paper_evaluation_report import evaluate_paper_run
from tools.quant_data_quality import scan_quant_data
from tools.replay_analyzer import analyze_replay
from tools.no_entry_analyzer import analyze_no_entries, discover_available_dates, main as no_entry_main, nearest_available_date, write_no_entry_report
from utils.quant_event_logger import QuantEventLogger
from utils.no_entry_diagnostics import classify_time_bucket, normalize_skip_reason
from utils.risk_manager import RiskPlan


class _CollectingDecisionLogger:
    def __init__(self) -> None:
        self.mode = "paper"
        self.payloads: list[dict] = []

    def log_decision(self, payload: dict) -> bool:
        self.payloads.append(payload)
        return True


def _jsonl_event(payload: dict) -> str:
    return json.dumps({
        "timestamp_utc": "2026-05-08T12:00:00Z",
        "event_type": "decision",
        "mode": "paper",
        "run_id": "test-run",
        "source_module": "test",
        "schema_version": "1.0",
        "payload": payload,
    })


def _runtime_snapshot() -> dict[str, tuple[int, int]]:
    snapshot: dict[str, tuple[int, int]] = {}
    for root in (Path("runtime/quant_data"), Path("runtime/reports"), Path("runtime/realtime_logs")):
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file():
                stat = path.stat()
                snapshot[str(path)] = (stat.st_size, stat.st_mtime_ns)
    return snapshot


def test_normalized_skip_reason_works() -> None:
    assert normalize_skip_reason("Risk plan returned zero position size -- skipping.") == "risk_plan_zero"
    assert normalize_skip_reason("Entry cutoff: 44s <= 90s") == "time_unsafe"
    assert normalize_skip_reason("orderbook_unavailable") == "orderbook_unavailable"
    assert normalize_skip_reason("delta_extreme") == "delta_extreme"


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (280, "early_window"),
        (200, "mid_window"),
        (120, "late_window"),
        (90, "unsafe_cutoff"),
        (None, "unknown"),
    ],
)
def test_time_buckets_are_correct(seconds: int | None, expected: str) -> None:
    assert classify_time_bucket(seconds, 90) == expected


def test_risk_plan_zero_diagnostics_emitted() -> None:
    trader = PolymarketTrader.__new__(PolymarketTrader)
    trader.settings = SimpleNamespace(paper_trading=True, execution_entry_cutoff_seconds=90)
    trader.quant_events = _CollectingDecisionLogger()
    trader._market_token_meta = {"BTC": {"slug": "btc-up-down-5m"}}
    trader._risk_mode_state = RiskModeState()
    trader.bankroll_state = SimpleNamespace(
        current_bankroll_for_sizing=8.7,
        current_cash_balance=8.7,
        open_position_market_value=0.0,
        current_bankroll_tier="T0_MICRO_SEED",
        bankroll_tier_locked=False,
        bankroll_hysteresis_active=False,
    )
    trader._wallet_reference_balance = None
    trader._paper_available_balance = lambda: 8.7
    trader._paper_wallet_reference_visible = lambda: False

    risk_plan = RiskPlan(
        account_balance=8.7,
        entry_price=0.52,
        stop_loss_price=0.52,
        take_profit_price=0.52,
        partial_tp_price=0.52,
        risk_amount=0.0,
        kelly_fraction=0.0,
        capped_fraction=0.0,
        position_size=0.0,
        notional_size=0.0,
        stop_loss_pct=0.08,
        diagnostics={
            "tier": "micro",
            "min_position_size_usd": 1.0,
            "reason_from_order_manager": "confidence_too_low,below_min_position_size",
        },
    )
    outcome = TradeOutcome(
        market_id="pm-5m-btc",
        question="BTC above?",
        decision="skip",
        confidence=0.51,
        risk_plan=risk_plan,
        receipt=None,
        skipped=True,
        skip_reason="Risk plan returned zero position size -- skipping.",
        display={
            "raw_skip_reason": "risk_plan_zero",
            "normalized_skip_reason": "risk_plan_zero",
            "ev": 0.01,
            "p_yes": 0.57,
            "p_no": 0.43,
            "outcome": "YES",
            "ask_price": 0.52,
            "market_epoch_start": 1_778_000_000,
            "seconds_remaining": 180,
            "entry_cutoff_seconds": 90,
        },
    )

    trader._emit_decision_event(outcome, ticker="BTC")

    payload = trader.quant_events.payloads[0]
    assert payload["raw_skip_reason"] == "risk_plan_zero"
    assert payload["normalized_skip_reason"] == "risk_plan_zero"
    assert payload["time_bucket"] == "mid_window"
    assert payload["lifecycle_phase"] == "ACTIVE_INVENTORY_TRADING"
    assert payload["candidate_id"].startswith("candidate_")
    assert payload["signal_id"].startswith("signal_")
    assert payload["fair_value"] == pytest.approx(0.57)
    assert payload["fair_value_available"] is True
    assert payload["fair_value_null_reason"] == ""
    assert payload["market_price"] == pytest.approx(0.52)
    assert payload["market_price_available"] is True
    assert payload["market_price_null_reason"] == ""
    assert payload["true_probability"] == pytest.approx(0.57)
    assert payload["true_probability_available"] is True
    assert payload["true_probability_null_reason"] == ""
    assert payload["ev_after_spread"] == pytest.approx(0.01)
    assert payload["ev_after_spread_available"] is True
    assert payload["ev_after_spread_null_reason"] == ""
    assert payload["probability_model_stage"] == "probability_model_output"
    assert payload["ev_calculation_stage"] == "ev_calculated"
    assert payload["mfe_candidate_price"] == pytest.approx(0.52)
    assert payload["mae_candidate_price"] == pytest.approx(0.52)
    assert payload["starter_candidate"] is True
    assert payload["reload_candidate"] is False
    assert payload["unload_candidate"] is False
    assert payload["final_derisk_candidate"] is False
    assert "token_ready_at" in payload
    assert "first_tradable_at" in payload
    assert payload["exposure_before"] == pytest.approx(0.0)
    assert payload["exposure_after"] == pytest.approx(0.0)
    assert payload["risk_budget_used"] == pytest.approx(0.0)
    assert "remaining_risk_budget" in payload
    diagnostics = payload["risk_plan_zero_diagnostics"]
    assert diagnostics["bankroll"] == pytest.approx(8.7)
    assert diagnostics["tier"] == "micro"
    assert diagnostics["risk_mode"] == "NORMAL"
    assert diagnostics["confidence"] == pytest.approx(0.51)
    assert diagnostics["edge"] == pytest.approx(0.01)
    assert diagnostics["entry_price"] == pytest.approx(0.52)
    assert diagnostics["final_position_size"] == 0.0
    assert diagnostics["final_notional_size"] == 0.0
    assert diagnostics["min_position_size_usd"] == pytest.approx(1.0)
    assert diagnostics["reason_from_order_manager"] == "confidence_too_low,below_min_position_size"


def test_phase2_ev_null_reasons_emitted_for_pre_model_skip() -> None:
    trader = PolymarketTrader.__new__(PolymarketTrader)
    trader.settings = SimpleNamespace(paper_trading=True, execution_entry_cutoff_seconds=90)
    trader.quant_events = _CollectingDecisionLogger()
    trader._market_token_meta = {"BTC": {"slug": "btc-up-down-5m"}}
    trader._risk_mode_state = RiskModeState()
    trader.bankroll_state = SimpleNamespace(
        current_bankroll_for_sizing=8.7,
        current_cash_balance=8.7,
        open_position_market_value=0.0,
        current_bankroll_tier="T0_MICRO_SEED",
        bankroll_tier_locked=False,
        bankroll_hysteresis_active=False,
    )
    trader._wallet_reference_balance = None
    trader._paper_available_balance = lambda: 8.7
    trader._paper_wallet_reference_visible = lambda: False

    outcome = TradeOutcome(
        market_id="pm-5m-btc",
        question="BTC above?",
        decision="skip",
        confidence=0.0,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="Entry cutoff: 40s <= 90s",
        display={
            "raw_skip_reason": "Entry cutoff: 40s <= 90s",
            "normalized_skip_reason": "time_unsafe",
            "seconds_remaining": 40,
            "entry_cutoff_seconds": 90,
            "market_epoch_start": 1_778_000_000,
            "ev_after_spread": None,
        },
    )

    trader._emit_decision_event(outcome, ticker="BTC")

    payload = trader.quant_events.payloads[0]
    assert payload["fair_value"] is None
    assert payload["fair_value_available"] is False
    assert payload["fair_value_null_reason"] == "time_unsafe"
    assert payload["market_price"] is None
    assert payload["market_price_available"] is False
    assert payload["market_price_null_reason"] == "time_unsafe"
    assert payload["true_probability"] is None
    assert payload["true_probability_available"] is False
    assert payload["true_probability_null_reason"] == "time_unsafe"
    assert payload["ev_after_spread"] is None
    assert payload["ev_after_spread_available"] is False
    assert payload["ev_after_spread_null_reason"] == "time_unsafe"
    assert payload["probability_model_stage"] == "pre_model_skip"
    assert payload["ev_calculation_stage"] == "pre_model_skip"


def test_analyzer_handles_empty_data(tmp_path: Path) -> None:
    report = analyze_no_entries(
        date="2026-05-08",
        quant_data_dir=tmp_path / "quant_data",
        realtime_log_dir=tmp_path / "realtime_logs",
    )

    assert report.total_scanned == 0
    assert report.total_entered == 0
    assert report.total_skipped == 0
    assert report.root_cause_category == "data"
    assert report.recommendations == ["No decision_log JSONL or scan_log CSV rows found for this date."]


def test_no_entry_filters_jsonl_by_utc_time_window(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    decision_dir = quant_dir / "decision_log"
    decision_dir.mkdir(parents=True)
    (decision_dir / "2026-05-08.jsonl").write_text(
        "\n".join([
            json.dumps({
                "timestamp_utc": "2026-05-08T17:42:59Z",
                "event_type": "decision",
                "mode": "paper",
                "run_id": "legacy",
                "source_module": "test",
                "schema_version": "1.0",
                "payload": {
                    "asset": "BTC",
                    "decision": "skip",
                    "skipped": True,
                    "raw_skip_reason": "legacy_before_window",
                },
            }),
            json.dumps({
                "timestamp_utc": "2026-05-08T17:44:08Z",
                "event_type": "decision",
                "mode": "paper",
                "run_id": "fresh",
                "source_module": "test",
                "schema_version": "1.0",
                "payload": {
                    "asset": "BTC",
                    "decision": "skip",
                    "skipped": True,
                    "raw_skip_reason": "warmup_pending",
                    "orderbook_readiness_reason": "warmup_pending",
                    "fair_value_available": False,
                    "fair_value_null_reason": "no_orderbook",
                },
            }),
            json.dumps({
                "timestamp_utc": "2026-05-08T17:47:00Z",
                "event_type": "decision",
                "mode": "paper",
                "run_id": "legacy",
                "source_module": "test",
                "schema_version": "1.0",
                "payload": {
                    "asset": "BTC",
                    "decision": "skip",
                    "skipped": True,
                    "raw_skip_reason": "legacy_after_window",
                },
            }),
        ])
        + "\n",
        encoding="utf-8",
    )

    report = analyze_no_entries(
        date="2026-05-08",
        quant_data_dir=quant_dir,
        realtime_log_dir=tmp_path / "realtime_logs",
        since="17:43",
        until="17:47",
    )

    assert report.time_filter["applied"] is True
    assert report.decision_events_loaded == 1
    assert report.total_scanned == 1
    assert report.skip_reason_counts == {"warmup_pending": 1}
    assert report.phase2_coverage["ev_null_reason_coverage"]["fields"]["fair_value"]["null_reason_events"] == 1


def test_no_entry_filters_jsonl_by_run_id_and_writes_run_scoped_report(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    reports_dir = tmp_path / "reports"
    decision_dir = quant_dir / "decision_log"
    decision_dir.mkdir(parents=True)
    (decision_dir / "2026-05-08.jsonl").write_text(
        "\n".join([
            json.dumps({
                "timestamp_utc": "2026-05-08T17:44:08Z",
                "event_type": "decision",
                "mode": "paper",
                "run_id": "run/target",
                "payload": {
                    "asset": "BTC",
                    "decision": "skip",
                    "skipped": True,
                    "raw_skip_reason": "warmup_pending",
                    "orderbook_readiness_reason": "warmup_pending",
                },
            }),
            json.dumps({
                "timestamp_utc": "2026-05-08T17:44:09Z",
                "event_type": "decision",
                "mode": "paper",
                "run_id": "run-other",
                "payload": {
                    "asset": "BTC",
                    "decision": "skip",
                    "skipped": True,
                    "raw_skip_reason": "other_run",
                },
            }),
            json.dumps({
                "timestamp_utc": "2026-05-08T17:44:10Z",
                "event_type": "decision",
                "mode": "paper",
                "payload": {
                    "asset": "BTC",
                    "decision": "skip",
                    "skipped": True,
                    "raw_skip_reason": "missing_run_id",
                },
            }),
        ])
        + "\n",
        encoding="utf-8",
    )

    report = analyze_no_entries(
        date="2026-05-08",
        quant_data_dir=quant_dir,
        realtime_log_dir=tmp_path / "realtime_logs",
        report_dir=reports_dir,
        write_report=True,
        run_id="run/target",
    )

    assert report.run_id == "run/target"
    assert report.decision_events_loaded == 1
    assert report.total_scanned == 1
    assert report.skip_reason_counts == {"warmup_pending": 1}
    assert report.time_filter["run_id"] == "run/target"
    assert report.time_filter["run_id_applied"] is True
    assert (reports_dir / "no_entry_report_2026-05-08_run_run_target.json").exists()


def test_no_entry_cli_lists_run_ids(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    quant_dir = tmp_path / "quant_data"
    decision_dir = quant_dir / "decision_log"
    decision_dir.mkdir(parents=True)
    (decision_dir / "2026-05-08.jsonl").write_text(
        "\n".join([
            json.dumps({
                "timestamp_utc": "2026-05-08T17:44:08Z",
                "event_type": "decision",
                "mode": "paper",
                "run_id": "run-a",
                "payload": {"asset": "BTC"},
            }),
            json.dumps({
                "timestamp_utc": "2026-05-08T17:45:08Z",
                "event_type": "decision",
                "mode": "paper",
                "run_id": "run-b",
                "payload": {"asset": "ETH"},
            }),
        ])
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", [
        "no_entry_analyzer",
        "--date",
        "2026-05-08",
        "--quant-data-dir",
        str(quant_dir),
        "--realtime-log-dir",
        str(tmp_path / "realtime_logs"),
        "--list-run-ids",
    ])

    assert no_entry_main() == 0

    output = capsys.readouterr().out
    assert "Available run IDs" in output
    assert "run_id=run-a event_count=1" in output
    assert "run_id=run-b event_count=1" in output
    assert "categories=decision_log" in output


def test_no_entry_phase2_coverage_reads_market_snapshot_ev_null_reasons(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    snapshot_dir = quant_dir / "market_snapshots"
    snapshot_dir.mkdir(parents=True)
    (snapshot_dir / "2026-05-08.jsonl").write_text(
        _jsonl_event({
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
        })
        + "\n",
        encoding="utf-8",
    )

    report = analyze_no_entries(
        date="2026-05-08",
        quant_data_dir=quant_dir,
        realtime_log_dir=tmp_path / "realtime_logs",
    )

    null_coverage = report.phase2_coverage["ev_null_reason_coverage"]
    assert null_coverage["events_checked"] == 1
    assert null_coverage["fields"]["ev_after_spread"]["null_reasons"] == [["no_orderbook", 1]]
    assert ["pre_model_skip", 1] in null_coverage["ev_calculation_stages"]


def test_analyzer_counts_malformed_events(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    decision_dir = quant_dir / "decision_log"
    decision_dir.mkdir(parents=True)
    (decision_dir / "2026-05-08.jsonl").write_text(
        "\n".join([
            "{bad-json",
            "[]",
            _jsonl_event({
                "asset": "BTC",
                "decision": "skip",
                "skipped": True,
                "raw_skip_reason": "confidence_too_low",
                "seconds_remaining": 200,
                "entry_cutoff_seconds": 90,
            }),
        ])
        + "\n",
        encoding="utf-8",
    )

    report = analyze_no_entries(
        date="2026-05-08",
        quant_data_dir=quant_dir,
        realtime_log_dir=tmp_path / "realtime_logs",
    )

    assert report.bad_json_lines == 2
    assert report.total_scanned == 1
    assert report.count_confidence_too_low == 1
    assert report.root_cause_category == "data"
    assert any("Malformed JSONL" in item for item in report.recommendations)


def test_analyzer_classifies_zero_entry_mixed_skip_reasons(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    decision_dir = quant_dir / "decision_log"
    decision_dir.mkdir(parents=True)
    (decision_dir / "2026-05-08.jsonl").write_text(
        "\n".join([
            _jsonl_event({
                "asset": "BTC",
                "decision": "skip",
                "skipped": True,
                "raw_skip_reason": "risk_plan_zero",
                "normalized_skip_reason": "risk_plan_zero",
                "seconds_remaining": 240,
                "entry_cutoff_seconds": 90,
            }),
            _jsonl_event({
                "asset": "ETH",
                "decision": "skip",
                "skipped": True,
                "raw_skip_reason": "Risk plan returned zero position size -- skipping.",
                "seconds_remaining": 180,
                "entry_cutoff_seconds": 90,
            }),
            _jsonl_event({
                "asset": "BTC",
                "decision": "skip",
                "skipped": True,
                "raw_skip_reason": "Risk plan returned zero position size -- skipping.",
                "seconds_remaining": 175,
                "entry_cutoff_seconds": 90,
            }),
            _jsonl_event({
                "asset": "BTC",
                "decision": "skip",
                "skipped": True,
                "raw_skip_reason": "confidence_too_low",
                "seconds_remaining": 170,
                "entry_cutoff_seconds": 90,
            }),
            _jsonl_event({
                "asset": "ETH",
                "decision": "skip",
                "skipped": True,
                "raw_skip_reason": "ev_below_threshold",
                "seconds_remaining": 160,
                "entry_cutoff_seconds": 90,
            }),
            _jsonl_event({
                "asset": "BTC",
                "decision": "skip",
                "skipped": True,
                "raw_skip_reason": "Entry cutoff: 80s <= 90s",
                "seconds_remaining": 80,
                "entry_cutoff_seconds": 90,
            }),
            _jsonl_event({
                "asset": "ETH",
                "decision": "skip",
                "skipped": True,
                "raw_skip_reason": "orderbook_unavailable",
                "seconds_remaining": 220,
                "entry_cutoff_seconds": 90,
            }),
        ])
        + "\n",
        encoding="utf-8",
    )

    report = analyze_no_entries(
        date="2026-05-08",
        quant_data_dir=quant_dir,
        realtime_log_dir=tmp_path / "realtime_logs",
    )

    assert report.total_entered == 0
    assert report.total_skipped == 7
    assert report.count_risk_plan_zero == 3
    assert report.count_confidence_too_low == 1
    assert report.count_ev_below_threshold == 1
    assert report.count_time_unsafe == 1
    assert report.count_orderbook_unavailable_or_stale == 1
    assert report.root_cause_category == "risk"
    assert report.root_cause_counts == {
        "data": 1,
        "strategy": 2,
        "risk": 3,
        "cutoff": 1,
        "execution": 0,
    }
    assert ["risk_plan_zero", 3] in report.top_skip_reasons


def test_order_intent_reject_is_not_execution_failure(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    execution_dir = quant_dir / "execution_log"
    execution_dir.mkdir(parents=True)
    (execution_dir / "2026-05-08.jsonl").write_text(
        "\n".join([
            _jsonl_event({"event": "order_intent_reject", "reason": "risk_not_approved"}),
            _jsonl_event({"event": "order_submit_attempt"}),
            _jsonl_event({"event": "paper_fill"}),
        ])
        + "\n",
        encoding="utf-8",
    )

    report = analyze_no_entries(
        date="2026-05-08",
        quant_data_dir=quant_dir,
        realtime_log_dir=tmp_path / "realtime_logs",
    )

    assert report.execution_events_loaded == 3
    assert report.execution_stage_attempt_count == 2
    assert report.execution_diagnostic_event_count == 1
    assert report.order_submit_attempt_count == 1
    assert report.paper_fill_count == 1
    assert report.execution_failure_count == 0


def test_execution_log_diagnostics_do_not_override_pre_execution_blocks(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    decision_dir = quant_dir / "decision_log"
    execution_dir = quant_dir / "execution_log"
    decision_dir.mkdir(parents=True)
    execution_dir.mkdir(parents=True)
    (decision_dir / "2026-05-08.jsonl").write_text(
        "\n".join([
            _jsonl_event({
                "asset": "BTC",
                "decision": "skip",
                "skipped": True,
                "raw_skip_reason": "Entry cutoff: 80s <= 90s",
                "seconds_remaining": 80,
                "entry_cutoff_seconds": 90,
            }),
            _jsonl_event({
                "asset": "ETH",
                "decision": "skip",
                "skipped": True,
                "raw_skip_reason": "Entry cutoff: 70s <= 90s",
                "seconds_remaining": 70,
                "entry_cutoff_seconds": 90,
            }),
            _jsonl_event({
                "asset": "BTC",
                "decision": "skip",
                "skipped": True,
                "raw_skip_reason": "risk_plan_zero",
                "seconds_remaining": 180,
                "entry_cutoff_seconds": 90,
            }),
        ])
        + "\n",
        encoding="utf-8",
    )
    (execution_dir / "2026-05-08.jsonl").write_text(
        "\n".join([
            _jsonl_event({"event": "market_analysis_exception"}),
            _jsonl_event({"event": "market_analysis_exception"}),
            _jsonl_event({"event": "order_intent_reject", "reason": "risk_not_approved"}),
        ])
        + "\n",
        encoding="utf-8",
    )

    report = analyze_no_entries(
        date="2026-05-08",
        quant_data_dir=quant_dir,
        realtime_log_dir=tmp_path / "realtime_logs",
    )

    assert report.execution_events_loaded == 3
    assert report.execution_stage_attempt_count == 0
    assert report.execution_diagnostic_event_count == 3
    assert report.execution_analysis_exception_count == 2
    assert report.execution_failure_count == 0
    assert report.root_cause_category == "cutoff"
    assert report.root_cause_counts == {
        "data": 0,
        "strategy": 0,
        "risk": 1,
        "cutoff": 2,
        "execution": 0,
    }


def test_real_execution_stage_errors_still_count_as_execution_failures(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    execution_dir = quant_dir / "execution_log"
    execution_dir.mkdir(parents=True)
    (execution_dir / "2026-05-08.jsonl").write_text(
        "\n".join([
            _jsonl_event({"event": "order_submit_failed"}),
            _jsonl_event({"event": "cancel_order", "status": "failed"}),
            _jsonl_event({"event": "market_analysis_exception"}),
        ])
        + "\n",
        encoding="utf-8",
    )

    report = analyze_no_entries(
        date="2026-05-08",
        quant_data_dir=quant_dir,
        realtime_log_dir=tmp_path / "realtime_logs",
    )

    assert report.execution_stage_attempt_count == 2
    assert report.execution_diagnostic_event_count == 1
    assert report.execution_analysis_exception_count == 1
    assert report.execution_failure_count == 2
    assert report.root_cause_counts["execution"] == 2


def test_cli_does_not_write_report_without_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    quant_dir = tmp_path / "quant_data"
    reports_dir = tmp_path / "reports"
    decision_dir = quant_dir / "decision_log"
    decision_dir.mkdir(parents=True)
    (decision_dir / "2026-05-08.jsonl").write_text(
        _jsonl_event({
            "asset": "BTC",
            "decision": "skip",
            "skipped": True,
            "raw_skip_reason": "confidence_too_low",
        })
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", [
        "no_entry_analyzer",
        "--date",
        "2026-05-08",
        "--quant-data-dir",
        str(quant_dir),
        "--realtime-log-dir",
        str(tmp_path / "realtime_logs"),
        "--report-dir",
        str(reports_dir),
    ])

    assert no_entry_main() == 0

    assert not (reports_dir / "no_entry_report_2026-05-08.json").exists()


def test_analyzer_classifies_decision_time_bucket_from_seconds(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    decision_dir = quant_dir / "decision_log"
    decision_dir.mkdir(parents=True)
    (decision_dir / "2026-05-08.jsonl").write_text(
        _jsonl_event({
            "asset": "BTC",
            "decision": "skip",
            "skipped": True,
            "raw_skip_reason": "confidence_too_low",
            "confidence": 0.48,
            "ev": 0.0,
            "seconds_remaining": 180,
            "entry_cutoff_seconds": 90,
        })
        + "\n",
        encoding="utf-8",
    )

    report = analyze_no_entries(
        date="2026-05-08",
        quant_data_dir=quant_dir,
        realtime_log_dir=tmp_path / "realtime_logs",
    )

    assert report.skip_by_time_bucket == {"mid_window": 1}
    assert report.missing_timing_count == 0


def test_analyzer_counts_missing_timing(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    decision_dir = quant_dir / "decision_log"
    decision_dir.mkdir(parents=True)
    (decision_dir / "2026-05-08.jsonl").write_text(
        _jsonl_event({
            "asset": "ETH",
            "decision": "skip",
            "skipped": True,
            "raw_skip_reason": "orderbook_unavailable",
            "normalized_skip_reason": "orderbook_unavailable",
        })
        + "\n",
        encoding="utf-8",
    )

    report = analyze_no_entries(
        date="2026-05-08",
        quant_data_dir=quant_dir,
        realtime_log_dir=tmp_path / "realtime_logs",
    )

    assert report.skip_by_time_bucket == {"unknown": 1}
    assert report.missing_timing_count == 1
    assert report.missing_timing_percentage == 1.0
    assert report.unknown_timing_by_cause == {"missing_data": 1}
    assert report.top_skip_reasons_with_missing_timing == [["orderbook_unavailable", 1]]


def test_analyzer_recommends_shorter_interval_when_time_unsafe_dominates(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    decision_dir = quant_dir / "decision_log"
    decision_dir.mkdir(parents=True)
    (decision_dir / "2026-05-08.jsonl").write_text(
        "\n".join([
            _jsonl_event({
                "asset": "BTC",
                "decision": "skip",
                "skipped": True,
                "raw_skip_reason": "Entry cutoff: 80s <= 90s",
                "seconds_remaining": 80,
                "entry_cutoff_seconds": 90,
            }),
            _jsonl_event({
                "asset": "ETH",
                "decision": "skip",
                "skipped": True,
                "raw_skip_reason": "Entry cutoff: 70s <= 90s",
                "seconds_remaining": 70,
                "entry_cutoff_seconds": 90,
            }),
            _jsonl_event({
                "asset": "BTC",
                "decision": "skip",
                "skipped": True,
                "raw_skip_reason": "confidence_too_low",
                "seconds_remaining": 180,
                "entry_cutoff_seconds": 90,
            }),
        ])
        + "\n",
        encoding="utf-8",
    )

    report = analyze_no_entries(
        date="2026-05-08",
        quant_data_dir=quant_dir,
        realtime_log_dir=tmp_path / "realtime_logs",
    )

    assert any("shorter scan interval" in item for item in report.recommendations)


def test_analyzer_recommends_instrumentation_when_unknown_timing_dominates(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    decision_dir = quant_dir / "decision_log"
    decision_dir.mkdir(parents=True)
    (decision_dir / "2026-05-08.jsonl").write_text(
        "\n".join([
            _jsonl_event({
                "asset": "BTC",
                "decision": "skip",
                "skipped": True,
                "raw_skip_reason": "orderbook_unavailable",
            }),
            _jsonl_event({
                "asset": "ETH",
                "decision": "skip",
                "skipped": True,
                "raw_skip_reason": "delta_extreme",
                "seconds_remaining": "not-a-number",
                "entry_cutoff_seconds": 90,
            }),
            _jsonl_event({
                "asset": "BTC",
                "decision": "skip",
                "skipped": True,
                "raw_skip_reason": "confidence_too_low",
                "seconds_remaining": 180,
                "entry_cutoff_seconds": 90,
            }),
        ])
        + "\n",
        encoding="utf-8",
    )

    report = analyze_no_entries(
        date="2026-05-08",
        quant_data_dir=quant_dir,
        realtime_log_dir=tmp_path / "realtime_logs",
    )

    assert report.missing_timing_count == 1
    assert report.unparseable_timing_count == 1
    assert report.unknown_timing_percentage == pytest.approx(0.6667)
    assert report.unknown_timing_by_cause == {"missing_data": 1, "unparseable_data": 1}
    assert any("timing instrumentation" in item for item in report.recommendations)


def test_analyzer_and_report_tests_do_not_write_real_runtime(tmp_path: Path) -> None:
    before = _runtime_snapshot()

    quant_dir = tmp_path / "quant_data"
    reports_dir = tmp_path / "reports"
    realtime_dir = tmp_path / "realtime_logs"
    logger = QuantEventLogger(
        base_dir=quant_dir,
        enabled=True,
        mode="paper",
        run_id="isolation-test",
    )
    assert logger.log_decision({"asset": "BTC", "decision": "SKIP"})

    scan_quant_data(base_dir=quant_dir, date="2026-05-08", report_dir=reports_dir, write_report=True)
    analyze_replay(base_dir=quant_dir, date="2026-05-08", report_dir=reports_dir, write_reports=True, write_csv=True)
    evaluate_paper_run(report_dir=reports_dir, date="2026-05-08", write_report=True)
    analyze_no_entries(
        date="2026-05-08",
        quant_data_dir=quant_dir,
        realtime_log_dir=realtime_dir,
        report_dir=reports_dir,
        write_report=True,
    )

    assert _runtime_snapshot() == before
    assert (reports_dir / "quant_data_quality_2026-05-08.json").exists()
    assert (reports_dir / "replay_report_2026-05-08.json").exists()
    assert (reports_dir / "paper_evaluation_2026-05-08.json").exists()
    assert (reports_dir / "no_entry_report_2026-05-08.json").exists()


def test_analyzer_uses_scan_csv_when_decision_log_is_absent(tmp_path: Path) -> None:
    day_dir = tmp_path / "realtime_logs" / "2026-05-08"
    day_dir.mkdir(parents=True)
    (day_dir / "scan_log_test.csv").write_text(
        "\n".join([
            "timestamp_utc,date_th,time_th,asset,feed,decision,confidence,edge,momentum_pct,score,signal,position_size,order_id,order_status,skip_reason,daily_pnl_pct,bankroll,raw_skip_reason,normalized_skip_reason,seconds_remaining,entry_cutoff_seconds,time_bucket",
            "2026-05-08T12:00:00Z,08/05/2026,12:00:00,BTC,polymarket-5m,rejected,0.49,0.01,0,0,SKIP,0,,skipped,Entry cutoff: 80s <= 90s,0,10,Entry cutoff: 80s <= 90s,time_unsafe,80,90,unsafe_cutoff",
        ])
        + "\n",
        encoding="utf-8",
    )

    report = analyze_no_entries(
        date="2026-05-08",
        quant_data_dir=tmp_path / "quant_data",
        realtime_log_dir=tmp_path / "realtime_logs",
    )

    assert report.decision_events_loaded == 0
    assert report.scan_rows_loaded == 1
    assert report.total_scanned == 1
    assert report.total_skipped == 1
    assert report.skip_reason_counts == {"time_unsafe": 1}
    assert report.skip_by_time_bucket == {"unsafe_cutoff": 1}


def test_analyzer_writes_json_report(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    decision_dir = quant_dir / "decision_log"
    decision_dir.mkdir(parents=True)
    decision_path = decision_dir / "2026-05-08.jsonl"
    decision_path.write_text(
        "\n".join([
            _jsonl_event({
                "asset": "BTC",
                "decision": "skip",
                "skipped": True,
                "raw_skip_reason": "orderbook_unavailable",
                "normalized_skip_reason": "orderbook_unavailable",
                "confidence": 0.0,
                "ev": 0.0,
                "seconds_remaining": 260,
                "entry_cutoff_seconds": 90,
                "time_bucket": "early_window",
            }),
            _jsonl_event({
                "asset": "ETH",
                "decision": "skip",
                "skipped": True,
                "raw_skip_reason": "risk_plan_zero",
                "normalized_skip_reason": "risk_plan_zero",
                "confidence": 0.53,
                "ev": 0.015,
                "seconds_remaining": 180,
                "entry_cutoff_seconds": 90,
                "time_bucket": "mid_window",
            }),
            _jsonl_event({
                "asset": "BTC",
                "decision": "buy",
                "skipped": False,
                "confidence": 0.62,
                "ev": 0.05,
            }),
        ])
        + "\n",
        encoding="utf-8",
    )

    report = analyze_no_entries(
        date="2026-05-08",
        quant_data_dir=quant_dir,
        realtime_log_dir=tmp_path / "realtime_logs",
    )
    output_path = write_no_entry_report(report, report_dir=tmp_path / "reports")

    assert output_path == tmp_path / "reports" / "no_entry_report_2026-05-08.json"
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["total_scanned"] == 3
    assert saved["total_entered"] == 1
    assert saved["total_skipped"] == 2
    assert saved["skip_reason_counts"] == {
        "orderbook_unavailable": 1,
        "risk_plan_zero": 1,
    }
    assert saved["skip_percentages"] == {
        "orderbook_unavailable": 0.5,
        "risk_plan_zero": 0.5,
    }
    assert saved["skip_by_asset"]["BTC"]["orderbook_unavailable"] == 1
    assert saved["skip_by_asset"]["ETH"]["risk_plan_zero"] == 1
    assert saved["skip_by_time_bucket"] == {"early_window": 1, "mid_window": 1}
    assert saved["average_confidence_by_skip_reason"]["risk_plan_zero"] == pytest.approx(0.53)
    assert saved["average_ev_by_skip_reason"]["risk_plan_zero"] == pytest.approx(0.015)
    assert saved["count_risk_plan_zero"] == 1
    assert saved["count_orderbook_unavailable"] == 1
    assert any("Orderbook unavailable" in item for item in saved["recommendations"])


def test_analyzer_reports_market_data_quality_section(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    decision_dir = quant_dir / "decision_log"
    snapshot_dir = quant_dir / "market_snapshots"
    decision_dir.mkdir(parents=True)
    snapshot_dir.mkdir(parents=True)
    (decision_dir / "2026-05-08.jsonl").write_text(
        "\n".join([
            _jsonl_event({
                "asset": "BTC",
                "decision": "skip",
                "skipped": True,
                "raw_skip_reason": "orderbook_unavailable",
                "normalized_skip_reason": "orderbook_unavailable",
            }),
            _jsonl_event({
                "asset": "ETH",
                "decision": "skip",
                "skipped": True,
                "raw_skip_reason": "stale_feed",
                "normalized_skip_reason": "stale_data",
            }),
        ])
        + "\n",
        encoding="utf-8",
    )
    (snapshot_dir / "2026-05-08.jsonl").write_text(
        _jsonl_event({
            "ticker": "BTC",
            "orderbook_age_ms": 100,
            "yes_orderbook_age_ms": 80,
            "no_orderbook_age_ms": 120,
            "token_mapping_warning": "yes_no_condition_id_mismatch",
        })
        + "\n",
        encoding="utf-8",
    )

    report = analyze_no_entries(
        date="2026-05-08",
        quant_data_dir=quant_dir,
        realtime_log_dir=tmp_path / "realtime_logs",
    )

    assert report.market_data_quality["market_snapshots_loaded"] == 1
    assert report.market_data_quality["stale_data_count"] == 1
    assert report.market_data_quality["orderbook_unavailable_count"] == 1
    assert report.market_data_quality["average_orderbook_age_ms"] == pytest.approx(100.0)
    assert report.market_data_quality["token_mapping_warning_count"] == 1
    assert any("Token mapping warnings" in item for item in report.recommendations)


def test_no_entry_report_includes_phase2_coverage_gaps(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    decision_dir = quant_dir / "decision_log"
    decision_dir.mkdir(parents=True)
    (decision_dir / "2026-05-08.jsonl").write_text(
        _jsonl_event({
            "asset": "BTC",
            "decision": "skip",
            "skipped": True,
            "raw_skip_reason": "ev_below_threshold",
            "seconds_remaining": 180,
            "entry_cutoff_seconds": 90,
            "orderbook_readiness_reason": "ready",
            "spread": 0.03,
            "liquidity_state": "HEALTHY",
            "ev": 0.01,
        })
        + "\n",
        encoding="utf-8",
    )

    report = analyze_no_entries(
        date="2026-05-08",
        quant_data_dir=quant_dir,
        realtime_log_dir=tmp_path / "realtime_logs",
    )
    coverage = report.phase2_coverage

    assert coverage["status"] == "PARTIAL_PHASE2_COVERAGE"
    assert "mfe_mae_support" in coverage["coverage_gaps"]
    assert coverage["requirements"]["fair_value_ev_decay"]["status"] == "proxy_inferred"
    assert coverage["requirements"]["token_orderbook_readiness"]["status"] == "available"
    assert report.partial_lifecycle_replay["status"] == "PARTIAL_PROXY_REPLAY"
    assert report.missed_starter_candidates
    assert report.missed_starter_candidates[0]["starter_replay_inference"] == "proxy_inferred"
    assert any(item["status"] == "coverage_gap" for item in report.replay_unsupported_sections)


def test_list_dates_finds_available_data(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    realtime_dir = tmp_path / "realtime_logs"
    (quant_dir / "decision_log").mkdir(parents=True)
    (quant_dir / "market_snapshots").mkdir(parents=True)
    (realtime_dir / "2026-05-09").mkdir(parents=True)
    (quant_dir / "decision_log" / "2026-05-08.jsonl").write_text(_jsonl_event({"asset": "BTC"}) + "\n", encoding="utf-8")
    (quant_dir / "market_snapshots" / "2026-05-09.jsonl").write_text(_jsonl_event({"ticker": "ETH"}) + "\n", encoding="utf-8")
    (realtime_dir / "2026-05-09" / "scan_log_test.csv").write_text("timestamp_utc,asset,decision\n", encoding="utf-8")

    dates = discover_available_dates(
        quant_data_dir=quant_dir,
        realtime_log_dir=realtime_dir,
    )

    assert dates == {
        "2026-05-08": {"decision_log": 1},
        "2026-05-09": {"market_snapshots": 1, "scan_csv": 1},
    }


def test_missing_date_prints_helpful_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    quant_dir = tmp_path / "quant_data"
    realtime_dir = tmp_path / "realtime_logs"
    (quant_dir / "decision_log").mkdir(parents=True)
    (quant_dir / "decision_log" / "2026-05-08.jsonl").write_text(_jsonl_event({"asset": "BTC"}) + "\n", encoding="utf-8")

    monkeypatch.setattr(sys, "argv", [
        "no_entry_analyzer",
        "--date",
        "2026-05-09",
        "--quant-data-dir",
        str(quant_dir),
        "--realtime-log-dir",
        str(realtime_dir),
        "--report-dir",
        str(tmp_path / "reports"),
    ])

    assert no_entry_main() == 0
    output = capsys.readouterr().out

    assert "No data found for requested date." in output
    assert f"searched decision_log path: {quant_dir / 'decision_log' / '2026-05-09.jsonl'}" in output
    assert f"searched market_snapshots path: {quant_dir / 'market_snapshots' / '2026-05-09.jsonl'}" in output
    assert f"searched realtime_logs path: {realtime_dir / '2026-05-09'}" in output
    assert "available dates:" in output
    assert "2026-05-08: decision_log JSONL=1" in output
    assert "nearest date with data: 2026-05-08" in output
    assert "suggestion: python -m tools.no_entry_analyzer --date 2026-05-08" in output


def test_utc_local_mismatch_suggests_nearest_date(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    realtime_dir = tmp_path / "realtime_logs"
    (quant_dir / "decision_log").mkdir(parents=True)
    (realtime_dir / "2026-05-10").mkdir(parents=True)
    (quant_dir / "decision_log" / "2026-05-08.jsonl").write_text(_jsonl_event({"asset": "BTC"}) + "\n", encoding="utf-8")
    (realtime_dir / "2026-05-10" / "scan_log_test.csv").write_text("timestamp_utc,asset,decision\n", encoding="utf-8")

    dates = discover_available_dates(
        quant_data_dir=quant_dir,
        realtime_log_dir=realtime_dir,
    )

    assert nearest_available_date("2026-05-09", dates) == "2026-05-08"
