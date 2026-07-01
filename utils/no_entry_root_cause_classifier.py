"""
No-Entry Root Cause Classifier v1.

Pure stateless classification of why a market produced no entry.
Observability-only — does not affect strategy, risk, execution, or paper/live behavior.
Called from _decision_diagnostics_payload to add structured fields to JSONL.
Also used by tools/no_entry_root_cause_report.py for offline aggregation.
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Keyword match tables — substring search against normalized_skip_reason
# ---------------------------------------------------------------------------

# Observability-only reason sources. Provenance:
# NO_ENTRY_CLASSIFIER_RISK_OFF_LABEL_REPAIR_001 and
# BOOK_WARMING_ROOT_CAUSE_AND_MARKET_LIFECYCLE_AUDIT_001 showed that
# model_not_run_reason=risk_off and raw hard-drawdown reasons must be
# considered before lifecycle fallback labels such as book_warming.
_REASON_SOURCE_FIELDS: tuple[str, ...] = (
    "normalized_skip_reason",
    "raw_skip_reason",
    "skip_reason",
    "model_not_run_reason",
)

_TIMING_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("time_unsafe",            "cutoff_passed"),
    ("late_entry",             "cutoff_passed"),
    ("hard_close_zone",        "cutoff_passed"),
    ("final_derisk",           "cutoff_passed"),
    ("cutoff",                 "cutoff_passed"),
    ("book_warming",           "book_warming"),
    ("empty_book",             "book_warming"),
    ("orderbook_unavailable",  "book_warming"),
    ("warmup",                 "book_warming"),
    ("clob_error",             "book_warming"),
    ("clob_timeout",           "book_warming"),
    ("clob_rate_limited",      "book_warming"),
    ("missing_token",          "token_not_ready"),
    ("token_not_ready",        "token_not_ready"),
    ("token_mapping",          "token_not_ready"),
    ("no_token",               "token_not_ready"),
    ("late_discovery",         "late_discovery"),
    ("preload",                "book_warming"),
)

_EVIDENCE_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("confidence_too_low",          "confidence_below_threshold"),
    ("confidence_low",              "confidence_below_threshold"),
    ("ev_negative",                 "ev_negative"),
    ("ev_below",                    "ev_negative"),   # must precede "below_threshold"
    ("ev_insufficient",             "ev_negative"),
    ("ev_too_low",                  "ev_negative"),
    ("below_threshold",             "confidence_below_threshold"),
    ("no_probability_model_output", "probability_unstable"),
    ("probability_unstable",        "probability_unstable"),
    ("no_fair_value",               "probability_unstable"),
    ("model_not_attempted",         "probability_unstable"),
    ("regime_unclear",              "regime_unclear"),
    ("regime_filtered",             "regime_unclear"),
    ("regime_block",                "regime_unclear"),
)

_RISK_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("hard_drawdown",      "drawdown_cap"),
    ("risk_off",           "risk_mode_defensive"),
    ("runtime_safety_gate", "risk_mode_defensive"),
    ("runtime safety gate", "risk_mode_defensive"),
    ("risk_mode_lockdown", "risk_mode_defensive"),
    ("min_bet",             "bankroll_too_small"),
    ("bankroll_too_small",  "bankroll_too_small"),
    ("insufficient_funds",  "bankroll_too_small"),
    ("zero_size",           "zero_size_plan"),
    ("risk_plan_zero",      "zero_size_plan"),
    ("no_risk_plan",        "zero_size_plan"),
    ("lockdown",            "risk_mode_defensive"),
    ("defensive",           "risk_mode_defensive"),
    ("micro_recovery",      "risk_mode_defensive"),
    ("risk_mode",           "risk_mode_defensive"),
    ("max_drawdown",        "drawdown_cap"),
    ("drawdown_cap",        "drawdown_cap"),
    ("drawdown",            "drawdown_cap"),
    ("reconciliation",      "risk_mode_defensive"),
    ("blocked",             "risk_mode_defensive"),
)

_MICROSTRUCTURE_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("spread_too_wide",       "spread_too_wide"),
    ("spread_not_executable", "spread_too_wide"),
    ("wide_spread",           "spread_too_wide"),
    ("thin_liquidity",        "thin_liquidity"),
    ("insufficient_liquidity","thin_liquidity"),
    ("liquidity_not_ready",   "thin_liquidity"),
    ("low_liquidity",         "thin_liquidity"),
    ("stale_book",            "stale_book"),
    ("orderbook_stale",       "stale_book"),
    ("stale_orderbook",       "stale_book"),
    ("imbalance_extreme",     "imbalance_extreme"),
    ("delta_extreme",         "imbalance_extreme"),
    ("imbalance",             "imbalance_extreme"),
)

# Orderbook states that signal timing blocks via lifecycle evidence
_TIMING_READINESS_STATES = frozenset({
    "DISCOVERED", "TOKEN_READY", "BOOK_SEEN", "NONZERO_BOOK",
})

# Empty return structure
_EMPTY: dict[str, Any] = {
    "skip_reason_category": "system_or_unknown",
    "skip_reason_primary": "unclassified",
    "skip_reason_secondary": "",
    "no_entry_root_cause_confidence": 0.1,
    "timing_block_reason": "",
    "evidence_block_reason": "",
    "risk_block_reason": "",
    "microstructure_block_reason": "",
}


def _first_match(reason_lower: str, table: tuple[tuple[str, str], ...]) -> str | None:
    for keyword, label in table:
        if keyword in reason_lower:
            return label
    return None


def _reason_candidates(payload: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    for field in _REASON_SOURCE_FIELDS:
        text = str(payload.get(field) or "").lower().strip()
        if text and text not in candidates:
            candidates.append(text)
    return candidates


def _first_match_from_candidates(
    candidates: list[str],
    table: tuple[tuple[str, str], ...],
) -> str | None:
    for reason in candidates:
        match = _first_match(reason, table)
        if match:
            return match
    return None


def classify_no_entry_root_cause(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Classify why a market produced no entry.
    Returns 8 additive observability fields — does not mutate payload.
    Fail-soft: returns system_or_unknown defaults on any error.
    """
    try:
        return _classify(payload)
    except Exception:
        return dict(_EMPTY)


