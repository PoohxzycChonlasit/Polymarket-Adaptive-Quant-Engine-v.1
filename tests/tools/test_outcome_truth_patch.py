from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

from polymarket.risk_modes import RiskModeState
from polymarket.trader import BankrollState, PaperSessionStats, PolymarketTrader
from utils.position_tracker import PositionTracker


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

    def log_trade_open(self, payload: dict) -> bool:
        self.events.append(("trade_open", payload))
        return True

    def log_trade_close(self, payload: dict) -> bool:
        self.events.append(("trade_close", payload))
        return True


def _trader() -> tuple[PolymarketTrader, _CollectingQuantLogger]:
    trader = PolymarketTrader.__new__(PolymarketTrader)
    collector = _CollectingQuantLogger()
    trader.settings = SimpleNamespace(
        paper_trading=True,
        dry_run=True,
        execution_entry_cutoff_seconds=90,
        adaptive_entry_hard_block_seconds=45,
        entry_min_seconds_remaining=30,
        exit_agent_entry_cutoff_seconds=45,
        exit_agent_cancel_entries_seconds=35,
        exit_agent_force_exit_seconds=25,
        adaptive_entry_max_spread=0.06,
        hybrid_phase_v1_enabled=False,
    )
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


@dataclass
class _FakePosition:
    position_id: str = "pos-test-001"
    symbol: str = "pm-5m-btc"
    entry_price: float = 0.55
    entry_time: str = "2026-05-22T08:00:00Z"
    size: float = 0.1
    notional_size: float = 0.055
    metadata: dict = field(default_factory=lambda: {
        "condition_id": "0xabc123",
        "epoch_start_ts": 1779372600,
        "outcome": "YES",
    })


def _get_close(collector: _CollectingQuantLogger) -> dict:
    closes = [p for _, p in collector.events if _ == "trade_close"]
    assert closes, "No trade_close emitted"
    return closes[-1]


def _emit_close(
    trader: PolymarketTrader,
    *,
    reason: str,
    exit_price: float,
    pnl: float,
    entry_price: float = 0.55,
) -> dict:
    pos = _FakePosition(entry_price=entry_price)
    trader._emit_trade_closed_event(
        position=pos,
        reason=reason,
        exit_price=exit_price,
        size=pos.size,
        pnl=pnl,
        receipt=None,
        partial=False,
    )
    _, collector = trader, trader.quant_events  # type: ignore[assignment]
    return _get_close(collector)  # type: ignore[arg-type]


# ── Outcome truth tests ───────────────────────────────────────────────────────

def test_trade_result_tp_from_take_profit_reason() -> None:
    """reason=take_profit → trade_result=TP."""
    trader, collector = _trader()
    pos = _FakePosition()
    trader._emit_trade_closed_event(
        position=pos, reason="take_profit", exit_price=0.70,
        size=pos.size, pnl=0.015, receipt=None,
    )
    close = _get_close(collector)
    assert close["trade_result"] == "TP"


def test_trade_result_tp_from_take_profit_target_reached() -> None:
    """reason=take_profit_target_reached → trade_result=TP."""
    trader, collector = _trader()
    pos = _FakePosition()
    trader._emit_trade_closed_event(
        position=pos, reason="take_profit_target_reached", exit_price=0.70,
        size=pos.size, pnl=0.015, receipt=None,
    )
    close = _get_close(collector)
    assert close["trade_result"] == "TP"


def test_trade_result_tp_from_take_profit_full() -> None:
    """reason=take_profit_full → trade_result=TP."""
    trader, collector = _trader()
    pos = _FakePosition()
    trader._emit_trade_closed_event(
        position=pos, reason="take_profit_full", exit_price=0.70,
        size=pos.size, pnl=0.015, receipt=None,
    )
    close = _get_close(collector)
    assert close["trade_result"] == "TP"


def test_trade_result_sl_from_stop_loss_reason() -> None:
    """reason=stop_loss → trade_result=SL."""
    trader, collector = _trader()
    pos = _FakePosition()
    trader._emit_trade_closed_event(
        position=pos, reason="stop_loss", exit_price=0.34,
        size=pos.size, pnl=-0.021, receipt=None,
    )
    close = _get_close(collector)
    assert close["trade_result"] == "SL"


