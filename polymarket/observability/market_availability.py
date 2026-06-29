"""Market availability observability layer.

Pure, trader-free builders for market availability payload assembly.
Describes WHY a market is or is not tradable at a given point in time.

Companion to polymarket/market_availability_engine.py, which is the runtime
engine (makes Gamma API calls, holds cache, drives main-loop sleep). This
module adds structured reason codes, health scoring, and TypedDict schema
contracts. It makes no API calls and has no runtime side effects.

All functions are Tier 1 (pure, no trader coupling). They accept plain
scalar or dict inputs and return plain dicts with a stable schema.

Schema version: market_availability_obs_v1
"""
from __future__ import annotations

from typing import TypedDict


# ---------------------------------------------------------------------------
# Schema versions
# ---------------------------------------------------------------------------

_SCHEMA_VERSION = "market_availability_obs_v1"
_HEALTH_SCHEMA_VERSION = "availability_health_v1"
_SCORE_SCHEMA_VERSION = "availability_score_v1"

# ---------------------------------------------------------------------------
# Reason codes
#
# Nine standardised unavailability codes (all reachable via
# evaluate_market_availability) plus one positive sentinel (REASON_ACTIVE).
#
# Precedence when conditions co-occur (highest priority first):
#   CLIENT_ERROR → TOKEN_NOT_FOUND → MARKET_CLOSED → STALE_FEED →
#   ORDERBOOK_NOT_READY → EMPTY_ORDERBOOK → UNKNOWN (crossed book) →
#   LOW_LIQUIDITY → HIGH_SPREAD → ACTIVE
# ---------------------------------------------------------------------------

MARKET_CLOSED = "MARKET_CLOSED"
STALE_FEED = "STALE_FEED"
EMPTY_ORDERBOOK = "EMPTY_ORDERBOOK"
LOW_LIQUIDITY = "LOW_LIQUIDITY"
HIGH_SPREAD = "HIGH_SPREAD"
TOKEN_NOT_FOUND = "TOKEN_NOT_FOUND"
CLIENT_ERROR = "CLIENT_ERROR"
ORDERBOOK_NOT_READY = "ORDERBOOK_NOT_READY"
UNKNOWN = "UNKNOWN"

REASON_ACTIVE = "ACTIVE"  # positive sentinel — market is tradable

REASON_CODES: tuple[str, ...] = (
    MARKET_CLOSED,
    STALE_FEED,
    EMPTY_ORDERBOOK,
    LOW_LIQUIDITY,
    HIGH_SPREAD,
    TOKEN_NOT_FOUND,
    CLIENT_ERROR,
    ORDERBOOK_NOT_READY,
    UNKNOWN,
)

_REASON_PRECEDENCE: tuple[str, ...] = (
    CLIENT_ERROR,
    TOKEN_NOT_FOUND,
    MARKET_CLOSED,
    STALE_FEED,
    ORDERBOOK_NOT_READY,
    EMPTY_ORDERBOOK,
    UNKNOWN,
    LOW_LIQUIDITY,
    HIGH_SPREAD,
    REASON_ACTIVE,
)


# ---------------------------------------------------------------------------
# TypedDicts — schema contracts
# ---------------------------------------------------------------------------


class AvailabilityReason(TypedDict, total=False):
    """Why a market is or is not tradable at a given point in time."""

    reason_code: str    # one of REASON_CODES or REASON_ACTIVE
    reason_detail: str  # human-readable explanation
    severity: str       # "info" | "warning" | "error"


class AvailabilityScore(TypedDict, total=False):
    """Numerical availability scores decomposed by dimension.

    Embedded inside AvailabilityHealth.availability_score.
    """

    bid_ask_score: float          # 0.0–1.0; 1.0 when spread is absent or tight
    liquidity_score: float        # 0.0–1.0; 1.0 when active market count > 0
    latency_score: float          # 0.0–1.0; 1.0 when api_latency_ms ≤ 100
    availability_penalty: float   # 0.0–1.0; 0.0 when state is ACTIVE
    final_score: float            # 0.0–1.0; weighted composite
    score_schema_version: str


