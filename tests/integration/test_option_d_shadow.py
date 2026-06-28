from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from polymarket.client import OrderbookSnapshot
from polymarket.trader import PolymarketTrader, evaluate_option_d_shadow
from utils.position_tracker import Position, PositionTracker
from utils.quant_event_logger import QuantEventLogger


def _settings(**overrides):
    values = {
        "paper_trading": True,
        "account_balance": 100.0,
        "max_risk_per_trade": 0.01,
        "default_stop_loss_pct": 0.08,
        "default_take_profit_pct": 0.15,
        "execution_stop_loss_pct": 0.08,
        "option_d_shadow_enabled": False,  # Disabled by default
        "sl_activation_delay_seconds": 30.0,
        "sl_emergency_stop_pct": 0.30,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _position(hold_seconds: int = 15, entry_price: float = 0.50, **overrides) -> Position:
    entry_time = (datetime.now(UTC) - timedelta(seconds=hold_seconds)).isoformat().replace("+00:00", "Z")
    values = {
        "position_id": "pos-test",
        "symbol": "pm-5m-btc",
        "source": "polymarket",
        "side": "BUY",
        "entry_price": entry_price,
        "entry_time": entry_time,
        "size": 10.0,
        "notional_size": 5.0,
        "stop_loss": entry_price * 0.92,
        "take_profit": entry_price * 1.15,
        "order_id": "entry-test",
        "status": "open",
        "metadata": {"token_id": "test-token", "outcome": "NO"},
    }
    values.update(overrides)
    return Position(**values)


class TestOptionDShadow(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.config = _settings()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_disabled_by_default(self) -> None:
        # Verify default configuration is False
        self.assertFalse(self.config.option_d_shadow_enabled)

        # Setup mock trader with disabled Option D
        trader = PolymarketTrader()
        trader.settings = self.config
        trader.tracker = PositionTracker(settings=trader.settings)
        trader.quant_events = QuantEventLogger(base_dir=self.temp_dir, enabled=True)
        
        pos = trader.tracker.open_position(
            symbol="pm-5m-btc",
            source="polymarket",
            side="BUY",
            entry_price=0.50,
            size=10.0,
            stop_loss=0.46,
            take_profit=0.60,
            order_id="entry-1",
            metadata={"token_id": "test-token", "outcome": "NO"},
        )
        
        trader.client = MagicMock()
        ob = OrderbookSnapshot(
            token_id="test-token",
            best_bid=0.40,
            best_ask=0.42,
            spread=0.02,
            bid_size=15.0,
            ask_size=15.0,
        )
        trader.client.get_orderbook.return_value = ob

        # Verify that calling check_stop_loss executes but does not write Option D logs
        # because settings.option_d_shadow_enabled is False.
        with patch("polymarket.trader.evaluate_option_d_shadow") as mock_eval:
            trader.check_stop_loss(0)
            mock_eval.assert_not_called()

    def test_no_call_to_close_position_from_evaluator(self) -> None:
        # The evaluator must be a pure function and should never execute exit orders
        pos = _position(hold_seconds=40)
        ob = OrderbookSnapshot(
            token_id="test-token",
            best_bid=0.30,  # 40% loss
            best_ask=0.32,
            spread=0.02,
            bid_size=15.0,
            ask_size=15.0,
        )
        config = _settings(option_d_shadow_enabled=True)
        
        # Evaluate should return would_stop = True but does not close the position
        payload = evaluate_option_d_shadow(pos, ob, datetime.now(UTC), config)
        self.assertTrue(payload["option_d_would_stop"])

    def test_delay_window_suppresses_normal_stop(self) -> None:
        # Hold time = 10s (inside 30s delay window)
        # Entry price = 0.50, Mid = 0.40 (20% loss, breaches 8% SL)
        pos = _position(hold_seconds=10, entry_price=0.50)
        ob = OrderbookSnapshot(
            token_id="test-token",
            best_bid=0.39,
            best_ask=0.41,
            spread=0.02,
            bid_size=15.0,
            ask_size=15.0,
        )
        config = _settings(option_d_shadow_enabled=True)
        
        payload = evaluate_option_d_shadow(pos, ob, datetime.now(UTC), config)
        self.assertTrue(payload["delay_active"])
        self.assertFalse(payload["option_d_would_stop"])
        self.assertTrue(payload["option_d_would_hold"])
        self.assertEqual(payload["three_sample_count"], 0)

    def test_emergency_stop_marks_would_stop(self) -> None:
        # Hold time = 10s (inside 30s delay window)
        # Mid = 0.30 (40% loss, breaches 30% emergency SL)
        pos = _position(hold_seconds=10, entry_price=0.50)
        ob = OrderbookSnapshot(
            token_id="test-token",
            best_bid=0.29,
            best_ask=0.31,
            spread=0.02,
            bid_size=15.0,
            ask_size=15.0,
        )
        config = _settings(option_d_shadow_enabled=True)
        
        payload = evaluate_option_d_shadow(pos, ob, datetime.now(UTC), config)
        self.assertTrue(payload["delay_active"])
        self.assertTrue(payload["emergency_stop_trigger"])
        self.assertTrue(payload["option_d_would_stop"])

    def test_depth_gate_blocks_confirmation(self) -> None:
        # Hold time = 40s (outside delay window)
        # Mid = 0.40 (20% loss, breaches 8% SL)
        # Bid size = 5.0 (below 10 contracts threshold -> depth gate fails)
        pos = _position(hold_seconds=40, entry_price=0.50)
        ob = OrderbookSnapshot(
            token_id="test-token",
            best_bid=0.39,
            best_ask=0.41,
            spread=0.02,
            bid_size=5.0,  # Fails depth
            ask_size=15.0,
        )
        config = _settings(option_d_shadow_enabled=True)
        
        # Iteration 1
        payload = evaluate_option_d_shadow(pos, ob, datetime.now(UTC), config)
        self.assertFalse(payload["depth_gate_pass"])
        self.assertEqual(payload["three_sample_count"], 0)
        self.assertFalse(payload["three_sample_pass"])

    def test_three_sample_confirmation_requires_3_breaches(self) -> None:
        pos = _position(hold_seconds=40, entry_price=0.50)
        # Mid breaches 8% SL, depth is OK
        ob = OrderbookSnapshot(
            token_id="test-token",
            best_bid=0.39,
            best_ask=0.41,
            spread=0.02,
            bid_size=12.0,
            ask_size=15.0,
        )
        config = _settings(option_d_shadow_enabled=True)
        
        # Sample 1
        payload = evaluate_option_d_shadow(pos, ob, datetime.now(UTC), config)
        self.assertEqual(payload["three_sample_count"], 1)
        self.assertFalse(payload["three_sample_pass"])
        self.assertFalse(payload["option_d_would_stop"])

        # Sample 2
        payload = evaluate_option_d_shadow(pos, ob, datetime.now(UTC), config)
        self.assertEqual(payload["three_sample_count"], 2)
        self.assertFalse(payload["three_sample_pass"])
        self.assertFalse(payload["option_d_would_stop"])

        # Sample 3
        payload = evaluate_option_d_shadow(pos, ob, datetime.now(UTC), config)
        self.assertEqual(payload["three_sample_count"], 3)
        self.assertTrue(payload["three_sample_pass"])
        self.assertTrue(payload["option_d_would_stop"])

    def test_malformed_orderbook_does_not_crash(self) -> None:
        pos = _position(hold_seconds=40, entry_price=0.50)
        config = _settings(option_d_shadow_enabled=True)
        
        # Test with None orderbook
        payload1 = evaluate_option_d_shadow(pos, None, datetime.now(UTC), config)
        self.assertEqual(payload1["raw_bid"], 0.0)
        self.assertEqual(payload1["raw_ask"], 0.0)
        self.assertEqual(payload1["mid_price"], 0.50)  # fallbacks to entry price
        
        # Test with dict orderbook lacking fields
        payload2 = evaluate_option_d_shadow(pos, {}, datetime.now(UTC), config)
        self.assertEqual(payload2["raw_bid"], 0.0)
        self.assertEqual(payload2["raw_ask"], 0.0)
        self.assertEqual(payload2["mid_price"], 0.50)


if __name__ == "__main__":
    unittest.main()
