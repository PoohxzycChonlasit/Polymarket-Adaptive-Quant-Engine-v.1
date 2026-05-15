"""
Decision Cycle Timing Alignment Classifier v1.

Pure stateless classification of decision-cycle timing relative to the market
entry window. Returns 9 per-event observability fields derived from the existing
decision-log payload — does NOT add new runtime fields, affect strategy, risk,
execution, or paper/live behavior.

Used by tools/decision_cycle_timing_probe.py for offline aggregation.
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Lifecycle phase thresholds — must mirror _phase2_lifecycle_phase in trader.py
# ---------------------------------------------------------------------------

_EPOCH_SECONDS: int = 300  # 5-minute market epoch
_OPENING_SCAN_CUTOFF: int = 35       # seconds since open
_ACTIVE_END_SECONDS_SINCE_OPEN: int = 240
_PROFIT_END_SECONDS_SINCE_OPEN: int = 270

# Hard entry safety gate from settings.py (execution_entry_cutoff_seconds)
_ENTRY_CUTOFF_SECONDS: int = 90

_ACTIVE_PHASES: frozenset[str] = frozenset({"ACTIVE_INVENTORY_TRADING"})
_LATE_PHASES: frozenset[str] = frozenset({
    "FINAL_DERISK", "PROFIT_MANAGEMENT", "CLOSED_OR_UNSAFE",
})


# ---------------------------------------------------------------------------
# Timestamp parsing
# ---------------------------------------------------------------------------

def _parse_iso(ts: Any) -> float | None:
    """Return POSIX timestamp float from ISO-8601 string, or None on failure."""
    if not ts:
        return None
    s = str(ts).strip()
    if not s:
        return None
    try:
        from datetime import datetime, timezone
        # Handle trailing Z
        s = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return None


def _safe_int(v: Any) -> int | None:
    try:
        return int(v) if v is not None and str(v).strip() not in ("", "None") else None
    except (TypeError, ValueError):
        return None


def _safe_float(v: Any) -> float | None:
    try:
        f = float(v)
        return f
    except (TypeError, ValueError):
        return None


def _truthy_str(v: Any) -> str:
    return str(v).strip() if v is not None else ""


# ---------------------------------------------------------------------------
# Public classifier
# ---------------------------------------------------------------------------

def classify_decision_cycle_timing(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Classify decision-cycle timing from an existing decision payload.
    Returns 9 additive observability fields. Fail-soft: UNKNOWN defaults on error.
    Does not mutate payload.
    """
    try:
        return _classify(payload)
    except Exception:
        return _unknown_defaults()


