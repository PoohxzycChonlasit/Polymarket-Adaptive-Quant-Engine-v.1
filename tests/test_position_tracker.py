from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from utils.position_tracker import Position, PositionTracker


def _make_tracker(
    account_balance: float = 10_000.0,
    max_open: int = 3,
    max_exposure: float = 0.30,
    max_drawdown: float = 0.03,
) -> PositionTracker:
    settings = MagicMock()
    settings.account_balance = account_balance
    settings.max_open_positions = max_open
    settings.max_total_exposure = max_exposure
    settings.max_daily_drawdown = max_drawdown
    settings.default_take_profit_pct = 0.03
    return PositionTracker(settings=settings)


def _open(tracker: PositionTracker, symbol: str = "BTC/USDT", side: str = "BUY",
           price: float = 65000.0, size: float = 0.01) -> Position:
    return tracker.open_position(
        symbol=symbol, source="crypto", side=side,
        entry_price=price, size=size,
        stop_loss=price * 0.98, take_profit=price * 1.03,
        order_id="ord-test",
    )


class CanOpenTests(unittest.TestCase):
    def test_allows_first_position(self) -> None:
        tracker = _make_tracker()
        ok, reason = tracker.can_open(notional_size=500.0)
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    def test_blocks_when_max_positions_reached(self) -> None:
        tracker = _make_tracker(max_open=2)
        _open(tracker)
        _open(tracker)
        ok, reason = tracker.can_open(notional_size=100.0)
        self.assertFalse(ok)
        self.assertIn("Max open positions", reason)

    def test_blocks_when_exposure_exceeded(self) -> None:
        tracker = _make_tracker(account_balance=1_000.0, max_exposure=0.30)
        # notional > 30% of 1000
        ok, reason = tracker.can_open(notional_size=400.0)
        self.assertFalse(ok)
        self.assertIn("exposure", reason.lower())

    def test_blocks_when_daily_drawdown_hit(self) -> None:
        tracker = _make_tracker(account_balance=10_000.0, max_drawdown=0.03)
        # Simulate -5% daily loss
        tracker._daily_realized_pnl = -500.0
        tracker._peak_equity = 10_000.0
        ok, reason = tracker.can_open(notional_size=100.0)
        self.assertFalse(ok)
        self.assertIn("drawdown", reason.lower())


class OpenCloseTests(unittest.TestCase):
    def test_open_position_is_tracked(self) -> None:
        tracker = _make_tracker()
        pos = _open(tracker)
        self.assertEqual(len(tracker.open_positions()), 1)
        self.assertEqual(pos.status, "open")
        self.assertAlmostEqual(pos.notional_size, 65000.0 * 0.01)

    def test_close_position_calculates_buy_profit(self) -> None:
        tracker = _make_tracker()
        pos = _open(tracker, price=65000.0, size=0.01)
        closed = tracker.close_position(pos.position_id, exit_price=66000.0)
        self.assertIsNotNone(closed)
        self.assertAlmostEqual(closed.realized_pnl, 10.0)  # (66000-65000)*0.01
        self.assertEqual(closed.status, "closed")
        self.assertEqual(len(tracker.open_positions()), 0)

    def test_close_position_calculates_sell_loss(self) -> None:
        tracker = _make_tracker()
        pos = _open(tracker, side="SELL", price=65000.0, size=0.01)
        closed = tracker.close_position(pos.position_id, exit_price=66000.0)
        self.assertAlmostEqual(closed.realized_pnl, -10.0)  # short, price went up

    def test_close_unknown_position_returns_none(self) -> None:
        tracker = _make_tracker()
        result = tracker.close_position("nonexistent-id", exit_price=65000.0)
        self.assertIsNone(result)

    def test_daily_pnl_updated_on_close(self) -> None:
        tracker = _make_tracker()
        pos = _open(tracker, price=65000.0, size=0.01)
        tracker.close_position(pos.position_id, exit_price=65500.0)
        self.assertAlmostEqual(tracker._daily_realized_pnl, 5.0)


class UpdatePriceTests(unittest.TestCase):
    def test_unrealized_pnl_updates_for_buy(self) -> None:
        tracker = _make_tracker()
        pos = _open(tracker, price=65000.0, size=0.01)
        tracker.update_price("BTC/USDT", 65500.0)
        updated = tracker.get_position(pos.position_id)
        self.assertAlmostEqual(updated.unrealized_pnl, 5.0)

    def test_unrealized_pnl_updates_for_sell(self) -> None:
        tracker = _make_tracker()
        pos = _open(tracker, side="SELL", price=65000.0, size=0.01)
        tracker.update_price("BTC/USDT", 64000.0)
        updated = tracker.get_position(pos.position_id)
        self.assertAlmostEqual(updated.unrealized_pnl, 10.0)

    def test_stop_loss_triggers_auto_close(self) -> None:
        tracker = _make_tracker()
        pos = _open(tracker, price=65000.0, size=0.01)  # sl = 63700
        triggered = tracker.update_price("BTC/USDT", 63000.0)
        self.assertEqual(len(triggered), 1)
        closed = tracker.get_position(pos.position_id)
        self.assertEqual(closed.status, "stopped_out")

    def test_take_profit_triggers_auto_close(self) -> None:
        tracker = _make_tracker()
        pos = _open(tracker, price=65000.0, size=0.01)  # tp = 66950
        triggered = tracker.update_price("BTC/USDT", 67000.0)
        self.assertEqual(len(triggered), 1)
        closed = tracker.get_position(pos.position_id)
        self.assertEqual(closed.status, "take_profit_hit")

    def test_no_trigger_within_sl_tp_range(self) -> None:
        tracker = _make_tracker()
        _open(tracker, price=65000.0, size=0.01)
        triggered = tracker.update_price("BTC/USDT", 65200.0)
        self.assertEqual(len(triggered), 0)

    def test_ignores_different_symbol(self) -> None:
        tracker = _make_tracker()
        pos = _open(tracker, symbol="BTC/USDT", price=65000.0, size=0.01)
        tracker.update_price("ETH/USDT", 63000.0)
        updated = tracker.get_position(pos.position_id)
        self.assertEqual(updated.status, "open")


class SummaryTests(unittest.TestCase):
    def test_summary_reflects_open_positions(self) -> None:
        tracker = _make_tracker(account_balance=10_000.0)
        _open(tracker, price=65000.0, size=0.01)  # notional = 650
        summary = tracker.summary()
        self.assertEqual(summary.open_count, 1)
        self.assertAlmostEqual(summary.total_exposure, 650.0)
        self.assertAlmostEqual(summary.total_exposure_pct, 0.065)

    def test_summary_no_positions(self) -> None:
        tracker = _make_tracker()
        summary = tracker.summary()
        self.assertEqual(summary.open_count, 0)
        self.assertEqual(summary.total_exposure, 0.0)
        self.assertEqual(summary.daily_drawdown_pct, 0.0)


class PersistenceTests(unittest.TestCase):
    def test_save_and_load_state(self) -> None:
        tracker = _make_tracker()
        pos = _open(tracker, price=65000.0, size=0.01)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.json"
            tracker.save_state(path)
            self.assertTrue(path.exists())

            tracker2 = _make_tracker()
            tracker2.load_state(path)
            loaded = tracker2.get_position(pos.position_id)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.symbol, "BTC/USDT")
            self.assertEqual(loaded.status, "open")

    def test_load_missing_file_is_safe(self) -> None:
        tracker = _make_tracker()
        tracker.load_state(Path("/nonexistent/path/state.json"))
        self.assertEqual(len(tracker.open_positions()), 0)


if __name__ == "__main__":
    unittest.main()
