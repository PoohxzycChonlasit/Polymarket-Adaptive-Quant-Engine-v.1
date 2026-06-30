from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from polymarket.client import OrderReceipt, OrderbookSnapshot
from polymarket.gamma_fetcher import GammaMarket
from polymarket.order_manager import PolymarketOrderManager
from polymarket.trader import BankrollState, PolymarketTrader
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
        "execution_entry_cutoff_seconds": 45,
        "execution_force_exit_seconds": 25,
        "exit_agent_entry_cutoff_seconds": 45,
        "exit_agent_cancel_entries_seconds": 35,
        "exit_agent_force_exit_seconds": 25,
        "exit_agent_residual_sweep_seconds": 15,
        "exit_agent_emergency_flatten_seconds": 10,
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
    trader.bankroll_state = BankrollState(
        starting_bankroll=trader.settings.account_balance,
        current_cash_balance=trader.settings.account_balance,
    )
    trader.client = MagicMock()
    return trader


def _market() -> GammaMarket:
    return GammaMarket(
        market_id="pm-5m-btc",
        question="Will BTC close above PTB?",
        volume=1000.0,
        liquidity=1000.0,
        end_date_iso="",
    )


def _ptb(seconds_remaining: int | None):
    values = {
        "is_above_ptb": True,
        "price_to_beat": 100.0,
        "current_price": 101.0,
        "price_diff_pct": 0.01,
        "epoch_start_ts": 123,
        "last_updated": 1000.0,
        "feed_age_seconds": 1.0,
    }
    if seconds_remaining is not None:
        values["seconds_remaining"] = seconds_remaining
    return SimpleNamespace(**values)


def _strong_runner_state():
    return SimpleNamespace(
        is_above_ptb=True,
        price_to_beat=100.0,
        current_price=120.0,
    )


def _open_position(trader: PolymarketTrader, token_id: str = "yes-token"):
    return trader.tracker.open_position(
        symbol="pm-5m-btc",
        source="polymarket",
        side="BUY",
        entry_price=0.50,
        size=10.0,
        stop_loss=0.46,
        take_profit=0.60,
        order_id="entry-1",
        metadata={"token_id": token_id, "outcome": "YES"},
    )


