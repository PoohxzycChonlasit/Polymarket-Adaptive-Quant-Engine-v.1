"""
oracle_price_feed.py
====================
Thread-safe Polymarket-synced price oracle.

Strategy:
  - Polymarket uses Coinbase Advanced Trade API spot prices as the oracle
    for their 5-minute Up/Down crypto markets.
  - This module fetches the spot price at exactly the 5-minute epoch boundary
    (the "Price To Beat") and streams the current live price.
  - Active 5-minute market windows are discovered from the Gamma API slug pattern:
    {asset}-updown-5m-{epoch_unix_timestamp}

Usage:
    feed = PolymarketOracleFeed()
    feed.start()
    ptb = feed.get_ptb("BTC")     # price at epoch start
    now = feed.get_current("BTC") # latest spot price
    info = feed.get_market_info("BTC")  # full market window info
    feed.stop()
"""
from __future__ import annotations

import asyncio
import atexit
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

LOGGER = logging.getLogger(__name__)

# ── Polymarket crypto-price API (Primary PTB source — openPrice = Chainlink strike) ──
_PM_CRYPTO_URL = "https://polymarket.com/api/crypto/crypto-price"

# Symbol names as the PM API expects them.
_PM_SYMBOL: dict[str, str] = {
    "BTC":  "BTC",
    "ETH":  "ETH",
}

# ── Coinbase REST (live oracle + epoch-candle fallback) ───────────────────────
_CB_SPOT_URL   = "https://api.coinbase.com/v2/prices/{pair}/spot"
_CB_CANDLE_URL = "https://api.exchange.coinbase.com/products/{pair}/candles?granularity=60"

# ── Gamma API for market metadata (slug / token IDs / groupItemThreshold) ────
_GAMMA_BASE = "https://gamma-api.polymarket.com"

# Asset → Coinbase pair + Gamma slug prefix
ASSET_CONFIG: dict[str, dict] = {
    "BTC":  {"coinbase_pair": "BTC-USD",  "slug_prefix": "btc-updown-5m"},
    "ETH":  {"coinbase_pair": "ETH-USD",  "slug_prefix": "eth-updown-5m"},
}


@dataclass
class MarketWindow:
    """Metadata for a single 5-minute Polymarket window."""
    asset: str
    slug: str
    question: str
    epoch_start_ts: int      # Unix ts divisible by 300
    epoch_end_ts: int        # epoch_start_ts + 300
    price_to_beat: float     # Coinbase spot price at epoch start (oracle reference)
    yes_token_id: str
    yes_price: float         # current PM market-implied YES probability


@dataclass
class OraclePriceState:
    """Live price state for one asset."""
    asset: str
    current_price: float = 0.0
    epoch_start_ts: int = 0
    price_to_beat: float = 0.0
    seconds_remaining: int = 0
    is_above_ptb: bool = False
    price_diff_pct: float = 0.0
    market: MarketWindow | None = None
    last_updated: float = field(default_factory=time.time)


