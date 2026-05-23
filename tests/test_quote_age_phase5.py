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


# ── Phase 5 tests ─────────────────────────────────────────────────────────────

def test_paper_fill_emits_quote_age_at_fill_ms_when_context_present() -> None:
    """quote_age_at_fill_ms is a non-negative float on paper_fill when quote context exists."""
    trader, collector = _trader()
    _seed_quote(trader)
    _submit(trader)

    fill = _get_fill(collector)
    assert "quote_age_at_fill_ms" in fill
    v = fill["quote_age_at_fill_ms"]
    assert isinstance(v, float), f"expected float, got {type(v)}"
    assert v >= 0.0, f"expected non-negative, got {v}"


def test_submit_attempt_emits_quote_age_at_submit_ms_when_context_present() -> None:
    """quote_age_at_submit_ms is a non-negative float on order_submit_attempt when quote context exists."""
    trader, collector = _trader()
    _seed_quote(trader)
    _submit(trader)

    sub = _get_submit_event(collector)
    assert "quote_age_at_submit_ms" in sub
    v = sub["quote_age_at_submit_ms"]
    assert isinstance(v, float), f"expected float, got {type(v)}"
    assert v >= 0.0, f"expected non-negative, got {v}"


def test_quote_age_at_fill_ms_is_null_when_quote_capture_ts_missing() -> None:
    """quote_age_at_fill_ms is None when no quote context exists."""
    trader, collector = _trader()
    # no _seed_quote — no quote_capture_ts
    _submit(trader)

    fill = _get_fill(collector)
    assert fill.get("quote_age_at_fill_ms") is None


def test_quote_age_at_submit_ms_is_null_when_quote_capture_ts_missing() -> None:
    """quote_age_at_submit_ms is None when no quote context exists."""
    trader, collector = _trader()
    _submit(trader)

    sub = _get_submit_event(collector)
    assert sub.get("quote_age_at_submit_ms") is None


def test_quote_age_at_fill_ge_quote_age_at_submit() -> None:
    """quote_age_at_fill_ms >= quote_age_at_submit_ms (fill always after submit)."""
    trader, collector = _trader()
    _seed_quote(trader)
    _submit(trader)

    sub = _get_submit_event(collector)
    fill = _get_fill(collector)
    age_submit = sub.get("quote_age_at_submit_ms")
    age_fill = fill.get("quote_age_at_fill_ms")
    assert age_submit is not None and age_fill is not None
    assert age_fill >= age_submit, f"fill age {age_fill} < submit age {age_submit}"


def test_live_path_does_not_emit_quote_age_at_submit_ms() -> None:
    """Live order_submit path must not carry quote_age_at_submit_ms."""
    trader, collector = _trader(paper=False)
    _seed_quote(trader)

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
    _submit(trader)

    submits = [p for _, p in collector.events if p.get("event") == "order_submit_attempt"]
    for s in submits:
        assert s.get("quote_age_at_submit_ms") is None, "live path must not emit quote_age_at_submit_ms"

    fills = [p for _, p in collector.events if p.get("event") == "paper_fill"]
    assert not fills, "paper_fill must not fire on live path"


def test_phase1_to_phase4_fields_intact_alongside_phase5() -> None:
    """All Phase 1–4 fields remain present alongside Phase 5 additions."""
    trader, collector = _trader()
    _seed_quote(trader)
    _submit(trader)

    fill = _get_fill(collector)
    # Phase 1+2 labels
    assert fill["timestamp_source"] == "paper_fill_emit"
    assert fill["latency_truth_level"] == "paper_simulated"
    assert "order_ack_ts" in fill
    assert "fill_ts" in fill
    # Phase 3 derived metrics
    assert isinstance(fill.get("submit_to_ack_ms"), float)
    assert isinstance(fill.get("submit_to_fill_ms"), float)
    assert fill["derived_metric_source"] == "paper_proxy"
    # Phase 4 lineage
    assert fill.get("quote_lineage_id") is not None
    assert fill.get("quote_capture_ts") is not None
    assert "quote_source" in fill
    # Phase 5 age metrics
    assert isinstance(fill.get("quote_age_at_fill_ms"), float)
    assert fill.get("quote_age_at_fill_ms") >= 0.0
