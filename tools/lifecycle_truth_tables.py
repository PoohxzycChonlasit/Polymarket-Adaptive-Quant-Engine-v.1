from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.replay_analyzer import (
    DEFAULT_QUANT_DATA_DIR,
    DEFAULT_REPORT_DIR,
    build_phase2_coverage_from_events,
    build_time_filter,
    load_replay_events,
)


DIRECT_FIELD_PATHS = (
    "candidate_id",
    "signal_id",
    "lifecycle_phase",
    "token_ready_at",
    "orderbook_ready_at",
    "liquidity_ready_at",
    "spread_ready_at",
    "first_tradable_at",
    "first_evaluable_at",
    "fair_value",
    "market_price",
    "true_probability",
    "ev_after_spread",
    "inventory_action",
    "starter_candidate",
    "reload_candidate",
    "unload_candidate",
    "final_derisk_candidate",
    "exposure_before",
    "exposure_after",
    "risk_budget_used",
    "remaining_risk_budget",
    "lifecycle_phase_transition_reason",
    "candidate_block_reason",
    "candidate_block_stage",
    "readiness_transition_reason",
    "market_readiness_state",
    "candidate_survival_ms",
    "candidate_expiry_reason",
    "lifecycle_phase_entered_at",
    "lifecycle_phase_exited_at",
    "ev_candidate_ready",
    "model_output_ready",
    "orderbook_state_classification",
)

PROXY_FIELD_PATHS = (
    "seconds_remaining",
    "seconds_since_open",
    "first_seen_seconds_remaining",
    "first_evaluable_seconds_remaining",
    "spread",
    "edge",
    "ev",
    "confidence",
    "liquidity_state",
    "orderbook_readiness_reason",
    "orderbook_unavailable_reason",
    "skip_reason",
    "normalized_skip_reason",
    "active_window_alignment_reason",
)

EV_FIELDS = ("fair_value", "market_price", "true_probability", "ev_after_spread")
NULL_REASON_FIELDS = tuple(f"{field}_null_reason" for field in EV_FIELDS)
AVAILABLE_FIELDS = tuple(f"{field}_available" for field in EV_FIELDS)
ORDERBOOK_LIQUIDITY_TOKENS = (
    "no_orderbook",
    "orderbook",
    "empty_book",
    "warmup",
    "liquidity",
    "spread",
    "stale",
    "clob",
    "token",
)
TIME_UNSAFE_TOKENS = ("time_unsafe", "cutoff", "hard_close", "too_late", "time")
TELEMETRY_CATEGORIES = {"system_health", "risk_log", "execution_log"}
CANDIDATE_IDENTITY_FIELDS = ("candidate_id", "signal_id", "opportunity_id", "replay_candidate_id")
CANDIDATE_ACTION_FIELDS = (
    "inventory_action",
    "starter_candidate",
    "reload_candidate",
    "unload_candidate",
    "final_derisk_candidate",
)
CANDIDATE_CONTINUITY_FIELDS = (
    *CANDIDATE_IDENTITY_FIELDS,
    *CANDIDATE_ACTION_FIELDS,
    "candidate_block_stage",
    "candidate_block_reason",
    "candidate_survival_ms",
    "candidate_expiry_reason",
)
LIFECYCLE_OWNERSHIP_FIELDS = (
    "lifecycle_phase",
    "lifecycle_phase_transition_reason",
    "lifecycle_phase_entered_at",
    "lifecycle_phase_exited_at",
    "readiness_transition_reason",
    "market_readiness_state",
    "orderbook_state_classification",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def _as_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool) or value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_filename_token(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    sanitized = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in text)
    return sanitized[:80] or "run"


def _date_part(date_from: str, date_to: str, time_filter: dict[str, Any], run_id: str | None) -> str:
    date_text = date_from if date_from == date_to else f"{date_from}_to_{date_to}"
    if time_filter.get("applied"):
        since = str(time_filter.get("since") or "start").replace(":", "")
        until = str(time_filter.get("until") or "end").replace(":", "")
        date_text = f"{date_text}_{since}_to_{until}"
    safe_run_id = _safe_filename_token(run_id)
    if safe_run_id:
        date_text = f"{date_text}_run_{safe_run_id}"
    return date_text


def _payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload")
    return payload if isinstance(payload, dict) else event


