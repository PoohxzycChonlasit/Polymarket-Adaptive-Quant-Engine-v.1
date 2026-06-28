from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from polymarket.client import OrderbookSnapshot
from polymarket.trader import PolymarketTrader
from utils.position_tracker import PositionTracker
from utils.quant_event_logger import QuantEventLogger


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
        "execution_take_profit_pct": 0.10,
        "execution_stop_loss_pct": 0.08,
        "panic_sell_max_slippage": 0.08,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _trader(temp_dir: str, **settings_overrides) -> PolymarketTrader:
    trader = PolymarketTrader()
    trader.settings = _settings(**settings_overrides)
    trader.tracker = PositionTracker(settings=trader.settings)
    trader.client = MagicMock()
    # Replace quant logger to write to a temp directory
    trader.quant_events = QuantEventLogger(
        base_dir=temp_dir,
        enabled=True,
        mode="paper",
        run_id="test_run",
    )
    return trader


def _read_events(temp_dir: str, category: str) -> list[dict]:
    log_dir = os.path.join(temp_dir, category)
    if not os.path.exists(log_dir):
        return []
    events: list[dict] = []
    for log_name in os.listdir(log_dir):
        with open(os.path.join(log_dir, log_name), "r") as handle:
            events.extend(json.loads(line) for line in handle if line.strip())
    return events


def _open_position(trader: PolymarketTrader, position_id: str, symbol: str, entry_price: float, side: str = "BUY"):
    return trader.tracker.open_position(
        symbol=symbol,
        source="polymarket",
        side=side,
        entry_price=entry_price,
        size=10.0,
        stop_loss=0.46,
        take_profit=0.60,
        order_id="entry-1",
        metadata={"token_id": "test-token", "outcome": "NO"},
    )