class ExitAgentTests(unittest.TestCase):
    def test_no_new_entries_after_t45_seconds(self) -> None:
        trader = _trader()
        trader.ptb_tracker = MagicMock()
        trader.ptb_tracker.get_market_ptb.return_value = _ptb(44)

        with patch("polymarket.trader.compute_realtime_signal") as signal_mock:
            outcome = trader._analyze_market(_market())

        self.assertTrue(outcome.skipped)
        self.assertIn("Entry cutoff", outcome.skip_reason)
        trader.client.get_orderbook.assert_not_called()
        signal_mock.assert_not_called()

    def test_passive_entry_orders_cancel_at_t35_seconds(self) -> None:
        trader = _trader(_settings(paper_trading=False))
        trader.ptb_tracker = MagicMock()
        trader.ptb_tracker.get_market_ptb.return_value = _ptb(35)
        trader.client.get_open_orders.return_value = [
            {"order_id": "entry-1", "side": "BUY", "market_id": "pm-5m-btc"},
        ]
        trader.client.cancel_order.return_value = True

        outcome = trader._analyze_market(_market())

        self.assertTrue(outcome.skipped)
        trader.client.cancel_order.assert_called_once_with("entry-1")

    def test_force_exit_triggers_at_t25_seconds(self) -> None:
        trader = _trader()
        _open_position(trader)
        trader.ptb_tracker = MagicMock()
        trader.ptb_tracker.get_market_ptb.return_value = _ptb(25)
        trader.client.get_orderbook.return_value = OrderbookSnapshot("yes-token", 0.54, 0.56, 0.02, 10, 10)

        trader._manage_open_positions_for_cycle()

        self.assertEqual(trader.tracker.open_positions(), [])
        self.assertEqual(trader.tracker.closed_positions()[0].exit_reason, "forced_exit")

    def test_pre_close_exit_refreshes_bot_status_snapshot(self) -> None:
        trader = _trader()
        _open_position(trader)
        trader.client.get_orderbook.return_value = OrderbookSnapshot("yes-token", 0.54, 0.56, 0.02, 10, 10)

        with tempfile.TemporaryDirectory() as tmp_dir:
            previous_cwd = os.getcwd()
            try:
                os.chdir(tmp_dir)
                Path("runtime").mkdir()
                trader.update_dashboard_status(25)
                before_status = json.loads(Path("runtime/bot_status.json").read_text())
                self.assertEqual(len(before_status["open_positions"]), 1)

                trader.enforce_pre_close_exits(25)

                after_status = json.loads(Path("runtime/bot_status.json").read_text())
                self.assertEqual(trader.tracker.open_positions(), [])
                self.assertEqual(after_status["open_positions"], [])
                self.assertEqual(after_status["current_countdown"], 25)
            finally:
                os.chdir(previous_cwd)

    def test_residual_sweep_triggers_at_t15_seconds(self) -> None:
        trader = _trader()
        _open_position(trader)
        trader.ptb_tracker = MagicMock()
        trader.ptb_tracker.get_market_ptb.return_value = _ptb(15)
        trader.client.get_orderbook.return_value = OrderbookSnapshot("yes-token", 0.53, 0.56, 0.03, 10, 10)

        trader._manage_open_positions_for_cycle()

        self.assertEqual(trader.tracker.open_positions(), [])
        self.assertEqual(trader.tracker.closed_positions()[0].exit_reason, "residual_sweep")

    def test_emergency_flatten_triggers_at_t10_seconds(self) -> None:
        trader = _trader()
        _open_position(trader)
        trader.ptb_tracker = MagicMock()
        trader.ptb_tracker.get_market_ptb.return_value = _ptb(10)
        trader.client.get_orderbook.return_value = OrderbookSnapshot("yes-token", 0.51, 0.56, 0.05, 10, 10)

        trader._manage_open_positions_for_cycle()

        self.assertEqual(trader.tracker.open_positions(), [])
        self.assertEqual(trader.tracker.closed_positions()[0].exit_reason, "emergency_flatten")

    def test_missing_close_time_blocks_new_entries(self) -> None:
        trader = _trader()
        trader.ptb_tracker = MagicMock()
        trader.ptb_tracker.get_market_ptb.return_value = _ptb(None)

        with patch("polymarket.trader.compute_realtime_signal") as signal_mock:
            outcome = trader._analyze_market(_market())

        self.assertTrue(outcome.skipped)
        self.assertEqual(outcome.skip_reason, "missing_close_time")
        trader.client.get_orderbook.assert_not_called()
        signal_mock.assert_not_called()

    def test_live_mode_cannot_bypass_force_exit(self) -> None:
        trader = _trader(_settings(paper_trading=False))
        _open_position(trader)
        trader.ptb_tracker = MagicMock()
        trader.ptb_tracker.get_market_ptb.return_value = _ptb(25)
        trader.client.get_orderbook.return_value = OrderbookSnapshot("yes-token", 0.54, 0.56, 0.02, 10, 10)
        trader._submit_order = MagicMock(return_value=OrderReceipt(
            order_id="close-1",
            status="filled",
            token_id="yes-token",
            side="SELL",
            price=0.54,
            size=10.0,
            filled_size=10.0,
            remaining_size=0.0,
        ))

        trader._manage_open_positions_for_cycle()

        trader._submit_order.assert_called_once()
        self.assertEqual(trader.tracker.open_positions(), [])
        self.assertEqual(trader.tracker.closed_positions()[0].exit_reason, "forced_exit")

    def test_tp1_partial_reduces_position_once_and_updates_paper_cash(self) -> None:
        trader = _trader(_settings(let_profit_run=False))
        pos = _open_position(trader)
        trader._paper_record_trade(pos.entry_price * pos.size)
        trader.ptb_tracker = MagicMock()
        trader.ptb_tracker.get_state.return_value = _strong_runner_state()
        trader.client.get_orderbook.return_value = OrderbookSnapshot("yes-token", 0.53, 0.54, 0.01, 10, 10)

        trader.check_take_profit(countdown=120)
        trader.check_take_profit(countdown=120)

        open_pos = trader.tracker.open_positions()
        self.assertEqual(len(open_pos), 1)
        self.assertAlmostEqual(open_pos[0].size, 5.0)
        self.assertTrue(open_pos[0].metadata["tp1_taken"])
        self.assertEqual(trader.paper_stats.paper_orders_created, 1)
        self.assertAlmostEqual(trader.bankroll_state.current_cash_balance, 97.65)
        self.assertAlmostEqual(trader.paper_stats.simulated_pnl, 0.15)

    def test_tp2_runner_sells_down_to_small_leftover(self) -> None:
        trader = _trader(_settings(let_profit_run=True, let_profit_run_min_seconds=60))
        pos = _open_position(trader)
        trader._paper_record_trade(pos.entry_price * pos.size)
        trader.ptb_tracker = MagicMock()
        trader.ptb_tracker.get_state.return_value = _strong_runner_state()
        trader.client.get_orderbook.return_value = OrderbookSnapshot("yes-token", 0.57, 0.58, 0.01, 10, 10)

        trader.check_take_profit(countdown=120)
        trader.check_take_profit(countdown=120)

        open_pos = trader.tracker.open_positions()
        self.assertEqual(len(open_pos), 1)
        self.assertAlmostEqual(open_pos[0].size, 2.5)
        self.assertTrue(open_pos[0].metadata["tp1_taken"])
        self.assertTrue(open_pos[0].metadata["tp2_taken"])
        self.assertTrue(open_pos[0].metadata["runner_active"])
        self.assertEqual(trader.paper_stats.paper_orders_created, 2)
        self.assertAlmostEqual(trader.paper_stats.simulated_pnl, 0.525)
        self.assertAlmostEqual(trader.bankroll_state.current_cash_balance, 99.275)

        trader.check_take_profit(countdown=120)
        self.assertEqual(trader.paper_stats.paper_orders_created, 2)
        self.assertAlmostEqual(trader.tracker.open_positions()[0].size, 2.5)

    def test_tp2_full_exit_when_runner_disabled(self) -> None:
        trader = _trader(_settings(let_profit_run=False))
        pos = _open_position(trader)
        trader._paper_record_trade(pos.entry_price * pos.size)
        trader.ptb_tracker = MagicMock()
        trader.ptb_tracker.get_state.return_value = _strong_runner_state()
        trader.client.get_orderbook.return_value = OrderbookSnapshot("yes-token", 0.57, 0.58, 0.01, 10, 10)

        trader.check_take_profit(countdown=120)
        trader.check_take_profit(countdown=120)

        self.assertEqual(trader.tracker.open_positions(), [])
        self.assertEqual(trader.tracker.closed_positions()[0].exit_reason, "take_profit_full")
        self.assertEqual(trader.paper_stats.paper_orders_created, 2)
        self.assertAlmostEqual(trader.paper_stats.simulated_pnl, 0.7)
        self.assertAlmostEqual(trader.bankroll_state.current_cash_balance, 100.7)

    def test_runner_leftover_still_obeys_forced_exit_agent(self) -> None:
        trader = _trader(_settings(let_profit_run=True, execution_force_exit_seconds=25))
        pos = _open_position(trader)
        pos.size = 2.5
        pos.notional_size = pos.entry_price * pos.size
        pos.metadata.update({
            "tp_original_size": 10.0,
            "tp1_taken": True,
            "tp2_taken": True,
            "runner_active": True,
        })
        trader._partial_tp_taken.add(pos.position_id)
        trader.ptb_tracker = MagicMock()
        trader.ptb_tracker.get_state.return_value = _strong_runner_state()
        trader.client.get_orderbook.return_value = OrderbookSnapshot("yes-token", 0.57, 0.58, 0.01, 10, 10)

        trader.check_take_profit(countdown=10)

        self.assertEqual(trader.tracker.open_positions(), [])
        self.assertEqual(trader.tracker.closed_positions()[0].exit_reason, "emergency_flatten")


if __name__ == "__main__":
    unittest.main()
