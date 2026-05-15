"""
Executable State Persistence Probe Classifier v1.

Pure stateless classification of executable orderbook state persistence,
regression, and staleness at decision time. Returns 12 additive observability
fields — does NOT affect strategy, risk, execution, or paper/live behavior.

Called from _decision_diagnostics_payload to enrich JSONL payloads.
Also used by tools/executable_state_persistence_probe.py for offline aggregation.
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Regression source sets
# ---------------------------------------------------------------------------

_REGRESSION_SOURCES_CURRENT_NON_EXEC: frozenset[str] = frozenset({
    "CURRENT_FETCH_NON_EXECUTABLE_PRIOR_EXECUTABLE_SAME_TOKEN_PAIR",
})
_REGRESSION_SOURCES_NO_FETCH: frozenset[str] = frozenset({
    "NO_CURRENT_FETCH_PRIOR_EXECUTABLE_SAME_TOKEN_PAIR",
})
_NO_PRIOR_EXECUTABLE: frozenset[str] = frozenset({
    "NO_CURRENT_FETCH_NO_PRIOR_EXECUTABLE",
})

# States that count as "executable" for regression detection
_EXECUTABLE_STATES: frozenset[str] = frozenset({
    "EXECUTABLE", "TRADABLE", "SPREAD_NORMALIZED",
})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(v: Any) -> float | None:
    try:
        f = float(v)
        return f
    except (TypeError, ValueError):
        return None


def _safe_int(v: Any) -> int | None:
    try:
        return int(v) if v is not None and str(v).strip() != "" else None
    except (TypeError, ValueError):
        return None


def _truthy_str(v: Any) -> str:
    """Return stripped string or empty string."""
    if v is None:
        return ""
    return str(v).strip()


# ---------------------------------------------------------------------------
# Public classifier
# ---------------------------------------------------------------------------

def classify_executable_state_persistence(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Classify executable state persistence and regression from an existing decision payload.
    Returns 12 additive observability fields. Fail-soft: returns UNKNOWN
    defaults on any error. Does not mutate payload.
    """
    try:
        return _classify(payload)
    except Exception:
        return _unknown_defaults()


