"""
Market Readiness Admission Probe Classifier v1.

Pure stateless classification of the admission pipeline stage for a
market decision event. Returns 12 additive observability fields — does
NOT affect strategy, risk, execution, or paper/live behavior.

Called from _decision_diagnostics_payload to enrich JSONL payloads.
Also used by tools/market_readiness_admission_probe.py for offline
aggregation.
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Book state sets
# ---------------------------------------------------------------------------

_BOOK_PRE_TOKEN: frozenset[str] = frozenset({"DISCOVERED", ""})
_BOOK_TOKEN_ONLY: frozenset[str] = frozenset({"TOKEN_READY"})
_BOOK_HAS_BOOK: frozenset[str] = frozenset({"BOOK_SEEN", "NONZERO_BOOK"})
_BOOK_NORMALIZED: frozenset[str] = frozenset({"SPREAD_NORMALIZED"})
_BOOK_EXECUTABLE: frozenset[str] = frozenset({"EXECUTABLE", "TRADABLE", "SPREAD_NORMALIZED"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_int(v: Any) -> int | None:
    try:
        return int(v) if v is not None and str(v).strip() != "" else None
    except (TypeError, ValueError):
        return None


def _safe_float(v: Any) -> float | None:
    try:
        f = float(v)
        return f
    except (TypeError, ValueError):
        return None


def _truthy_value(v: Any) -> bool:
    """True if value is present, non-None, non-empty-string, and not False."""
    if v is None or v is False or v == "" or v == 0:
        return False
    return True


# ---------------------------------------------------------------------------
# Public classifier
# ---------------------------------------------------------------------------

def classify_admission_probe(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Classify the admission pipeline state from an existing decision payload.
    Returns 12 additive observability fields. Fail-soft: returns UNKNOWN
    defaults on any error. Does not mutate payload.
    """
    try:
        return _classify(payload)
    except Exception:
        return _unknown_defaults()