class TestStopLossShadowPolicy(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_shadow_logging_and_decisions(self) -> None:
        trader = _trader(self.temp_dir)
        pos = _open_position(trader, "pos-1", "pm-5m-btc", 0.50)

        # Mock orderbook where raw bid drops (should breach 8%), but midpoint doesn't breach 8%
        # Entry price: 0.50. 8% stop loss threshold = 0.46
        # Raw bid: 0.45 (10% loss -> breaches)
        # Raw ask: 0.53
        # Midpoint: (0.45 + 0.53)/2 = 0.49 (2% loss -> hold)
        # Bid size: 12.0, Ask size: 15.0 (depth_ok = True)
        ob = OrderbookSnapshot(
            token_id="test-token",
            best_bid=0.45,
            best_ask=0.53,
            spread=0.08,
            bid_size=12.0,
            ask_size=15.0,
        )
        trader.client.get_orderbook.return_value = ob

        # Run check_stop_loss (first tick)
        trader.check_stop_loss(countdown=10)

        # PATCH_STOP_002: paper mode requires shadow_mid_3sample_stop to fire.
        # Mid price (0.49) only shows 2% loss vs 8% threshold -> shadow_mid_stop=False.
        # Paper policy suppresses the stop on tick 1.
        open_positions = trader.tracker.open_positions()
        self.assertEqual(len(open_positions), 1)  # Position held by paper policy

        # 2. Check the logged shadow event
        log_dir = os.path.join(self.temp_dir, "stop_loss_shadow")
        self.assertTrue(os.path.exists(log_dir))
        log_files = os.listdir(log_dir)
        self.assertEqual(len(log_files), 1)

        log_file_path = os.path.join(log_dir, log_files[0])
        with open(log_file_path, "r") as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 1)
            event = json.loads(lines[0])

            self.assertEqual(event["event_type"], "stop_loss_shadow")
            payload = event["payload"]
            self.assertEqual(payload["position_id"], pos.position_id)
            self.assertEqual(payload["market"], "pm-5m-btc")
            self.assertEqual(payload["ticker"], "BTC")
            self.assertEqual(payload["side"], "NO")
            self.assertEqual(payload["raw_bid"], 0.45)
            self.assertEqual(payload["raw_ask"], 0.53)
            self.assertEqual(payload["midpoint"], 0.49)
            self.assertTrue(payload["depth_ok"])
            self.assertAlmostEqual(payload["unrealized_raw_bid_pct"], -0.10)
            self.assertAlmostEqual(payload["unrealized_mid_pct"], -0.02)
            self.assertEqual(payload["actual_raw_bid_stop"], True)
            self.assertEqual(payload["shadow_mid_stop"], False)
            self.assertEqual(payload["shadow_mid_depth_stop"], False)
            # Since it's the 1st tick of breach, consecutive_raw_breach_count is 1
            self.assertEqual(payload["consecutive_raw_breach_count"], 1)
            self.assertEqual(payload["consecutive_mid_breach_count"], 0)
            # decisions for multi-sample are false
            self.assertEqual(payload["shadow_raw_2sample_stop"], False)
            self.assertEqual(payload["shadow_raw_3sample_stop"], False)
            self.assertEqual(payload["shadow_mid_3sample_stop"], False)
            # PATCH_STOP_002: paper-gated stop telemetry
            self.assertEqual(payload["paper_stop_policy_active"], True)
            self.assertEqual(payload["paper_mid_confirmed_stop"], False)
            self.assertEqual(payload["paper_stop_suppressed"], True)
            self.assertEqual(payload["paper_stop_suppression_reason"], "mid_not_breached")
            self.assertEqual(payload["actual_stop_triggered"], False)
            # PAPER_STOP_FAILSAFE: OB was available, no freeze
            self.assertEqual(payload["orderbook_unavailable_consecutive_count"], 0)
            self.assertEqual(payload["ob_freeze_active"], False)
            self.assertEqual(payload["ob_freeze_hold_reason"], "")

    def test_temporal_confirmation_counters(self) -> None:
        trader = _trader(self.temp_dir)
        pos = _open_position(trader, "pos-1", "pm-5m-btc", 0.50)

        # Mock orderbook where raw bid breaches stop loss, but midpoint also breaches
        # Raw bid: 0.45 (breach), Raw ask: 0.45 (breach)
        ob = OrderbookSnapshot(
            token_id="test-token",
            best_bid=0.45,
            best_ask=0.45,
            spread=0.0,
            bid_size=12.0,
            ask_size=15.0,
        )
        trader.client.get_orderbook.return_value = ob

        # To prevent actual stop from closing the position on the first check,
        # we temporarily patch _close_position_with_retry to do nothing (hold the position).
        # This allows us to check consecutive ticks.
        with patch.object(trader, "_close_position_with_retry") as mock_close:
            # Check 1
            trader.check_stop_loss(countdown=10)
            self.assertEqual(trader._consecutive_raw_breach_seconds[pos.position_id], 1)
            self.assertEqual(trader._consecutive_mid_breach_seconds[pos.position_id], 1)

            # Check 2
            trader.check_stop_loss(countdown=10)
            self.assertEqual(trader._consecutive_raw_breach_seconds[pos.position_id], 2)
            self.assertEqual(trader._consecutive_mid_breach_seconds[pos.position_id], 2)

            # Check 3
            trader.check_stop_loss(countdown=10)
            self.assertEqual(trader._consecutive_raw_breach_seconds[pos.position_id], 3)
            self.assertEqual(trader._consecutive_mid_breach_seconds[pos.position_id], 3)

        # Let's inspect the log entries for 2-sample and 3-sample stops
        log_dir = os.path.join(self.temp_dir, "stop_loss_shadow")
        log_files = os.listdir(log_dir)
        log_file_path = os.path.join(log_dir, log_files[0])
        import json
        events = []
        with open(log_file_path, "r") as f:
            for line in f:
                events.append(json.loads(line))

        self.assertEqual(len(events), 3)
        # Event 1: no multi-sample stops true
        self.assertEqual(events[0]["payload"]["shadow_raw_2sample_stop"], False)
        self.assertEqual(events[0]["payload"]["shadow_raw_3sample_stop"], False)
        # PATCH_STOP_002 fields present
        self.assertIn("paper_stop_policy_active", events[0]["payload"])
        self.assertIn("paper_stop_suppressed", events[0]["payload"])
        self.assertIn("actual_stop_triggered", events[0]["payload"])
        self.assertIn("orderbook_unavailable_consecutive_count", events[0]["payload"])

        # Event 2: 2-sample stop becomes true
        self.assertEqual(events[1]["payload"]["shadow_raw_2sample_stop"], True)
        self.assertEqual(events[1]["payload"]["shadow_raw_3sample_stop"], False)

        # Event 3: 3-sample stop becomes true
        self.assertEqual(events[2]["payload"]["shadow_raw_2sample_stop"], True)
        self.assertEqual(events[2]["payload"]["shadow_raw_3sample_stop"], True)
        self.assertEqual(events[2]["payload"]["shadow_mid_3sample_stop"], True)
        # PATCH_STOP_002: with paper mode and shadow_mid_3sample_stop=True, stop fires
        self.assertEqual(events[2]["payload"]["actual_stop_triggered"], True)
        self.assertEqual(events[2]["payload"]["paper_mid_confirmed_stop"], True)
        self.assertEqual(events[2]["payload"]["paper_stop_suppressed"], False)
        mock_close.assert_called_once()
        self.assertEqual(mock_close.call_args.kwargs["reason"], "stop_loss")

    def test_live_mode_raw_bid_stop_behavior_is_unchanged(self) -> None:
        trader = _trader(self.temp_dir, paper_trading=False)
        _open_position(trader, "pos-live", "pm-5m-btc", 0.50)
        trader.client.get_orderbook.return_value = OrderbookSnapshot(
            token_id="test-token",
            best_bid=0.45,
            best_ask=0.53,
            spread=0.08,
            bid_size=12.0,
            ask_size=15.0,
        )

        with patch.object(trader, "_close_position_with_retry") as mock_close:
            trader.check_stop_loss(countdown=10)

        mock_close.assert_called_once()
        self.assertEqual(mock_close.call_args.kwargs["reason"], "stop_loss")
        payload = _read_events(self.temp_dir, "stop_loss_shadow")[0]["payload"]
        self.assertEqual(payload["actual_raw_bid_stop"], True)
        self.assertEqual(payload["shadow_mid_3sample_stop"], False)
        self.assertEqual(payload["actual_stop_triggered"], True)
        self.assertEqual(payload["paper_stop_policy_active"], False)

    def test_orderbook_unavailable_counter_increments_and_resets(self) -> None:
        trader = _trader(self.temp_dir)
        pos = _open_position(trader, "pos-ob", "pm-5m-btc", 0.50)
        recovery_ob = OrderbookSnapshot(
            token_id="test-token",
            best_bid=0.50,
            best_ask=0.52,
            spread=0.02,
            bid_size=12.0,
            ask_size=15.0,
        )
        trader.client.get_orderbook.side_effect = [
            RuntimeError("orderbook down"),
            RuntimeError("orderbook down"),
            recovery_ob,
            recovery_ob,
        ]

        trader.check_stop_loss(countdown=10)
        self.assertEqual(trader._consecutive_ob_unavailable_seconds[pos.position_id], 1)

        trader.check_stop_loss(countdown=10)
        self.assertEqual(trader._consecutive_ob_unavailable_seconds[pos.position_id], 0)

        payloads = [event["payload"] for event in _read_events(self.temp_dir, "stop_loss_shadow")]
        self.assertEqual(payloads[0]["orderbook_unavailable_consecutive_count"], 1)
        self.assertEqual(payloads[0]["ob_freeze_active"], True)
        self.assertEqual(payloads[1]["orderbook_unavailable_consecutive_count"], 0)
        self.assertEqual(payloads[1]["ob_freeze_active"], False)

    def test_orderbook_unavailable_five_cycles_emits_critical_observability_event(self) -> None:
        trader = _trader(self.temp_dir)
        pos = _open_position(trader, "pos-critical", "pm-5m-btc", 0.50)
        trader.client.get_orderbook.side_effect = RuntimeError("orderbook down")

        for _ in range(5):
            trader.check_stop_loss(countdown=10)

        shadow_payload = _read_events(self.temp_dir, "stop_loss_shadow")[-1]["payload"]
        self.assertEqual(shadow_payload["orderbook_unavailable_consecutive_count"], 5)
        health_events = _read_events(self.temp_dir, "system_health")
        critical_events = [
            event["payload"]
            for event in health_events
            if event["payload"].get("event") == "stop_loss_orderbook_unavailable_critical"
        ]
        self.assertEqual(len(critical_events), 1)
        self.assertEqual(critical_events[0]["position_id"], pos.position_id)
        self.assertEqual(critical_events[0]["severity"], "critical")
        self.assertEqual(critical_events[0]["orderbook_unavailable_consecutive_count"], 5)
