from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from tools.unknown.candidate_continuity import (
    _parse_timestamp,
    build_candidate_continuity_report,
)
from tools.unknown.candidate_path_observability import (
    _event_identity_matches,
    _event_in_chain_window,
    _event_market_matches,
)
from tools.unknown.lifecycle_truth_tables import (
    _date_part,
    _first_value,
    _payload,
    _phase,
)
from tools.replay_analyzer import (
    DEFAULT_QUANT_DATA_DIR,
    DEFAULT_REPORT_DIR,
    build_phase2_coverage_from_events,
    build_time_filter,
    load_replay_events,
)


EV_COMPONENT_FIELDS = ("fair_value", "market_price", "true_probability", "ev_after_spread")
EV_VISIBILITY_ACCEPTED_FIELDS = {
    "fair_value": ("fair_value", "fair_value_available", "fair_value_null_reason"),
    "market_price": ("market_price", "market_price_available", "market_price_null_reason"),
    "true_probability": ("true_probability", "true_probability_available", "true_probability_null_reason"),
    "ev_after_spread": ("ev_after_spread", "ev_after_spread_available", "ev_after_spread_null_reason"),
}
EV_VALUE_ALIASES = {
    "fair_value": ("fair_value", "model_fair_value", "fair_value_yes", "fair_value_no", "yes_fair_value", "no_fair_value"),
    "market_price": ("market_price", "ask_price", "entry_price", "yes_ask", "no_ask"),
    "true_probability": (
        "true_probability",
        "model_probability",
        "model_probability_yes",
        "model_probability_no",
        "p_yes",
        "p_no",
        "model_p_yes",
        "model_p_no",
    ),
    "ev_after_spread": ("ev_after_spread", "executable_ev", "expected_value", "model_ev", "ev"),
}
RISK_LAYER_TRACE_REQUIREMENTS = {
    "candidate_identity": ("candidate_trace_id", "candidate_id", "signal_id", "parent_candidate_trace_id"),
    "market_key": ("market_key", "market_id", "condition_id", "source_market_id", "market_slug", "slug"),
    "lifecycle_phase": ("lifecycle_phase",),
    "risk_state": ("risk_state", "risk_decision", "risk_status", "risk_mode", "risk_reject_reason", "candidate_block_stage", "candidate_block_reason"),
}
SCHEMA_GENERATION_VERSION = "ev_field_coverage_post_fallback_condition_coverage_verification_v1"
EV_PRODUCER_CATEGORIES = (
    "decision_log",
    "market_snapshots",
    "execution_log",
    "risk_log",
    "system_health",
    "trade_journal",
)
TRACE_PRODUCER_ORDER = (
    "market_snapshots",
    "decision_log",
    "risk_log",
    "execution_log",
    "trade_journal",
)
TRACE_PRODUCER_RANK = {producer: index for index, producer in enumerate(TRACE_PRODUCER_ORDER)}
IDENTITY_CONFIDENCE_LEVELS = ("DIRECT", "STRONG", "WEAK", "PROXY", "UNKNOWN")
IDENTITY_CONFIDENCE_RANK = {level: index for index, level in enumerate(("UNKNOWN", "PROXY", "WEAK", "STRONG", "DIRECT"))}
IDENTITY_TRANSITIONS = tuple(
    f"{left}->{right}" for left, right in zip(TRACE_PRODUCER_ORDER, TRACE_PRODUCER_ORDER[1:])
)
DECISION_TO_RISK_BOUNDARY_CATEGORIES = (
    "BLOCKED_BEFORE_RISK",
    "RISK_NOT_REACHED",
    "RISK_REACHED_NOT_SERIALIZED",
    "RISK_PRODUCER_NOT_RESPONSIBLE",
    "NO_DECISION_EVIDENCE",
    "LEGACY_OR_UNKNOWN",
)
PRE_RISK_BLOCK_CAUSES = (
    "EV_NOT_VISIBLE",
    "PROBABILITY_NOT_VISIBLE",
    "FAIR_VALUE_NOT_VISIBLE",
    "ORDERBOOK_NOT_READY",
    "LIQUIDITY_NOT_READY",
    "SPREAD_NOT_EXECUTABLE",
    "CUTOFF_OR_TIME_BLOCK",
    "LIFECYCLE_PHASE_BLOCK",
    "MARKET_NOT_EVALUABLE",
    "IDENTITY_LINK_WEAK",
    "UNKNOWN_PRE_RISK_BLOCK",
)
MODEL_STATE_GAP_CATEGORIES = (
    "MODEL_NOT_ATTEMPTED",
    "MODEL_ATTEMPTED_OUTPUT_MISSING",
    "MODEL_OUTPUT_EXISTS_NOT_SERIALIZED",
    "BLOCKED_BEFORE_MODEL",
    "IDENTITY_TOO_WEAK_TO_LINK_MODEL_STATE",
    "MODEL_STATE_UNKNOWN",
)
MODEL_STATE_FIELDS = {
    "probability": "true_probability",
    "fair_value": "fair_value",
    "ev": "ev_after_spread",
}
MODEL_ATTEMPT_GATE_CAUSES = (
    "ORDERBOOK_GATE",
    "LIQUIDITY_GATE",
    "SPREAD_GATE",
    "TIME_CUTOFF_GATE",
    "LIFECYCLE_PHASE_GATE",
    "IDENTITY_CONFIDENCE_GATE",
    "MARKET_NOT_EVALUABLE_GATE",
    "PRODUCER_NOT_RESPONSIBLE",
    "MODEL_GATE_UNKNOWN",
)
MODEL_GATE_MICROSTRUCTURE_CAUSES = {"ORDERBOOK_GATE", "LIQUIDITY_GATE", "SPREAD_GATE"}
MODEL_GATE_TIMING_CAUSES = {"TIME_CUTOFF_GATE", "LIFECYCLE_PHASE_GATE", "MARKET_NOT_EVALUABLE_GATE"}
MODEL_GATE_IDENTITY_CAUSES = {"IDENTITY_CONFIDENCE_GATE"}
IDENTITY_UPGRADE_FIELDS = (
    "candidate_trace_id",
    "parent_candidate_trace_id",
    "market_key",
    "condition_id",
    "token_id",
    "side",
    "lifecycle_phase",
    "candidate_seen_ts",
    "producer_event_type",
    "trace_link_reason",
)
IDENTITY_CONFIDENCE_REQUIREMENTS = {
    "DIRECT": (
        "candidate_trace_id",
        "parent_candidate_trace_id",
        "market_key",
        "condition_id",
        "token_id",
        "side",
        "lifecycle_phase",
        "candidate_seen_ts",
        "producer_event_type",
        "trace_link_reason",
    ),
    "STRONG": (
        "market_key",
        "condition_id",
        "token_id",
        "side",
        "lifecycle_phase",
        "candidate_seen_ts",
        "producer_event_type",
        "trace_link_reason",
    ),
    "WEAK": (
        "market_key",
        "lifecycle_phase",
        "candidate_seen_ts",
    ),
    "PROXY": (
        "market_key",
        "candidate_seen_ts",
    ),
    "UNKNOWN": (),
}
POST_EMISSION_TRACE_FIELDS = (
    "candidate_trace_id",
    "parent_candidate_trace_id",
    "trace_link_reason",
    "market_key",
    "condition_id",
    "token_id",
    "side",
)
ALIAS_NORMALIZATION_FIELDS = ("condition_id", "token_id", "side", "market_key", "market_slug")
IDENTITY_FIELD_ALIASES = {
    "condition_id": ("conditionId",),
    "token_id": ("tokenId", "clob_token_id", "clobTokenId", "yes_token_id", "no_token_id"),
    "side": ("asset_side", "outcome", "best_side", "token_side"),
    "market_key": ("market_id", "source_market_id", "marketKey"),
    "market_slug": ("slug", "marketSlug"),
}
CONDITION_IDENTITY_ALIAS_FIELDS = (
    "condition_id",
    "conditionId",
    "conditionID",
    "condition",
    "market_condition_id",
    "conditionIdHex",
    "clob_condition_id",
    "question_id",
    "market_question_id",
    "event_condition_id",
)
EV_RELATED_PRE_RISK_CAUSES = {"EV_NOT_VISIBLE", "PROBABILITY_NOT_VISIBLE", "FAIR_VALUE_NOT_VISIBLE"}
MICROSTRUCTURE_RELATED_PRE_RISK_CAUSES = {"ORDERBOOK_NOT_READY", "LIQUIDITY_NOT_READY", "SPREAD_NOT_EXECUTABLE"}
TIMING_RELATED_PRE_RISK_CAUSES = {"CUTOFF_OR_TIME_BLOCK", "LIFECYCLE_PHASE_BLOCK", "MARKET_NOT_EVALUABLE"}
IDENTITY_RELATED_PRE_RISK_CAUSES = {"IDENTITY_LINK_WEAK"}
CANDIDATE_TRACE_ENVELOPE_FIELDS = (
    "candidate_trace_id",
    "market_key",
    "asset",
    "side",
    "condition_id",
    "token_id",
    "event_start_ts",
    "lifecycle_phase",
    "producer",
    "producer_event_type",
    "candidate_seen_ts",
    "evaluation_state",
    "probability_state",
    "fair_value_state",
    "ev_state",
    "liquidity_state",
    "spread_state",
    "risk_state",
    "execution_state",
    "identity_confidence",
    "parent_candidate_trace_id",
    "trace_link_reason",
)
PRODUCER_REQUIRED_FIELDS = {
    "market_snapshots": (
        "candidate_trace_id",
        "market_key",
        "asset",
        "side",
        "condition_id",
        "token_id",
        "event_start_ts",
        "lifecycle_phase",
        "producer",
        "producer_event_type",
        "candidate_seen_ts",
        "liquidity_state",
        "spread_state",
        "identity_confidence",
        "trace_link_reason",
    ),
    "decision_log": (
        "candidate_trace_id",
        "market_key",
        "asset",
        "side",
        "condition_id",
        "token_id",
        "lifecycle_phase",
        "producer",
        "producer_event_type",
        "candidate_seen_ts",
        "evaluation_state",
        "probability_state",
        "fair_value_state",
        "ev_state",
        "liquidity_state",
        "spread_state",
        "identity_confidence",
        "parent_candidate_trace_id",
        "trace_link_reason",
    ),
    "risk_log": (
        "candidate_trace_id",
        "market_key",
        "asset",
        "side",
        "condition_id",
        "lifecycle_phase",
        "producer",
        "producer_event_type",
        "candidate_seen_ts",
        "evaluation_state",
        "risk_state",
        "identity_confidence",
        "parent_candidate_trace_id",
        "trace_link_reason",
    ),
    "execution_log": (
        "candidate_trace_id",
        "market_key",
        "asset",
        "side",
        "condition_id",
        "token_id",
        "lifecycle_phase",
        "producer",
        "producer_event_type",
        "candidate_seen_ts",
        "execution_state",
        "risk_state",
        "identity_confidence",
        "parent_candidate_trace_id",
        "trace_link_reason",
    ),
    "trade_journal": (
        "candidate_trace_id",
        "market_key",
        "asset",
        "side",
        "condition_id",
        "token_id",
        "lifecycle_phase",
        "producer",
        "producer_event_type",
        "candidate_seen_ts",
        "execution_state",
        "identity_confidence",
        "parent_candidate_trace_id",
        "trace_link_reason",
    ),
}
UNCERTAIN_MISSING_REASONS = ("field_not_emitted", "legacy_missing_reason")
NORMALIZED_EV_NULL_REASONS = (
    "no_probability_model_output",
    "no_market_price",
    "no_orderbook",
    "empty_book",
    "spread_not_ready",
    "liquidity_not_ready",
    "time_unsafe",
    "candidate_blocked_before_ev",
    "candidate_blocked_after_ev",
    "field_not_emitted",
    "legacy_missing_reason",
)
NORMALIZED_EV_NULL_REASON_SET = set(NORMALIZED_EV_NULL_REASONS)
UNKNOWN_CONTEXT = "unknown"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str) and value.strip():
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
    return None


def _as_float_or_none(value: Any) -> float | None:
    if isinstance(value, bool) or value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _reason_text(value: Any) -> str:
    return _text(value).lower().replace("-", "_").replace(" ", "_")


def _normalize_reason_token(reason: str) -> str:
    reason = _reason_text(reason)
    if not reason:
        return ""
    if reason in NORMALIZED_EV_NULL_REASON_SET:
        return reason
    if "probability" in reason or "prob_model" in reason or "true_prob" in reason:
        return "no_probability_model_output"
    if "market_price" in reason or reason in {"no_price", "price_missing"}:
        return "no_market_price"
    if "empty_book" in reason or "empty_orderbook" in reason or "zero_depth" in reason:
        return "empty_book"
    if "orderbook" in reason or reason in {"no_book", "book_missing", "book_not_ready"}:
        return "no_orderbook"
    if "spread" in reason:
        return "spread_not_ready"
    if "liquidity" in reason or "depth" in reason:
        return "liquidity_not_ready"
    if "time" in reason or "cutoff" in reason or "unsafe" in reason:
        return "time_unsafe"
    if "before_ev" in reason or "pre_ev" in reason:
        return "candidate_blocked_before_ev"
    if "after_ev" in reason or "post_ev" in reason:
        return "candidate_blocked_after_ev"
    if "not_emitted" in reason or "not_emit" in reason:
        return "field_not_emitted"
    if "missing" in reason or "null" in reason or "unknown" in reason:
        return "legacy_missing_reason"
    return "legacy_missing_reason"


def _normalize_context_token(value: str) -> str:
    token = _reason_text(value)
    if not token or token in {"unknown", "none", "null", "na", "n/a"}:
        return UNKNOWN_CONTEXT
    return _normalize_reason_token(token)


def _stage_reason(payload: dict[str, Any], field: str) -> str:
    stage_values = [
        _first_value(payload, f"{field}_calculation_stage"),
        _first_value(payload, f"{field}_stage"),
        _first_value(payload, "ev_calculation_stage"),
        _first_value(payload, "probability_model_stage"),
        _first_value(payload, "candidate_block_stage"),
        _first_value(payload, "candidate_block_reason"),
        _first_value(payload, "block_stage"),
        _first_value(payload, "block_reason"),
    ]
    for value in stage_values:
        normalized = _normalize_reason_token(_text(value))
        if normalized:
            return normalized
    return ""


def _context_value(payload: dict[str, Any], *keys: str, normalize_reason: bool = False) -> str:
    value = _text(_first_value(payload, *keys))
    if normalize_reason:
        value = _normalize_context_token(value)
    return value or UNKNOWN_CONTEXT


def _market_readiness_context(payload: dict[str, Any]) -> str:
    return _context_value(
        payload,
        "market_readiness_state",
        "readiness_state",
        "readiness_transition_reason",
        "orderbook_readiness_reason",
        "orderbook_unavailable_reason",
        "liquidity_state",
        normalize_reason=True,
    )


def _orderbook_state_context(payload: dict[str, Any]) -> str:
    return _context_value(
        payload,
        "orderbook_state_classification",
        "orderbook_state",
        "orderbook_readiness_reason",
        "orderbook_unavailable_reason",
        "clob_error_category",
        normalize_reason=True,
    )


def _raw_context_value(payload: dict[str, Any], *keys: str) -> str:
    return _text(_first_value(payload, *keys))


def _field_status(payload: dict[str, Any], field: str) -> dict[str, Any]:
    value_aliases = EV_VALUE_ALIASES.get(field, (field,))
    value = _first_value(payload, *value_aliases)
    available_flag = _as_bool(_first_value(payload, f"{field}_available"))
    field_was_emitted = (
        field in payload
        or any(alias in payload for alias in value_aliases)
        or f"{field}_available" in payload
        or f"{field}_null_reason" in payload
    )
    value_available = _as_float_or_none(value) is not None
    available = available_flag is True or (available_flag is None and value_available)
    reason = _normalize_reason_token(_text(_first_value(payload, f"{field}_null_reason")))
    if not available and not reason:
        reason = _stage_reason(payload, field)
    if not available and not reason:
        reason = "legacy_missing_reason" if field_was_emitted else "field_not_emitted"
    return {
        "available": bool(available),
        "value_present": value_available,
        "emitted": field_was_emitted,
        "null_reason": "" if available else reason,
    }