def _classify(payload: dict[str, Any]) -> dict[str, Any]:
    # --- inputs from existing payload ---
    first_tradable_ts = _truthy_str(payload.get("first_tradable_ts"))
    executable_book_last_seen_age_ms = _safe_float(payload.get("executable_book_last_seen_age_ms"))
    decision_ts = _truthy_str(payload.get("decision_timestamp") or payload.get("ts") or "")
    orderbook_stale_reuse_source = _truthy_str(payload.get("orderbook_stale_reuse_source")).upper()
    book_state = _truthy_str(payload.get("executable_book_state")).upper()
    # Dual-State: best-seen emitted by runtime since Fix B; fall back to inference from
    # first_tradable_ts when the field is absent (pre-Fix-B events or offline classification).
    best_seen_raw = _truthy_str(payload.get("executable_book_state_best_seen")).upper()
    orderbook_snapshot_age_ms = _safe_float(payload.get("orderbook_snapshot_age_ms_at_decision"))
    first_tradable_sec = _safe_int(payload.get("first_tradable_seconds_remaining"))
    seconds_remaining = _safe_int(payload.get("seconds_remaining"))

    # Revision count — number of times readiness bucket state changed
    readiness_bucket_revision_raw = _safe_int(payload.get("readiness_bucket_revision_count")
                                               or payload.get("readiness_bucket_revision"))

    # Transition count — number of orderbook state transitions observed
    transition_count_raw = _safe_int(payload.get("orderbook_state_transition_count_raw")
                                      or payload.get("state_transition_count"))

    # --- executable_state_first_seen_ts ---
    # Populated when first_tradable_ts is set (runtime sets it on first executable fetch)
    executable_state_first_seen_ts: str = first_tradable_ts if first_tradable_ts else ""

    # --- executable_state_persisted_to_decision ---
    # True when current book_state is still executable at decision time
    executable_state_persisted_to_decision: bool = book_state in _EXECUTABLE_STATES

    # --- executable_state_regressed ---
    # True when a prior executable state existed but current state is non-executable
    had_prior_executable = bool(first_tradable_ts) or (
        first_tradable_sec is not None and first_tradable_sec > 0
    )
    currently_non_executable = book_state not in _EXECUTABLE_STATES and book_state != ""
    regression_via_source = (
        orderbook_stale_reuse_source in _REGRESSION_SOURCES_CURRENT_NON_EXEC
        or orderbook_stale_reuse_source in _REGRESSION_SOURCES_NO_FETCH
    )
    executable_state_regressed: bool = (
        (had_prior_executable and currently_non_executable)
        or regression_via_source
    )

    # --- executable_regression_reason ---
    if not executable_state_regressed:
        executable_regression_reason = "NONE"
    elif orderbook_stale_reuse_source in _REGRESSION_SOURCES_CURRENT_NON_EXEC:
        executable_regression_reason = "CURRENT_FETCH_RETURNED_NON_EXECUTABLE"
    elif orderbook_stale_reuse_source in _REGRESSION_SOURCES_NO_FETCH:
        executable_regression_reason = "NO_FETCH_PRIOR_EXECUTABLE_STALE"
    elif had_prior_executable and currently_non_executable:
        executable_regression_reason = "STATE_DOWNGRADE_UNKNOWN_SOURCE"
    else:
        executable_regression_reason = "NONE"

    # --- executable_state_last_seen_ts ---
    # We can't reconstruct absolute timestamp from age alone without decision_ts parsing,
    # so we store the age as a descriptor when the regression source is known.
    # When persisted (not regressed), last_seen = current decision.
    if executable_state_persisted_to_decision:
        executable_state_last_seen_ts = decision_ts if decision_ts else "CURRENT"
    elif executable_book_last_seen_age_ms is not None:
        # Express as relative age string when absolute ts unavailable
        executable_state_last_seen_ts = f"ago_{int(executable_book_last_seen_age_ms)}ms"
    elif first_tradable_ts:
        executable_state_last_seen_ts = f"unknown_since_{first_tradable_ts}"
    else:
        executable_state_last_seen_ts = ""

    # --- executable_state_duration_ms ---
    # Duration the state was executable: approximated from first_tradable_sec and
    # executable_book_last_seen_age_ms when available.
    # If persisted: duration = time from first_tradable_sec to now (convert to ms)
    # If regressed: duration = first_tradable_sec window minus last_seen age
    executable_state_duration_ms: float | None = None
    if executable_state_persisted_to_decision and first_tradable_sec is not None and seconds_remaining is not None:
        # Duration = (first_tradable_sec - seconds_remaining) * 1000
        elapsed_sec = first_tradable_sec - seconds_remaining
        if elapsed_sec >= 0:
            executable_state_duration_ms = float(elapsed_sec * 1000)
    elif executable_book_last_seen_age_ms is not None and first_tradable_sec is not None and seconds_remaining is not None:
        # The state was seen at first_tradable_sec; last seen age tells us when it was last seen
        # Duration ≈ (first_tradable_sec - seconds_remaining) * 1000 - last_seen_age_ms
        elapsed_sec = first_tradable_sec - seconds_remaining
        if elapsed_sec >= 0:
            raw_dur = float(elapsed_sec * 1000) - executable_book_last_seen_age_ms
            executable_state_duration_ms = max(0.0, raw_dur)

    # --- evaluator_snapshot_state ---
    # The book state captured at the time the evaluator/model ran
    # This is the current book_state (runtime snapshots at decision time)
    evaluator_snapshot_state: str = book_state if book_state else "UNKNOWN"

    # --- evaluator_snapshot_age_ms ---
    # How old the orderbook snapshot was when the evaluator used it
    evaluator_snapshot_age_ms: float | None = orderbook_snapshot_age_ms

    # --- readiness_bucket_revision ---
    # How many times the readiness classification changed for this market
    readiness_bucket_revision: int = readiness_bucket_revision_raw if readiness_bucket_revision_raw is not None else 0

    # --- orderbook_state_transition_count ---
    # How many state transitions were observed
    orderbook_state_transition_count: int = transition_count_raw if transition_count_raw is not None else 0

    # --- normalized_to_token_ready_regression ---
    # Specific regression: state was SPREAD_NORMALIZED/EXECUTABLE, now TOKEN_READY
    normalized_to_token_ready_regression: bool = (
        book_state in {"TOKEN_READY"}
        and had_prior_executable
        and executable_state_regressed
    )

    # --- executable_to_non_executable_regression ---
    # Any regression from any executable state to any non-executable state
    executable_to_non_executable_regression: bool = executable_state_regressed

    # --- Dual-State: best_seen_state and current_vs_best_seen_diverged ---
    # best_seen_state: highest state reached this epoch.
    # When runtime emits executable_book_state_best_seen (Fix B), use it directly.
    # Fallback for pre-Fix-B events: infer from first_tradable_ts (market was executable
    # at some point → best_seen was at least SPREAD_NORMALIZED).
    _STATE_LEVEL: dict[str, int] = {
        "DISCOVERED": 0, "TOKEN_READY": 1, "BOOK_SEEN": 2,
        "NONZERO_BOOK": 3, "SPREAD_NORMALIZED": 4, "TRADABLE": 5,
        "UNKNOWN": -1,
    }
    if best_seen_raw and best_seen_raw not in ("UNKNOWN", ""):
        best_seen_state: str = best_seen_raw
    elif had_prior_executable:
        # first_tradable_ts set means state reached at least SPREAD_NORMALIZED level
        best_seen_state = "SPREAD_NORMALIZED"
    elif book_state and book_state not in ("UNKNOWN", ""):
        best_seen_state = book_state
    else:
        best_seen_state = "UNKNOWN"

    # current_vs_best_seen_diverged: True when current state is LOWER than best-seen
    current_level = _STATE_LEVEL.get(book_state, -1)
    best_level = _STATE_LEVEL.get(best_seen_state, -1)
    current_vs_best_seen_diverged: bool = (
        current_level >= 0 and best_level >= 0 and current_level < best_level
    )

    return {
        "executable_state_first_seen_ts": executable_state_first_seen_ts,
        "executable_state_last_seen_ts": executable_state_last_seen_ts,
        "executable_state_duration_ms": executable_state_duration_ms,
        "executable_state_persisted_to_decision": executable_state_persisted_to_decision,
        "executable_state_regressed": executable_state_regressed,
        "executable_regression_reason": executable_regression_reason,
        "evaluator_snapshot_state": evaluator_snapshot_state,
        "evaluator_snapshot_age_ms": evaluator_snapshot_age_ms,
        "readiness_bucket_revision": readiness_bucket_revision,
        "orderbook_state_transition_count": orderbook_state_transition_count,
        "normalized_to_token_ready_regression": normalized_to_token_ready_regression,
        "executable_to_non_executable_regression": executable_to_non_executable_regression,
        "best_seen_state": best_seen_state,
        "current_vs_best_seen_diverged": current_vs_best_seen_diverged,
    }


def _unknown_defaults() -> dict[str, Any]:
    return {
        "executable_state_first_seen_ts": "",
        "executable_state_last_seen_ts": "",
        "executable_state_duration_ms": None,
        "executable_state_persisted_to_decision": False,
        "executable_state_regressed": False,
        "executable_regression_reason": "UNKNOWN",
        "evaluator_snapshot_state": "UNKNOWN",
        "evaluator_snapshot_age_ms": None,
        "readiness_bucket_revision": 0,
        "orderbook_state_transition_count": 0,
        "normalized_to_token_ready_regression": False,
        "executable_to_non_executable_regression": False,
        "best_seen_state": "UNKNOWN",
        "current_vs_best_seen_diverged": False,
    }
