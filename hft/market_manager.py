"""
hft/market_manager.py
=====================
Manages the current 5-min window state for each asset.

Responsibilities:
  - Fetch and cache YES/NO prices + PTB from Gamma API (once per window)
  - Track open positions per window (entry price, shares, side)
  - Detect window rollovers and trigger settlement
  - Provide live spot price from Binance feed (no API call needed)
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from hft import config as C
from hft.utils import current_epoch, epoch_end, seconds_remaining, window_label

LOGGER = logging.getLogger(__name__)


@dataclass
class WindowState:
    """Complete state of one 5-min window for one asset."""
    asset:             str
    epoch:             int
    yes_price:         float
    no_price:          float
    ptb:               float    # Coinbase price-to-beat from Gamma
    spot_price:        float    # Binance live spot price
    seconds_remaining: int
    slug:              str
    fetched_at:        float = field(default_factory=time.time)
    is_stale:          bool  = False


@dataclass
class OpenPosition:
    pos_id:       str
    asset:        str
    window_epoch: int
    side:         str       # YES / NO
    entry_price:  float
    shares:       float
    cost_usd:     float
    p_model:      float
    opened_at:    float = field(default_factory=time.time)
    closed_at:    float = 0.0
    exit_price:   float = 0.0
    pnl_usd:      float = 0.0
    is_open:      bool  = True


class MarketManager:
    """
    Per-asset window state manager.

    Cache policy:
    - PTB and Gamma prices: re-fetch on window rollover or if data is > 30s old
    - Spot price: always fresh from Binance WebSocket (no cache needed)
    """

    # Re-fetch market data if older than this many seconds
    _CACHE_TTL = 30.0

    def __init__(self) -> None:
        self._window_cache:  dict[str, WindowState]       = {}
        self._positions:     dict[str, list[OpenPosition]] = {}  # asset → positions
        self._gamma_fetcher  = None   # lazy-init to avoid circular import
        self._pos_counter    = 0

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_window(self, asset: str) -> WindowState | None:
        """
        Return current window state.  Fetches from Gamma API on cache miss.
        Returns None only if the Gamma fetch fails completely.
        """
        now   = time.time()
        epoch = current_epoch()
        cached = self._window_cache.get(asset)

        need_refresh = (
            cached is None
            or cached.epoch != epoch
            or (now - cached.fetched_at) > self._CACHE_TTL
        )

        if need_refresh:
            fresh = self._fetch_window(asset, epoch)
            if fresh is None:
                if cached is not None:
                    cached.is_stale = True
                    cached.seconds_remaining = seconds_remaining(cached.epoch)
                    return cached
                return None
            self._window_cache[asset] = fresh
            return fresh

        # Update time-sensitive fields without API call
        cached.spot_price        = self._get_spot(asset, fallback=cached.spot_price)
        cached.seconds_remaining = seconds_remaining(epoch)
        return cached

    def open_position(
        self,
        asset:        str,
        window_epoch: int,
        side:         str,
        entry_price:  float,
        shares:       float,
        cost_usd:     float,
        p_model:      float,
    ) -> OpenPosition:
        self._pos_counter += 1
        pos = OpenPosition(
            pos_id=f"hft-{asset.lower()}-{window_epoch}-{self._pos_counter:04d}",
            asset=asset, window_epoch=window_epoch, side=side,
            entry_price=entry_price, shares=shares, cost_usd=cost_usd,
            p_model=p_model,
        )
        self._positions.setdefault(asset, []).append(pos)
        LOGGER.info(
            "[MarketMgr] OPEN pos_id=%s side=%s price=%.4f shares=%.4f cost=$%.4f",
            pos.pos_id, side, entry_price, shares, cost_usd,
        )
        return pos

    def close_position(
        self, pos: OpenPosition, exit_price: float, pnl_usd: float,
    ) -> None:
        pos.is_open    = False
        pos.exit_price = exit_price
        pos.pnl_usd    = pnl_usd
        pos.closed_at  = time.time()
        LOGGER.info(
            "[MarketMgr] CLOSE pos_id=%s exit=%.4f pnl=%+.4f",
            pos.pos_id, exit_price, pnl_usd,
        )

    def open_positions(self, asset: str | None = None) -> list[OpenPosition]:
        if asset:
            return [p for p in self._positions.get(asset, []) if p.is_open]
        return [p for ps in self._positions.values() for p in ps if p.is_open]

    def closed_today(self) -> list[OpenPosition]:
        today_start = time.mktime(time.strptime(time.strftime("%Y-%m-%d"), "%Y-%m-%d"))
        result = []
        for ps in self._positions.values():
            for p in ps:
                if not p.is_open and p.closed_at >= today_start:
                    result.append(p)
        return result

    def get_stats(self) -> dict:
        closed = self.closed_today()
        wins   = [p for p in closed if p.pnl_usd > 0]
        total_pnl = sum(p.pnl_usd for p in closed)
        return {
            "trades_today": len(closed),
            "wins":         len(wins),
            "win_rate":     len(wins) / max(len(closed), 1),
            "total_pnl":    total_pnl,
            "open_count":   len(self.open_positions()),
        }

    # ── Internal ───────────────────────────────────────────────────────────────

    def _fetch_window(self, asset: str, epoch: int) -> WindowState | None:
        fetcher = self._get_fetcher()
        try:
            market = fetcher.get_exact_5min_ptb(asset)
            if market is None:
                active = fetcher.get_current_5min_market(asset)
                if active is None:
                    LOGGER.warning("[MarketMgr] No market found for %s", asset)
                    return None
                ptb      = 0.0
                yes_price = active.yes_price
                no_price  = 1.0 - yes_price
                slug      = active.slug
            else:
                ptb       = market.price_to_beat
                yes_price = market.yes_price
                no_price  = market.no_price
                slug      = market.slug

            spot = self._get_spot(asset, fallback=ptb)

            state = WindowState(
                asset=asset, epoch=epoch,
                yes_price=yes_price, no_price=no_price,
                ptb=ptb, spot_price=spot,
                seconds_remaining=seconds_remaining(epoch),
                slug=slug,
            )
            LOGGER.debug(
                "[MarketMgr] Fetched window %s | ptb=%.4f yes=%.4f no=%.4f spot=%.4f %ds",
                slug, ptb, yes_price, no_price, spot, state.seconds_remaining,
            )
            return state

        except Exception as exc:
            LOGGER.warning("[MarketMgr] Fetch error for %s: %s", asset, exc)
            return None

    def _get_spot(self, asset: str, fallback: float = 0.0) -> float:
        try:
            from polymarket.market_feed import get_feed
            price = get_feed().get_live_price(asset)
            return price if price > 0 else fallback
        except Exception:
            return fallback

    def _get_fetcher(self):
        if self._gamma_fetcher is None:
            from polymarket.gamma_fetcher import GammaFetcher
            self._gamma_fetcher = GammaFetcher()
        return self._gamma_fetcher