def _nested(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _first_value(payload: dict[str, Any], *paths: str) -> Any:
    display = payload.get("display")
    for path in paths:
        value = _nested(payload, path)
        if value is not None and value != "":
            return value
        if isinstance(display, dict):
            value = _nested(display, path)
            if value is not None and value != "":
                return value
    return None


def _has_any(payload: dict[str, Any], fields: tuple[str, ...]) -> bool:
    return any(_first_value(payload, field) is not None for field in fields)


def _has_lifecycle_ownership(payload: dict[str, Any]) -> bool:
    for field in LIFECYCLE_OWNERSHIP_FIELDS:
        value = _first_value(payload, field)
        if value is None:
            continue
        if field in {"lifecycle_phase", "market_lifecycle_phase", "inventory_lifecycle_phase"}:
            phase = str(value or "").strip().upper()
            if not phase or phase == "UNKNOWN":
                continue
        return True
    return False


def _has_known_lifecycle_phase(payload: dict[str, Any]) -> bool:
    phase = str(_first_value(payload, "lifecycle_phase", "market_lifecycle_phase", "inventory_lifecycle_phase") or "").strip().upper()
    return bool(phase and phase != "UNKNOWN")


def _has_meaningful_candidate_block(payload: dict[str, Any]) -> bool:
    stage = str(_first_value(payload, "candidate_block_stage") or "").strip().lower()
    reason = str(_first_value(payload, "candidate_block_reason") or "").strip().lower()
    if stage in {"pre_ev", "post_ev"}:
        return True
    return bool(reason and reason not in {"not_blocked", "unavailable", "unknown"})


def _asset_from(event: dict[str, Any], payload: dict[str, Any]) -> str:
    top_level_asset = str(event.get("asset") or event.get("ticker") or "").upper()
    if "BTC" in top_level_asset:
        return "BTC"
    if "ETH" in top_level_asset:
        return "ETH"
    for key in ("asset", "ticker", "market_id", "market_slug", "condition_id"):
        value = str(_first_value(payload, key) or "").upper()
        if "BTC" in value:
            return "BTC"
        if "ETH" in value:
            return "ETH"
    return "UNKNOWN"


def _skip_reason(payload: dict[str, Any]) -> str:
    return str(_first_value(payload, "normalized_skip_reason", "skip_reason", "raw_skip_reason") or "").strip()


def _decision_state(payload: dict[str, Any]) -> str:
    decision_type = str(_first_value(payload, "decision_type") or "").lower()
    decision = str(_first_value(payload, "decision") or "").lower()
    skipped = _as_bool(_first_value(payload, "skipped")) or decision in {"skip", "skipped"}
    if decision_type in {"approved", "enter", "entered"} or (decision in {"buy", "enter", "approved"} and not skipped):
        return "enter_candidate"
    if decision_type in {"risk_rejected", "rejected", "skipped"} or skipped:
        return "blocked_or_skipped"
    return "observed"


def _phase(payload: dict[str, Any]) -> tuple[str, str]:
    direct = str(_first_value(payload, "lifecycle_phase", "market_lifecycle_phase", "inventory_lifecycle_phase") or "").strip()
    if direct:
        return direct, "direct_observed"
    seconds = _as_float(_first_value(payload, "seconds_since_open"), default=float("nan"))
    if seconds == seconds:
        if seconds < 35:
            return "OPENING_SCAN", "proxy_inferred"
        if seconds < 240:
            return "ACTIVE_INVENTORY_TRADING", "proxy_inferred"
        if seconds < 270:
            return "PROFIT_MANAGEMENT", "proxy_inferred"
        if seconds < 300:
            return "FINAL_DERISK", "proxy_inferred"
    remaining = _as_float(_first_value(payload, "seconds_remaining", "seconds_until_close"), default=float("nan"))
    if remaining == remaining:
        since_open = 300.0 - remaining
        if since_open < 35:
            return "OPENING_SCAN", "proxy_inferred"
        if since_open < 240:
            return "ACTIVE_INVENTORY_TRADING", "proxy_inferred"
        if since_open < 270:
            return "PROFIT_MANAGEMENT", "proxy_inferred"
        if since_open < 300:
            return "FINAL_DERISK", "proxy_inferred"
    return "UNKNOWN", "coverage_gap"


def _candidate_key(event: dict[str, Any], payload: dict[str, Any]) -> tuple[str, str]:
    direct = str(_first_value(payload, "candidate_id") or "").strip()
    if direct:
        return direct, "direct_observed"
    signal = str(_first_value(payload, "signal_id") or "").strip()
    if signal:
        return signal, "direct_observed"
    market = str(_first_value(payload, "market_id", "condition_id", "market_slug") or "").strip()
    timestamp = str(event.get("timestamp_utc") or _first_value(payload, "timestamp_utc") or "").strip()
    if market or timestamp:
        return f"proxy::{market or 'unknown_market'}::{timestamp or 'unknown_time'}", "proxy_inferred"
    return "coverage_gap::unknown_candidate", "coverage_gap"


def _ev_available(payload: dict[str, Any]) -> bool:
    for field in EV_FIELDS:
        available = _first_value(payload, f"{field}_available")
        value = _first_value(payload, field)
        if available is True or value is not None:
            return True
    return False


def _null_reasons(payload: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    for field in NULL_REASON_FIELDS:
        reason = str(_first_value(payload, field) or "").strip()
        if reason:
            reasons.append(reason)
    return reasons


def _legacy_is_candidate_event(payload: dict[str, Any]) -> bool:
    return (
        _has_any(payload, ("candidate_id", "signal_id", "inventory_action", "starter_candidate", "reload_candidate", "unload_candidate"))
        or _decision_state(payload) != "observed"
        or _has_any(payload, EV_FIELDS)
        or _has_any(payload, NULL_REASON_FIELDS)
    )


def _candidate_classification(event: dict[str, Any]) -> dict[str, Any]:
    payload = _payload(event)
    category = str(event.get("_category") or "").strip()
    event_type = str(event.get("event_type") or "").strip()
    has_identity = _has_any(payload, CANDIDATE_IDENTITY_FIELDS)
    has_action = _has_any(payload, CANDIDATE_ACTION_FIELDS)
    has_block_stage = _has_meaningful_candidate_block(payload)
    has_lifecycle = _has_lifecycle_ownership(payload)
    has_readiness = _has_any(
        payload,
        (
            "token_ready_at",
            "orderbook_ready_at",
            "liquidity_ready_at",
            "spread_ready_at",
            "first_tradable_at",
            "first_evaluable_at",
            "first_seen_seconds_remaining",
            "first_evaluable_seconds_remaining",
        ),
    )
    has_ev_model = _has_any(payload, (*EV_FIELDS, *NULL_REASON_FIELDS, *AVAILABLE_FIELDS, "probability_model_stage", "ev_calculation_stage", "model_output_ready", "ev_candidate_ready"))
    decision_candidate = category == "decision_log" and _decision_state(payload) != "observed"
    market_lifecycle_candidate = category == "market_snapshots" and has_lifecycle and (has_readiness or has_ev_model or has_identity)
    telemetry = category in TELEMETRY_CATEGORIES or event_type in {"system_health", "risk_event", "execution"}
    telemetry_lifecycle_owned = has_identity and (_has_known_lifecycle_phase(payload) or has_action or has_block_stage)

    if telemetry and not telemetry_lifecycle_owned:
        return {
            "is_candidate_event": False,
            "candidate_classification_reason": "excluded_telemetry_without_lifecycle_ownership",
            "candidate_classification_confidence": "excluded",
        }

    if has_identity:
        return {
            "is_candidate_event": True,
            "candidate_classification_reason": "direct_candidate_identity",
            "candidate_classification_confidence": "high",
        }
    if has_action:
        return {
            "is_candidate_event": True,
            "candidate_classification_reason": "direct_inventory_action_label",
            "candidate_classification_confidence": "high",
        }
    if has_block_stage and has_lifecycle:
        return {
            "is_candidate_event": True,
            "candidate_classification_reason": "direct_candidate_block_lifecycle",
            "candidate_classification_confidence": "high",
        }
    if decision_candidate:
        return {
            "is_candidate_event": True,
            "candidate_classification_reason": "decision_event_candidate_state",
            "candidate_classification_confidence": "medium",
        }
    if market_lifecycle_candidate:
        return {
            "is_candidate_event": True,
            "candidate_classification_reason": "market_snapshot_lifecycle_evidence",
            "candidate_classification_confidence": "medium",
        }
    if has_block_stage or (has_lifecycle and has_ev_model):
        return {
            "is_candidate_event": True,
            "candidate_classification_reason": "direct_lifecycle_model_evidence",
            "candidate_classification_confidence": "medium",
        }
    if _legacy_is_candidate_event(payload):
        return {
            "is_candidate_event": False,
            "candidate_classification_reason": "excluded_weak_candidate_evidence",
            "candidate_classification_confidence": "excluded",
        }
    return {
        "is_candidate_event": False,
        "candidate_classification_reason": "non_candidate_telemetry",
        "candidate_classification_confidence": "excluded",
    }


def _is_starter_candidate(payload: dict[str, Any]) -> tuple[bool, str]:
    if _as_bool(_first_value(payload, "starter_candidate")):
        return True, "direct_observed"
    action = str(_first_value(payload, "inventory_action", "lifecycle_action", "replay_action") or "").upper()
    if action in {"OPEN", "STARTER", "STARTER_CANDIDATE"}:
        return True, "direct_observed"
    if _decision_state(payload) == "enter_candidate":
        return True, "proxy_inferred"
    return False, ""


def _is_blocked(payload: dict[str, Any]) -> bool:
    return _decision_state(payload) == "blocked_or_skipped" or bool(_skip_reason(payload))


def _blocked_before_ev(payload: dict[str, Any]) -> tuple[bool, str]:
    direct_stage = str(_first_value(payload, "candidate_block_stage") or "").lower()
    if direct_stage == "pre_ev":
        return True, "direct_observed"
    stage = str(_first_value(payload, "probability_model_stage", "ev_calculation_stage") or "").lower()
    reasons = " ".join(_null_reasons(payload)).lower()
    if "candidate_blocked_before_ev" in stage or "pre_model_skip" in stage:
        return True, "direct_observed"
    if "candidate_blocked_before_ev" in reasons or "pre_model_skip" in reasons:
        return True, "direct_observed"
    if _is_blocked(payload) and not _ev_available(payload):
        return True, "proxy_inferred"
    return False, ""


def _blocked_after_ev(payload: dict[str, Any]) -> tuple[bool, str]:
    direct_stage = str(_first_value(payload, "candidate_block_stage") or "").lower()
    if direct_stage == "post_ev":
        return True, "direct_observed"
    stage = str(_first_value(payload, "ev_calculation_stage") or "").lower()
    if "risk_blocked_after_ev" in stage:
        return True, "direct_observed"
    if _is_blocked(payload) and _ev_available(payload):
        return True, "direct_observed"
    if _is_blocked(payload) and _first_value(payload, "ev", "edge") is not None:
        return True, "proxy_inferred"
    return False, ""


def _reason_contains(payload: dict[str, Any], tokens: tuple[str, ...]) -> bool:
    text = " ".join([
        _skip_reason(payload),
        str(_first_value(
            payload,
            "candidate_block_reason",
            "readiness_transition_reason",
            "market_readiness_state",
            "orderbook_state_classification",
            "orderbook_readiness_reason",
            "orderbook_unavailable_reason",
            "liquidity_state",
        ) or ""),
        " ".join(_null_reasons(payload)),
    ]).lower()
    return any(token in text for token in tokens)


def _candidate_row(event: dict[str, Any], *, table: str, inference: str) -> dict[str, Any]:
    payload = _payload(event)
    phase, phase_inference = _phase(payload)
    candidate_id, candidate_inference = _candidate_key(event, payload)
    classification = _candidate_classification(event)
    row = {
        "timestamp_utc": str(event.get("timestamp_utc") or _first_value(payload, "timestamp_utc") or ""),
        "run_id": str(event.get("run_id") or ""),
        "event_category": str(event.get("_category") or ""),
        "event_type": str(event.get("event_type") or ""),
        "asset": _asset_from(event, payload),
        "market_id": str(_first_value(payload, "market_id", "condition_id", "market_slug") or ""),
        "candidate_id": candidate_id,
        "candidate_id_inference": candidate_inference,
        "signal_id": str(_first_value(payload, "signal_id") or ""),
        "lifecycle_phase": phase,
        "lifecycle_phase_inference": phase_inference,
        "decision_state": _decision_state(payload),
        "candidate_classification_reason": classification["candidate_classification_reason"],
        "candidate_classification_confidence": classification["candidate_classification_confidence"],
        "skip_reason": _skip_reason(payload),
        "readiness": {
            "token_ready_at": _first_value(payload, "token_ready_at"),
            "orderbook_ready_at": _first_value(payload, "orderbook_ready_at"),
            "liquidity_ready_at": _first_value(payload, "liquidity_ready_at"),
            "spread_ready_at": _first_value(payload, "spread_ready_at"),
            "first_tradable_at": _first_value(payload, "first_tradable_at"),
            "first_evaluable_at": _first_value(payload, "first_evaluable_at"),
        },
        "fair_value": _first_value(payload, "fair_value"),
        "market_price": _first_value(payload, "market_price"),
        "true_probability": _first_value(payload, "true_probability"),
        "ev_after_spread": _first_value(payload, "ev_after_spread"),
        "ev_availability": {
            "fair_value": {
                "available": _first_value(payload, "fair_value_available"),
                "null_reason": _first_value(payload, "fair_value_null_reason"),
            },
            "market_price": {
                "available": _first_value(payload, "market_price_available"),
                "null_reason": _first_value(payload, "market_price_null_reason"),
            },
            "true_probability": {
                "available": _first_value(payload, "true_probability_available"),
                "null_reason": _first_value(payload, "true_probability_null_reason"),
            },
            "ev_after_spread": {
                "available": _first_value(payload, "ev_after_spread_available"),
                "null_reason": _first_value(payload, "ev_after_spread_null_reason"),
            },
        },
        "ev_proxy": _first_value(payload, "ev", "edge"),
        "ev_null_reasons": _null_reasons(payload),
        "probability_model_stage": str(_first_value(payload, "probability_model_stage") or ""),
        "ev_calculation_stage": str(_first_value(payload, "ev_calculation_stage") or ""),
        "lifecycle_observability": {
            "lifecycle_phase_transition_reason": _first_value(payload, "lifecycle_phase_transition_reason"),
            "candidate_block_reason": _first_value(payload, "candidate_block_reason"),
            "candidate_block_stage": _first_value(payload, "candidate_block_stage"),
            "readiness_transition_reason": _first_value(payload, "readiness_transition_reason"),
            "market_readiness_state": _first_value(payload, "market_readiness_state"),
            "candidate_survival_ms": _first_value(payload, "candidate_survival_ms"),
            "candidate_expiry_reason": _first_value(payload, "candidate_expiry_reason"),
            "lifecycle_phase_entered_at": _first_value(payload, "lifecycle_phase_entered_at"),
            "lifecycle_phase_exited_at": _first_value(payload, "lifecycle_phase_exited_at"),
            "ev_candidate_ready": _first_value(payload, "ev_candidate_ready"),
            "model_output_ready": _first_value(payload, "model_output_ready"),
            "orderbook_state_classification": _first_value(payload, "orderbook_state_classification"),
        },
        "inventory_action": str(_first_value(payload, "inventory_action", "lifecycle_action", "replay_action") or ""),
        "inventory_action_labels": {
            "starter_candidate": _as_bool(_first_value(payload, "starter_candidate")),
            "reload_candidate": _as_bool(_first_value(payload, "reload_candidate")),
            "unload_candidate": _as_bool(_first_value(payload, "unload_candidate")),
            "final_derisk_candidate": _as_bool(_first_value(payload, "final_derisk_candidate")),
        },
        "exposure": {
            "exposure_before": _first_value(payload, "exposure_before"),
            "exposure_after": _first_value(payload, "exposure_after"),
            "risk_budget_used": _first_value(payload, "risk_budget_used"),
            "remaining_risk_budget": _first_value(payload, "remaining_risk_budget"),
        },
        "evidence_inference": inference,
        "table": table,
    }
    return row


def _count_direct_proxy(events: list[dict[str, Any]]) -> tuple[float, float, dict[str, Any]]:
    total_direct_slots = max(1, len(events) * len(DIRECT_FIELD_PATHS))
    total_proxy_slots = max(1, len(events) * len(PROXY_FIELD_PATHS))
    direct_hits = 0
    proxy_hits = 0
    direct_field_counts: Counter[str] = Counter()
    proxy_field_counts: Counter[str] = Counter()
    for event in events:
        payload = _payload(event)
        for field in DIRECT_FIELD_PATHS:
            if _first_value(payload, field) is not None:
                direct_hits += 1
                direct_field_counts[field] += 1
        for field in PROXY_FIELD_PATHS:
            if _first_value(payload, field) is not None:
                proxy_hits += 1
                proxy_field_counts[field] += 1
    return (
        round(direct_hits / total_direct_slots, 4),
        round(proxy_hits / total_proxy_slots, 4),
        {
            "direct_field_counts": dict(direct_field_counts.most_common()),
            "proxy_field_counts": dict(proxy_field_counts.most_common()),
            "direct_fields_checked": list(DIRECT_FIELD_PATHS),
            "proxy_fields_checked": list(PROXY_FIELD_PATHS),
        },
    )


def _excluded_telemetry_summary(events: list[dict[str, Any]], candidate_events: list[dict[str, Any]]) -> dict[str, Any]:
    candidate_ids = {id(event) for event in candidate_events}
    excluded_categories: Counter[str] = Counter()
    excluded_reasons: Counter[str] = Counter()
    excluded_legacy_like = 0
    for event in events:
        if id(event) in candidate_ids:
            continue
        payload = _payload(event)
        classification = _candidate_classification(event)
        reason = str(classification["candidate_classification_reason"])
        category = str(event.get("_category") or event.get("event_type") or "unknown")
        excluded_categories[category] += 1
        excluded_reasons[reason] += 1
        if _legacy_is_candidate_event(payload):
            excluded_legacy_like += 1
    return {
        "excluded_total": max(0, len(events) - len(candidate_events)),
        "excluded_legacy_candidate_like_events": excluded_legacy_like,
        "by_category": dict(excluded_categories.most_common()),
        "by_reason": dict(excluded_reasons.most_common()),
    }


def _unknown_precision_metrics(
    legacy_candidate_events: list[dict[str, Any]],
    candidate_events: list[dict[str, Any]],
) -> dict[str, Any]:
    legacy_unknown = sum(1 for event in legacy_candidate_events if _phase(_payload(event))[0] == "UNKNOWN")
    refined_unknown = sum(1 for event in candidate_events if _phase(_payload(event))[0] == "UNKNOWN")
    removed_unknown = max(0, legacy_unknown - refined_unknown)
    return {
        "legacy_candidate_like_events": len(legacy_candidate_events),
        "refined_candidate_events": len(candidate_events),
        "legacy_unknown_lifecycle_events": legacy_unknown,
        "refined_unknown_lifecycle_events": refined_unknown,
        "unknown_lifecycle_events_removed_by_filter": removed_unknown,
        "legacy_unknown_lifecycle_rate": round(legacy_unknown / len(legacy_candidate_events), 4) if legacy_candidate_events else 0.0,
        "refined_unknown_lifecycle_rate": round(refined_unknown / len(candidate_events), 4) if candidate_events else 0.0,
        "unknown_inflation_removed_rate": round(removed_unknown / legacy_unknown, 4) if legacy_unknown else 0.0,
    }


def _classification_summary(candidate_events: list[dict[str, Any]]) -> dict[str, Any]:
    reasons: Counter[str] = Counter()
    confidence: Counter[str] = Counter()
    for event in candidate_events:
        classification = _candidate_classification(event)
        reasons[str(classification["candidate_classification_reason"])] += 1
        confidence[str(classification["candidate_classification_confidence"])] += 1
    return {
        "candidate_classification_reasons": dict(reasons.most_common()),
        "candidate_classification_confidence": dict(confidence.most_common()),
    }


def build_lifecycle_truth_tables(
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
    legacy_candidate_events = [event for event in events if _legacy_is_candidate_event(_payload(event))]
    candidate_events = [event for event in events if _candidate_classification(event)["is_candidate_event"]]

    starter_candidates: list[dict[str, Any]] = []
    missed_starter_candidates: list[dict[str, Any]] = []
    blocked_before_ev: list[dict[str, Any]] = []
    blocked_after_ev: list[dict[str, Any]] = []
    time_unsafe: list[dict[str, Any]] = []
    liquidity_orderbook: list[dict[str, Any]] = []
    lifecycle_distribution: Counter[str] = Counter()
    lifecycle_by_asset: defaultdict[str, Counter[str]] = defaultdict(Counter)
    ev_null_reasons: Counter[str] = Counter()
    ev_null_reasons_by_asset: defaultdict[str, Counter[str]] = defaultdict(Counter)

    for event in candidate_events:
        payload = _payload(event)
        phase, _phase_inference = _phase(payload)
        asset = _asset_from(event, payload)
        lifecycle_distribution[phase] += 1
        lifecycle_by_asset[asset][phase] += 1
        for reason in _null_reasons(payload):
            ev_null_reasons[reason] += 1
            ev_null_reasons_by_asset[asset][reason] += 1

        is_starter, starter_inference = _is_starter_candidate(payload)
        if is_starter:
            starter_candidates.append(_candidate_row(event, table="starter_candidates", inference=starter_inference))
            if _is_blocked(payload):
                missed_starter_candidates.append(_candidate_row(event, table="missed_starter_candidates", inference=starter_inference))

        before, before_inference = _blocked_before_ev(payload)
        if before:
            blocked_before_ev.append(_candidate_row(event, table="candidate_blocked_before_ev", inference=before_inference))

        after, after_inference = _blocked_after_ev(payload)
        if after:
            blocked_after_ev.append(_candidate_row(event, table="candidate_blocked_after_ev", inference=after_inference))

        if _reason_contains(payload, TIME_UNSAFE_TOKENS):
            time_unsafe.append(_candidate_row(event, table="time_unsafe_candidates", inference="direct_observed" if _skip_reason(payload) else "proxy_inferred"))

        if _reason_contains(payload, ORDERBOOK_LIQUIDITY_TOKENS):
            liquidity_orderbook.append(_candidate_row(event, table="liquidity_or_orderbook_blocked_candidates", inference="direct_observed"))

    phase2_coverage = build_phase2_coverage_from_events(events)
    direct_rate, proxy_rate, field_counts = _count_direct_proxy(candidate_events)
    coverage_gaps = list(phase2_coverage.get("coverage_gaps", []))
    if not events:
        replay_truth_confidence = "INSUFFICIENT"
        replay_truth_quality = "NO_EVIDENCE"
    elif direct_rate >= 0.35 and not coverage_gaps:
        replay_truth_confidence = "HIGH_DIRECT"
        replay_truth_quality = "READY_DIRECT_TRUTH_TABLES"
    elif direct_rate >= 0.20:
        replay_truth_confidence = "MEDIUM_DIRECT"
        replay_truth_quality = "PARTIAL_DIRECT_TRUTH_TABLES"
    elif proxy_rate > direct_rate:
        replay_truth_confidence = "LOW_PROXY"
        replay_truth_quality = "PROXY_HEAVY_TRUTH_TABLES"
    else:
        replay_truth_confidence = "LOW_EVIDENCE"
        replay_truth_quality = "INCOMPLETE_TRUTH_TABLES"

    structural_count = sum(len(table) for table in (time_unsafe, liquidity_orderbook))
    model_count = len(blocked_before_ev) + len(blocked_after_ev)
    if structural_count > model_count:
        no_entry_hypothesis = "structural_timing_liquidity_orderbook"
    elif model_count > structural_count:
        no_entry_hypothesis = "model_or_ev_pipeline"
    elif structural_count or model_count:
        no_entry_hypothesis = "mixed_structural_and_model"
    else:
        no_entry_hypothesis = "insufficient_candidate_evidence"

    phase_loss = lifecycle_distribution.most_common(1)[0][0] if lifecycle_distribution else "UNKNOWN"
    asset_failures = {
        asset_key: {
            "blocked_before_ev": sum(1 for row in blocked_before_ev if row["asset"] == asset_key),
            "blocked_after_ev": sum(1 for row in blocked_after_ev if row["asset"] == asset_key),
            "time_unsafe": sum(1 for row in time_unsafe if row["asset"] == asset_key),
            "liquidity_or_orderbook": sum(1 for row in liquidity_orderbook if row["asset"] == asset_key),
        }
        for asset_key in sorted({row["asset"] for row in [*blocked_before_ev, *blocked_after_ev, *time_unsafe, *liquidity_orderbook]})
    }

    report = {
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
        "does_not_claim_profitability": True,
        "does_not_authorize_runtime_decisions": True,
        "events_loaded": len(events),
        "candidate_events": len(candidate_events),
        "candidate_classification_version": "truth_table_candidate_classification_v1",
        "excluded_telemetry_counts": _excluded_telemetry_summary(events, candidate_events),
        "unknown_lifecycle_precision_metrics": _unknown_precision_metrics(legacy_candidate_events, candidate_events),
        "bad_json_lines": bad_json_lines,
        "replay_truth_confidence": replay_truth_confidence,
        "replay_truth_quality": replay_truth_quality,
        "direct_field_rate": direct_rate,
        "proxy_field_rate": proxy_rate,
        "evidence_completeness": {
            "events_loaded": len(events),
            "candidate_events": len(candidate_events),
            "coverage_gap_count": len(coverage_gaps),
            "coverage_gaps": coverage_gaps,
            **_classification_summary(candidate_events),
            **field_counts,
        },
        "tables": {
            "starter_candidates": starter_candidates,
            "missed_starter_candidates": missed_starter_candidates,
            "candidate_blocked_before_ev": blocked_before_ev,
            "candidate_blocked_after_ev": blocked_after_ev,
            "time_unsafe_candidates": time_unsafe,
            "liquidity_or_orderbook_blocked_candidates": liquidity_orderbook,
            "lifecycle_phase_distribution": {
                "counts": dict(lifecycle_distribution.most_common()),
                "by_asset": {asset: dict(counter.most_common()) for asset, counter in sorted(lifecycle_by_asset.items())},
            },
            "ev_null_reason_distribution": {
                "counts": dict(ev_null_reasons.most_common()),
                "by_asset": {asset: dict(counter.most_common()) for asset, counter in sorted(ev_null_reasons_by_asset.items())},
            },
            "direct_vs_proxy_evidence_quality": {
                "phase2_status": phase2_coverage.get("status"),
                "requirements": phase2_coverage.get("requirements", {}),
                "direct_field_rate": direct_rate,
                "proxy_field_rate": proxy_rate,
            },
        },
        "research_questions": {
            "did_timing_decay_kill_executable_edge": {
                "answer": "evidence_present" if time_unsafe else "not_observed",
                "time_unsafe_candidate_count": len(time_unsafe),
                "uncertainty": "requires source review; no profitability claim",
            },
            "did_liquidity_become_ready_too_late": {
                "answer": "evidence_present" if liquidity_orderbook else "not_observed",
                "liquidity_or_orderbook_block_count": len(liquidity_orderbook),
                "uncertainty": "readiness timestamps are only conclusive when direct fields are present",
            },
            "which_lifecycle_phase_loses_most_candidates": {
                "answer": phase_loss,
                "distribution": dict(lifecycle_distribution.most_common()),
            },
            "are_btc_and_eth_failing_differently": {
                "answer": "compare_asset_counts",
                "asset_failure_counts": asset_failures,
            },
            "are_candidates_blocked_before_ev_or_after_ev": {
                "blocked_before_ev": len(blocked_before_ev),
                "blocked_after_ev": len(blocked_after_ev),
            },
            "are_no_entry_causes_structural_or_model_related": {
                "hypothesis": no_entry_hypothesis,
                "structural_count": structural_count,
                "model_count": model_count,
                "confidence": "evidence_index_only",
            },
            "how_much_unknown_inflation_comes_from_telemetry_pollution": {
                **_unknown_precision_metrics(legacy_candidate_events, candidate_events),
                "excluded_telemetry_counts": _excluded_telemetry_summary(events, candidate_events),
            },
            "does_direct_field_maturity_improve_after_filtering": {
                "answer": "compare_against_prior_reports",
                "direct_field_rate_after_filtering": direct_rate,
                "proxy_field_rate_after_filtering": proxy_rate,
            },
            "are_pre_ev_blocks_still_dominant_after_cleanup": {
                "answer": len(blocked_before_ev) > len(blocked_after_ev),
                "blocked_before_ev": len(blocked_before_ev),
                "blocked_after_ev": len(blocked_after_ev),
            },
            "does_lifecycle_phase_ranking_stabilize": {
                "answer": phase_loss,
                "distribution": dict(lifecycle_distribution.most_common()),
                "uncertainty": "requires multiple filtered runs",
            },
        },
    }
    return report


def write_lifecycle_truth_tables(report: dict[str, Any], *, report_dir: str | Path = DEFAULT_REPORT_DIR) -> Path:
    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    date_part = _date_part(
        str(report.get("date_from")),
        str(report.get("date_to")),
        dict(report.get("time_filter", {})),
        str(report.get("run_id") or ""),
    )
    output_path = output_dir / f"lifecycle_truth_tables_{date_part}.json"
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return output_path


def print_summary(report: dict[str, Any]) -> None:
    tables = report.get("tables", {})
    print("Lifecycle Truth Tables")
    print(
        "range={start}..{end} run_id={run_id} events={events} candidates={candidates} confidence={confidence} quality={quality}".format(
            start=report.get("date_from"),
            end=report.get("date_to"),
            run_id=report.get("run_id") or "",
            events=report.get("events_loaded"),
            candidates=report.get("candidate_events"),
            confidence=report.get("replay_truth_confidence"),
            quality=report.get("replay_truth_quality"),
        )
    )
    print(
        "starter={starter} missed_starter={missed} before_ev={before} after_ev={after} time_unsafe={time} liquidity_orderbook={liq}".format(
            starter=len(tables.get("starter_candidates", [])),
            missed=len(tables.get("missed_starter_candidates", [])),
            before=len(tables.get("candidate_blocked_before_ev", [])),
            after=len(tables.get("candidate_blocked_after_ev", [])),
            time=len(tables.get("time_unsafe_candidates", [])),
            liq=len(tables.get("liquidity_or_orderbook_blocked_candidates", [])),
        )
    )
    print(f"direct_field_rate={report.get('direct_field_rate')} proxy_field_rate={report.get('proxy_field_rate')}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build offline lifecycle truth tables from quant JSONL replay evidence.")
    parser.add_argument("--date", default=None, help="Single date in YYYY-MM-DD format.")
    parser.add_argument("--from", dest="date_from", default=None, help="Start date in YYYY-MM-DD format.")
    parser.add_argument("--to", dest="date_to", default=None, help="End date in YYYY-MM-DD format.")
    parser.add_argument("--since", default=None, help="UTC start time HH:MM for same-day filtering; inclusive.")
    parser.add_argument("--until", default=None, help="UTC end time HH:MM for same-day filtering; exclusive.")
    parser.add_argument("--run-id", default=None, help="Exact run_id to isolate; events without this run_id are excluded.")
    parser.add_argument("--base-dir", default=str(DEFAULT_QUANT_DATA_DIR), help="Quant data root directory.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Output report directory.")
    parser.add_argument("--no-write", action="store_true", help="Do not write lifecycle_truth_tables JSON.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_lifecycle_truth_tables(
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
        path = write_lifecycle_truth_tables(report, report_dir=args.report_dir)
        print(f"wrote_report={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