class AvailabilitySnapshot(TypedDict, total=False):
    """Single-market availability evaluation at a point in time.

    Produced by evaluate_market_availability().
    """

    market_id: str
    ticker: str
    token_id: str | None
    outcome: str | None
    state: str                    # reason code (or REASON_ACTIVE when tradable)
    reason: AvailabilityReason
    best_bid: float | None
    best_ask: float | None
    spread: float | None
    spread_pct: float | None
    orderbook_depth: int
    is_tradable: bool
    is_accepting_orders: bool
    has_valid_bid: bool
    has_valid_ask: bool
    feed_age_seconds: float | None
    cache_hit: bool
    api_latency_ms: int
    checked_at: str
    schema_version: str


class AvailabilitySummary(TypedDict, total=False):
    """Aggregate summary across multiple market snapshots.

    Produced by summarize_market_availability().
    """

    overall_state: str
    active_market_count: int
    tradable_count: int
    non_tradable_count: int
    btc_market_count: int
    eth_market_count: int
    symbols_available: list[str]
    matching_slugs: list[str]
    primary_reason_code: str
    next_check_seconds: int
    api_error: str | None
    api_latency_ms: int
    cache_hit: bool
    summary_checked_at: str
    schema_version: str


class AvailabilityHealth(TypedDict, total=False):
    """Health verdict and score for overall market availability.

    Produced by build_availability_health(). Embedded inside the payload
    returned by build_market_availability_payload() under key "health".
    """

    health_score: float           # 0.0–1.0
    health_grade: str             # "A" | "B" | "C" | "D" | "F"
    health_verdict: str           # "HEALTHY" | "DEGRADED" | "UNAVAILABLE"
    availability_score: AvailabilityScore
    degradation_reasons: list[str]
    recovery_suggestion: str
    schema_version: str


class AvailabilityDiagnostics(TypedDict, total=False):
    """Detailed diagnostics for debugging availability issues.

    Optional sub-field; may be embedded inside larger payloads.
    """

    snapshots: list[AvailabilitySnapshot]
    api_error: str | None
    api_latency_ms: int
    cache_hit: bool
    failure_count: int
    reason_codes: list[str]
    schema_version: str


# ---------------------------------------------------------------------------
# Private lookup tables
# ---------------------------------------------------------------------------

_STATE_TO_REASON: dict[str, str] = {
    "ACTIVE": REASON_ACTIVE,
    "BETWEEN_EPOCHS": EMPTY_ORDERBOOK,
    "MARKET_NOT_SCHEDULED": MARKET_CLOSED,
    "API_UNAVAILABLE": CLIENT_ERROR,
    "UNKNOWN": UNKNOWN,
}

_STATE_HEALTH_SCORE: dict[str, float] = {
    "ACTIVE": 1.0,
    "BETWEEN_EPOCHS": 0.7,
    "MARKET_NOT_SCHEDULED": 0.5,
    "API_UNAVAILABLE": 0.2,
    "UNKNOWN": 0.0,
}

_STATE_AVAILABILITY_PENALTY: dict[str, float] = {
    "ACTIVE": 0.0,
    "BETWEEN_EPOCHS": 0.3,
    "MARKET_NOT_SCHEDULED": 0.5,
    "API_UNAVAILABLE": 0.8,
    "UNKNOWN": 1.0,
}

_STATE_RECOVERY: dict[str, str] = {
    "ACTIVE": "",
    "BETWEEN_EPOCHS": "Wait for next 5m epoch to begin",
    "MARKET_NOT_SCHEDULED": "Check Gamma API for upcoming market schedule",
    "API_UNAVAILABLE": "Check network connectivity and Gamma API status",
    "UNKNOWN": "Investigate engine state and retry",
}


def _compute_availability_score(
    *,
    state: str,
    api_latency_ms: int = 0,
    spread_pct: float | None = None,
    active_market_count: int = 0,
) -> AvailabilityScore:
    """Compute numerical availability score from current state."""
    if spread_pct is None or spread_pct <= 0.02:
        bid_ask_score: float = 1.0
    elif spread_pct <= 0.05:
        bid_ask_score = 0.6
    else:
        bid_ask_score = round(max(0.0, 1.0 - spread_pct * 10), 6)

    liquidity_score: float = 1.0 if active_market_count > 0 else 0.0

    if api_latency_ms <= 100:
        latency_score: float = 1.0
    else:
        latency_score = round(max(0.0, 1.0 - (api_latency_ms - 100) / 1900), 6)

    availability_penalty = _STATE_AVAILABILITY_PENALTY.get(state, 1.0)
    raw = (bid_ask_score + liquidity_score + latency_score) / 3.0
    final_score = round(max(0.0, raw * (1.0 - availability_penalty)), 6)

    return AvailabilityScore(
        bid_ask_score=bid_ask_score,
        liquidity_score=liquidity_score,
        latency_score=latency_score,
        availability_penalty=availability_penalty,
        final_score=final_score,
        score_schema_version=_SCORE_SCHEMA_VERSION,
    )


