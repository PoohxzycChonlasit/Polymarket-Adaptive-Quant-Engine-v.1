from __future__ import annotations

import asyncio
import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Callable

import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from config.settings import Settings, get_settings


LOGGER = logging.getLogger(__name__)

# Reconnect delay caps (seconds)
_RECONNECT_BASE = 2
_RECONNECT_MAX = 60


@dataclass(slots=True)
class LiveTick:
    symbol: str
    source: str
    timestamp_utc: str
    last_price: float
    bid: float
    ask: float
    spread: float
    volume_24h: float
    change_pct_24h: float


# ------------------------------------------------------------------
# Exchange-specific WebSocket configs
# ------------------------------------------------------------------

def _binance_ws_url(symbol: str) -> str:
    stream = symbol.replace("/", "").lower() + "@ticker"
    return f"wss://stream.binance.com:9443/ws/{stream}"


def _binance_parse(raw: str, symbol: str) -> LiveTick | None:
    try:
        data = json.loads(raw)
        if data.get("e") != "24hrTicker":
            return None
        last_price = float(data["c"])
        bid = float(data["b"])
        ask = float(data["a"])
        return LiveTick(
            symbol=symbol,
            source="binance",
            timestamp_utc=datetime.fromtimestamp(data["E"] / 1000, tz=UTC)
                .isoformat()
                .replace("+00:00", "Z"),
            last_price=last_price,
            bid=bid,
            ask=ask,
            spread=round(max(ask - bid, 0.0), 6),
            volume_24h=float(data["q"]),
            change_pct_24h=float(data["P"]),
        )
    except Exception:
        LOGGER.debug("Binance parse error for raw=%s", raw[:120])
        return None


def _bybit_ws_url(_symbol: str) -> str:
    return "wss://stream.bybit.com/v5/public/spot"


def _bybit_subscribe_msg(symbol: str) -> str:
    normalized = symbol.replace("/", "")
    return json.dumps({"op": "subscribe", "args": [f"tickers.{normalized}"]})


def _bybit_parse(raw: str, symbol: str) -> LiveTick | None:
    try:
        data = json.loads(raw)
        if data.get("topic", "").startswith("tickers.") and "data" in data:
            d = data["data"]
            last_price = float(d.get("lastPrice", 0))
            bid = float(d.get("bid1Price", last_price))
            ask = float(d.get("ask1Price", last_price))
            return LiveTick(
                symbol=symbol,
                source="bybit",
                timestamp_utc=datetime.fromtimestamp(data.get("ts", 0) / 1000, tz=UTC)
                    .isoformat()
                    .replace("+00:00", "Z"),
                last_price=last_price,
                bid=bid,
                ask=ask,
                spread=round(max(ask - bid, 0.0), 6),
                volume_24h=float(d.get("turnover24h", 0)),
                change_pct_24h=float(d.get("price24hPcnt", 0)) * 100,
            )
        return None
    except Exception:
        LOGGER.debug("Bybit parse error for raw=%s", raw[:120])
        return None


def _coinbase_ws_url(_symbol: str) -> str:
    return "wss://advanced-trade-ws.coinbase.com"


def _coinbase_subscribe_msg(symbol: str) -> str:
    base, quote = symbol.upper().split("/")
    if quote == "USDT":
        quote = "USD"
    product_id = f"{base}-{quote}"
    return json.dumps({"type": "subscribe", "product_ids": [product_id], "channel": "ticker"})


def _coinbase_parse(raw: str, symbol: str) -> LiveTick | None:
    try:
        data = json.loads(raw)
        events = data.get("events", [])
        for event in events:
            if event.get("type") == "update":
                for ticker in event.get("tickers", []):
                    last_price = float(ticker.get("price", 0))
                    bid = float(ticker.get("best_bid", last_price))
                    ask = float(ticker.get("best_ask", last_price))
                    return LiveTick(
                        symbol=symbol,
                        source="coinbase",
                        timestamp_utc=data.get("timestamp", datetime.now(tz=UTC)
                            .isoformat().replace("+00:00", "Z")),
                        last_price=last_price,
                        bid=bid,
                        ask=ask,
                        spread=round(max(ask - bid, 0.0), 6),
                        volume_24h=float(ticker.get("volume_24_h", 0)),
                        change_pct_24h=float(ticker.get("price_percent_chg_24_h", 0)),
                    )
        return None
    except Exception:
        LOGGER.debug("Coinbase parse error for raw=%s", raw[:120])
        return None


