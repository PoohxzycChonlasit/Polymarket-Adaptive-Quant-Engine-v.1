from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from polymarket.trader import PolymarketTrader
from utils.position_tracker import InventoryClassification, PositionTracker


def _settings(paper: bool = True):
    return SimpleNamespace(
        paper_trading=paper,
        account_balance=100.0,
        max_open_positions=10,
        max_total_exposure=1.0,
        max_daily_drawdown=0.10,
    )


def _tracker(paper: bool = True) -> PositionTracker:
    return PositionTracker(settings=_settings(paper=paper))


def _open(tracker: PositionTracker, outcome: str, size: float = 5.0):
    return tracker.open_position(
        symbol="pm-5m-btc",
        source="polymarket",
        side="BUY" if outcome == "YES" else "SELL",
        entry_price=0.50,
        size=size,
        stop_loss=0.40,
        take_profit=0.60,
        order_id=f"{outcome.lower()}-order",
        metadata={"outcome": outcome, "token_id": f"{outcome.lower()}-token"},
    )


class PositionReconciliationClassificationTests(unittest.TestCase):
    def test_flat(self) -> None:
        report = _tracker().reconcile_inventory()
        self.assertEqual(report.classification, InventoryClassification.FLAT)
        self.assertFalse(report.block_new_trading)

    def test_directional_yes(self) -> None:
        tracker = _tracker()
        _open(tracker, "YES")
        report = tracker.reconcile_inventory()
        self.assertEqual(report.classification, InventoryClassification.DIRECTIONAL_YES)
        self.assertFalse(report.block_new_trading)

    def test_directional_no(self) -> None:
        tracker = _tracker()
        _open(tracker, "NO")
        report = tracker.reconcile_inventory()
        self.assertEqual(report.classification, InventoryClassification.DIRECTIONAL_NO)
        self.assertFalse(report.block_new_trading)

    def test_fully_hedged_arb(self) -> None:
        tracker = _tracker()
        _open(tracker, "YES", size=7.0)
        _open(tracker, "NO", size=7.0)
        report = tracker.reconcile_inventory()
        self.assertEqual(report.classification, InventoryClassification.FULLY_HEDGED_ARB)
        self.assertFalse(report.block_new_trading)

    def test_partially_hedged_arb_blocks(self) -> None:
        tracker = _tracker()
        _open(tracker, "YES", size=7.0)
        _open(tracker, "NO", size=3.0)
        report = tracker.reconcile_inventory()
        self.assertEqual(report.classification, InventoryClassification.PARTIALLY_HEDGED_ARB)
        self.assertTrue(report.block_new_trading)

    def test_unknown_or_mismatch_blocks_on_local_clob_mismatch(self) -> None:
        tracker = _tracker(paper=False)
        _open(tracker, "YES", size=5.0)
        report = tracker.reconcile_inventory(
            polymarket_positions=[{"outcome": "YES", "size": "3"}],
            open_orders=[],
        )
        self.assertEqual(report.classification, InventoryClassification.UNKNOWN_OR_MISMATCH)
        self.assertTrue(report.block_new_trading)
        self.assertTrue(report.mismatches)

    def test_unknown_or_mismatch_blocks_on_open_orders(self) -> None:
        tracker = _tracker()
        report = tracker.reconcile_inventory(
            open_orders=[{"side": "BUY", "remaining_size": "2", "status": "open"}],
        )
        self.assertEqual(report.classification, InventoryClassification.UNKNOWN_OR_MISMATCH)
        self.assertTrue(report.block_new_trading)


class TraderReconciliationGateTests(unittest.TestCase):
    def test_live_cycle_blocks_when_reconciliation_is_unknown(self) -> None:
        settings = _settings(paper=False)
        settings.account_balance = 100.0
        settings.max_risk_per_trade = 0.01
        settings.default_stop_loss_pct = 0.02
        settings.kelly_fraction_cap = 0.25
        settings.bankroll_floor = 5.0
        trader = PolymarketTrader()
        trader.settings = settings
        trader.tracker = PositionTracker(settings=settings)
        trader.client = MagicMock()
        trader.client.get_positions.return_value = [{"outcome": "YES", "size": "3"}]
        trader.client.get_open_orders.return_value = []
        trader.client.get_order_status.return_value = SimpleNamespace(
            order_id="",
            status="",
            filled_size=0.0,
        )
        _open(trader.tracker, "YES", size=5.0)

        with patch.object(trader, "_ensure_connected", return_value=None), \
             patch.object(trader, "_select_markets") as select_markets:
            outcomes = trader.run_single_cycle()

        self.assertEqual(outcomes, [])
        select_markets.assert_not_called()
        self.assertEqual(
            trader._last_reconciliation.classification,
            InventoryClassification.UNKNOWN_OR_MISMATCH,
        )


if __name__ == "__main__":
    unittest.main()
