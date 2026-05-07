from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_fixed

from config.settings import Settings, get_settings


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class CryptoMarketSnapshot:
    symbol: str
    source: str
    timestamp_utc: str
    last_price: float
    bid: float
    ask: float
    spread: float
    volume: float
    open_interest: float | None


class CryptoMarketDataFetcher:
    """Fetch normalized crypto market data from the configured exchange."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.timeout = httpx.Timeout(10.0)

    def fetch_snapshot(self, symbol: str) -> CryptoMarketSnapshot:
        """Fetch a market snapshot from the configured exchange."""
        if self.settings.crypto_exchange == "binance":
            return self._fetch_binance_snapshot(symbol)
        if self.settings.crypto_exchange == "coinbase":
            return self._fetch_coinbase_snapshot(symbol)
        return self._fetch_bybit_snapshot(symbol)

    def fetch_candles(self, symbol: str, limit: int = 120) -> pd.DataFrame:
        """Fetch recent OHLCV candles from the configured exchange."""
        if self.settings.crypto_exchange == "binance":
            return self._fetch_binance_candles(symbol=symbol, limit=limit)
        if self.settings.crypto_exchange == "coinbase":
            return self._fetch_coinbase_candles(symbol=symbol, limit=limit)
        return self._fetch_bybit_candles(symbol=symbol, limit=limit)

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def _fetch_binance_snapshot(self, symbol: str) -> CryptoMarketSnapshot:
        normalized_symbol = symbol.replace("/", "")
        base_url = "https://api.binance.com"
        ticker_url = f"{base_url}/api/v3/ticker/24hr"
        book_url = f"{base_url}/api/v3/ticker/bookTicker"
        LOGGER.info("Fetching Binance market data | symbol=%s", normalized_symbol)

        with httpx.Client(timeout=self.timeout) as client:
            ticker_response = client.get(ticker_url, params={"symbol": normalized_symbol})
            ticker_response.raise_for_status()
            ticker_payload = ticker_response.json()

            book_response = client.get(book_url, params={"symbol": normalized_symbol})
            book_response.raise_for_status()
            book_payload = book_response.json()

        bid = float(book_payload["bidPrice"])
        ask = float(book_payload["askPrice"])
        last_price = float(ticker_payload["lastPrice"])
        timestamp_ms = int(ticker_payload["closeTime"])
        timestamp_utc = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC).isoformat().replace("+00:00", "Z")
        spread = max(ask - bid, 0.0)
        volume = float(ticker_payload["quoteVolume"])

        return CryptoMarketSnapshot(
            symbol=symbol,
            source="binance",
            timestamp_utc=timestamp_utc,
            last_price=last_price,
            bid=bid,
            ask=ask,
            spread=spread,
            volume=volume,
            open_interest=None,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def _fetch_binance_candles(self, symbol: str, limit: int) -> pd.DataFrame:
        normalized_symbol = symbol.replace("/", "")
        url = "https://api.binance.com/api/v3/klines"
        LOGGER.info("Fetching Binance candles | symbol=%s | limit=%s", normalized_symbol, limit)

        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                url,
                params={"symbol": normalized_symbol, "interval": self.settings.crypto_timeframe, "limit": limit},
            )
            response.raise_for_status()
            payload = response.json()

        frame = pd.DataFrame(
            payload,
            columns=[
                "open_time",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
                "quote_asset_volume",
                "number_of_trades",
                "taker_buy_base_asset_volume",
                "taker_buy_quote_asset_volume",
                "ignore",
            ],
        )
        frame = frame[["open_time", "open", "high", "low", "close", "volume"]].copy()
        frame["timestamp"] = pd.to_datetime(frame["open_time"], unit="ms", utc=True)
        for column in ["open", "high", "low", "close", "volume"]:
            frame[column] = frame[column].astype(float)
        return frame[["timestamp", "open", "high", "low", "close", "volume"]]

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def _fetch_bybit_snapshot(self, symbol: str) -> CryptoMarketSnapshot:
        normalized_symbol = symbol.replace("/", "")
        base_url = "https://api.bybit.com"
        ticker_url = f"{base_url}/v5/market/tickers"
        orderbook_url = f"{base_url}/v5/market/orderbook"
        LOGGER.info("Fetching Bybit market data | symbol=%s", normalized_symbol)

        with httpx.Client(timeout=self.timeout) as client:
            ticker_response = client.get(ticker_url, params={"category": "spot", "symbol": normalized_symbol})
            ticker_response.raise_for_status()
            ticker_payload = ticker_response.json()["result"]["list"][0]

            orderbook_response = client.get(orderbook_url, params={"category": "spot", "symbol": normalized_symbol, "limit": 1})
            orderbook_response.raise_for_status()
            orderbook_payload = orderbook_response.json()["result"]

        bid = float(orderbook_payload["b"][0][0])
        ask = float(orderbook_payload["a"][0][0])
        last_price = float(ticker_payload["lastPrice"])
        timestamp_ms = int(orderbook_payload["ts"])
        timestamp_utc = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC).isoformat().replace("+00:00", "Z")
        spread = max(ask - bid, 0.0)
        volume = float(ticker_payload.get("turnover24h", 0.0))
        open_interest = float(ticker_payload["openInterest"]) if ticker_payload.get("openInterest") else None

        return CryptoMarketSnapshot(
            symbol=symbol,
            source="bybit",
            timestamp_utc=timestamp_utc,
            last_price=last_price,
            bid=bid,
            ask=ask,
            spread=spread,
            volume=volume,
            open_interest=open_interest,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def _fetch_bybit_candles(self, symbol: str, limit: int) -> pd.DataFrame:
        normalized_symbol = symbol.replace("/", "")
        url = "https://api.bybit.com/v5/market/kline"
        interval = self.settings.crypto_timeframe.replace("m", "")
        LOGGER.info("Fetching Bybit candles | symbol=%s | limit=%s", normalized_symbol, limit)

        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                url,
                params={"category": "spot", "symbol": normalized_symbol, "interval": interval, "limit": limit},
            )
            response.raise_for_status()
            payload = response.json()["result"]["list"]

        frame = pd.DataFrame(payload, columns=["open_time", "open", "high", "low", "close", "volume", "turnover"])
        frame["timestamp"] = pd.to_datetime(frame["open_time"].astype(int), unit="ms", utc=True)
        for column in ["open", "high", "low", "close", "volume"]:
            frame[column] = frame[column].astype(float)
        frame = frame.sort_values("timestamp").reset_index(drop=True)
        return frame[["timestamp", "open", "high", "low", "close", "volume"]]

    # ------------------------------------------------------------------
    # Coinbase Advanced Trade  (public REST — no auth required for market data)
    # Pairs use USD quote: BTC/USD, ETH/USD
    # ------------------------------------------------------------------

    @staticmethod
    def _to_coinbase_product(symbol: str) -> str:
        """Convert BTC/USD or BTC/USDT to Coinbase product_id format BTC-USD."""
        base, quote = symbol.upper().split("/")
        # Coinbase spot uses USD not USDT; map USDT → USD silently.
        if quote == "USDT":
            quote = "USD"
        return f"{base}-{quote}"

    @staticmethod
    def _coinbase_granularity(timeframe: str) -> str:
        """Map Freqtrade-style timeframe (5m, 15m, 1h …) to Coinbase granularity string."""
        mapping: dict[str, str] = {
            "1m": "ONE_MINUTE",
            "5m": "FIVE_MINUTE",
            "15m": "FIFTEEN_MINUTE",
            "30m": "THIRTY_MINUTE",
            "1h": "ONE_HOUR",
            "6h": "SIX_HOUR",
            "1d": "ONE_DAY",
        }
        return mapping.get(timeframe, "FIVE_MINUTE")

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def _fetch_coinbase_snapshot(self, symbol: str) -> CryptoMarketSnapshot:
        product_id = self._to_coinbase_product(symbol)
        base_url = "https://api.coinbase.com/api/v3/brokerage"
        ticker_url = f"{base_url}/market/products/{product_id}"
        book_url = f"{base_url}/market/product_book"
        LOGGER.info("Fetching Coinbase market data | product=%s", product_id)

        with httpx.Client(timeout=self.timeout) as client:
            ticker_response = client.get(ticker_url)
            ticker_response.raise_for_status()
            ticker_payload = ticker_response.json()

            book_response = client.get(book_url, params={"product_id": product_id, "limit": 1})
            book_response.raise_for_status()
            book_payload = book_response.json()["pricebook"]

        last_price = float(ticker_payload["price"])
        volume = float(ticker_payload.get("volume_24h", 0.0))
        timestamp_utc = datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

        bids = book_payload.get("bids", [])
        asks = book_payload.get("asks", [])
        bid = float(bids[0]["price"]) if bids else last_price
        ask = float(asks[0]["price"]) if asks else last_price
        spread = max(ask - bid, 0.0)

        return CryptoMarketSnapshot(
            symbol=symbol,
            source="coinbase",
            timestamp_utc=timestamp_utc,
            last_price=last_price,
            bid=bid,
            ask=ask,
            spread=spread,
            volume=volume,
            open_interest=None,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def _fetch_coinbase_candles(self, symbol: str, limit: int) -> pd.DataFrame:
        product_id = self._to_coinbase_product(symbol)
        granularity = self._coinbase_granularity(self.settings.crypto_timeframe)
        url = f"https://api.coinbase.com/api/v3/brokerage/market/products/{product_id}/candles"
        LOGGER.info("Fetching Coinbase candles | product=%s | granularity=%s | limit=%s", product_id, granularity, limit)

        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, params={"granularity": granularity, "limit": min(limit, 300)})
            response.raise_for_status()
            payload = response.json()["candles"]

        frame = pd.DataFrame(payload)
        # Coinbase candle fields: start (unix epoch str), low, high, open, close, volume
        frame["timestamp"] = pd.to_datetime(frame["start"].astype(int), unit="s", utc=True)
        for column in ["open", "high", "low", "close", "volume"]:
            frame[column] = frame[column].astype(float)
        frame = frame.sort_values("timestamp").reset_index(drop=True)
        return frame[["timestamp", "open", "high", "low", "close", "volume"]]
