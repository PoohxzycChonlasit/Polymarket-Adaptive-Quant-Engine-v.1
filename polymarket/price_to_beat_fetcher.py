"""
price_to_beat_fetcher.py
========================
ดึง Price To Beat (groupItemThreshold) ของ 5-minute Up/Down markets
สำหรับ BTC, ETH, SOL, XRP, DOGE, HYPE, BNB จาก Polymarket Gamma API

Strategy:
  1. Fetch events จาก Gamma API → filter ด้วย "5 min" ใน title/question
  2. หา market ที่ active + ยังไม่ close ในแต่ละ round
  3. ดึง current price จาก Coinbase REST API (เพราะ 5M ใช้ Coinbase feed)
  4. Return structured data พร้อม PTB comparison
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from utils.rate_limiter import coinbase_limiter, gamma_limiter

LOGGER = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

GAMMA_BASE = "https://gamma-api.polymarket.com"
COINBASE_BASE = "https://api.coinbase.com/v2/prices"
CLOB_BASE = "https://clob.polymarket.com"

# Mapping: asset name → Coinbase product ID + Gamma market keywords
ASSET_CONFIG: dict[str, dict[str, str]] = {
    "BTC": {
        "coinbase_pair": "BTC-USD",
        "keywords": ["bitcoin", "btc"],
        "symbol": "₿",
    },
    "ETH": {
        "coinbase_pair": "ETH-USD",
        "keywords": ["ethereum", "eth"],
        "symbol": "Ξ",
    },
    "SOL": {
        "coinbase_pair": "SOL-USD",
        "keywords": ["solana", "sol"],
        "symbol": "◎",
    },
    "XRP": {
        "coinbase_pair": "XRP-USD",
        "keywords": ["xrp", "ripple"],
        "symbol": "✕",
    },
    "DOGE": {
        "coinbase_pair": "DOGE-USD",
        "keywords": ["dogecoin", "doge"],
        "symbol": "Ð",
    },
    "HYPE": {
        "coinbase_pair": "HYPE-USD",
        "keywords": ["hyperliquid", "hype"],
        "symbol": "H",
    },
    "BNB": {
        "coinbase_pair": "BNB-USD",
        "keywords": ["bnb", "binance"],
        "symbol": "⬡",
    },
}

# ──────────────────────────────────────────────────────────────────────────────
# Data Classes
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class MarketRound:
    """ข้อมูล 1 รอบของ 5-minute market"""
    asset: str
    symbol: str
    market_id: str
    condition_id: str
    question: str
    price_to_beat: float           # จาก groupItemThreshold หรือ parse จาก question
    current_price: float           # ราคา Coinbase ล่าสุด
    yes_price: float               # ราคา YES token (implied prob)
    no_price: float                # ราคา NO token
    end_date: str                  # เวลาหมดรอบ
    seconds_remaining: float       # วินาทีที่เหลือ
    is_above_ptb: bool             # current > price_to_beat
    price_diff_pct: float          # % ต่างจาก PTB
    liquidity: float
    volume_24hr: float
    clob_token_ids: list[str] = field(default_factory=list)
    source: str = "coinbase"


@dataclass
class FetchResult:
    """ผลการ fetch ทั้งหมด"""
    timestamp_utc: str
    markets: list[MarketRound]
    errors: list[str] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Fetcher
# ──────────────────────────────────────────────────────────────────────────────


class PriceToBeatFetcher:
    """
    Fetches Price To Beat data สำหรับ 7 coin 5-minute markets บน Polymarket
    
    Price To Beat = threshold price ที่ถ้า coin close >= PTB → YES wins
    Source: Gamma API `groupItemThreshold` field หรือ parse จาก question text
    """

    def __init__(self, timeout: float = 10.0) -> None:
        self._http = httpx.Client(
            timeout=httpx.Timeout(timeout),
            headers={"User-Agent": "PolyTradeBot/1.0"},
        )

    def close(self) -> None:
        self._http.close()

    # ── Coinbase Price ─────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def _get_coinbase_price(self, coinbase_pair: str) -> float:
        """ดึง current spot price จาก Coinbase Public API"""
        url = f"{COINBASE_BASE}/{coinbase_pair}/spot"
        try:
            coinbase_limiter.acquire()
            resp = self._http.get(url)
            resp.raise_for_status()
            data = resp.json()
            price = float(data["data"]["amount"])
            LOGGER.debug("Coinbase %s = $%.6f", coinbase_pair, price)
            return price
        except Exception as exc:
            LOGGER.warning("Coinbase price fetch failed for %s: %s", coinbase_pair, exc)
            raise

    def _get_all_coinbase_prices(self) -> dict[str, float]:
        """Fetch prices สำหรับทุก asset พร้อมกัน (ทีละตัว แต่เร็ว)"""
        prices: dict[str, float] = {}
        for asset, cfg in ASSET_CONFIG.items():
            try:
                prices[asset] = self._get_coinbase_price(cfg["coinbase_pair"])
            except Exception as exc:
                LOGGER.error("Cannot get price for %s: %s", asset, exc)
                prices[asset] = 0.0
        return prices

    # ── Gamma Events ───────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _fetch_gamma_events(self, limit: int = 200) -> list[dict[str, Any]]:
        """
        Fetch active events จาก Gamma API
        Filter หา 5-minute markets ที่ active
        """
        url = f"{GAMMA_BASE}/events"
        params = {
            "limit": limit,
            "active": "true",
            "closed": "false",
            "tag_slug": "crypto-prices",
        }
        try:
            gamma_limiter.acquire()
            resp = self._http.get(url, params=params)
            resp.raise_for_status()
            events: list[dict[str, Any]] = resp.json()
            LOGGER.info("Fetched %d crypto-prices events from Gamma", len(events))
            return events
        except Exception as exc:
            LOGGER.warning("Gamma events fetch failed: %s — trying fallback tags", exc)
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _fetch_gamma_markets_by_slug(self, slug_pattern: str) -> list[dict[str, Any]]:
        """Fallback: ค้นหา markets โดย slug pattern"""
        url = f"{GAMMA_BASE}/markets"
        params = {
            "limit": 50,
            "active": "true",
            "closed": "false",
        }
        gamma_limiter.acquire()
        resp = self._http.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    # ── Price To Beat Parsing ──────────────────────────────────────────────────

    def _parse_ptb_from_question(self, question: str) -> float | None:
        """
        Extract Price To Beat จาก question text
        Patterns เช่น:
        - "Will BTC be ABOVE $83,245 in the next 5 minutes?"
        - "Bitcoin up or down - 5 min? | $83,245.00"
        - "Will Bitcoin be above $83,245.50?"
        """
        # Pattern 1: $XX,XXX.XX หรือ $XXXXX
        patterns = [
            r'\$([0-9,]+\.?[0-9]*)',
            r'above\s+\$?([0-9,]+\.?[0-9]*)',
            r'below\s+\$?([0-9,]+\.?[0-9]*)',
            r'([0-9,]+\.?[0-9]+)\s*USD',
        ]
        for pattern in patterns:
            match = re.search(pattern, question, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(",", "")
                try:
                    price = float(price_str)
                    if price > 0:
                        return price
                except ValueError:
                    continue
        return None

    def _parse_ptb_from_threshold(self, threshold: str) -> float | None:
        """Parse groupItemThreshold ซึ่งอาจเป็น price string"""
        if not threshold or threshold in ("0", ""):
            return None
        try:
            val = float(threshold.replace(",", ""))
            if val > 0:
                return val
        except (ValueError, AttributeError):
            pass
        return None

    def _detect_asset_from_text(self, text: str) -> str | None:
        """Detect ว่า market นี้เกี่ยวกับ asset ไหน"""
        text_lower = text.lower()
        for asset, cfg in ASSET_CONFIG.items():
            for kw in cfg["keywords"]:
                if kw in text_lower:
                    return asset
        return None

    def _is_5min_market(self, text: str) -> bool:
        """ตรวจว่าเป็น 5-minute market"""
        text_lower = text.lower()
        return any(kw in text_lower for kw in [
            "5 min", "5min", "5-min", "5 minutes", "5minutes",
            "up or down", "up-or-down"
        ])

    # ── CLOB Orderbook Price ───────────────────────────────────────────────────

    def _get_yes_no_prices_from_market(self, market: dict[str, Any]) -> tuple[float, float]:
        """
        ดึง YES/NO price จาก outcomePrices field ของ market
        outcomePrices = "[\"0.55\", \"0.45\"]" → YES=0.55, NO=0.45
        """
        try:
            prices_raw = market.get("outcomePrices", "[\"0.5\", \"0.5\"]")
            if isinstance(prices_raw, str):
                prices = json.loads(prices_raw)
            else:
                prices = prices_raw
            yes_price = float(prices[0]) if prices else 0.5
            no_price = float(prices[1]) if len(prices) > 1 else 1.0 - yes_price
            return yes_price, no_price
        except Exception as exc:
            LOGGER.debug("yes/no price parse failed: %s", exc)
            return 0.5, 0.5

    # ── Main Fetch ─────────────────────────────────────────────────────────────

    def fetch(self) -> FetchResult:
        """
        Main entry point — fetch Price To Beat สำหรับทุก active 5M market
        Returns FetchResult พร้อม list[MarketRound]
        """
        now_utc = datetime.now(timezone.utc)
        timestamp = now_utc.isoformat()
        errors: list[str] = []
        rounds: list[MarketRound] = {}  # type: ignore[assignment]
        rounds = {}  # asset → MarketRound (เก็บ best/latest per asset)

        # 1. Get current prices จาก Coinbase
        coinbase_prices = self._get_all_coinbase_prices()

        # 2. Fetch events/markets จาก Gamma
        all_markets: list[dict[str, Any]] = []
        try:
            events = self._fetch_gamma_events(limit=300)
            for event in events:
                # แต่ละ event มี markets array
                for mkt in event.get("markets", []):
                    # ฝัง event title ลงใน market เพื่อ detection
                    mkt["_event_title"] = event.get("title", "")
                    mkt["_event_slug"] = event.get("slug", "")
                    mkt["_volume_24hr"] = event.get("volume24hr", 0.0)
                    all_markets.append(mkt)
        except Exception as exc:
            err = f"Gamma fetch failed: {exc}"
            LOGGER.error(err)
            errors.append(err)

        # 3. Fallback: fetch markets endpoint โดยตรง
        if not all_markets:
            try:
                all_markets = self._fetch_gamma_markets_by_slug("5-min")
            except Exception as exc:
                errors.append(f"Fallback markets fetch failed: {exc}")

        # 4. Filter + parse 5M markets
        for mkt in all_markets:
            # Check if active and not closed
            if mkt.get("closed", True):
                continue
            if not mkt.get("active", False):
                continue

            question = mkt.get("question", "")
            event_title = mkt.get("_event_title", "")
            slug = mkt.get("slug", "")
            combined_text = f"{question} {event_title} {slug}"

            # Check 5-minute keyword
            if not self._is_5min_market(combined_text):
                continue

            # Detect asset
            asset = self._detect_asset_from_text(combined_text)
            if not asset:
                continue

            # Parse Price To Beat
            threshold_str = str(mkt.get("groupItemThreshold", "0"))
            ptb = self._parse_ptb_from_threshold(threshold_str)
            if ptb is None or ptb <= 0:
                ptb = self._parse_ptb_from_question(question) or 0.0

            # Parse end date + seconds remaining
            end_date_str = mkt.get("endDate", "")
            seconds_remaining = 0.0
            try:
                if end_date_str:
                    end_dt = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                    delta = end_dt - now_utc
                    seconds_remaining = max(0.0, delta.total_seconds())
            except Exception as exc:
                LOGGER.debug("end_date parse failed for %r: %s", end_date_str, exc)

            # Get YES/NO prices
            yes_price, no_price = self._get_yes_no_prices_from_market(mkt)

            # CLOB token IDs
            clob_raw = mkt.get("clobTokenIds", "[]")
            try:
                clob_ids = json.loads(clob_raw) if isinstance(clob_raw, str) else clob_raw
            except Exception as exc:
                LOGGER.debug("clob token ids parse failed: %s", exc)
                clob_ids = []

            current_price = coinbase_prices.get(asset, 0.0)
            is_above = current_price >= ptb if ptb > 0 else False
            price_diff_pct = 0.0
            if ptb > 0 and current_price > 0:
                price_diff_pct = (current_price - ptb) / ptb * 100.0

            liquidity = float(mkt.get("liquidityNum") or mkt.get("liquidity") or 0.0)
            vol_24hr = float(mkt.get("volume24hr") or mkt.get("_volume_24hr") or 0.0)

            market_round = MarketRound(
                asset=asset,
                symbol=ASSET_CONFIG[asset]["symbol"],
                market_id=str(mkt.get("id", "")),
                condition_id=mkt.get("conditionId", ""),
                question=question[:100],
                price_to_beat=ptb,
                current_price=current_price,
                yes_price=yes_price,
                no_price=no_price,
                end_date=end_date_str,
                seconds_remaining=seconds_remaining,
                is_above_ptb=is_above,
                price_diff_pct=price_diff_pct,
                liquidity=liquidity,
                volume_24hr=vol_24hr,
                clob_token_ids=clob_ids,
            )

            # เก็บ market ที่ดีที่สุดต่อ asset (ยังไม่หมดเวลา + liquidity สูงสุด)
            existing = rounds.get(asset)
            if existing is None:
                rounds[asset] = market_round
            elif (
                market_round.seconds_remaining > 0
                and market_round.liquidity > existing.liquidity
            ):
                rounds[asset] = market_round

        return FetchResult(
            timestamp_utc=timestamp,
            markets=list(rounds.values()),
            errors=errors,
        )

    def __enter__(self) -> "PriceToBeatFetcher":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
