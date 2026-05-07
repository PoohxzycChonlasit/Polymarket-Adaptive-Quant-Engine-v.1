from __future__ import annotations

import unittest
from types import SimpleNamespace

from polymarket.arbitrage import ArbitrageOpportunity
from polymarket.arbitrage_executor import ArbInventory, ArbitrageExecutor
from polymarket.client import BUY, SELL, OrderReceipt


class FakeArbClient:
    def __init__(self, statuses: list[str]) -> None:
        self.statuses = statuses
        self.orders: list[OrderReceipt] = []
        self.cancelled: list[str] = []

    def place_limit_order(self, token_id: str, price: float, size: float, side: str) -> OrderReceipt:
        status = self.statuses.pop(0) if self.statuses else "open"
        receipt = OrderReceipt(
            order_id=f"ord-{len(self.orders) + 1}",
            status=status,
            token_id=token_id,
            side=side,
            price=price,
            size=size,
            filled_size=size if status in {"paper", "filled", "matched"} else 0.0,
            remaining_size=0.0 if status in {"paper", "filled", "matched"} else size,
        )
        self.orders.append(receipt)
        return receipt

    def cancel_order(self, order_id: str) -> bool:
        self.cancelled.append(order_id)
        return True

    def get_open_orders(self) -> list[dict]:
        return []

    def get_positions(self) -> list[dict]:
        return []

    def get_order(self, order_id: str) -> dict:
        return {"status": "open", "filled_size": 0.0}


def _settings(**overrides):
    values = {
        "paper_trading": True,
        "arb_auto_execute": True,
        "arb_min_profit_usdc": 0.02,
        "arb_live_min_profit_usdc": 0.05,
        "arb_entry_min_seconds_remaining": 90,
        "arb_force_cancel_seconds_remaining": 60,
        "arb_leg_fill_timeout_sec": 0.0,
        "arb_second_leg_retry": 2,
        "arb_unwind_on_partial_fill": True,
        "arb_max_active_markets_small_bankroll": 1,
        "arb_max_leg_spread": 0.03,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _opp() -> ArbitrageOpportunity:
    return ArbitrageOpportunity(
        ticker="BTC",
        market_id="pm-5m-btc",
        yes_token_id="yes-token",
        no_token_id="no-token",
        yes_bid=0.47,
        yes_ask=0.48,
        yes_bid_size=100.0,
        yes_ask_size=100.0,
        no_bid=0.48,
        no_ask=0.49,
        no_bid_size=100.0,
        no_ask_size=100.0,
        ask_sum=0.97,
        gross_edge=0.03,
        net_edge=0.022,
        max_size=100.0,
        est_profit=2.20,
        executable=True,
        action="BUY_BOTH_ARB",
        opportunity_type="BUY_BOTH_ARB",
        fill_risk="LOW",
        reason="locked_profit_detected",
    )


class ArbitrageExecutorTests(unittest.TestCase):
    def test_small_bankroll_sizing_caps_total_cost_near_two_dollars(self) -> None:
        executor = ArbitrageExecutor(FakeArbClient([]), settings=_settings())

        sizing = executor.calculate_sizing(_opp(), bankroll=20.0)

        self.assertAlmostEqual(sizing.max_total_cost, 2.0)
        self.assertAlmostEqual(sizing.shares, 2.0 / 0.97)

    def test_successful_buy_both_leaves_balanced_inventory(self) -> None:
        client = FakeArbClient(["filled", "filled"])
        executor = ArbitrageExecutor(client, settings=_settings())

        result = executor.execute_buy_both(_opp(), bankroll=20.0, seconds_remaining=200)

        self.assertTrue(result.success)
        self.assertAlmostEqual(result.inventory.yes_size, result.inventory.no_size)
        self.assertEqual([o.side for o in client.orders], [BUY, BUY])

    def test_failed_second_leg_unwinds_first_leg_and_leaves_no_naked_inventory(self) -> None:
        client = FakeArbClient(["filled", "open", "open", "open", "filled"])
        executor = ArbitrageExecutor(client, settings=_settings())

        result = executor.execute_buy_both(_opp(), bankroll=20.0, seconds_remaining=200)

        self.assertFalse(result.success)
        self.assertAlmostEqual(result.inventory.yes_size, 0.0)
        self.assertAlmostEqual(result.inventory.no_size, 0.0)
        self.assertGreater(result.unwound_yes, 0.0)
        self.assertEqual(client.orders[-1].side, SELL)

    def test_auto_execute_false_does_not_place_orders(self) -> None:
        client = FakeArbClient(["filled", "filled"])
        executor = ArbitrageExecutor(client, settings=_settings(arb_auto_execute=False))

        result = executor.execute_buy_both(_opp(), bankroll=20.0, seconds_remaining=200)

        self.assertFalse(result.attempted)
        self.assertEqual(client.orders, [])

    def test_time_cutoff_blocks_arb_entry(self) -> None:
        client = FakeArbClient(["filled", "filled"])
        executor = ArbitrageExecutor(client, settings=_settings())

        result = executor.execute_buy_both(_opp(), bankroll=20.0, seconds_remaining=89)

        self.assertFalse(result.attempted)
        self.assertEqual(result.reason, "entry_time_cutoff")
        self.assertEqual(client.orders, [])

    def test_force_cancel_window_cancels_resting_orders_and_blocks_entry(self) -> None:
        client = FakeArbClient(["filled", "filled"])
        client.get_open_orders = lambda: [{"order_id": "stale-1"}]
        executor = ArbitrageExecutor(client, settings=_settings())

        result = executor.execute_buy_both(_opp(), bankroll=20.0, seconds_remaining=60)

        self.assertFalse(result.attempted)
        self.assertEqual(result.reason, "force_cancel_window")
        self.assertEqual(client.cancelled, ["stale-1"])
        self.assertEqual(client.orders, [])

    def test_exit_arb_requires_equal_yes_no_inventory(self) -> None:
        client = FakeArbClient(["filled", "filled"])
        executor = ArbitrageExecutor(client, settings=_settings())
        opp = _opp()
        opp.opportunity_type = "EXIT_ARB"
        opp.action = "EXIT_ARB"
        opp.bid_sum = 1.03
        opp.exit_edge = 0.03
        opp.exit_net_edge = 0.025

        result = executor.execute_exit_arb(
            opp,
            inventory=ArbInventory(yes_size=3.0, no_size=0.0),
        )

        self.assertFalse(result.attempted)
        self.assertEqual(result.reason, "requires_equal_yes_no_inventory")
        self.assertEqual(client.orders, [])


if __name__ == "__main__":
    unittest.main()
