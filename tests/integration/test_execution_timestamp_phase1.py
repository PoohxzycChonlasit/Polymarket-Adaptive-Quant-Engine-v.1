from __future__ import annotations

import re
from types import SimpleNamespace

from polymarket.client import BUY
from polymarket.order_intent import OrderIntentType
from polymarket.risk_modes import RiskModeState
from polymarket.trader import BankrollState, PaperSessionStats, PolymarketTrader, TradeOutcome
from utils.position_tracker import PositionTracker
from utils.quant_event_logger import QuantEventLogger
from utils.risk_manager import RiskPlan


ISO_Z_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T.*Z$")


class _CollectingQuantLogger:
    def __init__(self) -> None:
        self.mode = "paper"
        self.schema_version = "test"
        self.events: list[tuple[str, dict]] = []

    def _with_candidate_trace_identity(self, payload: dict, timestamp_utc: str) -> dict:
        return QuantEventLogger(
            enabled=True,
            mode=self.mode,
            run_id="test-run",
            schema_version=self.schema_version,
        )._with_candidate_trace_identity(payload, timestamp_utc)

    def log_decision(self, payload: dict) -> bool:
        self.events.append(("decision", payload))
        return True

    def log_execution(self, payload: dict) -> bool:
        self.events.append(("execution", payload))
        return True

    def log_risk_event(self, payload: dict) -> bool:
        self.events.append(("risk", payload))
        return True


def _settings(*, paper: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        paper_trading=paper,
        dry_run=paper,
        execution_entry_cutoff_seconds=90,
        adaptive_entry_hard_block_seconds=45,
        entry_min_seconds_remaining=30,
        exit_agent_entry_cutoff_seconds=45,
        exit_agent_cancel_entries_seconds=35,
        exit_agent_force_exit_seconds=25,
        adaptive_entry_max_spread=0.06,
        hybrid_phase_v1_enabled=False,
    )


def _trader(*, paper: bool = True) -> tuple[PolymarketTrader, _CollectingQuantLogger]:
    trader = PolymarketTrader.__new__(PolymarketTrader)
    collector = _CollectingQuantLogger()
    trader.settings = _settings(paper=paper)
    trader.quant_events = collector
    trader.paper_stats = PaperSessionStats()
    trader.bankroll_state = BankrollState(starting_bankroll=100.0, current_cash_balance=100.0)
    trader.tracker = PositionTracker()
    trader.client = SimpleNamespace(place_limit_order=lambda **_kwargs: None)
    trader._risk_mode_state = RiskModeState()
    trader._observability_health_display_state = {}
    trader._last_structured_logs = {}
    trader._last_reconciliation = None
    trader._wallet_reference_balance = None
    trader._paper_wallet_reference_initialized = False
    trader._wallet_reference_source = ""
    trader._wallet_reference_error = ""
    trader._paper_virtual_reference_balance = 100.0
    trader.last_quant_details = {}
    trader._market_token_meta = {}
    trader._real_token_ids = {}
    trader._market_first_seen_seconds_remaining = {}
    trader._market_readiness_timestamps = {}
    trader._cycle_started_monotonic = 0.0
    trader._current_cycle_market_count = 0
    trader._market_evaluation_started_monotonic = {}
    trader._market_evaluation_started_at_utc = {}
    trader._current_cycle_market_sequence_index = {}
    trader._current_cycle_market_sequence_count = {}
    trader._last_scan_cycle_duration_ms = 0
    trader._last_orderbook_refresh_at_utc = {}
    trader._last_successful_yes_no_book_at_utc = {}
    trader._orderbook_refresh_token_pair_key = {}
    trader._successful_yes_no_book_token_pair_key = {}
    trader._orderbook_refresh_count = {}
    trader._last_orderbook_refresh_monotonic = {}
    return trader, collector


def _risk_plan() -> RiskPlan:
    return RiskPlan(
        account_balance=100.0,
        entry_price=0.50,
        stop_loss_price=0.42,
        take_profit_price=0.70,
        partial_tp_price=0.60,
        risk_amount=1.0,
        kelly_fraction=0.0,
        capped_fraction=0.01,
        position_size=2.0,
        notional_size=1.0,
        stop_loss_pct=0.08,
    )


def _assert_iso_z(value: object) -> None:
    assert isinstance(value, str)
    assert ISO_Z_RE.match(value)


def test_decision_payload_emits_phase1_timestamp_shape_and_proxy_provenance() -> None:
    trader, collector = _trader()
    outcome = TradeOutcome(
        market_id="pm-5m-btc",
        question="BTC up?",
        decision="skip",
        confidence=0.0,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="no_signal",
        display={"market_slug": "btc-updown-5m", "condition_id": "condition-btc", "token_id": "yes-token"},
    )

    trader._emit_decision_event(outcome, ticker="BTC")

    payload = [payload for event, payload in collector.events if event == "decision"][-1]
    _assert_iso_z(payload["decision_complete_ts"])
    _assert_iso_z(payload["signal_generated_ts"])
    assert payload["signal_generated_ts"] == payload["decision_timestamp"]
    assert payload["timestamp_source"] == "decision_emit"
    assert payload["latency_truth_level"] == "proxy"
    assert payload["decision_timestamp"]
    assert "signal_to_submit_ms" not in payload


def test_order_intent_and_submit_emit_paper_simulated_phase1_timestamps() -> None:
    trader, collector = _trader()

    receipt = trader._submit_order(
        "yes-token",
        side=BUY,
        price=0.50,
        size=2.0,
        intent_type=OrderIntentType.ENTRY,
        risk_plan=_risk_plan(),
        source_market_id="pm-5m-btc",
        outcome="YES",
    )

    assert receipt is not None
    execution_payloads = [payload for event, payload in collector.events if event == "execution"]
    intent_payload = next(payload for payload in execution_payloads if payload["event"] == "order_intent_approved")
    submit_payload = next(payload for payload in execution_payloads if payload["event"] == "order_submit_attempt")

    _assert_iso_z(intent_payload["order_intent_ts"])
    assert intent_payload["timestamp_source"] == "order_intent_approved"
    assert intent_payload["latency_truth_level"] == "paper_simulated"

    _assert_iso_z(submit_payload["order_submit_ts"])
    assert submit_payload["timestamp_source"] == "order_submit_attempt"
    assert submit_payload["latency_truth_level"] == "paper_simulated"


def test_missing_phase1_timestamp_fields_fail_soft_through_jsonl_logger(tmp_path) -> None:
    logger = QuantEventLogger(base_dir=tmp_path, enabled=True, mode="paper", run_id="run-test")

    assert logger.log_execution({"event": "legacy_execution_event", "size": 1.0})
    assert logger.log_decision({"decision": "SKIP", "skip_reason": "legacy_payload"})


def test_phase1_does_not_emit_fake_live_submit_timestamp_label() -> None:
    trader, _collector = _trader(paper=False)

    assert trader._validate_submit_order_intent(
        market_id="yes-token",
        side=BUY,
        price=0.50,
        size=2.0,
        intent_type=OrderIntentType.ENTRY,
        risk_plan=_risk_plan(),
        source_market_id="pm-5m-btc",
        outcome="YES",
    )

    intent_payload = [
        payload
        for event, payload in trader.quant_events.events
        if event == "execution" and payload["event"] == "order_intent_approved"
    ][-1]
    assert "order_submit_ts" not in intent_payload
    assert intent_payload["latency_truth_level"] == "unknown"
