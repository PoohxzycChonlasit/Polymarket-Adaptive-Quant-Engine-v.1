from __future__ import annotations
import unittest
from unittest.mock import MagicMock
import time
from polymarket.trader import PolymarketTrader

class TestMarketReadinessTiming(unittest.TestCase):
    def setUp(self) -> None:
        self.trader = PolymarketTrader()
        # Mock settings to avoid background loops or real API calls
        self.trader.settings = MagicMock()
        self.trader.settings.paper_trading = True
        self.trader.settings.adaptive_entry_max_spread = 0.06
        self.trader.settings.execution_entry_hard_block_seconds = 35
        self.trader._connected = True

    def test_readiness_timing_v1_progression(self) -> None:
        """
        Tests the progression of readiness states:
        DISCOVERED -> TOKEN_READY -> BOOK_SEEN -> NONZERO_BOOK -> SPREAD_NORMALIZED -> TRADABLE
        """
        ticker = "BTC"
        epoch_start = int(time.time()) // 300 * 300
        epoch_end = epoch_start + 300
        
        # 1. First discovery (no tokens, no orderbook)
        detail1 = self.trader._active_window_alignment_detail(
            ticker=ticker,
            epoch_start=epoch_start,
            epoch_end=epoch_end,
            seconds_remaining=300,
            token_ids=None,
            orderbook_ready=None,
            nonzero_bidask=False,
            liquidity_state=None,
            spread=None
        )
        
        self.assertEqual(detail1["executable_book_state"], "DISCOVERED")
        self.assertTrue(detail1["first_discovered_ts"] != "")
        self.assertEqual(detail1["first_token_ready_ts"], "")
        self.assertEqual(detail1["readiness_confidence"], 0.0)

        # 2. Tokens ready
        detail2 = self.trader._active_window_alignment_detail(
            ticker=ticker,
            epoch_start=epoch_start,
            epoch_end=epoch_end,
            seconds_remaining=290,
            token_ids=("tok1", "tok2"),
            orderbook_ready=None,
            nonzero_bidask=False,
            liquidity_state=None,
            spread=None
        )
        
        self.assertEqual(detail2["executable_book_state"], "TOKEN_READY")
        self.assertTrue(detail2["first_token_ready_ts"] != "")
        self.assertEqual(detail2["first_orderbook_seen_ts"], "")
        self.assertEqual(detail2["readiness_confidence"], 0.2)

        # 3. Orderbook seen (but zero bid/ask)
        detail3 = self.trader._active_window_alignment_detail(
            ticker=ticker,
            epoch_start=epoch_start,
            epoch_end=epoch_end,
            seconds_remaining=280,
            token_ids=("tok1", "tok2"),
            orderbook_ready=True,
            nonzero_bidask=False,
            liquidity_state="HEALTHY",
            spread=0.1
        )
        
        self.assertEqual(detail3["executable_book_state"], "BOOK_SEEN")
        self.assertTrue(detail3["first_orderbook_seen_ts"] != "")
        self.assertEqual(detail3["first_nonzero_bidask_ts"], "")
        self.assertEqual(detail3["readiness_confidence"], 0.4)

        # 3b. Nonzero bid/ask (but spread still wide)
        detail3b = self.trader._active_window_alignment_detail(
            ticker=ticker,
            epoch_start=epoch_start,
            epoch_end=epoch_end,
            seconds_remaining=275,
            token_ids=("tok1", "tok2"),
            orderbook_ready=True,
            nonzero_bidask=True,
            liquidity_state="HEALTHY",
            spread=0.1
        )
        self.assertEqual(detail3b["executable_book_state"], "NONZERO_BOOK")
        self.assertTrue(detail3b["first_nonzero_bidask_ts"] != "")

        # 4. Nonzero bid/ask + spread normalized + tradable
        from polymarket.client import OrderbookSnapshot
        raw = {
            "top_bids": [{"price": 0.5, "size": 1000}],
            "top_asks": [{"price": 0.51, "size": 1000}]
        }
        ob_strong = OrderbookSnapshot(
            token_id="tok", best_bid=0.5, best_ask=0.51, spread=0.01, bid_size=1000, ask_size=1000, raw_response=raw
        )
        detail4 = self.trader._active_window_alignment_detail(
            ticker=ticker,
            epoch_start=epoch_start,
            epoch_end=epoch_end,
            seconds_remaining=270,
            token_ids=("tok1", "tok2"),
            orderbook_ready=True,
            nonzero_bidask=True,
            liquidity_state="HEALTHY",
            spread=0.01,
            yes_ob=ob_strong
        )
        
        self.assertEqual(detail4["executable_book_state"], "TRADABLE")
        self.assertTrue(detail4["first_nonzero_bidask_ts"] != "")
        self.assertTrue(detail4["first_spread_normalized_ts"] != "")
        self.assertTrue(detail4["first_tradable_ts"] != "")
        self.assertEqual(detail4["readiness_confidence"], 1.0)
        
        # Verify metrics
        # discovery (300) to book (280) = 20s
        self.assertEqual(detail4["discovery_to_book_seconds"], 20)
        # book (280) to tradable (270) = 10s
        self.assertEqual(detail4["book_to_tradable_seconds"], 10)
        # total (300 to 270) = 30s
        self.assertEqual(detail4["total_discovery_to_tradable_seconds"], 30)

    def test_first_timestamp_persistence(self) -> None:
        """
        Verifies that first_* timestamps are written only once and not overwritten by later snapshots.
        """
        ticker = "ETH"
        epoch_start = int(time.time()) // 300 * 300
        epoch_end = epoch_start + 300
        
        # Discovery
        detail1 = self.trader._active_window_alignment_detail(
            ticker=ticker, epoch_start=epoch_start, epoch_end=epoch_end, seconds_remaining=290
        )
        ts1 = detail1["first_discovered_ts"]
        rem1 = detail1["first_discovered_seconds_remaining"]
        self.assertTrue(ts1 != "")
        self.assertEqual(rem1, 290)
        
        # Later snapshot of same market
        detail2 = self.trader._active_window_alignment_detail(
            ticker=ticker, epoch_start=epoch_start, epoch_end=epoch_end, seconds_remaining=280
        )
        self.assertEqual(detail2["first_discovered_ts"], ts1)
        self.assertEqual(detail2["first_discovered_seconds_remaining"], rem1)

    def test_spread_oscillation_count(self) -> None:
        """
        Verifies spread_oscillation_count increments on spread state flips.
        """
        ticker = "POL"
        epoch_start = int(time.time()) // 300 * 300
        epoch_end = epoch_start + 300
        
        # Spread Wide
        detail1 = self.trader._active_window_alignment_detail(
            ticker=ticker, epoch_start=epoch_start, epoch_end=epoch_end, seconds_remaining=290,
            token_ids=("t1", "t2"), orderbook_ready=True, spread=0.1
        )
        self.assertEqual(detail1["spread_oscillation_count"], 0)
        
        # Spread Normalized
        detail2 = self.trader._active_window_alignment_detail(
            ticker=ticker, epoch_start=epoch_start, epoch_end=epoch_end, seconds_remaining=280,
            token_ids=("t1", "t2"), orderbook_ready=True, spread=0.01
        )
        self.assertEqual(detail2["spread_oscillation_count"], 1)
        
        # Spread Wide again
        detail3 = self.trader._active_window_alignment_detail(
            ticker=ticker, epoch_start=epoch_start, epoch_end=epoch_end, seconds_remaining=270,
            token_ids=("t1", "t2"), orderbook_ready=True, spread=0.1
        )
        self.assertEqual(detail3["spread_oscillation_count"], 2)

    def test_seconds_remaining_clamp_over_epoch(self) -> None:
        """Clamp fix: seconds_remaining > epoch_length must be stored as epoch_length."""
        ticker = "BTC"
        epoch_start = 1778757000
        epoch_end = epoch_start + 300  # epoch_length = 300

        result = self.trader._phase2_mark_readiness(
            ticker=ticker,
            epoch_start=epoch_start,
            epoch_end=epoch_end,
            token_ready=True,
            seconds_remaining=349,  # Impossible — exceeds 300s epoch
        )
        assert result["token_ready_seconds_remaining"] == 300, (
            f"Expected 300 (clamped), got {result['token_ready_seconds_remaining']}"
        )

    def test_seconds_remaining_clamp_valid_passthrough(self) -> None:
        """Clamp fix: valid seconds_remaining within [0, epoch_length] must pass through unchanged."""
        ticker = "ETH"
        epoch_start = 1778757000
        epoch_end = epoch_start + 300

        result = self.trader._phase2_mark_readiness(
            ticker=ticker,
            epoch_start=epoch_start,
            epoch_end=epoch_end,
            token_ready=True,
            seconds_remaining=250,
        )
        assert result["token_ready_seconds_remaining"] == 250, (
            f"Expected 250 (unchanged), got {result['token_ready_seconds_remaining']}"
        )

    def test_seconds_remaining_clamp_zero_floor(self) -> None:
        """Clamp fix: negative seconds_remaining must be stored as 0."""
        ticker = "BTC"
        epoch_start = 1778757000
        epoch_end = epoch_start + 300

        result = self.trader._phase2_mark_readiness(
            ticker=ticker,
            epoch_start=epoch_start,
            epoch_end=epoch_end,
            token_ready=True,
            seconds_remaining=-5,
        )
        assert result["token_ready_seconds_remaining"] == 0, (
            f"Expected 0 (zero-floored), got {result['token_ready_seconds_remaining']}"
        )


    # ── Lifecycle Latency Observatory v1 ──────────────────────────────

    def test_compute_lifecycle_latency_ms_returns_zero_defaults_on_empty_bucket(self) -> None:
        result = self.trader._compute_lifecycle_latency_ms({})
        self.assertEqual(result["discovery_to_token_ready_ms"], 0)
        self.assertEqual(result["total_discovery_to_decision_ms"], 0)
        self.assertEqual(result["dominant_latency_stage"], "")
        self.assertEqual(result["lifecycle_latency_classification"], "")

    def test_compute_lifecycle_latency_ms_computes_correct_ms(self) -> None:
        bucket = {
            "first_discovered_ts":       "2026-05-14T10:00:00.000000Z",
            "first_token_ready_ts":      "2026-05-14T10:00:00.500000Z",   # +500ms
            "first_orderbook_seen_ts":   "2026-05-14T10:00:01.000000Z",   # +500ms
            "first_nonzero_bidask_ts":   "2026-05-14T10:00:01.800000Z",   # +800ms
            "first_spread_normalized_ts":"2026-05-14T10:00:02.200000Z",   # +400ms
            "first_tradable_ts":         "2026-05-14T10:00:02.600000Z",   # +400ms
            "decision_complete_ts":      "2026-05-14T10:00:03.200000Z",   # +600ms
        }
        result = self.trader._compute_lifecycle_latency_ms(bucket)
        self.assertEqual(result["discovery_to_token_ready_ms"], 500)
        self.assertEqual(result["token_ready_to_book_ms"], 500)
        self.assertEqual(result["book_to_nonzero_ms"], 800)
        self.assertEqual(result["nonzero_to_normalized_ms"], 400)
        self.assertEqual(result["normalized_to_executable_ms"], 400)
        self.assertEqual(result["executable_to_decision_ms"], 600)
        self.assertEqual(result["total_discovery_to_decision_ms"], 3200)
        # total 3200ms → NORMAL
        self.assertEqual(result["lifecycle_latency_classification"], "NORMAL")

    def test_compute_lifecycle_latency_ms_dominant_stage(self) -> None:
        bucket = {
            "first_discovered_ts":       "2026-05-14T10:00:00.000000Z",
            "first_token_ready_ts":      "2026-05-14T10:00:00.100000Z",   # 100ms
            "first_orderbook_seen_ts":   "2026-05-14T10:00:05.100000Z",   # 5000ms ← dominant
            "first_nonzero_bidask_ts":   "2026-05-14T10:00:05.300000Z",
            "first_spread_normalized_ts":"2026-05-14T10:00:05.400000Z",
            "first_tradable_ts":         "2026-05-14T10:00:05.500000Z",
            "decision_complete_ts":      "2026-05-14T10:00:05.600000Z",
        }
        result = self.trader._compute_lifecycle_latency_ms(bucket)
        self.assertEqual(result["dominant_latency_stage"], "TOKEN_READY")

    def test_compute_lifecycle_latency_ms_classification_thresholds(self) -> None:
        def _bucket_with_total_ms(total_ms: int) -> dict:
            from datetime import datetime, timezone, timedelta
            t0 = datetime(2026, 5, 14, 10, 0, 0, tzinfo=timezone.utc)
            t1 = t0 + timedelta(milliseconds=total_ms)
            fmt = lambda dt: dt.isoformat().replace("+00:00", "Z")
            return {
                "first_discovered_ts": fmt(t0),
                "decision_complete_ts": fmt(t1),
            }

        for total_ms, expected_class in [
            (500, "FAST"), (1000, "FAST"), (1999, "FAST"),
            (2000, "NORMAL"), (4999, "NORMAL"),
            (5000, "SLOW"), (14999, "SLOW"),
            (15000, "CRITICAL"), (30000, "CRITICAL"),
        ]:
            result = self.trader._compute_lifecycle_latency_ms(_bucket_with_total_ms(total_ms))
            self.assertEqual(
                result["lifecycle_latency_classification"], expected_class,
                f"total_ms={total_ms} → expected {expected_class}, got {result['lifecycle_latency_classification']}"
            )

    def test_compute_lifecycle_latency_ms_fail_soft_on_bad_timestamps(self) -> None:
        bucket = {
            "first_discovered_ts": "not-a-timestamp",
            "first_token_ready_ts": "also-bad",
            "decision_complete_ts": "",
        }
        result = self.trader._compute_lifecycle_latency_ms(bucket)
        self.assertEqual(result["discovery_to_token_ready_ms"], 0)
        self.assertEqual(result["total_discovery_to_decision_ms"], 0)
        self.assertEqual(result["lifecycle_latency_classification"], "")


if __name__ == "__main__":
    unittest.main()