def _classify(payload: dict[str, Any]) -> dict[str, Any]:
    # --- gather inputs ---
    raw_reason = str(payload.get("raw_skip_reason") or payload.get("skip_reason") or "")
    reason_candidates = _reason_candidates(payload)
    norm_reason = reason_candidates[0] if reason_candidates else raw_reason.lower().strip()

    book_state = str(payload.get("executable_book_state") or "").upper()
    first_tradable_ts = str(payload.get("first_tradable_ts") or "").strip()
    first_tradable_sec = _safe_int(payload.get("first_tradable_seconds_remaining"))
    first_disc_sec = _safe_int(payload.get("first_discovered_seconds_remaining"))
    seconds_remaining = _safe_int(payload.get("seconds_remaining"))
    spread_normalized = payload.get("spread_normalized")
    liquidity_state = str(payload.get("liquidity_state") or "").upper()
    model_block = str(payload.get("model_activation_block_group") or "").lower()
    is_skipped = bool(payload.get("skipped", True))

    # --- pass 1: keyword match against reason string ---
    category = ""
    primary = ""
    secondary = ""
    confidence = 0.1

    timing_match = _first_match_from_candidates(reason_candidates, _TIMING_KEYWORDS)
    evidence_match = _first_match_from_candidates(reason_candidates, _EVIDENCE_KEYWORDS)
    risk_match = _first_match_from_candidates(reason_candidates, _RISK_KEYWORDS)
    micro_match = _first_match_from_candidates(reason_candidates, _MICROSTRUCTURE_KEYWORDS)

    if risk_match:
        category, primary, confidence = "risk", risk_match, 0.9
    elif timing_match:
        category, primary, confidence = "timing", timing_match, 0.9
    elif micro_match:
        category, primary, confidence = "microstructure", micro_match, 0.9
    elif evidence_match:
        category, primary, confidence = "evidence", evidence_match, 0.85

    # --- pass 2: lifecycle evidence refinement ---
    lifecycle_primary = ""

    # Determine whether lifecycle evidence is actually present in this payload.
    # Check both non-empty values AND explicit key presence (key written but empty = data was collected).
    _has_lifecycle_data = bool(
        payload.get("first_discovered_ts")
        or first_disc_sec is not None
        or book_state not in {"", "UNKNOWN"}
        or first_tradable_sec is not None
        or "first_tradable_ts" in payload
        or "first_discovered_ts" in payload
        or "executable_book_state" in payload
    )

    if not category or confidence < 0.5:
        # Use lifecycle readiness state to improve classification
        if book_state in _TIMING_READINESS_STATES:
            if "TOKEN_READY" in book_state or "DISCOVERED" in book_state:
                lifecycle_primary = "token_not_ready"
            else:
                lifecycle_primary = "book_warming"
            if not category:
                category, primary, confidence = "timing", lifecycle_primary, 0.6
        elif first_disc_sec is not None and first_disc_sec < 60:
            # Late discovery check BEFORE first_executable_too_late — more specific
            lifecycle_primary = "late_discovery"
            if not category:
                category, primary, confidence = "timing", lifecycle_primary, 0.5
        elif _has_lifecycle_data and not first_tradable_ts and is_skipped:
            # Only infer first_executable_too_late when we have real lifecycle evidence
            lifecycle_primary = "first_executable_too_late"
            if not category:
                category, primary, confidence = "timing", lifecycle_primary, 0.4
        elif first_tradable_sec is not None and seconds_remaining is not None:
            if first_tradable_sec - seconds_remaining > 120:
                lifecycle_primary = "first_executable_too_late"
                if not category:
                    category, primary, confidence = "timing", lifecycle_primary, 0.4

    # --- pass 3: model_activation_block_group as evidence signal ---
    if not category and model_block:
        if "orderbook" in model_block or "book" in model_block:
            category, primary, confidence = "timing", "book_warming", 0.5
        elif "lifecycle" in model_block or "timing" in model_block:
            category, primary, confidence = "timing", "cutoff_passed", 0.5
        elif "spread" in model_block or "microstructure" in model_block:
            category, primary, confidence = "microstructure", "spread_too_wide", 0.5
        elif "risk" in model_block:
            category, primary, confidence = "risk", "risk_mode_defensive", 0.5

    # --- pass 4: spread/liquidity state override ---
    if not category:
        if spread_normalized is False or "WIDE" in str(spread_normalized or "").upper():
            category, primary, confidence = "microstructure", "spread_too_wide", 0.45
        elif liquidity_state in {"THIN", "EMPTY", "UNSTABLE"}:
            category, primary, confidence = "microstructure", "thin_liquidity", 0.45

    # --- secondary reason: add lifecycle evidence as context if primary came from keywords ---
    if category and lifecycle_primary and lifecycle_primary != primary:
        secondary = lifecycle_primary
    elif category == "timing" and evidence_match:
        secondary = evidence_match
    elif category == "evidence" and timing_match:
        secondary = timing_match

    # --- fallback ---
    if not category:
        category = "system_or_unknown"
        primary = "unclassified"
        confidence = 0.1

    # --- build per-category reason slots ---
    timing_block = primary if category == "timing" else (secondary if secondary and category != "timing" and _is_timing(secondary) else "")
    evidence_block = primary if category == "evidence" else (secondary if secondary and _is_evidence(secondary) else "")
    risk_block = primary if category == "risk" else ""
    micro_block = primary if category == "microstructure" else ""

    return {
        "skip_reason_category": category,
        "skip_reason_primary": primary,
        "skip_reason_secondary": secondary,
        "no_entry_root_cause_confidence": round(float(confidence), 2),
        "timing_block_reason": timing_block,
        "evidence_block_reason": evidence_block,
        "risk_block_reason": risk_block,
        "microstructure_block_reason": micro_block,
    }


def _safe_int(v: Any) -> int | None:
    try:
        return int(v) if v is not None and str(v).strip() != "" else None
    except (TypeError, ValueError):
        return None


def _is_timing(reason: str) -> bool:
    return reason in {
        "cutoff_passed", "book_warming", "token_not_ready",
        "late_discovery", "first_executable_too_late",
    }


def _is_evidence(reason: str) -> bool:
    return reason in {
        "confidence_below_threshold", "ev_negative",
        "probability_unstable", "regime_unclear",
    }
