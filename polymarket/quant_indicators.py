import asyncio
import logging
import threading
import time
from typing import Dict, Optional
import httpx

LOGGER = logging.getLogger(__name__)

_FUTURES_API = "https://fapi.binance.com"
_DATA_API = "https://fapi.binance.com/futures/data"

_SYMBOL_MAP = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
}

class QuantIndicatorsFeed:
    """
    Polls Binance Futures for Quant Indicators (Open Interest, Long/Short Ratio).
    Runs in a background thread to avoid blocking the main trading loop.
    """
    def __init__(self) -> None:
        self._data: Dict[str, Dict[str, float]] = {
            a: {"open_interest": 0.0, "long_short_ratio": 0.0, "ls_long_pct": 0.0, "ls_short_pct": 0.0}
            for a in _SYMBOL_MAP
        }
        self._lock = threading.RLock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="QuantFeed")
        self._thread.start()
        LOGGER.info("[QuantFeed] Started background polling for %s", list(_SYMBOL_MAP.keys()))

    def _run_loop(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_main())
        finally:
            loop.close()

    async def _async_main(self) -> None:
        # Initial fill
        await self._poll_all()
        while self._running:
            await asyncio.sleep(15)  # Poll every 15 seconds
            await self._poll_all()

    async def _poll_all(self) -> None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            tasks = []
            for asset in _SYMBOL_MAP:
                tasks.append(self._fetch_oi(client, asset))
                tasks.append(self._fetch_ls_ratio(client, asset))
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _fetch_oi(self, client: httpx.AsyncClient, asset: str) -> None:
        symbol = _SYMBOL_MAP[asset]
        try:
            resp = await client.get(f"{_FUTURES_API}/fapi/v1/openInterest", params={"symbol": symbol})
            resp.raise_for_status()
            data = resp.json()
            with self._lock:
                self._data[asset]["open_interest"] = float(data.get("openInterest", 0.0))
        except Exception as e:
            LOGGER.debug(f"[QuantFeed] Failed to fetch OI for {asset}: {e}")

    async def _fetch_ls_ratio(self, client: httpx.AsyncClient, asset: str) -> None:
        symbol = _SYMBOL_MAP[asset]
        try:
            resp = await client.get(
                f"{_DATA_API}/globalLongShortAccountRatio", 
                params={"symbol": symbol, "period": "5m", "limit": 1}
            )
            resp.raise_for_status()
            data = resp.json()
            if data and len(data) > 0:
                latest = data[0]
                with self._lock:
                    self._data[asset]["long_short_ratio"] = float(latest.get("longShortRatio", 0.0))
                    self._data[asset]["ls_long_pct"] = float(latest.get("longAccount", 0.0))
                    self._data[asset]["ls_short_pct"] = float(latest.get("shortAccount", 0.0))
        except Exception as e:
            LOGGER.debug(f"[QuantFeed] Failed to fetch L/S ratio for {asset}: {e}")

    def get_quant_data(self, asset: str) -> Dict[str, float]:
        """Returns the latest quant metrics for the given asset."""
        asset = asset.upper()
        with self._lock:
            return dict(self._data.get(asset, {}))

    def stop(self) -> None:
        self._running = False


_quant_feed: Optional[QuantIndicatorsFeed] = None
_quant_lock = threading.Lock()

def get_quant_feed() -> QuantIndicatorsFeed:
    global _quant_feed
    if _quant_feed is None:
        with _quant_lock:
            if _quant_feed is None:
                _quant_feed = QuantIndicatorsFeed()
                _quant_feed.start()
    return _quant_feed
