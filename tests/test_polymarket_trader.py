from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from polymarket.arbitrage import ArbitrageScanner
from polymarket.client import OrderReceipt, OrderbookSnapshot, PolymarketClient
from polymarket.gamma_fetcher import GammaMarket
from polymarket.order_intent import OrderIntentType
from polymarket.trader import PolymarketTrader, TradeOutcome
from utils.risk_manager import RiskPlan


def _make_gamma_market(market_id: str = "mkt-001", liquidity: float = 5000.0) -> GammaMarket:
    return GammaMarket(
        market_id=market_id,
        question="Will X happen?",
        volume=10000.0,
        liquidity=liquidity,
        end_date_iso="2026-12-31T00:00:00Z",
    )


def _make_risk_plan(position_size: float = 0.05) -> RiskPlan:
    return RiskPlan(
        account_balance=10_000.0,
        entry_price=0.50,
        stop_loss_price=0.49,
        take_profit_price=0.53,
        partial_tp_price=0.515,
        risk_amount=100.0,
        kelly_fraction=0.20,
        capped_fraction=0.20,
        position_size=position_size,
        notional_size=position_size * 0.50,
        stop_loss_pct=0.02,
    )


class PolymarketClientStubTests(unittest.TestCase):
    """Unit tests for PolymarketClient that do not require py-clob-client."""

    def test_connect_skips_when_paper_trading(self) -> None:
        client = PolymarketClient()
        trader = PolymarketTrader()
        # Paper trading should not call connect() on the CLOB.
        trader.settings = MagicMock()
        trader.settings.paper_trading = True
        trader.settings.account_balance = 10_000.0
        trader._ensure_connected()
        self.assertTrue(trader._connected)

    def test_place_limit_order_raises_on_invalid_side(self) -> None:
        client = PolymarketClient()
        client._client = MagicMock()
        with self.assertRaises(ValueError):
            client.place_limit_order(token_id="tok", price=0.50, size=10.0, side="HOLD")

    def test_place_limit_order_raises_on_zero_price(self) -> None:
        client = PolymarketClient()
        client._client = MagicMock()
        with self.assertRaises(ValueError):
            client.place_limit_order(token_id="tok", price=0.0, size=10.0, side="BUY")

    def test_cancel_order_returns_false_on_exception(self) -> None:
        client = PolymarketClient()
        mock_clob = MagicMock()
        mock_clob.cancel.side_effect = RuntimeError("Network error")
        client._client = mock_clob
        result = client.cancel_order("order-123")
        self.assertFalse(result)

    def test_get_orderbook_parses_dict_response_best_prices(self) -> None:
        client = PolymarketClient()
        mock_clob = MagicMock()
        mock_clob.get_order_book.return_value = {
            "bids": [
                {"price": "0.10", "size": "20"},
                {"price": "0.53", "size": "7"},
                {"price": "0.51", "size": "11"},
            ],
            "asks": [
                {"price": "0.70", "size": "4"},
                {"price": "0.55", "size": "8"},
                {"price": "0.60", "size": "9"},
            ],
        }
        client._client = mock_clob

        ob = client.get_orderbook("token-123")

        self.assertEqual(ob.best_bid, 0.53)
        self.assertEqual(ob.bid_size, 7.0)
        self.assertEqual(ob.best_ask, 0.55)
        self.assertEqual(ob.ask_size, 8.0)
        self.assertEqual(ob.spread, 0.02)


class ArbitrageScannerTests(unittest.TestCase):
    def test_scan_marks_buy_both_when_yes_no_sum_locks_profit(self) -> None:
        client = MagicMock()
        client.get_orderbook.side_effect = [
            OrderbookSnapshot("yes-token", 0.46, 0.47, 0.01, 50.0, 20.0),
            OrderbookSnapshot("no-token", 0.49, 0.50, 0.01, 40.0, 15.0),
        ]
        scanner = ArbitrageScanner(
            client,
            min_net_edge=0.005,
            min_profit_usdc=0.02,
            fee_buffer=0.002,
            slippage_buffer=0.003,
        )

        opp = scanner.scan("BTC", "yes-token", "no-token")

        self.assertTrue(opp.executable)
        self.assertEqual(opp.action, "BUY_BOTH_ARB")
        self.assertEqual(opp.opportunity_type, "BUY_BOTH_ARB")
        self.assertAlmostEqual(opp.ask_sum, 0.97)
        self.assertAlmostEqual(opp.net_edge, 0.022)
        self.assertAlmostEqual(opp.max_size, 15.0)
        self.assertAlmostEqual(opp.est_profit, 0.33)

    def test_scan_waits_when_net_edge_is_below_threshold(self) -> None:
        client = MagicMock()
        client.get_orderbook.side_effect = [
            OrderbookSnapshot("yes-token", 0.49, 0.50, 0.01, 50.0, 20.0),
            OrderbookSnapshot("no-token", 0.49, 0.50, 0.01, 40.0, 15.0),
        ]
        scanner = ArbitrageScanner(client, min_net_edge=0.005)

        opp = scanner.scan("BTC", "yes-token", "no-token")

        self.assertFalse(opp.executable)
        self.assertEqual(opp.action, "WAIT")
        self.assertEqual(opp.reason, "net_edge_below_threshold")


