from __future__ import annotations

import time
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from polymarket.client import OrderbookSnapshot
from polymarket.gamma_fetcher import GammaMarket
from polymarket.order_manager import PolymarketOrderManager
from polymarket.signal import SignalResult
from polymarket.trader import PolymarketTrader
from utils.position_tracker import PositionTracker


def _settings(**overrides):
    values = {
        "paper_trading": True,
        "account_balance": 100.0,
        "max_risk_per_trade": 0.01,
        "default_stop_loss_pct": 0.02,
        "default_take_profit_pct": 0.15,
        "kelly_fraction_cap": 0.25,
        "bankroll_floor": 5.0,
        "max_open_positions": 10,
        "max_total_exposure": 1.0,
        "max_daily_drawdown": 0.10,
        "execution_entry_cutoff_seconds": 90,
        "execution_force_exit_seconds": 60,
        "execution_take_profit_pct": 0.10,
        "execution_stop_loss_pct": 0.08,
        "max_feed_age_seconds": 10.0,
        "max_active_positions_per_market": 1,
        "max_entries_per_market": 1,
        "max_risk_per_market": 0.20,
        "close_order_retry_attempts": 3,
        "close_order_retry_delay_seconds": 0.0,
        "entry_min_seconds_remaining": 30,
        "min_shares_per_order": 1,
        "strategy_mom_upper": 1.0,
        "snipe_min_edge": 0.30,
        "sniper_max_entry_price": 0.45,
        "tp_partial_pct": 0.05,
        "tp_full_pct": 0.10,
        "dynamic_tp_enabled": False,
        "dynamic_tp_boost_factor": 0.5,
        "let_profit_run": False,
        "let_profit_run_min_seconds": 60,
        "panic_sell_max_slippage": 0.08,
        "panic_sell_delta_threshold": 5.0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _trader(settings=None) -> PolymarketTrader:
    trader = PolymarketTrader()
    trader.settings = settings or _settings()
    trader.tracker = PositionTracker(settings=trader.settings)
    trader.order_manager = PolymarketOrderManager(
        account_balance=trader.settings.account_balance,
        max_risk_per_trade=trader.settings.max_risk_per_trade,
        stop_loss_pct=trader.settings.default_stop_loss_pct,
        kelly_fraction_cap=trader.settings.kelly_fraction_cap,
    )
    trader.client = MagicMock()
    trader._real_token_ids["BTC"] = ("yes-token", "no-token")
    trader._market_token_meta["BTC"] = {
        "slug": "btc-updown-5m",
        "condition_id": "condition-btc",
        "yes_token_id": "yes-token",
        "no_token_id": "no-token",
    }
    return trader


def _market() -> GammaMarket:
    return GammaMarket(
        market_id="pm-5m-btc",
        question="Will BTC close above PTB?",
        volume=1000.0,
        liquidity=1000.0,
        end_date_iso="",
    )


def _ptb(age_seconds: float | None = 1.0, include_timestamp: bool = True):
    values = {
        "is_above_ptb": True,
        "price_to_beat": 100.0,
        "current_price": 101.0,
        "price_diff_pct": 0.01,
        "seconds_remaining": 200,
        "epoch_start_ts": 123,
    }
    if include_timestamp and age_seconds is not None:
        values["last_updated"] = time.time() - age_seconds
        values["feed_age_seconds"] = age_seconds
    return SimpleNamespace(**values)


class StaleFeedKillSwitchTests(unittest.TestCase):
    def test_stale_oracle_ptb_feed_skips_before_signal_and_order(self) -> None:
        trader = _trader()
        trader.ptb_tracker = MagicMock()
        trader.ptb_tracker.get_market_ptb.return_value = _ptb(age_seconds=30.0)
        trader._submit_order = MagicMock()

        with patch("polymarket.trader.compute_realtime_signal") as signal_mock:
            outcome = trader._analyze_market(_market())

        self.assertTrue(outcome.skipped)
        self.assertEqual(outcome.skip_reason, "stale_feed")
        trader.client.get_orderbook.assert_not_called()
        signal_mock.assert_not_called()
        trader._submit_order.assert_not_called()

    def test_missing_feed_timestamp_skips_before_signal_and_order(self) -> None:
        trader = _trader()
        trader.ptb_tracker = MagicMock()
        trader.ptb_tracker.get_market_ptb.return_value = _ptb(age_seconds=None, include_timestamp=False)
        trader._submit_order = MagicMock()

        with patch("polymarket.trader.compute_realtime_signal") as signal_mock:
            outcome = trader._analyze_market(_market())

        self.assertTrue(outcome.skipped)
        self.assertEqual(outcome.skip_reason, "stale_feed")
        trader.client.get_orderbook.assert_not_called()
        signal_mock.assert_not_called()
        trader._submit_order.assert_not_called()

    def test_live_mode_stale_feed_never_submits_order(self) -> None:
        trader = _trader(_settings(paper_trading=False))
        trader.ptb_tracker = MagicMock()
        trader.ptb_tracker.get_market_ptb.return_value = _ptb(age_seconds=30.0)
        trader._submit_order = MagicMock()

        outcome = trader._analyze_market(_market())

        self.assertTrue(outcome.skipped)
        self.assertEqual(outcome.skip_reason, "stale_feed")
        trader.client.get_orderbook.assert_not_called()
        trader._submit_order.assert_not_called()

    def test_fresh_feed_allows_normal_analysis_to_continue(self) -> None:
        trader = _trader()
        trader.ptb_tracker = MagicMock()
        trader.ptb_tracker.get_market_ptb.return_value = _ptb(age_seconds=1.0)
        trader.client.get_orderbook.side_effect = [
            OrderbookSnapshot("yes-token", 0.49, 0.50, 0.01, 10, 10),
            OrderbookSnapshot("no-token", 0.49, 0.50, 0.01, 10, 10),
        ]
        signal = SignalResult(
            asset="BTC",
            side="YES",
            score=0.70,
            momentum_pct=0.4,
            rsi=50,
            vol_ratio=1.0,
            skip_reason="",
            strategy="reversion",
        )

        with patch("polymarket.trader.compute_realtime_signal", return_value=signal) as signal_mock:
            outcome = trader._analyze_market(_market())

        self.assertNotEqual(outcome.skip_reason, "stale_feed")
        trader.client.get_orderbook.assert_called()
        signal_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
