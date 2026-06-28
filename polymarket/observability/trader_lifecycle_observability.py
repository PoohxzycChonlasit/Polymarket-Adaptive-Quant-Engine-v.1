"""Pure observability utility functions extracted from PolymarketTrader.

EXTRACTION SCOPE — Phase 1 of TRADER_MODULE_DECOMPOSITION_AUDIT_001:
  Only @staticmethod pure functions with no trading state side effects.
  All functions here:
    - take only explicit inputs (no self / trader state)
    - return primitive values or dicts
    - have no side effects on order submission, risk, sizing, wallet, or
      reconciliation paths

trader.py retains thin @staticmethod wrappers that delegate here for
backward compatibility with existing call sites.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


# ── Diagnostic type converters ──────────────────────────────────────────────

def diagnostic_float(value: object, default: float = 0.0) -> float:
    """Safe float conversion, returning default on None/bool/invalid."""
    if isinstance(value, bool) or value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def diagnostic_int(value: object) -> int | None:
    """Safe int conversion, returning None on None/invalid."""
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


# ── Lifecycle phase classification ───────────────────────────────────────────

def phase2_lifecycle_phase(seconds_remaining: object = None) -> str:
    """Return lifecycle phase string from seconds remaining to market close.

    300s = epoch start; 0s = market close.
    """
    seconds = diagnostic_int(seconds_remaining)
    if seconds is None or seconds <= 0:
        return "CLOSED_OR_UNSAFE"
    seconds_since_open = max(0, min(300, 300 - seconds))
    if seconds_since_open < 35:
        return "OPENING_SCAN"
    if seconds_since_open < 240:
        return "ACTIVE_INVENTORY_TRADING"
    if seconds_since_open < 270:
        return "PROFIT_MANAGEMENT"
    if seconds_since_open <= 300:
        return "FINAL_DERISK"
    return "CLOSED_OR_UNSAFE"


def phase2_elapsed_second(seconds_remaining: object) -> int | None:
    """Return elapsed seconds since epoch open (0–300), or None."""
    remaining = diagnostic_int(seconds_remaining)
    if remaining is None:
        return None
    return int(max(0, min(300, 300 - remaining)))


def phase2_candidate_survival_ms(payload: dict[str, Any]) -> int | None:
    """Return candidate survival in milliseconds from a detail payload."""
    first_seen = diagnostic_int(payload.get("first_seen_seconds_remaining"))
    remaining = diagnostic_int(
        payload.get("seconds_remaining") or payload.get("seconds_until_close")
    )
    if first_seen is None or remaining is None:
        return None
    return int(max(0, first_seen - remaining) * 1000)


# ── Orderbook state helpers ──────────────────────────────────────────────────

def phase2_book_state_level(state: object) -> int:
    """Map orderbook state string to a numeric severity level (lower = better)."""
    levels = {
        "TRADABLE": 0,
        "EXECUTABLE": 0,
        "WARMED": 1,
        "THIN": 2,
        "EMPTY": 3,
        "STALE": 4,
        "FAIL": 5,
        "UNKNOWN": 6,
    }
    return levels.get(str(state or "").upper(), 6)


def orderbook_age_ms(snapshot: object) -> int:
    """Return orderbook age in milliseconds from a snapshot object."""
    try:
        return int(max(0.0, float(getattr(snapshot, "age_seconds", 0.0) or 0.0)) * 1000)
    except (TypeError, ValueError):
        return 0


def is_empty_orderbook_error(error: object) -> bool:
    """Return True if the error represents a truly empty orderbook."""
    message = str(error).lower()
    return (
        "empty_orderbook" in message
        or "empty_book" in message
        or "invalid_orderbook" in message
        or "clob_empty_response" in message
    )


def empty_book_recovery_detail(*, liquidity_state: str = "HEALTHY") -> dict[str, object]:
    """Return an empty-book recovery detail dict with defaults."""
    return {
        "empty_book_recovery_attempted": False,
        "empty_book_recovery_succeeded": False,
        "empty_book_recovery_skip_reason": "",
        "liquidity_state": liquidity_state,
        "liquidity_depth_state": liquidity_state,
        "liquidity_depth_confidence": 1.0 if liquidity_state == "HEALTHY" else 0.0,
    }


# ── Orderbook lineage helpers ────────────────────────────────────────────────

def orderbook_lineage_compact_text(value: object, *, limit: int = 160) -> str:
    """Compact a value to a single-line string, truncating at `limit`."""
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    if len(text) > limit:
        return text[: max(0, limit - 3)] + "..."
    return text


def orderbook_lineage_raw_count(ob: object, key: str) -> int | None:
    """Return the count of items in a raw orderbook response field."""
    raw = getattr(ob, "raw_response", None)
    if not isinstance(raw, dict):
        return None
    value = raw.get(key)
    if isinstance(value, list):
        return len(value)
    return None


def orderbook_lineage_current_fetch_status(
    orderbook_refresh_detail: dict[str, object],
    orderbook_fetch_succeeded: bool | None,
    current_executable_yes_no_book: bool,
) -> str:
    """Classify current orderbook fetch status into a canonical string.

    Mirrors the logic in PolymarketTrader._orderbook_lineage_current_fetch_status.
    """
    raw = str(
        orderbook_refresh_detail.get("orderbook_current_fetch_status") or ""
    ).strip()
    if raw == "fresh_fetch_not_attempted_or_unobserved":
        return "fresh_fetch_not_attempted"
    if raw:
        return raw
    if orderbook_fetch_succeeded is True and current_executable_yes_no_book:
        return "fresh_fetch_executable"
    if orderbook_fetch_succeeded is True:
        return "fresh_fetch_non_executable"
    if orderbook_fetch_succeeded is False:
        return "fresh_fetch_failed"
    if orderbook_fetch_succeeded is None:
        return "unknown"
    return "unknown"


# ── Path truth helpers ───────────────────────────────────────────────────────

def path_truth_parse_ts(raw: object) -> datetime | None:
    """Parse a timestamp string into a timezone-aware UTC datetime."""
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except Exception:
        return None