def test_trade_result_sl_from_stop_loss_hit() -> None:
    """reason=stop_loss_hit → trade_result=SL."""
    trader, collector = _trader()
    pos = _FakePosition()
    trader._emit_trade_closed_event(
        position=pos, reason="stop_loss_hit", exit_price=0.42,
        size=pos.size, pnl=-0.013, receipt=None,
    )
    close = _get_close(collector)
    assert close["trade_result"] == "SL"


def test_trade_result_win_from_positive_pnl_unknown_reason() -> None:
    """reason not TP/SL, pnl > 0 → trade_result=WIN."""
    trader, collector = _trader()
    pos = _FakePosition()
    trader._emit_trade_closed_event(
        position=pos, reason="forced_exit", exit_price=0.60,
        size=pos.size, pnl=0.005, receipt=None,
    )
    close = _get_close(collector)
    assert close["trade_result"] == "WIN"


def test_trade_result_loss_from_negative_pnl_unknown_reason() -> None:
    """reason not TP/SL, pnl < 0 → trade_result=LOSS."""
    trader, collector = _trader()
    pos = _FakePosition()
    trader._emit_trade_closed_event(
        position=pos, reason="forced_exit", exit_price=0.45,
        size=pos.size, pnl=-0.010, receipt=None,
    )
    close = _get_close(collector)
    assert close["trade_result"] == "LOSS"


def test_trade_result_unknown_when_pnl_zero_and_reason_unrecognised() -> None:
    """pnl=0 and unknown reason → trade_result=UNKNOWN."""
    trader, collector = _trader()
    pos = _FakePosition()
    trader._emit_trade_closed_event(
        position=pos, reason="residual_sweep", exit_price=0.55,
        size=pos.size, pnl=0.0, receipt=None,
    )
    close = _get_close(collector)
    assert close["trade_result"] == "UNKNOWN"


def test_pnl_usdc_equals_pnl() -> None:
    """pnl_usdc is present and equals pnl (alias, no new calculation)."""
    trader, collector = _trader()
    pos = _FakePosition()
    pnl_val = 0.012345
    trader._emit_trade_closed_event(
        position=pos, reason="take_profit", exit_price=0.67,
        size=pos.size, pnl=pnl_val, receipt=None,
    )
    close = _get_close(collector)
    assert "pnl_usdc" in close
    assert close["pnl_usdc"] == close["pnl"]
    assert close["pnl_usdc"] == pnl_val


def test_entry_price_emitted_from_position() -> None:
    """entry_price on trade_close matches position.entry_price."""
    trader, collector = _trader()
    pos = _FakePosition(entry_price=0.48)
    trader._emit_trade_closed_event(
        position=pos, reason="stop_loss", exit_price=0.34,
        size=pos.size, pnl=-0.014, receipt=None,
    )
    close = _get_close(collector)
    assert "entry_price" in close
    assert close["entry_price"] == 0.48


def test_existing_fields_intact() -> None:
    """Existing trade_close fields are unaffected by outcome truth additions."""
    trader, collector = _trader()
    pos = _FakePosition(entry_price=0.55)
    trader._emit_trade_closed_event(
        position=pos, reason="stop_loss_hit", exit_price=0.42,
        size=0.1, pnl=-0.013, receipt=None,
    )
    close = _get_close(collector)
    assert close["reason"] == "stop_loss_hit"
    assert close["exit_price"] == 0.42
    assert close["size"] == 0.1
    assert close["pnl"] == -0.013
    assert close["asset"] == "BTC"
    assert "position_id" in close
    assert "market_id" in close


def test_fail_soft_on_position_without_entry_price() -> None:
    """entry_price gracefully handles position object missing entry_price attr."""
    trader, collector = _trader()

    class _MinimalPosition:
        position_id = "min-001"
        symbol = "pm-5m-btc"
        entry_time = None
        metadata: dict = {}

    pos = _MinimalPosition()
    trader._emit_trade_closed_event(
        position=pos, reason="forced_exit", exit_price=0.50,
        size=0.1, pnl=0.0, receipt=None,
    )
    close = _get_close(collector)
    # Must not raise; trade_result and pnl_usdc still present
    assert "trade_result" in close
    assert "pnl_usdc" in close
