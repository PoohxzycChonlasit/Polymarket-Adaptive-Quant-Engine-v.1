from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from inspect import signature
from typing import Any

try:
    from py_clob_client_v2.client import ClobClient
    from py_clob_client_v2.clob_types import ApiCreds, OrderArgs, OrderType, BalanceAllowanceParams, AssetType
    _CLOB_AVAILABLE = True
except ImportError:  # pragma: no cover
    try:
        from py_clob_client.client import ClobClient
        from py_clob_client.clob_types import ApiCreds, OrderArgs, OrderType, BalanceAllowanceParams, AssetType
        _CLOB_AVAILABLE = True
    except ImportError:
        ClobClient = None  # type: ignore[assignment,misc]
        ApiCreds = None  # type: ignore[assignment,misc]
        OrderArgs = None  # type: ignore[assignment,misc]
        OrderType = None  # type: ignore[assignment,misc]
        BalanceAllowanceParams = None  # type: ignore[assignment,misc]
        AssetType = None  # type: ignore[assignment,misc]
        _CLOB_AVAILABLE = False

try:
    from web3 import Web3
    _WEB3_AVAILABLE = True
except ImportError:
    Web3 = None  # type: ignore[assignment,misc]
    _WEB3_AVAILABLE = False

from config.settings import get_settings

# USDC contracts on Polygon (6 decimals)
# Polymarket migrated to native USDC in 2024 — check both
_USDC_NATIVE  = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"  # Native USDC (primary)
_USDC_BRIDGED = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"  # USDC.e (bridged, legacy)
_POLYGON_RPC  = "https://polygon-rpc.com"
_USDC_ABI     = [{"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function","stateMutability":"view"}]


LOGGER = logging.getLogger(__name__)

BUY = "BUY"
SELL = "SELL"


@dataclass(slots=True)
class OrderbookSnapshot:
    token_id: str
    best_bid: float
    best_ask: float
    spread: float
    bid_size: float
    ask_size: float
    condition_id: str = ""
    timestamp_ms: int = 0
    age_seconds: float = 0.0
    raw_response: dict[str, Any] | None = None


