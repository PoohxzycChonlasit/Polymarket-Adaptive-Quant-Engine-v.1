"""
Binance WebSocket + REST feed for real-time 5-min candle data.

Replaces Coinbase REST API (5–15 s delay) with <1 ms Binance data.
Singleton feed runs in a background daemon thread; all callers share one WS connection.
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from collections import deque
from typing import Optional

import httpx
import pandas as pd

LOGGER = logging.getLogger(__name__)

_BINANCE_REST = "https://api.binance.com/api/v3/klines"
_BINANCE_WS   = "wss://stream.binance.com/stream"

_SYMBOL_MAP: dict[str, str] = {
    "BTC":  "BTCUSDT",
    "ETH":  "ETHUSDT",
}

# Only these assets are fetched/subscribed — others in _SYMBOL_MAP kept for future use
_ACTIVE_ASSETS: set[str] = {"BTC", "ETH"}

_MAX_CANDLES = 120  # ~10 hours of 5-min bars
_READY_MIN   = 30   # minimum closed candles before feed is "ready" for signal


class BinanceFeed:
    """Thread-safe Binance 5-min kline feed.

    On start():
    1. Fetches last 100 closed candles per symbol via Binance REST (initial fill).
    2. Opens a combined WebSocket to receive new closed klines + live miniTicker prices.

    Use get_feed() for the module-level singleton.
    """

    def __init__(self) -> None:
        self._candles_5m: dict[str, deque] = {a: deque(maxlen=_MAX_CANDLES) for a in _ACTIVE_ASSETS}
        self._candles_1m: dict[str, deque] = {a: deque(maxlen=_MAX_CANDLES) for a in _ACTIVE_ASSETS}
        self._live: dict[str, float]    = {}
        self._lock    = threading.RLock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._ready: set[str] = set()
        self._stop_event = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ws_connection = None

    # ── Startup ────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start background feed thread. Idempotent."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread  = threading.Thread(target=self._run_loop, daemon=True, name="BinanceFeed")
        self._thread.start()
        # Wait up to 20 s for REST fill across active symbols
        deadline = time.time() + 20
        while time.time() < deadline:
            with self._lock:
                if len(self._ready) >= len(_ACTIVE_ASSETS):
                    break
            time.sleep(0.25)
        with self._lock:
            ready = sorted(self._ready)
        LOGGER.info("[BinanceFeed] Started — REST-ready symbols: %s", ready)

    def _run_loop(self) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_main())
        finally:
            self._loop = None
            loop.close()

    # ── Async internals ────────────────────────────────────────────────────

    async def _async_main(self) -> None:
        tasks = []
        for a in _ACTIVE_ASSETS:
            tasks.append(self._rest_fill(a, "5m", self._candles_5m))
            tasks.append(self._rest_fill(a, "1m", self._candles_1m))
        await asyncio.gather(*tasks)
        while self._running and not self._stop_event.is_set():
            try:
                await self._ws_loop()
            except Exception as exc:
                LOGGER.warning("[BinanceFeed] WS error — reconnecting in 3 s: %s", exc)
                await asyncio.sleep(3)

    async def _rest_fill(self, asset: str, interval: str, target_dict: dict) -> None:
        """Fetch closed candles from Binance REST for initial fill."""
        symbol = _SYMBOL_MAP[asset]
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(_BINANCE_REST, params={
                    "symbol": symbol, "interval": interval, "limit": 100,
                })
                resp.raise_for_status()
                rows = resp.json()
        except Exception as exc:
            LOGGER.error("[BinanceFeed] REST fill %s %s failed: %s", asset, interval, exc)
            if interval == "5m":
                with self._lock:
                    self._ready.add(asset)
            return

        candles = [
            {
                "time":   int(r[0]) // 1000,
                "open":   float(r[1]),
                "high":   float(r[2]),
                "low":    float(r[3]),
                "close":  float(r[4]),
                "volume": float(r[5]),
                "taker_buy_volume": float(r[9]),
            }
            for r in rows
        ]
        with self._lock:
            for c in candles:
                target_dict[asset].append(c)
            if candles and interval == "5m":
                self._live[asset] = candles[-1]["close"]
            if interval == "5m":
                self._ready.add(asset)
        LOGGER.debug("[BinanceFeed] REST fill %s %s: %d candles", asset, interval, len(candles))

    async def _ws_loop(self) -> None:
        """Subscribe to kline_5m + miniTicker streams for all symbols."""
        import websockets

        active_syms       = [_SYMBOL_MAP[a] for a in _ACTIVE_ASSETS if a in _SYMBOL_MAP]
        kline_5m_streams  = [f"{sym.lower()}@kline_5m"   for sym in active_syms]
        kline_1m_streams  = [f"{sym.lower()}@kline_1m"   for sym in active_syms]
        ticker_streams    = [f"{sym.lower()}@miniTicker" for sym in active_syms]
        url = f"{_BINANCE_WS}?streams={'/'.join(kline_5m_streams + kline_1m_streams + ticker_streams)}"

        LOGGER.info("[BinanceFeed] WS connecting (%d streams)…", len(kline_5m_streams) + len(kline_1m_streams) + len(ticker_streams))
        async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
            self._ws_connection = ws
            async for raw in ws:
                if not self._running or self._stop_event.is_set():
                    return
                try:
                    msg   = json.loads(raw)
                    data  = msg.get("data", {})
                    event = data.get("e", "")
                    sym   = data.get("s", "").upper()
                    asset = next((a for a, s in _SYMBOL_MAP.items() if s == sym), None)
                    if asset is None:
                        continue

                    if event == "kline" and data["k"]["x"]:  # closed kline only
                        k = data["k"]
                        interval = k.get("i", "")
                        candle = {
                            "time":   int(k["t"]) // 1000,
                            "open":   float(k["o"]),
                            "high":   float(k["h"]),
                            "low":    float(k["l"]),
                            "close":  float(k["c"]),
                            "volume": float(k["v"]),
                            "taker_buy_volume": float(k.get("V", 0.0)),
                        }
                        with self._lock:
                            target = self._candles_5m if interval == "5m" else self._candles_1m if interval == "1m" else None
                            if target is not None:
                                dq = target[asset]
                                if dq and dq[-1]["time"] == candle["time"]:
                                    dq[-1] = candle
                                else:
                                    dq.append(candle)
                            if interval == "5m":
                                self._live[asset] = candle["close"]

                    elif event == "24hrMiniTicker":
                        with self._lock:
                            self._live[asset] = float(data["c"])

                except Exception as exc:
                    LOGGER.debug("[BinanceFeed] Parse error: %s", exc)

    # ── Public API ─────────────────────────────────────────────────────────

    def get_candles_df(self, asset: str, interval: str = "5m") -> pd.DataFrame:
        """Return closed candles as DataFrame."""
        asset = asset.upper()
        if asset not in _SYMBOL_MAP:
            return pd.DataFrame()
        with self._lock:
            target = self._candles_5m if interval == "5m" else self._candles_1m
            rows = list(target[asset])
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        return df[["time", "low", "high", "open", "close", "volume", "taker_buy_volume"]].reset_index(drop=True)

    def get_live_price(self, asset: str) -> float:
        """Return latest known price (updated via miniTicker, <1 s latency)."""
        with self._lock:
            return self._live.get(asset.upper(), 0.0)

    def is_ready(self, asset: str) -> bool:
        """True if asset has ≥30 closed 5m candles."""
        with self._lock:
            return len(self._candles_5m.get(asset.upper(), [])) >= _READY_MIN

    def stop(self, join_timeout: float = 5.0) -> None:
        self._running = False
        self._stop_event.set()
        self._signal_ws_shutdown()
        if self._thread and self._thread.is_alive() and self._thread is not threading.current_thread():
            self._thread.join(timeout=join_timeout)

    def close(self) -> None:
        self.stop()

    def shutdown(self) -> None:
        self.stop()

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def _signal_ws_shutdown(self) -> None:
        loop = self._loop
        ws = self._ws_connection
        if loop is None or ws is None or loop.is_closed():
            return

        def _close_ws() -> None:
            try:
                asyncio.create_task(ws.close())
            except Exception:
                pass

        try:
            loop.call_soon_threadsafe(_close_ws)
        except Exception:
            pass


_feed: Optional[BinanceFeed] = None
_feed_lock = threading.Lock()


def get_feed() -> BinanceFeed:
    """Return the shared BinanceFeed singleton, started on first call."""
    global _feed
    if _feed is None or not _feed.is_running():
        with _feed_lock:
            if _feed is None or not _feed.is_running():
                _feed = BinanceFeed()
                _feed.start()
    return _feed
