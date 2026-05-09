from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import cast

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from config.settings import get_settings


LOGGER = logging.getLogger(__name__)

_GAMMA_BASE = "https://gamma-api.polymarket.com"

# asset slug prefix mapping (matches Polymarket URL pattern)
_ASSET_SLUG_PREFIX: dict[str, str] = {
    "BTC":  "btc-updown-5m",
    "ETH":  "eth-updown-5m",
    "SOL":  "sol-updown-5m",
    "XRP":  "xrp-updown-5m",
    "DOGE": "doge-updown-5m",
    "HYPE": "hype-updown-5m",
    "BNB":  "bnb-updown-5m",
}


@dataclass(slots=True)
class GammaMarket:
    market_id: str
    question: str
    volume: float
    liquidity: float
    end_date_iso: str


@dataclass(slots=True)
class ExactFiveMinMarket:
    """Authoritative 5-minute market data pulled directly from Gamma /markets?slug=."""
    asset: str
    slug: str
    condition_id: str
    market_id: str
    question: str
    price_to_beat: float     # groupItemThreshold — exact Polymarket PTB
    yes_price: float
    no_price: float
    epoch_start_ts: int      # Unix ts (divisible by 300)
    epoch_end_ts: int
    seconds_remaining: int
    liquidity: float
    yes_token_id: str
    no_token_id: str


@dataclass(slots=True)
class ActiveFiveMinMarket:
    """Information about the currently active 5-minute Polymarket window."""
    asset: str
    slug: str
    condition_id: str
    question: str
    epoch_start_ts: int   # Unix ts (divisible by 300)
    epoch_end_ts: int     # epoch_start_ts + 300
    seconds_remaining: int
    yes_token_id: str
    no_token_id: str
    yes_price: float      # implied YES probability from market
    liquidity: float
    market_id: str = ""