# ------------------------------------------------------------------
# Main feed class
# ------------------------------------------------------------------

class CryptoRealtimeFeed:
    """Stream live BTC (or any pair) ticks via WebSocket in a background thread.

    Usage::

        feed = CryptoRealtimeFeed(symbol="BTC/USDT", exchange="binance")
        feed.subscribe(lambda tick: print(tick.last_price))
        feed.start()
        # ... do other work ...
        feed.stop()
    """

    def __init__(
        self,
        symbol: str = "BTC/USDT",
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.symbol = symbol
        self.exchange = self.settings.crypto_exchange
        self._latest: LiveTick | None = None
        self._lock = threading.Lock()
        self._callbacks: list[Callable[[LiveTick], None]] = []
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def subscribe(self, callback: Callable[[LiveTick], None]) -> None:
        """Register a callback invoked on every new tick."""
        self._callbacks.append(callback)

    def get_latest(self) -> LiveTick | None:
        """Return the most recent tick (thread-safe)."""
        with self._lock:
            return self._latest

    def start(self) -> None:
        """Start the WebSocket stream in a background thread."""
        if self._thread and self._thread.is_alive():
            LOGGER.warning("Feed already running.")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="realtime-feed")
        self._thread.start()
        LOGGER.info("Realtime feed started | symbol=%s exchange=%s", self.symbol, self.exchange)

    def stop(self) -> None:
        """Signal the background thread to stop and wait for it."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        LOGGER.info("Realtime feed stopped.")

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_loop(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._stream_with_reconnect())
        finally:
            loop.close()

    async def _stream_with_reconnect(self) -> None:
        delay = _RECONNECT_BASE
        while not self._stop_event.is_set():
            task = asyncio.ensure_future(self._stream())
            try:
                while not task.done():
                    if self._stop_event.is_set():
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                        return
                    await asyncio.sleep(0.1)
                await task  # surface any exception
                delay = _RECONNECT_BASE
            except (ConnectionClosedError, ConnectionClosedOK):
                LOGGER.warning("WebSocket closed — reconnecting in %ss.", delay)
            except asyncio.CancelledError:
                return
            except Exception:
                LOGGER.exception("WebSocket error — reconnecting in %ss.", delay)
            if not self._stop_event.is_set():
                await asyncio.sleep(delay)
                delay = min(delay * 2, _RECONNECT_MAX)

    async def _stream(self) -> None:
        ws_url, subscribe_msg, parser = self._resolve_exchange()
        LOGGER.info("Connecting to %s", ws_url)
        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10) as ws:
            if subscribe_msg:
                await ws.send(subscribe_msg)
            async for raw in ws:
                if self._stop_event.is_set():
                    break
                tick = parser(raw, self.symbol)
                if tick is not None:
                    self._on_tick(tick)

    def _on_tick(self, tick: LiveTick) -> None:
        with self._lock:
            self._latest = tick
        for cb in self._callbacks:
            try:
                cb(tick)
            except Exception:
                LOGGER.exception("Callback raised an exception.")

    def _resolve_exchange(self) -> tuple[str, str | None, Callable[[str, str], LiveTick | None]]:
        if self.exchange == "binance":
            return _binance_ws_url(self.symbol), None, _binance_parse
        if self.exchange == "bybit":
            return _bybit_ws_url(self.symbol), _bybit_subscribe_msg(self.symbol), _bybit_parse
        if self.exchange == "coinbase":
            return _coinbase_ws_url(self.symbol), _coinbase_subscribe_msg(self.symbol), _coinbase_parse
        raise ValueError(f"Unsupported exchange for realtime feed: {self.exchange!r}")