def _classify(payload: dict[str, Any]) -> dict[str, Any]:
    # --- inputs ---
    seconds_remaining = _safe_int(payload.get("seconds_remaining"))
    entry_cutoff = _safe_int(payload.get("entry_cutoff_seconds")) or 90
    effective_cutoff = _safe_int(payload.get("effective_cutoff_seconds")) or entry_cutoff

    first_tradable_sec = _safe_int(payload.get("first_tradable_seconds_remaining"))
    first_evaluable_sec = _safe_int(payload.get("first_evaluable_seconds_remaining"))
    first_seen_sec = _safe_int(payload.get("first_seen_seconds_remaining"))

    book_state = str(payload.get("executable_book_state") or "").upper().strip()
    late_hard_block = bool(payload.get("late_entry_hard_block"))
    pre_model_gate_group = str(payload.get("pre_model_gate_group") or "").upper().strip()

    model_attempted = bool(payload.get("model_attempted"))
    model_output_visible = bool(payload.get("probability_model_output_visible"))
    fair_value_available = bool(payload.get("fair_value_available"))
    true_prob_available = bool(payload.get("true_probability_available"))

    ev_available = bool(payload.get("ev_after_spread_available"))
    ev_value = _safe_float(payload.get("ev_after_spread"))

    calc_size = _safe_float(payload.get("calculated_order_size")) or 0.0
    risk_per_trade = _safe_float(payload.get("risk_per_trade")) or 0.0

    # --- derived booleans ---

    # first_executable_before_cutoff: market had an executable book with
    # more time remaining than the cutoff threshold.
    # first_tradable_seconds_remaining=0 means unset (bucket default) → False.
    first_executable_before_cutoff: bool = (
        first_tradable_sec is not None
        and first_tradable_sec > 0
        and first_tradable_sec > effective_cutoff
    )

    # readiness_before_cutoff: executable book was available before cutoff,
    # OR book is currently in a normalized/executable state with time left.
    current_executable = book_state in _BOOK_EXECUTABLE or book_state in _BOOK_NORMALIZED
    readiness_before_cutoff: bool = (
        first_executable_before_cutoff
        or (
            current_executable
            and seconds_remaining is not None
            and seconds_remaining > effective_cutoff
        )
    )

    # candidate_seen_before_cutoff
    candidate_seen_before_cutoff: bool = (
        first_seen_sec is not None
        and first_seen_sec > 0
        and first_seen_sec > effective_cutoff
    )

    # candidate_evaluable_before_cutoff
    candidate_evaluable_before_cutoff: bool = (
        first_evaluable_sec is not None
        and first_evaluable_sec > 0
        and first_evaluable_sec > effective_cutoff
    )

    # gate flags
    model_gate_reached: bool = (
        model_attempted
        or model_output_visible
        or fair_value_available
        or true_prob_available
    )
    ev_gate_reached: bool = (
        ev_available
        or bool(fair_value_available)
        or (ev_value is not None and ev_value != 0.0)
    )
    risk_gate_reached: bool = (calc_size > 0.0) or (risk_per_trade > 0.0)

    # --- cutoff_policy_state ---
    if seconds_remaining is not None and seconds_remaining <= 0:
        cutoff_policy_state = "HARD_BLOCK"
    elif late_hard_block:
        cutoff_policy_state = "HARD_BLOCK"
    elif seconds_remaining is not None and seconds_remaining <= effective_cutoff:
        cutoff_policy_state = "SOFT_BLOCK"
    else:
        cutoff_policy_state = "OPEN"
    cutoff_block_observed = (
        cutoff_policy_state in {"HARD_BLOCK", "SOFT_BLOCK"}
        or pre_model_gate_group == "TIME_CUTOFF_GATE"
    )

    # --- admission_block_stage: earliest stage that blocked progression ---
    if cutoff_policy_state == "HARD_BLOCK" and not first_executable_before_cutoff:
        admission_block_stage = "CUTOFF"
    elif cutoff_block_observed and current_executable and not model_gate_reached:
        admission_block_stage = "CUTOFF"
    elif book_state in _BOOK_PRE_TOKEN:
        admission_block_stage = "TOKEN"
    elif book_state in _BOOK_TOKEN_ONLY:
        admission_block_stage = "ORDERBOOK"
    elif book_state in _BOOK_HAS_BOOK:
        admission_block_stage = "NORMALIZATION"
    elif not model_gate_reached:
        admission_block_stage = "MODEL_GATE"
    elif not ev_gate_reached:
        admission_block_stage = "EV_GATE"
    elif not risk_gate_reached:
        admission_block_stage = "RISK_GATE"
    else:
        admission_block_stage = "NONE"

    # --- admission_probe_state ---
    if first_executable_before_cutoff and not model_gate_reached:
        admission_probe_state = "EXECUTABLE_BEFORE_CUTOFF_NO_MODEL"
    elif first_executable_before_cutoff and model_gate_reached and not ev_gate_reached:
        admission_probe_state = "EXECUTABLE_BEFORE_CUTOFF_NO_EV"
    elif first_executable_before_cutoff and ev_gate_reached:
        admission_probe_state = "EXECUTABLE_EVALUATED"
    elif candidate_seen_before_cutoff and not first_executable_before_cutoff:
        admission_probe_state = "SEEN_NOT_EXECUTABLE_BEFORE_CUTOFF"
    elif cutoff_policy_state == "HARD_BLOCK":
        admission_probe_state = "CUTOFF_HARD_BLOCK"
    elif book_state in _BOOK_PRE_TOKEN:
        admission_probe_state = "LATE_DISCOVERY"
    elif book_state in (_BOOK_TOKEN_ONLY | _BOOK_HAS_BOOK):
        admission_probe_state = "TOKEN_READY_NOT_EXECUTABLE"
    else:
        admission_probe_state = "UNKNOWN"

    # --- admission_probe_reason: compact human-readable summary ---
    parts: list[str] = []
    if cutoff_policy_state != "OPEN":
        parts.append(f"cutoff={cutoff_policy_state.lower()}")
    if first_executable_before_cutoff:
        parts.append(f"first_exec_at_{first_tradable_sec}s")
    else:
        if first_tradable_sec is None or first_tradable_sec == 0:
            parts.append("no_first_executable")
        else:
            parts.append(f"first_exec_too_late_at_{first_tradable_sec}s")
    if not model_gate_reached:
        block = str(
            payload.get("model_activation_block_reason")
            or payload.get("model_output_missing_reason")
            or ""
        )
        if block:
            parts.append(f"model_blocked:{block[:35]}")
        else:
            parts.append("model_not_reached")
    if model_gate_reached and not ev_gate_reached:
        parts.append("ev_not_computed")
    admission_probe_reason = " | ".join(parts) if parts else "ok"

    return {
        "readiness_before_cutoff": readiness_before_cutoff,
        "first_executable_before_cutoff": first_executable_before_cutoff,
        "admission_probe_state": admission_probe_state,
        "admission_probe_reason": admission_probe_reason,
        "admission_block_stage": admission_block_stage,
        "model_gate_reached": model_gate_reached,
        "ev_gate_reached": ev_gate_reached,
        "risk_gate_reached": risk_gate_reached,
        "candidate_seen_before_cutoff": candidate_seen_before_cutoff,
        "candidate_evaluable_before_cutoff": candidate_evaluable_before_cutoff,
        "cutoff_policy_state": cutoff_policy_state,
        "effective_cutoff_seconds": effective_cutoff,
    }


def _unknown_defaults() -> dict[str, Any]:
    return {
        "readiness_before_cutoff": False,
        "first_executable_before_cutoff": False,
        "admission_probe_state": "UNKNOWN",
        "admission_probe_reason": "classifier_error",
        "admission_block_stage": "UNKNOWN",
        "model_gate_reached": False,
        "ev_gate_reached": False,
        "risk_gate_reached": False,
        "candidate_seen_before_cutoff": False,
        "candidate_evaluable_before_cutoff": False,
        "cutoff_policy_state": "UNKNOWN",
        "effective_cutoff_seconds": 0,
    }