class GammaFetcher:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.timeout = httpx.Timeout(10.0)
        self._five_min_cache_ttl_seconds = 5.0
        self._five_min_market_cache: dict[str, tuple[float, list[ActiveFiveMinMarket]]] = {}

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def fetch_markets(self, limit: int = 25) -> list[GammaMarket]:
        url = f"{self.settings.polymarket_gamma_url}/markets"
        params = {"limit": limit}
        LOGGER.info("Fetching Polymarket Gamma markets from %s", url)

        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = cast(list[dict[str, object]], response.json())

        markets: list[GammaMarket] = []
        for item in payload:
            markets.append(
                GammaMarket(
                    market_id=str(item.get("id", "")),
                    question=str(item.get("question", "")),
                    volume=float(item.get("volume", 0.0) or 0.0),
                    liquidity=float(item.get("liquidity", 0.0) or 0.0),
                    end_date_iso=str(item.get("endDate", "")),
                )
            )

        LOGGER.info("Fetched %s Polymarket Gamma markets", len(markets))
        return markets

    def get_current_5min_market(self, asset: str) -> ActiveFiveMinMarket | None:
        """
        Fetch the currently active (or next upcoming) 5-minute Up/Down market
        for the given asset from the Gamma API using slug pattern lookup.

        Returns None if no market is found.
        """
        markets = self.get_current_and_next_5min_markets(asset)
        return markets[0] if markets else None

    def get_next_5min_market(self, asset: str) -> ActiveFiveMinMarket | None:
        markets = self.get_current_and_next_5min_markets(asset)
        return markets[1] if len(markets) > 1 else None

    def get_current_and_next_5min_markets(self, asset: str, *, force_refresh: bool = False) -> list[ActiveFiveMinMarket]:
        asset_upper = asset.upper()
        slug_prefix = _ASSET_SLUG_PREFIX.get(asset_upper)
        if not slug_prefix:
            LOGGER.warning("Unknown 5M asset: %s", asset)
            return []

        now_monotonic = time.monotonic()
        cached = self._five_min_market_cache.get(asset_upper)
        if cached and not force_refresh and cached[0] > now_monotonic:
            return cached[1]

        now_ts = int(time.time())
        current_epoch = now_ts - (now_ts % 300)
        markets: list[ActiveFiveMinMarket] = []

        with httpx.Client(timeout=self.timeout) as client:
            for epoch_offset in (0, 300):
                epoch_ts = current_epoch + epoch_offset
                slug = f"{slug_prefix}-{epoch_ts}"
                try:
                    resp = client.get(f"{_GAMMA_BASE}/events?slug={slug}")
                    resp.raise_for_status()
                    data = resp.json()
                    if not data:
                        continue

                    ev = data[0] if isinstance(data, list) else data
                    mkts = ev.get("markets", [])
                    if not mkts:
                        continue

                    m = mkts[0]
                    question = m.get("question", "")
                    end_date_str = m.get("endDate", "")
                    liquidity = float(m.get("liquidityNum") or m.get("liquidity") or 0.0)

                    # Parse clob token IDs
                    tok_raw = m.get("clobTokenIds", "[]")
                    toks = json.loads(tok_raw) if isinstance(tok_raw, str) else tok_raw
                    yes_token = toks[0] if len(toks) > 0 else ""
                    no_token  = toks[1] if len(toks) > 1 else ""

                    # Parse market-implied YES probability
                    prices_raw = m.get("outcomePrices", '["0.5","0.5"]')
                    prices_list = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
                    yes_price = float(prices_list[0]) if prices_list else 0.5

                    # Compute epoch timestamps
                    end_ts = epoch_ts + 300
                    seconds_remaining = max(0, end_ts - now_ts)
                    if seconds_remaining <= 0:
                        continue

                    market = ActiveFiveMinMarket(
                        asset=asset_upper,
                        slug=slug,
                        condition_id=str(m.get("conditionId") or m.get("condition_id") or m.get("conditionID") or ""),
                        question=question,
                        epoch_start_ts=epoch_ts,
                        epoch_end_ts=end_ts,
                        seconds_remaining=seconds_remaining,
                        yes_token_id=yes_token,
                        no_token_id=no_token,
                        yes_price=yes_price,
                        liquidity=liquidity,
                        market_id=str(m.get("id", "")),
                    )
                    LOGGER.info(
                        "[GammaFetcher] Active 5M market found: %s | condition_id=%s | YES=%.4f | %ds remaining",
                        slug, market.condition_id, yes_price, seconds_remaining,
                    )
                    markets.append(market)

                except Exception as exc:
                    LOGGER.debug("[GammaFetcher] Slug lookup failed %s: %s", slug, exc)

        markets = sorted(
            {market.epoch_start_ts: market for market in markets}.values(),
            key=lambda market: market.epoch_start_ts,
        )
        self._five_min_market_cache[asset_upper] = (
            now_monotonic + self._five_min_cache_ttl_seconds,
            markets,
        )
        if not markets:
            LOGGER.warning("[GammaFetcher] No active 5M market found for %s", asset)
        return markets

    def get_exact_5min_ptb(self, asset: str) -> ExactFiveMinMarket | None:
        """
        Fetch the exact Price To Beat for a 5-minute market directly from
        Gamma /markets?slug= endpoint.  Uses groupItemThreshold as the
        authoritative PTB (matches what Polymarket website displays).
        """
        asset_upper = asset.upper()
        slug_prefix = _ASSET_SLUG_PREFIX.get(asset_upper)
        if not slug_prefix:
            LOGGER.warning("[GammaFetcher] Unknown asset: %s", asset)
            return None

        now_ts = int(time.time())
        epoch_ts = int(now_ts // 300) * 300   # snap to 5-min boundary

        with httpx.Client(timeout=self.timeout) as client:
            for offset in (0, 300, -300):
                slug = f"{slug_prefix}-{epoch_ts + offset}"
                try:
                    resp = client.get(f"{_GAMMA_BASE}/markets?slug={slug}")
                    resp.raise_for_status()
                    data = resp.json()
                    if not data:
                        continue
                    m = data[0] if isinstance(data, list) else data

                    # groupItemThreshold is the exact PTB Polymarket uses
                    threshold_raw = m.get("groupItemThreshold") or "0"
                    try:
                        ptb = float(str(threshold_raw).replace(",", ""))
                    except (ValueError, TypeError):
                        ptb = 0.0

                    # Token IDs
                    tok_raw = m.get("clobTokenIds", "[]")
                    toks = json.loads(tok_raw) if isinstance(tok_raw, str) else tok_raw
                    yes_token = toks[0] if len(toks) > 0 else ""
                    no_token  = toks[1] if len(toks) > 1 else ""

                    # YES/NO prices
                    prices_raw = m.get("outcomePrices", '["0.5","0.5"]')
                    prices_list = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
                    yes_price = float(prices_list[0]) if prices_list else 0.5
                    no_price  = float(prices_list[1]) if len(prices_list) > 1 else 1.0 - yes_price

                    # End date → epoch timestamps
                    end_date_str = m.get("endDate", "")
                    try:
                        from datetime import datetime, timezone
                        end_dt = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                        end_ts = int(end_dt.timestamp())
                        start_ts = end_ts - 300
                    except Exception:
                        start_ts = epoch_ts + offset
                        end_ts   = start_ts + 300

                    seconds_remaining = max(0, end_ts - now_ts)
                    liquidity = float(m.get("liquidityNum") or m.get("liquidity") or 0.0)

                    market = ExactFiveMinMarket(
                        asset=asset_upper,
                        slug=slug,
                        condition_id=str(m.get("conditionId") or m.get("condition_id") or m.get("conditionID") or ""),
                        market_id=str(m.get("id", "")),
                        question=m.get("question", ""),
                        price_to_beat=ptb,
                        yes_price=yes_price,
                        no_price=no_price,
                        epoch_start_ts=start_ts,
                        epoch_end_ts=end_ts,
                        seconds_remaining=seconds_remaining,
                        liquidity=liquidity,
                        yes_token_id=yes_token,
                        no_token_id=no_token,
                    )
                    LOGGER.info(
                        "[GammaFetcher] Exact PTB for %s: $%.4f | slug=%s | condition_id=%s | %ds remaining",
                        asset_upper, ptb, slug, market.condition_id, seconds_remaining,
                    )
                    return market

                except Exception as exc:
                    LOGGER.debug("[GammaFetcher] Exact PTB lookup failed %s: %s", slug, exc)

        LOGGER.warning("[GammaFetcher] Could not fetch exact PTB for %s", asset_upper)
        return None
