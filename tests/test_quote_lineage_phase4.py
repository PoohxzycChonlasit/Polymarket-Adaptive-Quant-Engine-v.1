from __future__ import annotations

import hashlib
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
    trader._last_orderbook_refresh_token_pair_key = {}
    trader._successful_yes_no_book_token_pair_key = {}
    trader._last_orderbook_refresh_count = {}
    trader._last_orderbook_refresh_monotonic = {}
    trader._last_successful_yes_no_book_token_pair_key = {}
    trader._last_orderbook_refresh_source = {}
    trader._last_quote_lineage_context = {}
    return trader, collector


def _trader_with_quote_context(
    ticker: str = "BTC",
    market_id: str = "pm-5m-btc",
    token_pair_key: str = "btc-yes-no-pair",
    quote_capture_ts: str = "2026-05-22T06:00:00.123456Z",
    quote_source: str = "clob_orderbook_rest",
) -> tuple[PolymarketTrader, _CollectingQuantLogger]:
    trader, collector = _trader()
    tk = ticker.upper()
    trader._last_successful_yes_no_book_at_utc[tk] = quote_capture_ts
    trader._last_successful_yes_no_book_token_pair_key[tk] = token_pair_key
    trader._last_orderbook_refresh_source[tk] = quote_source
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


def _expected_lineage_id(market_id: str, token_pair_key: str, quote_capture_ts: str) -> str:
    ts_second = quote_capture_ts.split(".")[0].rstrip("Z") + "Z"
    h = hashlib.sha1(f"{market_id}|{token_pair_key}|{ts_second}".encode()).hexdigest()[:12]
    return f"ql_{h}"


def _get_paper_fill(collector: _CollectingQuantLogger) -> dict:
    fills = [p for event, p in collector.events if event == "execution" and p.get("event") == "paper_fill"]
    assert fills, "No paper_fill event emitted"
    return fills[-1]


def _get_submit(collector: _CollectingQuantLogger) -> dict:
    submits = [p for event, p in collector.events if event == "execution" and p.get("event") == "order_submit_attempt"]
    assert submits, "No order_submit_attempt event emitted"
    return submits[-1]


# ── Phase 4 tests ─────────────────────────────────────────────────────────────

def test_quote_lineage_id_generated_when_context_present() -> None:
    """quote_lineage_id is a ql_-prefixed string when quote context exists."""
    trader, _ = _trader_with_quote_context()
    ctx = trader._phase4_build_quote_lineage("pm-5m-btc", "BTC")

    assert ctx.get("quote_lineage_id") is not None
    assert str(ctx["quote_lineage_id"]).startswith("ql_")
    assert len(ctx["quote_lineage_id"]) == 15  # "ql_" + 12 hex chars


def test_quote_lineage_id_is_deterministic() -> None:
    """Same inputs always produce the same quote_lineage_id."""
    trader, _ = _trader_with_quote_context()
    ctx1 = trader._phase4_build_quote_lineage("pm-5m-btc", "BTC")
    ctx2 = trader._phase4_build_quote_lineage("pm-5m-btc", "BTC")
    assert ctx1["quote_lineage_id"] == ctx2["quote_lineage_id"]


def test_quote_lineage_id_matches_expected_hash() -> None:
    """quote_lineage_id value matches the contracted SHA-1 formula."""
    market_id = "pm-5m-btc"
    token_pair_key = "btc-yes-no-pair"
    quote_capture_ts = "2026-05-22T06:00:00.123456Z"
    trader, _ = _trader_with_quote_context(
        market_id=market_id, token_pair_key=token_pair_key, quote_capture_ts=quote_capture_ts
    )
    ctx = trader._phase4_build_quote_lineage(market_id, "BTC")
    expected = _expected_lineage_id(market_id, token_pair_key, quote_capture_ts)
    assert ctx["quote_lineage_id"] == expected


def test_quote_capture_ts_propagated_from_instance_state() -> None:
    """quote_capture_ts matches the stored orderbook timestamp."""
    quote_ts = "2026-05-22T06:00:00.123456Z"
    trader, _ = _trader_with_quote_context(quote_capture_ts=quote_ts)
    ctx = trader._phase4_build_quote_lineage("pm-5m-btc", "BTC")
    assert ctx["quote_capture_ts"] == quote_ts


def test_quote_source_propagated() -> None:
    """quote_source is carried from the orderbook refresh source."""
    trader, _ = _trader_with_quote_context(quote_source="clob_orderbook_rest")
    ctx = trader._phase4_build_quote_lineage("pm-5m-btc", "BTC")
    assert ctx["quote_source"] == "clob_orderbook_rest"