# ---------------------------------------------------------------------------
# Public builders
# ---------------------------------------------------------------------------


def evaluate_market_availability(
    *,
    ticker: str,
    market_id: str = "",
    token_id: str | None = None,
    outcome: str | None = None,
    best_bid: float | None = None,
    best_ask: float | None = None,
    orderbook_depth: int = 0,
    accepting_orders: bool = False,
    is_active: bool = False,
    client_error: str | None = None,
    feed_age_seconds: float | None = None,
    feed_staleness_threshold: float = 60.0,
    spread_threshold: float = 0.05,
    liquidity_threshold: int = 0,
    checked_at: str = "",
    api_latency_ms: int = 0,
    cache_hit: bool = False,
) -> AvailabilitySnapshot:
    """Evaluate single-market availability from orderbook and metadata inputs.

    Returns an AvailabilitySnapshot whose state and reason reflect the
    highest-priority condition preventing trading, or REASON_ACTIVE if all
    checks pass.

    Precedence: CLIENT_ERROR → TOKEN_NOT_FOUND → MARKET_CLOSED → STALE_FEED
    → ORDERBOOK_NOT_READY → EMPTY_ORDERBOOK → UNKNOWN (crossed book)
    → LOW_LIQUIDITY → HIGH_SPREAD → ACTIVE.
    """
    _common: dict[str, object] = {
        "market_id": market_id,
        "ticker": ticker,
        "token_id": token_id,
        "outcome": outcome,
        "best_bid": best_bid,
        "best_ask": best_ask,
        "orderbook_depth": orderbook_depth,
        "is_accepting_orders": accepting_orders,
        "has_valid_bid": best_bid is not None and best_bid > 0,
        "has_valid_ask": best_ask is not None and best_ask > 0,
        "feed_age_seconds": feed_age_seconds,
        "cache_hit": cache_hit,
        "api_latency_ms": api_latency_ms,
        "checked_at": checked_at,
        "schema_version": _SCHEMA_VERSION,
    }

    def _result(
        *,
        state: str,
        reason_code: str,
        reason_detail: str,
        severity: str,
        is_tradable: bool,
        spread: float | None = None,
        spread_pct: float | None = None,
    ) -> AvailabilitySnapshot:
        return {  # type: ignore[return-value]
            **_common,
            "state": state,
            "reason": AvailabilityReason(
                reason_code=reason_code,
                reason_detail=reason_detail,
                severity=severity,
            ),
            "is_tradable": is_tradable,
            "spread": spread,
            "spread_pct": spread_pct,
        }

    # 1: CLIENT_ERROR — API or client failure overrides all orderbook checks
    if client_error is not None:
        return _result(
            state=CLIENT_ERROR,
            reason_code=CLIENT_ERROR,
            reason_detail=str(client_error),
            severity="error",
            is_tradable=False,
        )

    # 2: TOKEN_NOT_FOUND — no token ID for this outcome
    if not token_id:
        return _result(
            state=TOKEN_NOT_FOUND,
            reason_code=TOKEN_NOT_FOUND,
            reason_detail="Token ID not found or empty",
            severity="warning",
            is_tradable=False,
        )

    # 3: MARKET_CLOSED — not active or not accepting orders
    if not is_active or not accepting_orders:
        detail = (
            "Market is closed"
            if not is_active
            else "Market is not accepting orders"
        )
        return _result(
            state=MARKET_CLOSED,
            reason_code=MARKET_CLOSED,
            reason_detail=detail,
            severity="warning",
            is_tradable=False,
        )

    # 4: STALE_FEED — data older than staleness threshold
    if feed_age_seconds is not None and feed_age_seconds > feed_staleness_threshold:
        return _result(
            state=STALE_FEED,
            reason_code=STALE_FEED,
            reason_detail=(
                f"Feed age {feed_age_seconds:.1f}s exceeds "
                f"threshold {feed_staleness_threshold:.1f}s"
            ),
            severity="warning",
            is_tradable=False,
        )

    # 5: ORDERBOOK_NOT_READY — bid or ask price absent
    if best_bid is None or best_ask is None:
        return _result(
            state=ORDERBOOK_NOT_READY,
            reason_code=ORDERBOOK_NOT_READY,
            reason_detail="Bid or ask price not available",
            severity="warning",
            is_tradable=False,
        )

    # 6: EMPTY_ORDERBOOK — bid or ask is zero (market scheduled but not populated)
    if best_bid <= 0 or best_ask <= 0:
        return _result(
            state=EMPTY_ORDERBOOK,
            reason_code=EMPTY_ORDERBOOK,
            reason_detail="Best bid or ask is zero or negative",
            severity="warning",
            is_tradable=False,
        )

    # Compute spread — both bid and ask are confirmed > 0
    spread = round(best_ask - best_bid, 8)

    # 7: UNKNOWN — crossed orderbook is a data / stale-feed error
    if spread < 0:
        return _result(
            state=UNKNOWN,
            reason_code=UNKNOWN,
            reason_detail=f"Crossed orderbook: bid {best_bid} > ask {best_ask}",
            severity="error",
            is_tradable=False,
            spread=spread,
        )

    spread_pct = round(spread / best_ask, 6) if best_ask > 0 else None

    # 8: LOW_LIQUIDITY — insufficient orderbook depth
    if liquidity_threshold > 0 and orderbook_depth < liquidity_threshold:
        return _result(
            state=LOW_LIQUIDITY,
            reason_code=LOW_LIQUIDITY,
            reason_detail=(
                f"Orderbook depth {orderbook_depth} below "
                f"threshold {liquidity_threshold}"
            ),
            severity="warning",
            is_tradable=False,
            spread=spread,
            spread_pct=spread_pct,
        )

    # 9: HIGH_SPREAD — spread exceeds cost threshold
    if spread_pct is not None and spread_pct > spread_threshold:
        return _result(
            state=HIGH_SPREAD,
            reason_code=HIGH_SPREAD,
            reason_detail=(
                f"Spread {spread_pct:.4%} exceeds threshold {spread_threshold:.4%}"
            ),
            severity="warning",
            is_tradable=False,
            spread=spread,
            spread_pct=spread_pct,
        )

    # ACTIVE — all checks passed
    return _result(
        state=REASON_ACTIVE,
        reason_code=REASON_ACTIVE,
        reason_detail="Market is tradable",
        severity="info",
        is_tradable=True,
        spread=spread,
        spread_pct=spread_pct,
    )


