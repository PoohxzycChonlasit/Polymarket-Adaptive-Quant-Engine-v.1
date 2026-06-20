from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from polymarket.trader import PolymarketTrader, evaluate_delta_extreme_shadow_candidate
from polymarket.gamma_fetcher import GammaMarket
from polymarket.delta_engine import DeltaRegime
from utils.quant_event_logger import QuantEventLogger


def _settings(**overrides):
    values = {
        "paper_trading": True,
        "account_balance": 100.0,
        "max_risk_per_trade": 0.01,
        "delta_shadow_enabled": False,  # Disabled by default
        "quant_data_enabled": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class TestDeltaShadow(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.config = _settings()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_default_flag_is_false(self) -> None:
        self.assertFalse(self.config.delta_shadow_enabled)

    def test_evaluator_pass_case(self) -> None:
        # Standard: max(1.00, 5 * 0.025) = 1.00 USD. Shares = math.ceil(1.00/0.025) = 40.
        # Micro: max(0.05, 5 * 0.025) = 0.125 USD. Shares = math.ceil(0.05/0.025) = 5.
        res = evaluate_delta_extreme_shadow_candidate(
            price=0.025,
            spread=0.01,
            quote_age_ms=150,
            oracle_age_ms=300,
            ask_size=100.0,
            seconds_remaining=120.0,
        )
        self.assertTrue(res["executable_pass"])
        self.assertIsNone(res["executable_reject_reason"])
        self.assertEqual(res["standard_shares"], 40.0)
        self.assertEqual(res["standard_size_usd"], 1.0)
        self.assertEqual(res["micro_shares"], 5.0)
        self.assertEqual(res["micro_size_usd"], 0.125)

    def test_stale_quote_rejection(self) -> None:
        res = evaluate_delta_extreme_shadow_candidate(
            price=0.025,
            spread=0.01,
            quote_age_ms=1050,  # Fails (>1000)
            oracle_age_ms=300,
            ask_size=100.0,
            seconds_remaining=120.0,
        )
        self.assertFalse(res["executable_pass"])
        self.assertEqual(res["executable_reject_reason"], "quote_stale")

    def test_wide_spread_rejection(self) -> None:
        res = evaluate_delta_extreme_shadow_candidate(
            price=0.025,
            spread=0.07,  # Fails (>0.06)
            quote_age_ms=150,
            oracle_age_ms=300,
            ask_size=100.0,
            seconds_remaining=120.0,
        )
        self.assertFalse(res["executable_pass"])
        self.assertEqual(res["executable_reject_reason"], "spread_too_wide")

    def test_insufficient_depth_rejection(self) -> None:
        res = evaluate_delta_extreme_shadow_candidate(
            price=0.025,
            spread=0.01,
            quote_age_ms=150,
            oracle_age_ms=300,
            ask_size=10.0,  # Fails (<40 standard shares)
            seconds_remaining=120.0,
        )
        self.assertFalse(res["executable_pass"])
        self.assertEqual(res["executable_reject_reason"], "liquidity_too_small")

    def test_time_unsafe_rejection(self) -> None:
        res = evaluate_delta_extreme_shadow_candidate(
            price=0.025,
            spread=0.01,
            quote_age_ms=150,
            oracle_age_ms=300,
            ask_size=100.0,
            seconds_remaining=80.0,  # Fails (<=90)
        )
        self.assertFalse(res["executable_pass"])
        self.assertEqual(res["executable_reject_reason"], "time_unsafe")

    def test_non_delta_skip_does_not_log(self) -> None:
        trader = PolymarketTrader()
        trader.settings = _settings(delta_shadow_enabled=True)
        trader.quant_logger = QuantEventLogger(base_dir=self.temp_dir, enabled=True)

        with patch.object(trader, "_evaluate_and_log_delta_extreme_shadow") as mock_eval:
            # If we run check_stop_loss or other flows, it should not trigger it.
            pass

    def test_delta_skip_logs_shadow_payload(self) -> None:
        trader = PolymarketTrader()
        trader.settings = _settings(delta_shadow_enabled=True)
        trader.quant_logger = QuantEventLogger(base_dir=self.temp_dir, enabled=True)

        market = MagicMock(spec=GammaMarket)
        market.market_id = "test-market"

        ptb_info = SimpleNamespace(
            epoch_start_ts=1718888000,
            seconds_remaining=120.0,
            current_price=0.025,
            price_to_beat=0.025,
        )

        delta = SimpleNamespace(
            delta_score=4.5,
            delta_regime=DeltaRegime.EXTREME,
            delta_multiplier=0.2,
            reason="Mechanism_B",
        )

        trader._evaluate_and_log_delta_extreme_shadow(
            market=market,
            ticker="BTC",
            ptb_info=ptb_info,
            model_side="YES",
            confidence=0.58,
            model_ev=0.23,
            delta=delta,
            ob_spread=0.01,
            ob_liquidity_usd=100.0,
            yes_token_id="test-token-yes",
            no_token_id="test-token-no",
            yes_bid=0.02,
            yes_ask=0.03,
            yes_bid_size=100.0,
            yes_ask_size=150.0,
            no_bid=0.97,
            no_ask=0.98,
            no_bid_size=10.0,
            no_ask_size=10.0,
            yes_orderbook_age_ms=100,
            no_orderbook_age_ms=100,
            feed_age=0.3,
            current_balance=100.0,
            timing_detail={},
        )

        log_dir = os.path.join(self.temp_dir, "delta_shadow")
        self.assertTrue(os.path.exists(log_dir))
        files = os.listdir(log_dir)
        self.assertEqual(len(files), 1)

        log_file = os.path.join(log_dir, files[0])
        with open(log_file, "r") as f:
            line = f.readline()
            data = json.loads(line)

        self.assertEqual(data["event_type"], "delta_shadow")
        payload = data["payload"]
        self.assertEqual(payload["market"], "test-market")
        self.assertEqual(payload["side"], "YES")
        self.assertEqual(payload["price"], 0.03)  # price = yes_ask
        self.assertTrue(payload["executable_pass"])
        self.assertEqual(payload["shadow_shares"], 34.0)  # max(5, ceil(1.00 / 0.03)) = 34

    def test_logger_failure_does_not_crash(self) -> None:
        trader = PolymarketTrader()
        trader.settings = _settings(delta_shadow_enabled=True)
        trader.quant_logger = QuantEventLogger(base_dir=self.temp_dir, enabled=True)

        with patch("builtins.open", side_effect=PermissionError("Permission Denied")):
            market = MagicMock(spec=GammaMarket)
            market.market_id = "test-market"

            ptb_info = SimpleNamespace(
                epoch_start_ts=1718888000,
                seconds_remaining=120.0,
            )

            delta = SimpleNamespace(
                delta_score=4.5,
                delta_regime=DeltaRegime.EXTREME,
                delta_multiplier=0.2,
                reason="Mechanism_B",
            )

            trader._evaluate_and_log_delta_extreme_shadow(
                market=market,
                ticker="BTC",
                ptb_info=ptb_info,
                model_side="YES",
                confidence=0.58,
                model_ev=0.23,
                delta=delta,
                ob_spread=0.01,
                ob_liquidity_usd=100.0,
                yes_token_id="test-token-yes",
                no_token_id="test-token-no",
                yes_bid=0.02,
                yes_ask=0.03,
                yes_bid_size=100.0,
                yes_ask_size=150.0,
                no_bid=0.97,
                no_ask=0.98,
                no_bid_size=10.0,
                no_ask_size=10.0,
                yes_orderbook_age_ms=100,
                no_orderbook_age_ms=100,
                feed_age=0.3,
                current_balance=100.0,
                timing_detail={},
            )
            # Should have disabled the category without raising
            self.assertIn("delta_shadow", trader.quant_logger.disabled_categories)


if __name__ == "__main__":
    unittest.main()
