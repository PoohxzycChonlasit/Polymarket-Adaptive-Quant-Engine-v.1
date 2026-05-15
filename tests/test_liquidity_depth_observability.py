from __future__ import annotations
import unittest
from unittest.mock import MagicMock
import time
from polymarket.trader import PolymarketTrader
from polymarket.client import OrderbookSnapshot

class TestLiquidityDepthObservability(unittest.TestCase):
    def setUp(self) -> None:
        self.trader = PolymarketTrader()
        # Mock settings
        self.trader.settings = MagicMock()
        self.trader.settings.paper_trading = True
        self.trader.settings.adaptive_entry_max_spread = 0.06
        self.trader.settings.execution_entry_hard_block_seconds = 35
        self.trader.settings.liquidity_min_depth_usd_threshold = 250.0
        self.trader._connected = True

    def test_liquidity_depth_progression(self) -> None:
        """
        Tests liquidity depth state transitions: EMPTY -> THIN -> ACCEPTABLE -> STRONG
        """
        ticker = "BTC"
        epoch_start = int(time.time()) // 300 * 300
        epoch_end = epoch_start + 300
        
        # Helper to create mock OB
        def create_ob(bid_sz, ask_sz, bid_sz3=None, ask_sz3=None):
            if bid_sz3 is None: bid_sz3 = bid_sz
            if ask_sz3 is None: ask_sz3 = ask_sz
            
            raw = {
                "top_bids": [{"price": 0.5, "size": bid_sz}, {"price": 0.49, "size": bid_sz3 - bid_sz}],
                "top_asks": [{"price": 0.51, "size": ask_sz}, {"price": 0.52, "size": ask_sz3 - ask_sz}]
            }
            return OrderbookSnapshot(
                token_id="tok",
                best_bid=0.5,
                best_ask=0.51,
                spread=0.01,
                bid_size=bid_sz,
                ask_size=ask_sz,
                raw_response=raw
            )

        # 1. Empty book
        ob_empty = create_ob(0, 0)
        detail1 = self.trader._active_window_alignment_detail(
            ticker=ticker,
            epoch_start=epoch_start,
            epoch_end=epoch_end,
            seconds_remaining=300,
            token_ids=("tok1", "tok2"),
            orderbook_ready=True,
            nonzero_bidask=False,
            yes_ob=ob_empty
        )
        self.assertEqual(detail1["liquidity_depth_state"], "EMPTY")
        self.assertEqual(detail1["best_bid_size"], 0.0)

        # 2. Thin book
        ob_thin = create_ob(10, 10, 20, 20) # $10 fillable (approx)
        detail2 = self.trader._active_window_alignment_detail(
            ticker=ticker,
            epoch_start=epoch_start,
            epoch_end=epoch_end,
            seconds_remaining=290,
            token_ids=("tok1", "tok2"),
            orderbook_ready=True,
            nonzero_bidask=True,
            yes_ob=ob_thin
        )
        self.assertEqual(detail2["liquidity_depth_state"], "THIN")
        self.assertEqual(detail2["total_bid_depth_l1_l3"], 20.0)
        self.assertEqual(detail2["depth_oscillation_count"], 1) # EMPTY -> THIN

        # 3. Acceptable book
        ob_acc = create_ob(300, 300, 600, 600) # $300 fillable
        detail3 = self.trader._active_window_alignment_detail(
            ticker=ticker,
            epoch_start=epoch_start,
            epoch_end=epoch_end,
            seconds_remaining=280,
            token_ids=("tok1", "tok2"),
            orderbook_ready=True,
            nonzero_bidask=True,
            yes_ob=ob_acc
        )
        self.assertEqual(detail3["liquidity_depth_state"], "ACCEPTABLE")
        self.assertEqual(detail3["depth_oscillation_count"], 2) # THIN -> ACCEPTABLE
        self.assertTrue(detail3["first_min_depth_ts"] != "")
        self.assertEqual(detail3["first_min_depth_seconds_remaining"], 280)
        self.assertEqual(detail3["time_to_min_depth_seconds"], 20) # 300 - 280

        # 4. Strong book
        ob_strong = create_ob(2000, 2000, 3000, 3000) # $1500 fillable
        detail4 = self.trader._active_window_alignment_detail(
            ticker=ticker,
            epoch_start=epoch_start,
            epoch_end=epoch_end,
            seconds_remaining=270,
            token_ids=("tok1", "tok2"),
            orderbook_ready=True,
            nonzero_bidask=True,
            yes_ob=ob_strong
        )
        self.assertEqual(detail4["liquidity_depth_state"], "STRONG")
        self.assertEqual(detail4["depth_oscillation_count"], 3)

    def test_unstable_liquidity_behavior(self) -> None:
        """
        Verifies depth_oscillation_count increments and state becomes UNSTABLE when dropping from STRONG/ACCEPTABLE to THIN.
        """
        ticker = "ETH"
        epoch_start = int(time.time()) // 300 * 300
        epoch_end = epoch_start + 300
        
        def create_ob(sz):
            raw = {
                "top_bids": [{"price": 0.5, "size": sz}],
                "top_asks": [{"price": 0.51, "size": sz}]
            }
            return OrderbookSnapshot(token_id="tok", best_bid=0.5, best_ask=0.51, spread=0.01, bid_size=sz, ask_size=sz, raw_response=raw)

        # Strong
        self.trader._active_window_alignment_detail(
            ticker=ticker, epoch_start=epoch_start, epoch_end=epoch_end, seconds_remaining=290,
            token_ids=("t1", "t2"), orderbook_ready=True, nonzero_bidask=True, yes_ob=create_ob(2000)
        )
        
        # Drop to Thin
        detail2 = self.trader._active_window_alignment_detail(
            ticker=ticker, epoch_start=epoch_start, epoch_end=epoch_end, seconds_remaining=280,
            token_ids=("t1", "t2"), orderbook_ready=True, nonzero_bidask=True, yes_ob=create_ob(10)
        )
        self.assertEqual(detail2["liquidity_depth_state"], "UNSTABLE")
        self.assertEqual(detail2["depth_oscillation_count"], 1) # STRONG -> UNSTABLE

    def test_tradable_but_thin_behavior(self) -> None:
        """
        Verifies tradable_but_thin_count increments when state is TRADABLE but depth is THIN/EMPTY.
        """
        ticker = "POL"
        epoch_start = int(time.time()) // 300 * 300
        epoch_end = epoch_start + 300
        
        def create_ob(sz):
            raw = {
                "top_bids": [{"price": 0.5, "size": sz}],
                "top_asks": [{"price": 0.51, "size": sz}]
            }
            return OrderbookSnapshot(token_id="tok", best_bid=0.5, best_ask=0.51, spread=0.01, bid_size=sz, ask_size=sz, raw_response=raw)

        # TRADABLE but THIN
        detail1 = self.trader._active_window_alignment_detail(
            ticker=ticker, epoch_start=epoch_start, epoch_end=epoch_end, seconds_remaining=290,
            token_ids=("t1", "t2"), orderbook_ready=True, nonzero_bidask=True, liquidity_state="HEALTHY", spread=0.01, yes_ob=create_ob(10)
        )
        self.assertEqual(detail1["executable_book_state"], "TRADABLE")
        self.assertEqual(detail1["liquidity_depth_state"], "THIN")
        self.assertEqual(detail1["tradable_but_thin_count"], 1)

    def test_depth_not_overwritten_when_ob_none(self) -> None:
        """
        Regression: _phase2_mark_readiness must NOT overwrite depth to 0.0 when called
        without yes_ob/no_ob. The bucket depth from the real orderbook call must persist.
        Root cause of executable_spread_state=UNKNOWN / liquidity_depth_state=EMPTY in
        research snapshots was _decision_diagnostics_payload calling _active_window_alignment_detail
        without ob objects, silently zeroing the bucket.
        """
        ticker = "BTC"
        epoch_start = int(time.time()) // 300 * 300
        epoch_end = epoch_start + 300

        def create_ob(sz):
            raw = {
                "top_bids": [{"price": 0.5, "size": sz}],
                "top_asks": [{"price": 0.51, "size": sz}],
            }
            return OrderbookSnapshot(
                token_id="tok", best_bid=0.5, best_ask=0.51,
                spread=0.01, bid_size=sz, ask_size=sz, raw_response=raw
            )

        # Call 1: real orderbook with meaningful depth (ACCEPTABLE)
        detail_with_ob = self.trader._active_window_alignment_detail(
            ticker=ticker,
            epoch_start=epoch_start,
            epoch_end=epoch_end,
            seconds_remaining=200,
            token_ids=("tok1", "tok2"),
            orderbook_ready=True,
            nonzero_bidask=True,
            yes_ob=create_ob(400),
        )
        self.assertEqual(detail_with_ob["liquidity_depth_state"], "ACCEPTABLE")
        self.assertGreater(detail_with_ob["best_bid_size"], 0.0)

        # Call 2: no orderbook (simulates _decision_diagnostics_payload calling without ob)
        detail_no_ob = self.trader._active_window_alignment_detail(
            ticker=ticker,
            epoch_start=epoch_start,
            epoch_end=epoch_end,
            seconds_remaining=195,
            token_ids=("tok1", "tok2"),
            orderbook_ready=True,
            nonzero_bidask=True,
            yes_ob=None,
            no_ob=None,
        )
        # Depth must be preserved from call 1 — not overwritten to EMPTY/0.0
        self.assertEqual(detail_no_ob["liquidity_depth_state"], "ACCEPTABLE",
                         "Depth state must not be overwritten to EMPTY when no ob provided")
        self.assertGreater(detail_no_ob["best_bid_size"], 0.0,
                           "best_bid_size must not be zeroed when no ob provided")

    def test_depth_empty_when_ob_provides_zero_sizes(self) -> None:
        """
        Confirms EMPTY state is still set correctly when an ob IS provided but has zero depth.
        The guard must still allow writing EMPTY when real zero-depth ob is supplied.
        """
        ticker = "ETH"
        epoch_start = int(time.time()) // 300 * 300
        epoch_end = epoch_start + 300

        def create_empty_ob():
            raw = {"top_bids": [], "top_asks": []}
            return OrderbookSnapshot(
                token_id="tok", best_bid=0.0, best_ask=0.0,
                spread=0.0, bid_size=0.0, ask_size=0.0, raw_response=raw
            )

        detail = self.trader._active_window_alignment_detail(
            ticker=ticker,
            epoch_start=epoch_start,
            epoch_end=epoch_end,
            seconds_remaining=200,
            token_ids=("tok1", "tok2"),
            orderbook_ready=True,
            nonzero_bidask=False,
            yes_ob=create_empty_ob(),
        )
        self.assertEqual(detail["liquidity_depth_state"], "EMPTY")
        self.assertEqual(detail["best_bid_size"], 0.0)
        self.assertEqual(detail["best_ask_size"], 0.0)


if __name__ == "__main__":
    unittest.main()
