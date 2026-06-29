"""Offline decision diagnostics for canonical trade context rows.

This module is intentionally independent of runtime trading packages. It
labels context quality for offline analysis only and does not authorize orders.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA_VERSION = "decision_engine_prototype.v1"

PASS_CONTEXT = "PASS_CONTEXT"
REJECT_MISSING_CONTEXT = "REJECT_MISSING_CONTEXT"
REJECT_BAD_PROBABILITY = "REJECT_BAD_PROBABILITY"
REJECT_BAD_EV = "REJECT_BAD_EV"
REJECT_LOW_EVIDENCE = "REJECT_LOW_EVIDENCE"
REVIEW_REQUIRED = "REVIEW_REQUIRED"

_WEAK_EVIDENCE_GRADES = {"D", "E", "F"}
_REVIEW_EVIDENCE_GRADES = {"B", "C"}


def validate_trade_context(row: Mapping[str, Any]) -> dict[str, Any]:
    """Return structured offline diagnostics for one canonical context row."""

    missing_fields: list[str] = []
    reject_reasons: list[str] = []
    notes: list[str] = []

    intended_price = row.get("intended_price")
    probability_value, probability_field = _read_probability(row)
    ev_after_spread = row.get("ev_after_spread")

    if not _present(intended_price):
        missing_fields.append("intended_price")
    if probability_value is None:
        missing_fields.append("true_probability")
    if not _present(ev_after_spread):
        missing_fields.append("ev_after_spread")

    canonical_missing = _string_list(row.get("missing_fields"))
    for field in canonical_missing:
        if field not in missing_fields:
            missing_fields.append(field)

    probability_quality = _probability_quality(probability_value, probability_field)
    ev_quality = _ev_quality(ev_after_spread)
    evidence_quality = _evidence_quality(row)
    liquidity_quality = _liquidity_quality(row, intended_price)
    availability_quality = _availability_quality(missing_fields)

    if any(field in missing_fields for field in ("intended_price", "true_probability", "ev_after_spread")):
        reject_reasons.append("missing_required_context")
        decision_state = REJECT_MISSING_CONTEXT
    elif probability_quality["status"] == "FAIL":
        reject_reasons.append("invalid_probability")
        decision_state = REJECT_BAD_PROBABILITY
    elif ev_quality["status"] == "FAIL":
        reject_reasons.append("invalid_ev_after_spread")
        decision_state = REJECT_BAD_EV
    elif evidence_quality["status"] == "FAIL":
        reject_reasons.append("low_evidence_quality")
        decision_state = REJECT_LOW_EVIDENCE
    elif _requires_review(evidence_quality, liquidity_quality, availability_quality):
        decision_state = REVIEW_REQUIRED
    else:
        decision_state = PASS_CONTEXT

    if evidence_quality["status"] == "REVIEW":
        notes.append("evidence_quality_review")
    if liquidity_quality["status"] == "REVIEW":
        notes.append("liquidity_context_missing")
    if availability_quality["status"] == "REVIEW":
        notes.append("noncritical_context_missing")

    return {
        "schema_version": SCHEMA_VERSION,
        "decision_state": decision_state,
        "confidence": _confidence_for(decision_state),
        "missing_fields": missing_fields,
        "evidence_quality": evidence_quality,
        "probability_quality": probability_quality,
        "ev_quality": ev_quality,
        "liquidity_quality": liquidity_quality,
        "availability_quality": availability_quality,
        "reject_reasons": reject_reasons,
        "notes": notes,
    }


def evaluate_trade_context(row: Mapping[str, Any]) -> dict[str, Any]:
    """Alias for callers that prefer decision-engine wording."""

    return validate_trade_context(row)


def _read_probability(row: Mapping[str, Any]) -> tuple[Any | None, str]:
    for field in ("true_probability", "probability"):
        value = row.get(field)
        if _present(value):
            return value, field
    return None, "true_probability"


def _probability_quality(value: Any | None, field: str) -> dict[str, Any]:
    if value is None:
        return {"status": "MISSING", "field": field, "value": None}

    numeric = _as_float(value)
    if numeric is None or not 0.0 < numeric < 1.0:
        return {"status": "FAIL", "field": field, "value": _json_value(value)}

    return {"status": "PASS", "field": field, "value": numeric}


def _ev_quality(value: Any) -> dict[str, Any]:
    if not _present(value):
        return {"status": "MISSING", "field": "ev_after_spread", "value": None}

    numeric = _as_float(value)
    if numeric is None or numeric <= 0.0:
        return {"status": "FAIL", "field": "ev_after_spread", "value": _json_value(value)}

    return {"status": "PASS", "field": "ev_after_spread", "value": numeric}


def _evidence_quality(row: Mapping[str, Any]) -> dict[str, Any]:
    grade = str(row.get("data_quality_grade") or "UNKNOWN").upper()
    join_confidence = str(row.get("join_confidence") or "UNKNOWN").upper()
    source_streams = _string_list(row.get("source_streams"))
    source_stream_count = len(source_streams)

    status = "PASS"
    if grade in _WEAK_EVIDENCE_GRADES or join_confidence in {"LOW", "INSUFFICIENT"}:
        status = "FAIL"
    elif grade in _REVIEW_EVIDENCE_GRADES or join_confidence in {"MEDIUM", "UNKNOWN"} or source_stream_count < 2:
        status = "REVIEW"

    return {
        "status": status,
        "data_quality_grade": grade,
        "join_confidence": join_confidence,
        "source_stream_count": source_stream_count,
        "source_streams": source_streams,
    }


def _liquidity_quality(row: Mapping[str, Any], intended_price: Any) -> dict[str, Any]:
    quote_age_ms = row.get("quote_age_ms")
    slippage = row.get("slippage")
    source_streams = set(_string_list(row.get("source_streams")))
    has_liquidity_context = _present(quote_age_ms) or _present(slippage) or "execution_log" in source_streams

    if not _present(intended_price):
        status = "FAIL"
    elif has_liquidity_context:
        status = "PASS"
    else:
        status = "REVIEW"

    return {
        "status": status,
        "intended_price_present": _present(intended_price),
        "quote_age_ms_present": _present(quote_age_ms),
        "slippage_present": _present(slippage),
        "execution_stream_present": "execution_log" in source_streams,
    }


def _availability_quality(missing_fields: Sequence[str]) -> dict[str, Any]:
    required_missing = [field for field in missing_fields if field in {"intended_price", "true_probability", "ev_after_spread"}]
    if required_missing:
        status = "FAIL"
    elif missing_fields:
        status = "REVIEW"
    else:
        status = "PASS"

    return {
        "status": status,
        "required_missing_fields": required_missing,
        "missing_field_count": len(missing_fields),
    }


def _requires_review(*qualities: Mapping[str, Any]) -> bool:
    return any(quality.get("status") == "REVIEW" for quality in qualities)


def _confidence_for(decision_state: str) -> str:
    if decision_state == PASS_CONTEXT:
        return "HIGH"
    if decision_state == REVIEW_REQUIRED:
        return "MEDIUM"
    return "LOW"


def _present(value: Any) -> bool:
    return value is not None and value != ""


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, Sequence):
        return [str(item) for item in value if item is not None and str(item)]
    return [str(value)]


def _json_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


__all__ = [
    "PASS_CONTEXT",
    "REJECT_BAD_EV",
    "REJECT_BAD_PROBABILITY",
    "REJECT_LOW_EVIDENCE",
    "REJECT_MISSING_CONTEXT",
    "REVIEW_REQUIRED",
    "SCHEMA_VERSION",
    "evaluate_trade_context",
    "validate_trade_context",
]
