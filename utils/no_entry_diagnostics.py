from __future__ import annotations

from typing import Any


TIME_BUCKET_EARLY = "early_window"
TIME_BUCKET_MID = "mid_window"
TIME_BUCKET_LATE = "late_window"
TIME_BUCKET_UNSAFE = "unsafe_cutoff"
TIME_BUCKET_UNKNOWN = "unknown"
TIMING_PRESENT = "present"
TIMING_MISSING = "missing_data"
TIMING_UNPARSEABLE = "unparseable_data"


def normalize_skip_reason(reason: Any) -> str:
    text = str(reason or "").strip().lower()
    if not text:
        return "unknown"

    if "risk_plan_zero" in text or "zero position" in text:
        return "risk_plan_zero"
    if "orderbook" in text or "no_orderbook" in text or "bid/ask" in text:
        return "orderbook_unavailable"
    if "cutoff" in text or "entry timing" in text or "time_remaining" in text or "time remaining" in text:
        return "time_unsafe"
    if "delta_extreme" in text or "delta" in text:
        return "delta_extreme"
    if "confidence" in text:
        return "confidence_too_low"
    if "ev_below_threshold" in text or "scanner" in text or "threshold" in text or "ev" in text:
        return "ev_below_threshold"
    if "stale" in text or "feed" in text:
        return "stale_data"
    if "spread" in text:
        return "spread_too_wide"
    if "liquidity" in text or "min shares" in text:
        return "liquidity_too_low"
    if "cooldown" in text or "frequency" in text or "max 1" in text or "max entries" in text:
        return "frequency_cooldown"
    if any(token in text for token in ("risk", "floor", "balance", "drawdown", "reconciliation", "lockdown")):
        return "risk_off"
    if "missing_close_time" in text or "close_time" in text:
        return "missing_close_time"
    if "api" in text or "token" in text or "missing" in text or "parse" in text:
        return "api_missing_fields"
    return text.replace(" ", "_")[:80]


def classify_time_bucket(seconds_remaining: Any, entry_cutoff_seconds: Any = 90) -> str:
    try:
        seconds = int(float(seconds_remaining))
    except (TypeError, ValueError):
        return TIME_BUCKET_UNKNOWN
    try:
        cutoff = int(float(entry_cutoff_seconds))
    except (TypeError, ValueError):
        cutoff = 90

    if seconds <= cutoff:
        return TIME_BUCKET_UNSAFE
    if seconds > 240:
        return TIME_BUCKET_EARLY
    if seconds > 150:
        return TIME_BUCKET_MID
    return TIME_BUCKET_LATE


def classify_timing_status(seconds_remaining: Any) -> str:
    if seconds_remaining is None:
        return TIMING_MISSING
    if isinstance(seconds_remaining, str) and not seconds_remaining.strip():
        return TIMING_MISSING
    try:
        int(float(seconds_remaining))
    except (TypeError, ValueError):
        return TIMING_UNPARSEABLE
    return TIMING_PRESENT
