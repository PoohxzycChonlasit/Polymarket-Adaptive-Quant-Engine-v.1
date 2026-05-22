from __future__ import annotations

from types import SimpleNamespace

from polymarket.client import BUY
from polymarket.order_intent import OrderIntentType
from polymarket.risk_modes import RiskModeState
from polymarket.trader import BankrollState, PaperSessionStats, PolymarketTrader, TradeOutcome
from utils.position_tracker import PositionTracker
from utils.risk_manager import RiskPlan


class _CollectingQuantLogger:
    def __init__(self) -> None:
        self.mode = "paper"
        self.schema_version = "test"
        self.events: list[tuple[str, dict]] = []

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


def _get_paper_fill_payload(collector: _CollectingQuantLogger) -> dict:
    fills = [p for event, p in collector.events if event == "execution" and p.get("event") == "paper_fill"]
    assert fills, "No paper_fill event emitted"
    return fills[-1]


# ── Phase 3 tests ─────────────────────────────────────────────────────────────

def test_paper_fill_emits_submit_to_ack_ms() -> None:
    """submit_to_ack_ms must be a non-negative float on paper_fill."""
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
    assert "submit_to_ack_ms" in payload, "submit_to_ack_ms missing from paper_fill"
    value = payload["submit_to_ack_ms"]
    assert isinstance(value, float), f"submit_to_ack_ms must be float, got {type(value)}"
    assert value >= 0.0, f"submit_to_ack_ms must be non-negative, got {value}"


def test_paper_fill_emits_submit_to_fill_ms() -> None:
    """submit_to_fill_ms must be a non-negative float on paper_fill."""
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
    assert "submit_to_fill_ms" in payload, "submit_to_fill_ms missing from paper_fill"
    value = payload["submit_to_fill_ms"]
    assert isinstance(value, float), f"submit_to_fill_ms must be float, got {type(value)}"
    assert value >= 0.0, f"submit_to_fill_ms must be non-negative, got {value}"


def test_phase3_metrics_fail_soft_on_missing_or_invalid_fields() -> None:
    """_phase3_paper_proxy_ms must return None for missing or malformed timestamps."""
    trader, _ = _trader(paper=True)

    assert trader._phase3_paper_proxy_ms("", "") is None
    assert trader._phase3_paper_proxy_ms("not-a-timestamp", "2026-05-22T05:00:00Z") is None
    assert trader._phase3_paper_proxy_ms("2026-05-22T05:00:00Z", "not-a-timestamp") is None
    assert trader._phase3_paper_proxy_ms(None, "2026-05-22T05:00:00Z") is None  # type: ignore[arg-type]
    assert trader._phase3_paper_proxy_ms("2026-05-22T05:00:00Z", None) is None  # type: ignore[arg-type]


def test_paper_fill_labels_preserved_alongside_phase3_metrics() -> None:
    """Phase 1+2 provenance labels must still be present when Phase 3 fields are added."""
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
    assert payload["latency_truth_level"] == "paper_simulated"
    assert payload["ack_source"] == "paper_simulated"
    assert payload["fill_source"] == "paper_simulated"
    assert payload["derived_metric_source"] == "paper_proxy"
    assert "submit_to_ack_ms" in payload
    assert "submit_to_fill_ms" in payload


def test_live_path_does_not_emit_phase3_derived_metrics() -> None:
    """Live order_submit path must not carry submit_to_ack_ms or submit_to_fill_ms."""
    trader, collector = _trader(paper=False)

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
    for p in live_payloads:
        assert "submit_to_ack_ms" not in p, "live path must not emit submit_to_ack_ms"
        assert "submit_to_fill_ms" not in p, "live path must not emit submit_to_fill_ms"
        assert "derived_metric_source" not in p, "live path must not emit derived_metric_source"

    paper_fills = [p for event, p in collector.events if event == "execution" and p.get("event") == "paper_fill"]
    assert not paper_fills, "paper_fill must not fire on live path"