def summarize_market_availability(
    snapshots: list[dict[str, object]],
    *,
    overall_state: str = "",
    checked_at: str = "",
    next_check_seconds: int = 30,
    api_error: str | None = None,
    api_latency_ms: int = 0,
    cache_hit: bool = False,
    matching_slugs: list[str] | None = None,
) -> AvailabilitySummary:
    """Aggregate multiple AvailabilitySnapshots into a summary.

    Computes tradable/non-tradable counts, symbol lists, and the
    highest-precedence reason code across all non-tradable snapshots.
    """
    tradable = [s for s in snapshots if s.get("is_tradable")]
    non_tradable = [s for s in snapshots if not s.get("is_tradable")]

    symbols = sorted(
        {str(s.get("ticker", "")) for s in tradable if s.get("ticker")}
    )
    btc_count = sum(
        1 for s in tradable if str(s.get("ticker", "")).upper() == "BTC"
    )
    eth_count = sum(
        1 for s in tradable if str(s.get("ticker", "")).upper() == "ETH"
    )

    non_tradable_codes = {
        str(s.get("reason", {}).get("reason_code", UNKNOWN))  # type: ignore[union-attr]
        for s in non_tradable
        if s.get("reason")
    }
    primary_reason_code = REASON_ACTIVE
    if non_tradable_codes:
        for code in _REASON_PRECEDENCE:
            if code in non_tradable_codes:
                primary_reason_code = code
                break

    if not overall_state:
        if tradable:
            overall_state = "ACTIVE"
        elif snapshots:
            overall_state = "BETWEEN_EPOCHS"
        else:
            overall_state = "UNKNOWN"

    return AvailabilitySummary(
        overall_state=overall_state,
        active_market_count=len(tradable),
        tradable_count=len(tradable),
        non_tradable_count=len(non_tradable),
        btc_market_count=btc_count,
        eth_market_count=eth_count,
        symbols_available=symbols,
        matching_slugs=list(matching_slugs or []),
        primary_reason_code=primary_reason_code,
        next_check_seconds=next_check_seconds,
        api_error=api_error,
        api_latency_ms=api_latency_ms,
        cache_hit=cache_hit,
        summary_checked_at=checked_at,
        schema_version=_SCHEMA_VERSION,
    )


