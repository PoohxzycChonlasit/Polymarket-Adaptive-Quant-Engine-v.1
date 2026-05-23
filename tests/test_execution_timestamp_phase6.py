from __future__ import annotations

from types import SimpleNamespace

from polymarket.client import BUY
from polymarket.order_intent import OrderIntentType
from polymarket.risk_modes import RiskModeState
from polymarket.trader import BankrollState, PaperSessionStats, PolymarketTrader
from utils.position_tracker import PositionTracker
from utils.risk_manager import RiskPlan


class _CollectingQuantLogger:
    def __init__(self) -> None:
        self.mode = "paper"
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
    trader._last_orderbook_refresh_token_pair_key = {}
    trader._successful_yes_no_book_token_pair_key = {}
    trader._last_orderbook_refresh_count = {}
    trader._last_orderbook_refresh_monotonic = {}
    trader._last_successful_yes_no_book_token_pair_key = {}
    trader._last_orderbook_refresh_source = {}
    trader._last_quote_lineage_context = {}
    return trader, collector


def _seed_quote(
    trader: PolymarketTrader,
    ticker: str = "BTC",
    quote_capture_ts: str = "2026-05-22T06:00:00.000000Z",
    token_pair_key: str = "btc-yes-no-pair",
    quote_source: str = "clob_orderbook_rest",
) -> None:
    tk = ticker.upper()
    trader._last_successful_yes_no_book_at_utc[tk] = quote_capture_ts
    trader._last_successful_yes_no_book_token_pair_key[tk] = token_pair_key
    trader._last_orderbook_refresh_source[tk] = quote_source


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


def _submit(trader: PolymarketTrader) -> None:
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


def _get_fill(collector: _CollectingQuantLogger) -> dict:
    fills = [p for _, p in collector.events if p.get("event") == "paper_fill"]
    assert fills, "No paper_fill emitted"
    return fills[-1]


def _get_submit_event(collector: _CollectingQuantLogger) -> dict:
    submits = [p for _, p in collector.events if p.get("event") == "order_submit_attempt"]
    assert submits, "No order_submit_attempt emitted"
    return submits[-1]


def test_paper_fill_emits_quote_stale_ms_as_max_quote_age() -> None:
    """quote_stale_ms is the max of submit/fill quote age on paper_fill."""
    trader, collector = _trader()
    _seed_quote(trader)
    _submit(trader)

    fill = _get_fill(collector)

    assert "quote_stale_ms" in fill
    assert isinstance(fill["quote_stale_ms"], float)
    assert fill["quote_stale_ms"] == max(
        fill["quote_age_at_submit_ms"],
        fill["quote_age_at_fill_ms"],
    )
    assert fill["derived_metric_source"] == "paper_proxy"


def test_quote_stale_ms_is_null_when_quote_age_is_missing() -> None:
    """quote_stale_ms is None when quote-age inputs are unavailable."""
    trader, collector = _trader()
    _submit(trader)

    fill = _get_fill(collector)

    assert fill.get("quote_age_at_submit_ms") is None
    assert fill.get("quote_age_at_fill_ms") is None
    assert fill.get("quote_stale_ms") is None
    assert fill["derived_metric_source"] == "paper_proxy"


def test_quote_stale_ms_is_not_added_to_submit_attempt_payload() -> None:
    """Phase 6 metric is scoped to paper_fill payload only."""
    trader, collector = _trader()
    _seed_quote(trader)
    _submit(trader)

    submit = _get_submit_event(collector)

    assert "quote_age_at_submit_ms" in submit
    assert "quote_stale_ms" not in submit
