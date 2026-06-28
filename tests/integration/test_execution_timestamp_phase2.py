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
    assert ISO_Z_RE.match(value), f"Not ISO-8601 UTC Z: {value!r}"


def _get_paper_fill_payload(collector: _CollectingQuantLogger) -> dict:
    fills = [p for event, p in collector.events if event == "execution" and p.get("event") == "paper_fill"]
    assert fills, "No paper_fill event emitted"
    return fills[-1]


# ── Phase 2 core tests ────────────────────────────────────────────────────────

def test_paper_fill_emits_order_ack_ts_with_paper_simulated_label() -> None:
    trader, collector = _trader(paper=True)

    trader._submit_order(
        "yes-token",
        side=BUY,
        price=0.50,
        size=2.0,
        intent_type=OrderIntentType.ENTRY,
        risk_plan=_risk_plan(),
        source_market_id="pm-5m-btc",
        outcome="YES",
    )

    payload = _get_paper_fill_payload(collector)
    _assert_iso_z(payload["order_ack_ts"])
    assert payload["ack_source"] == "paper_simulated"
    assert payload["latency_truth_level"] == "paper_simulated"


def test_paper_fill_emits_fill_ts_with_paper_simulated_label() -> None:
    trader, collector = _trader(paper=True)

    trader._submit_order(
        "yes-token",
        side=BUY,
        price=0.50,
        size=2.0,
        intent_type=OrderIntentType.ENTRY,
        risk_plan=_risk_plan(),
        source_market_id="pm-5m-btc",
        outcome="YES",
    )

    payload = _get_paper_fill_payload(collector)
    _assert_iso_z(payload["fill_ts"])
    assert payload["fill_source"] == "paper_simulated"
    assert payload["latency_truth_level"] == "paper_simulated"


def test_paper_fill_timestamp_source_is_paper_fill_emit() -> None:
    trader, collector = _trader(paper=True)

    trader._submit_order(
        "yes-token",
        side=BUY,
        price=0.50,
        size=2.0,
        intent_type=OrderIntentType.ENTRY,
        risk_plan=_risk_plan(),
        source_market_id="pm-5m-btc",
        outcome="YES",
    )

    payload = _get_paper_fill_payload(collector)
    assert payload["timestamp_source"] == "paper_fill_emit"


def test_paper_fill_order_ack_ts_not_after_fill_ts() -> None:
    """order_ack_ts must not be later than fill_ts (ack before fill in paper)."""
    trader, collector = _trader(paper=True)

    trader._submit_order(
        "yes-token",
        side=BUY,
        price=0.50,
        size=2.0,
        intent_type=OrderIntentType.ENTRY,
        risk_plan=_risk_plan(),
        source_market_id="pm-5m-btc",
        outcome="YES",
    )

    payload = _get_paper_fill_payload(collector)
    assert payload["order_ack_ts"] <= payload["fill_ts"]


def test_live_path_does_not_emit_paper_simulated_ack_or_fill_timestamps() -> None:
    """Live order_submit path must not emit paper_simulated ack/fill fields."""
    trader, collector = _trader(paper=False)

    # Patch client.place_limit_order to return a minimal receipt-like object
    from dataclasses import dataclass

    @dataclass
    class _FakeReceipt:
        order_id: str = "live-abc"
        status: str = "live"
        token_id: str = "yes-token"
        price: float = 0.50
        size: float = 2.0
        side: str = BUY
        filled_size: float = 0.0
        remaining_size: float = 2.0
        created_at: str = "2026-05-22T00:00:00"
        order_type: str = "GTC"

    trader.client = SimpleNamespace(place_limit_order=lambda **_kwargs: _FakeReceipt())
    trader._reconcile_after_order_attempt = lambda: None  # type: ignore[method-assign]

    trader._submit_order(
        "yes-token",
        side=BUY,
        price=0.50,
        size=2.0,
        intent_type=OrderIntentType.ENTRY,
        risk_plan=_risk_plan(),
        source_market_id="pm-5m-btc",
        outcome="YES",
    )

    live_payloads = [
        p for event, p in collector.events
        if event == "execution" and p.get("event") == "live_order_submitted"
    ]
    # If live_order_submitted fired, it must not carry paper_simulated labels
    for p in live_payloads:
        assert p.get("ack_source") != "paper_simulated", "live path must not fake paper_simulated ack"
        assert p.get("fill_source") != "paper_simulated", "live path must not fake paper_simulated fill"
        assert p.get("latency_truth_level") != "paper_simulated", "live path must not carry paper_simulated label"

    # Confirm no paper_fill event fired on live path
    paper_fills = [p for event, p in collector.events if event == "execution" and p.get("event") == "paper_fill"]
    assert not paper_fills, "paper_fill must not fire on live path"


def test_missing_phase2_fields_fail_soft_through_jsonl_logger(tmp_path) -> None:
    """Legacy payloads without Phase 2 fields must still parse without error."""
    logger = QuantEventLogger(base_dir=tmp_path, enabled=True, mode="paper", run_id="run-p2-test")
    assert logger.log_execution({"event": "paper_fill", "intent": "ENTRY", "size": 1.0})
    assert logger.log_execution({"event": "paper_fill", "intent": "ENTRY"})


# ── Phase 1 fields still present ─────────────────────────────────────────────

def test_phase1_fields_still_present_alongside_phase2() -> None:
    """Phase 1 timestamps must still be emitted when Phase 2 fields are added."""
    trader, collector = _trader(paper=True)

    trader._submit_order(
        "yes-token",
        side=BUY,
        price=0.50,
        size=2.0,
        intent_type=OrderIntentType.ENTRY,
        risk_plan=_risk_plan(),
        source_market_id="pm-5m-btc",
        outcome="YES",
    )

    execution_payloads = [p for event, p in collector.events if event == "execution"]

    intent_payload = next(p for p in execution_payloads if p["event"] == "order_intent_approved")
    _assert_iso_z(intent_payload["order_intent_ts"])
    assert intent_payload["timestamp_source"] == "order_intent_approved"
    assert intent_payload["latency_truth_level"] == "paper_simulated"

    submit_payload = next(p for p in execution_payloads if p["event"] == "order_submit_attempt")
    _assert_iso_z(submit_payload["order_submit_ts"])
    assert submit_payload["timestamp_source"] == "order_submit_attempt"
    assert submit_payload["latency_truth_level"] == "paper_simulated"

    fill_payload = next(p for p in execution_payloads if p["event"] == "paper_fill")
    _assert_iso_z(fill_payload["order_ack_ts"])
    _assert_iso_z(fill_payload["fill_ts"])
    assert fill_payload["timestamp_source"] == "paper_fill_emit"
    assert fill_payload["latency_truth_level"] == "paper_simulated"

    # signal_to_submit_ms is not a paper_fill field (it requires a cross-log join)
    for p in execution_payloads:
        assert "signal_to_submit_ms" not in p