def build_availability_health(
    *,
    state: str,
    reason_codes: list[str] | None = None,
    api_latency_ms: int = 0,
    active_market_count: int = 0,
    spread_pct: float | None = None,
    error: str | None = None,
) -> AvailabilityHealth:
    """Build a health verdict and score for overall market availability.

    state: engine state string — ACTIVE, BETWEEN_EPOCHS,
           MARKET_NOT_SCHEDULED, API_UNAVAILABLE, UNKNOWN.
    """
    health_score = _STATE_HEALTH_SCORE.get(state, 0.0)

    if health_score >= 0.9:
        grade = "A"
    elif health_score >= 0.7:
        grade = "B"
    elif health_score >= 0.5:
        grade = "C"
    elif health_score >= 0.2:
        grade = "D"
    else:
        grade = "F"

    if state == "ACTIVE":
        verdict = "HEALTHY"
    elif state in ("BETWEEN_EPOCHS", "MARKET_NOT_SCHEDULED"):
        verdict = "DEGRADED"
    else:
        verdict = "UNAVAILABLE"

    degradation_reasons: list[str] = []
    if state != "ACTIVE":
        degradation_reasons.append(state)
    if error:
        degradation_reasons.append(str(error))
    if reason_codes:
        for rc in reason_codes:
            if rc not in degradation_reasons and rc != REASON_ACTIVE:
                degradation_reasons.append(rc)

    score = _compute_availability_score(
        state=state,
        api_latency_ms=api_latency_ms,
        spread_pct=spread_pct,
        active_market_count=active_market_count,
    )

    return AvailabilityHealth(
        health_score=health_score,
        health_grade=grade,
        health_verdict=verdict,
        availability_score=score,
        degradation_reasons=degradation_reasons,
        recovery_suggestion=_STATE_RECOVERY.get(state, "Investigate and retry"),
        schema_version=_HEALTH_SCHEMA_VERSION,
    )


def build_market_availability_payload(
    *,
    state: str,
    active_market_count: int = 0,
    btc_market_count: int = 0,
    eth_market_count: int = 0,
    symbols_available: list[str] | None = None,
    matching_slugs: list[str] | None = None,
    next_check_seconds: int = 30,
    cache_hit: bool = False,
    api_latency_ms: int = 0,
    error: str | None = None,
    ticker: str = "",
    checked_at: str = "",
) -> dict[str, object]:
    """Build the full market availability observability payload.

    Accepts the same fields produced by MarketAvailabilityResult and adds
    a reason code, health assessment, and a distinct schema version
    (market_availability_obs_v1 vs. the engine's market_availability_v1).
    """
    primary_reason_code = _STATE_TO_REASON.get(state, UNKNOWN)
    health = build_availability_health(
        state=state,
        api_latency_ms=api_latency_ms,
        active_market_count=active_market_count,
        error=error,
    )
    return {
        "state": state,
        "active_market_count": active_market_count,
        "btc_market_count": btc_market_count,
        "eth_market_count": eth_market_count,
        "symbols_available": list(symbols_available or []),
        "matching_slugs": list(matching_slugs or []),
        "next_check_seconds": next_check_seconds,
        "cache_hit": cache_hit,
        "api_latency_ms": api_latency_ms,
        "error": error,
        "ticker": ticker,
        "checked_at": checked_at,
        "primary_reason_code": primary_reason_code,
        "health": health,
        "schema_version": _SCHEMA_VERSION,
    }