class PolymarketOracleFeed:
    """
    Continuously polls Coinbase Advanced Trade for live oracle prices
    and syncs with the 5-minute Polymarket epoch clock.

    Thread architecture:
        _price_thread  → 1s Coinbase spot price updates (never blocked by PTB logic)
        _thread        → epoch detection + parallel PTB fetch + 30s retry for unconfirmed
        _ws_thread     → Polymarket RTDS WebSocket for binary YES prices
    """

    _WS_URL = "wss://ws-live-data.polymarket.com"

    def __init__(self, refresh_interval: float = 5.0, timeout: float = 8.0) -> None:
        self._timeout = timeout
        self._http = self._make_http_client(timeout)
        self._refresh_interval = refresh_interval
        self._state: dict[str, OraclePriceState] = {
            asset: OraclePriceState(asset=asset)
            for asset in ASSET_CONFIG
        }
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._price_thread: threading.Thread | None = None
        self._ws_thread: threading.Thread | None = None
        self._start_stop_lock = threading.RLock()
        self._stop_event = threading.Event()
        # token_id → asset name, populated as Gamma markets are discovered
        self._token_map: dict[str, str] = {}
        self._ws_connected: bool = False
        self._current_epoch: int = 0
        self._ws_loop_ref: asyncio.AbstractEventLoop | None = None
        self._ws_connection = None
        self._atexit_registered = False

    @staticmethod
    def _make_http_client(timeout: float) -> httpx.Client:
        transport = httpx.HTTPTransport(retries=3)
        return httpx.Client(
            transport=transport,
            timeout=httpx.Timeout(timeout),
            headers={"User-Agent": "PolyTradeBot/1.0"},
        )

    def _safe_log(self, level: int, message: str, *args: object) -> None:
        try:
            LOGGER.log(level, message, *args)
        except (ValueError, OSError, RuntimeError):
            pass

    # ── Public API ──────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start background threads: price polling, epoch/PTB loop, WebSocket."""
        with self._start_stop_lock:
            if self.is_running():
                return
            if getattr(self._http, "is_closed", False):
                self._http = self._make_http_client(self._timeout)
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, daemon=True, name="OracleFeed")
            self._thread.start()
            self._price_thread = threading.Thread(target=self._price_loop, daemon=True, name="OraclePriceFeed")
            self._price_thread.start()
            self._ws_thread = threading.Thread(target=self._ws_run, daemon=True, name="OracleWSFeed")
            self._ws_thread.start()
            if not self._atexit_registered:
                atexit.register(self.stop)
                self._atexit_registered = True
            self._safe_log(logging.INFO, "[OracleFeed] Started (price=1s, epoch=parallel, WebSocket)")

    def stop(self, join_timeout: float = 5.0) -> None:
        """Stop all oracle background work and wait briefly for clean exit."""
        with self._start_stop_lock:
            self._stop_event.set()
            self._signal_ws_shutdown()
            for thread in self._background_threads():
                if thread and thread.is_alive() and thread is not threading.current_thread():
                    thread.join(timeout=join_timeout)
            self._ws_connected = False
            try:
                self._http.close()
            except Exception:
                pass
            if self._atexit_registered:
                try:
                    atexit.unregister(self.stop)
                except Exception:
                    pass
                self._atexit_registered = False
            self._safe_log(logging.INFO, "[OracleFeed] Stopped.")

    def close(self) -> None:
        self.stop()

    def shutdown(self) -> None:
        self.stop()

    def is_running(self) -> bool:
        return any(thread is not None and thread.is_alive() for thread in self._background_threads())

    def _background_threads(self) -> tuple[threading.Thread | None, threading.Thread | None, threading.Thread | None]:
        return (self._thread, self._price_thread, self._ws_thread)

    def _signal_ws_shutdown(self) -> None:
        loop = self._ws_loop_ref
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

    @property
    def ws_connected(self) -> bool:
        return self._ws_connected

    def get_state(self, asset: str) -> OraclePriceState:
        """Return live oracle state for an asset (thread-safe snapshot)."""
        with self._lock:
            state = self._state.get(asset.upper())
            if state is None:
                return OraclePriceState(asset=asset.upper())
            # Rebuild seconds_remaining dynamically
            now = int(time.time())
            epoch = now - (now % 300)
            end_ts = epoch + 300
            state.seconds_remaining = max(0, end_ts - now)
            state.epoch_start_ts = epoch
            return state

    def get_ws_sync_status(self) -> str:
        """Return a human-readable WebSocket sync status string."""
        if self._ws_connected:
            return "✅ Synced"
        return "⚠️  REST only"

    def get_ptb(self, asset: str) -> float:
        return self.get_state(asset).price_to_beat

    def get_current_price(self, asset: str) -> float:
        return self.get_state(asset).current_price

    def get_market_window(self, asset: str) -> MarketWindow | None:
        return self.get_state(asset).market

    def format_log_line(self, asset: str) -> str:
        """Return a clean log line: 'PTB: $X | Oracle: $X | Window: HH:MM-HH:MM'"""
        s = self.get_state(asset)
        ptb_str = f"${s.price_to_beat:,.4f}" if s.price_to_beat > 0 else "N/A"
        cur_str = f"${s.current_price:,.4f}" if s.current_price > 0 else "N/A"
        direction = "^ABOVE" if s.is_above_ptb else "vBELOW"

        if s.epoch_start_ts > 0:
            start_dt = datetime.fromtimestamp(s.epoch_start_ts, tz=timezone.utc)
            end_dt   = datetime.fromtimestamp(s.epoch_start_ts + 300, tz=timezone.utc)
            window   = f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')} UTC"
        else:
            window = "syncing..."

        return (
            f"[{asset}] Polymarket Price To Beat: {ptb_str} | "
            f"Oracle Price: {cur_str} ({direction} {abs(s.price_diff_pct):.4f}%) | "
            f"Market Window: {window} | {s.seconds_remaining}s remaining"
        )

    # ── Background loops ─────────────────────────────────────────────────────

    def _price_loop(self) -> None:
        """Dedicated 1s live Coinbase price updates — never blocked by PTB logic."""
        while not self._stop_event.is_set():
            self._refresh_live_prices()
            self._stop_event.wait(1.0)

    def _run_loop(self) -> None:
        """Epoch detection + parallel PTB fetch + 30s Chainlink-lock polling."""
        last_epoch = 0
        ptb_retry_until = 0.0

        while not self._stop_event.is_set():
            now_ts = int(time.time())
            epoch = now_ts - (now_ts % 300)

            if epoch != last_epoch:
                LOGGER.info("[OracleFeed] New 5-min epoch: %s — fetching PTBs in parallel", epoch)
                self._current_epoch = epoch
                self._refresh_ptb_at_epoch(epoch)
                last_epoch = epoch
                # Keep polling PM API for 30s — PM CDN cache may be stale at t=0
                # Chainlink price typically locks within 5-15s of epoch start
                ptb_retry_until = time.monotonic() + 30.0

            elif time.monotonic() < ptb_retry_until:
                # Re-fetch PM API for all assets every 2s; update if value has changed.
                # This catches the Chainlink lock even if the initial fetch got cached stale data.
                self._poll_pm_api_updates(epoch)

            self._stop_event.wait(2.0)

    def _poll_pm_api_updates(self, epoch_ts: int) -> None:
        """
        Re-query PM API for all assets and update PTB if the value has changed.
        Called every 2s for 30s after each epoch boundary to catch Chainlink cache flush.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _fetch_one(asset: str) -> tuple[str, float]:
            return asset, self._fetch_pm_crypto_ptb(asset, epoch_ts)

        if self._stop_event.is_set():
            return

        with ThreadPoolExecutor(max_workers=len(ASSET_CONFIG)) as pool:
            try:
                futures = {pool.submit(_fetch_one, a): a for a in ASSET_CONFIG}
            except RuntimeError as exc:
                if self._stop_event.is_set() or "interpreter shutdown" in str(exc):
                    return
                raise
            for fut in as_completed(futures):
                if self._stop_event.is_set():
                    return
                asset, new_ptb = fut.result()
                if new_ptb <= 0:
                    continue
                with self._lock:
                    old_ptb = self._state[asset].price_to_beat
                if abs(new_ptb - old_ptb) > 0.0001:
                    with self._lock:
                        self._state[asset].price_to_beat = new_ptb
                    LOGGER.info(
                        "[OracleFeed] ✅ %s PTB updated $%.4f → $%.4f (Chainlink cache flushed)",
                        asset, old_ptb, new_ptb,
                    )

    def _refresh_ptb_at_epoch(self, epoch_ts: int) -> None:
        """
        Fetch Price To Beat for all assets in parallel at epoch boundary.

        Priority chain (highest → lowest accuracy):
          1. polymarket.com/api/crypto/crypto-price  openPrice  ← Chainlink strike, verified
          2. gamma-api.polymarket.com groupItemThreshold         ← Polymarket on-chain ref
          3. Coinbase 1-min candle at epoch_ts                   ← last-resort approximation
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _fetch_one(asset: str, cfg: dict) -> tuple[str, float, "MarketWindow | None", str]:
            market = self._fetch_gamma_market(asset, cfg["slug_prefix"], epoch_ts)
            # Priority 1: PM crypto-price API (Chainlink strike — authoritative)
            ptb = self._fetch_pm_crypto_ptb(asset, epoch_ts)
            if ptb > 0:
                return asset, ptb, market, "pm_api"
            # Priority 2: Gamma groupItemThreshold (Polymarket on-chain ref)
            if market and market.price_to_beat > 0:
                return asset, market.price_to_beat, market, "gamma"
            # Priority 3: Coinbase candle (placeholder only — 30s retry will correct it)
            ptb_fallback = self._fetch_epoch_price(cfg["coinbase_pair"], epoch_ts)
            return asset, ptb_fallback, market, "coinbase"

        if self._stop_event.is_set():
            return

        with ThreadPoolExecutor(max_workers=len(ASSET_CONFIG)) as pool:
            try:
                futures = {pool.submit(_fetch_one, a, c): a for a, c in ASSET_CONFIG.items()}
            except RuntimeError as exc:
                if self._stop_event.is_set() or "interpreter shutdown" in str(exc):
                    return
                raise
            for fut in as_completed(futures):
                if self._stop_event.is_set():
                    return
                asset, ptb, market, source = fut.result()
                with self._lock:
                    if market:
                        self._state[asset].market = market
                    if ptb > 0:
                        self._state[asset].price_to_beat = ptb
                if source == "pm_api":
                    LOGGER.info("[OracleFeed] ✅ %s PTB = $%.4f  [PM API] (epoch=%s)", asset, ptb, epoch_ts)
                elif source == "gamma":
                    LOGGER.info("[OracleFeed] ✅ %s PTB = $%.4f  [Gamma] (epoch=%s)", asset, ptb, epoch_ts)
                elif ptb > 0:
                    LOGGER.warning(
                        "[OracleFeed] ⚠️  %s PTB = $%.4f [Coinbase placeholder] — 30s retry active",
                        asset, ptb,
                    )
                else:
                    LOGGER.warning("[OracleFeed] ⚠️  %s PTB unavailable at epoch start — retrying", asset)

    def _refresh_live_prices(self) -> None:
        """Fetch current Coinbase Advanced Trade spot prices."""
        for asset, cfg in ASSET_CONFIG.items():
            pair = cfg["coinbase_pair"]
            price = self._fetch_coinbase_spot(pair)
            if price <= 0:
                continue

            with self._lock:
                state = self._state[asset]
                state.current_price = price
                state.last_updated = time.time()

                ptb = state.price_to_beat
                if ptb > 0:
                    state.is_above_ptb = price >= ptb
                    state.price_diff_pct = (price - ptb) / ptb * 100.0

    # ── Price fetching ────────────────────────────────────────────────────────

    def _fetch_pm_crypto_ptb(self, asset: str, epoch_ts: int) -> float:
        """
        Fetch the exact Chainlink strike price (Price To Beat) from
        Polymarket's internal crypto-price API.

        Response field ``openPrice`` contains the Chainlink oracle price
        locked at the window open — verified drift < $0.01 vs website PTB.
        The endpoint returns data immediately (``incomplete=true``) so it
        is safe to call right at the epoch boundary.
        """
        pm_symbol = _PM_SYMBOL.get(asset.upper())
        if not pm_symbol:
            return 0.0

        # ISO-8601 window bounds  e.g. "2024-01-15T14:35:00Z"
        start_dt = datetime.fromtimestamp(epoch_ts,       tz=timezone.utc)
        end_dt   = datetime.fromtimestamp(epoch_ts + 300, tz=timezone.utc)
        event_start_iso = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_date_iso    = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        try:
            resp = self._http.get(
                _PM_CRYPTO_URL,
                params={
                    "symbol":         pm_symbol,
                    "eventStartTime": event_start_iso,
                    "variant":        "fiveminute",
                    "endDate":        end_date_iso,
                },
                timeout=6,
            )
            resp.raise_for_status()
            data = resp.json()

            # The API may return a list or a single object
            item = data[0] if isinstance(data, list) and data else data
            if not isinstance(item, dict):
                return 0.0

            # Try known field names for the strike / open price
            raw = (
                item.get("openPrice")
                or item.get("open_price")
                or item.get("strikePrice")
                or item.get("strike")
                or 0.0
            )
            ptb = float(raw) if raw else 0.0
            if ptb > 0:
                LOGGER.debug(
                    "[OracleFeed] PM crypto-price %s openPrice=$%.4f window=%s",
                    asset, ptb, event_start_iso,
                )
            return ptb

        except Exception as exc:
            LOGGER.debug("[OracleFeed] PM crypto-price fetch failed %s: %s", asset, exc)
            return 0.0

    def _fetch_coinbase_spot(self, pair: str) -> float:
        """
        Fetch current spot price from Coinbase Advanced Trade API.
        This is the SAME oracle Polymarket uses for its 5-minute markets.
        """
        try:
            url = _CB_SPOT_URL.format(pair=pair)
            resp = self._http.get(url)
            resp.raise_for_status()
            data = resp.json()
            price = float(data["data"]["amount"])
            LOGGER.debug("[OracleFeed] Coinbase spot %s = $%.6f", pair, price)
            return price
        except Exception as exc:
            LOGGER.debug("[OracleFeed] Spot fetch failed %s: %s", pair, exc)
            return 0.0

    def _fetch_epoch_price(self, pair: str, epoch_ts: int) -> float:
        """
        Get the Coinbase spot price at exactly epoch_ts using 1m candle history.
        Falls back to current spot if candle unavailable.
        """
        try:
            url = _CB_CANDLE_URL.format(pair=pair)
            resp = self._http.get(url)
            resp.raise_for_status()
            candles = resp.json()  # [[time, low, high, open, close, vol], ...]

            if not candles:
                return self._fetch_coinbase_spot(pair)

            # Look for candle matching epoch_ts exactly
            for candle in candles:
                c_time = int(candle[0])
                if c_time == epoch_ts:
                    ptb = float(candle[4])  # close price = oracle reference
                    LOGGER.debug("[OracleFeed] Epoch candle matched %s@%s = $%.6f", pair, epoch_ts, ptb)
                    return ptb

            # Not found: use most recent candle as best approximation (new epoch, 1st minute)
            # The candle at epoch_ts won't exist until the minute closes
            # → Use current spot instead (what Polymarket actually locks in)
            spot = self._fetch_coinbase_spot(pair)
            LOGGER.debug("[OracleFeed] No candle at %s for %s, using spot $%.6f", epoch_ts, pair, spot)
            return spot

        except Exception as exc:
            LOGGER.debug("[OracleFeed] Epoch price fetch failed %s: %s", pair, exc)
            return self._fetch_coinbase_spot(pair)

    # ── Gamma market discovery ────────────────────────────────────────────────

    def _fetch_gamma_market(self, asset: str, slug_prefix: str, epoch_ts: int) -> MarketWindow | None:
        """
        Find the active Polymarket 5-minute market for this epoch and asset.
        Extracts groupItemThreshold as the authoritative Price To Beat.
        Tries current epoch + next epoch slugs.
        """
        for ts_offset in (0, 300, -300):
            ts = epoch_ts + ts_offset
            slug = f"{slug_prefix}-{ts}"
            try:
                resp = self._http.get(f"{_GAMMA_BASE}/events?slug={slug}", timeout=6)
                data = resp.json()
                if not data:
                    continue
                ev = data[0] if isinstance(data, list) else data
                mkts = ev.get("markets", [])
                if not mkts:
                    continue
                m = mkts[0]
                q = m.get("question", "")
                end_date = m.get("endDate", "")
                tok_raw = m.get("clobTokenIds", "[]")
                toks = json.loads(tok_raw) if isinstance(tok_raw, str) else tok_raw
                yes_token = toks[0] if toks else ""
                no_token  = toks[1] if len(toks) > 1 else ""
                prices_raw = m.get("outcomePrices", '["0.5","0.5"]')
                prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
                yes_price = float(prices[0]) if prices else 0.5

                # ── KEY FIX: groupItemThreshold = exact Polymarket PTB ─────────
                ptb_from_gamma = 0.0
                threshold_raw = m.get("groupItemThreshold") or "0"
                try:
                    ptb_from_gamma = float(str(threshold_raw).replace(",", ""))
                    if ptb_from_gamma < 0:
                        ptb_from_gamma = 0.0
                except (ValueError, TypeError):
                    ptb_from_gamma = 0.0

                # Parse end timestamp from market endDate (most precise)
                try:
                    end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                    end_ts_val = int(end_dt.timestamp())
                    start_ts_val = end_ts_val - 300
                except Exception:
                    start_ts_val = ts
                    end_ts_val = ts + 300

                window = MarketWindow(
                    asset=asset,
                    slug=slug,
                    question=q,
                    epoch_start_ts=start_ts_val,
                    epoch_end_ts=end_ts_val,
                    price_to_beat=ptb_from_gamma,   # ← from Polymarket groupItemThreshold
                    yes_token_id=yes_token,
                    yes_price=yes_price,
                )
                if ptb_from_gamma > 0:
                    LOGGER.info(
                        "[OracleFeed] ✅ Gamma PTB for %s: $%.4f | slug=%s | YES=%.4f",
                        asset, ptb_from_gamma, slug, yes_price,
                    )
                else:
                    LOGGER.debug("[OracleFeed] Gamma market found %s but no groupItemThreshold", slug)

                # Store WS token ID for subscription
                with self._lock:
                    self._token_map[yes_token] = asset

                return window
            except Exception as exc:
                LOGGER.debug("[OracleFeed] Gamma market fetch failed %s/%s: %s", asset, slug, exc)

        return None

    # ── WebSocket listener (best-effort Polymarket RTDS) ─────────────────────

    def _ws_run(self) -> None:
        """Run the async WebSocket loop inside a dedicated thread."""
        try:
            asyncio.run(self._ws_loop())
        except Exception as exc:
            if not self._stop_event.is_set():
                self._safe_log(logging.DEBUG, "[OracleWSFeed] Thread exited: %s", exc)
        finally:
            self._ws_connected = False
            self._ws_loop_ref = None

    async def _ws_loop(self) -> None:
        """Connect to Polymarket RTDS WebSocket and update YES prices for binary tokens."""
        import websockets  # lazy import — optional dependency

        self._ws_loop_ref = asyncio.get_running_loop()
        delay = 5.0
        while not self._stop_event.is_set():
            try:
                async with websockets.connect(
                    self._WS_URL,
                    ping_interval=20,
                    ping_timeout=10,
                    additional_headers={"User-Agent": "PolyTradeBot/1.0"},
                ) as ws:
                    self._ws_connection = ws
                    self._ws_connected = True
                    delay = 5.0
                    self._safe_log(logging.INFO, "[OracleWSFeed] Connected to %s", self._WS_URL)

                    # Subscribe to known token IDs
                    with self._lock:
                        token_ids = list(self._token_map.keys())
                    if token_ids:
                        await ws.send(json.dumps({"type": "subscribe", "markets": token_ids}))
                        self._safe_log(logging.INFO, "[OracleWSFeed] Subscribed to %d tokens", len(token_ids))

                    async for raw in ws:
                        if self._stop_event.is_set():
                            break
                        try:
                            self._handle_ws_message(json.loads(raw))
                        except Exception as exc:
                            self._safe_log(logging.DEBUG, "[OracleWSFeed] Message parse error: %s", exc)
                    self._ws_connection = None

            except websockets.exceptions.ConnectionClosed as exc:
                self._ws_connected = False
                self._ws_connection = None
                if self._stop_event.is_set():
                    return
                self._safe_log(logging.DEBUG, "[OracleWSFeed] Connection closed unexpectedly: %s", exc)
                if await self._sleep_or_stop(delay):
                    return
                delay = min(delay * 2, 60.0)
            except Exception as exc:
                self._ws_connected = False
                self._ws_connection = None
                if self._stop_event.is_set():
                    return
                self._safe_log(logging.ERROR, "[OracleWSFeed] Exception (%s) - retry in %.0fs", exc, delay)
                if await self._sleep_or_stop(delay):
                    return
                delay = min(delay * 2, 60.0)

        self._ws_connected = False

    async def _sleep_or_stop(self, seconds: float) -> bool:
        deadline = time.monotonic() + max(0.0, seconds)
        while not self._stop_event.is_set() and time.monotonic() < deadline:
            await asyncio.sleep(min(0.25, max(0.0, deadline - time.monotonic())))
        return self._stop_event.is_set()

    def _handle_ws_message(self, msg: dict) -> None:
        """Parse a Polymarket RTDS message and update YES price for the matching asset."""
        event_type = msg.get("event_type") or msg.get("type", "")
        if event_type not in ("price_change", "last_trade_price", "tick"):
            return
        market_id = str(msg.get("market", msg.get("asset_id", "")))
        price_raw = msg.get("price") or msg.get("yes_price") or msg.get("data", {})
        if not market_id or not price_raw:
            return
        try:
            price = float(price_raw) if not isinstance(price_raw, dict) else float(price_raw.get("price", 0))
            with self._lock:
                asset = self._token_map.get(market_id)
                if asset and asset in self._state and self._state[asset].market:
                    self._state[asset].market.yes_price = price  # type: ignore[union-attr]
                    self._safe_log(logging.DEBUG, "[OracleWSFeed] %s YES price -> %.4f", asset, price)
        except (ValueError, TypeError):
            pass

    # ── Context manager ───────────────────────────────────────────────────────

    def __enter__(self) -> "PolymarketOracleFeed":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()