def _classify(payload: dict[str, Any]) -> dict[str, Any]:
    seconds_remaining = _safe_int(payload.get("seconds_remaining"))
    lifecycle_phase = _truthy_str(payload.get("lifecycle_phase"))
    decision_ts_raw = _truthy_str(
        payload.get("decision_timestamp") or payload.get("decision_cycle_started_at") or ""
    )
    first_tradable_ts = _truthy_str(payload.get("first_tradable_ts"))
    first_discovered_ts = _truthy_str(
        payload.get("first_discovered_ts") or payload.get("first_discovered_ts_raw") or ""
    )
    # Inter-cycle gap — already in payload as decision_cycle_interval_seconds
    gap_raw = _safe_float(
        payload.get("decision_cycle_interval_seconds")
        or payload.get("actual_market_revisit_frequency_seconds")
    )
    first_tradable_sec_rem = _safe_int(payload.get("first_tradable_seconds_remaining"))

    # --- decision_cycle_ts ---
    decision_cycle_ts: str = decision_ts_raw

    # --- decision_cycle_seconds_remaining ---
    decision_cycle_seconds_remaining: int | None = seconds_remaining

    # --- decision_cycle_seconds_since_open ---
    if seconds_remaining is not None:
        decision_cycle_seconds_since_open: int | None = max(
            0, min(_EPOCH_SECONDS, _EPOCH_SECONDS - seconds_remaining)
        )
    else:
        decision_cycle_seconds_since_open = None

    # --- decision_cycle_lifecycle_phase ---
    decision_cycle_lifecycle_phase: str = lifecycle_phase if lifecycle_phase else "UNKNOWN"

    # --- decision_cycle_gap_seconds ---
    decision_cycle_gap_seconds: float | None = gap_raw

    # --- entry_window_decision_seen ---
    # True when this decision occurred during ACTIVE_INVENTORY_TRADING with time to trade
    entry_window_decision_seen: bool = (
        lifecycle_phase in _ACTIVE_PHASES
        and seconds_remaining is not None
        and seconds_remaining > _ENTRY_CUTOFF_SECONDS
    )

    # --- model_gate_blocked_by_timing ---
    # True when lifecycle or remaining seconds exclude this event from model evaluation
    model_gate_blocked_by_timing: bool = (
        lifecycle_phase in _LATE_PHASES
        or (seconds_remaining is not None and seconds_remaining <= _ENTRY_CUTOFF_SECONDS)
    )

    # --- executable_first_seen_to_decision_ms ---
    # Time from market first becoming executable to this decision cycle
    executable_first_seen_to_decision_ms: float | None = None
    if first_tradable_ts and decision_ts_raw:
        t_exec = _parse_iso(first_tradable_ts)
        t_dec = _parse_iso(decision_ts_raw)
        if t_exec is not None and t_dec is not None:
            delta = (t_dec - t_exec) * 1000.0
            executable_first_seen_to_decision_ms = round(delta, 1)

    # --- candidate_first_seen_to_decision_ms ---
    # Time from market discovery to this decision cycle
    candidate_first_seen_to_decision_ms: float | None = None
    if first_discovered_ts and decision_ts_raw:
        t_disc = _parse_iso(first_discovered_ts)
        t_dec = _parse_iso(decision_ts_raw)
        if t_disc is not None and t_dec is not None:
            delta = (t_dec - t_disc) * 1000.0
            candidate_first_seen_to_decision_ms = round(delta, 1)

    # --- active_inventory_window_missed ---
    # True when the market had a usable executable state before the entry cutoff,
    # but this decision is NOT in the active window. Set at event level as a flag
    # that the aggregation layer uses to identify missed-window epochs.
    had_early_executable = (
        first_tradable_sec_rem is not None and first_tradable_sec_rem > _ENTRY_CUTOFF_SECONDS
    )
    active_inventory_window_missed: bool = (
        had_early_executable and not entry_window_decision_seen
    )

    return {
        "decision_cycle_ts": decision_cycle_ts,
        "decision_cycle_seconds_remaining": decision_cycle_seconds_remaining,
        "decision_cycle_seconds_since_open": decision_cycle_seconds_since_open,
        "decision_cycle_lifecycle_phase": decision_cycle_lifecycle_phase,
        "decision_cycle_gap_seconds": decision_cycle_gap_seconds,
        "entry_window_decision_seen": entry_window_decision_seen,
        "model_gate_blocked_by_timing": model_gate_blocked_by_timing,
        "executable_first_seen_to_decision_ms": executable_first_seen_to_decision_ms,
        "candidate_first_seen_to_decision_ms": candidate_first_seen_to_decision_ms,
        "active_inventory_window_missed": active_inventory_window_missed,
    }


def _unknown_defaults() -> dict[str, Any]:
    return {
        "decision_cycle_ts": "",
        "decision_cycle_seconds_remaining": None,
        "decision_cycle_seconds_since_open": None,
        "decision_cycle_lifecycle_phase": "UNKNOWN",
        "decision_cycle_gap_seconds": None,
        "entry_window_decision_seen": False,
        "model_gate_blocked_by_timing": False,
        "executable_first_seen_to_decision_ms": None,
        "candidate_first_seen_to_decision_ms": None,
        "active_inventory_window_missed": False,
    }
