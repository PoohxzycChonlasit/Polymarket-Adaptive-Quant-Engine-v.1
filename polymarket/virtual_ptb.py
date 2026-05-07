"""
virtual_ptb.py
==============
Virtual Price-To-Beat tracker that delegates to PolymarketOracleFeed.
This provides a backward-compatible VirtualPTB dataclass with the same interface
as before, but backed by the proper Coinbase Advanced Trade oracle price.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from polymarket.oracle_price_feed import OraclePriceState, PolymarketOracleFeed

LOGGER = logging.getLogger(__name__)


@dataclass
class VirtualPTB:
    asset: str
    epoch_start_ts: int
    price_to_beat: float
    current_price: float
    seconds_remaining: int
    is_above_ptb: bool
    price_diff_pct: float
    last_updated: float | None = None
    feed_age_seconds: float | None = None


class VirtualPriceToBeatTracker:
    """
    Thin wrapper around PolymarketOracleFeed that provides the same interface
    as the old tracker but uses Coinbase Advanced Trade (the real Polymarket oracle).

    The underlying feed runs in a background thread refreshing every 10s.
    """

    def __init__(self, timeout: float = 8.0) -> None:
        self._feed = PolymarketOracleFeed(refresh_interval=5.0, timeout=timeout)
        self._started = False

    def _ensure_started(self) -> None:
        if not self._started:
            self._feed.start()
            self._started = True

    def close(self) -> None:
        if self._started:
            self._feed.stop()
            self._started = False

    def get_market_ptb(self, asset: str) -> VirtualPTB:
        """Return a VirtualPTB snapshot for the given asset (logs to INFO)."""
        self._ensure_started()
        state = self._feed.get_state(asset.upper())

        # Log the Polymarket-aligned line for every call (INFO level so it appears in realtime log)
        log_line = self._feed.format_log_line(asset.upper())
        LOGGER.info(log_line)

        return VirtualPTB(
            asset=state.asset,
            epoch_start_ts=state.epoch_start_ts,
            price_to_beat=state.price_to_beat,
            current_price=state.current_price,
            seconds_remaining=state.seconds_remaining,
            is_above_ptb=state.is_above_ptb,
            price_diff_pct=state.price_diff_pct,
            last_updated=state.last_updated,
            feed_age_seconds=max(0.0, time.time() - state.last_updated) if state.last_updated else None,
        )

    def get_state(self, asset: str) -> OraclePriceState:
        """Return OraclePriceState for the given asset without logging (for fast 1s polling)."""
        self._ensure_started()
        return self._feed.get_state(asset.upper())

    def get_feed_age_seconds(self, asset: str) -> float | None:
        """Return seconds since the last oracle price update, or None if unavailable."""
        state = self.get_state(asset)
        if not state.last_updated:
            return None
        return max(0.0, time.time() - state.last_updated)

    def __enter__(self) -> "VirtualPriceToBeatTracker":
        self._ensure_started()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