class ClobOrderbookError(RuntimeError):
    """Structured market-data exception for orderbook diagnostics."""

    def __init__(
        self,
        category: str,
        message: str,
        *,
        token_id: str = "",
        exception_type: str = "",
        status_code: int | None = None,
        parse_failure: bool = False,
        api_failure: bool = False,
        retry_count: int = 0,
        error_class: str = "",
        cooldown_seconds_remaining: float = 0.0,
        circuit_open: bool = False,
        backoff_active: bool = False,
        error_rate: float = 0.0,
        recovery_count: int = 0,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.token_id = token_id
        self.exception_type = exception_type or self.__class__.__name__
        self.status_code = status_code
        self.parse_failure = parse_failure
        self.api_failure = api_failure
        self.retry_count = retry_count
        self.error_class = error_class
        self.cooldown_seconds_remaining = cooldown_seconds_remaining
        self.circuit_open = circuit_open
        self.backoff_active = backoff_active
        self.error_rate = error_rate
        self.recovery_count = recovery_count


@dataclass(slots=True)
class ClobOrderbookHealth:
    token_id: str
    consecutive_failures: int = 0
    cooldown_until: float = 0.0
    circuit_open_until: float = 0.0
    recent_failures: deque[float] = field(default_factory=deque)
    recent_requests: deque[float] = field(default_factory=deque)
    total_failures: int = 0
    total_successes: int = 0
    recovery_count: int = 0
    last_error_class: str = ""
    last_category: str = ""
    last_exception_type: str = ""
    last_status_code: int | None = None


@dataclass(slots=True)
class OrderReceipt:
    order_id: str
    status: str
    token_id: str
    side: str
    price: float
    size: float
    filled_size: float = 0.0
    remaining_size: float = 0.0
    created_at: str = ""
    order_type: str = "GTC"


@dataclass(slots=True)
class BalanceSnapshot:
    balance: float
    source: str
    wallet_address: str
    clob_balance: float = 0.0
    onchain_balance: float = 0.0
    proxy_wallet: str = ""
    funder_wallet: str = ""


class PolymarketClient:
    """Thin wrapper around py-clob-client for CLOB order flow."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client: Any | None = None
        self._market_data_client: Any | None = None
        # v3.2: Circuit breaker state
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0
        self._orderbook_health: defaultdict[str, ClobOrderbookHealth] = defaultdict(
            lambda: ClobOrderbookHealth(token_id="")
        )

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------

    def _require_clob(self) -> Any:
        if self._client is None:
            if not _CLOB_AVAILABLE:
                raise RuntimeError(
                    "py-clob-client is not installed. Run: pip install py-clob-client"
                )
            raise RuntimeError(
                "PolymarketClient not connected. Call connect() first."
            )
        return self._client

    def _require_market_data_client(self) -> Any:
        """Return a CLOB client usable for public market-data endpoints."""
        if self._market_data_client is not None:
            return self._market_data_client
        if self._client is not None:
            self._market_data_client = self._client
            return self._market_data_client
        if not _CLOB_AVAILABLE:
            raise RuntimeError(
                "py-clob-client is not installed. Run: pip install py-clob-client"
            )
        self._market_data_client = ClobClient(host=self.settings.polymarket_host)
        LOGGER.info(
            "[CLOB_MARKET_DATA] Public client ready host=%s",
            self.settings.polymarket_host,
        )
        return self._market_data_client

    def _now_iso(self) -> str:
        return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")

    def _get_order_type(self, order_type: str) -> Any:
        normalized = order_type.upper()
        if normalized not in {"GTC", "GTD", "FOK", "FAK"}:
            raise ValueError(f"order_type must be one of GTC, GTD, FOK, FAK; got {order_type!r}.")
        if OrderType is None:
            return normalized
        resolved = getattr(OrderType, normalized, None)
        if resolved is None:
            raise ValueError(f"Installed CLOB SDK does not expose OrderType.{normalized}.")
        return resolved

    def _order_args_accepts(self, field_name: str) -> bool:
        if OrderArgs is None:
            return False
        try:
            params = signature(OrderArgs).parameters
            return field_name in params
        except Exception:
            return False

    def _build_order_args(
        self,
        *,
        token_id: str,
        price: float,
        size: float,
        side: str,
        order_type: str,
        expiration: int | None,
        post_only: bool,
    ) -> Any:
        kwargs: dict[str, Any] = {
            "token_id": token_id,
            "price": price,
            "size": size,
            "side": side,
        }
        if expiration is not None and self._order_args_accepts("expiration"):
            kwargs["expiration"] = expiration
        elif order_type == "GTD" and expiration is not None:
            LOGGER.warning("[CLOB] GTD expiration requested but SDK OrderArgs does not expose expiration.")

        if post_only:
            if order_type not in {"GTC", "GTD"}:
                raise ValueError("post_only is only valid for resting limit orders GTC/GTD.")
            if self._order_args_accepts("post_only"):
                kwargs["post_only"] = True
            else:
                LOGGER.warning("[CLOB] post_only requested but SDK OrderArgs does not expose post_only.")

        if OrderArgs is None:
            return kwargs
        return OrderArgs(**kwargs)

    def _float_field(self, payload: dict[str, Any], *keys: str) -> float:
        for key in keys:
            if key in payload and payload[key] is not None:
                try:
                    return float(payload[key])
                except (TypeError, ValueError):
                    return 0.0
        return 0.0

    def _str_field(self, payload: dict[str, Any], *keys: str, default: str = "") -> str:
        for key in keys:
            value = payload.get(key)
            if value is not None:
                return str(value)
        return default

    def _exception_status_code(self, exc: Exception) -> int | None:
        for attr in ("status_code", "status"):
            value = getattr(exc, attr, None)
            if value is not None:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    pass
        response = getattr(exc, "response", None)
        if response is not None:
            for attr in ("status_code", "status"):
                value = getattr(response, attr, None)
                if value is not None:
                    try:
                        return int(value)
                    except (TypeError, ValueError):
                        pass
        return None

    def _orderbook_health_for(self, token_id: str) -> ClobOrderbookHealth:
        health = self._orderbook_health[token_id]
        if not health.token_id:
            health.token_id = token_id
        return health

    def _clob_error_class(self, category: str, status_code: int | None = None) -> str:
        if status_code == 429 or category == "clob_rate_limited":
            return "rate_limited"
        if status_code in {400, 404} or category == "clob_token_not_found":
            return "token_or_market_issue"
        if status_code in {401, 403} or category in {"clob_auth_or_client_issue", "clob_client_not_connected"}:
            return "auth_or_client_issue"
        if category in {"clob_timeout", "clob_empty_response"}:
            return "transient_api_issue"
        if status_code is not None and status_code >= 500:
            return "transient_api_issue"
        if category == "clob_http_error":
            return "transient_api_issue"
        return "transient_api_issue"

    def _clob_orderbook_category(self, exc: Exception, *, token_id: str) -> str:
        message = str(exc).lower()
        status_code = self._exception_status_code(exc)
        exc_name = exc.__class__.__name__.lower()
        if not token_id or "not connected" in message or "not installed" in message or "client_not_connected" in message:
            return "clob_client_not_connected"
        if "timeout" in message or "timed out" in message or "timeout" in exc_name:
            return "clob_timeout"
        if status_code == 429 or "rate limit" in message or "too many requests" in message:
            return "clob_rate_limited"
        if status_code in {401, 403} or "unauthorized" in message or "forbidden" in message:
            return "clob_auth_or_client_issue"
        if status_code in {400, 404} or "not found" in message or "unknown token" in message or "invalid token" in message:
            return "clob_token_not_found"
        if status_code is not None and status_code >= 400:
            return "clob_http_error"
        return "clob_http_error"

    def _wrap_orderbook_exception(self, exc: Exception, *, token_id: str) -> ClobOrderbookError:
        if isinstance(exc, ClobOrderbookError):
            return exc
        status_code = self._exception_status_code(exc)
        category = self._clob_orderbook_category(exc, token_id=token_id)
        return ClobOrderbookError(
            category,
            str(exc),
            token_id=token_id,
            exception_type=exc.__class__.__name__,
            status_code=status_code,
            parse_failure=False,
            api_failure=True,
            error_class=self._clob_error_class(category, status_code),
        )

    def _trim_orderbook_health(self, health: ClobOrderbookHealth, now: float) -> None:
        window = max(1, int(getattr(self.settings, "clob_circuit_breaker_window_seconds", 60)))
        cutoff = now - window
        while health.recent_failures and health.recent_failures[0] < cutoff:
            health.recent_failures.popleft()
        while health.recent_requests and health.recent_requests[0] < cutoff:
            health.recent_requests.popleft()

    def _orderbook_error_rate(self, health: ClobOrderbookHealth, now: float | None = None) -> float:
        now = time.monotonic() if now is None else now
        self._trim_orderbook_health(health, now)
        requests = len(health.recent_requests)
        if requests <= 0:
            return 0.0
        return round(len(health.recent_failures) / requests, 4)

    def get_orderbook_health(self, token_id: str) -> dict[str, Any]:
        health = self._orderbook_health_for(token_id)
        now = time.monotonic()
        self._trim_orderbook_health(health, now)
        cooldown_remaining = max(0.0, health.cooldown_until - now, health.circuit_open_until - now)
        circuit_open = health.circuit_open_until > now
        return {
            "clob_error_rate": self._orderbook_error_rate(health, now),
            "clob_backoff_active": cooldown_remaining > 0.0,
            "clob_circuit_open": circuit_open,
            "clob_cooldown_seconds_remaining": round(cooldown_remaining, 3),
            "clob_recovery_count": int(health.recovery_count),
            "clob_consecutive_failures": int(health.consecutive_failures),
            "clob_last_error_class": health.last_error_class,
            "clob_last_error_category": health.last_category,
        }

    def _orderbook_cooldown_error(self, token_id: str, health: ClobOrderbookHealth) -> ClobOrderbookError:
        now = time.monotonic()
        cooldown_remaining = max(0.0, health.cooldown_until - now, health.circuit_open_until - now)
        circuit_open = health.circuit_open_until > now
        category = health.last_category or "clob_http_error"
        error_class = health.last_error_class or self._clob_error_class(category, health.last_status_code)
        return ClobOrderbookError(
            category,
            f"clob_orderbook_cooldown_active token={token_id[:12]}... remaining={cooldown_remaining:.2f}s",
            token_id=token_id,
            exception_type="ClobOrderbookCooldown",
            status_code=health.last_status_code,
            api_failure=True,
            retry_count=0,
            error_class=error_class,
            cooldown_seconds_remaining=cooldown_remaining,
            circuit_open=circuit_open,
            backoff_active=True,
            error_rate=self._orderbook_error_rate(health, now),
            recovery_count=health.recovery_count,
        )

    def _record_orderbook_success(self, token_id: str, health: ClobOrderbookHealth) -> None:
        now = time.monotonic()
        self._trim_orderbook_health(health, now)
        health.total_successes += 1
        if health.consecutive_failures or health.cooldown_until > now or health.circuit_open_until > now:
            health.recovery_count += 1
        health.consecutive_failures = 0
        health.cooldown_until = 0.0
        health.circuit_open_until = 0.0
        health.last_error_class = ""
        health.last_category = ""
        health.last_exception_type = ""
        health.last_status_code = None

    def _record_orderbook_failure(
        self,
        token_id: str,
        health: ClobOrderbookHealth,
        exc: ClobOrderbookError,
        *,
        retry_count: int,
    ) -> ClobOrderbookError:
        now = time.monotonic()
        self._trim_orderbook_health(health, now)
        health.consecutive_failures += 1
        health.total_failures += 1
        health.recent_failures.append(now)
        health.last_error_class = exc.error_class or self._clob_error_class(exc.category, exc.status_code)
        health.last_category = exc.category
        health.last_exception_type = exc.exception_type
        health.last_status_code = exc.status_code

        cooldown_seconds = 0
        if health.last_error_class == "rate_limited":
            cooldown_seconds = int(getattr(self.settings, "clob_rate_limit_cooldown_seconds", 30))
        elif health.last_error_class in {"token_or_market_issue", "auth_or_client_issue"}:
            cooldown_seconds = int(getattr(self.settings, "clob_market_error_cooldown_seconds", 10))

        threshold = max(1, int(getattr(self.settings, "clob_circuit_breaker_threshold", 3)))
        if len(health.recent_failures) >= threshold:
            cooldown_seconds = max(cooldown_seconds, int(getattr(self.settings, "clob_market_error_cooldown_seconds", 10)))
            health.circuit_open_until = max(health.circuit_open_until, now + cooldown_seconds)
        if cooldown_seconds > 0:
            health.cooldown_until = max(health.cooldown_until, now + cooldown_seconds)

        cooldown_remaining = max(0.0, health.cooldown_until - now, health.circuit_open_until - now)
        return ClobOrderbookError(
            exc.category,
            str(exc),
            token_id=token_id,
            exception_type=exc.exception_type,
            status_code=exc.status_code,
            parse_failure=exc.parse_failure,
            api_failure=exc.api_failure,
            retry_count=retry_count,
            error_class=health.last_error_class,
            cooldown_seconds_remaining=cooldown_remaining,
            circuit_open=health.circuit_open_until > now,
            backoff_active=cooldown_remaining > 0.0,
            error_rate=self._orderbook_error_rate(health, now),
            recovery_count=health.recovery_count,
        )

    def _orderbook_should_retry(self, exc: ClobOrderbookError) -> bool:
        error_class = exc.error_class or self._clob_error_class(exc.category, exc.status_code)
        return error_class == "transient_api_issue"

    def _normalise_order_receipt(
        self,
        payload: dict[str, Any],
        *,
        token_id: str,
        side: str,
        price: float,
        size: float,
        order_type: str,
    ) -> OrderReceipt:
        filled = self._float_field(payload, "filled_size", "filled", "matched_size", "size_matched")
        remaining = self._float_field(payload, "remaining_size", "remaining", "size_remaining")
        if remaining <= 0 and filled >= 0:
            remaining = max(0.0, size - filled)
        return OrderReceipt(
            order_id=self._str_field(payload, "orderID", "order_id", "id", default="unknown"),
            status=self._str_field(payload, "status", "state", default="unknown").lower(),
            token_id=self._str_field(payload, "asset_id", "token_id", "token", default=token_id),
            side=self._str_field(payload, "side", default=side),
            price=self._float_field(payload, "price") or price,
            size=self._float_field(payload, "size", "original_size") or size,
            filled_size=filled,
            remaining_size=remaining,
            created_at=self._str_field(payload, "created_at", "createdAt", default=self._now_iso()),
            order_type=self._str_field(payload, "order_type", "orderType", default=order_type),
        )

    def _balance_raw_to_float(self, value: Any) -> float:
        try:
            amount = float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0
        if amount > 10_000:
            return amount / 1_000_000
        return amount

    def _api_call_with_retry(self, func, *args, operation: str = "api_call", **kwargs) -> Any:
        """v3.2: Retry API calls with exponential backoff + circuit breaker."""
        # Circuit breaker check
        if time.time() < self._circuit_open_until:
            remaining = int(self._circuit_open_until - time.time())
            LOGGER.warning("[CIRCUIT_BREAKER] %s blocked — circuit open for %ds", operation, remaining)
            raise RuntimeError(f"Circuit breaker open for {operation} ({remaining}s remaining)")

        max_attempts = self.settings.api_retry_attempts
        backoff_base = self.settings.api_retry_backoff_base

        for attempt in range(1, max_attempts + 1):
            try:
                result = func(*args, **kwargs)
                # Success — reset circuit breaker
                if self._consecutive_failures > 0:
                    LOGGER.info("[API_RETRY] %s recovered after %d failures", operation, self._consecutive_failures)
                self._consecutive_failures = 0
                return result
            except Exception as e:
                self._consecutive_failures += 1
                if attempt < max_attempts:
                    wait = backoff_base * (2 ** (attempt - 1))
                    LOGGER.warning(
                        "[API_RETRY] %s attempt %d/%d failed: %s — retrying in %.1fs",
                        operation, attempt, max_attempts, e, wait,
                    )
                    time.sleep(wait)
                else:
                    # All retries exhausted
                    if self._consecutive_failures >= self.settings.api_circuit_breaker_threshold:
                        self._circuit_open_until = time.time() + self.settings.api_circuit_breaker_cooldown
                        LOGGER.error(
                            "[CIRCUIT_BREAKER] %s OPEN — %d consecutive failures, pausing %ds",
                            operation, self._consecutive_failures,
                            self.settings.api_circuit_breaker_cooldown,
                        )
                    raise

    def connect(self) -> None:
        """Create the ClobClient and derive/set L2 API credentials."""
        if not _CLOB_AVAILABLE:
            LOGGER.warning("py-clob-client not installed — running in stub mode.")
            return

        private_key = self.settings.polymarket_private_key.get_secret_value()
        if not private_key:
            raise ValueError("POLYMARKET_PRIVATE_KEY is required to connect.")

        LOGGER.info(
            "Connecting to Polymarket CLOB host=%s chain_id=%s",
            self.settings.polymarket_host,
            self.settings.polymarket_chain_id,
        )

        proxy_wallet = self.settings.polymarket_proxy_wallet
        if proxy_wallet:
            client = ClobClient(
                host=self.settings.polymarket_host,
                key=private_key,
                chain_id=self.settings.polymarket_chain_id,
                funder=proxy_wallet,
                signature_type=2,
            )
        else:
            client = ClobClient(
                host=self.settings.polymarket_host,
                key=private_key,
                chain_id=self.settings.polymarket_chain_id,
                signature_type=self.settings.polymarket_signature_type,
                funder=self.settings.polymarket_funder or None,
            )

        try:
            # If API keys are explicitly provided, use them instead of deriving
            api_secret = self.settings.polymarket_api_secret.get_secret_value() if self.settings.polymarket_api_secret else ""
            if self.settings.polymarket_api_key and api_secret and self.settings.polymarket_api_passphrase:
                LOGGER.info("Using explicitly provided Polymarket API Keys.")
                creds = ApiCreds(
                    api_key=self.settings.polymarket_api_key,
                    api_secret=api_secret,
                    api_passphrase=self.settings.polymarket_api_passphrase,
                )
            else:
                LOGGER.info("Deriving API credentials using private key...")
                creds = client.create_or_derive_api_creds()
                
            client.set_api_creds(creds)
            LOGGER.info("Polymarket L2 API credentials set.")
        except Exception:
            LOGGER.exception("Failed to derive Polymarket API credentials.")
            raise

        self._client = client
        self._market_data_client = client

    # ------------------------------------------------------------------
    # Market helpers
    # ------------------------------------------------------------------

    def get_markets(self, limit: int = 25) -> list[dict[str, Any]]:
        """Return a list of active CLOB markets (raw dicts from the API)."""
        client = self._require_clob()
        markets: list[dict[str, Any]] = []
        next_cursor = ""

        while len(markets) < limit:
            try:
                resp = client.get_markets(next_cursor=next_cursor)
            except Exception:
                LOGGER.exception("get_markets call failed.")
                break

            batch: list[dict[str, Any]] = resp.get("data", [])
            markets.extend(batch)
            next_cursor = resp.get("next_cursor", "LTE=")
            if next_cursor == "LTE=" or not batch:
                break

        result = markets[:limit]
        LOGGER.info("Fetched %s CLOB markets.", len(result))
        return result

    def get_orderbook(self, token_id: str) -> OrderbookSnapshot:
        """Return a normalized orderbook snapshot for a binary outcome token."""
        if not token_id:
            raise ClobOrderbookError(
                "clob_token_not_found",
                "missing token_id for get_orderbook",
                token_id=token_id,
                exception_type="ValueError",
                api_failure=False,
            )
        client = self._require_market_data_client()

        def _level_value(level: Any, field: str) -> float:
            if isinstance(level, dict):
                value = level.get(field, 0.0)
            else:
                value = getattr(level, field, 0.0)
            return float(value or 0.0)

        def _raw_field(raw: Any, *keys: str, default: Any = None) -> Any:
            for key in keys:
                if isinstance(raw, dict):
                    value = raw.get(key)
                else:
                    value = getattr(raw, key, None)
                if value is not None:
                    return value
            return default

        def _timestamp_age(raw: Any) -> tuple[int, float]:
            timestamp_raw = _raw_field(raw, "timestamp", "ts", "updated_at", "updatedAt", default=0)
            try:
                timestamp = float(timestamp_raw or 0)
            except (TypeError, ValueError):
                return 0, 0.0
            if timestamp <= 0:
                return 0, 0.0
            if timestamp > 1_000_000_000_000:
                timestamp_seconds = timestamp / 1000.0
                timestamp_ms = int(timestamp)
            else:
                timestamp_seconds = timestamp
                timestamp_ms = int(timestamp * 1000)
            return timestamp_ms, max(0.0, time.time() - timestamp_seconds)

        def _compact_raw(raw: Any, bids: list[Any], asks: list[Any]) -> dict[str, Any]:
            top_bids = sorted(bids, key=lambda level: _level_value(level, "price"), reverse=True)[:3]
            top_asks = sorted(asks, key=lambda level: _level_value(level, "price"))[:3]
            return {
                "market": _raw_field(raw, "market", "condition_id", "conditionId", default=""),
                "asset_id": _raw_field(raw, "asset_id", "assetId", "token_id", "tokenId", default=token_id),
                "timestamp": _raw_field(raw, "timestamp", default=""),
                "bids_count": len(bids),
                "asks_count": len(asks),
                "top_bids": [
                    {"price": _level_value(level, "price"), "size": _level_value(level, "size")}
                    for level in top_bids
                ],
                "top_asks": [
                    {"price": _level_value(level, "price"), "size": _level_value(level, "size")}
                    for level in top_asks
                ],
            }

        def _parse_snapshot(raw: Any) -> OrderbookSnapshot:
            if raw in (None, "", [], {}):
                raise ClobOrderbookError(
                    "clob_empty_response",
                    f"empty_orderbook_response token={token_id[:12]}...",
                    token_id=token_id,
                    exception_type="ValueError",
                    parse_failure=True,
                    error_class="transient_api_issue",
                )
            try:
                if isinstance(raw, dict):
                    bids: list[Any] = raw.get("bids") or []
                    asks: list[Any] = raw.get("asks") or []
                else:
                    bids = raw.bids or []
                    asks = raw.asks or []
            except Exception as exc:
                raise ClobOrderbookError(
                    "clob_parse_error",
                    f"parse_orderbook_failed token={token_id[:12]}... error={exc}",
                    token_id=token_id,
                    exception_type=exc.__class__.__name__,
                    parse_failure=True,
                    error_class="token_or_market_issue",
                ) from exc

            timestamp_ms, age_seconds = _timestamp_age(raw)
            if timestamp_ms and age_seconds > 3.0:
                raise RuntimeError(f"stale_orderbook age={age_seconds:.3f}s token={token_id[:12]}...")
            if not bids or not asks:
                raise RuntimeError(
                    f"empty_orderbook bids={len(bids)} asks={len(asks)} token={token_id[:12]}..."
                )

            best_bid_level = max(bids, key=lambda level: _level_value(level, "price"), default=None)
            best_ask_level = min(asks, key=lambda level: _level_value(level, "price"), default=None)

            best_bid = _level_value(best_bid_level, "price") if best_bid_level is not None else 0.0
            bid_size = _level_value(best_bid_level, "size") if best_bid_level is not None else 0.0
            best_ask = _level_value(best_ask_level, "price") if best_ask_level is not None else 0.0
            ask_size = _level_value(best_ask_level, "size") if best_ask_level is not None else 0.0
            if best_bid <= 0 or best_ask <= 0:
                raise RuntimeError(
                    f"invalid_orderbook bid={best_bid:.4f} ask={best_ask:.4f} token={token_id[:12]}..."
                )
            spread = round(best_ask - best_bid, 6)
            raw_response = _compact_raw(raw, bids, asks)

            return OrderbookSnapshot(
                token_id=str(_raw_field(raw, "asset_id", "assetId", "token_id", "tokenId", default=token_id)),
                best_bid=best_bid,
                best_ask=best_ask,
                spread=spread,
                bid_size=bid_size,
                ask_size=ask_size,
                condition_id=str(_raw_field(raw, "market", "condition_id", "conditionId", default="")),
                timestamp_ms=timestamp_ms,
                age_seconds=age_seconds,
                raw_response=raw_response,
            )

        def _fetch_and_parse() -> OrderbookSnapshot:
            try:
                raw = client.get_order_book(token_id)
            except Exception as exc:
                raise self._wrap_orderbook_exception(exc, token_id=token_id) from exc
            snapshot = _parse_snapshot(raw)
            LOGGER.info(
                "[ORDERBOOK_RESPONSE] token=%s raw=%s",
                token_id,
                snapshot.raw_response,
            )
            return snapshot

        health = self._orderbook_health_for(token_id)
        now = time.monotonic()
        self._trim_orderbook_health(health, now)
        health.recent_requests.append(now)
        if health.cooldown_until > now or health.circuit_open_until > now:
            raise self._orderbook_cooldown_error(token_id, health)

        max_retries = max(0, int(getattr(self.settings, "clob_orderbook_retry_count", 1)))
        max_attempts = max(1, 1 + max_retries)
        backoff_ms = max(0, int(getattr(self.settings, "clob_orderbook_retry_backoff_ms", 150)))
        last_error: ClobOrderbookError | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                snapshot = _fetch_and_parse()
                self._record_orderbook_success(token_id, health)
                break
            except ClobOrderbookError as exc:
                last_error = exc
            except RuntimeError as exc:
                message = str(exc).lower()
                if (
                    message.startswith("stale_orderbook")
                    or message.startswith("empty_orderbook")
                    or message.startswith("invalid_orderbook")
                ):
                    raise
                last_error = self._wrap_orderbook_exception(exc, token_id=token_id)
            except Exception as exc:
                last_error = self._wrap_orderbook_exception(exc, token_id=token_id)

            retry_count = attempt - 1
            retry_allowed = (
                last_error is not None
                and self._orderbook_should_retry(last_error)
                and attempt < max_attempts
            )
            if retry_allowed and backoff_ms > 0:
                wait_seconds = min(1.0, (backoff_ms / 1000.0) * (2 ** retry_count))
                LOGGER.debug(
                    "[CLOB_ORDERBOOK_BACKOFF] token=%s category=%s class=%s attempt=%d/%d sleep=%.3fs",
                    token_id[:12],
                    last_error.category,
                    last_error.error_class,
                    attempt,
                    max_attempts,
                    wait_seconds,
                )
                time.sleep(wait_seconds)
                continue

            degraded = self._record_orderbook_failure(
                token_id,
                health,
                last_error,
                retry_count=retry_count,
            )
            LOGGER.warning(
                "[CLOB_ORDERBOOK_DEGRADED] token=%s category=%s class=%s status=%s retry_count=%s "
                "error_rate=%.3f circuit_open=%s cooldown=%.2fs error=%s",
                token_id[:12],
                degraded.category,
                degraded.error_class,
                degraded.status_code,
                degraded.retry_count,
                degraded.error_rate,
                degraded.circuit_open,
                degraded.cooldown_seconds_remaining,
                degraded,
            )
            raise degraded
        else:  # pragma: no cover - defensive guard for type checkers.
            raise self._record_orderbook_failure(
                token_id,
                health,
                last_error or ClobOrderbookError("clob_http_error", "unknown orderbook failure", token_id=token_id),
                retry_count=max_retries,
            )
        LOGGER.info(
            "[ORDERBOOK_BEST] condition_id=%s token=%s bid=%.4f ask=%.4f spread=%.6f "
            "bid_size=%.4f ask_size=%.4f age=%.3fs",
            snapshot.condition_id,
            snapshot.token_id,
            snapshot.best_bid,
            snapshot.best_ask,
            snapshot.spread,
            snapshot.bid_size,
            snapshot.ask_size,
            snapshot.age_seconds,
        )
        return snapshot

    def _fetch_clob_balance(self) -> float:
        """Primary: Fetch USDC balance via Polymarket CLOB API (~200ms)."""
        client = self._require_clob()
        params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
        res = client.get_balance_allowance(params)
        raw = res.get("balance", 0)
        # CLOB returns raw integer in micro-USDC (6 decimals)
        return int(raw) / 1_000_000

    def _fetch_onchain_balance_for_wallet(self, wallet: str, label: str) -> float:
        """Read native USDC + USDC.e balance for one Polygon wallet."""
        if not _WEB3_AVAILABLE:
            raise RuntimeError("web3 not installed")

        rpc_url = getattr(self.settings, "alchemy_url", None) or _POLYGON_RPC
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        checksum_addr = Web3.to_checksum_address(wallet)

        total = 0.0
        wallet_tag = f"{label}:{checksum_addr[:6]}...{checksum_addr[-4:]}"
        for token_label, addr in [("native USDC", _USDC_NATIVE), ("USDC.e", _USDC_BRIDGED)]:
            try:
                contract = w3.eth.contract(
                    address=Web3.to_checksum_address(addr), abi=_USDC_ABI
                )
                raw = contract.functions.balanceOf(checksum_addr).call()
                amount = raw / 1_000_000
                LOGGER.info("[OnChain] %s %s balance: $%.4f", wallet_tag, token_label, amount)
                total += amount
            except Exception as e:
                LOGGER.warning("[OnChain] %s %s check failed: %s", wallet_tag, token_label, e)

        return total

    def _fetch_onchain_balance(self) -> float:
        """Fallback: read balances from the trading proxy wallet first, then funder.

        Polymarket proxy accounts can show cash under POLYMARKET_PROXY_WALLET while the
        signer/funder wallet has a different on-chain USDC balance. The terminal should
        reflect the wallet that can actually be used by live CLOB orders.
        """
        wallets: list[tuple[str, str]] = []
        if self.settings.polymarket_proxy_wallet:
            wallets.append(("proxy", self.settings.polymarket_proxy_wallet))
        if self.settings.polymarket_funder:
            wallets.append(("funder", self.settings.polymarket_funder))

        deduped: list[tuple[str, str]] = []
        seen: set[str] = set()
        for label, wallet in wallets:
            key = wallet.lower()
            if key not in seen:
                deduped.append((label, wallet))
                seen.add(key)

        if not deduped:
            raise ValueError("POLYMARKET_PROXY_WALLET or POLYMARKET_FUNDER must be set")

        balances: list[tuple[str, float]] = []
        for label, wallet in deduped:
            balances.append((label, self._fetch_onchain_balance_for_wallet(wallet, label)))

        best_label, best_balance = max(balances, key=lambda item: item[1])
        LOGGER.info("[Wallet] Selected %s USDC balance: $%.4f", best_label, best_balance)
        return best_balance

    def get_usdc_balance_snapshot(self) -> BalanceSnapshot:
        """Fetch the live balance source used for terminal portfolio and sizing.

        CLOB collateral is the primary live trading cash source. On-chain USDC is logged
        as a fallback/diagnostic, but it is not mixed into the CLOB balance.
        """
        wallet = self.settings.polymarket_proxy_wallet or self.settings.polymarket_funder
        clob_balance = 0.0
        clob_ok = False
        try:
            clob_balance = self._fetch_clob_balance()
            clob_ok = True
            LOGGER.info("[CLOB] Polymarket internal balance: $%.4f", clob_balance)
        except Exception as e:
            LOGGER.warning("CLOB balance check failed: %s", e)

        try:
            onchain_balance = self._fetch_onchain_balance()
            LOGGER.info("[Wallet] Total on-chain USDC: $%.4f", onchain_balance)
        except Exception as e:
            LOGGER.warning("On-chain balance failed: %s", e)
            onchain_balance = 0.0

        source = "clob_collateral" if clob_ok else "onchain_wallet"
        balance = clob_balance if clob_ok else onchain_balance
        snapshot = BalanceSnapshot(
            balance=balance,
            source=source,
            wallet_address=wallet,
            clob_balance=clob_balance,
            onchain_balance=onchain_balance,
            proxy_wallet=self.settings.polymarket_proxy_wallet,
            funder_wallet=self.settings.polymarket_funder,
        )
        LOGGER.info(
            "[USDC BALANCE] wallet_address=%s source=%s balance=$%.4f clob=$%.4f onchain=$%.4f",
            snapshot.wallet_address,
            snapshot.source,
            snapshot.balance,
            snapshot.clob_balance,
            snapshot.onchain_balance,
        )
        return snapshot

    def get_usdc_balance(self) -> float:
        """Fetch the USDC balance used by live trading and portfolio display."""
        return self.get_usdc_balance_snapshot().balance

    def get_balance_allowance(self, *, token_id: str | None = None, side: str = BUY) -> dict[str, float]:
        """Return normalized balance/allowance data for collateral or outcome token."""
        client = self._require_clob()
        side = side.upper()
        if side == BUY:
            params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
        else:
            kwargs: dict[str, Any] = {"asset_type": AssetType.CONDITIONAL}
            if token_id:
                kwargs["token_id"] = token_id
            try:
                params = BalanceAllowanceParams(**kwargs)
            except TypeError:
                kwargs.pop("token_id", None)
                params = BalanceAllowanceParams(**kwargs)

        raw = client.get_balance_allowance(params)
        if not isinstance(raw, dict):
            raw = {}
        return {
            "balance": self._balance_raw_to_float(raw.get("balance", 0.0)),
            "allowance": self._balance_raw_to_float(raw.get("allowance", raw.get("allowances", 0.0))),
        }

    def _preflight_balance_allowance(
        self,
        *,
        token_id: str,
        price: float,
        size: float,
        side: str,
    ) -> None:
        needed = price * size if side == BUY else size
        try:
            ba = self.get_balance_allowance(token_id=token_id, side=side)
        except Exception as exc:
            raise RuntimeError(f"balance/allowance preflight failed: {exc}") from exc

        balance = ba["balance"]
        allowance = ba["allowance"]
        if balance + 1e-9 < needed:
            raise RuntimeError(
                f"insufficient {'USDC' if side == BUY else 'token'} balance: "
                f"balance={balance:.6f} required={needed:.6f}"
            )
        if allowance and allowance + 1e-9 < needed:
            raise RuntimeError(
                f"insufficient allowance: allowance={allowance:.6f} required={needed:.6f}"
            )

    # ------------------------------------------------------------------
    # Order flow
    # ------------------------------------------------------------------

    def place_limit_order(
        self,
        token_id: str,
        price: float,
        size: float,
        side: str,
        order_type: str = "GTC",
        *,
        expiration: int | None = None,
        post_only: bool = False,
        timeout_sec: float | None = None,
        check_balance: bool = True,
    ) -> OrderReceipt:
        """Place a CLOB limit order and return structured status.

        GTC/GTD rest on the book. FOK/FAK are immediate modes and should only be
        used by callers that explicitly opt in. A GTC timeout cancels the order
        if it has not fully filled.
        """
        order_type = order_type.upper()
        resolved_order_type = self._get_order_type(order_type)
        if side not in (BUY, SELL):
            raise ValueError(f"side must be BUY or SELL, got {side!r}.")
        if price <= 0 or size <= 0:
            raise ValueError("price and size must be positive.")
        if post_only and order_type not in {"GTC", "GTD"}:
            raise ValueError("post_only is only supported for GTC/GTD.")
        if self.settings.paper_trading:
            raise RuntimeError("paper_mode_live_order_api_blocked")

        client = self._require_clob()
        if check_balance and not self.settings.paper_trading:
            self._preflight_balance_allowance(token_id=token_id, price=price, size=size, side=side)

        LOGGER.info(
            "Placing limit order | token=%s side=%s type=%s price=%.4f size=%.4f post_only=%s",
            token_id,
            side,
            order_type,
            price,
            size,
            post_only,
        )

        order_args = self._build_order_args(
            token_id=token_id,
            price=price,
            size=size,
            side=side,
            order_type=order_type,
            expiration=expiration,
            post_only=post_only,
        )
        signed_order = client.create_order(order_args)

        def _post():
            return client.post_order(signed_order, resolved_order_type)

        resp: dict[str, Any] = self._api_call_with_retry(_post, operation=f"post_order({token_id[:12]}...)")
        receipt = self._normalise_order_receipt(
            resp if isinstance(resp, dict) else {},
            token_id=token_id,
            side=side,
            price=price,
            size=size,
            order_type=order_type,
        )
        if receipt.filled_size <= 0 and receipt.status in {"filled", "matched"}:
            receipt.filled_size = receipt.size
            receipt.remaining_size = 0.0
        LOGGER.info(
            "Order submitted | id=%s status=%s filled=%.6f remaining=%.6f",
            receipt.order_id,
            receipt.status,
            receipt.filled_size,
            receipt.remaining_size,
        )
        if timeout_sec is not None and order_type == "GTC":
            return self.wait_for_fill(receipt.order_id, timeout_sec=timeout_sec, cancel_on_timeout=True, original=receipt)
        return receipt

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order. Returns True if the cancel was accepted."""
        if self.settings.paper_trading:
            LOGGER.warning("[PAPER_MODE_BLOCK] cancel_order blocked in paper mode | id=%s", order_id)
            return False
        client = self._require_clob()
        LOGGER.info("Cancelling order id=%s", order_id)
        try:
            client.cancel(order_id)
            LOGGER.info("Order cancelled id=%s", order_id)
            return True
        except Exception:
            LOGGER.exception("Failed to cancel order id=%s", order_id)
            return False

    def get_open_orders(self) -> list[dict[str, Any]]:
        """Return all open orders for the configured account."""
        client = self._require_clob()
        try:
            resp = client.get_orders()
            orders: list[dict[str, Any]] = resp if isinstance(resp, list) else resp.get("data", [])
            LOGGER.info("Fetched %s open orders.", len(orders))
            return orders
        except Exception:
            LOGGER.exception("Failed to fetch open orders.")
            return []

    def get_order(self, order_id: str) -> dict[str, Any]:
        """Return one order if the CLOB client exposes an order lookup method."""
        client = self._require_clob()
        try:
            if hasattr(client, "get_order"):
                resp = client.get_order(order_id)
            elif hasattr(client, "get_order_by_id"):
                resp = client.get_order_by_id(order_id)
            else:
                return {}
            return resp if isinstance(resp, dict) else {}
        except Exception:
            LOGGER.exception("Failed to fetch order id=%s", order_id)
            return {}

    def get_order_status(self, order_id: str, original: OrderReceipt | None = None) -> OrderReceipt:
        """Fetch and normalize current order state."""
        raw = self.get_order(order_id)
        if not raw and original is not None:
            return original
        token_id = original.token_id if original else ""
        side = original.side if original else ""
        price = original.price if original else 0.0
        size = original.size if original else 0.0
        order_type = original.order_type if original else "GTC"
        return self._normalise_order_receipt(
            raw,
            token_id=token_id,
            side=side,
            price=price,
            size=size,
            order_type=order_type,
        )

    def wait_for_fill(
        self,
        order_id: str,
        *,
        timeout_sec: float,
        poll_interval: float = 0.25,
        cancel_on_timeout: bool = False,
        original: OrderReceipt | None = None,
    ) -> OrderReceipt:
        """Poll an order until filled, terminal, or timeout. Never assumes fill."""
        deadline = time.monotonic() + max(0.0, timeout_sec)
        latest = original
        terminal = {"filled", "matched", "cancelled", "canceled", "failed", "expired", "rejected"}

        while True:
            latest = self.get_order_status(order_id, original=latest)
            if latest.status.lower() in terminal:
                return latest
            if latest.remaining_size <= 0 < latest.size:
                latest.status = "filled"
                latest.filled_size = latest.size
                return latest
            if time.monotonic() >= deadline:
                if cancel_on_timeout:
                    self.cancel_order(order_id)
                    latest = self.get_order_status(order_id, original=latest)
                    if latest.status == (original.status if original else latest.status):
                        latest.status = "timeout_cancelled"
                return latest
            time.sleep(poll_interval)

    def get_positions(self) -> list[dict[str, Any]]:
        """Return current CLOB positions for inventory reconciliation."""
        if not _CLOB_AVAILABLE and self._client is None:
            return []
        client = self._require_clob()
        try:
            if hasattr(client, "get_positions"):
                resp = client.get_positions()
            else:
                return []
            return resp if isinstance(resp, list) else resp.get("data", [])
        except Exception:
            LOGGER.exception("Failed to fetch positions.")
            return []

    # ------------------------------------------------------------------
    # Redeem (claim settled winnings back as USDC)
    # ------------------------------------------------------------------

    def get_redeemable_positions(self) -> list[dict]:
        """Fetch list of settled positions that have unclaimed USDC winnings.

        Returns a list of dicts with keys: position_id, market_id, size, amount_usd.
        Returns empty list in stub / paper mode.
        """
        if not _CLOB_AVAILABLE or self._client is None:
            return []
        try:
            resp = self._client.get_positions()
            positions: list[dict] = resp if isinstance(resp, list) else resp.get("data", [])
            redeemable = []
            for p in positions:
                # Polymarket marks redeemable positions with redeemable=True or status='SETTLED'
                is_redeemable = (
                    p.get("redeemable", False)
                    or p.get("status", "").upper() in ("SETTLED", "RESOLVED")
                )
                size = float(p.get("size", 0) or 0)
                if is_redeemable and size > 0:
                    redeemable.append({
                        "position_id": p.get("id", p.get("position_id", "")),
                        "market_id":   p.get("market", p.get("market_id", "")),
                        "token_id":    p.get("asset_id", p.get("token_id", "")),
                        "size":        size,
                        "outcome":     p.get("outcome", ""),
                    })
            LOGGER.info("[Redeem] Found %d redeemable positions.", len(redeemable))
            return redeemable
        except Exception as e:
            LOGGER.warning("[Redeem] Failed to fetch redeemable positions: %s", e)
            return []

    def redeem_position(self, token_id: str, size: float) -> float:
        """Redeem a settled position token back into USDC.

        Calls the CLOB redeem endpoint. Returns the USD amount redeemed (size × $1.00
        since winning binary = $1/share). Returns 0.0 on failure.
        """
        if self.settings.paper_trading:
            LOGGER.warning("[PAPER_MODE_BLOCK] redeem_position blocked in paper mode | token=%s", token_id[:16])
            return 0.0
        if not _CLOB_AVAILABLE or self._client is None:
            return 0.0
        try:
            LOGGER.info("[Redeem] Redeeming token=%s size=%.2f", token_id[:16], size)

            def _do_redeem():
                # py-clob-client method: redeem_positions or similar
                # Attempt common method names gracefully
                if hasattr(self._client, "redeem_positions"):
                    return self._client.redeem_positions({"token_id": token_id, "size": size})
                elif hasattr(self._client, "redeem"):
                    return self._client.redeem(token_id, size)
                else:
                    raise RuntimeError("py-clob-client has no redeem method — upgrade to latest version.")

            self._api_call_with_retry(_do_redeem, operation=f"redeem({token_id[:12]}...)")
            amount_usd = size * 1.0  # each winning share = $1.00
            LOGGER.info("[Redeem] Successfully redeemed $%.4f from token=%s", amount_usd, token_id[:16])
            return amount_usd
        except Exception as e:
            LOGGER.warning("[Redeem] Failed to redeem token=%s: %s", token_id[:16], e)
            return 0.0

    # ------------------------------------------------------------------
    # Legacy factory (kept for backward compatibility)
    # ------------------------------------------------------------------

    def create(self) -> Any | None:
        """Return the underlying ClobClient after connecting, or None if unavailable."""
        if not _CLOB_AVAILABLE:
            LOGGER.warning("py-clob-client not installed — returning None.")
            return None
        self.connect()
        return self._client