def _candidate_identity_values(chain: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    for key in ("candidate_trace_id", "candidate_id", "signal_id", "continuity_chain_id"):
        value = _text(chain.get(key))
        if value:
            values.add(value)
    return values


def _payload_identity_values(payload: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    for key in ("candidate_trace_id", "candidate_id", "signal_id", "parent_candidate_trace_id", "opportunity_id", "replay_candidate_id"):
        value = _text(_first_value(payload, key))
        if value:
            values.add(value)
    return values


def _event_identity_matches_with_trace_aliases(chain: dict[str, Any], event: dict[str, Any], payload: dict[str, Any]) -> bool:
    if _event_identity_matches(chain, event, payload):
        return True
    chain_values = _candidate_identity_values(chain)
    payload_values = _payload_identity_values(payload)
    return bool(chain_values and payload_values and chain_values.intersection(payload_values))


def _market_values_from_chain(chain: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    for key in ("market_key", "market_id", "condition_id", "market_slug", "slug"):
        value = _text(chain.get(key))
        if value:
            values.add(value)
    return values


def _market_values_from_payload(payload: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    for key in ("market_key", "market_id", "condition_id", "source_market_id", "market_slug", "slug"):
        value = _text(_first_value(payload, key))
        if value:
            values.add(value)
    return values


def _event_market_matches_with_aliases(chain: dict[str, Any], event: dict[str, Any], payload: dict[str, Any]) -> bool:
    if _event_market_matches(chain, event, payload):
        return True
    chain_values = _market_values_from_chain(chain)
    payload_values = _market_values_from_payload(payload)
    if chain_values and payload_values and chain_values.intersection(payload_values):
        return True
    return False


def _matching_window_events(chain: dict[str, Any], events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for event in events:
        if not _event_in_chain_window(chain, event):
            continue
        payload = _payload(event)
        identity_match = _event_identity_matches_with_trace_aliases(chain, event, payload)
        market_match = _event_market_matches_with_aliases(chain, event, payload)
        if not identity_match and not market_match:
            continue
        phase, phase_inference = _phase(payload)
        timestamp = _text(event.get("timestamp_utc") or _first_value(payload, "timestamp_utc"))
        fields = {field: _field_status(payload, field) for field in EV_COMPONENT_FIELDS}
        any_visible = any(item["available"] for item in fields.values())
        matches.append({
            "timestamp_utc": timestamp,
            "timestamp": _parse_timestamp(timestamp),
            "event_category": _text(event.get("_category")),
            "event_type": _text(event.get("event_type")),
            "candidate_trace_id": _raw_context_value(payload, "candidate_trace_id", "trace_id"),
            "candidate_id": _text(_first_value(payload, "candidate_id")),
            "signal_id": _text(_first_value(payload, "signal_id")),
            "market_key": _raw_context_value(payload, "market_key", "market_id", "condition_id", "source_market_id", "market_slug", "slug"),
            "market_id": _text(_first_value(payload, "market_id", "condition_id", "market_key", "source_market_id", "slug")),
            "asset": _raw_context_value(payload, "asset", "symbol", "base_asset"),
            "side": _raw_context_value(payload, "side", "outcome", "token_side", "direction"),
            "condition_id": _raw_context_value(payload, "condition_id"),
            "token_id": _raw_context_value(payload, "token_id", "clob_token_id", "yes_token_id", "no_token_id"),
            "event_start_ts": _raw_context_value(payload, "event_start_ts", "market_start_ts", "market_open_ts", "start_ts", "start_time"),
            "parent_candidate_trace_id": _raw_context_value(payload, "parent_candidate_trace_id", "parent_candidate_id", "parent_signal_id"),
            "evaluation_state": _raw_context_value(payload, "evaluation_state", "decision", "candidate_block_stage", "candidate_block_reason", "block_stage", "block_reason"),
            "spread_state": _raw_context_value(payload, "spread_state", "spread_quality", "spread_readiness", "spread_bps", "spread"),
            "risk_state": _raw_context_value(payload, "risk_state", "risk_decision", "risk_status", "risk_mode", "risk_reject_reason"),
            "execution_state": _raw_context_value(payload, "execution_state", "execution_status", "order_state", "fill_state", "execution_result"),
            "match_inference": "direct_identity" if identity_match else "market_window_proxy",
            "lifecycle_phase": phase,
            "lifecycle_phase_inference": phase_inference,
            "candidate_block_stage": _context_value(payload, "candidate_block_stage", "block_stage", normalize_reason=True),
            "candidate_block_reason": _context_value(payload, "candidate_block_reason", "block_reason", normalize_reason=True),
            "market_readiness_state": _market_readiness_context(payload),
            "orderbook_state_classification": _orderbook_state_context(payload),
            "model_activation_state": _raw_context_value(payload, "model_activation_state"),
            "model_activation_block_group": _raw_context_value(payload, "model_activation_block_group"),
            "model_activation_block_reason": _raw_context_value(payload, "model_activation_block_reason"),
            "fields": fields,
            "any_ev_component_visible": any_visible,
        })
    return sorted(matches, key=lambda item: item["timestamp_utc"])


def _duration_ms(events: list[dict[str, Any]]) -> float:
    timestamps = [event["timestamp"] for event in events if event.get("timestamp") is not None]
    if len(timestamps) < 2:
        return 0.0
    return max(0.0, (timestamps[-1] - timestamps[0]).total_seconds() * 1000.0)


def _first_dropout_reason(events: list[dict[str, Any]], field: str) -> tuple[str, float | None]:
    seen_available = False
    first_timestamp = events[0]["timestamp"] if events else None
    for event in events:
        status = event["fields"][field]
        if status["available"]:
            seen_available = True
            continue
        if seen_available:
            timestamp = event.get("timestamp")
            dropout_ms = None
            if first_timestamp is not None and timestamp is not None:
                dropout_ms = max(0.0, (timestamp - first_timestamp).total_seconds() * 1000.0)
            return status["null_reason"] or "field_dropped_without_reason", dropout_ms
    return "", None


def _never_visible_reason(events: list[dict[str, Any]], field: str) -> str:
    reasons = Counter(
        event["fields"][field]["null_reason"]
        for event in events
        if not event["fields"][field]["available"] and event["fields"][field]["null_reason"]
    )
    return reasons.most_common(1)[0][0] if reasons else "field_never_visible"


def _compact_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp_utc": event["timestamp_utc"],
        "event_category": event["event_category"],
        "event_type": event["event_type"],
        "match_inference": event["match_inference"],
        "lifecycle_phase": event["lifecycle_phase"],
        "candidate_block_stage": event["candidate_block_stage"],
        "candidate_block_reason": event["candidate_block_reason"],
        "market_readiness_state": event["market_readiness_state"],
        "orderbook_state_classification": event["orderbook_state_classification"],
        "model_activation_state": event.get("model_activation_state", ""),
        "model_activation_block_group": event.get("model_activation_block_group", ""),
        "model_activation_block_reason": event.get("model_activation_block_reason", ""),
        "any_ev_component_visible": event["any_ev_component_visible"],
        "fields": {
            field: {
                "available": event["fields"][field]["available"],
                "emitted": event["fields"][field].get("emitted", False),
                "null_reason": event["fields"][field]["null_reason"],
            }
            for field in EV_COMPONENT_FIELDS
        },
    }


def _visible_fields(event: dict[str, Any]) -> list[str]:
    return [field for field in EV_COMPONENT_FIELDS if event["fields"][field]["available"]]


def _event_ev_attempted(event: dict[str, Any]) -> bool:
    for field in EV_COMPONENT_FIELDS:
        status = event["fields"][field]
        if status["available"]:
            return True
        reason = status.get("null_reason") or ""
        if status.get("emitted") and reason not in {"field_not_emitted", "legacy_missing_reason", "candidate_blocked_before_ev"}:
            return True
    if event.get("candidate_block_stage") == "candidate_blocked_after_ev":
        return True
    if event.get("candidate_block_reason") == "candidate_blocked_after_ev":
        return True
    return False


def _event_blocked_before_ev(event: dict[str, Any]) -> bool:
    if event.get("candidate_block_stage") == "candidate_blocked_before_ev":
        return True
    if event.get("candidate_block_reason") == "candidate_blocked_before_ev":
        return True
    return any(
        event["fields"][field].get("null_reason") == "candidate_blocked_before_ev"
        for field in EV_COMPONENT_FIELDS
    )


def _event_null_reason_counts(event: dict[str, Any]) -> Counter[str]:
    reasons: Counter[str] = Counter()
    for field in EV_COMPONENT_FIELDS:
        reason = event["fields"][field]["null_reason"]
        if reason:
            reasons[reason] += 1
    return reasons


def _dominant_event_null_reason(event: dict[str, Any]) -> str:
    reasons = _event_null_reason_counts(event)
    return reasons.most_common(1)[0][0] if reasons else "ev_visible"


def _missing_semantic(event: dict[str, Any]) -> str:
    if event["any_ev_component_visible"]:
        return "ev_visible"
    reasons = set(_event_null_reason_counts(event))
    category = str(event.get("event_category") or "unknown")
    if not reasons:
        return "field_missing"
    if "legacy_missing_reason" in reasons:
        return "uncertain_legacy_missing"
    if "field_not_emitted" in reasons:
        if category in {"execution_log", "risk_log", "system_health", "trade_journal"}:
            return "producer_not_responsible_or_not_ev_owner"
        return "field_missing"
    if "no_probability_model_output" in reasons:
        return "field_never_evaluated"
    if "candidate_blocked_before_ev" in reasons:
        return "field_intentionally_absent_pre_ev"
    if "candidate_blocked_after_ev" in reasons:
        return "field_intentionally_absent_post_ev"
    if reasons & {"no_market_price", "no_orderbook", "empty_book", "spread_not_ready", "liquidity_not_ready", "time_unsafe"}:
        return "lifecycle_or_microstructure_absence"
    return "field_missing"


def _phase_coverage(events: list[dict[str, Any]]) -> dict[str, Any]:
    coverage: dict[str, dict[str, int]] = {}
    for event in events:
        phase = event.get("lifecycle_phase") or UNKNOWN_CONTEXT
        if phase not in coverage:
            coverage[phase] = {"event_count": 0, "ev_visible_event_count": 0}
        coverage[phase]["event_count"] += 1
        if event["any_ev_component_visible"]:
            coverage[phase]["ev_visible_event_count"] += 1
    return {
        phase: {
            **stats,
            "ev_visibility_rate": round(stats["ev_visible_event_count"] / stats["event_count"], 4)
            if stats["event_count"]
            else 0.0,
        }
        for phase, stats in sorted(coverage.items())
    }


def _trace_quality(
    *,
    event_count: int,
    visible_event_count: int,
    transition_failures: int,
    lifecycle_interrupted: bool,
) -> str:
    if event_count <= 0:
        return "NO_TRACE_EVENTS"
    if visible_event_count <= 0:
        return "EV_TRACE_BLIND"
    if lifecycle_interrupted and visible_event_count < event_count:
        return "EV_TRACE_INTERRUPTED"
    if transition_failures:
        return "EV_TRACE_BREAK"
    if visible_event_count == event_count:
        return "EV_TRACE_CONTINUOUS"
    return "EV_TRACE_PARTIAL"


def _handoff_quality(transition_count: int, failure_count: int) -> str:
    if transition_count <= 0:
        return "NO_HANDOFF_EVIDENCE"
    if failure_count <= 0:
        return "GOOD_PRODUCER_HANDOFF"
    if failure_count == transition_count:
        return "BROKEN_PRODUCER_HANDOFF"
    return "PARTIAL_PRODUCER_HANDOFF"


def _identity_counter_dict(counter: Counter[str]) -> dict[str, int]:
    return {level: int(counter.get(level, 0)) for level in IDENTITY_CONFIDENCE_LEVELS}


def _identity_rate(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def _identity_link_quality(counts: Counter[str], total: int) -> str:
    if total <= 0:
        return "NO_IDENTITY_EVIDENCE"
    strong_or_direct = counts.get("DIRECT", 0) + counts.get("STRONG", 0)
    weak_proxy_unknown = counts.get("WEAK", 0) + counts.get("PROXY", 0) + counts.get("UNKNOWN", 0)
    if counts.get("DIRECT", 0) == total:
        return "DIRECT_IDENTITY"
    if strong_or_direct == total:
        return "STRONG_OR_DIRECT_IDENTITY"
    if counts.get("PROXY", 0) / total >= 0.5:
        return "PROXY_DEPENDENT"
    if weak_proxy_unknown / total >= 0.5:
        return "IDENTITY_GAPPED"
    return "MIXED_IDENTITY"


def _event_identity_confidence(event: dict[str, Any]) -> str:
    inference = str(event.get("match_inference") or "")
    if inference == "direct_identity":
        return "DIRECT" if event.get("candidate_id") or event.get("signal_id") else "STRONG"
    if inference == "market_window_proxy":
        return "PROXY"
    return "UNKNOWN"


def _strongest_identity(classes: list[str]) -> str:
    if not classes:
        return "UNKNOWN"
    return max(classes, key=lambda item: IDENTITY_CONFIDENCE_RANK.get(item, 0))


def _weakest_identity(classes: list[str]) -> str:
    if not classes:
        return "UNKNOWN"
    return min(classes, key=lambda item: IDENTITY_CONFIDENCE_RANK.get(item, 0))


def _producer_identity_confidence(
    window_events: list[dict[str, Any]],
    candidate_trace_confidence: str,
    identity_fragmentation_detected: bool,
) -> dict[str, Any]:
    events_by_producer: dict[str, list[dict[str, Any]]] = {}
    for event in window_events:
        producer = str(event.get("event_category") or "unknown")
        events_by_producer.setdefault(producer, []).append(event)

    tables: dict[str, Any] = {}
    for producer in sorted(set(TRACE_PRODUCER_ORDER) | set(events_by_producer)):
        events = events_by_producer.get(producer, [])
        counts: Counter[str] = Counter()
        confidence = candidate_trace_confidence if events and candidate_trace_confidence in IDENTITY_CONFIDENCE_RANK else "UNKNOWN"
        counts[confidence] += 1
        event_confidences = [_event_identity_confidence(event) for event in events]
        direct_events = sum(1 for item in event_confidences if item == "DIRECT")
        proxy_events = sum(1 for item in event_confidences if item == "PROXY")
        gap_count = counts.get("WEAK", 0) + counts.get("PROXY", 0) + counts.get("UNKNOWN", 0)
        total = sum(counts.values())
        tables[producer] = {
            **_identity_counter_dict(counts),
            "total_candidates": total,
            "direct_identity_event_count": direct_events,
            "proxy_match_event_count": proxy_events,
            "total_identity_events": len(event_confidences),
            "identity_gap_count": gap_count,
            "proxy_dependency_count": counts.get("PROXY", 0),
            "direct_identity_absence_count": int(direct_events <= 0),
            "identity_fragmentation_count": int(identity_fragmentation_detected),
            "direct_identity_rate": _identity_rate(counts.get("DIRECT", 0), total),
            "proxy_dependency_rate": _identity_rate(counts.get("PROXY", 0), total),
            "strong_or_direct_rate": _identity_rate(counts.get("DIRECT", 0) + counts.get("STRONG", 0), total),
            "identity_fragmentation_share": _identity_rate(int(identity_fragmentation_detected), total),
            "strongest_event_identity": _strongest_identity(event_confidences),
            "identity_link_quality": _identity_link_quality(counts, total),
        }
    return tables


def _producer_event_identity_classes(window_events: list[dict[str, Any]]) -> dict[str, str]:
    by_producer: dict[str, list[str]] = {}
    for event in window_events:
        producer = str(event.get("event_category") or "unknown")
        by_producer.setdefault(producer, []).append(_event_identity_confidence(event))
    return {producer: _strongest_identity(classes) for producer, classes in by_producer.items()}


def _transition_identity_gap_tables(window_events: list[dict[str, Any]]) -> dict[str, Any]:
    producer_classes = _producer_event_identity_classes(window_events)
    tables: dict[str, Any] = {}
    for left, right in zip(TRACE_PRODUCER_ORDER, TRACE_PRODUCER_ORDER[1:]):
        left_class = producer_classes.get(left, "UNKNOWN")
        right_class = producer_classes.get(right, "UNKNOWN")
        transition_class = _weakest_identity([left_class, right_class])
        counts: Counter[str] = Counter({transition_class: 1})
        total = sum(counts.values())
        gap_count = counts.get("WEAK", 0) + counts.get("PROXY", 0) + counts.get("UNKNOWN", 0)
        tables[f"{left}->{right}"] = {
            **_identity_counter_dict(counts),
            "total_candidates": total,
            "from_producer": left,
            "to_producer": right,
            "from_identity_confidence": left_class,
            "to_identity_confidence": right_class,
            "strongest_available_identity": _strongest_identity([left_class, right_class]),
            "transition_identity_confidence": transition_class,
            "identity_gap_count": gap_count,
            "proxy_dependency_count": int(left_class == "PROXY" or right_class == "PROXY" or transition_class == "PROXY"),
            "direct_identity_absence_count": int(left_class != "DIRECT" or right_class != "DIRECT"),
            "direct_identity_rate": _identity_rate(counts.get("DIRECT", 0), total),
            "proxy_dependency_rate": _identity_rate(counts.get("PROXY", 0), total),
            "strong_or_direct_rate": _identity_rate(counts.get("DIRECT", 0) + counts.get("STRONG", 0), total),
            "identity_fragmentation_share": _identity_rate(gap_count, total),
            "identity_link_quality": _identity_link_quality(counts, total),
        }
    return tables


def _merge_identity_table(target: dict[str, Counter[str]], source: Any) -> None:
    if not isinstance(source, dict):
        return
    raw_fields = set(IDENTITY_CONFIDENCE_LEVELS) | {
        "total_candidates",
        "direct_identity_event_count",
        "proxy_match_event_count",
        "total_identity_events",
        "identity_gap_count",
        "proxy_dependency_count",
        "direct_identity_absence_count",
        "identity_fragmentation_count",
    }
    for key, values in source.items():
        if not isinstance(values, dict):
            continue
        bucket = target.setdefault(str(key), Counter())
        for field in raw_fields:
            bucket[field] += int(values.get(field) or 0)


def _identity_table_dict(table: dict[str, Counter[str]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, counts in sorted(table.items()):
        total = int(counts.get("total_candidates", 0))
        class_counts = Counter({level: int(counts.get(level, 0)) for level in IDENTITY_CONFIDENCE_LEVELS})
        output[key] = {
            **_identity_counter_dict(class_counts),
            "total_candidates": total,
            "direct_identity_event_count": int(counts.get("direct_identity_event_count", 0)),
            "proxy_match_event_count": int(counts.get("proxy_match_event_count", 0)),
            "total_identity_events": int(counts.get("total_identity_events", 0)),
            "identity_gap_count": int(counts.get("identity_gap_count", 0)),
            "proxy_dependency_count": int(counts.get("proxy_dependency_count", 0)),
            "direct_identity_absence_count": int(counts.get("direct_identity_absence_count", 0)),
            "identity_fragmentation_count": int(counts.get("identity_fragmentation_count", 0)),
            "direct_identity_rate": _identity_rate(class_counts.get("DIRECT", 0), total),
            "proxy_dependency_rate": _identity_rate(int(counts.get("proxy_dependency_count", 0)), total),
            "strong_or_direct_rate": _identity_rate(class_counts.get("DIRECT", 0) + class_counts.get("STRONG", 0), total),
            "identity_fragmentation_share": _identity_rate(int(counts.get("identity_fragmentation_count", 0)), total),
            "identity_gap_share": _identity_rate(int(counts.get("identity_gap_count", 0)), total),
            "identity_link_quality": _identity_link_quality(class_counts, total),
        }
    return output


def _transition_identity_table_dict(table: dict[str, Counter[str]]) -> dict[str, Any]:
    output = _identity_table_dict(table)
    for transition, stats in output.items():
        if "->" in transition:
            left, right = transition.split("->", 1)
            stats["from_producer"] = left
            stats["to_producer"] = right
        class_counts = Counter({level: int(stats.get(level, 0)) for level in IDENTITY_CONFIDENCE_LEVELS})
        stats["strongest_available_identity"] = _strongest_identity(
            [level for level, count in class_counts.items() if count > 0]
        )
    return output


def _dominant_identity_table_item(table: dict[str, Any], *, metric: str, lowest: bool = False) -> dict[str, Any]:
    if not table:
        return {"key": "none", "value": None}
    def sort_key(item: tuple[str, dict[str, Any]]) -> tuple[float, int, str]:
        key, stats = item
        return (float(stats.get(metric) or 0.0), int(stats.get("identity_gap_count") or 0), key)
    if lowest:
        key, stats = sorted(
            table.items(),
            key=lambda item: (float(item[1].get(metric) or 0.0), -int(item[1].get("identity_gap_count") or 0), item[0]),
        )[0]
    else:
        key, stats = sorted(table.items(), key=sort_key, reverse=True)[0]
    return {"key": key, **stats}


def _candidate_trace_envelope_spec() -> dict[str, Any]:
    return {
        "version": "candidate_trace_envelope_v1",
        "scope": "offline_replay_observability_spec_only",
        "fields": list(CANDIDATE_TRACE_ENVELOPE_FIELDS),
        "field_meanings": {
            "candidate_trace_id": "stable replay identity for one candidate across producer handoffs",
            "market_key": "stable market/window key used when condition or token identity is partial",
            "asset": "BTC/ETH or other underlying asset label",
            "side": "YES/NO or equivalent token-side intent",
            "condition_id": "Polymarket condition identifier when known",
            "token_id": "specific outcome token identifier when known",
            "event_start_ts": "market window start timestamp",
            "lifecycle_phase": "OPENING_SCAN through CLOSED_OR_UNSAFE",
            "producer": "source event category",
            "producer_event_type": "source event type within the producer",
            "candidate_seen_ts": "timestamp when producer observed or handled candidate",
            "evaluation_state": "candidate evaluation/block/decision state",
            "probability_state": "probability model visibility or null state",
            "fair_value_state": "fair-value visibility or null state",
            "ev_state": "EV visibility or null state",
            "liquidity_state": "liquidity/readiness state known to producer",
            "spread_state": "spread/readiness state known to producer",
            "risk_state": "risk approval/reject/block state",
            "execution_state": "order/fill/journal state, if producer owns execution evidence",
            "identity_confidence": "DIRECT/STRONG/WEAK/PROXY/UNKNOWN replay linkage class",
            "parent_candidate_trace_id": "previous trace id when producer creates derived or child event",
            "trace_link_reason": "why this event links to the trace; direct identity, parent link, or proxy reason",
        },
        "guardrail": "spec/report only; does not emit runtime fields, reconstruct EV values, infer execution, or authorize trading decisions",
    }


def _field_state_present(event: dict[str, Any], field: str) -> bool:
    status = event.get("fields", {}).get(field)
    if not isinstance(status, dict):
        return False
    return bool(status.get("available") or status.get("emitted") or status.get("null_reason"))


def _envelope_field_present(event: dict[str, Any], field: str) -> bool:
    if field == "candidate_trace_id":
        return bool(event.get("candidate_trace_id") or event.get("candidate_id") or event.get("signal_id"))
    if field == "market_key":
        return bool(event.get("market_key") or event.get("market_id"))
    if field == "producer":
        return bool(event.get("event_category"))
    if field == "producer_event_type":
        return bool(event.get("event_type"))
    if field == "candidate_seen_ts":
        return bool(event.get("timestamp_utc"))
    if field == "lifecycle_phase":
        return bool(event.get("lifecycle_phase") and event.get("lifecycle_phase") != UNKNOWN_CONTEXT)
    if field == "probability_state":
        return _field_state_present(event, "true_probability")
    if field == "fair_value_state":
        return _field_state_present(event, "fair_value")
    if field == "ev_state":
        return _field_state_present(event, "ev_after_spread")
    if field == "liquidity_state":
        return bool(event.get("market_readiness_state") and event.get("market_readiness_state") != UNKNOWN_CONTEXT)
    if field == "identity_confidence":
        return _event_identity_confidence(event) != "UNKNOWN"
    if field == "trace_link_reason":
        return bool(event.get("match_inference"))
    value = event.get(field)
    return bool(value and str(value).strip() and str(value).strip().lower() not in {"unknown", "none", "null", "na", "n/a"})


def _candidate_trace_envelope_coverage(window_events: list[dict[str, Any]]) -> dict[str, Any]:
    events_by_producer: dict[str, list[dict[str, Any]]] = {}
    for event in window_events:
        producer = str(event.get("event_category") or "unknown")
        events_by_producer.setdefault(producer, []).append(event)

    by_producer: dict[str, Any] = {}
    total_required = 0
    total_present = 0
    for producer in TRACE_PRODUCER_ORDER:
        required_fields = PRODUCER_REQUIRED_FIELDS[producer]
        events = events_by_producer.get(producer, [])
        missing_fields = []
        present_fields = []
        for field in required_fields:
            present = any(_envelope_field_present(event, field) for event in events)
            if present:
                present_fields.append(field)
            else:
                missing_fields.append(field)
        required_count = len(required_fields)
        present_count = len(present_fields)
        total_required += required_count
        total_present += present_count
        by_producer[producer] = {
            "required_fields": list(required_fields),
            "present_fields": present_fields,
            "missing_fields": missing_fields,
            "required_field_count": required_count,
            "present_field_count": present_count,
            "missing_field_count": len(missing_fields),
            "envelope_readiness_score": round(present_count / required_count, 4) if required_count else 0.0,
            "event_count": len(events),
        }
    weakest = min(
        by_producer.items(),
        key=lambda item: (item[1]["envelope_readiness_score"], -item[1]["missing_field_count"], item[0]),
    )[0] if by_producer else "none"
    return {
        "by_producer": by_producer,
        "envelope_readiness_score": round(total_present / total_required, 4) if total_required else 0.0,
        "weakest_envelope_producer": weakest,
    }


def _identity_upgrade_field_present(window_events: list[dict[str, Any]], field: str) -> bool:
    if field == "market_key":
        return any(event.get("market_id") or event.get("condition_id") for event in window_events)
    if field == "candidate_seen_ts":
        return any(event.get("timestamp_utc") for event in window_events)
    if field == "producer_event_type":
        return any(event.get("event_type") for event in window_events)
    if field == "trace_link_reason":
        return any(event.get("match_inference") for event in window_events)
    return any(
        bool(_text(event.get(field)) and _text(event.get(field)) != UNKNOWN_CONTEXT)
        for event in window_events
    )


def _candidate_identity_upgrade_requirements(
    window_events: list[dict[str, Any]],
    lifecycle_trace: dict[str, Any],
) -> dict[str, Any]:
    present_fields = [
        field for field in IDENTITY_UPGRADE_FIELDS
        if _identity_upgrade_field_present(window_events, field)
    ]
    present = set(present_fields)
    missing_direct = [
        field for field in IDENTITY_CONFIDENCE_REQUIREMENTS["DIRECT"]
        if field not in present
    ]
    missing_strong = [
        field for field in IDENTITY_CONFIDENCE_REQUIREMENTS["STRONG"]
        if field not in present
    ]
    actual_confidence = str(lifecycle_trace.get("candidate_trace_confidence") or "UNKNOWN")
    if actual_confidence == "DIRECT" and not missing_direct:
        path = "CONFIRMED_DIRECT"
    elif actual_confidence == "DIRECT":
        path = "ACTUAL_DIRECT_CANONICAL_FIELDS_MISSING"
    elif actual_confidence == "STRONG" and not missing_strong:
        path = "CONFIRMED_STRONG"
    elif actual_confidence == "STRONG":
        path = "ACTUAL_STRONG_CANONICAL_FIELDS_MISSING"
    elif not missing_direct:
        path = "HYPOTHETICAL_DIRECT_READY_NOT_CONFIRMED"
    elif not missing_strong:
        path = "HYPOTHETICAL_STRONG_READY_NOT_CONFIRMED"
    elif actual_confidence in {"PROXY", "UNKNOWN"}:
        path = "PROXY_OR_UNKNOWN_NEEDS_IDENTITY_FIELDS"
    else:
        path = "WEAK_NEEDS_IDENTITY_FIELDS"
    return {
        "identity_confidence_requirements": {
            level: list(fields)
            for level, fields in IDENTITY_CONFIDENCE_REQUIREMENTS.items()
        },
        "identity_upgrade_required_fields": list(IDENTITY_UPGRADE_FIELDS),
        "identity_upgrade_present_fields": present_fields,
        "missing_fields_preventing_direct_identity": missing_direct,
        "missing_fields_preventing_strong_identity": missing_strong,
        "candidate_identity_upgrade_path": path,
        "hypothetical_identity_upgrade_note": "hypothetical only; actual candidate_trace_confidence is not changed",
    }


def _post_emission_field_present(payload: dict[str, Any], event: dict[str, Any], field: str) -> bool:
    if field == "candidate_seen_ts":
        return bool(_text(_first_value(payload, "candidate_seen_ts")) or _text(event.get("timestamp_utc")))
    if field == "producer_event_type":
        return bool(_text(_first_value(payload, "producer_event_type")) or _text(event.get("event_type")))
    return bool(_text(_first_value(payload, field)))


def _presence_by_producer(
    producer_totals: Counter[str],
    producer_present: dict[str, Counter[str]],
    field: str,
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for producer in sorted(set(TRACE_PRODUCER_ORDER) | set(producer_totals)):
        total = int(producer_totals.get(producer, 0))
        present = int(producer_present.get(producer, Counter()).get(field, 0))
        output[producer] = {
            "present_count": present,
            "missing_count": max(0, total - present),
            "total_events": total,
            "presence_rate": round(present / total, 4) if total else 0.0,
        }
    return output


def _alias_source_values(payload: dict[str, Any], field: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for alias in IDENTITY_FIELD_ALIASES.get(field, ()):
        value = _text(_first_value(payload, alias))
        if value:
            values[alias] = value
    return values


def _identity_field_origin_after_normalization(payload: dict[str, Any], field: str) -> str:
    canonical_present = bool(_text(_first_value(payload, field)))
    if canonical_present and _alias_source_values(payload, field):
        return "normalized_alias"
    if canonical_present:
        return "original_canonical"
    return "missing"


def _nested_counter_dict(table: dict[str, Counter[str]]) -> dict[str, dict[str, int]]:
    return {
        str(key): {str(inner_key): int(count) for inner_key, count in counts.items() if count}
        for key, counts in sorted(table.items())
    }


def _candidate_trace_alias_normalization_verification(events: list[dict[str, Any]]) -> dict[str, Any]:
    producer_totals: Counter[str] = Counter()
    canonical_present_by_producer: dict[str, Counter[str]] = {}
    alias_dependency_by_producer: dict[str, Counter[str]] = {}
    field_origin_counts: dict[str, Counter[str]] = {field: Counter() for field in ALIAS_NORMALIZATION_FIELDS}
    alias_normalized_counts: Counter[str] = Counter()
    alias_source_counts: Counter[str] = Counter()
    canonical_presence: dict[str, Counter[str]] = {field: Counter() for field in ALIAS_NORMALIZATION_FIELDS}
    readiness_counts: Counter[str] = Counter()
    missing_direct: Counter[str] = Counter()

    for event in events:
        payload = _payload(event)
        if not _post_emission_field_present(payload, event, "candidate_trace_id"):
            continue
        producer = _text(event.get("_category")) or "unknown"
        producer_totals[producer] += 1
        readiness_counts["trace_events_with_candidate_trace_id"] += 1
        present_bucket = canonical_present_by_producer.setdefault(producer, Counter())
        alias_bucket = alias_dependency_by_producer.setdefault(producer, Counter())

        for field in ALIAS_NORMALIZATION_FIELDS:
            origin = _identity_field_origin_after_normalization(payload, field)
            field_origin_counts[field][origin] += 1
            canonical_presence[field]["total_events"] += 1
            if origin == "missing":
                canonical_presence[field]["missing_count"] += 1
            else:
                canonical_presence[field]["present_count"] += 1
                present_bucket[field] += 1
                if origin == "normalized_alias":
                    alias_normalized_counts[field] += 1
                    alias_bucket[field] += 1
            for alias in _alias_source_values(payload, field):
                alias_source_counts[alias] += 1

        for field in ("condition_id", "token_id", "side"):
            if _post_emission_field_present(payload, event, field):
                readiness_counts[f"trace_events_with_{field}"] += 1

        missing_direct_fields = [
            field for field in IDENTITY_CONFIDENCE_REQUIREMENTS["DIRECT"]
            if not _post_emission_field_present(payload, event, field)
        ]
        missing_strong_fields = [
            field for field in IDENTITY_CONFIDENCE_REQUIREMENTS["STRONG"]
            if not _post_emission_field_present(payload, event, field)
        ]
        if not missing_direct_fields:
            readiness_counts["trace_events_direct_ready"] += 1
        if not missing_strong_fields:
            readiness_counts["trace_events_strong_ready"] += 1
        for field in missing_direct_fields:
            missing_direct[field] += 1

    trace_events = int(readiness_counts.get("trace_events_with_candidate_trace_id", 0))
    canonical_presence_output: dict[str, Any] = {}
    for field in ALIAS_NORMALIZATION_FIELDS:
        counts = canonical_presence[field]
        present = int(counts.get("present_count", 0))
        total = int(counts.get("total_events", 0))
        canonical_presence_output[field] = {
            "present_count": present,
            "missing_count": int(counts.get("missing_count", 0)),
            "total_events": total,
            "presence_rate": round(present / total, 4) if total else 0.0,
            "origin_counts": {
                "original_canonical": int(field_origin_counts[field].get("original_canonical", 0)),
                "normalized_alias": int(field_origin_counts[field].get("normalized_alias", 0)),
                "missing": int(field_origin_counts[field].get("missing", 0)),
            },
        }

    producer_canonical_presence: dict[str, Any] = {}
    for producer in sorted(set(TRACE_PRODUCER_ORDER) | set(producer_totals)):
        total = int(producer_totals.get(producer, 0))
        producer_canonical_presence[producer] = {
            field: {
                "present_count": int(canonical_present_by_producer.get(producer, Counter()).get(field, 0)),
                "missing_count": max(0, total - int(canonical_present_by_producer.get(producer, Counter()).get(field, 0))),
                "total_events": total,
                "presence_rate": round(
                    int(canonical_present_by_producer.get(producer, Counter()).get(field, 0)) / total,
                    4,
                ) if total else 0.0,
            }
            for field in ALIAS_NORMALIZATION_FIELDS
        }

    status = "POST_NORMALIZATION_DATA_FOUND" if trace_events else "POST_NORMALIZATION_DATA_NOT_FOUND"
    return {
        "post_normalization_data_status": status,
        "post_normalization_data_exists": bool(trace_events),
        "events_scanned": len(events),
        "trace_events_scanned": trace_events,
        "alias_normalized_field_counts": dict(alias_normalized_counts.most_common()) if trace_events else {},
        "alias_source_field_counts": dict(alias_source_counts.most_common()) if trace_events else {},
        "canonical_identity_field_presence_after_normalization": canonical_presence_output if trace_events else {},
        "producer_alias_dependency_counts": _nested_counter_dict(alias_dependency_by_producer) if trace_events else {},
        "producer_canonical_presence_counts": producer_canonical_presence if trace_events else {},
        "trace_events_with_candidate_trace_id": trace_events,
        "trace_events_with_condition_id": int(readiness_counts.get("trace_events_with_condition_id", 0)) if trace_events else 0,
        "trace_events_with_token_id": int(readiness_counts.get("trace_events_with_token_id", 0)) if trace_events else 0,
        "trace_events_with_side": int(readiness_counts.get("trace_events_with_side", 0)) if trace_events else 0,
        "trace_events_direct_ready": int(readiness_counts.get("trace_events_direct_ready", 0)) if trace_events else 0,
        "trace_events_strong_ready": int(readiness_counts.get("trace_events_strong_ready", 0)) if trace_events else 0,
        "fields_still_missing_after_alias_normalization": dict(missing_direct.most_common()) if trace_events else {},
        "interpretation": (
            "fresh post-normalization trace events found; alias-derived canonical fields are counted separately from original canonical fields"
            if trace_events
            else "POST_NORMALIZATION_DATA_NOT_FOUND; no candidate_trace_id-bearing JSONL events were found in the selected replay data"
        ),
        "guardrail": "offline alias coverage verification only; does not claim identity improvement without fresh trace events",
    }


def _condition_identity_alias_discovery(events: list[dict[str, Any]]) -> dict[str, Any]:
    alias_counts: Counter[str] = Counter()
    alias_by_producer: dict[str, Counter[str]] = {}
    traced_events = 0
    with_any_alias = 0

    for event in events:
        payload = _payload(event)
        if not _post_emission_field_present(payload, event, "candidate_trace_id"):
            continue
        traced_events += 1
        producer = _text(event.get("_category")) or "unknown"
        producer_bucket = alias_by_producer.setdefault(producer, Counter())
        found_alias = False
        for alias in CONDITION_IDENTITY_ALIAS_FIELDS:
            value = _text(_first_value(payload, alias))
            if not value:
                continue
            alias_counts[alias] += 1
            producer_bucket[alias] += 1
            found_alias = True
        if found_alias:
            with_any_alias += 1

    missing = max(0, traced_events - with_any_alias)
    best_alias, best_count = alias_counts.most_common(1)[0] if alias_counts else ("", 0)
    return {
        "condition_identity_alias_counts": dict(alias_counts.most_common()),
        "condition_identity_alias_by_producer": _nested_counter_dict(alias_by_producer),
        "traced_events_with_any_condition_alias": with_any_alias,
        "traced_events_condition_alias_missing": missing,
        "condition_identity_best_alias": {
            "alias": best_alias,
            "count": int(best_count),
            "share_of_traced_events": round(best_count / traced_events, 4) if traced_events else 0.0,
            "interpretation": (
                "canonical_condition_id_present"
                if best_alias == "condition_id"
                else "alias_evidence_only_not_canonical_truth"
                if best_alias
                else "no_condition_alias_evidence"
            ),
        },
        "condition_identity_alias_coverage_rate": round(with_any_alias / traced_events, 4) if traced_events else 0.0,
        "traced_events_scanned": traced_events,
        "condition_id_truly_absent_or_alias_hidden": (
            "condition_id_present"
            if alias_counts.get("condition_id")
            else "alias_hidden"
            if with_any_alias
            else "absent_in_discovered_aliases"
        ),
        "guardrail": "condition aliases are discovery evidence only; question_id and related fields are not treated as canonical condition_id truth",
    }


def _post_condition_enrichment_verification(events: list[dict[str, Any]]) -> dict[str, Any]:
    producer_totals: Counter[str] = Counter()
    producer_present: dict[str, Counter[str]] = {}
    direct_blockers: Counter[str] = Counter()
    strong_blockers: Counter[str] = Counter()
    condition_trace_ids: set[str] = set()
    trace_events = 0
    condition_present = 0
    direct_ready = 0
    strong_ready = 0

    for event in events:
        payload = _payload(event)
        candidate_trace_id = _text(_first_value(payload, "candidate_trace_id"))
        if not candidate_trace_id:
            continue
        trace_events += 1
        producer = _text(event.get("_category")) or "unknown"
        producer_totals[producer] += 1
        bucket = producer_present.setdefault(producer, Counter())
        has_condition = _post_emission_field_present(payload, event, "condition_id")
        if has_condition:
            condition_present += 1
            condition_trace_ids.add(candidate_trace_id)
            bucket["condition_id"] += 1

        missing_direct = [
            field for field in IDENTITY_CONFIDENCE_REQUIREMENTS["DIRECT"]
            if not _post_emission_field_present(payload, event, field)
        ]
        missing_strong = [
            field for field in IDENTITY_CONFIDENCE_REQUIREMENTS["STRONG"]
            if not _post_emission_field_present(payload, event, field)
        ]
        if not missing_direct:
            direct_ready += 1
        if not missing_strong:
            strong_ready += 1
        for field in missing_direct:
            direct_blockers[field] += 1
        for field in missing_strong:
            strong_blockers[field] += 1

    status = (
        "POST_CONDITION_ENRICHMENT_DATA_FOUND"
        if condition_present
        else "POST_CONDITION_ENRICHMENT_DATA_NOT_FOUND"
    )
    baseline = {
        "pre_patch_traced_events_with_condition_id": 0,
        "pre_patch_trace_events_direct_ready": 0,
        "pre_patch_trace_events_strong_ready": 0,
    }
    return {
        "post_condition_enrichment_data_status": status,
        "post_condition_enrichment_data_exists": bool(condition_present),
        "events_scanned": len(events),
        "trace_events_scanned": trace_events,
        **baseline,
        "traced_events_with_condition_id_after_enrichment": condition_present,
        "condition_id_presence_by_producer_after_enrichment": _presence_by_producer(
            producer_totals,
            producer_present,
            "condition_id",
        ),
        "condition_id_enrichment_candidate_count": len(condition_trace_ids),
        "trace_events_direct_ready_after_condition_enrichment": direct_ready if condition_present else 0,
        "trace_events_strong_ready_after_condition_enrichment": strong_ready if condition_present else 0,
        "condition_enrichment_delta": {
            "traced_events_with_condition_id_delta": condition_present - baseline["pre_patch_traced_events_with_condition_id"],
            "trace_events_direct_ready_delta": (direct_ready if condition_present else 0) - baseline["pre_patch_trace_events_direct_ready"],
            "trace_events_strong_ready_delta": (strong_ready if condition_present else 0) - baseline["pre_patch_trace_events_strong_ready"],
        },
        "fields_still_preventing_direct_identity_after_condition_enrichment": (
            dict(direct_blockers.most_common()) if condition_present else {}
        ),
        "fields_still_preventing_strong_identity_after_condition_enrichment": (
            dict(strong_blockers.most_common()) if condition_present else {}
        ),
        "interpretation": (
            "fresh trace events with canonical condition_id were found after passive condition enrichment; DIRECT and STRONG readiness remain separated from PROXY"
            if condition_present
            else "POST_CONDITION_ENRICHMENT_DATA_NOT_FOUND; no candidate_trace_id-bearing events with canonical condition_id were found in the selected replay data"
        ),
        "guardrail": "offline verification only; old reports are not reinterpreted as post-condition-enrichment evidence and condition_id is not used for decisions",
    }


def _post_fallback_condition_coverage_verification(
    post_condition_enrichment: dict[str, Any],
    alias_normalization: dict[str, Any],
) -> dict[str, Any]:
    traced_with_condition = int(post_condition_enrichment.get("traced_events_with_condition_id_after_enrichment") or 0)
    trace_events = int(alias_normalization.get("trace_events_with_candidate_trace_id") or 0)
    direct_ready = int(post_condition_enrichment.get("trace_events_direct_ready_after_condition_enrichment") or 0)
    strong_ready = int(post_condition_enrichment.get("trace_events_strong_ready_after_condition_enrichment") or 0)
    direct_blockers = dict(
        post_condition_enrichment.get("fields_still_preventing_direct_identity_after_condition_enrichment") or {}
    )
    if not direct_blockers:
        direct_blockers = dict(alias_normalization.get("fields_still_missing_after_alias_normalization") or {})

    status = "POST_FALLBACK_DATA_FOUND" if traced_with_condition else "POST_FALLBACK_DATA_NOT_FOUND"
    return {
        "post_fallback_data_status": status,
        "post_fallback_data_exists": bool(traced_with_condition),
        "pre_fallback_condition_id": 0,
        "pre_fallback_direct_ready": 0,
        "pre_fallback_strong_ready": 0,
        "trace_events_with_candidate_trace_id": trace_events,
        "traced_events_with_condition_id": traced_with_condition,
        "condition_id_presence_by_producer": post_condition_enrichment.get(
            "condition_id_presence_by_producer_after_enrichment",
            {},
        ),
        "trace_events_direct_ready": direct_ready if traced_with_condition else 0,
        "trace_events_strong_ready": strong_ready if traced_with_condition else 0,
        "remaining_identity_blockers": direct_blockers,
        "post_fallback_delta": {
            "condition_id_delta": traced_with_condition,
            "direct_ready_delta": direct_ready if traced_with_condition else 0,
            "strong_ready_delta": strong_ready if traced_with_condition else 0,
        },
        "interpretation": (
            "fresh post-fallback trace events contain canonical condition_id; DIRECT and STRONG readiness are evidence-only"
            if traced_with_condition
            else "POST_FALLBACK_DATA_NOT_FOUND; no candidate_trace_id-bearing events with canonical condition_id were found in the selected fresh replay slice"
        ),
        "guardrail": "offline verification only; condition_id and candidate_trace_id are not used for runtime decisions",
    }


def _candidate_trace_id_post_emission_verification(events: list[dict[str, Any]]) -> dict[str, Any]:
    producer_totals: Counter[str] = Counter()
    producer_present: dict[str, Counter[str]] = {}
    field_totals: Counter[str] = Counter()
    direct_ids: set[str] = set()
    strong_ids: set[str] = set()
    proxy_events = 0
    direct_blockers: Counter[str] = Counter()

    for index, event in enumerate(events):
        payload = _payload(event)
        producer = _text(event.get("_category")) or "unknown"
        producer_totals[producer] += 1
        bucket = producer_present.setdefault(producer, Counter())
        for field in POST_EMISSION_TRACE_FIELDS:
            if _post_emission_field_present(payload, event, field):
                bucket[field] += 1
                field_totals[field] += 1

        candidate_trace_id = _text(_first_value(payload, "candidate_trace_id"))
        missing_direct = [
            field for field in IDENTITY_CONFIDENCE_REQUIREMENTS["DIRECT"]
            if not _post_emission_field_present(payload, event, field)
        ]
        missing_strong = [
            field for field in IDENTITY_CONFIDENCE_REQUIREMENTS["STRONG"]
            if not _post_emission_field_present(payload, event, field)
        ]
        if candidate_trace_id:
            if not missing_direct:
                direct_ids.add(candidate_trace_id)
            if not missing_strong:
                strong_ids.add(candidate_trace_id)
            for field in missing_direct:
                direct_blockers[field] += 1
        elif (
            _post_emission_field_present(payload, event, "market_key")
            and _post_emission_field_present(payload, event, "candidate_seen_ts")
        ):
            proxy_events += 1

    total_events = sum(producer_totals.values())
    present_count = int(field_totals.get("candidate_trace_id", 0))
    status = "POST_EMISSION_DATA_FOUND" if present_count else "POST_EMISSION_DATA_NOT_FOUND"
    return {
        "post_emission_data_status": status,
        "post_emission_data_exists": bool(present_count),
        "events_scanned": total_events,
        "candidate_trace_id_present_count": present_count,
        "candidate_trace_id_missing_count": max(0, total_events - present_count),
        "candidate_trace_id_presence_by_producer": _presence_by_producer(producer_totals, producer_present, "candidate_trace_id"),
        "parent_candidate_trace_id_presence_by_producer": _presence_by_producer(producer_totals, producer_present, "parent_candidate_trace_id"),
        "trace_link_reason_presence_by_producer": _presence_by_producer(producer_totals, producer_present, "trace_link_reason"),
        "market_key_presence_by_producer": _presence_by_producer(producer_totals, producer_present, "market_key"),
        "condition_id_presence_by_producer": _presence_by_producer(producer_totals, producer_present, "condition_id"),
        "token_id_presence_by_producer": _presence_by_producer(producer_totals, producer_present, "token_id"),
        "side_presence_by_producer": _presence_by_producer(producer_totals, producer_present, "side"),
        "post_emission_direct_identity_candidates": len(direct_ids),
        "post_emission_strong_identity_candidates": len(strong_ids),
        "post_emission_proxy_candidates": proxy_events if present_count else 0,
        "direct_identity_improvement_possible": bool(present_count),
        "fields_still_preventing_direct_identity": dict(direct_blockers.most_common()) if present_count else {},
        "interpretation": (
            "fresh post-emission trace fields found in JSONL"
            if present_count
            else "POST_EMISSION_DATA_NOT_FOUND; no candidate_trace_id-bearing JSONL events were found in the selected replay data"
        ),
        "guardrail": "offline verification only; historical reports are not treated as post-emission evidence",
    }


def _merge_envelope_coverage(target: dict[str, Counter[str]], source: Any) -> None:
    if not isinstance(source, dict):
        return
    by_producer = source.get("by_producer") if isinstance(source.get("by_producer"), dict) else {}
    for producer, stats in by_producer.items():
        if not isinstance(stats, dict):
            continue
        bucket = target.setdefault(str(producer), Counter())
        for field in stats.get("required_fields", []):
            bucket[f"{field}:required"] += 1
        for field in stats.get("present_fields", []):
            bucket[f"{field}:present"] += 1


def _envelope_readiness_summary(raw: dict[str, Counter[str]]) -> dict[str, Any]:
    missing_by_producer: dict[str, Any] = {}
    readiness_by_producer: dict[str, Any] = {}
    runtime_needed: dict[str, list[str]] = {}
    total_required = 0
    total_present = 0
    for producer in TRACE_PRODUCER_ORDER:
        counts = raw.get(producer, Counter())
        required_fields = PRODUCER_REQUIRED_FIELDS[producer]
        producer_required = 0
        producer_present = 0
        field_missing: dict[str, Any] = {}
        needed_fields: list[str] = []
        for field in required_fields:
            required_count = int(counts.get(f"{field}:required", 0))
            present_count = int(counts.get(f"{field}:present", 0))
            missing_count = max(0, required_count - present_count)
            producer_required += required_count
            producer_present += present_count
            if missing_count:
                needed_fields.append(field)
            field_missing[field] = {
                "missing_count": missing_count,
                "present_count": present_count,
                "required_count": required_count,
                "missing_rate": round(missing_count / required_count, 4) if required_count else 0.0,
            }
        total_required += producer_required
        total_present += producer_present
        score = round(producer_present / producer_required, 4) if producer_required else 0.0
        missing_by_producer[producer] = field_missing
        readiness_by_producer[producer] = {
            "envelope_readiness_score": score,
            "present_field_slots": producer_present,
            "required_field_slots": producer_required,
            "missing_field_slots": max(0, producer_required - producer_present),
        }
        runtime_needed[producer] = needed_fields
    weakest = min(
        readiness_by_producer.items(),
        key=lambda item: (item[1]["envelope_readiness_score"], -item[1]["missing_field_slots"], item[0]),
    )[0] if readiness_by_producer else "none"
    return {
        "producer_required_fields": {producer: list(fields) for producer, fields in PRODUCER_REQUIRED_FIELDS.items()},
        "missing_envelope_fields_by_producer": missing_by_producer,
        "envelope_readiness_by_producer": readiness_by_producer,
        "envelope_readiness_score": round(total_present / total_required, 4) if total_required else 0.0,
        "weakest_envelope_producer": {
            "producer": weakest,
            **readiness_by_producer.get(weakest, {}),
        },
        "runtime_observability_fields_needed": runtime_needed,
    }


def _event_has_candidate_trace_id(event: dict[str, Any]) -> bool:
    return bool(event.get("candidate_trace_id") or event.get("candidate_id") or event.get("signal_id") or event.get("parent_candidate_trace_id"))


def _event_has_market_key(event: dict[str, Any]) -> bool:
    return bool(event.get("market_key") or event.get("market_id") or event.get("condition_id"))


def _event_has_lifecycle_phase(event: dict[str, Any]) -> bool:
    return bool(event.get("lifecycle_phase") and event.get("lifecycle_phase") != UNKNOWN_CONTEXT)


def _event_has_risk_state(event: dict[str, Any]) -> bool:
    return any(
        bool(_text(event.get(field)) and _text(event.get(field)) != UNKNOWN_CONTEXT)
        for field in ("risk_state", "candidate_block_stage", "candidate_block_reason")
    )


def _event_has_decision_block_evidence(event: dict[str, Any]) -> bool:
    if event.get("event_category") != "decision_log":
        return False
    normalized_values = {
        _reason_text(event.get("candidate_block_stage")),
        _reason_text(event.get("candidate_block_reason")),
    }
    normalized_values.discard("")
    normalized_values.discard(UNKNOWN_CONTEXT)
    if normalized_values - {"field_not_emitted", "legacy_missing_reason", "candidate_blocked_after_ev"}:
        return True
    raw_text = " ".join(
        _reason_text(event.get(field))
        for field in ("evaluation_state", "candidate_block_stage", "candidate_block_reason")
    )
    return any(token in raw_text for token in ("skip", "block", "reject", "deny", "cutoff", "zero_position", "no_entry"))


def _event_has_risk_reach_evidence(event: dict[str, Any]) -> bool:
    risk_state = _reason_text(event.get("risk_state"))
    if risk_state and risk_state not in {UNKNOWN_CONTEXT, "field_not_emitted", "legacy_missing_reason"}:
        return True
    raw_text = " ".join(
        _reason_text(event.get(field))
        for field in ("evaluation_state", "candidate_block_stage", "candidate_block_reason")
    )
    return "risk" in raw_text


def _decision_to_risk_boundary_category(
    *,
    decision_events: list[dict[str, Any]],
    risk_events: list[dict[str, Any]],
    pre_risk_events: list[dict[str, Any]],
    risk_identity_visible: bool,
    risk_state_visible: bool,
) -> str:
    if not decision_events:
        return "NO_DECISION_EVIDENCE"
    if risk_events:
        if risk_identity_visible and risk_state_visible:
            return "LEGACY_OR_UNKNOWN"
        return "RISK_REACHED_NOT_SERIALIZED"
    if any(_event_has_decision_block_evidence(event) for event in decision_events):
        return "BLOCKED_BEFORE_RISK"
    if any(_event_has_risk_reach_evidence(event) for event in pre_risk_events):
        return "RISK_REACHED_NOT_SERIALIZED"
    if any(_event_blocked_before_ev(event) for event in pre_risk_events if event.get("event_category") != "decision_log"):
        return "RISK_PRODUCER_NOT_RESPONSIBLE"
    return "RISK_NOT_REACHED"


def _event_tokens(event: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    for field in (
        "candidate_block_stage",
        "candidate_block_reason",
        "market_readiness_state",
        "orderbook_state_classification",
        "evaluation_state",
        "spread_state",
        "lifecycle_phase",
        "model_activation_state",
        "model_activation_block_reason",
    ):
        token = _reason_text(event.get(field))
        if token and token != UNKNOWN_CONTEXT:
            tokens.add(token)
    for field in EV_COMPONENT_FIELDS:
        status = event.get("fields", {}).get(field, {})
        if isinstance(status, dict):
            reason = _reason_text(status.get("null_reason"))
            if reason:
                tokens.add(reason)
    return tokens


def _pre_risk_block_causes(pre_risk_events: list[dict[str, Any]], boundary_category: str) -> dict[str, Any]:
    if boundary_category != "BLOCKED_BEFORE_RISK":
        return {
            "pre_risk_block_causes": [],
            "dominant_pre_risk_block_cause": "",
        }
    causes: set[str] = set()
    for event in pre_risk_events:
        tokens = _event_tokens(event)
        fields = event.get("fields", {})
        if event.get("match_inference") == "market_window_proxy":
            causes.add("IDENTITY_LINK_WEAK")
        if not event.get("candidate_id") and not event.get("signal_id"):
            causes.add("IDENTITY_LINK_WEAK")
        if any(token in tokens for token in {"no_probability_model_output", "candidate_blocked_before_ev"}):
            causes.add("PROBABILITY_NOT_VISIBLE")
        if isinstance(fields.get("true_probability"), dict) and not fields["true_probability"].get("available"):
            causes.add("PROBABILITY_NOT_VISIBLE")
        if isinstance(fields.get("fair_value"), dict) and not fields["fair_value"].get("available"):
            causes.add("FAIR_VALUE_NOT_VISIBLE")
        if isinstance(fields.get("ev_after_spread"), dict) and not fields["ev_after_spread"].get("available"):
            causes.add("EV_NOT_VISIBLE")
        if any(token in tokens for token in {"no_orderbook", "empty_book", "no_market_price"}):
            causes.add("ORDERBOOK_NOT_READY")
        if "liquidity_not_ready" in tokens:
            causes.add("LIQUIDITY_NOT_READY")
        if "spread_not_ready" in tokens:
            causes.add("SPREAD_NOT_EXECUTABLE")
        if "time_unsafe" in tokens or any("cutoff" in token or "time" in token for token in tokens):
            causes.add("CUTOFF_OR_TIME_BLOCK")
        phase = _reason_text(event.get("lifecycle_phase"))
        if phase in {"closed_or_unsafe", "final_derisk"} or "lifecycle" in " ".join(tokens):
            causes.add("LIFECYCLE_PHASE_BLOCK")
        if any(token in tokens for token in {"market_not_evaluable", "not_evaluable", "field_never_evaluated"}):
            causes.add("MARKET_NOT_EVALUABLE")
    if not causes:
        causes.add("UNKNOWN_PRE_RISK_BLOCK")
    ordered = [cause for cause in PRE_RISK_BLOCK_CAUSES if cause in causes]
    return {
        "pre_risk_block_causes": ordered,
        "dominant_pre_risk_block_cause": ordered[0],
    }


def _field_model_state_gap(
    window_events: list[dict[str, Any]],
    field: str,
    *,
    candidate_trace_confidence: str,
    identity_fragmentation_detected: bool,
    candidate_seen_but_never_evaluable: bool,
) -> tuple[str, bool, bool]:
    field_events = [
        event for event in window_events
        if isinstance(event.get("fields", {}).get(field), dict)
    ]
    decision_events = [
        event for event in field_events
        if event.get("event_category") == "decision_log"
    ]
    output_serialized = any(event["fields"][field].get("available") for event in decision_events)
    output_visible_elsewhere = any(event["fields"][field].get("available") for event in field_events)
    if output_serialized:
        return "", True, True
    if output_visible_elsewhere:
        return "MODEL_OUTPUT_EXISTS_NOT_SERIALIZED", True, False
    if any(str(event.get("model_activation_state") or "").upper() == "BLOCKED_BEFORE_MODEL" for event in field_events):
        return "BLOCKED_BEFORE_MODEL", False, False

    reasons = {
        _reason_text(event["fields"][field].get("null_reason"))
        for event in field_events
        if _reason_text(event["fields"][field].get("null_reason"))
    }
    tokens: set[str] = set()
    for event in field_events:
        tokens.update(_event_tokens(event))
    emitted = any(event["fields"][field].get("emitted") for event in field_events)
    explicit_block_before_model = (
        "candidate_blocked_before_ev" in reasons
        or any(_event_blocked_before_ev(event) for event in field_events)
    )
    if explicit_block_before_model:
        return "BLOCKED_BEFORE_MODEL", False, False

    attempt_reasons = {
        "no_probability_model_output",
        "candidate_blocked_after_ev",
        "no_market_price",
        "no_orderbook",
        "empty_book",
        "spread_not_ready",
        "liquidity_not_ready",
        "time_unsafe",
    }
    if emitted and bool(reasons & attempt_reasons):
        return "MODEL_ATTEMPTED_OUTPUT_MISSING", True, False
    if field == "ev_after_spread" and any(_event_ev_attempted(event) for event in field_events):
        return "MODEL_ATTEMPTED_OUTPUT_MISSING", True, False

    explicit_not_attempted = bool(
        candidate_seen_but_never_evaluable
        or "model_not_attempted" in tokens
        or "probability_not_attempted" in tokens
        or "not_evaluable" in tokens
        or "market_not_evaluable" in tokens
    )
    if explicit_not_attempted:
        return "MODEL_NOT_ATTEMPTED", False, False

    if (
        candidate_trace_confidence in {"PROXY", "UNKNOWN"}
        or identity_fragmentation_detected
        or any(event.get("match_inference") == "market_window_proxy" for event in field_events)
    ):
        return "IDENTITY_TOO_WEAK_TO_LINK_MODEL_STATE", False, False
    return "MODEL_STATE_UNKNOWN", False, False


def _model_state_gap_report(window_events: list[dict[str, Any]], lifecycle_trace: dict[str, Any]) -> dict[str, Any]:
    field_gaps: dict[str, str] = {}
    attempt_visible = False
    output_serialized = False
    for name, field in MODEL_STATE_FIELDS.items():
        gap, field_attempt_visible, field_output_serialized = _field_model_state_gap(
            window_events,
            field,
            candidate_trace_confidence=str(lifecycle_trace.get("candidate_trace_confidence") or "UNKNOWN"),
            identity_fragmentation_detected=bool(lifecycle_trace.get("identity_fragmentation_detected")),
            candidate_seen_but_never_evaluable=bool(lifecycle_trace.get("candidate_seen_but_never_evaluable")),
        )
        field_gaps[name] = gap
        attempt_visible = attempt_visible or field_attempt_visible
        output_serialized = output_serialized or field_output_serialized
    gap_values = [gap for gap in field_gaps.values() if gap]
    dominant_gap = ""
    if gap_values:
        dominant_gap = Counter(gap_values).most_common(1)[0][0]
    identity_blocked = "IDENTITY_TOO_WEAK_TO_LINK_MODEL_STATE" in gap_values
    return {
        "model_state_gaps": field_gaps,
        "probability_state_gap": field_gaps["probability"],
        "fair_value_state_gap": field_gaps["fair_value"],
        "ev_state_gap": field_gaps["ev"],
        "model_attempt_visible": attempt_visible,
        "model_output_serialized": output_serialized,
        "identity_blocked_model_link": identity_blocked,
        "dominant_model_state_gap": dominant_gap,
    }


def _model_attempt_gate_report(
    window_events: list[dict[str, Any]],
    lifecycle_trace: dict[str, Any],
    model_state_gap: dict[str, Any],
) -> dict[str, Any]:
    dominant_gap = str(model_state_gap.get("dominant_model_state_gap") or "")
    gated = dominant_gap in {"MODEL_NOT_ATTEMPTED", "BLOCKED_BEFORE_MODEL"}
    if not gated:
        return {
            "model_attempt_gates": [],
            "dominant_model_attempt_gate": "",
            "model_attempt_eligible": True,
        }

    tokens: set[str] = set()
    for event in window_events:
        tokens.update(_event_tokens(event))
    gates: set[str] = set()
    for event in window_events:
        group = str(event.get("model_activation_block_group") or "").strip().upper()
        if group in MODEL_ATTEMPT_GATE_CAUSES:
            gates.add(group)
    if any(token in tokens for token in {"no_orderbook", "empty_book", "no_market_price"}):
        gates.add("ORDERBOOK_GATE")
    if "liquidity_not_ready" in tokens:
        gates.add("LIQUIDITY_GATE")
    if "spread_not_ready" in tokens:
        gates.add("SPREAD_GATE")
    if "time_unsafe" in tokens or any("cutoff" in token or "time" in token for token in tokens):
        gates.add("TIME_CUTOFF_GATE")
    lifecycle_tokens = {_reason_text(event.get("lifecycle_phase")) for event in window_events}
    if lifecycle_tokens & {"closed_or_unsafe", "final_derisk"} or any("lifecycle" in token for token in tokens):
        gates.add("LIFECYCLE_PHASE_GATE")
    if any(token in tokens for token in {"market_not_evaluable", "not_evaluable", "field_never_evaluated"}):
        gates.add("MARKET_NOT_EVALUABLE_GATE")
    trace_confidence = str(lifecycle_trace.get("candidate_trace_confidence") or "UNKNOWN")
    if (
        trace_confidence in {"PROXY", "UNKNOWN"}
        or bool(lifecycle_trace.get("identity_fragmentation_detected"))
        or any(event.get("match_inference") == "market_window_proxy" for event in window_events)
    ):
        gates.add("IDENTITY_CONFIDENCE_GATE")
    if any(event.get("event_category") in {"risk_log", "execution_log", "trade_journal", "system_health"} for event in window_events) and not any(
        event.get("event_category") == "decision_log" for event in window_events
    ):
        gates.add("PRODUCER_NOT_RESPONSIBLE")
    if not gates:
        gates.add("MODEL_GATE_UNKNOWN")
    ordered = [gate for gate in MODEL_ATTEMPT_GATE_CAUSES if gate in gates]
    return {
        "model_attempt_gates": ordered,
        "dominant_model_attempt_gate": ordered[0],
        "model_attempt_eligible": False,
    }


def _risk_layer_gap(window_events: list[dict[str, Any]]) -> dict[str, Any]:
    decision_events = [event for event in window_events if event.get("event_category") == "decision_log"]
    risk_events = [event for event in window_events if event.get("event_category") == "risk_log"]
    execution_events = [event for event in window_events if event.get("event_category") == "execution_log"]
    pre_risk_events = [event for event in window_events if event.get("event_category") in {"market_snapshots", "decision_log"}]

    risk_event_exists = bool(risk_events)
    risk_identity_visible = any(_event_has_candidate_trace_id(event) for event in risk_events)
    risk_market_key_visible = any(_event_has_market_key(event) for event in risk_events)
    risk_lifecycle_visible = any(_event_has_lifecycle_phase(event) for event in risk_events)
    risk_state_visible = any(_event_has_risk_state(event) for event in risk_events)
    decision_identity_visible = any(_event_has_candidate_trace_id(event) for event in decision_events)
    execution_identity_visible = any(_event_has_candidate_trace_id(event) for event in execution_events)
    blocked_before_risk = bool(not risk_event_exists and any(_event_blocked_before_ev(event) for event in pre_risk_events))
    ev_visible_before_risk = any(event.get("any_ev_component_visible") for event in pre_risk_events)
    ev_visible_before_risk_missing_after = bool(ev_visible_before_risk and (not risk_event_exists or not risk_state_visible))
    boundary_category = _decision_to_risk_boundary_category(
        decision_events=decision_events,
        risk_events=risk_events,
        pre_risk_events=pre_risk_events,
        risk_identity_visible=risk_identity_visible,
        risk_state_visible=risk_state_visible,
    )
    risk_reachable = bool(risk_event_exists or any(_event_has_risk_reach_evidence(event) for event in pre_risk_events))
    risk_serialization_visible = bool(risk_event_exists and risk_identity_visible and risk_state_visible)
    pre_risk_cause_report = _pre_risk_block_causes(pre_risk_events, boundary_category)

    if not decision_events:
        decision_to_risk_quality = "NO_DECISION_EVIDENCE"
    elif not risk_event_exists:
        decision_to_risk_quality = "NO_RISK_EVENT"
    elif not risk_identity_visible:
        decision_to_risk_quality = "RISK_EVENT_LACKS_CANDIDATE_IDENTITY"
    elif not risk_state_visible:
        decision_to_risk_quality = "RISK_EVENT_LACKS_RISK_STATE"
    else:
        decision_to_risk_quality = "RISK_HANDOFF_OBSERVABLE"

    if not risk_event_exists:
        risk_to_execution_quality = "NO_RISK_EVENT"
    elif not execution_events:
        risk_to_execution_quality = "NO_EXECUTION_EVENT"
    elif not risk_identity_visible:
        risk_to_execution_quality = "UPSTREAM_RISK_IDENTITY_MISSING"
    elif not execution_identity_visible:
        risk_to_execution_quality = "EXECUTION_EVENT_LACKS_CANDIDATE_IDENTITY"
    else:
        risk_to_execution_quality = "RISK_TO_EXECUTION_OBSERVABLE"

    if blocked_before_risk:
        block_visibility = "CANDIDATE_BLOCKED_BEFORE_RISK_SERIALIZATION"
    elif not risk_event_exists:
        block_visibility = "NO_RISK_EVENT"
    elif not risk_state_visible:
        block_visibility = "RISK_EVENT_LACKS_RISK_STATE"
    else:
        block_visibility = "RISK_STATE_VISIBLE"

    if not risk_event_exists:
        gap_reason = "no_risk_event_exists"
    elif not risk_identity_visible:
        gap_reason = "risk_event_exists_but_lacks_candidate_identity"
    elif not risk_state_visible:
        gap_reason = "risk_event_exists_but_lacks_risk_state"
    elif blocked_before_risk:
        gap_reason = "candidate_blocked_before_risk_serialization"
    else:
        gap_reason = "risk_layer_trace_observable"

    visible_slots = sum(1 for visible in (risk_identity_visible, risk_market_key_visible, risk_lifecycle_visible, risk_state_visible) if visible)
    return {
        "risk_log_event_count": len(risk_events),
        "risk_log_identity_missing": not risk_identity_visible,
        "risk_log_market_key_missing": not risk_market_key_visible,
        "risk_log_lifecycle_phase_missing": not risk_lifecycle_visible,
        "risk_log_risk_state_missing": not risk_state_visible,
        "no_risk_event_exists": not risk_event_exists,
        "risk_event_exists_but_lacks_candidate_identity": bool(risk_event_exists and not risk_identity_visible),
        "risk_event_exists_but_lacks_risk_state": bool(risk_event_exists and not risk_state_visible),
        "candidate_blocked_before_risk_visibility": blocked_before_risk,
        "ev_visible_before_risk_missing_after": ev_visible_before_risk_missing_after,
        "risk_producer_not_responsible": bool(blocked_before_risk),
        "stale_legacy_schema": False,
        "decision_to_risk_boundary_category": boundary_category,
        "risk_reachable": risk_reachable,
        "risk_serialization_visible": risk_serialization_visible,
        "blocked_before_risk_boundary": boundary_category == "BLOCKED_BEFORE_RISK",
        "no_decision_evidence_boundary": boundary_category == "NO_DECISION_EVIDENCE",
        **pre_risk_cause_report,
        "decision_to_risk_handoff_quality": decision_to_risk_quality,
        "risk_to_execution_handoff_quality": risk_to_execution_quality,
        "risk_layer_block_visibility": block_visibility,
        "risk_layer_trace_readiness": round(visible_slots / 4, 4),
        "weakest_risk_gap_reason": gap_reason,
        "dominant_risk_visibility_failure": gap_reason,
        "runtime_observability_fields_needed_for_risk_layer": [
            field
            for field, missing in (
                ("candidate_trace_id", not risk_identity_visible),
                ("market_key", not risk_market_key_visible),
                ("lifecycle_phase", not risk_lifecycle_visible),
                ("risk_state", not risk_state_visible),
                ("parent_candidate_trace_id", risk_event_exists and not any(event.get("parent_candidate_trace_id") for event in risk_events)),
                ("trace_link_reason", risk_event_exists and not any(event.get("match_inference") for event in risk_events)),
            )
            if missing
        ],
    }


def _candidate_lifecycle_trace(
    chain: dict[str, Any],
    window_events: list[dict[str, Any]],
    visible_duration_ms: float,
) -> dict[str, Any]:
    event_count = len(window_events)
    visible_events = [event for event in window_events if event["any_ev_component_visible"]]
    direct_events = [event for event in window_events if event.get("match_inference") == "direct_identity"]
    proxy_events = [event for event in window_events if event.get("match_inference") == "market_window_proxy"]
    observed_producers = {
        str(event.get("event_category") or "unknown")
        for event in window_events
        if event.get("event_category")
    }
    observed_producer_ranks = sorted(
        TRACE_PRODUCER_RANK[producer]
        for producer in observed_producers
        if producer in TRACE_PRODUCER_RANK
    )
    direct_candidate_ids = {
        str(event.get("candidate_id") or "")
        for event in direct_events
        if event.get("candidate_id")
    }
    direct_signal_ids = {
        str(event.get("signal_id") or "")
        for event in direct_events
        if event.get("signal_id")
    }
    missing_direct_identity = bool(direct_events) and any(
        not event.get("candidate_id") and not event.get("signal_id")
        for event in direct_events
    )
    identity_fragmentation_detected = bool(
        proxy_events
        or missing_direct_identity
        or len(direct_candidate_ids) > 1
        or len(direct_signal_ids) > 1
    )
    producer_rank_gap = any(
        right - left > 1
        for left, right in zip(observed_producer_ranks, observed_producer_ranks[1:])
    )
    ev_visibility_attempted = any(_event_ev_attempted(event) for event in window_events)
    ev_visibility_confirmed = bool(visible_events)
    candidate_blocked_before_ev = any(_event_blocked_before_ev(event) for event in window_events)
    candidate_seen_but_never_evaluable = bool(window_events) and not ev_visibility_attempted and not ev_visibility_confirmed
    ev_attempted_but_not_visible = ev_visibility_attempted and not ev_visibility_confirmed
    first_visible = visible_events[0] if visible_events else None
    last_visible = visible_events[-1] if visible_events else None
    post_visible_events: list[dict[str, Any]] = []
    if last_visible is not None:
        last_timestamp = last_visible.get("timestamp")
        post_visible_events = [
            event
            for event in window_events
            if event.get("timestamp") is not None
            and last_timestamp is not None
            and event["timestamp"] > last_timestamp
            and not event["any_ev_component_visible"]
        ]
    disappearance_event = post_visible_events[0] if post_visible_events else None

    transitions: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    ordered_events = sorted(
        window_events,
        key=lambda event: (
            TRACE_PRODUCER_RANK.get(str(event.get("event_category") or ""), len(TRACE_PRODUCER_ORDER)),
            event.get("timestamp_utc") or "",
        ),
    )
    for previous, current in zip(ordered_events, ordered_events[1:]):
        previous_visible = bool(previous["any_ev_component_visible"])
        current_visible = bool(current["any_ev_component_visible"])
        transition = {
            "from_producer": previous.get("event_category") or "unknown",
            "to_producer": current.get("event_category") or "unknown",
            "from_phase": previous.get("lifecycle_phase") or UNKNOWN_CONTEXT,
            "to_phase": current.get("lifecycle_phase") or UNKNOWN_CONTEXT,
            "from_ev_visible": previous_visible,
            "to_ev_visible": current_visible,
            "break_reason": _dominant_event_null_reason(current) if previous_visible and not current_visible else "",
            "missing_semantic": _missing_semantic(current) if previous_visible and not current_visible else "",
        }
        transitions.append(transition)
        if previous_visible and not current_visible:
            failures.append(transition)

    terminal_state = _text(chain.get("candidate_terminal_state"))
    continuity_status = _text(chain.get("continuity_status"))
    continuity_break_reason = _text(chain.get("continuity_break_reason"))
    lifecycle_interrupted = bool(
        continuity_break_reason
        or terminal_state.upper() in {"EXPIRED", "DISAPPEARED", "ORPHANED", "BLOCKED_PRE_EV"}
        or "BREAK" in continuity_status.upper()
    )
    expiry_before_propagation = not visible_events and terminal_state.upper() in {"EXPIRED", "BLOCKED_PRE_EV"}

    disappearance_reason = _dominant_event_null_reason(disappearance_event) if disappearance_event else ""
    trace_break_phase = (
        disappearance_event.get("lifecycle_phase")
        if disappearance_event
        else (last_visible.get("lifecycle_phase") if last_visible else "NO_EV_VISIBLE")
    ) or UNKNOWN_CONTEXT
    lifecycle_timing_reasons = {
        "candidate_blocked_before_ev",
        "candidate_blocked_after_ev",
        "time_unsafe",
        "no_orderbook",
        "empty_book",
        "spread_not_ready",
        "liquidity_not_ready",
    }
    producer_caused = bool(
        disappearance_event
        and _dominant_event_null_reason(disappearance_event) in UNCERTAIN_MISSING_REASONS
    )
    lifecycle_timing_caused = bool(
        disappearance_event
        and _dominant_event_null_reason(disappearance_event) in lifecycle_timing_reasons
    ) or expiry_before_propagation
    survival_ms = _as_float_or_none(chain.get("candidate_survival_ms")) or 0.0
    survival_rate = round(visible_duration_ms / survival_ms, 4) if survival_ms > 0 else (
        round(len(visible_events) / event_count, 4) if event_count else 0.0
    )
    quality = _trace_quality(
        event_count=event_count,
        visible_event_count=len(visible_events),
        transition_failures=len(failures),
        lifecycle_interrupted=lifecycle_interrupted,
    )
    handoff_quality = _handoff_quality(len(transitions), len(failures))
    propagation_gap_detected = bool(
        failures
        or producer_rank_gap
        or candidate_seen_but_never_evaluable
        or (event_count > 1 and len(observed_producers) <= 1)
    )
    lifecycle_propagation_interruption = bool(
        lifecycle_interrupted
        or candidate_blocked_before_ev
        or candidate_seen_but_never_evaluable
        or ev_attempted_but_not_visible
    )
    if event_count <= 0:
        candidate_trace_confidence = "UNKNOWN"
    elif not direct_events:
        candidate_trace_confidence = "PROXY"
    elif identity_fragmentation_detected:
        candidate_trace_confidence = "WEAK"
    elif len(direct_events) == event_count and len(observed_producers) >= 2 and not propagation_gap_detected:
        candidate_trace_confidence = "DIRECT"
    elif len(direct_events) == event_count or len(observed_producers) >= 2:
        candidate_trace_confidence = "STRONG"
    else:
        candidate_trace_confidence = "WEAK"
    identity_by_producer = _producer_identity_confidence(
        window_events,
        candidate_trace_confidence,
        identity_fragmentation_detected,
    )
    transition_identity_gaps = _transition_identity_gap_tables(window_events)
    uncertainty = []
    if any(_dominant_event_null_reason(event) == "legacy_missing_reason" for event in window_events):
        uncertainty.append("legacy_missing_reason_preserved")
    if any(event.get("match_inference") == "market_window_proxy" for event in window_events):
        uncertainty.append("market_window_proxy_match_used")
    if not window_events:
        uncertainty.append("no_candidate_window_events")
    if not visible_events:
        uncertainty.append("no_ev_visible_events")

    return {
        "candidate_trace_confidence": candidate_trace_confidence,
        "identity_fragmentation_detected": identity_fragmentation_detected,
        "propagation_gap_detected": propagation_gap_detected,
        "lifecycle_propagation_interruption": lifecycle_propagation_interruption,
        "candidate_seen_but_never_evaluable": candidate_seen_but_never_evaluable,
        "candidate_blocked_before_ev": candidate_blocked_before_ev,
        "ev_attempted_but_not_visible": ev_attempted_but_not_visible,
        "ev_visibility_attempted": ev_visibility_attempted,
        "ev_visibility_confirmed": ev_visibility_confirmed,
        "trace_confidence_evidence": {
            "direct_identity_events": len(direct_events),
            "proxy_match_events": len(proxy_events),
            "observed_producers": sorted(observed_producers),
            "producer_rank_gap": producer_rank_gap,
            "direct_candidate_ids": sorted(direct_candidate_ids),
            "direct_signal_ids": sorted(direct_signal_ids),
        },
        "identity_confidence_by_producer": identity_by_producer,
        "producer_transition_identity_gap_tables": transition_identity_gaps,
        "first_ev_visible_phase": first_visible.get("lifecycle_phase") if first_visible else "NO_EV_VISIBLE",
        "first_ev_visible_producer": first_visible.get("event_category") if first_visible else "none",
        "last_ev_visible_phase": last_visible.get("lifecycle_phase") if last_visible else "NO_EV_VISIBLE",
        "last_ev_visible_producer": last_visible.get("event_category") if last_visible else "none",
        "ev_disappearance_phase": disappearance_event.get("lifecycle_phase") if disappearance_event else (
            "NO_EV_DISAPPEARANCE_AFTER_VISIBILITY" if visible_events else "NO_EV_VISIBLE"
        ),
        "ev_disappearance_producer": disappearance_event.get("event_category") if disappearance_event else "none",
        "ev_disappearance_reason": disappearance_reason or ("never_ev_visible" if not visible_events else "no_disappearance_observed"),
        "ev_trace_break_phase": trace_break_phase,
        "ev_lifecycle_visibility_score": round(len(visible_events) / event_count, 4) if event_count else 0.0,
        "candidate_phase_coverage": _phase_coverage(window_events),
        "producer_handoff_quality": handoff_quality,
        "continuity_survival_rate": survival_rate,
        "lifecycle_observability_quality": quality,
        "producer_transition_blindness": failures[:12],
        "producer_transition_count": len(transitions),
        "producer_handoff_failure_count": len(failures),
        "candidate_continuity_breaks": {
            "continuity_status": continuity_status,
            "continuity_break_reason": continuity_break_reason,
            "candidate_terminal_state": terminal_state,
            "lifecycle_interrupted": lifecycle_interrupted,
        },
        "lifecycle_truncation": {
            "detected": lifecycle_interrupted or expiry_before_propagation,
            "reason": continuity_break_reason or terminal_state or ("candidate_expired_before_propagation" if expiry_before_propagation else ""),
        },
        "why_ev_disappeared": disappearance_reason or ("candidate_expired_before_propagation" if expiry_before_propagation else "no_ev_disappearance_observed"),
        "where_ev_disappeared": {
            "phase": disappearance_event.get("lifecycle_phase") if disappearance_event else trace_break_phase,
            "producer": disappearance_event.get("event_category") if disappearance_event else "none",
        },
        "disappearance_expected": bool(lifecycle_timing_caused or expiry_before_propagation),
        "producer_caused_disappearance": producer_caused,
        "lifecycle_timing_caused_disappearance": lifecycle_timing_caused,
        "uncertainty": uncertainty,
        "compact_trace_events": [
            {
                "timestamp_utc": event["timestamp_utc"],
                "producer": event["event_category"],
                "lifecycle_phase": event["lifecycle_phase"],
                "ev_visible": event["any_ev_component_visible"],
                "visible_fields": _visible_fields(event),
                "dominant_null_reason": _dominant_event_null_reason(event),
                "missing_semantic": _missing_semantic(event),
            }
            for event in window_events[:16]
        ],
    }


def _classify_visibility(
    *,
    event_count: int,
    any_visible_count: int,
    field_dropout_reasons: dict[str, str],
) -> tuple[str, str, str]:
    visible_dropout = [reason for reason in field_dropout_reasons.values() if reason]
    if event_count == 0:
        return "EV_NO_WINDOW_EVENTS", "NO_EV_WINDOW", "no_candidate_window_events"
    if any_visible_count == 0:
        return "EV_NEVER_VISIBLE", "EV_BLIND", "no_ev_fields_in_survival_window"
    if any_visible_count == 1:
        return "EV_SPARSE_SINGLE_POINT", "SPARSE_EV_COMPONENTS", "single_ev_visible_event"
    if visible_dropout:
        return "EV_FIELD_DROPOUT", "PARTIAL_EV_COMPONENTS", f"field_dropout:{visible_dropout[0]}"
    if any_visible_count == event_count:
        return "EV_VISIBLE_CONTINUOUS", "FULL_OR_PARTIAL_CONTINUOUS", "no_sparse_ev_path"
    return "EV_PARTIAL_VISIBLE", "PARTIAL_EV_COMPONENTS", "intermittent_ev_visibility"


def _empty_crosstab() -> dict[str, Any]:
    return {
        "ev_null_by_lifecycle_phase": {},
        "ev_null_by_block_stage": {},
        "ev_null_by_block_reason": {},
        "ev_null_by_market_readiness": {},
        "ev_null_by_orderbook_state": {},
        "dominant_ev_blindness_context": {
            "dimension": "none",
            "context": UNKNOWN_CONTEXT,
            "reason": "no_ev_null_evidence",
            "count": 0,
            "share": 0.0,
        },
        "ev_blindness_root_cause_confidence": "NO_EVIDENCE",
    }


def _increment_crosstab(table: dict[str, Counter[str]], context: str, reason: str) -> None:
    if context not in table:
        table[context] = Counter()
    table[context][reason] += 1


def _crosstab_dict(table: dict[str, Counter[str]]) -> dict[str, dict[str, int]]:
    return {context: dict(counts.most_common()) for context, counts in sorted(table.items())}


def _merge_crosstab(target: dict[str, Counter[str]], source: dict[str, dict[str, int]]) -> None:
    for context, reason_counts in source.items():
        if context not in target:
            target[context] = Counter()
        for reason, count in reason_counts.items():
            target[context][reason] += int(count)


def _merge_producer_missing(target: dict[str, Counter[str]], source: dict[str, Any]) -> None:
    if not isinstance(source, dict):
        return
    for category, counts in source.items():
        if not isinstance(counts, dict):
            continue
        if category not in target:
            target[category] = Counter()
        for reason in UNCERTAIN_MISSING_REASONS:
            target[category][reason] += int(counts.get(reason) or 0)
        target[category]["missing_uncertain_ev_fields"] += int(counts.get("missing_uncertain_ev_fields") or 0)
        target[category]["total_ev_field_slots"] += int(counts.get("total_ev_field_slots") or 0)


def _merge_producer_visibility(target: dict[str, dict[str, Any]], source: dict[str, Any]) -> None:
    if not isinstance(source, dict):
        return
    by_category = source.get("by_event_category") if isinstance(source.get("by_event_category"), dict) else {}
    for category, stats in by_category.items():
        if not isinstance(stats, dict):
            continue
        if category not in target:
            target[category] = {
                "event_count": 0,
                "total_ev_field_slots": 0,
                "visible_ev_field_slots": 0,
                "ev_visible_event_count": 0,
                "missing_reason_counts": Counter(),
            }
        bucket = target[category]
        bucket["event_count"] += int(stats.get("event_count") or 0)
        bucket["total_ev_field_slots"] += int(stats.get("total_ev_field_slots") or 0)
        bucket["visible_ev_field_slots"] += int(stats.get("visible_ev_field_slots") or 0)
        bucket["ev_visible_event_count"] += int(stats.get("ev_visible_event_count") or 0)
        reasons = stats.get("missing_reason_counts") if isinstance(stats.get("missing_reason_counts"), dict) else {}
        for reason, count in reasons.items():
            bucket["missing_reason_counts"][str(reason)] += int(count)


def _producer_summary(
    producer_missing: dict[str, Counter[str]],
    producer_visibility: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    missing_by_category: dict[str, Any] = {}
    missing_counter: Counter[str] = Counter()
    producer_level: dict[str, Any] = {}
    total_uncertain_missing = 0
    total_slots = 0
    best_category = "none"
    best_rate = 0.0

    categories = sorted(set(producer_missing) | set(producer_visibility))
    for category in categories:
        missing_counts = producer_missing.get(category, Counter())
        visibility = producer_visibility.get(category, {})
        field_not_emitted = int(missing_counts.get("field_not_emitted", 0))
        legacy_missing = int(missing_counts.get("legacy_missing_reason", 0))
        uncertain_missing = int(missing_counts.get("missing_uncertain_ev_fields", field_not_emitted + legacy_missing))
        slots = int(missing_counts.get("total_ev_field_slots", 0)) or int(visibility.get("total_ev_field_slots") or 0)
        visible = int(visibility.get("visible_ev_field_slots") or 0)
        rate = round(visible / slots, 4) if slots else 0.0
        total_uncertain_missing += uncertain_missing
        total_slots += slots
        missing_counter[category] = uncertain_missing
        missing_by_category[category] = {
            "field_not_emitted": field_not_emitted,
            "legacy_missing_reason": legacy_missing,
            "missing_uncertain_ev_fields": uncertain_missing,
            "total_ev_field_slots": slots,
            "missing_uncertain_share_of_slots": round(uncertain_missing / slots, 4) if slots else 0.0,
        }
        producer_level[category] = {
            "event_count": int(visibility.get("event_count") or 0),
            "total_ev_field_slots": slots,
            "visible_ev_field_slots": visible,
            "ev_visible_event_count": int(visibility.get("ev_visible_event_count") or 0),
            "ev_field_continuity_rate": rate,
            "missing_reason_counts": dict(visibility.get("missing_reason_counts", Counter()).most_common()),
        }
        if rate > best_rate:
            best_category = category
            best_rate = rate

    dominant_category, dominant_count = missing_counter.most_common(1)[0] if missing_counter else ("none", 0)
    dominant_share = round(dominant_count / total_uncertain_missing, 4) if total_uncertain_missing else 0.0
    return {
        "ev_field_missing_by_event_category": missing_by_category,
        "dominant_missing_producer": {
            "event_category": dominant_category,
            "missing_uncertain_ev_fields": int(dominant_count),
            "share": dominant_share,
        },
        "producer_missing_share": {
            category: round(count / total_uncertain_missing, 4) if total_uncertain_missing else 0.0
            for category, count in missing_counter.most_common()
        },
        "ev_producer_observability_quality": _producer_quality(
            total_slots=total_slots,
            uncertain_missing_total=total_uncertain_missing,
            dominant_category=dominant_category,
            dominant_share=dominant_share,
            best_rate=best_rate,
        ),
        "producer_level_ev_visibility": {
            "best_ev_continuity_producer": {
                "event_category": best_category,
                "ev_field_continuity_rate": best_rate,
            },
            "by_event_category": producer_level,
        },
    }


def _dominant_context(crosstabs: dict[str, dict[str, Counter[str]]], total_nulls: int) -> dict[str, Any]:
    dominant = {
        "dimension": "none",
        "context": UNKNOWN_CONTEXT,
        "reason": "no_ev_null_evidence",
        "count": 0,
        "share": 0.0,
    }
    if total_nulls <= 0:
        return dominant
    for dimension, table in crosstabs.items():
        for context, counts in table.items():
            for reason, count in counts.items():
                if count > dominant["count"]:
                    dominant = {
                        "dimension": dimension,
                        "context": context,
                        "reason": reason,
                        "count": int(count),
                        "share": round(count / total_nulls, 4),
                    }
    return dominant


def _root_cause_confidence(total_nulls: int, legacy_count: int, dominant: dict[str, Any]) -> str:
    if total_nulls <= 0:
        return "NO_EVIDENCE"
    legacy_rate = legacy_count / total_nulls
    dominant_share = float(dominant.get("share") or 0.0)
    dominant_reason = str(dominant.get("reason") or "")
    if dominant_reason == "legacy_missing_reason" or legacy_rate >= 0.5:
        return "LOW_UNCERTAIN_LEGACY_HEAVY"
    if dominant_share >= 0.5:
        return "MEDIUM_CONTEXT_ALIGNED"
    return "LOW_MIXED_CONTEXT"


def _cross_tabs(window_events: list[dict[str, Any]]) -> dict[str, Any]:
    if not window_events:
        return _empty_crosstab()

    by_lifecycle: dict[str, Counter[str]] = {}
    by_stage: dict[str, Counter[str]] = {}
    by_block_reason: dict[str, Counter[str]] = {}
    by_market_readiness: dict[str, Counter[str]] = {}
    by_orderbook_state: dict[str, Counter[str]] = {}
    total_nulls = 0
    legacy_count = 0

    for event in window_events:
        contexts = {
            "lifecycle_phase": event["lifecycle_phase"] or UNKNOWN_CONTEXT,
            "candidate_block_stage": event["candidate_block_stage"] or UNKNOWN_CONTEXT,
            "candidate_block_reason": event["candidate_block_reason"] or UNKNOWN_CONTEXT,
            "market_readiness_state": event["market_readiness_state"] or UNKNOWN_CONTEXT,
            "orderbook_state_classification": event["orderbook_state_classification"] or UNKNOWN_CONTEXT,
        }
        for field in EV_COMPONENT_FIELDS:
            reason = event["fields"][field]["null_reason"]
            if not reason:
                continue
            total_nulls += 1
            if reason == "legacy_missing_reason":
                legacy_count += 1
            _increment_crosstab(by_lifecycle, contexts["lifecycle_phase"], reason)
            _increment_crosstab(by_stage, contexts["candidate_block_stage"], reason)
            _increment_crosstab(by_block_reason, contexts["candidate_block_reason"], reason)
            _increment_crosstab(by_market_readiness, contexts["market_readiness_state"], reason)
            _increment_crosstab(by_orderbook_state, contexts["orderbook_state_classification"], reason)

    raw_crosstabs = {
        "lifecycle_phase": by_lifecycle,
        "candidate_block_stage": by_stage,
        "candidate_block_reason": by_block_reason,
        "market_readiness_state": by_market_readiness,
        "orderbook_state_classification": by_orderbook_state,
    }
    dominant = _dominant_context(raw_crosstabs, total_nulls)
    return {
        "ev_null_by_lifecycle_phase": _crosstab_dict(by_lifecycle),
        "ev_null_by_block_stage": _crosstab_dict(by_stage),
        "ev_null_by_block_reason": _crosstab_dict(by_block_reason),
        "ev_null_by_market_readiness": _crosstab_dict(by_market_readiness),
        "ev_null_by_orderbook_state": _crosstab_dict(by_orderbook_state),
        "dominant_ev_blindness_context": dominant,
        "ev_blindness_root_cause_confidence": _root_cause_confidence(total_nulls, legacy_count, dominant),
    }


def _empty_producer_attribution() -> dict[str, Any]:
    return {
        "ev_field_missing_by_event_category": {},
        "dominant_missing_producer": {
            "event_category": "none",
            "missing_uncertain_ev_fields": 0,
            "share": 0.0,
        },
        "producer_missing_share": {},
        "ev_producer_observability_quality": "NO_PRODUCER_EVIDENCE",
        "producer_level_ev_visibility": {},
    }


def _producer_quality(
    *,
    total_slots: int,
    uncertain_missing_total: int,
    dominant_category: str,
    dominant_share: float,
    best_rate: float,
) -> str:
    if total_slots <= 0:
        return "NO_PRODUCER_EVIDENCE"
    if best_rate >= 0.75:
        return "HAS_EV_PRODUCER_CONTINUITY"
    if dominant_category == "market_snapshots" and dominant_share >= 0.5:
        return "SNAPSHOT_EV_FIELD_GAP"
    if dominant_category in {"execution_log", "risk_log", "system_health", "trade_journal"} and dominant_share >= 0.5:
        return "TELEMETRY_EV_FIELD_GAP"
    if uncertain_missing_total / total_slots >= 0.5:
        return "PRODUCER_MISSING_REASON_HEAVY"
    if best_rate == 0.0:
        return "EV_BLIND_ALL_PRODUCERS"
    return "MIXED_PRODUCER_OBSERVABILITY"


def _producer_attribution(window_events: list[dict[str, Any]]) -> dict[str, Any]:
    if not window_events:
        return _empty_producer_attribution()

    stats: dict[str, dict[str, Any]] = {}
    total_slots = 0
    uncertain_missing_total = 0
    for event in window_events:
        category = event.get("event_category") or "unknown"
        if category not in stats:
            stats[category] = {
                "event_count": 0,
                "total_ev_field_slots": 0,
                "visible_ev_field_slots": 0,
                "ev_visible_event_count": 0,
                "missing_reason_counts": Counter(),
                "field_not_emitted": 0,
                "legacy_missing_reason": 0,
            }
        bucket = stats[category]
        bucket["event_count"] += 1
        any_visible = False
        for field in EV_COMPONENT_FIELDS:
            total_slots += 1
            bucket["total_ev_field_slots"] += 1
            status = event["fields"][field]
            if status["available"]:
                bucket["visible_ev_field_slots"] += 1
                any_visible = True
                continue
            reason = status["null_reason"] or "legacy_missing_reason"
            bucket["missing_reason_counts"][reason] += 1
            if reason in UNCERTAIN_MISSING_REASONS:
                bucket[reason] += 1
                uncertain_missing_total += 1
        if any_visible:
            bucket["ev_visible_event_count"] += 1

    producer_level: dict[str, Any] = {}
    missing_by_category: dict[str, Any] = {}
    missing_counter: Counter[str] = Counter()
    best_category = "none"
    best_rate = 0.0
    for category, bucket in sorted(stats.items()):
        total = int(bucket["total_ev_field_slots"])
        visible = int(bucket["visible_ev_field_slots"])
        rate = round(visible / total, 4) if total else 0.0
        uncertain_missing = int(bucket["field_not_emitted"]) + int(bucket["legacy_missing_reason"])
        producer_level[category] = {
            "event_count": int(bucket["event_count"]),
            "total_ev_field_slots": total,
            "visible_ev_field_slots": visible,
            "ev_visible_event_count": int(bucket["ev_visible_event_count"]),
            "ev_field_continuity_rate": rate,
            "missing_reason_counts": dict(bucket["missing_reason_counts"].most_common()),
        }
        missing_by_category[category] = {
            "field_not_emitted": int(bucket["field_not_emitted"]),
            "legacy_missing_reason": int(bucket["legacy_missing_reason"]),
            "missing_uncertain_ev_fields": uncertain_missing,
            "total_ev_field_slots": total,
            "missing_uncertain_share_of_slots": round(uncertain_missing / total, 4) if total else 0.0,
        }
        missing_counter[category] = uncertain_missing
        if rate > best_rate:
            best_category = category
            best_rate = rate

    dominant_category, dominant_count = missing_counter.most_common(1)[0] if missing_counter else ("none", 0)
    dominant_share = round(dominant_count / uncertain_missing_total, 4) if uncertain_missing_total else 0.0
    producer_missing_share = {
        category: round(count / uncertain_missing_total, 4) if uncertain_missing_total else 0.0
        for category, count in missing_counter.most_common()
    }
    return {
        "ev_field_missing_by_event_category": missing_by_category,
        "dominant_missing_producer": {
            "event_category": dominant_category,
            "missing_uncertain_ev_fields": int(dominant_count),
            "share": dominant_share,
        },
        "producer_missing_share": producer_missing_share,
        "ev_producer_observability_quality": _producer_quality(
            total_slots=total_slots,
            uncertain_missing_total=uncertain_missing_total,
            dominant_category=dominant_category,
            dominant_share=dominant_share,
            best_rate=best_rate,
        ),
        "producer_level_ev_visibility": {
            "best_ev_continuity_producer": {
                "event_category": best_category,
                "ev_field_continuity_rate": best_rate,
            },
            "by_event_category": producer_level,
        },
    }


def _coverage_row(chain: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    window_events = _matching_window_events(chain, events)
    event_count = len(window_events)
    any_visible_events = [event for event in window_events if event["any_ev_component_visible"]]
    visible_duration_ms = _duration_ms(any_visible_events)
    total_slots = max(1, event_count * len(EV_COMPONENT_FIELDS))
    available_slots = 0
    field_rates: dict[str, Any] = {}
    dropout_reasons: dict[str, str] = {}
    dropout_timing_ms: dict[str, float | None] = {}
    never_visible_reasons: dict[str, str] = {}
    null_reason_counts: Counter[str] = Counter()

    for field in EV_COMPONENT_FIELDS:
        available_count = sum(1 for event in window_events if event["fields"][field]["available"])
        available_slots += available_count
        field_rates[field] = {
            "available_events": available_count,
            "total_events": event_count,
            "continuity_rate": round(available_count / event_count, 4) if event_count else 0.0,
        }
        dropout_reason, dropout_ms = _first_dropout_reason(window_events, field)
        dropout_reasons[field] = dropout_reason
        dropout_timing_ms[field] = dropout_ms
        if available_count == 0:
            never_visible_reasons[field] = _never_visible_reason(window_events, field)
        for event in window_events:
            reason = event["fields"][field]["null_reason"]
            if reason:
                null_reason_counts[reason] += 1

    state, quality, sparse_reason = _classify_visibility(
        event_count=event_count,
        any_visible_count=len(any_visible_events),
        field_dropout_reasons=dropout_reasons,
    )
    dominant_dropout_reason = ""
    for reason in dropout_reasons.values():
        if reason:
            dominant_dropout_reason = reason
            break
    if not dominant_dropout_reason and never_visible_reasons:
        dominant_dropout_reason = Counter(never_visible_reasons.values()).most_common(1)[0][0]
    if not dominant_dropout_reason and null_reason_counts:
        dominant_dropout_reason = null_reason_counts.most_common(1)[0][0]
    if not dominant_dropout_reason:
        dominant_dropout_reason = "no_dropout_observed"
    cross_tabs = _cross_tabs(window_events)
    producer_attribution = _producer_attribution(window_events)
    lifecycle_trace = _candidate_lifecycle_trace(chain, window_events, visible_duration_ms)
    envelope_coverage = _candidate_trace_envelope_coverage(window_events)
    identity_upgrade = _candidate_identity_upgrade_requirements(window_events, lifecycle_trace)
    risk_layer_gap = _risk_layer_gap(window_events)
    model_state_gap = _model_state_gap_report(window_events, lifecycle_trace)
    model_attempt_gate = _model_attempt_gate_report(window_events, lifecycle_trace, model_state_gap)

    return {
        "continuity_chain_id": chain["continuity_chain_id"],
        "candidate_id": chain.get("candidate_id", ""),
        "signal_id": chain.get("signal_id", ""),
        "asset": chain.get("asset", ""),
        "market_id": chain.get("market_id", ""),
        "continuity_status": chain.get("continuity_status", ""),
        "continuity_confidence": chain.get("continuity_confidence", ""),
        "candidate_survival_ms": chain.get("candidate_survival_ms", 0.0),
        "candidate_terminal_state": chain.get("candidate_terminal_state", ""),
        "window_event_count": event_count,
        "ev_visible_event_count": len(any_visible_events),
        "ev_field_continuity_rate": round(available_slots / total_slots, 4),
        "ev_visibility_duration_ms": round(visible_duration_ms, 3),
        "ev_field_dropout_reason": dominant_dropout_reason,
        "ev_observability_quality": quality,
        "candidate_ev_visibility_state": state,
        "sparse_ev_path_reason": sparse_reason,
        "field_continuity": field_rates,
        "field_dropout_reasons": dropout_reasons,
        "field_dropout_timing_ms": dropout_timing_ms,
        "field_never_visible_reasons": never_visible_reasons,
        "null_reason_counts": dict(null_reason_counts.most_common()),
        "ev_candidate_lifecycle_trace": lifecycle_trace,
        "candidate_trace_envelope_coverage": envelope_coverage,
        "candidate_identity_upgrade_requirements": identity_upgrade,
        "risk_layer_envelope_gap": risk_layer_gap,
        "model_state_gap_report": model_state_gap,
        "model_attempt_gate_report": model_attempt_gate,
        **lifecycle_trace,
        **{
            "envelope_readiness_score": envelope_coverage["envelope_readiness_score"],
            "weakest_envelope_producer": envelope_coverage["weakest_envelope_producer"],
        },
        **identity_upgrade,
        **risk_layer_gap,
        **model_state_gap,
        **model_attempt_gate,
        **cross_tabs,
        **producer_attribution,
        "compact_events": [_compact_event(event) for event in window_events[:16]],
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    state_counts: Counter[str] = Counter()
    quality_counts: Counter[str] = Counter()
    dropout_counts: Counter[str] = Counter()
    sparse_counts: Counter[str] = Counter()
    null_counts: Counter[str] = Counter()
    by_lifecycle: dict[str, Counter[str]] = {}
    by_stage: dict[str, Counter[str]] = {}
    by_block_reason: dict[str, Counter[str]] = {}
    by_market_readiness: dict[str, Counter[str]] = {}
    by_orderbook_state: dict[str, Counter[str]] = {}
    producer_missing: dict[str, Counter[str]] = {}
    producer_visibility: dict[str, dict[str, Any]] = {}
    identity_by_producer_raw: dict[str, Counter[str]] = {}
    transition_identity_raw: dict[str, Counter[str]] = {}
    envelope_raw: dict[str, Counter[str]] = {}
    missing_direct_identity_fields: Counter[str] = Counter()
    missing_strong_identity_fields: Counter[str] = Counter()
    identity_upgrade_path_counts: Counter[str] = Counter()
    risk_gap_counts: Counter[str] = Counter()
    risk_gap_reason_counts: Counter[str] = Counter()
    decision_to_risk_boundary_counts: Counter[str] = Counter()
    pre_risk_block_cause_counts: Counter[str] = Counter()
    model_state_gap_counts: Counter[str] = Counter()
    probability_state_gap_counts: Counter[str] = Counter()
    fair_value_state_gap_counts: Counter[str] = Counter()
    ev_state_gap_counts: Counter[str] = Counter()
    model_attempt_gate_counts: Counter[str] = Counter()
    decision_to_risk_quality_counts: Counter[str] = Counter()
    risk_to_execution_quality_counts: Counter[str] = Counter()
    risk_block_visibility_counts: Counter[str] = Counter()
    risk_readiness_scores: list[float] = []
    risk_reachable_count = 0
    risk_serialization_visible_count = 0
    pre_risk_ev_related_count = 0
    pre_risk_microstructure_related_count = 0
    pre_risk_timing_related_count = 0
    pre_risk_identity_related_count = 0
    pre_risk_unknown_count = 0
    model_attempt_visible_count = 0
    model_output_serialized_count = 0
    identity_blocked_model_link_count = 0
    model_attempt_eligible_count = 0
    model_gate_microstructure_count = 0
    model_gate_timing_count = 0
    model_gate_identity_count = 0
    model_gate_unknown_count = 0
    first_phase_counts: Counter[str] = Counter()
    last_phase_counts: Counter[str] = Counter()
    disappearance_phase_counts: Counter[str] = Counter()
    disappearance_reason_counts: Counter[str] = Counter()
    trace_break_phase_counts: Counter[str] = Counter()
    handoff_quality_counts: Counter[str] = Counter()
    lifecycle_quality_counts: Counter[str] = Counter()
    trace_confidence_counts: Counter[str] = Counter()
    identity_fragmentation_count = 0
    propagation_gap_count = 0
    lifecycle_interruption_count = 0
    candidate_seen_but_never_evaluable_count = 0
    candidate_blocked_before_ev_count = 0
    ev_attempted_but_not_visible_count = 0
    ev_visibility_attempted_count = 0
    ev_visibility_confirmed_count = 0
    rates: list[float] = []
    visibility_durations: list[float] = []
    lifecycle_visibility_scores: list[float] = []
    continuity_survival_rates: list[float] = []
    survival_visible_pairs: list[dict[str, Any]] = []
    for row in rows:
        state_counts[row["candidate_ev_visibility_state"]] += 1
        quality_counts[row["ev_observability_quality"]] += 1
        dropout_counts[row["ev_field_dropout_reason"]] += 1
        sparse_counts[row["sparse_ev_path_reason"]] += 1
        rates.append(float(row["ev_field_continuity_rate"]))
        visibility_durations.append(float(row["ev_visibility_duration_ms"]))
        lifecycle_visibility_scores.append(float(row.get("ev_lifecycle_visibility_score") or 0.0))
        continuity_survival_rates.append(float(row.get("continuity_survival_rate") or 0.0))
        first_phase_counts[str(row.get("first_ev_visible_phase") or "unknown")] += 1
        last_phase_counts[str(row.get("last_ev_visible_phase") or "unknown")] += 1
        disappearance_phase_counts[str(row.get("ev_disappearance_phase") or "unknown")] += 1
        disappearance_reason_counts[str(row.get("ev_disappearance_reason") or "unknown")] += 1
        trace_break_phase_counts[str(row.get("ev_trace_break_phase") or "unknown")] += 1
        handoff_quality_counts[str(row.get("producer_handoff_quality") or "unknown")] += 1
        lifecycle_quality_counts[str(row.get("lifecycle_observability_quality") or "unknown")] += 1
        trace_confidence_counts[str(row.get("candidate_trace_confidence") or "UNKNOWN")] += 1
        identity_fragmentation_count += int(bool(row.get("identity_fragmentation_detected")))
        propagation_gap_count += int(bool(row.get("propagation_gap_detected")))
        lifecycle_interruption_count += int(bool(row.get("lifecycle_propagation_interruption")))
        candidate_seen_but_never_evaluable_count += int(bool(row.get("candidate_seen_but_never_evaluable")))
        candidate_blocked_before_ev_count += int(bool(row.get("candidate_blocked_before_ev")))
        ev_attempted_but_not_visible_count += int(bool(row.get("ev_attempted_but_not_visible")))
        ev_visibility_attempted_count += int(bool(row.get("ev_visibility_attempted")))
        ev_visibility_confirmed_count += int(bool(row.get("ev_visibility_confirmed")))
        survival_visible_pairs.append({
            "continuity_chain_id": row["continuity_chain_id"],
            "candidate_survival_ms": row["candidate_survival_ms"],
            "ev_visibility_duration_ms": row["ev_visibility_duration_ms"],
            "candidate_ev_visibility_state": row["candidate_ev_visibility_state"],
            "ev_lifecycle_visibility_score": row.get("ev_lifecycle_visibility_score", 0.0),
            "producer_handoff_quality": row.get("producer_handoff_quality", ""),
            "ev_trace_break_phase": row.get("ev_trace_break_phase", ""),
        })
        for reason, count in row["null_reason_counts"].items():
            null_counts[reason] += int(count)
        _merge_crosstab(by_lifecycle, row.get("ev_null_by_lifecycle_phase", {}))
        _merge_crosstab(by_stage, row.get("ev_null_by_block_stage", {}))
        _merge_crosstab(by_block_reason, row.get("ev_null_by_block_reason", {}))
        _merge_crosstab(by_market_readiness, row.get("ev_null_by_market_readiness", {}))
        _merge_crosstab(by_orderbook_state, row.get("ev_null_by_orderbook_state", {}))
        _merge_producer_missing(producer_missing, row.get("ev_field_missing_by_event_category", {}))
        _merge_producer_visibility(producer_visibility, row.get("producer_level_ev_visibility", {}))
        _merge_identity_table(identity_by_producer_raw, row.get("identity_confidence_by_producer", {}))
        _merge_identity_table(transition_identity_raw, row.get("producer_transition_identity_gap_tables", {}))
        _merge_envelope_coverage(envelope_raw, row.get("candidate_trace_envelope_coverage", {}))
        for field in row.get("missing_fields_preventing_direct_identity", []):
            missing_direct_identity_fields[str(field)] += 1
        for field in row.get("missing_fields_preventing_strong_identity", []):
            missing_strong_identity_fields[str(field)] += 1
        identity_upgrade_path_counts[str(row.get("candidate_identity_upgrade_path") or "unknown")] += 1
        risk_gap_counts["risk_log_identity_missing_count"] += int(bool(row.get("risk_log_identity_missing")))
        risk_gap_counts["risk_log_market_key_missing_count"] += int(bool(row.get("risk_log_market_key_missing")))
        risk_gap_counts["risk_log_lifecycle_phase_missing_count"] += int(bool(row.get("risk_log_lifecycle_phase_missing")))
        risk_gap_counts["risk_log_risk_state_missing_count"] += int(bool(row.get("risk_log_risk_state_missing")))
        risk_gap_counts["no_risk_event_exists_count"] += int(bool(row.get("no_risk_event_exists")))
        risk_gap_counts["risk_event_exists_but_lacks_candidate_identity_count"] += int(bool(row.get("risk_event_exists_but_lacks_candidate_identity")))
        risk_gap_counts["risk_event_exists_but_lacks_risk_state_count"] += int(bool(row.get("risk_event_exists_but_lacks_risk_state")))
        risk_gap_counts["candidate_blocked_before_risk_visibility_count"] += int(bool(row.get("candidate_blocked_before_risk_visibility")))
        risk_gap_counts["ev_visible_before_risk_missing_after_count"] += int(bool(row.get("ev_visible_before_risk_missing_after")))
        risk_gap_counts["risk_producer_not_responsible_count"] += int(bool(row.get("risk_producer_not_responsible")))
        risk_gap_counts["stale_legacy_schema_count"] += int(bool(row.get("stale_legacy_schema")))
        risk_gap_reason_counts[str(row.get("weakest_risk_gap_reason") or "unknown")] += 1
        boundary_category = str(row.get("decision_to_risk_boundary_category") or "LEGACY_OR_UNKNOWN")
        decision_to_risk_boundary_counts[boundary_category] += 1
        risk_reachable_count += int(bool(row.get("risk_reachable")))
        risk_serialization_visible_count += int(bool(row.get("risk_serialization_visible")))
        if boundary_category == "BLOCKED_BEFORE_RISK":
            causes = [
                str(cause)
                for cause in row.get("pre_risk_block_causes", [])
                if str(cause) in PRE_RISK_BLOCK_CAUSES
            ] or ["UNKNOWN_PRE_RISK_BLOCK"]
            for cause in causes:
                pre_risk_block_cause_counts[cause] += 1
            cause_set = set(causes)
            pre_risk_ev_related_count += int(bool(cause_set & EV_RELATED_PRE_RISK_CAUSES))
            pre_risk_microstructure_related_count += int(bool(cause_set & MICROSTRUCTURE_RELATED_PRE_RISK_CAUSES))
            pre_risk_timing_related_count += int(bool(cause_set & TIMING_RELATED_PRE_RISK_CAUSES))
            pre_risk_identity_related_count += int(bool(cause_set & IDENTITY_RELATED_PRE_RISK_CAUSES))
            pre_risk_unknown_count += int("UNKNOWN_PRE_RISK_BLOCK" in cause_set)
        for gap, counter in (
            (row.get("dominant_model_state_gap"), model_state_gap_counts),
            (row.get("probability_state_gap"), probability_state_gap_counts),
            (row.get("fair_value_state_gap"), fair_value_state_gap_counts),
            (row.get("ev_state_gap"), ev_state_gap_counts),
        ):
            gap_text = str(gap or "")
            if gap_text in MODEL_STATE_GAP_CATEGORIES:
                counter[gap_text] += 1
        model_attempt_visible_count += int(bool(row.get("model_attempt_visible")))
        model_output_serialized_count += int(bool(row.get("model_output_serialized")))
        identity_blocked_model_link_count += int(bool(row.get("identity_blocked_model_link")))
        model_attempt_eligible_count += int(bool(row.get("model_attempt_eligible")))
        gates = [
            str(gate)
            for gate in row.get("model_attempt_gates", [])
            if str(gate) in MODEL_ATTEMPT_GATE_CAUSES
        ]
        for gate in gates:
            model_attempt_gate_counts[gate] += 1
        gate_set = set(gates)
        model_gate_microstructure_count += int(bool(gate_set & MODEL_GATE_MICROSTRUCTURE_CAUSES))
        model_gate_timing_count += int(bool(gate_set & MODEL_GATE_TIMING_CAUSES))
        model_gate_identity_count += int(bool(gate_set & MODEL_GATE_IDENTITY_CAUSES))
        model_gate_unknown_count += int("MODEL_GATE_UNKNOWN" in gate_set)
        decision_to_risk_quality_counts[str(row.get("decision_to_risk_handoff_quality") or "unknown")] += 1
        risk_to_execution_quality_counts[str(row.get("risk_to_execution_handoff_quality") or "unknown")] += 1
        risk_block_visibility_counts[str(row.get("risk_layer_block_visibility") or "unknown")] += 1
        risk_readiness_scores.append(float(row.get("risk_layer_trace_readiness") or 0.0))
    raw_crosstabs = {
        "lifecycle_phase": by_lifecycle,
        "candidate_block_stage": by_stage,
        "candidate_block_reason": by_block_reason,
        "market_readiness_state": by_market_readiness,
        "orderbook_state_classification": by_orderbook_state,
    }
    total_nulls = sum(null_counts.values())
    dominant_blindness_context = _dominant_context(raw_crosstabs, total_nulls)
    producer = _producer_summary(producer_missing, producer_visibility)
    identity_by_producer = _identity_table_dict(identity_by_producer_raw)
    transition_identity = _transition_identity_table_dict(transition_identity_raw)
    identity_gap_by_producer = {
        producer_name: {
            "identity_gap_count": stats["identity_gap_count"],
            "identity_gap_share": stats["identity_gap_share"],
            "identity_link_quality": stats["identity_link_quality"],
        }
        for producer_name, stats in identity_by_producer.items()
    }
    proxy_dependency_by_producer = {
        producer_name: {
            "proxy_dependency_count": stats["proxy_dependency_count"],
            "proxy_dependency_rate": stats["proxy_dependency_rate"],
        }
        for producer_name, stats in identity_by_producer.items()
    }
    direct_identity_absence_by_producer = {
        producer_name: {
            "direct_identity_absence_count": stats["direct_identity_absence_count"],
            "direct_identity_absence_rate": _identity_rate(stats["direct_identity_absence_count"], stats["total_candidates"]),
        }
        for producer_name, stats in identity_by_producer.items()
    }
    strongest_available_identity_by_transition = {
        transition: stats["strongest_available_identity"]
        for transition, stats in transition_identity.items()
    }
    weakest_identity_transition = _dominant_identity_table_item(
        transition_identity,
        metric="strong_or_direct_rate",
        lowest=True,
    )
    dominant_identity_failure_transition = _dominant_identity_table_item(
        transition_identity,
        metric="identity_gap_count",
    )
    envelope_summary = _envelope_readiness_summary(envelope_raw)
    direct_identity_blocker_rank = [
        {"field": field, "missing_count": int(count), "share": _identity_rate(int(count), len(rows))}
        for field, count in missing_direct_identity_fields.most_common()
    ]
    strong_identity_blocker_rank = [
        {"field": field, "missing_count": int(count), "share": _identity_rate(int(count), len(rows))}
        for field, count in missing_strong_identity_fields.most_common()
    ]
    combined_identity_blockers = missing_direct_identity_fields + missing_strong_identity_fields
    highest_impact_identity_field = {
        "field": combined_identity_blockers.most_common(1)[0][0],
        "blocked_candidate_field_mentions": int(combined_identity_blockers.most_common(1)[0][1]),
        "direct_missing_count": int(missing_direct_identity_fields.get(combined_identity_blockers.most_common(1)[0][0], 0)),
        "strong_missing_count": int(missing_strong_identity_fields.get(combined_identity_blockers.most_common(1)[0][0], 0)),
    } if combined_identity_blockers else {
        "field": "none",
        "blocked_candidate_field_mentions": 0,
        "direct_missing_count": 0,
        "strong_missing_count": 0,
    }
    positive_blockers = [(field, count) for field, count in combined_identity_blockers.items() if count > 0]
    easiest_pair = sorted(
        positive_blockers,
        key=lambda item: (item[1], IDENTITY_UPGRADE_FIELDS.index(item[0]) if item[0] in IDENTITY_UPGRADE_FIELDS else 999),
    )[0] if positive_blockers else ("none", 0)
    easiest_identity_upgrade_field = {
        "field": easiest_pair[0],
        "blocked_candidate_field_mentions": int(easiest_pair[1]),
        "interpretation": "lowest observed missing-field count among canonical identity blockers; hypothetical only",
    }
    weakest_risk_gap_reason = risk_gap_reason_counts.most_common(1)[0][0] if risk_gap_reason_counts else "none"
    dominant_risk_visibility_failure = risk_gap_reason_counts.most_common(1)[0][0] if risk_gap_reason_counts else "none"
    for category in DECISION_TO_RISK_BOUNDARY_CATEGORIES:
        decision_to_risk_boundary_counts.setdefault(category, 0)
    for cause in PRE_RISK_BLOCK_CAUSES:
        pre_risk_block_cause_counts.setdefault(cause, 0)
    for gap in MODEL_STATE_GAP_CATEGORIES:
        model_state_gap_counts.setdefault(gap, 0)
        probability_state_gap_counts.setdefault(gap, 0)
        fair_value_state_gap_counts.setdefault(gap, 0)
        ev_state_gap_counts.setdefault(gap, 0)
    for gate in MODEL_ATTEMPT_GATE_CAUSES:
        model_attempt_gate_counts.setdefault(gate, 0)
    total_boundary_candidates = len(rows)
    total_pre_risk_blocks = int(decision_to_risk_boundary_counts["BLOCKED_BEFORE_RISK"])
    dominant_boundary_failure = (
        decision_to_risk_boundary_counts.most_common(1)[0][0] if decision_to_risk_boundary_counts else "LEGACY_OR_UNKNOWN"
    )
    dominant_pre_risk_block_cause = (
        pre_risk_block_cause_counts.most_common(1)[0][0] if total_pre_risk_blocks else "none"
    )
    dominant_model_state_gap = model_state_gap_counts.most_common(1)[0][0] if rows else "none"
    total_model_gated_candidates = (
        int(model_state_gap_counts.get("MODEL_NOT_ATTEMPTED", 0))
        + int(model_state_gap_counts.get("BLOCKED_BEFORE_MODEL", 0))
    )
    dominant_model_attempt_gate = model_attempt_gate_counts.most_common(1)[0][0] if total_model_gated_candidates else "none"
    pre_risk_block_cause_share = {
        cause: round(count / total_pre_risk_blocks, 4) if total_pre_risk_blocks else 0.0
        for cause, count in pre_risk_block_cause_counts.most_common()
    }
    for key in (
        "risk_log_identity_missing_count",
        "risk_log_market_key_missing_count",
        "risk_log_lifecycle_phase_missing_count",
        "risk_log_risk_state_missing_count",
        "no_risk_event_exists_count",
        "risk_event_exists_but_lacks_candidate_identity_count",
        "risk_event_exists_but_lacks_risk_state_count",
        "candidate_blocked_before_risk_visibility_count",
        "ev_visible_before_risk_missing_after_count",
        "risk_producer_not_responsible_count",
        "stale_legacy_schema_count",
    ):
        risk_gap_counts.setdefault(key, 0)
    risk_needed_fields = []
    for field, count_key in (
        ("candidate_trace_id", "risk_log_identity_missing_count"),
        ("market_key", "risk_log_market_key_missing_count"),
        ("lifecycle_phase", "risk_log_lifecycle_phase_missing_count"),
        ("risk_state", "risk_log_risk_state_missing_count"),
        ("parent_candidate_trace_id", "risk_log_identity_missing_count"),
        ("trace_link_reason", "risk_log_identity_missing_count"),
    ):
        if risk_gap_counts.get(count_key, 0):
            risk_needed_fields.append(field)
    risk_layer_report = {
        **{key: int(value) for key, value in risk_gap_counts.items()},
        "decision_to_risk_handoff_quality": dict(decision_to_risk_quality_counts.most_common()),
        "risk_to_execution_handoff_quality": dict(risk_to_execution_quality_counts.most_common()),
        "risk_layer_trace_readiness": round(sum(risk_readiness_scores) / len(risk_readiness_scores), 4) if risk_readiness_scores else 0.0,
        "risk_layer_block_visibility": dict(risk_block_visibility_counts.most_common()),
        "weakest_risk_gap_reason": weakest_risk_gap_reason,
        "dominant_risk_visibility_failure": dominant_risk_visibility_failure,
        "risk_visibility_failure_counts": dict(risk_gap_reason_counts.most_common()),
        "runtime_observability_fields_needed_for_risk_layer": risk_needed_fields,
        "transition_analysis": {
            "decision_log->risk_log": dict(decision_to_risk_quality_counts.most_common()),
            "risk_log->execution_log": dict(risk_to_execution_quality_counts.most_common()),
        },
        "decision_to_risk_boundary_categories": list(DECISION_TO_RISK_BOUNDARY_CATEGORIES),
        "decision_to_risk_boundary_counts": dict(decision_to_risk_boundary_counts.most_common()),
        "risk_reachability_rate": round(risk_reachable_count / total_boundary_candidates, 4) if total_boundary_candidates else 0.0,
        "risk_serialization_visibility_rate": round(risk_serialization_visible_count / total_boundary_candidates, 4)
        if total_boundary_candidates
        else 0.0,
        "pre_risk_block_share": round(decision_to_risk_boundary_counts["BLOCKED_BEFORE_RISK"] / total_boundary_candidates, 4)
        if total_boundary_candidates
        else 0.0,
        "no_decision_evidence_share": round(decision_to_risk_boundary_counts["NO_DECISION_EVIDENCE"] / total_boundary_candidates, 4)
        if total_boundary_candidates
        else 0.0,
        "dominant_decision_to_risk_boundary_failure": dominant_boundary_failure,
        "decision_to_risk_boundary_interpretation": (
            "risk reach is counted only when a serialized risk event or explicit risk-state evidence exists; "
            "absence of a risk event is not treated as a risk-layer failure by itself"
        ),
        "pre_risk_block_cause_taxonomy": list(PRE_RISK_BLOCK_CAUSES),
        "pre_risk_block_cause_counts": dict(pre_risk_block_cause_counts.most_common()),
        "dominant_pre_risk_block_cause": dominant_pre_risk_block_cause,
        "pre_risk_block_cause_share": pre_risk_block_cause_share,
        "ev_related_pre_risk_block_share": round(pre_risk_ev_related_count / total_pre_risk_blocks, 4)
        if total_pre_risk_blocks
        else 0.0,
        "ev_related_pre_risk_block_count": pre_risk_ev_related_count,
        "microstructure_related_pre_risk_block_share": round(pre_risk_microstructure_related_count / total_pre_risk_blocks, 4)
        if total_pre_risk_blocks
        else 0.0,
        "microstructure_related_pre_risk_block_count": pre_risk_microstructure_related_count,
        "timing_related_pre_risk_block_share": round(pre_risk_timing_related_count / total_pre_risk_blocks, 4)
        if total_pre_risk_blocks
        else 0.0,
        "timing_related_pre_risk_block_count": pre_risk_timing_related_count,
        "identity_related_pre_risk_block_share": round(pre_risk_identity_related_count / total_pre_risk_blocks, 4)
        if total_pre_risk_blocks
        else 0.0,
        "identity_related_pre_risk_block_count": pre_risk_identity_related_count,
        "unknown_pre_risk_block_share": round(pre_risk_unknown_count / total_pre_risk_blocks, 4)
        if total_pre_risk_blocks
        else 0.0,
        "unknown_pre_risk_block_count": pre_risk_unknown_count,
        "model_state_gap_taxonomy": list(MODEL_STATE_GAP_CATEGORIES),
        "model_state_gap_counts": dict(model_state_gap_counts.most_common()),
        "probability_state_gap_counts": dict(probability_state_gap_counts.most_common()),
        "fair_value_state_gap_counts": dict(fair_value_state_gap_counts.most_common()),
        "ev_state_gap_counts": dict(ev_state_gap_counts.most_common()),
        "model_attempt_visibility_rate": round(model_attempt_visible_count / total_boundary_candidates, 4)
        if total_boundary_candidates
        else 0.0,
        "model_output_serialization_rate": round(model_output_serialized_count / total_boundary_candidates, 4)
        if total_boundary_candidates
        else 0.0,
        "identity_blocked_model_link_rate": round(identity_blocked_model_link_count / total_boundary_candidates, 4)
        if total_boundary_candidates
        else 0.0,
        "model_attempt_visible_count": model_attempt_visible_count,
        "model_output_serialized_count": model_output_serialized_count,
        "identity_blocked_model_link_count": identity_blocked_model_link_count,
        "dominant_model_state_gap": dominant_model_state_gap,
        "model_attempt_gate_taxonomy": list(MODEL_ATTEMPT_GATE_CAUSES),
        "model_attempt_gate_counts": dict(model_attempt_gate_counts.most_common()),
        "dominant_model_attempt_gate": dominant_model_attempt_gate,
        "model_gate_microstructure_share": round(model_gate_microstructure_count / total_model_gated_candidates, 4)
        if total_model_gated_candidates
        else 0.0,
        "model_gate_microstructure_count": model_gate_microstructure_count,
        "model_gate_timing_share": round(model_gate_timing_count / total_model_gated_candidates, 4)
        if total_model_gated_candidates
        else 0.0,
        "model_gate_timing_count": model_gate_timing_count,
        "model_gate_identity_share": round(model_gate_identity_count / total_model_gated_candidates, 4)
        if total_model_gated_candidates
        else 0.0,
        "model_gate_identity_count": model_gate_identity_count,
        "model_gate_unknown_share": round(model_gate_unknown_count / total_model_gated_candidates, 4)
        if total_model_gated_candidates
        else 0.0,
        "model_gate_unknown_count": model_gate_unknown_count,
        "model_attempt_eligibility_rate": round(model_attempt_eligible_count / total_boundary_candidates, 4)
        if total_boundary_candidates
        else 0.0,
        "model_attempt_eligible_count": model_attempt_eligible_count,
        "identity_confidence_requirements": {
            level: list(fields)
            for level, fields in IDENTITY_CONFIDENCE_REQUIREMENTS.items()
        },
        "identity_upgrade_required_fields": list(IDENTITY_UPGRADE_FIELDS),
        "missing_fields_preventing_direct_identity": dict(missing_direct_identity_fields.most_common()),
        "missing_fields_preventing_strong_identity": dict(missing_strong_identity_fields.most_common()),
        "candidate_identity_upgrade_path_counts": dict(identity_upgrade_path_counts.most_common()),
        "easiest_identity_upgrade_field": easiest_identity_upgrade_field,
        "highest_impact_identity_field": highest_impact_identity_field,
        "direct_identity_blocker_rank": direct_identity_blocker_rank,
        "strong_identity_blocker_rank": strong_identity_blocker_rank,
        "hypothetical_identity_upgrade_impact": {
            "field_impact_counts": dict(combined_identity_blockers.most_common()),
            "rule": "hypothetical missing-field impact only; actual candidate_trace_confidence remains unchanged",
        },
        "guardrail": "offline replay observability only; does not change risk logic, sizing, execution, or runtime emission",
    }
    ev_never_visible_count = int(state_counts.get("EV_NEVER_VISIBLE", 0))
    risk_readiness = float(risk_layer_report["risk_layer_trace_readiness"])
    gap_types: list[str] = []
    if ev_never_visible_count:
        gap_types.append("field_not_emitted")
    if risk_gap_counts.get("no_risk_event_exists_count", 0):
        gap_types.append("producer_handoff_gap")
    if (
        risk_gap_counts.get("risk_event_exists_but_lacks_candidate_identity_count", 0)
        or risk_gap_counts.get("risk_event_exists_but_lacks_risk_state_count", 0)
    ):
        gap_types.append("field_not_emitted")
    if risk_readiness == 0.0 and ev_never_visible_count:
        gap_classification = "EV_AND_RISK_CHAIN_NOT_VISIBLE"
    elif ev_never_visible_count:
        gap_classification = "EV_CHAIN_NOT_VISIBLE"
    elif risk_readiness == 0.0:
        gap_classification = "RISK_CHAIN_NOT_VISIBLE"
    else:
        gap_classification = "EV_RISK_CHAIN_PARTIALLY_VISIBLE"
    ev_risk_gap_diagnostics = {
        "classification": gap_classification,
        "ev_visibility_accepted_fields": EV_VISIBILITY_ACCEPTED_FIELDS,
        "risk_layer_trace_readiness_requirements": RISK_LAYER_TRACE_REQUIREMENTS,
        "ev_never_visible_count": ev_never_visible_count,
        "risk_layer_trace_readiness": risk_readiness,
        "dominant_ev_visibility_state": state_counts.most_common(1)[0][0] if state_counts else "none",
        "dominant_risk_visibility_failure": dominant_risk_visibility_failure,
        "candidate_chain_trace_confidence_counts": dict(trace_confidence_counts.most_common()),
        "likely_gap_types": sorted(set(gap_types)) or ["insufficient_evidence"],
        "explanation": (
            "EV visibility requires one accepted EV component field in candidate-window events; "
            "risk readiness requires candidate identity, market key, lifecycle phase, and risk state in matched risk_log events. "
            "When both are absent, replay can identify the visibility gap but cannot infer hidden EV or hidden risk evaluation."
        ),
    }
    trace_summary = {
        "traceable_candidates": len(rows),
        "avg_ev_lifecycle_visibility_score": round(sum(lifecycle_visibility_scores) / len(lifecycle_visibility_scores), 4)
        if lifecycle_visibility_scores
        else 0.0,
        "avg_continuity_survival_rate": round(sum(continuity_survival_rates) / len(continuity_survival_rates), 4)
        if continuity_survival_rates
        else 0.0,
        "first_ev_visible_phase_counts": dict(first_phase_counts.most_common()),
        "last_ev_visible_phase_counts": dict(last_phase_counts.most_common()),
        "ev_disappearance_phase_counts": dict(disappearance_phase_counts.most_common()),
        "ev_disappearance_reason_counts": dict(disappearance_reason_counts.most_common()),
        "ev_trace_break_phase_counts": dict(trace_break_phase_counts.most_common()),
        "producer_handoff_quality_counts": dict(handoff_quality_counts.most_common()),
        "lifecycle_observability_quality_counts": dict(lifecycle_quality_counts.most_common()),
        "candidate_trace_confidence_counts": dict(trace_confidence_counts.most_common()),
        "identity_fragmentation_detected_count": identity_fragmentation_count,
        "propagation_gap_detected_count": propagation_gap_count,
        "lifecycle_propagation_interruption_count": lifecycle_interruption_count,
        "candidate_seen_but_never_evaluable_count": candidate_seen_but_never_evaluable_count,
        "candidate_blocked_before_ev_count": candidate_blocked_before_ev_count,
        "ev_attempted_but_not_visible_count": ev_attempted_but_not_visible_count,
        "ev_visibility_attempted_count": ev_visibility_attempted_count,
        "ev_visibility_confirmed_count": ev_visibility_confirmed_count,
        "identity_confidence_by_producer": identity_by_producer,
        "identity_gap_by_producer": identity_gap_by_producer,
        "proxy_dependency_by_producer": proxy_dependency_by_producer,
        "direct_identity_absence_by_producer": direct_identity_absence_by_producer,
        "producer_transition_identity_gap_tables": transition_identity,
        "strongest_available_identity_by_transition": strongest_available_identity_by_transition,
        "weakest_identity_transition": weakest_identity_transition,
        "dominant_identity_failure_transition": dominant_identity_failure_transition,
        **envelope_summary,
        "risk_layer_envelope_gap_report": risk_layer_report,
        **risk_layer_report,
        "ev_risk_chain_gap_diagnostics": ev_risk_gap_diagnostics,
    }
    return {
        "candidate_ev_coverage_rows": len(rows),
        "avg_ev_field_continuity_rate": round(sum(rates) / len(rates), 4) if rates else 0.0,
        "avg_ev_visibility_duration_ms": round(sum(visibility_durations) / len(visibility_durations), 3) if visibility_durations else 0.0,
        "candidate_ev_visibility_state_counts": dict(state_counts.most_common()),
        "ev_observability_quality_counts": dict(quality_counts.most_common()),
        "ev_field_dropout_reason_counts": dict(dropout_counts.most_common()),
        "sparse_ev_path_reason_counts": dict(sparse_counts.most_common()),
        "ev_null_reason_counts": dict(null_counts.most_common()),
        "ev_null_by_lifecycle_phase": _crosstab_dict(by_lifecycle),
        "ev_null_by_block_stage": _crosstab_dict(by_stage),
        "ev_null_by_block_reason": _crosstab_dict(by_block_reason),
        "ev_null_by_market_readiness": _crosstab_dict(by_market_readiness),
        "ev_null_by_orderbook_state": _crosstab_dict(by_orderbook_state),
        "dominant_ev_blindness_context": dominant_blindness_context,
        "ev_blindness_root_cause_confidence": _root_cause_confidence(
            total_nulls,
            int(null_counts.get("legacy_missing_reason", 0)),
            dominant_blindness_context,
        ),
        "ev_candidate_lifecycle_trace_summary": trace_summary,
        **trace_summary,
        "ev_risk_chain_gap_diagnostics": ev_risk_gap_diagnostics,
        "candidate_trace_envelope_spec": _candidate_trace_envelope_spec(),
        **producer,
        "candidate_survival_vs_ev_visibility": survival_visible_pairs[:50],
    }


def _lineage_confidence_from_payload(payload: dict[str, Any]) -> str:
    has_trace = bool(_raw_context_value(payload, "candidate_trace_id", "candidate_id", "signal_id"))
    has_parent = bool(_raw_context_value(payload, "parent_candidate_trace_id", "candidate_id", "signal_id", "decision_id"))
    has_market = bool(_raw_context_value(payload, "market_key", "market_id", "condition_id", "source_market_id", "market_slug", "slug"))
    has_token = bool(_raw_context_value(payload, "token_id", "clob_token_id", "yes_token_id", "no_token_id"))
    has_side = bool(_raw_context_value(payload, "side", "outcome", "token_side", "direction"))
    has_phase = bool(_raw_context_value(payload, "lifecycle_phase"))
    if has_trace and has_parent and has_market and has_token and has_side and has_phase:
        return "DIRECT"
    if has_trace and has_market and has_token and has_side and has_phase:
        return "STRONG"
    if has_trace and has_market:
        return "WEAK"
    if has_trace:
        return "PROXY"
    return "UNKNOWN"


def _identity_continuity_diagnostics_from_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    trace_producer_sets: dict[str, set[str]] = {}
    trace_confidence: dict[str, list[str]] = {}
    orphan_counts_by_producer: Counter[str] = Counter()
    trace_ids_by_producer: dict[str, set[str]] = {
        "decision_log": set(),
        "risk_log": set(),
        "execution_log": set(),
        "trade_journal": set(),
        "market_snapshots": set(),
    }
    for event in events:
        payload = _payload(event)
        producer = _text(event.get("_category") or event.get("event_category") or payload.get("producer_event_type") or payload.get("producer") or "unknown")
        trace_id = _raw_context_value(payload, "candidate_trace_id")
        confidence = _text(payload.get("lineage_confidence")).upper() or _lineage_confidence_from_payload(payload)
        if trace_id:
            trace_producer_sets.setdefault(trace_id, set()).add(producer)
            trace_confidence.setdefault(trace_id, []).append(confidence)
            if producer in trace_ids_by_producer:
                trace_ids_by_producer[producer].add(trace_id)
        else:
            orphan_counts_by_producer[producer] += 1

    decision_traces = trace_ids_by_producer["decision_log"]
    risk_traces = trace_ids_by_producer["risk_log"]
    execution_traces = trace_ids_by_producer["execution_log"]
    decision_to_risk_gap_count = len(decision_traces - risk_traces)
    risk_to_execution_gap_count = len(risk_traces - execution_traces)
    direct_chain_count = 0
    strong_chain_count = 0
    weak_chain_count = 0
    proxy_or_unknown_chain_count = 0
    deterministic_chain_count = 0
    for trace_id, producers in trace_producer_sets.items():
        confidences = trace_confidence.get(trace_id, [])
        best = "UNKNOWN"
        for level in ("DIRECT", "STRONG", "WEAK", "PROXY"):
            if level in confidences:
                best = level
                break
        if best == "DIRECT":
            direct_chain_count += 1
        elif best == "STRONG":
            strong_chain_count += 1
        elif best == "WEAK":
            weak_chain_count += 1
        else:
            proxy_or_unknown_chain_count += 1
        if "decision_log" in producers and "risk_log" in producers:
            deterministic_chain_count += 1

    total_traced_candidates = len(trace_producer_sets)
    return {
        "scope": "offline_identity_continuity_diagnostics_v1",
        "total_events_scanned": len(events),
        "total_traced_candidates": total_traced_candidates,
        "identity_continuity_score": round((direct_chain_count + strong_chain_count) / total_traced_candidates, 4) if total_traced_candidates else 0.0,
        "deterministic_chain_rate": round(deterministic_chain_count / total_traced_candidates, 4) if total_traced_candidates else 0.0,
        "deterministic_chain_count": deterministic_chain_count,
        "direct_chain_count": direct_chain_count,
        "strong_chain_count": strong_chain_count,
        "weak_chain_count": weak_chain_count,
        "proxy_or_unknown_chain_count": proxy_or_unknown_chain_count,
        "orphan_risk_count": int(orphan_counts_by_producer.get("risk_log", 0)),
        "orphan_execution_count": int(orphan_counts_by_producer.get("execution_log", 0)),
        "orphan_counts_by_producer": dict(orphan_counts_by_producer.most_common()),
        "decision_to_risk_identity_gap_count": decision_to_risk_gap_count,
        "risk_to_execution_identity_gap_count": risk_to_execution_gap_count,
        "replay_lineage_gap_rate": round((decision_to_risk_gap_count + risk_to_execution_gap_count) / max(total_traced_candidates, 1), 4),
        "producer_trace_coverage": {
            producer: len(trace_ids)
            for producer, trace_ids in sorted(trace_ids_by_producer.items())
        },
    }


def build_ev_field_coverage_report(
    *,
    base_dir: str | Path = DEFAULT_QUANT_DATA_DIR,
    date: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    since: str | None = None,
    until: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    if date:
        date_from = date_to = date
    if not date_from:
        date_from = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not date_to:
        date_to = date_from

    time_filter = build_time_filter(date_from=date_from, date_to=date_to, since=since, until=until, run_id=run_id)
    events, bad_json_lines = load_replay_events(
        base_dir=base_dir,
        date_from=date_from,
        date_to=date_to,
        since_utc=time_filter.get("since_utc"),
        until_utc=time_filter.get("until_utc"),
        run_id=run_id,
    )
    continuity_report = build_candidate_continuity_report(
        base_dir=base_dir,
        date_from=date_from,
        date_to=date_to,
        since=since,
        until=until,
        run_id=run_id,
    )
    chains = list(continuity_report.get("chains", []))
    rows = [_coverage_row(chain, events) for chain in chains]
    summary = _summary(rows)
    identity_continuity = _identity_continuity_diagnostics_from_events(events)
    post_emission_verification = _candidate_trace_id_post_emission_verification(events)
    alias_normalization_verification = _candidate_trace_alias_normalization_verification(events)
    condition_alias_discovery = _condition_identity_alias_discovery(events)
    post_condition_enrichment_verification = _post_condition_enrichment_verification(events)
    post_fallback_condition_coverage_verification = _post_fallback_condition_coverage_verification(
        post_condition_enrichment_verification,
        alias_normalization_verification,
    )
    phase2_coverage = build_phase2_coverage_from_events(events)
    dominant_causes = {
        "dropout_reasons": summary["ev_field_dropout_reason_counts"],
        "sparse_reasons": summary["sparse_ev_path_reason_counts"],
        "null_reasons": summary["ev_null_reason_counts"],
        "dominant_ev_blindness_context": summary["dominant_ev_blindness_context"],
        "ev_blindness_root_cause_confidence": summary["ev_blindness_root_cause_confidence"],
        "dominant_missing_producer": summary["dominant_missing_producer"],
        "ev_producer_observability_quality": summary["ev_producer_observability_quality"],
    }
    return {
        "generated_at_utc": _utc_now(),
        "date_from": date_from,
        "date_to": date_to,
        "run_id": run_id or "",
        "time_filter": {
            "since": since,
            "until": until,
            "since_utc": time_filter.get("since_utc").isoformat().replace("+00:00", "Z") if time_filter.get("since_utc") else None,
            "until_utc": time_filter.get("until_utc").isoformat().replace("+00:00", "Z") if time_filter.get("until_utc") else None,
            "run_id": run_id,
            "run_id_applied": bool(run_id),
            "applied": bool(time_filter.get("applied")),
            "semantics": time_filter.get("semantics"),
        },
        "scope": "offline_research_replay_only",
        "schema_version": "ev_field_coverage_v1",
        "schema_generation_version": SCHEMA_GENERATION_VERSION,
        "replay_schema_freshness": "fresh",
        "stale_schema_detected": False,
        "stale_report_reason": "",
        "normalized_ev_null_reason_schema": {
            "version": "ev_null_reason_normalization_v1",
            "categories": list(NORMALIZED_EV_NULL_REASONS),
            "rule": "explicit field null reason first, then EV/probability stage and block context, then field_not_emitted or legacy_missing_reason",
        },
        "ev_candidate_lifecycle_trace_schema": {
            "version": "ev_candidate_lifecycle_trace_v1",
            "producer_order": list(TRACE_PRODUCER_ORDER),
            "metrics": [
                "ev_lifecycle_visibility_score",
                "candidate_phase_coverage",
                "producer_handoff_quality",
                "ev_trace_break_phase",
                "continuity_survival_rate",
                "lifecycle_observability_quality",
            ],
            "rule": "offline evidence only; trace where EV visibility appears or disappears without inventing values",
        },
        "candidate_trace_confidence_schema": {
            "version": "candidate_trace_confidence_v1",
            "classes": ["DIRECT", "STRONG", "WEAK", "PROXY", "UNKNOWN"],
            "rule": "classify replay linkage confidence from direct identity matches, proxy matches, producer coverage, propagation gaps, and EV attempt evidence",
        },
        "direct_vs_proxy_identity_gap_schema": {
            "version": "direct_vs_proxy_identity_gap_tables_v1",
            "producer_transitions": list(IDENTITY_TRANSITIONS),
            "classes": list(IDENTITY_CONFIDENCE_LEVELS),
            "rule": "PROXY and WEAK are reported as uncertainty and do not count as confirmed continuity; DIRECT/STRONG remain separate from WEAK/PROXY",
        },
        "deterministic_identity_continuity_schema": {
            "version": "deterministic_replay_identity_continuity_v1",
            "canonical_fields": [
                "candidate_trace_id",
                "parent_candidate_trace_id",
                "replay_chain_id",
                "risk_trace_id",
                "execution_trace_id",
                "market_key",
                "lifecycle_instance_id",
                "inventory_context_id",
                "packet_schema_version",
            ],
            "rule": "offline-only decision->risk->execution lineage diagnostics; PROXY remains non-confirming and no EV/probability values are fabricated",
        },
        "candidate_trace_envelope_spec": summary["candidate_trace_envelope_spec"],
        "risk_layer_envelope_gap_schema": {
            "version": "risk_layer_envelope_gap_report_v1",
            "transitions": ["decision_log->risk_log", "risk_log->execution_log"],
            "rule": "offline replay evidence only; distinguish missing risk events, missing risk identity, missing risk state, pre-risk blocks, non-responsibility, and stale schemas",
        },
        "decision_to_risk_boundary_schema": {
            "version": "decision_to_risk_boundary_classification_v1",
            "categories": list(DECISION_TO_RISK_BOUNDARY_CATEGORIES),
            "rule": "classify the offline decision-to-risk boundary from serialized risk events, explicit risk-state evidence, and decision skip/block evidence without inferring risk evaluation from missing risk logs",
        },
        "pre_risk_block_cause_taxonomy_schema": {
            "version": "pre_risk_block_cause_taxonomy_v1",
            "categories": list(PRE_RISK_BLOCK_CAUSES),
            "rule": "classify BLOCKED_BEFORE_RISK candidates from visible decision_log/replay skip, block, EV-null, readiness, orderbook, spread, liquidity, timing, lifecycle, and identity-link fields only",
        },
        "model_state_attempt_emission_gap_schema": {
            "version": "model_state_attempt_vs_emission_gap_v1",
            "categories": list(MODEL_STATE_GAP_CATEGORIES),
            "rule": "classify probability, fair-value, and EV model-state gaps from visible replay fields, decision skip/block reasons, and candidate trace confidence without fabricating model outputs",
        },
        "model_attempt_gate_taxonomy_schema": {
            "version": "model_attempt_gate_taxonomy_v1",
            "categories": list(MODEL_ATTEMPT_GATE_CAUSES),
            "rule": "classify MODEL_NOT_ATTEMPTED and BLOCKED_BEFORE_MODEL candidates from visible replay gate fields only; ambiguous evidence remains MODEL_GATE_UNKNOWN",
        },
        "candidate_identity_upgrade_requirements_schema": {
            "version": "candidate_identity_upgrade_requirements_v1",
            "fields": list(IDENTITY_UPGRADE_FIELDS),
            "requirements": {
                level: list(fields)
                for level, fields in IDENTITY_CONFIDENCE_REQUIREMENTS.items()
            },
            "rule": "offline hypothetical identity-readiness audit only; actual candidate_trace_confidence is not upgraded without evidence",
        },
        "candidate_trace_id_post_emission_verification_schema": {
            "version": "candidate_trace_id_post_emission_verification_v1",
            "fields": list(POST_EMISSION_TRACE_FIELDS),
            "rule": "offline verification of freshly emitted JSONL trace fields only; historical reports are not interpreted as post-emission evidence",
        },
        "alias_normalization_coverage_schema": {
            "version": "alias_normalization_coverage_verification_v1",
            "canonical_fields": list(ALIAS_NORMALIZATION_FIELDS),
            "alias_fields": {field: list(aliases) for field, aliases in IDENTITY_FIELD_ALIASES.items()},
            "origin_classes": ["original_canonical", "normalized_alias", "missing"],
            "rule": "offline verification of freshly emitted post-normalization JSONL trace fields only; no historical identity upgrade is inferred",
        },
        "condition_identity_alias_discovery_schema": {
            "version": "condition_identity_alias_discovery_v1",
            "aliases": list(CONDITION_IDENTITY_ALIAS_FIELDS),
            "rule": "offline discovery only; aliases are reported as evidence and do not upgrade identity confidence or canonical condition_id truth",
        },
        "post_condition_enrichment_verification_schema": {
            "version": "post_condition_enrichment_verification_v1",
            "pre_patch_baseline": {
                "pre_patch_traced_events_with_condition_id": 0,
                "pre_patch_trace_events_direct_ready": 0,
                "pre_patch_trace_events_strong_ready": 0,
            },
            "rule": "offline verification of fresh candidate_trace_id-bearing events with canonical condition_id only; old reports are not reinterpreted as post-patch evidence",
        },
        "post_fallback_condition_coverage_verification_schema": {
            "version": "post_fallback_condition_coverage_verification_v1",
            "pre_fallback_baseline": {
                "pre_fallback_condition_id": 0,
                "pre_fallback_direct_ready": 0,
                "pre_fallback_strong_ready": 0,
            },
            "freshness_inputs": ["run_id", "since", "until", "date", "from", "to"],
            "rule": "offline verification of fresh post-fallback JSONL only; historical trace events without canonical condition_id are not treated as fallback evidence",
        },
        "ev_risk_chain_gap_schema": {
            "version": "ev_risk_chain_gap_diagnostics_v1",
            "ev_visibility_accepted_fields": EV_VISIBILITY_ACCEPTED_FIELDS,
            "risk_layer_trace_readiness_requirements": RISK_LAYER_TRACE_REQUIREMENTS,
            "rule": "offline explanation only; classify whether EV and risk chain visibility are absent without inferring hidden EV or hidden risk evaluation",
        },
        "does_not_claim_profitability": True,
        "does_not_authorize_runtime_decisions": True,
        "does_not_infer_execution": True,
        "does_not_claim_mfe_mae": True,
        "events_loaded": len(events),
        "bad_json_lines": bad_json_lines,
        "continuity_chains_loaded": len(chains),
        "phase2_coverage_status": phase2_coverage.get("status"),
        "coverage_gaps": list(phase2_coverage.get("coverage_gaps", [])),
        "summary": summary,
        "ev_risk_chain_gap_diagnostics": summary["ev_risk_chain_gap_diagnostics"],
        "ev_null_by_lifecycle_phase": summary["ev_null_by_lifecycle_phase"],
        "ev_null_by_block_stage": summary["ev_null_by_block_stage"],
        "ev_null_by_block_reason": summary["ev_null_by_block_reason"],
        "ev_null_by_market_readiness": summary["ev_null_by_market_readiness"],
        "ev_null_by_orderbook_state": summary["ev_null_by_orderbook_state"],
        "dominant_ev_blindness_context": summary["dominant_ev_blindness_context"],
        "ev_blindness_root_cause_confidence": summary["ev_blindness_root_cause_confidence"],
        "ev_field_missing_by_event_category": summary["ev_field_missing_by_event_category"],
        "dominant_missing_producer": summary["dominant_missing_producer"],
        "producer_missing_share": summary["producer_missing_share"],
        "ev_producer_observability_quality": summary["ev_producer_observability_quality"],
        "producer_level_ev_visibility": summary["producer_level_ev_visibility"],
        "ev_candidate_lifecycle_trace_summary": summary["ev_candidate_lifecycle_trace_summary"],
        "ev_trace_break_phase_counts": summary["ev_trace_break_phase_counts"],
        "producer_handoff_quality_counts": summary["producer_handoff_quality_counts"],
        "lifecycle_observability_quality_counts": summary["lifecycle_observability_quality_counts"],
        "candidate_trace_confidence_counts": summary["candidate_trace_confidence_counts"],
        "identity_continuity_diagnostics": identity_continuity,
        "identity_continuity_score": identity_continuity["identity_continuity_score"],
        "deterministic_chain_rate": identity_continuity["deterministic_chain_rate"],
        "direct_chain_count": identity_continuity["direct_chain_count"],
        "strong_chain_count": identity_continuity["strong_chain_count"],
        "weak_chain_count": identity_continuity["weak_chain_count"],
        "orphan_risk_count": identity_continuity["orphan_risk_count"],
        "orphan_execution_count": identity_continuity["orphan_execution_count"],
        "replay_lineage_gap_rate": identity_continuity["replay_lineage_gap_rate"],
        "decision_to_risk_identity_gap_count": identity_continuity["decision_to_risk_identity_gap_count"],
        "risk_to_execution_identity_gap_count": identity_continuity["risk_to_execution_identity_gap_count"],
        "candidate_trace_confidence_diagnostics": {
            "identity_fragmentation_detected_count": summary["identity_fragmentation_detected_count"],
            "propagation_gap_detected_count": summary["propagation_gap_detected_count"],
            "lifecycle_propagation_interruption_count": summary["lifecycle_propagation_interruption_count"],
            "candidate_seen_but_never_evaluable_count": summary["candidate_seen_but_never_evaluable_count"],
            "candidate_blocked_before_ev_count": summary["candidate_blocked_before_ev_count"],
            "ev_attempted_but_not_visible_count": summary["ev_attempted_but_not_visible_count"],
            "ev_visibility_attempted_count": summary["ev_visibility_attempted_count"],
            "ev_visibility_confirmed_count": summary["ev_visibility_confirmed_count"],
        },
        "identity_confidence_by_producer": summary["identity_confidence_by_producer"],
        "identity_gap_by_producer": summary["identity_gap_by_producer"],
        "proxy_dependency_by_producer": summary["proxy_dependency_by_producer"],
        "direct_identity_absence_by_producer": summary["direct_identity_absence_by_producer"],
        "producer_transition_identity_gap_tables": summary["producer_transition_identity_gap_tables"],
        "strongest_available_identity_by_transition": summary["strongest_available_identity_by_transition"],
        "weakest_identity_transition": summary["weakest_identity_transition"],
        "dominant_identity_failure_transition": summary["dominant_identity_failure_transition"],
        "producer_required_fields": summary["producer_required_fields"],
        "missing_envelope_fields_by_producer": summary["missing_envelope_fields_by_producer"],
        "envelope_readiness_by_producer": summary["envelope_readiness_by_producer"],
        "envelope_readiness_score": summary["envelope_readiness_score"],
        "weakest_envelope_producer": summary["weakest_envelope_producer"],
        "runtime_observability_fields_needed": summary["runtime_observability_fields_needed"],
        "risk_layer_envelope_gap_report": summary["risk_layer_envelope_gap_report"],
        "risk_log_identity_missing_count": summary["risk_log_identity_missing_count"],
        "risk_log_market_key_missing_count": summary["risk_log_market_key_missing_count"],
        "risk_log_lifecycle_phase_missing_count": summary["risk_log_lifecycle_phase_missing_count"],
        "risk_log_risk_state_missing_count": summary["risk_log_risk_state_missing_count"],
        "decision_to_risk_handoff_quality": summary["decision_to_risk_handoff_quality"],
        "risk_to_execution_handoff_quality": summary["risk_to_execution_handoff_quality"],
        "risk_layer_trace_readiness": summary["risk_layer_trace_readiness"],
        "risk_layer_block_visibility": summary["risk_layer_block_visibility"],
        "candidate_blocked_before_risk_visibility_count": summary["candidate_blocked_before_risk_visibility_count"],
        "ev_visible_before_risk_missing_after_count": summary["ev_visible_before_risk_missing_after_count"],
        "weakest_risk_gap_reason": summary["weakest_risk_gap_reason"],
        "dominant_risk_visibility_failure": summary["dominant_risk_visibility_failure"],
        "runtime_observability_fields_needed_for_risk_layer": summary["runtime_observability_fields_needed_for_risk_layer"],
        "decision_to_risk_boundary_counts": summary["decision_to_risk_boundary_counts"],
        "risk_reachability_rate": summary["risk_reachability_rate"],
        "risk_serialization_visibility_rate": summary["risk_serialization_visibility_rate"],
        "pre_risk_block_share": summary["pre_risk_block_share"],
        "no_decision_evidence_share": summary["no_decision_evidence_share"],
        "dominant_decision_to_risk_boundary_failure": summary["dominant_decision_to_risk_boundary_failure"],
        "pre_risk_block_cause_counts": summary["pre_risk_block_cause_counts"],
        "dominant_pre_risk_block_cause": summary["dominant_pre_risk_block_cause"],
        "pre_risk_block_cause_share": summary["pre_risk_block_cause_share"],
        "ev_related_pre_risk_block_share": summary["ev_related_pre_risk_block_share"],
        "microstructure_related_pre_risk_block_share": summary["microstructure_related_pre_risk_block_share"],
        "timing_related_pre_risk_block_share": summary["timing_related_pre_risk_block_share"],
        "identity_related_pre_risk_block_share": summary["identity_related_pre_risk_block_share"],
        "unknown_pre_risk_block_share": summary["unknown_pre_risk_block_share"],
        "ev_related_pre_risk_block_count": summary["ev_related_pre_risk_block_count"],
        "microstructure_related_pre_risk_block_count": summary["microstructure_related_pre_risk_block_count"],
        "timing_related_pre_risk_block_count": summary["timing_related_pre_risk_block_count"],
        "identity_related_pre_risk_block_count": summary["identity_related_pre_risk_block_count"],
        "unknown_pre_risk_block_count": summary["unknown_pre_risk_block_count"],
        "model_state_gap_counts": summary["model_state_gap_counts"],
        "probability_state_gap_counts": summary["probability_state_gap_counts"],
        "fair_value_state_gap_counts": summary["fair_value_state_gap_counts"],
        "ev_state_gap_counts": summary["ev_state_gap_counts"],
        "model_attempt_visibility_rate": summary["model_attempt_visibility_rate"],
        "model_output_serialization_rate": summary["model_output_serialization_rate"],
        "identity_blocked_model_link_rate": summary["identity_blocked_model_link_rate"],
        "dominant_model_state_gap": summary["dominant_model_state_gap"],
        "model_attempt_gate_counts": summary["model_attempt_gate_counts"],
        "dominant_model_attempt_gate": summary["dominant_model_attempt_gate"],
        "model_gate_microstructure_share": summary["model_gate_microstructure_share"],
        "model_gate_timing_share": summary["model_gate_timing_share"],
        "model_gate_identity_share": summary["model_gate_identity_share"],
        "model_gate_unknown_share": summary["model_gate_unknown_share"],
        "model_attempt_eligibility_rate": summary["model_attempt_eligibility_rate"],
        "identity_confidence_requirements": summary["identity_confidence_requirements"],
        "identity_upgrade_required_fields": summary["identity_upgrade_required_fields"],
        "missing_fields_preventing_direct_identity": summary["missing_fields_preventing_direct_identity"],
        "missing_fields_preventing_strong_identity": summary["missing_fields_preventing_strong_identity"],
        "candidate_identity_upgrade_path_counts": summary["candidate_identity_upgrade_path_counts"],
        "easiest_identity_upgrade_field": summary["easiest_identity_upgrade_field"],
        "highest_impact_identity_field": summary["highest_impact_identity_field"],
        "direct_identity_blocker_rank": summary["direct_identity_blocker_rank"],
        "strong_identity_blocker_rank": summary["strong_identity_blocker_rank"],
        "hypothetical_identity_upgrade_impact": summary["hypothetical_identity_upgrade_impact"],
        "candidate_trace_id_post_emission_verification": post_emission_verification,
        "candidate_trace_alias_normalization_verification": alias_normalization_verification,
        "post_emission_data_status": post_emission_verification["post_emission_data_status"],
        "post_emission_data_exists": post_emission_verification["post_emission_data_exists"],
        "post_normalization_data_status": alias_normalization_verification["post_normalization_data_status"],
        "post_normalization_data_exists": alias_normalization_verification["post_normalization_data_exists"],
        "alias_normalized_field_counts": alias_normalization_verification["alias_normalized_field_counts"],
        "alias_source_field_counts": alias_normalization_verification["alias_source_field_counts"],
        "canonical_identity_field_presence_after_normalization": alias_normalization_verification["canonical_identity_field_presence_after_normalization"],
        "producer_alias_dependency_counts": alias_normalization_verification["producer_alias_dependency_counts"],
        "producer_canonical_presence_counts": alias_normalization_verification["producer_canonical_presence_counts"],
        "condition_identity_alias_discovery": condition_alias_discovery,
        "condition_identity_alias_counts": condition_alias_discovery["condition_identity_alias_counts"],
        "condition_identity_alias_by_producer": condition_alias_discovery["condition_identity_alias_by_producer"],
        "traced_events_with_any_condition_alias": condition_alias_discovery["traced_events_with_any_condition_alias"],
        "traced_events_condition_alias_missing": condition_alias_discovery["traced_events_condition_alias_missing"],
        "condition_identity_best_alias": condition_alias_discovery["condition_identity_best_alias"],
        "condition_identity_alias_coverage_rate": condition_alias_discovery["condition_identity_alias_coverage_rate"],
        "condition_id_truly_absent_or_alias_hidden": condition_alias_discovery["condition_id_truly_absent_or_alias_hidden"],
        "post_condition_enrichment_verification": post_condition_enrichment_verification,
        "post_fallback_condition_coverage_verification": post_fallback_condition_coverage_verification,
        "post_condition_enrichment_data_status": post_condition_enrichment_verification["post_condition_enrichment_data_status"],
        "post_condition_enrichment_data_exists": post_condition_enrichment_verification["post_condition_enrichment_data_exists"],
        "post_fallback_data_status": post_fallback_condition_coverage_verification["post_fallback_data_status"],
        "post_fallback_data_exists": post_fallback_condition_coverage_verification["post_fallback_data_exists"],
        "pre_fallback_condition_id": post_fallback_condition_coverage_verification["pre_fallback_condition_id"],
        "pre_fallback_direct_ready": post_fallback_condition_coverage_verification["pre_fallback_direct_ready"],
        "pre_fallback_strong_ready": post_fallback_condition_coverage_verification["pre_fallback_strong_ready"],
        "traced_events_with_condition_id": post_fallback_condition_coverage_verification["traced_events_with_condition_id"],
        "post_fallback_condition_id_presence_by_producer": post_fallback_condition_coverage_verification["condition_id_presence_by_producer"],
        "post_fallback_trace_events_direct_ready": post_fallback_condition_coverage_verification["trace_events_direct_ready"],
        "post_fallback_trace_events_strong_ready": post_fallback_condition_coverage_verification["trace_events_strong_ready"],
        "remaining_identity_blockers": post_fallback_condition_coverage_verification["remaining_identity_blockers"],
        "post_fallback_delta": post_fallback_condition_coverage_verification["post_fallback_delta"],
        "pre_patch_traced_events_with_condition_id": post_condition_enrichment_verification["pre_patch_traced_events_with_condition_id"],
        "pre_patch_trace_events_direct_ready": post_condition_enrichment_verification["pre_patch_trace_events_direct_ready"],
        "pre_patch_trace_events_strong_ready": post_condition_enrichment_verification["pre_patch_trace_events_strong_ready"],
        "traced_events_with_condition_id_after_enrichment": post_condition_enrichment_verification["traced_events_with_condition_id_after_enrichment"],
        "condition_id_presence_by_producer_after_enrichment": post_condition_enrichment_verification["condition_id_presence_by_producer_after_enrichment"],
        "condition_id_enrichment_candidate_count": post_condition_enrichment_verification["condition_id_enrichment_candidate_count"],
        "trace_events_direct_ready_after_condition_enrichment": post_condition_enrichment_verification["trace_events_direct_ready_after_condition_enrichment"],
        "trace_events_strong_ready_after_condition_enrichment": post_condition_enrichment_verification["trace_events_strong_ready_after_condition_enrichment"],
        "condition_enrichment_delta": post_condition_enrichment_verification["condition_enrichment_delta"],
        "fields_still_preventing_direct_identity_after_condition_enrichment": post_condition_enrichment_verification["fields_still_preventing_direct_identity_after_condition_enrichment"],
        "fields_still_preventing_strong_identity_after_condition_enrichment": post_condition_enrichment_verification["fields_still_preventing_strong_identity_after_condition_enrichment"],
        "trace_events_with_candidate_trace_id": alias_normalization_verification["trace_events_with_candidate_trace_id"],
        "trace_events_with_condition_id": alias_normalization_verification["trace_events_with_condition_id"],
        "trace_events_with_token_id": alias_normalization_verification["trace_events_with_token_id"],
        "trace_events_with_side": alias_normalization_verification["trace_events_with_side"],
        "trace_events_direct_ready": alias_normalization_verification["trace_events_direct_ready"],
        "trace_events_strong_ready": alias_normalization_verification["trace_events_strong_ready"],
        "fields_still_missing_after_alias_normalization": alias_normalization_verification["fields_still_missing_after_alias_normalization"],
        "candidate_trace_id_present_count": post_emission_verification["candidate_trace_id_present_count"],
        "candidate_trace_id_missing_count": post_emission_verification["candidate_trace_id_missing_count"],
        "candidate_trace_id_presence_by_producer": post_emission_verification["candidate_trace_id_presence_by_producer"],
        "parent_candidate_trace_id_presence_by_producer": post_emission_verification["parent_candidate_trace_id_presence_by_producer"],
        "trace_link_reason_presence_by_producer": post_emission_verification["trace_link_reason_presence_by_producer"],
        "market_key_presence_by_producer": post_emission_verification["market_key_presence_by_producer"],
        "condition_id_presence_by_producer": post_emission_verification["condition_id_presence_by_producer"],
        "token_id_presence_by_producer": post_emission_verification["token_id_presence_by_producer"],
        "side_presence_by_producer": post_emission_verification["side_presence_by_producer"],
        "post_emission_direct_identity_candidates": post_emission_verification["post_emission_direct_identity_candidates"],
        "post_emission_strong_identity_candidates": post_emission_verification["post_emission_strong_identity_candidates"],
        "post_emission_proxy_candidates": post_emission_verification["post_emission_proxy_candidates"],
        "direct_identity_improvement_possible": post_emission_verification["direct_identity_improvement_possible"],
        "fields_still_preventing_direct_identity": post_emission_verification["fields_still_preventing_direct_identity"],
        "dominant_ev_blind_causes": dominant_causes,
        "candidate_ev_coverage": rows[:100],
        "research_questions": {
            "why_candidate_paths_remain_ev_unobservable": {
                "dominant_causes": dominant_causes,
                "guardrail": "evidence only; no fake MFE/MAE conclusions or execution inference",
            },
            "candidate_survival_vs_ev_visibility": summary["candidate_survival_vs_ev_visibility"],
            "field_level_continuity": {
                "fields": list(EV_COMPONENT_FIELDS),
                "avg_ev_field_continuity_rate": summary["avg_ev_field_continuity_rate"],
            },
            "where_candidate_ev_visibility_disappeared": summary["ev_candidate_lifecycle_trace_summary"],
            "candidate_trace_confidence": {
                "counts": summary["candidate_trace_confidence_counts"],
                "diagnostics": {
                    "identity_fragmentation_detected_count": summary["identity_fragmentation_detected_count"],
                    "propagation_gap_detected_count": summary["propagation_gap_detected_count"],
                    "candidate_seen_but_never_evaluable_count": summary["candidate_seen_but_never_evaluable_count"],
                    "ev_attempted_but_not_visible_count": summary["ev_attempted_but_not_visible_count"],
                },
            },
            "direct_vs_proxy_identity_gap": {
                "identity_confidence_by_producer": summary["identity_confidence_by_producer"],
                "identity_gap_by_producer": summary["identity_gap_by_producer"],
                "producer_transition_identity_gap_tables": summary["producer_transition_identity_gap_tables"],
                "weakest_identity_transition": summary["weakest_identity_transition"],
                "dominant_identity_failure_transition": summary["dominant_identity_failure_transition"],
            },
            "candidate_trace_envelope": {
                "candidate_trace_envelope_spec": summary["candidate_trace_envelope_spec"],
                "producer_required_fields": summary["producer_required_fields"],
                "missing_envelope_fields_by_producer": summary["missing_envelope_fields_by_producer"],
                "envelope_readiness_score": summary["envelope_readiness_score"],
                "weakest_envelope_producer": summary["weakest_envelope_producer"],
                "runtime_observability_fields_needed": summary["runtime_observability_fields_needed"],
            },
            "risk_layer_envelope_gap": summary["risk_layer_envelope_gap_report"],
            "decision_to_risk_boundary": {
                "counts": summary["decision_to_risk_boundary_counts"],
                "risk_reachability_rate": summary["risk_reachability_rate"],
                "risk_serialization_visibility_rate": summary["risk_serialization_visibility_rate"],
                "dominant_failure": summary["dominant_decision_to_risk_boundary_failure"],
                "interpretation": summary["decision_to_risk_boundary_interpretation"],
            },
            "pre_risk_block_cause_taxonomy": {
                "counts": summary["pre_risk_block_cause_counts"],
                "dominant_cause": summary["dominant_pre_risk_block_cause"],
                "cause_share": summary["pre_risk_block_cause_share"],
                "ev_related_share": summary["ev_related_pre_risk_block_share"],
                "microstructure_related_share": summary["microstructure_related_pre_risk_block_share"],
                "timing_related_share": summary["timing_related_pre_risk_block_share"],
                "identity_related_share": summary["identity_related_pre_risk_block_share"],
                "unknown_share": summary["unknown_pre_risk_block_share"],
            },
            "model_state_attempt_vs_emission_gap": {
                "model_state_gap_counts": summary["model_state_gap_counts"],
                "probability_state_gap_counts": summary["probability_state_gap_counts"],
                "fair_value_state_gap_counts": summary["fair_value_state_gap_counts"],
                "ev_state_gap_counts": summary["ev_state_gap_counts"],
                "model_attempt_visibility_rate": summary["model_attempt_visibility_rate"],
                "model_output_serialization_rate": summary["model_output_serialization_rate"],
                "identity_blocked_model_link_rate": summary["identity_blocked_model_link_rate"],
                "dominant_model_state_gap": summary["dominant_model_state_gap"],
            },
            "model_attempt_gate_taxonomy": {
                "counts": summary["model_attempt_gate_counts"],
                "dominant_gate": summary["dominant_model_attempt_gate"],
                "microstructure_share": summary["model_gate_microstructure_share"],
                "timing_share": summary["model_gate_timing_share"],
                "identity_share": summary["model_gate_identity_share"],
                "unknown_share": summary["model_gate_unknown_share"],
                "eligibility_rate": summary["model_attempt_eligibility_rate"],
            },
            "candidate_identity_upgrade_requirements": {
                "requirements": summary["identity_confidence_requirements"],
                "missing_fields_preventing_direct_identity": summary["missing_fields_preventing_direct_identity"],
                "missing_fields_preventing_strong_identity": summary["missing_fields_preventing_strong_identity"],
                "candidate_identity_upgrade_path_counts": summary["candidate_identity_upgrade_path_counts"],
                "highest_impact_identity_field": summary["highest_impact_identity_field"],
                "easiest_identity_upgrade_field": summary["easiest_identity_upgrade_field"],
                "rule": "hypothetical upgrade impact only; PROXY remains non-confirming",
            },
            "candidate_trace_id_post_emission_verification": post_emission_verification,
            "alias_normalization_coverage_verification": alias_normalization_verification,
            "condition_identity_alias_discovery": condition_alias_discovery,
            "post_condition_enrichment_verification": post_condition_enrichment_verification,
            "post_fallback_condition_coverage_verification": post_fallback_condition_coverage_verification,
        },
    }


def write_ev_field_coverage_report(report: dict[str, Any], *, report_dir: str | Path = DEFAULT_REPORT_DIR) -> Path:
    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    date_part = _date_part(
        str(report.get("date_from")),
        str(report.get("date_to")),
        dict(report.get("time_filter", {})),
        str(report.get("run_id") or ""),
    )
    output_path = output_dir / f"ev_field_coverage_{date_part}.json"
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return output_path


def print_summary(report: dict[str, Any]) -> None:
    summary = report.get("summary", {})
    print("EV Field Coverage Diagnostics")
    print(
        "range={start}..{end} run_id={run_id} events={events} chains={chains} rows={rows} avg_rate={rate}".format(
            start=report.get("date_from"),
            end=report.get("date_to"),
            run_id=report.get("run_id") or "",
            events=report.get("events_loaded"),
            chains=report.get("continuity_chains_loaded"),
            rows=summary.get("candidate_ev_coverage_rows", 0),
            rate=summary.get("avg_ev_field_continuity_rate", 0.0),
        )
    )
    print(f"visibility_states={summary.get('candidate_ev_visibility_state_counts', {})}")
    print(f"dropout_reasons={summary.get('ev_field_dropout_reason_counts', {})}")
    print(f"null_reasons={summary.get('ev_null_reason_counts', {})}")
    print(f"dominant_ev_blindness_context={summary.get('dominant_ev_blindness_context', {})}")
    print(f"ev_blindness_root_cause_confidence={summary.get('ev_blindness_root_cause_confidence', '')}")
    print(f"dominant_missing_producer={summary.get('dominant_missing_producer', {})}")
    print(f"ev_producer_observability_quality={summary.get('ev_producer_observability_quality', '')}")
    print(f"ev_trace_break_phases={summary.get('ev_trace_break_phase_counts', {})}")
    print(f"producer_handoff_quality={summary.get('producer_handoff_quality_counts', {})}")
    print(f"candidate_trace_confidence={summary.get('candidate_trace_confidence_counts', {})}")
    print(f"weakest_identity_transition={summary.get('weakest_identity_transition', {})}")
    print(f"envelope_readiness_score={summary.get('envelope_readiness_score', 0.0)}")
    print(f"weakest_envelope_producer={summary.get('weakest_envelope_producer', {})}")
    print(f"risk_layer_trace_readiness={summary.get('risk_layer_trace_readiness', 0.0)}")
    print(f"dominant_risk_visibility_failure={summary.get('dominant_risk_visibility_failure', '')}")
    print(f"decision_to_risk_boundary_counts={summary.get('decision_to_risk_boundary_counts', {})}")
    print(f"dominant_decision_to_risk_boundary_failure={summary.get('dominant_decision_to_risk_boundary_failure', '')}")
    print(f"pre_risk_block_cause_counts={summary.get('pre_risk_block_cause_counts', {})}")
    print(f"dominant_pre_risk_block_cause={summary.get('dominant_pre_risk_block_cause', '')}")
    print(f"model_state_gap_counts={summary.get('model_state_gap_counts', {})}")
    print(f"dominant_model_state_gap={summary.get('dominant_model_state_gap', '')}")
    print(f"model_attempt_gate_counts={summary.get('model_attempt_gate_counts', {})}")
    print(f"dominant_model_attempt_gate={summary.get('dominant_model_attempt_gate', '')}")
    print(f"highest_impact_identity_field={summary.get('highest_impact_identity_field', {})}")
    print(f"easiest_identity_upgrade_field={summary.get('easiest_identity_upgrade_field', {})}")
    print(f"post_emission_data_status={report.get('post_emission_data_status', '')}")
    print(f"candidate_trace_id_present_count={report.get('candidate_trace_id_present_count', 0)}")
    print(f"post_normalization_data_status={report.get('post_normalization_data_status', '')}")
    print(f"alias_normalized_field_counts={report.get('alias_normalized_field_counts', {})}")
    print(f"condition_identity_alias_counts={report.get('condition_identity_alias_counts', {})}")
    print(f"condition_identity_best_alias={report.get('condition_identity_best_alias', {})}")
    print(f"post_condition_enrichment_data_status={report.get('post_condition_enrichment_data_status', '')}")
    print(f"traced_events_with_condition_id_after_enrichment={report.get('traced_events_with_condition_id_after_enrichment', 0)}")
    print(f"post_fallback_data_status={report.get('post_fallback_data_status', '')}")
    print(f"traced_events_with_condition_id={report.get('traced_events_with_condition_id', 0)}")
    print(f"post_fallback_trace_events_strong_ready={report.get('post_fallback_trace_events_strong_ready', 0)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build offline EV field coverage diagnostics from candidate survival windows.")
    parser.add_argument("--date", default=None, help="Single date in YYYY-MM-DD format.")
    parser.add_argument("--from", dest="date_from", default=None, help="Start date in YYYY-MM-DD format.")
    parser.add_argument("--to", dest="date_to", default=None, help="End date in YYYY-MM-DD format.")
    parser.add_argument("--since", default=None, help="UTC start time HH:MM for same-day filtering; inclusive.")
    parser.add_argument("--until", default=None, help="UTC end time HH:MM for same-day filtering; exclusive.")
    parser.add_argument("--run-id", default=None, help="Exact run_id to isolate; events without this run_id are excluded.")
    parser.add_argument("--base-dir", default=str(DEFAULT_QUANT_DATA_DIR), help="Quant data root directory.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Output report directory.")
    parser.add_argument("--no-write", action="store_true", help="Do not write ev_field_coverage JSON.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_ev_field_coverage_report(
        base_dir=args.base_dir,
        date=args.date,
        date_from=args.date_from,
        date_to=args.date_to,
        since=args.since,
        until=args.until,
        run_id=args.run_id,
    )
    print_summary(report)
    if not args.no_write:
        path = write_ev_field_coverage_report(report, report_dir=args.report_dir)
        print(f"wrote_report={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