class PolymarketTraderPaperModeTests(unittest.TestCase):
    """Tests for PolymarketTrader in paper-trading mode (no live API calls)."""

    def _make_trader(self) -> PolymarketTrader:
        trader = PolymarketTrader()
        trader.settings = SimpleNamespace(
            paper_trading=True,
            account_balance=10_000.0,
            max_risk_per_trade=0.01,
            default_stop_loss_pct=0.02,
            kelly_fraction_cap=0.25,
            crypto_pairs=["BTC/USDT"],
            bankroll_floor=5.0,
        )
        return trader

    def test_run_single_cycle_skips_when_no_markets(self) -> None:
        trader = self._make_trader()
        with patch.object(trader, "_select_markets", return_value=[]), \
             patch.object(trader, "_ensure_connected", return_value=None), \
             patch.object(trader, "update_dashboard_status", return_value=None):
            outcomes = trader.run_single_cycle()
        self.assertEqual(outcomes, [])

    def test_run_single_cycle_returns_skipped_signal_outcome(self) -> None:
        trader = self._make_trader()
        market = _make_gamma_market()
        skipped = TradeOutcome(
            market_id=market.market_id, question=market.question,
            decision="skip", confidence=0.0, risk_plan=None, receipt=None,
            skipped=True, skip_reason="no_signal: no_strategy_met_threshold",
        )

        with patch.object(trader, "_select_markets", return_value=[market]), \
             patch.object(trader, "_ensure_connected", return_value=None), \
             patch.object(trader, "_analyze_market", return_value=skipped), \
             patch.object(trader, "update_dashboard_status", return_value=None):
            outcomes = trader.run_single_cycle()

        self.assertEqual(len(outcomes), 1)
        self.assertTrue(outcomes[0].skipped)
        self.assertIn("no_signal", outcomes[0].skip_reason)

    def test_submit_order_returns_paper_buy_receipt(self) -> None:
        trader = self._make_trader()

        receipt = trader._submit_order(
            "pm-5m-btc",
            side="BUY",
            price=0.51,
            size=2.0,
            intent_type=OrderIntentType.ENTRY,
            risk_plan=_make_risk_plan(position_size=2.0),
            source_market_id="pm-5m-btc",
            outcome="YES",
        )

        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.status, "paper")
        self.assertEqual(receipt.side, "BUY")
        self.assertTrue(receipt.order_id.startswith("paper-"))

    def test_submit_order_blocks_paper_sell_without_inventory(self) -> None:
        trader = self._make_trader()

        receipt = trader._submit_order(
            "pm-5m-btc",
            side="SELL",
            price=0.49,
            size=2.0,
            intent_type=OrderIntentType.EXIT,
            position_id="missing",
        )

        self.assertIsNone(receipt)

    def test_run_single_cycle_skips_on_zero_position_size_outcome(self) -> None:
        trader = self._make_trader()
        market = _make_gamma_market()
        zero_plan = _make_risk_plan(position_size=0.0)
        skipped = TradeOutcome(
            market_id=market.market_id, question=market.question,
            decision="buy", confidence=0.50, risk_plan=zero_plan, receipt=None,
            skipped=True, skip_reason="Risk plan returned zero position size -- skipping.",
        )

        with patch.object(trader, "_select_markets", return_value=[market]), \
             patch.object(trader, "_ensure_connected", return_value=None), \
             patch.object(trader, "_analyze_market", return_value=skipped), \
             patch.object(trader, "update_dashboard_status", return_value=None):
            outcomes = trader.run_single_cycle()

        self.assertEqual(len(outcomes), 1)
        self.assertTrue(outcomes[0].skipped)
        self.assertIn("zero", outcomes[0].skip_reason.lower())

    def test_run_single_cycle_handles_market_analysis_exception(self) -> None:
        trader = self._make_trader()
        market = _make_gamma_market()

        with patch.object(trader, "_select_markets", return_value=[market]), \
             patch.object(trader, "_ensure_connected", return_value=None), \
             patch.object(trader, "_analyze_market", side_effect=RuntimeError("signal failure")), \
             patch.object(trader, "update_dashboard_status", return_value=None):
            outcomes = trader.run_single_cycle()

        # Exception is caught internally — cycle returns empty list, not a crash.
        self.assertEqual(outcomes, [])

    def test_select_markets_returns_active_btc_eth_markets(self) -> None:
        trader = self._make_trader()

        with patch.object(trader.gamma, "get_current_5min_market", return_value=None):
            selected = trader._select_markets(top_n=2)

        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0].market_id, "pm-5m-btc")
        self.assertEqual(selected[1].market_id, "pm-5m-eth")

    def test_select_markets_caches_real_token_ids(self) -> None:
        trader = self._make_trader()
        market = SimpleNamespace(yes_token_id="yes-token", no_token_id="no-token")

        with patch.object(trader.gamma, "get_current_5min_market", return_value=market):
            selected = trader._select_markets()

        self.assertEqual(selected[0].market_id, "pm-5m-btc")
        self.assertEqual(trader._real_token_ids["BTC"], ("yes-token", "no-token"))
        self.assertEqual(trader._real_token_ids["ETH"], ("yes-token", "no-token"))


class TradeOutcomeTests(unittest.TestCase):
    def test_skipped_outcome_has_no_receipt(self) -> None:
        outcome = TradeOutcome(
            market_id="mkt-x",
            question="Test?",
            decision="hold",
            confidence=0.40,
            risk_plan=None,
            receipt=None,
            skipped=True,
            skip_reason="Low confidence.",
        )
        self.assertIsNone(outcome.receipt)
        self.assertTrue(outcome.skipped)

    def test_executed_outcome_has_receipt(self) -> None:
        receipt = OrderReceipt(
            order_id="ord-001",
            status="paper",
            token_id="mkt-x",
            price=0.55,
            size=0.05,
            side="BUY",
        )
        outcome = TradeOutcome(
            market_id="mkt-x",
            question="Test?",
            decision="buy",
            confidence=0.70,
            risk_plan=_make_risk_plan(),
            receipt=receipt,
            skipped=False,
            skip_reason="",
        )
        self.assertFalse(outcome.skipped)
        self.assertEqual(outcome.receipt.order_id, "ord-001")


if __name__ == "__main__":
    unittest.main()
