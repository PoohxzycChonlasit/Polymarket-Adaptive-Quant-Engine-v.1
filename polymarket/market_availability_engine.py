"""Market Availability Engine — observability/scheduler guard for 5-minute binary markets.

Queries the Gamma API before each scan cycle to determine if BTC/ETH
updown-5m-* markets are scheduled and accepting orders. Returns the
appropriate sleep duration or ACTIVE status to the caller.

This module is pure observability — it never modifies strategy, sizing,
risk, or execution behaviour. It only controls whether the main scan
proceeds or sleeps.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

try:
    import requests as _requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _requests = None  # type: ignore[assignment]
    _REQUESTS_AVAILABLE = False

LOGGER = logging.getLogger(__name__)

_GAMMA_BASE_URL = "https://gamma-api.polymarket.com"
_GAMMA_MARKETS_URL = _GAMMA_BASE_URL

_SLUG_PATTERNS: tuple[str, ...] = (
    "btc-updown-5m-",
    "eth-updown-5m-",
    "btcusd-5m-",
    "ethusd-5m-",
)

_SCHEMA_VERSION = "market_availability_v1"


class MarketAvailabilityState(str, Enum):
    ACTIVE = "ACTIVE"
    BETWEEN_EPOCHS = "BETWEEN_EPOCHS"
    MARKET_NOT_SCHEDULED = "MARKET_NOT_SCHEDULED"
    API_UNAVAILABLE = "API_UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


@dataclass
class MarketAvailabilityResult:
    state: MarketAvailabilityState
    active_market_count: int = 0
    btc_market_count: int = 0
    eth_market_count: int = 0
    symbols_available: list[str] = field(default_factory=list)
    matching_slugs: list[str] = field(default_factory=list)
    next_check_seconds: int = 30
    cache_hit: bool = False
    api_latency_ms: int = 0
    error: str | None = None
    fallback_used: bool = False
    exact_slug_checked: list[str] = field(default_factory=list)
    exact_slug_match_count: int = 0
    availability_source: str = "broad_markets"

    def is_active(self) -> bool:
        return self.state == MarketAvailabilityState.ACTIVE

    def should_skip_scan(self) -> bool:
        return self.state != MarketAvailabilityState.ACTIVE

    def to_telemetry_payload(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "active_market_count": self.active_market_count,
            "btc_market_count": self.btc_market_count,
            "eth_market_count": self.eth_market_count,
            "symbols_available": self.symbols_available,
            "matching_slugs": self.matching_slugs,
            "next_check_seconds": self.next_check_seconds,
            "cache_hit": self.cache_hit,
            "api_latency_ms": self.api_latency_ms,
            "error": self.error,
            "fallback_used": self.fallback_used,
            "exact_slug_checked": self.exact_slug_checked,
            "exact_slug_match_count": self.exact_slug_match_count,
            "availability_source": self.availability_source,
            "schema_version": _SCHEMA_VERSION,
        }


class MarketAvailabilityEngine:
    """Pre-scan guard: queries Gamma API and classifies BTC/ETH 5m market state.

    Usage::

        engine = MarketAvailabilityEngine(settings)
        result = engine.check()
        if result.should_skip_scan():
            time.sleep(result.next_check_seconds)
            return
        # proceed with normal scan
    """

    def __init__(
        self,
        settings: Any = None,
        *,
        gamma_url: str | None = None,
        slug_patterns: tuple[str, ...] | None = None,
        cache_ttl_sec: int | None = None,
        between_epochs_sleep_sec: int | None = None,
        not_scheduled_sleep_sec: int | None = None,
        api_unavailable_base_sleep_sec: int | None = None,
        api_unavailable_max_sleep_sec: int | None = None,
        request_timeout_sec: float = 8.0,
        now: Any = None,
    ) -> None:
        self._gamma_url = gamma_url or _GAMMA_MARKETS_URL
        if settings is not None:
            self._gamma_url = str(getattr(settings, "polymarket_gamma_url", _GAMMA_MARKETS_URL) or _GAMMA_MARKETS_URL)
        self._gamma_base_url = self._normalize_gamma_base_url(self._gamma_url)

        self._slug_patterns = slug_patterns or _SLUG_PATTERNS
        self._cache_ttl = int(
            cache_ttl_sec
            if cache_ttl_sec is not None
            else getattr(settings, "market_availability_cache_ttl_sec", 30)
        )
        self._between_epochs_sleep = int(
            between_epochs_sleep_sec
            if between_epochs_sleep_sec is not None
            else getattr(settings, "market_between_epochs_sleep_sec", 15)
        )
        self._not_scheduled_sleep = int(
            not_scheduled_sleep_sec
            if not_scheduled_sleep_sec is not None
            else getattr(settings, "market_not_scheduled_sleep_sec", 300)
        )
        self._api_base_sleep = int(
            api_unavailable_base_sleep_sec
            if api_unavailable_base_sleep_sec is not None
            else getattr(settings, "market_api_unavailable_base_sleep_sec", 60)
        )
        self._api_max_sleep = int(
            api_unavailable_max_sleep_sec
            if api_unavailable_max_sleep_sec is not None
            else getattr(settings, "market_api_unavailable_max_sleep_sec", 600)
        )
        self._request_timeout = request_timeout_sec
        self._now = now or time.monotonic

        self._cache: MarketAvailabilityResult | None = None
        self._cache_ts: float = 0.0
        self._api_failure_count: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self) -> MarketAvailabilityResult:
        """Return current market availability. Uses cache when fresh."""
        now = self._now()
        if self._cache is not None and (now - self._cache_ts) < self._cache_ttl:
            cached = MarketAvailabilityResult(
                state=self._cache.state,
                active_market_count=self._cache.active_market_count,
                btc_market_count=self._cache.btc_market_count,
                eth_market_count=self._cache.eth_market_count,
                symbols_available=list(self._cache.symbols_available),
                matching_slugs=list(self._cache.matching_slugs),
                next_check_seconds=self._cache.next_check_seconds,
                cache_hit=True,
                api_latency_ms=self._cache.api_latency_ms,
                error=self._cache.error,
                fallback_used=self._cache.fallback_used,
                exact_slug_checked=list(self._cache.exact_slug_checked),
                exact_slug_match_count=self._cache.exact_slug_match_count,
                availability_source=self._cache.availability_source,
            )
            return cached

        result = self._fetch_and_classify()
        self._cache = result
        self._cache_ts = now
        return result

    def invalidate_cache(self) -> None:
        """Force the next check() call to re-query the API."""
        self._cache = None
        self._cache_ts = 0.0

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _fetch_and_classify(self) -> MarketAvailabilityResult:
        if not _REQUESTS_AVAILABLE:
            LOGGER.warning("[MAE] requests not available — returning UNKNOWN")
            return MarketAvailabilityResult(
                state=MarketAvailabilityState.UNKNOWN,
                next_check_seconds=30,
                error="requests library not installed",
            )

        t0 = time.monotonic()
        try:
            resp = _requests.get(
                self._gamma_base_url + "/markets",
                params={"limit": 50, "closed": False, "active": True},
                timeout=self._request_timeout,
            )
            latency_ms = int((time.monotonic() - t0) * 1000)
            if resp.status_code != 200:
                return self._api_unavailable(
                    f"HTTP {resp.status_code}", latency_ms
                )
            try:
                raw = resp.json()
            except Exception as exc:
                return self._api_unavailable(f"JSON parse error: {exc}", latency_ms)
        except Exception as exc:
            latency_ms = int((time.monotonic() - t0) * 1000)
            return self._api_unavailable(str(exc), latency_ms)

        self._api_failure_count = 0
        result = self._classify(raw, latency_ms)
        if result.state == MarketAvailabilityState.MARKET_NOT_SCHEDULED:
            exact_candidates, exact_slugs, exact_latency_ms = self._fetch_exact_slug_candidates(t0)
            if exact_slugs:
                return self._classify(
                    exact_candidates,
                    max(latency_ms, exact_latency_ms),
                    fallback_used=True,
                    exact_slug_checked=exact_slugs,
                    exact_slug_match_count=len(exact_candidates),
                    availability_source="exact_slug_fallback",
                )
        return result

    def _classify(
        self,
        raw: Any,
        latency_ms: int,
        *,
        fallback_used: bool = False,
        exact_slug_checked: list[str] | None = None,
        exact_slug_match_count: int = 0,
        availability_source: str = "broad_markets",
    ) -> MarketAvailabilityResult:
        exact_slug_checked = exact_slug_checked or []
        if not isinstance(raw, list):
            raw = raw.get("data", []) if isinstance(raw, dict) else []

        try:
            candidates = [m for m in raw if isinstance(m, dict) and self._is_5m_binary(m)]
        except Exception as exc:
            return MarketAvailabilityResult(
                state=MarketAvailabilityState.UNKNOWN,
                next_check_seconds=30,
                api_latency_ms=latency_ms,
                fallback_used=fallback_used,
                exact_slug_checked=exact_slug_checked,
                exact_slug_match_count=exact_slug_match_count,
                availability_source=availability_source,
                error=f"classification error: {exc}",
            )

        matching_slugs = [str(m.get("slug", "")) for m in candidates]

        if not candidates:
            LOGGER.info(
                "[MAE] MARKET_NOT_SCHEDULED — no btc/eth-updown-5m-* markets on Gamma API"
            )
            return MarketAvailabilityResult(
                state=MarketAvailabilityState.MARKET_NOT_SCHEDULED,
                active_market_count=0,
                matching_slugs=[],
                next_check_seconds=self._not_scheduled_sleep,
                api_latency_ms=latency_ms,
                fallback_used=fallback_used,
                exact_slug_checked=exact_slug_checked,
                exact_slug_match_count=exact_slug_match_count,
                availability_source=availability_source,
            )

        try:
            tradable = [
                m for m in candidates
                if m.get("active") is True
                and m.get("acceptingOrders") is True
                and float(m.get("bestBid") or 0) > 0
                and float(m.get("bestAsk") or 0) > 0
            ]
        except Exception as exc:
            return MarketAvailabilityResult(
                state=MarketAvailabilityState.UNKNOWN,
                next_check_seconds=30,
                api_latency_ms=latency_ms,
                matching_slugs=matching_slugs,
                fallback_used=fallback_used,
                exact_slug_checked=exact_slug_checked,
                exact_slug_match_count=exact_slug_match_count,
                availability_source=availability_source,
                error=f"tradable filter error: {exc}",
            )

        if tradable:
            symbols = sorted({self._symbol_from_slug(m.get("slug", "")) for m in tradable} - {""})
            btc_count = sum(1 for m in tradable if "btc" in (m.get("slug", "")).lower())
            eth_count = sum(1 for m in tradable if "eth" in (m.get("slug", "")).lower())
            LOGGER.debug(
                "[MAE] ACTIVE — %d tradable 5m markets symbols=%s",
                len(tradable),
                symbols,
            )
            return MarketAvailabilityResult(
                state=MarketAvailabilityState.ACTIVE,
                active_market_count=len(tradable),
                btc_market_count=btc_count,
                eth_market_count=eth_count,
                symbols_available=symbols,
                matching_slugs=matching_slugs,
                next_check_seconds=self._cache_ttl,
                api_latency_ms=latency_ms,
                fallback_used=fallback_used,
                exact_slug_checked=exact_slug_checked,
                exact_slug_match_count=exact_slug_match_count,
                availability_source=availability_source,
            )

        LOGGER.info(
            "[MAE] BETWEEN_EPOCHS — %d 5m markets exist but all have empty orderbooks",
            len(candidates),
        )
        return MarketAvailabilityResult(
            state=MarketAvailabilityState.BETWEEN_EPOCHS,
            active_market_count=0,
            btc_market_count=sum(1 for m in candidates if "btc" in (m.get("slug","")).lower()),
            eth_market_count=sum(1 for m in candidates if "eth" in (m.get("slug","")).lower()),
            matching_slugs=matching_slugs,
            next_check_seconds=self._between_epochs_sleep,
            api_latency_ms=latency_ms,
            fallback_used=fallback_used,
            exact_slug_checked=exact_slug_checked,
            exact_slug_match_count=exact_slug_match_count,
            availability_source=availability_source,
        )

    def _fetch_exact_slug_candidates(self, started_at_monotonic: float) -> tuple[list[dict[str, Any]], list[str], int]:
        """Bounded fallback for exact current/next BTC/ETH 5-minute event slugs."""
        now_ts = int(time.time())
        current_epoch = now_ts - (now_ts % 300)
        slugs = [
            f"{asset}-updown-5m-{current_epoch + offset}"
            for asset in ("btc", "eth")
            for offset in (0, 300)
        ]
        candidates: list[dict[str, Any]] = []

        for slug in slugs:
            try:
                resp = _requests.get(
                    self._gamma_base_url + "/events",
                    params={"slug": slug},
                    timeout=self._request_timeout,
                )
                if resp.status_code != 200:
                    LOGGER.debug("[MAE] exact slug fallback HTTP %s for %s", resp.status_code, slug)
                    continue
                payload = resp.json()
            except Exception as exc:
                LOGGER.debug("[MAE] exact slug fallback failed for %s: %s", slug, exc)
                continue

            candidates.extend(self._markets_from_event_payload(payload))

        latency_ms = int((time.monotonic() - started_at_monotonic) * 1000)
        if candidates:
            LOGGER.info(
                "[MAE] exact slug fallback found %d BTC/ETH 5m candidate(s): %s",
                len(candidates),
                [str(m.get("slug", "")) for m in candidates],
            )
        else:
            LOGGER.info("[MAE] exact slug fallback found no BTC/ETH 5m candidates")
        return candidates, slugs, latency_ms

    def _markets_from_event_payload(self, payload: Any) -> list[dict[str, Any]]:
        events = payload if isinstance(payload, list) else [payload]
        markets: list[dict[str, Any]] = []
        for event in events:
            if not isinstance(event, dict):
                continue
            event_slug = str(event.get("slug") or "")
            event_markets = event.get("markets") or []
            if isinstance(event_markets, dict):
                event_markets = [event_markets]
            if not isinstance(event_markets, list):
                continue
            for market in event_markets:
                if not isinstance(market, dict):
                    continue
                market_copy = dict(market)
                if not market_copy.get("slug") and event_slug:
                    market_copy["slug"] = event_slug
                markets.append(market_copy)
        return markets

    def _api_unavailable(self, error: str, latency_ms: int) -> MarketAvailabilityResult:
        self._api_failure_count += 1
        backoff = min(
            self._api_base_sleep * (2 ** (self._api_failure_count - 1)),
            self._api_max_sleep,
        )
        LOGGER.warning("[MAE] API_UNAVAILABLE failures=%d backoff=%ds error=%s",
                       self._api_failure_count, backoff, error)
        return MarketAvailabilityResult(
            state=MarketAvailabilityState.API_UNAVAILABLE,
            next_check_seconds=int(backoff),
            api_latency_ms=latency_ms,
            error=error,
        )

    def _is_5m_binary(self, market: dict[str, Any]) -> bool:
        slug = str(market.get("slug") or "").lower()
        return any(pat in slug for pat in self._slug_patterns)

    @staticmethod
    def _normalize_gamma_base_url(url: str) -> str:
        clean = str(url or _GAMMA_BASE_URL).rstrip("/")
        if clean.endswith("/markets"):
            clean = clean[:-len("/markets")]
        if clean.endswith("/events"):
            clean = clean[:-len("/events")]
        return clean or _GAMMA_BASE_URL

    @staticmethod
    def _symbol_from_slug(slug: str) -> str:
        slug_l = slug.lower()
        if "btc" in slug_l:
            return "BTC"
        if "eth" in slug_l:
            return "ETH"
        return ""
