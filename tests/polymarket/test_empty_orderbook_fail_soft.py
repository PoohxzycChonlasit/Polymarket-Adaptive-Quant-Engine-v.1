from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from polymarket.gamma_fetcher import GammaMarket
from polymarket.trader import PolymarketTrader


class _CollectingQuantLogger:
    def __init__(self) -> None:
        self.mode = "paper"
        self.schema_version = "test"
        self.disabled_categories: set[str] = set()
        self.events: list[tuple[str, dict]] = []

    def __getattr__(self, name: str):
        if name.startswith("log_"):
            def _log(payload: dict) -> bool:
                self.events.append((name, payload))
                return True

            return _log
        raise AttributeError(name)


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        paper_trading=True,
        dry_run=True,
        account_balance=100.0,
        bankroll_floor=5.0,
        max_risk_per_trade=0.01,
        default_stop_loss_pct=0.08,
        kelly_fraction_cap=0.25,
        execution_entry_cutoff_seconds=90,
        adaptive_entry_hard_block_seconds=45,
        entry_min_seconds_remaining=30,
        exit_agent_entry_cutoff_seconds=45,
        exit_agent_cancel_entries_seconds=35,
        exit_agent_force_exit_seconds=25,
        adaptive_entry_max_spread=0.06,
        api_retry_attempts=1,
        max_active_positions_per_market=1,
        max_entries_per_market=1,
        max_feed_age_seconds=10.0,
        enable_market_availability_guard=False,
        micro_adaptive_timing_enabled=False,
        hybrid_phase_v1_enabled=False,
    )


def _trader() -> PolymarketTrader:
    trader = PolymarketTrader()
    trader.settings = _settings()
    trader.quant_events = _CollectingQuantLogger()
    trader._real_token_ids["BTC"] = ("yes-token", "no-token")
    trader._market_token_meta["BTC"] = {
        "slug": "btc-updown-5m",
        "condition_id": "condition-btc",
        "yes_token_id": "yes-token",
        "no_token_id": "no-token",
        "epoch_start_ts": int(time.time()) - 120,
        "epoch_end_ts": int(time.time()) + 180,
    }
    return trader


def _market() -> GammaMarket:
    return GammaMarket(
        market_id="pm-5m-btc",
        question="Will BTC close above the target?",
        volume=1000.0,
        liquidity=100.0,
        end_date_iso="",
    )


def _ptb_info() -> SimpleNamespace:
    epoch_start = int(time.time()) - 120
    return SimpleNamespace(
        current_price=100000.0,
        price_to_beat=100100.0,
        price_diff_pct=-0.10,
        seconds_remaining=180,
        epoch_start_ts=epoch_start,
        epoch_end_ts=epoch_start + 300,
        last_updated=time.time(),
        feed_age_seconds=1.0,
    )


def test_empty_orderbook_fetch_failure_skips_without_unbound_orderbook_reference() -> None:
    trader = _trader()
    trader._fetch_orderbook_pair_with_empty_recovery = MagicMock(
        side_effect=RuntimeError("empty_orderbook bids=0 asks=99 token=yes-token")
    )

    outcome = trader._analyze_market_quant(_market(), "BTC", _ptb_info())

    assert outcome.skipped is True
    assert outcome.skip_reason in {"warmup_pending", "empty_book", "orderbook_unavailable"}
    assert outcome.display["orderbook_error"] == "empty_orderbook bids=0 asks=99 token=yes-token"
    assert outcome.display["orderbook_unavailable_reason"]

    snapshots = [
        payload for name, payload in trader.quant_events.events
        if name == "log_market_snapshot"
    ]
    assert snapshots
    snapshot = snapshots[-1]
    assert snapshot["orderbook_error"] == "empty_orderbook bids=0 asks=99 token=yes-token"
    assert snapshot["orderbook_unavailable_reason"]
    assert snapshot["yes_ask"] == 0.0
    assert snapshot["no_ask"] == 0.0

    execution_events = [
        payload for name, payload in trader.quant_events.events
        if name == "log_execution" and payload.get("event") == "market_analysis_exception"
    ]
    assert execution_events == []


def test_market_analysis_exception_event_serializes_context() -> None:
    trader = _trader()
    market = _market()
    trader.last_quant_details["BTC"] = {
        "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
        "orderbook_state_classification": "unavailable",
        "market_readiness_state": "token_not_ready",
        "orderbook_unavailable_reason": "empty_orderbook",
    }

    with patch.object(trader, "_select_markets", return_value=[market]), \
         patch.object(trader, "_ensure_connected", return_value=None), \
         patch.object(trader, "_analyze_market", side_effect=RuntimeError("signal failure")), \
         patch.object(trader, "update_dashboard_status", return_value=None):
        outcomes = trader.run_single_cycle(top_n=1)

    assert outcomes == []
    execution_events = [
        payload for name, payload in trader.quant_events.events
        if name == "log_execution" and payload.get("event") == "market_analysis_exception"
    ]
    assert execution_events
    payload = execution_events[-1]
    assert payload["exception_type"] == "RuntimeError"
    assert payload["exception_message"] == "signal failure"
    assert payload["ticker"] == "BTC"
    assert payload["asset"] == "BTC"
    assert payload["lifecycle_phase"] == "ACTIVE_INVENTORY_TRADING"
    assert payload["orderbook_state_classification"] == "unavailable"
    assert payload["market_readiness_state"] == "token_not_ready"
    assert payload["orderbook_unavailable_reason"] == "empty_orderbook"