def test_quote_snapshot_id_uses_qs_prefix() -> None:
    """quote_snapshot_id is a qs_-prefixed string matching the same hash as quote_lineage_id."""
    trader, _ = _trader_with_quote_context()
    ctx = trader._phase4_build_quote_lineage("pm-5m-btc", "BTC")
    assert ctx["quote_snapshot_id"] is not None
    assert str(ctx["quote_snapshot_id"]).startswith("qs_")
    # Same hash body as quote_lineage_id
    assert ctx["quote_snapshot_id"][3:] == ctx["quote_lineage_id"][3:]


def test_missing_quote_context_returns_null_ids() -> None:
    """When no successful orderbook exists, quote_lineage_id and quote_snapshot_id are None."""
    trader, _ = _trader()  # no quote context seeded
    ctx = trader._phase4_build_quote_lineage("pm-5m-btc", "BTC")
    assert ctx.get("quote_lineage_id") is None
    assert ctx.get("quote_snapshot_id") is None
    assert ctx.get("quote_capture_ts") is None


def test_missing_context_carry_fails_soft() -> None:
    """_phase4_quote_lineage_carry returns empty dict when no context is stored."""
    trader, _ = _trader()
    result = trader._phase4_quote_lineage_carry("BTC")
    assert isinstance(result, dict)
    assert result.get("quote_lineage_id") is None


def test_paper_fill_carries_quote_lineage_id() -> None:
    """paper_fill event carries quote_lineage_id when quote context exists."""
    trader, collector = _trader_with_quote_context()

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

    fill = _get_paper_fill(collector)
    assert "quote_lineage_id" in fill
    assert fill["quote_lineage_id"] is not None
    assert str(fill["quote_lineage_id"]).startswith("ql_")


def test_paper_fill_carries_quote_capture_ts() -> None:
    """paper_fill event carries quote_capture_ts when quote context exists."""
    quote_ts = "2026-05-22T06:00:00.123456Z"
    trader, collector = _trader_with_quote_context(quote_capture_ts=quote_ts)

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

    fill = _get_paper_fill(collector)
    assert fill.get("quote_capture_ts") == quote_ts


def test_submit_attempt_carries_quote_lineage_id() -> None:
    """order_submit_attempt carries quote_lineage_id when context present."""
    trader, collector = _trader_with_quote_context()

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

    submit = _get_submit(collector)
    assert submit.get("quote_lineage_id") is not None
    assert str(submit["quote_lineage_id"]).startswith("ql_")


def test_quote_lineage_consistent_across_submit_and_fill() -> None:
    """quote_lineage_id is identical on order_submit_attempt and paper_fill."""
    trader, collector = _trader_with_quote_context()

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

    submit = _get_submit(collector)
    fill = _get_paper_fill(collector)
    assert submit["quote_lineage_id"] == fill["quote_lineage_id"]
    assert submit.get("quote_capture_ts") == fill.get("quote_capture_ts")


def test_paper_fill_without_quote_context_emits_null_lineage_id() -> None:
    """paper_fill emits even when quote context is absent; quote_lineage_id is None."""
    trader, collector = _trader()  # no quote context

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

    fill = _get_paper_fill(collector)
    assert fill.get("quote_lineage_id") is None  # null, not missing key entirely or crash


def test_phase1_to_phase3_fields_still_present_with_phase4() -> None:
    """Phase 1–3 timestamp and metric fields remain intact after Phase 4 additions."""
    trader, collector = _trader_with_quote_context()

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

    fill = _get_paper_fill(collector)
    # Phase 1+2 labels
    assert fill["timestamp_source"] == "paper_fill_emit"
    assert fill["latency_truth_level"] == "paper_simulated"
    assert fill["ack_source"] == "paper_simulated"
    assert fill["fill_source"] == "paper_simulated"
    assert "order_ack_ts" in fill
    assert "fill_ts" in fill
    # Phase 3 derived metrics
    assert "submit_to_ack_ms" in fill
    assert "submit_to_fill_ms" in fill
    assert fill["derived_metric_source"] == "paper_proxy"
    # Phase 4 lineage (present when context seeded)
    assert "quote_lineage_id" in fill
    assert "quote_capture_ts" in fill
    assert "quote_source" in fill
    # signal_to_submit_ms not yet computed
    assert "signal_to_submit_ms" not in fill
    # quote age metrics not yet computed
    assert "quote_age_at_submit_ms" not in fill
    assert "quote_age_at_fill_ms" not in fill
    assert "quote_stale_ms" not in fill
