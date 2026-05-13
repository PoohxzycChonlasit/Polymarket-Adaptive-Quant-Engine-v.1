from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:  # pragma: no cover - script execution path
    from tools.ev_field_coverage import build_ev_field_coverage_report
    from tools.replay_analyzer import (
        DEFAULT_QUANT_DATA_DIR,
        DEFAULT_REPORT_DIR,
        analyze_replay,
        build_time_filter,
        load_replay_events,
    )
    from tools.session_runtime_evaluator import evaluate_session_runtime
except ModuleNotFoundError:  # pragma: no cover - direct `python tools/...` path
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from tools.ev_field_coverage import build_ev_field_coverage_report
    from tools.replay_analyzer import (
        DEFAULT_QUANT_DATA_DIR,
        DEFAULT_REPORT_DIR,
        analyze_replay,
        build_time_filter,
        load_replay_events,
    )
    from tools.session_runtime_evaluator import evaluate_session_runtime


IDENTITY_FIELDS = (
    "candidate_trace_id",
    "condition_id",
    "token_id",
    "side",
)
MISSING_FIELDS = (
    "candidate_trace_id",
    "parent_candidate_trace_id",
    "condition_id",
    "token_id",
    "side",
    "market_key",
    "market_slug",
    "lifecycle_phase",
    "candidate_id",
    "decision_id",
    "risk_state",
    "true_probability",
    "fair_value",
    "ev_after_spread",
)
FIELD_ALIASES = {
    "candidate_trace_id": ("candidate_trace_id", "candidate_id", "signal_id", "parent_candidate_trace_id"),
    "parent_candidate_trace_id": ("parent_candidate_trace_id", "parent_candidate_id", "parent_signal_id"),
    "condition_id": ("condition_id", "conditionId", "market_condition_id", "clob_condition_id"),
    "token_id": ("token_id", "tokenId", "clob_token_id", "clobTokenId", "yes_token_id", "no_token_id"),
    "side": ("side", "asset_side", "outcome", "best_side", "token_side"),
    "market_key": ("market_key", "market_id", "source_market_id", "condition_id", "market_slug", "slug"),
    "market_slug": ("market_slug", "slug", "marketSlug"),
    "lifecycle_phase": ("lifecycle_phase",),
    "candidate_id": ("candidate_id", "candidate_trace_id", "signal_id"),
    "decision_id": ("decision_id", "decision_trace_id"),
    "risk_state": ("risk_state", "risk_decision", "risk_status", "risk_mode", "risk_reject_reason"),
    "true_probability": ("true_probability", "model_probability", "probability", "model_probability_yes", "model_probability_no", "p_yes", "p_no", "model_p_yes", "model_p_no"),
    "fair_value": ("fair_value", "model_fair_value", "fair_value_yes", "fair_value_no"),
    "ev_after_spread": ("ev_after_spread", "expected_value", "model_ev", "ev"),
}
MICROSTRUCTURE_KEYS = (
    "ORDERBOOK_NOT_READY",
    "ORDERBOOK_GATE",
    "LIQUIDITY_NOT_READY",
    "LIQUIDITY_GATE",
    "SPREAD_NOT_EXECUTABLE",
    "SPREAD_GATE",
)
LIFECYCLE_KEYS = (
    "CUTOFF_OR_TIME_BLOCK",
    "TIME_CUTOFF_GATE",
    "LIFECYCLE_PHASE_BLOCK",
    "LIFECYCLE_PHASE_GATE",
)
LIFECYCLE_SECOND_BOUNDARIES = {
    "OPENING_SCAN": 0,
    "ACTIVE_INVENTORY_TRADING": 35,
    "PROFIT_MANAGEMENT": 240,
    "FINAL_DERISK": 270,
    "CLOSED_OR_UNSAFE": 300,
}
DECISION_FUNNEL_STAGES = (
    "candidate_seen",
    "orderbook_ready",
    "candidate_ready",
    "current_cycle_model_eligible",
    "probability_model_called",
    "model_output_visible",
    "fair_value_visible",
    "EV_visible",
)
NON_DECISION_PRODUCERS = (
    "market_snapshots",
    "system_health",
    "execution_log",
    "risk_log",
    "trade_journal",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and value.strip().upper() not in {"UNKNOWN", "--", "NONE", "NULL"}
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return True


def _bool_true(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "ok", "ready", "visible", "called"}
    return False


def _first_present(payload: dict[str, Any], field: str) -> tuple[bool, str]:
    for key in FIELD_ALIASES.get(field, (field,)):
        if _present(payload.get(key)):
            return True, key
    return False, ""


def _payload(event: dict[str, Any]) -> dict[str, Any]:
    raw_payload = event.get("payload")
    if isinstance(raw_payload, dict):
        merged = dict(raw_payload)
        for key in ("run_id", "timestamp_utc", "event_type", "mode", "_category"):
            if key in event and key not in merged:
                merged[key] = event[key]
        return merged
    return dict(event)


def _producer(event: dict[str, Any]) -> str:
    return str(event.get("_category") or event.get("event_category") or event.get("producer") or "unknown")


def _event_timestamp_seconds(payload: dict[str, Any]) -> float | None:
    value = str(payload.get("timestamp_utc") or payload.get("timestamp") or "").strip()
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _payload_timestamp_seconds(payload: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = str(payload.get(key) or "").strip()
        if not value:
            continue
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    return None


def _epoch_stage_timestamp_seconds(payload: dict[str, Any], *second_keys: str, at_keys: tuple[str, ...] = ()) -> float | None:
    direct = _payload_timestamp_seconds(payload, *at_keys)
    if direct is not None:
        return direct
    epoch_start = _int_or_none(payload.get("market_epoch_start") or payload.get("epoch_start") or payload.get("epoch_start_ts"))
    if epoch_start is None:
        return None
    for key in second_keys:
        second = _int_or_none(payload.get(key))
        if second is not None:
            return float(epoch_start + second)
    for key in second_keys:
        if key.endswith("_second"):
            continue
        remaining = _int_or_none(payload.get(key))
        if remaining is not None:
            return float(epoch_start + _second_from_remaining(remaining))
    return None


def _market_sync_key(payload: dict[str, Any]) -> str:
    for key in ("condition_id", "market_slug", "market_id", "source_market_id", "market_key", "candidate_trace_id"):
        value = str(payload.get(key) or "").strip()
        if value:
            return f"{key}:{value}"
    yes_token = str(payload.get("yes_token_id") or "").strip()
    no_token = str(payload.get("no_token_id") or "").strip()
    if yes_token and no_token:
        return f"token_pair:{yes_token}|{no_token}"
    token = str(payload.get("token_id") or "").strip()
    if token:
        return f"token:{token}"
    ticker = str(payload.get("ticker") or payload.get("asset") or "").strip()
    if ticker:
        return f"ticker:{ticker.upper()}"
    return "unknown"


def _top(counter: Counter[str], limit: int = 5) -> list[dict[str, Any]]:
    return [{"reason": key, "count": value} for key, value in counter.most_common(limit)]


def _top_dict(mapping: dict[str, Any], limit: int = 5) -> dict[str, Any]:
    counter = Counter({str(k): int(v) for k, v in dict(mapping or {}).items() if isinstance(v, (int, float))})
    return dict(counter.most_common(limit))


def _counts_from_pairs(value: Any) -> dict[str, int]:
    if isinstance(value, dict):
        return {str(k): int(v) for k, v in value.items() if isinstance(v, (int, float))}
    counts: dict[str, int] = {}
    if isinstance(value, list):
        for item in value:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                try:
                    counts[str(item[0])] = int(item[1])
                except (TypeError, ValueError):
                    continue
            elif isinstance(item, dict):
                key = item.get("reason") or item.get("state") or item.get("name") or item.get("key")
                count = item.get("count")
                if key is not None and isinstance(count, (int, float)):
                    counts[str(key)] = int(count)
    return counts


def _int_or_none(value: Any) -> int | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _float_or_none(value: Any) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _second_from_remaining(value: Any) -> int | None:
    remaining = _int_or_none(value)
    if remaining is None:
        return None
    return max(0, min(300, 300 - remaining))


def _range(values: list[int]) -> dict[str, Any]:
    if not values:
        return {"min": None, "max": None, "avg": None}
    return {
        "min": min(values),
        "max": max(values),
        "avg": round(sum(values) / len(values), 2),
    }


def _median(values: list[int]) -> int | float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return round((ordered[mid - 1] + ordered[mid]) / 2.0, 2)


def _p95(values: list[int]) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * 0.95))))
    return ordered[index]


def _lifecycle_phase_from_second(second: int | None) -> str:
    if second is None:
        return "UNKNOWN"
    if second < LIFECYCLE_SECOND_BOUNDARIES["ACTIVE_INVENTORY_TRADING"]:
        return "OPENING_SCAN"
    if second < LIFECYCLE_SECOND_BOUNDARIES["PROFIT_MANAGEMENT"]:
        return "ACTIVE_INVENTORY_TRADING"
    if second < LIFECYCLE_SECOND_BOUNDARIES["FINAL_DERISK"]:
        return "PROFIT_MANAGEMENT"
    if second <= LIFECYCLE_SECOND_BOUNDARIES["CLOSED_OR_UNSAFE"]:
        return "FINAL_DERISK"
    return "CLOSED_OR_UNSAFE"


def _candidate_timing_relevant(event: dict[str, Any], payload: dict[str, Any]) -> bool:
    producer = _producer(event)
    if producer in {"decision_log", "risk_log", "execution_log", "trade_journal"}:
        return True
    if producer == "market_snapshots":
        return any(
            _present(payload.get(field))
            for field in (
                "candidate_trace_id",
                "candidate_id",
                "signal_id",
                "lifecycle_phase",
                "seconds_remaining",
                "seconds_until_close",
                "first_seen_second",
                "model_activation_state",
            )
        )
    return any(
        _present(payload.get(field))
        for field in (
            "candidate_trace_id",
            "candidate_id",
            "signal_id",
            "decision_id",
            "lifecycle_phase",
            "model_activation_state",
            "candidate_block_stage",
        )
    )


def _lifecycle_unknown_reason(event: dict[str, Any], payload: dict[str, Any]) -> str:
    if not _candidate_timing_relevant(event, payload):
        return "NON_CANDIDATE_TELEMETRY"
    if not _present(payload.get("lifecycle_phase")) and not _present(payload.get("model_activation_lifecycle_phase")):
        if _int_or_none(payload.get("seconds_remaining") or payload.get("seconds_until_close")) is None:
            return "MISSING_TIMING_AND_LIFECYCLE_FIELDS"
        return "MISSING_LIFECYCLE_SERIALIZATION"
    return "UNKNOWN_LIFECYCLE_LABEL"


def _event_identity_readiness(payload: dict[str, Any]) -> str:
    candidate_trace = _present(payload.get("candidate_trace_id"))
    condition = _present(payload.get("condition_id"))
    token = _present(payload.get("token_id"))
    side = _present(payload.get("side"))
    parent = _present(payload.get("parent_candidate_trace_id"))
    if candidate_trace and condition and token and side and parent:
        return "DIRECT"
    if candidate_trace and condition and token and side:
        return "STRONG"
    if condition and token and side:
        return "WEAK"
    if candidate_trace or condition or token or side:
        return "PROXY"
    return "UNKNOWN"


def _summarize_run_ids(events: list[dict[str, Any]], requested_run_id: str | None) -> tuple[str, list[dict[str, Any]]]:
    counts = Counter(str(event.get("run_id") or "missing_run_id") for event in events)
    run_ids = [{"run_id": run_id, "event_count": count} for run_id, count in counts.most_common(5)]
    if requested_run_id:
        return requested_run_id, run_ids
    if len(counts) == 1:
        return next(iter(counts)), run_ids
    if counts:
        return f"mixed:{counts.most_common(1)[0][0]}", run_ids
    return "", run_ids


def _time_range(date: str, since: str | None, until: str | None, events: list[dict[str, Any]]) -> dict[str, Any]:
    timestamps = sorted(str(event.get("timestamp_utc") or "") for event in events if event.get("timestamp_utc"))
    return {
        "date": date,
        "since": since,
        "until": until,
        "first_event_utc": timestamps[0] if timestamps else "",
        "last_event_utc": timestamps[-1] if timestamps else "",
        "events_loaded": len(events),
    }


def _paper_activity(events: list[dict[str, Any]], replay_payload: dict[str, Any]) -> dict[str, Any]:
    orders = fills = exits = 0
    for event in events:
        payload = _payload(event)
        text = " ".join(
            str(payload.get(key) or event.get(key) or "")
            for key in ("event", "event_type", "action", "status", "order_type", "side")
        ).lower()
        if "order" in text and any(token in text for token in ("submit", "created", "placed", "intent")):
            orders += 1
        if "fill" in text or "filled" in text:
            fills += 1
        if any(token in text for token in ("trade_close", "close", "exit", "sell")):
            exits += 1
    return {
        "orders": orders,
        "fills": fills,
        "exits": exits or int(replay_payload.get("total_trades") or 0),
        "replay_total_trades": int(replay_payload.get("total_trades") or 0),
    }


def _skip_reasons(events: list[dict[str, Any]], replay_payload: dict[str, Any], runtime_payload: dict[str, Any]) -> list[dict[str, Any]]:
    counts = Counter(_counts_from_pairs(replay_payload.get("top_skip_reasons")))
    runtime_skips = runtime_payload.get("skip_summary", {}).get("top_skip_reasons", [])
    counts.update(_counts_from_pairs(runtime_skips))
    for event in events:
        payload = _payload(event)
        reason = (
            payload.get("skip_reason")
            or payload.get("block_reason")
            or payload.get("candidate_block_reason")
            or payload.get("reason")
        )
        if _present(reason):
            counts[str(reason)] += 1
    return _top(counts)


def _missing_fields_by_producer(events: list[dict[str, Any]]) -> dict[str, Any]:
    totals: Counter[str] = Counter()
    missing: dict[str, Counter[str]] = defaultdict(Counter)
    alias_hits: dict[str, Counter[str]] = defaultdict(Counter)
    for event in events:
        producer = _producer(event)
        payload = _payload(event)
        totals[producer] += 1
        for field in MISSING_FIELDS:
            present, source = _first_present(payload, field)
            if present:
                if source != field:
                    alias_hits[producer][f"{field}<-{source}"] += 1
            else:
                missing[producer][field] += 1
    return {
        producer: {
            "events": totals[producer],
            "top_missing_fields": dict(missing[producer].most_common(6)),
            "alias_field_hits": dict(alias_hits[producer].most_common(6)),
        }
        for producer in sorted(totals)
    }


def _model_output_propagation(events: list[dict[str, Any]]) -> dict[str, Any]:
    fields = ("true_probability", "fair_value", "ev_after_spread", "side")
    totals: Counter[str] = Counter()
    canonical_present: dict[str, Counter[str]] = defaultdict(Counter)
    alias_present: dict[str, Counter[str]] = defaultdict(Counter)
    missing: dict[str, Counter[str]] = defaultdict(Counter)
    source_counts: dict[str, Counter[str]] = defaultdict(Counter)
    missing_reasons: dict[str, Counter[str]] = defaultdict(Counter)
    for event in events:
        producer = _producer(event)
        payload = _payload(event)
        totals[producer] += 1
        for field in fields:
            if _present(payload.get(field)):
                canonical_present[producer][field] += 1
                source = str(payload.get(f"{field}_source") or payload.get(f"{field}_propagation_status") or "canonical")
                source_counts[producer][f"{field}:{source}"] += 1
                continue
            alias = ""
            for candidate_alias in FIELD_ALIASES.get(field, (field,)):
                if candidate_alias == field:
                    continue
                if _present(payload.get(candidate_alias)):
                    alias = candidate_alias
                    break
            if alias:
                alias_present[producer][f"{field}<-{alias}"] += 1
            else:
                missing[producer][field] += 1
                reason = str(
                    payload.get(f"{field}_missing_reason")
                    or payload.get(f"{field}_null_reason")
                    or payload.get(f"{field}_propagation_status")
                    or "field_not_emitted"
                )
                missing_reasons[producer][f"{field}:{reason}"] += 1
    return {
        producer: {
            "events": totals[producer],
            "canonical_present": dict(canonical_present[producer].most_common()),
            "alias_present": dict(alias_present[producer].most_common()),
            "missing": dict(missing[producer].most_common()),
            "source_counts": dict(source_counts[producer].most_common(8)),
            "missing_reason_counts": dict(missing_reasons[producer].most_common(8)),
        }
        for producer in sorted(totals)
    }


def _identity_from_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    trace_events = 0
    for event in events:
        payload = _payload(event)
        if any(_present(payload.get(field)) for field in IDENTITY_FIELDS):
            trace_events += 1
        counts[_event_identity_readiness(payload)] += 1
    return {
        "event_identity_readiness_counts": dict(counts),
        "trace_identity_events": trace_events,
        "event_direct_or_strong_count": counts["DIRECT"] + counts["STRONG"],
    }


def _field_status_from_ev_report(ev_report: dict[str, Any]) -> dict[str, Any]:
    confidence_counts = dict(ev_report.get("candidate_trace_confidence_counts") or {})
    trace_break_counts = dict(ev_report.get("ev_trace_break_phase_counts") or {})
    diagnostics = dict(ev_report.get("candidate_trace_confidence_diagnostics") or {})
    ev_never_visible = int(trace_break_counts.get("EV_NEVER_VISIBLE") or trace_break_counts.get("NO_EV_VISIBLE") or 0)
    confirmed = int(diagnostics.get("ev_visibility_confirmed_count") or ev_report.get("ev_visibility_confirmed_count") or 0)
    attempted = int(diagnostics.get("ev_visibility_attempted_count") or ev_report.get("ev_visibility_attempted_count") or 0)
    if confirmed:
        status = "EV_VISIBLE"
    elif attempted:
        status = "EV_ATTEMPTED_NOT_VISIBLE"
    elif ev_never_visible:
        status = "EV_NEVER_VISIBLE"
    else:
        status = "UNKNOWN"
    return {
        "ev_visibility_status": status,
        "EV_NEVER_VISIBLE": ev_never_visible,
        "ev_visibility_attempted": attempted,
        "ev_visibility_confirmed": confirmed,
        "risk_layer_trace_readiness": float(ev_report.get("risk_layer_trace_readiness") or 0.0),
        "candidate_chain_trace_confidence": confidence_counts,
        "dominant_model_gap": ev_report.get("dominant_model_state_gap") or "UNKNOWN",
        "model_attempt_eligibility_rate": ev_report.get("model_attempt_eligibility_rate", 0.0),
    }


def _ev_risk_chain_gap(ev_report: dict[str, Any], ev_status: dict[str, Any]) -> dict[str, Any]:
    diagnostic = dict(ev_report.get("ev_risk_chain_gap_diagnostics") or {})
    if diagnostic:
        return diagnostic
    likely_gap_types: list[str] = []
    if ev_status.get("EV_NEVER_VISIBLE"):
        likely_gap_types.append("field_not_emitted")
    if float(ev_status.get("risk_layer_trace_readiness") or 0.0) == 0.0:
        likely_gap_types.append("producer_handoff_gap")
    classification = "EV_AND_RISK_CHAIN_NOT_VISIBLE" if len(likely_gap_types) == 2 else (
        "EV_CHAIN_NOT_VISIBLE" if ev_status.get("EV_NEVER_VISIBLE") else "RISK_CHAIN_NOT_VISIBLE"
    )
    return {
        "classification": classification,
        "ev_never_visible_count": ev_status.get("EV_NEVER_VISIBLE", 0),
        "risk_layer_trace_readiness": ev_status.get("risk_layer_trace_readiness", 0.0),
        "likely_gap_types": likely_gap_types or ["insufficient_evidence"],
        "explanation": "fallback compact classification; run current EV field coverage for full diagnostics",
    }


def _event_chain_status(event_identity: dict[str, Any], ev_status: dict[str, Any]) -> dict[str, Any]:
    event_ready = int(event_identity.get("event_direct_or_strong_count") or 0)
    chain_counts = dict(ev_status.get("candidate_chain_trace_confidence") or {})
    chain_ready = int(chain_counts.get("DIRECT") or 0) + int(chain_counts.get("STRONG") or 0)
    if event_ready and not chain_ready:
        status = "EVENT_IDENTITY_READY_CHAIN_NOT_CONFIRMED"
    elif event_ready and chain_ready:
        status = "EVENT_AND_CHAIN_HAVE_STRONG_IDENTITY"
    elif chain_ready and not event_ready:
        status = "CHAIN_READY_EVENT_IDENTITY_NOT_VISIBLE"
    else:
        status = "IDENTITY_NOT_READY"
    return {
        "status": status,
        "event_direct_or_strong_count": event_ready,
        "chain_direct_or_strong_count": chain_ready,
        "note": "Event identity is per emitted event; chain confidence requires lifecycle continuity.",
    }


def _orderbook_health(events: list[dict[str, Any]], replay_payload: dict[str, Any], ev_report: dict[str, Any]) -> dict[str, Any]:
    state_counts: Counter[str] = Counter()
    for event in events:
        payload = _payload(event)
        for key in ("orderbook_state_classification", "orderbook_state", "market_readiness_state"):
            if _present(payload.get(key)):
                state_counts[str(payload[key])] += 1
                break
    blockers = Counter(_counts_from_pairs(replay_payload.get("orderbook_readiness_reasons")))
    blockers.update(
        {
            key: int(ev_report.get("model_attempt_gate_counts", {}).get(key, 0))
            for key in MICROSTRUCTURE_KEYS
            if int(ev_report.get("model_attempt_gate_counts", {}).get(key, 0))
        }
    )
    dominant_blocker = blockers.most_common(1)[0][0] if blockers else "UNKNOWN"
    return {
        "state_counts": dict(state_counts.most_common(5)),
        "dominant_blocker": dominant_blocker,
        "orderbook_blockers": dict(blockers.most_common(5)),
        "average_orderbook_age_ms": replay_payload.get("average_orderbook_age_ms", 0.0),
        "max_orderbook_age_ms": replay_payload.get("max_orderbook_age_ms", 0.0),
    }


def _blockers(ev_report: dict[str, Any], replay_payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    pre_risk = Counter({str(k): int(v) for k, v in dict(ev_report.get("pre_risk_block_cause_counts") or {}).items()})
    gates = Counter({str(k): int(v) for k, v in dict(ev_report.get("model_attempt_gate_counts") or {}).items()})
    micro = Counter({key: pre_risk.get(key, 0) + gates.get(key, 0) for key in MICROSTRUCTURE_KEYS if pre_risk.get(key, 0) + gates.get(key, 0)})
    lifecycle = Counter({key: pre_risk.get(key, 0) + gates.get(key, 0) for key in LIFECYCLE_KEYS if pre_risk.get(key, 0) + gates.get(key, 0)})
    lifecycle.update(_counts_from_pairs(replay_payload.get("adaptive_cutoff_denied_reasons")))
    lifecycle.update(_counts_from_pairs(replay_payload.get("micro_timing_denied_reasons")))
    return (
        {
            "counts": {k: v for k, v in micro.most_common() if v},
            "dominant": micro.most_common(1)[0][0] if micro else "UNKNOWN",
            "share": ev_report.get("microstructure_related_pre_risk_block_share", 0.0),
        },
        {
            "counts": {k: v for k, v in lifecycle.most_common() if v},
            "dominant": lifecycle.most_common(1)[0][0] if lifecycle else "UNKNOWN",
            "cutoff_block_count": replay_payload.get("cutoff_block_count", 0),
            "share": ev_report.get("timing_related_pre_risk_block_share", 0.0),
        },
    )


def _model_activation_diagnostics(events: list[dict[str, Any]], ev_report: dict[str, Any]) -> dict[str, Any]:
    state_counts: Counter[str] = Counter()
    block_group_counts: Counter[str] = Counter()
    block_reason_counts: Counter[str] = Counter()
    eligibility_counts: Counter[str] = Counter()
    by_lifecycle: dict[str, Counter[str]] = defaultdict(Counter)
    seconds_remaining: list[int] = []
    for event in events:
        payload = _payload(event)
        state = str(payload.get("model_activation_state") or "").strip()
        group = str(payload.get("model_activation_block_group") or "").strip()
        reason = str(payload.get("model_activation_block_reason") or "").strip()
        if state:
            state_counts[state] += 1
        if group:
            block_group_counts[group] += 1
        if reason:
            block_reason_counts[reason] += 1
        if "model_attempt_eligible" in payload:
            eligibility_counts["eligible" if bool(payload.get("model_attempt_eligible")) else "not_eligible"] += 1
        lifecycle = str(payload.get("model_activation_lifecycle_phase") or payload.get("lifecycle_phase") or "UNKNOWN")
        if group:
            by_lifecycle[lifecycle][group] += 1
        remaining = payload.get("model_activation_seconds_remaining", payload.get("seconds_remaining"))
        try:
            if remaining is not None and str(remaining).strip() != "":
                seconds_remaining.append(int(float(remaining)))
        except (TypeError, ValueError):
            pass

    fallback_gate_counts = Counter({
        str(key): int(value)
        for key, value in dict(ev_report.get("model_attempt_gate_counts") or {}).items()
        if isinstance(value, (int, float)) and int(value)
    })
    dominant_group = block_group_counts.most_common(1)[0][0] if block_group_counts else (
        fallback_gate_counts.most_common(1)[0][0] if fallback_gate_counts else "UNKNOWN"
    )
    return {
        "model_activation_state_counts": dict(state_counts.most_common()),
        "model_activation_block_group_counts": dict(block_group_counts.most_common()),
        "model_activation_block_reason_top": dict(block_reason_counts.most_common(5)),
        "model_attempt_eligibility_observed": dict(eligibility_counts),
        "model_attempt_gate_counts_from_ev_report": dict(fallback_gate_counts.most_common()),
        "dominant_model_activation_block_group": dominant_group,
        "model_activation_by_lifecycle_phase": {
            phase: dict(counts.most_common(3))
            for phase, counts in sorted(by_lifecycle.items())
        },
        "seconds_remaining_range": {
            "min": min(seconds_remaining) if seconds_remaining else None,
            "max": max(seconds_remaining) if seconds_remaining else None,
        },
        "interpretation": "Runtime activation fields are observational only; missing fields fall back to EV coverage gate counts.",
    }


def _model_handoff_diagnostics(events: list[dict[str, Any]]) -> dict[str, Any]:
    stage_counts: Counter[str] = Counter()
    missing_reason_counts: Counter[str] = Counter()
    output_source_counts: Counter[str] = Counter()
    call_counts: Counter[str] = Counter()
    output_counts: Counter[str] = Counter()
    runtime_return_call_counts: Counter[str] = Counter()
    pre_model_gate_counts: Counter[str] = Counter()
    pre_model_gate_group_counts: Counter[str] = Counter()
    producer_observation_counts: Counter[str] = Counter()
    candidate_ready_gate_counts: Counter[str] = Counter()
    active_candidate_ready_gate_counts: Counter[str] = Counter()
    by_producer: dict[str, Counter[str]] = defaultdict(Counter)
    by_lifecycle: dict[str, Counter[str]] = defaultdict(Counter)
    candidate_ready_called = 0
    candidate_ready_not_called = 0
    active_candidate_ready_called = 0
    active_candidate_ready_not_called = 0
    runtime_candidate_ready_called = 0
    runtime_candidate_ready_not_called = 0
    runtime_active_candidate_ready_called = 0
    runtime_active_candidate_ready_not_called = 0
    called_without_output = 0

    for event in events:
        payload = _payload(event)
        producer = _producer(event)
        lifecycle = str(payload.get("model_activation_lifecycle_phase") or payload.get("lifecycle_phase") or "UNKNOWN")
        stage = str(payload.get("model_handoff_stage") or "").strip()
        called = bool(payload.get("probability_model_called"))
        output_visible = bool(payload.get("probability_model_output_visible")) or any(
            _present(payload.get(field))
            for field in ("true_probability", "fair_value", "model_probability_yes", "model_probability_no", "p_yes", "p_no")
        )
        if not stage:
            if output_visible:
                stage = "MODEL_OUTPUT_SERIALIZED"
            elif called:
                stage = "MODEL_CALLED_OUTPUT_NOT_VISIBLE"
            elif _present(payload.get("model_activation_state")) or _present(payload.get("probability_model_stage")):
                stage = "PRE_MODEL_GATE"
            else:
                stage = "UNKNOWN"
        stage_counts[stage] += 1
        by_producer[producer][stage] += 1
        by_lifecycle[lifecycle][stage] += 1
        call_counts["called" if called else "not_called"] += 1
        output_counts["visible" if output_visible else "not_visible"] += 1
        if called and not output_visible:
            called_without_output += 1
        reason = str(
            payload.get("model_output_missing_reason")
            or payload.get("model_activation_block_reason")
            or payload.get("probability_model_gate_reason")
            or ""
        ).strip()
        if reason:
            missing_reason_counts[reason] += 1
        source = str(payload.get("model_output_source") or payload.get("true_probability_source") or payload.get("fair_value_source") or "").strip()
        if source:
            output_source_counts[source] += 1
        gate_name = str(payload.get("pre_model_gate_name") or "").strip()
        gate_group = str(payload.get("pre_model_gate_group") or payload.get("model_activation_block_group") or "").strip()
        is_producer_observation = gate_name == "PRODUCER_PRE_MODEL_OBSERVATION" or gate_group == "PRODUCER_NOT_RESPONSIBLE"
        if not is_producer_observation:
            runtime_return_call_counts["called" if called else "not_called"] += 1
        if is_producer_observation:
            producer_observation_counts[producer] += 1
        elif gate_name and gate_name != "MODEL_OUTPUT_AVAILABLE":
            pre_model_gate_counts[gate_name] += 1
        if gate_group and gate_group not in {"MODEL_READY", "PRODUCER_NOT_RESPONSIBLE"}:
            pre_model_gate_group_counts[gate_group] += 1

        candidate_second = _int_or_none(payload.get("first_candidate_ready_second"))
        if candidate_second is None:
            candidate_remaining = _int_or_none(payload.get("first_tradable_seconds_remaining"))
            candidate_second = _second_from_remaining(candidate_remaining) if candidate_remaining else None
        if candidate_second is not None:
            if gate_name and gate_name not in {"MODEL_OUTPUT_AVAILABLE", "PRODUCER_PRE_MODEL_OBSERVATION"}:
                candidate_ready_gate_counts[gate_name] += 1
            if called:
                candidate_ready_called += 1
            else:
                candidate_ready_not_called += 1
            if not is_producer_observation:
                if called:
                    runtime_candidate_ready_called += 1
                else:
                    runtime_candidate_ready_not_called += 1
            if LIFECYCLE_SECOND_BOUNDARIES["ACTIVE_INVENTORY_TRADING"] <= candidate_second < LIFECYCLE_SECOND_BOUNDARIES["PROFIT_MANAGEMENT"]:
                if gate_name and gate_name not in {"MODEL_OUTPUT_AVAILABLE", "PRODUCER_PRE_MODEL_OBSERVATION"}:
                    active_candidate_ready_gate_counts[gate_name] += 1
                if called:
                    active_candidate_ready_called += 1
                else:
                    active_candidate_ready_not_called += 1
                if not is_producer_observation:
                    if called:
                        runtime_active_candidate_ready_called += 1
                    else:
                        runtime_active_candidate_ready_not_called += 1

    dominant_stage = stage_counts.most_common(1)[0][0] if stage_counts else "UNKNOWN"
    return {
        "probability_model_call_counts": dict(call_counts),
        "runtime_return_path_probability_model_call_counts": dict(runtime_return_call_counts),
        "probability_model_output_visibility_counts": dict(output_counts),
        "model_handoff_stage_counts": dict(stage_counts.most_common()),
        "dominant_model_handoff_stage": dominant_stage,
        "pre_model_gate_counts": dict(pre_model_gate_counts.most_common(10)),
        "pre_model_gate_group_counts": dict(pre_model_gate_group_counts.most_common(10)),
        "producer_pre_model_observation_counts": dict(producer_observation_counts.most_common(10)),
        "candidate_ready_pre_model_gate_counts": dict(candidate_ready_gate_counts.most_common(10)),
        "active_candidate_ready_pre_model_gate_counts": dict(active_candidate_ready_gate_counts.most_common(10)),
        "model_output_missing_reason_top": dict(missing_reason_counts.most_common(8)),
        "model_output_source_counts": dict(output_source_counts.most_common(8)),
        "model_handoff_by_producer": {
            producer: dict(counts.most_common(5))
            for producer, counts in sorted(by_producer.items())
        },
        "model_handoff_by_lifecycle_phase": {
            phase: dict(counts.most_common(5))
            for phase, counts in sorted(by_lifecycle.items())
        },
        "candidate_ready_model_called_count": candidate_ready_called,
        "candidate_ready_model_not_called_count": candidate_ready_not_called,
        "active_candidate_ready_model_called_count": active_candidate_ready_called,
        "active_candidate_ready_model_not_called_count": active_candidate_ready_not_called,
        "candidate_ready_runtime_return_model_called_count": runtime_candidate_ready_called,
        "candidate_ready_runtime_return_model_not_called_count": runtime_candidate_ready_not_called,
        "active_candidate_ready_runtime_return_model_called_count": runtime_active_candidate_ready_called,
        "active_candidate_ready_runtime_return_model_not_called_count": runtime_active_candidate_ready_not_called,
        "model_called_without_output_count": called_without_output,
        "interpretation": "Model handoff diagnostics separate function-call visibility from output serialization; they do not force model execution or infer missing probability values.",
    }


def _decision_funnel_event(event: dict[str, Any], payload: dict[str, Any]) -> bool:
    if _producer(event) != "decision_log":
        return False
    gate_name = str(payload.get("pre_model_gate_name") or "").strip()
    gate_group = str(payload.get("pre_model_gate_group") or payload.get("model_activation_block_group") or "").strip()
    if gate_name == "PRODUCER_PRE_MODEL_OBSERVATION" or gate_group == "PRODUCER_NOT_RESPONSIBLE":
        return False
    return any(
        _present(payload.get(field))
        for field in (
            "candidate_trace_id",
            "candidate_id",
            "signal_id",
            "decision_id",
            "skip_reason",
            "candidate_block_stage",
            "candidate_block_reason",
            "model_activation_state",
            "pre_model_gate_name",
            "probability_model_called",
            "probability_model_output_visible",
            "model_attempt_eligible",
            "current_cycle_model_eligible",
        )
    )


def _lifecycle_context(payload: dict[str, Any]) -> str:
    phase = str(payload.get("model_activation_lifecycle_phase") or payload.get("lifecycle_phase") or "").strip()
    if phase:
        return phase
    for key in ("first_candidate_ready_second", "first_orderbook_ready_second", "first_seen_second"):
        second = _int_or_none(payload.get(key))
        if second is not None:
            return _lifecycle_phase_from_second(second)
    return "UNKNOWN"


def _orderbook_context(payload: dict[str, Any]) -> str:
    for key in (
        "orderbook_state_classification",
        "orderbook_state",
        "market_readiness_state",
        "orderbook_readiness_state",
    ):
        value = str(payload.get(key) or "").strip()
        if value:
            return value
    gate_name = str(payload.get("pre_model_gate_name") or "").strip()
    gate_group = str(payload.get("pre_model_gate_group") or payload.get("model_activation_block_group") or "").strip()
    reason = str(
        payload.get("orderbook_readiness_reason")
        or payload.get("orderbook_unavailable_reason")
        or payload.get("model_output_missing_reason")
        or payload.get("model_activation_block_reason")
        or ""
    ).strip()
    if gate_name == "ORDERBOOK_COMPLETENESS_GATE" or gate_group == "ORDERBOOK_GATE":
        return reason or "not_ready"
    if _stage_probability_model_called(payload) or _stage_model_output_visible(payload):
        return "ready"
    return "UNKNOWN"


def _stage_orderbook_ready(payload: dict[str, Any]) -> bool:
    for key in ("orderbook_ready", "orderbook_complete", "market_ready"):
        if key in payload:
            return _bool_true(payload.get(key))
    state = _orderbook_context(payload).strip().lower()
    if state in {"ready", "ok", "healthy", "complete", "available", "executable", "usable"}:
        return True
    if state in {"unavailable", "empty_book", "warmup_pending", "not_ready", "missing", "stale", "none"}:
        return False
    gate_name = str(payload.get("pre_model_gate_name") or "").strip()
    gate_group = str(payload.get("pre_model_gate_group") or payload.get("model_activation_block_group") or "").strip()
    if gate_name == "ORDERBOOK_COMPLETENESS_GATE" or gate_group == "ORDERBOOK_GATE":
        return False
    if _present(payload.get("best_bid")) and _present(payload.get("best_ask")):
        return True
    return _stage_probability_model_called(payload) or _stage_model_output_visible(payload)


def _stage_candidate_ready(payload: dict[str, Any]) -> bool:
    for key in ("candidate_ready", "model_candidate_ready", "candidate_ready_for_model"):
        if key in payload:
            return _bool_true(payload.get(key))
    if _int_or_none(payload.get("first_candidate_ready_second")) is not None:
        return True
    if _int_or_none(payload.get("first_tradable_seconds_remaining")) is not None:
        return True
    return _stage_model_eligible(payload) or _stage_probability_model_called(payload) or _stage_model_output_visible(payload)


def _stage_model_eligible(payload: dict[str, Any]) -> bool:
    for key in ("current_cycle_model_eligible", "model_attempt_eligible", "model_eligible_current_cycle"):
        if key in payload:
            return _bool_true(payload.get(key))
    gate_name = str(payload.get("pre_model_gate_name") or "").strip()
    if gate_name == "MODEL_OUTPUT_AVAILABLE":
        return True
    return _stage_probability_model_called(payload) or _stage_model_output_visible(payload)


def _stage_probability_model_called(payload: dict[str, Any]) -> bool:
    return _bool_true(payload.get("probability_model_called"))


def _stage_model_output_visible(payload: dict[str, Any]) -> bool:
    return _bool_true(payload.get("probability_model_output_visible")) or any(
        _present(payload.get(field))
        for field in ("true_probability", "model_probability", "model_probability_yes", "model_probability_no", "p_yes", "p_no")
    )


def _stage_fair_value_visible(payload: dict[str, Any]) -> bool:
    return any(_present(payload.get(field)) for field in FIELD_ALIASES["fair_value"])


def _stage_ev_visible(payload: dict[str, Any]) -> bool:
    return any(_present(payload.get(field)) for field in FIELD_ALIASES["ev_after_spread"])


def _decision_stage_passed(stage: str, payload: dict[str, Any]) -> bool:
    if stage == "candidate_seen":
        return True
    if stage == "orderbook_ready":
        return _stage_orderbook_ready(payload)
    if stage == "candidate_ready":
        return _stage_candidate_ready(payload)
    if stage == "current_cycle_model_eligible":
        return _stage_model_eligible(payload)
    if stage == "probability_model_called":
        return _stage_probability_model_called(payload)
    if stage == "model_output_visible":
        return _stage_model_output_visible(payload)
    if stage == "fair_value_visible":
        return _stage_fair_value_visible(payload)
    if stage == "EV_visible":
        return _stage_ev_visible(payload)
    return False


def _decision_stage_blocker(stage: str, payload: dict[str, Any]) -> tuple[str, str]:
    gate_name = str(payload.get("pre_model_gate_name") or "").strip()
    gate_group = str(payload.get("pre_model_gate_group") or payload.get("model_activation_block_group") or "").strip()
    reason = str(
        payload.get("model_output_missing_reason")
        or payload.get("model_activation_block_reason")
        or payload.get("probability_model_gate_reason")
        or payload.get("candidate_block_reason")
        or payload.get("skip_reason")
        or ""
    ).strip()
    if stage == "orderbook_ready":
        orderbook_state = _orderbook_context(payload)
        if gate_name == "ORDERBOOK_COMPLETENESS_GATE":
            return gate_name, orderbook_state if orderbook_state != "UNKNOWN" else (reason or "UNKNOWN")
        return "ORDERBOOK_NOT_READY", orderbook_state if orderbook_state != "UNKNOWN" else (reason or "UNKNOWN")
    if stage in {"candidate_ready", "current_cycle_model_eligible", "probability_model_called"}:
        return gate_name or gate_group or "MODEL_GATE_UNKNOWN", reason or "UNKNOWN"
    if stage == "model_output_visible":
        return "MODEL_OUTPUT_NOT_VISIBLE", reason or "output_not_serialized"
    if stage == "fair_value_visible":
        return "FAIR_VALUE_NOT_VISIBLE", reason or "fair_value_not_serialized"
    if stage == "EV_visible":
        return "EV_NOT_VISIBLE", reason or "ev_not_serialized"
    return "UNKNOWN", reason or "UNKNOWN"


def _decision_runtime_eligibility_funnel(events: list[dict[str, Any]]) -> dict[str, Any]:
    stage_survivors: dict[str, int] = {stage: 0 for stage in DECISION_FUNNEL_STAGES}
    stage_reached: dict[str, int] = {stage: 0 for stage in DECISION_FUNNEL_STAGES}
    independent_observed: dict[str, int] = {stage: 0 for stage in DECISION_FUNNEL_STAGES}
    blockers: dict[str, Counter[str]] = {stage: Counter() for stage in DECISION_FUNNEL_STAGES}
    blocker_reasons: dict[str, Counter[str]] = {stage: Counter() for stage in DECISION_FUNNEL_STAGES}
    lifecycle_by_stage: dict[str, Counter[str]] = {stage: Counter() for stage in DECISION_FUNNEL_STAGES}
    orderbook_by_stage: dict[str, Counter[str]] = {stage: Counter() for stage in DECISION_FUNNEL_STAGES}
    included = 0
    excluded: Counter[str] = Counter()

    for event in events:
        payload = _payload(event)
        producer = _producer(event)
        if not _decision_funnel_event(event, payload):
            excluded[producer] += 1
            continue
        included += 1
        lifecycle = _lifecycle_context(payload)
        orderbook = _orderbook_context(payload)
        for stage in DECISION_FUNNEL_STAGES:
            if _decision_stage_passed(stage, payload):
                independent_observed[stage] += 1
        for stage in DECISION_FUNNEL_STAGES:
            stage_reached[stage] += 1
            lifecycle_by_stage[stage][lifecycle] += 1
            orderbook_by_stage[stage][orderbook] += 1
            if _decision_stage_passed(stage, payload):
                stage_survivors[stage] += 1
                continue
            blocker, reason = _decision_stage_blocker(stage, payload)
            blockers[stage][blocker] += 1
            blocker_reasons[stage][reason] += 1
            break

    stages: dict[str, Any] = {}
    for stage in DECISION_FUNNEL_STAGES:
        dominant_blocker = blockers[stage].most_common(1)[0][0] if blockers[stage] else "NONE"
        dominant_reason = blocker_reasons[stage].most_common(1)[0][0] if blocker_reasons[stage] else "NONE"
        stages[stage] = {
            "reached_count": stage_reached[stage],
            "survivor_count": stage_survivors[stage],
            "independent_observed_count": independent_observed[stage],
            "blocked_count": max(0, stage_reached[stage] - stage_survivors[stage]),
            "dominant_blocker": dominant_blocker,
            "dominant_blocker_reason": dominant_reason,
            "blocker_counts": dict(blockers[stage].most_common(5)),
            "blocker_reason_counts": dict(blocker_reasons[stage].most_common(5)),
            "lifecycle_phase_distribution": dict(lifecycle_by_stage[stage].most_common(5)),
            "orderbook_state_distribution": dict(orderbook_by_stage[stage].most_common(5)),
        }

    first_blockers = Counter()
    for stage in DECISION_FUNNEL_STAGES:
        first_blockers.update(blockers[stage])
    dominant_blocker = first_blockers.most_common(1)[0][0] if first_blockers else "NONE"
    path_reachable = stage_survivors["probability_model_called"] > 0
    return {
        "scope": "decision_log_only_runtime_eligibility",
        "stage_order": list(DECISION_FUNNEL_STAGES),
        "decision_candidate_event_count": included,
        "excluded_producer_counts": dict(excluded.most_common()),
        "excluded_producers": list(NON_DECISION_PRODUCERS),
        "stages": stages,
        "dominant_decision_path_blocker": dominant_blocker,
        "probability_model_path_reachable_after_filtering": path_reachable,
        "interpretation": (
            "Decision-only funnel excludes passive snapshots, system health, risk/execution/trade handoff events, "
            "and producer-not-responsible observations; it is offline observability only."
        ),
    }


def _decision_cycle_orderbook_readiness_audit(events: list[dict[str, Any]]) -> dict[str, Any]:
    token_status: Counter[str] = Counter()
    token_pair_presence: Counter[str] = Counter()
    fetch_attempt_visibility: Counter[str] = Counter()
    fetch_result_origin: Counter[str] = Counter()
    fetch_result: Counter[str] = Counter()
    completeness: Counter[str] = Counter()
    ask_presence: Counter[str] = Counter()
    spread_normalization: Counter[str] = Counter()
    recovery_visibility: Counter[str] = Counter()
    recovery_exit_reasons: Counter[str] = Counter()
    lifecycle: Counter[str] = Counter()
    blockers: Counter[str] = Counter()
    blocker_reasons: Counter[str] = Counter()
    candidate_ready_without_current_orderbook = 0
    lifecycle_candidate_ready = 0
    current_cycle_orderbook_ready = 0
    events_seen = 0

    for event in events:
        payload = _payload(event)
        if not _decision_funnel_event(event, payload):
            continue
        events_seen += 1
        lifecycle[_lifecycle_context(payload)] += 1

        token_id_present = _present(payload.get("token_id"))
        yes_token_present = _present(payload.get("yes_token_id"))
        no_token_present = _present(payload.get("no_token_id"))
        token_pair_ready = yes_token_present and no_token_present
        token_ready = token_id_present or token_pair_ready
        token_warning = str(payload.get("token_mapping_warning") or "").strip()
        if token_pair_ready:
            token_pair_presence["yes_no_pair_present"] += 1
        elif token_id_present:
            token_pair_presence["token_id_only"] += 1
        else:
            token_pair_presence["missing_all_token_ids"] += 1
        if token_warning:
            token_pair_presence[f"token_mapping_warning:{token_warning}"] += 1

        if not token_ready:
            token_status["missing_token_fields"] += 1
        elif token_warning:
            token_status[f"token_warning:{token_warning}"] += 1
        else:
            token_status["token_fields_present"] += 1

        explicit_price_fields = any(
            field in payload
            for field in ("yes_bid", "yes_ask", "no_bid", "no_ask", "best_bid", "best_ask", "bid", "ask")
        )
        orderbook_error_present = _present(payload.get("orderbook_error")) or _present(payload.get("clob_error_category"))
        readiness_reason_present = _present(payload.get("orderbook_readiness_reason")) or _present(payload.get("orderbook_unavailable_reason"))
        orderbook_gate_present = (
            str(payload.get("pre_model_gate_name") or "") == "ORDERBOOK_COMPLETENESS_GATE"
            or str(payload.get("pre_model_gate_group") or payload.get("model_activation_block_group") or "") == "ORDERBOOK_GATE"
        )
        fetch_visible = any(
            _present(payload.get(field))
            for field in (
                "orderbook_readiness_reason",
                "orderbook_unavailable_reason",
                "orderbook_error",
                "clob_error_category",
                "orderbook_state_classification",
                "yes_ask",
                "no_ask",
                "best_ask",
                "ask",
            )
        )
        fetch_attempt_visibility["visible"] += int(fetch_visible)
        fetch_attempt_visibility["not_visible"] += int(not fetch_visible)
        if explicit_price_fields:
            fetch_result_origin["explicit_price_fields"] += 1
        elif orderbook_error_present:
            fetch_result_origin["orderbook_error_or_clob_category"] += 1
        elif readiness_reason_present:
            fetch_result_origin["local_readiness_classification"] += 1
        elif orderbook_gate_present:
            fetch_result_origin["pre_model_orderbook_gate_classification"] += 1
        else:
            fetch_result_origin["no_fetch_result_fields"] += 1

        orderbook_state = _orderbook_context(payload)
        fetch_result[orderbook_state] += 1

        yes_ask = _float_or_none(payload.get("yes_ask"))
        no_ask = _float_or_none(payload.get("no_ask"))
        best_ask = _float_or_none(payload.get("best_ask") or payload.get("ask"))
        complete = (
            orderbook_state == "ready"
            or (yes_ask is not None and yes_ask > 0 and no_ask is not None and no_ask > 0)
            or (best_ask is not None and best_ask > 0)
        )
        completeness["complete_bid_ask"] += int(complete)
        completeness["incomplete_bid_ask"] += int(not complete)
        for label, value in (("yes_ask", yes_ask), ("no_ask", no_ask), ("best_ask", best_ask)):
            if value is None:
                ask_presence[f"{label}_missing"] += 1
            elif value > 0:
                ask_presence[f"{label}_positive"] += 1
            else:
                ask_presence[f"{label}_zero"] += 1

        spread_value = _float_or_none(payload.get("spread"))
        spread_limit = _float_or_none(payload.get("spread_limit"))
        spread_normalized = payload.get("spread_normalized")
        if spread_normalized is True or (spread_value is not None and spread_limit is not None and spread_value <= spread_limit):
            spread_normalization["ready"] += 1
        elif spread_normalized is False:
            spread_normalization["not_ready"] += 1
        else:
            spread_normalization["unknown"] += 1
        if payload.get("empty_book_recovery_attempted") is True:
            recovery_visibility["attempted"] += 1
        else:
            recovery_visibility["not_attempted_or_not_serialized"] += 1
        if payload.get("empty_book_recovery_success") is True:
            recovery_visibility["success"] += 1
        if payload.get("empty_book_recovery_failed") is True:
            recovery_visibility["failed"] += 1
        recovery_reason = str(
            payload.get("recovery_branch_skipped_reason")
            or payload.get("recovery_exit_reason")
            or ""
        ).strip()
        if recovery_reason:
            recovery_exit_reasons[recovery_reason] += 1

        current_ready = _stage_orderbook_ready(payload)
        current_cycle_orderbook_ready += int(current_ready)
        candidate_ready = _stage_candidate_ready(payload)
        lifecycle_candidate_ready += int(candidate_ready)
        if candidate_ready and not current_ready:
            candidate_ready_without_current_orderbook += 1

        if current_ready:
            blockers["ready"] += 1
            continue
        reason = str(
            payload.get("orderbook_readiness_reason")
            or payload.get("orderbook_unavailable_reason")
            or payload.get("orderbook_error")
            or payload.get("model_activation_block_reason")
            or payload.get("model_output_missing_reason")
            or orderbook_state
            or "UNKNOWN"
        ).strip()
        if not token_ready or token_warning:
            blocker = "TOKEN_MAPPING_BLOCK"
        elif orderbook_state in {
            "empty_book",
            "unavailable",
            "orderbook_unavailable",
            "orderbook_not_ready",
            "not_ready",
            "warmup_pending",
            "stale_orderbook",
        }:
            blocker = "CURRENT_CYCLE_ORDERBOOK_NOT_COMPLETE"
        elif not complete:
            blocker = "MISSING_BID_ASK_COMPLETENESS"
        elif spread_normalized is False:
            blocker = "SPREAD_NOT_NORMALIZED"
        else:
            blocker = "ORDERBOOK_READY_FALSE_UNCLASSIFIED"
        blockers[blocker] += 1
        blocker_reasons[reason or "UNKNOWN"] += 1

    dominant = blockers.most_common(1)[0][0] if blockers else "NONE"
    return {
        "scope": "decision_log_only_current_cycle_orderbook_readiness",
        "decision_candidate_event_count": events_seen,
        "orderbook_ready_conditions": [
            "token_id or yes/no token ids present without token mapping warning",
            "current decision-cycle orderbook fetch produces positive YES/NO ask or canonical ready state",
            "orderbook_readiness_reason and orderbook_unavailable_reason are empty",
            "market_readiness_state remains ready after time, liquidity, and spread checks",
            "spread_normalized is not false for model-stage readiness",
        ],
        "token_mapping_status_counts": dict(token_status.most_common()),
        "token_pair_presence_counts": dict(token_pair_presence.most_common()),
        "orderbook_fetch_attempt_visibility_counts": dict(fetch_attempt_visibility.most_common()),
        "orderbook_fetch_result_origin_counts": dict(fetch_result_origin.most_common()),
        "orderbook_fetch_result_counts": dict(fetch_result.most_common()),
        "orderbook_completeness_counts": dict(completeness.most_common()),
        "ask_presence_counts": dict(ask_presence.most_common()),
        "spread_normalization_counts": dict(spread_normalization.most_common()),
        "empty_book_recovery_visibility_counts": dict(recovery_visibility.most_common()),
        "empty_book_recovery_exit_reason_counts": dict(recovery_exit_reasons.most_common(8)),
        "lifecycle_phase_distribution": dict(lifecycle.most_common()),
        "current_cycle_orderbook_ready_count": current_cycle_orderbook_ready,
        "lifecycle_candidate_ready_count": lifecycle_candidate_ready,
        "candidate_ready_without_current_orderbook_count": candidate_ready_without_current_orderbook,
        "dominant_decision_cycle_orderbook_blocker": dominant,
        "blocker_counts": dict(blockers.most_common(8)),
        "blocker_reason_counts": dict(blocker_reasons.most_common(8)),
        "dashboard_global_orderbook_note": (
            "Global/dashboard orderbook health can be healthy while the decision-producing event is not orderbook-ready; "
            "this audit only counts the current decision-cycle payload."
        ),
        "interpretation": "Offline observability only; does not widen orderbook acceptance or force model execution.",
    }


def _global_vs_decision_orderbook_sync_audit(events: list[dict[str, Any]]) -> dict[str, Any]:
    producer_state_counts: dict[str, Counter[str]] = defaultdict(Counter)
    ready_by_producer: Counter[str] = Counter()
    ask_sync: Counter[str] = Counter()
    latency_buckets: Counter[str] = Counter()
    decay_classification: Counter[str] = Counter()
    lifecycle_latency_buckets: dict[str, Counter[str]] = defaultdict(Counter)
    lifecycle_decay_loss: Counter[str] = Counter()
    pipeline_stage_latencies: dict[str, list[int]] = defaultdict(list)
    pipeline_stage_unobservable: Counter[str] = Counter()
    freshness_loss_by_stage: Counter[str] = Counter()
    latency_attribution: Counter[str] = Counter()
    global_ready_by_key: dict[str, dict[str, Any]] = {}
    global_ready_by_key_run: dict[tuple[str, str], dict[str, Any]] = {}
    latest_candidate_ready_by_key: dict[str, dict[str, Any]] = {}
    latest_candidate_ready_by_key_run: dict[tuple[str, str], dict[str, Any]] = {}
    first_candidate_ready_delays_ms: list[int] = []
    latest_candidate_ready_delays_ms: list[int] = []
    active_latest_candidate_ready_delays_ms: list[int] = []
    latest_candidate_ready_unobservable = 0
    last_global_ready_to_decision_created_ms: list[int] = []
    same_run_global_ready_to_decision_ms: list[int] = []
    mixed_run_global_ready_to_decision_ms: list[int] = []
    active_same_run_global_ready_to_decision_ms: list[int] = []
    per_run_global_ready_to_decision_ms: dict[str, list[int]] = defaultdict(list)
    global_ready_event_count = 0
    decision_event_count = 0
    decision_ready_count = 0
    same_market_global_ready_before_decision = 0
    fresh_global_ready_before_decision = 0
    global_ready_before_decision_but_local_incomplete = 0
    decision_without_prior_global_ready = 0
    active_decisions_after_global_ready = 0
    active_decisions_exceeding_5s = 0
    final_derisk_freshness_loss = 0
    delays_ms: list[int] = []

    pipeline_stages = (
        "market_snapshot_received_to_token_mapping_ready",
        "token_mapping_ready_to_orderbook_fetch_complete",
        "orderbook_fetch_complete_to_candidate_ready",
        "candidate_ready_to_decision_event_created",
        "decision_event_created_to_decision_serialized",
        "decision_serialized_to_model_eligibility_check",
        "market_snapshot_received_to_decision_serialized",
    )

    def add_stage_latency(stage: str, start_ts: float | None, end_ts: float | None) -> None:
        if start_ts is None or end_ts is None or end_ts < start_ts:
            pipeline_stage_unobservable[stage] += 1
            return
        pipeline_stage_latencies[stage].append(int(round((end_ts - start_ts) * 1000)))

    def stage_stats() -> dict[str, dict[str, Any]]:
        return {
            stage: {
                "sample_count": len(pipeline_stage_latencies.get(stage, [])),
                "unobservable_count": pipeline_stage_unobservable.get(stage, 0),
                "median_ms": _median(pipeline_stage_latencies.get(stage, [])),
                "p95_ms": _p95(pipeline_stage_latencies.get(stage, [])),
                "range_ms": _range(pipeline_stage_latencies.get(stage, [])),
            }
            for stage in pipeline_stages
        }

    def attribution(payload: dict[str, Any], delay_ms: int | None, decay_reason: str | None) -> str:
        token_ready = _present(payload.get("token_id")) or (_present(payload.get("yes_token_id")) and _present(payload.get("no_token_id")))
        token_warning = _present(payload.get("token_mapping_warning"))
        if payload.get("empty_book_recovery_attempted") is True or _int_or_none(payload.get("empty_book_recovery_retry_count")):
            return "latency_caused_by_recovery_retries"
        if not token_ready or token_warning:
            return "latency_caused_by_token_preload_or_mapping"
        if decay_reason in {"global_ready_but_cutoff_reached"}:
            return "latency_caused_by_lifecycle_timing"
        if delay_ms is not None and delay_ms > 10000:
            return "latency_caused_by_decision_batching_or_polling"
        if decay_reason and "incomplete" in decay_reason:
            return "latency_caused_by_serialization_gap"
        if not any(key in payload for key in ("yes_ask", "no_ask", "best_ask", "ask")):
            return "latency_caused_by_serialization_gap"
        return "latency_cause_unclassified"

    def record_delay(target: list[int], start_ts: float | None, end_ts: float | None) -> bool:
        if start_ts is None or end_ts is None or end_ts < start_ts:
            return False
        target.append(int(round((end_ts - start_ts) * 1000)))
        return True

    def latency_bucket(delay_ms: int | None) -> str:
        if delay_ms is None:
            return "unknown_timestamp"
        if delay_ms <= 1000:
            return "<=1s"
        if delay_ms <= 3000:
            return "<=3s"
        if delay_ms <= 5000:
            return "<=5s"
        if delay_ms <= 10000:
            return "<=10s"
        return ">10s"

    def local_decay_reason(payload: dict[str, Any], orderbook_state: str) -> str:
        reason = str(
            payload.get("orderbook_readiness_reason")
            or payload.get("orderbook_unavailable_reason")
            or payload.get("orderbook_error")
            or payload.get("model_activation_block_reason")
            or payload.get("model_output_missing_reason")
            or orderbook_state
            or ""
        ).lower()
        if "cutoff" in reason or "time_unsafe" in reason or "hard_close" in reason:
            return "global_ready_but_cutoff_reached"
        if "stale" in reason:
            return "global_ready_but_local_stale"
        if payload.get("spread_normalized") is False or "spread" in reason:
            return "global_ready_but_spread_invalid"
        if "empty" in reason or orderbook_state == "empty_book":
            return "global_ready_but_local_empty"
        if orderbook_state in {"unavailable", "orderbook_unavailable", "warmup_pending", "not_ready"}:
            return f"global_ready_but_local_{orderbook_state}"
        return "global_ready_but_local_incomplete_unknown"

    for event in events:
        payload = _payload(event)
        producer = _producer(event)
        run_id = str(payload.get("run_id") or "unknown_run")
        sync_key_for_event = _market_sync_key(payload)
        event_ts_for_ready = _event_timestamp_seconds(payload)
        orderbook_state = _orderbook_context(payload)
        producer_state_counts[producer][orderbook_state] += 1

        yes_ask = _float_or_none(payload.get("yes_ask"))
        no_ask = _float_or_none(payload.get("no_ask"))
        best_ask = _float_or_none(payload.get("best_ask") or payload.get("ask"))
        yes_positive = yes_ask is not None and yes_ask > 0
        no_positive = no_ask is not None and no_ask > 0
        best_positive = best_ask is not None and best_ask > 0
        if yes_positive and no_positive:
            ask_sync[f"{producer}:yes_no_asks_positive"] += 1
        elif yes_positive:
            ask_sync[f"{producer}:yes_ask_only"] += 1
        elif no_positive:
            ask_sync[f"{producer}:no_ask_only"] += 1
        elif best_positive:
            ask_sync[f"{producer}:single_best_ask_positive"] += 1
        else:
            ask_sync[f"{producer}:asks_not_positive_or_not_serialized"] += 1

        global_ready = (
            producer != "decision_log"
            and (
                orderbook_state == "ready"
                or (yes_positive and no_positive)
                or best_positive
            )
        )
        if global_ready:
            ready_by_producer[producer] += 1
            global_ready_event_count += 1
            ready_record = {
                "timestamp_seconds": _event_timestamp_seconds(payload),
                "producer": producer,
                "orderbook_state": orderbook_state,
                "run_id": run_id,
            }
            global_ready_by_key[sync_key_for_event] = ready_record
            global_ready_by_key_run[(sync_key_for_event, run_id)] = ready_record

        if not _decision_funnel_event(event, payload):
            if _stage_candidate_ready(payload):
                latest_candidate_ready_by_key[sync_key_for_event] = {
                    "timestamp_seconds": event_ts_for_ready,
                    "run_id": run_id,
                    "producer": producer,
                }
                latest_candidate_ready_by_key_run[(sync_key_for_event, run_id)] = latest_candidate_ready_by_key[sync_key_for_event]
            continue

        decision_event_count += 1
        decision_ready = _stage_orderbook_ready(payload) and (orderbook_state == "ready" or yes_positive and no_positive or best_positive)
        decision_ready_count += int(decision_ready)
        sync_key = _market_sync_key(payload)
        matched_global = global_ready_by_key.get(sync_key)
        matched_global_same_run = global_ready_by_key_run.get((sync_key, run_id))
        if matched_global is None:
            decision_without_prior_global_ready += 1
            if _stage_candidate_ready(payload):
                latest_candidate_ready_by_key[sync_key_for_event] = {
                    "timestamp_seconds": event_ts_for_ready,
                    "run_id": run_id,
                    "producer": producer,
                }
                latest_candidate_ready_by_key_run[(sync_key_for_event, run_id)] = latest_candidate_ready_by_key[sync_key_for_event]
            continue
        same_market_global_ready_before_decision += 1
        lifecycle = _lifecycle_context(payload)
        if lifecycle == "ACTIVE_INVENTORY_TRADING":
            active_decisions_after_global_ready += 1
        decision_ts = _event_timestamp_seconds(payload)
        global_ts = matched_global.get("timestamp_seconds")
        global_same_run_ts = matched_global_same_run.get("timestamp_seconds") if matched_global_same_run else None
        delay_ms: int | None = None
        if decision_ts is not None and global_ts is not None and decision_ts >= global_ts:
            delay_ms = int(round((decision_ts - global_ts) * 1000))
            delays_ms.append(delay_ms)
            if delay_ms <= 5000:
                fresh_global_ready_before_decision += 1
            if lifecycle == "ACTIVE_INVENTORY_TRADING" and delay_ms > 5000:
                active_decisions_exceeding_5s += 1
        decision_created_ts = _payload_timestamp_seconds(payload, "decision_timestamp") or decision_ts
        if record_delay(last_global_ready_to_decision_created_ms, global_ts, decision_created_ts):
            pass
        if record_delay(mixed_run_global_ready_to_decision_ms, global_ts, decision_created_ts):
            per_run_global_ready_to_decision_ms[run_id].append(mixed_run_global_ready_to_decision_ms[-1])
        if record_delay(same_run_global_ready_to_decision_ms, global_same_run_ts, decision_created_ts):
            if lifecycle == "ACTIVE_INVENTORY_TRADING":
                active_same_run_global_ready_to_decision_ms.append(same_run_global_ready_to_decision_ms[-1])
        bucket = latency_bucket(delay_ms)
        latency_buckets[bucket] += 1
        lifecycle_latency_buckets[lifecycle][bucket] += 1
        token_ready_ts = _payload_timestamp_seconds(payload, "token_ready_at")
        orderbook_ready_ts = _payload_timestamp_seconds(payload, "orderbook_ready_at")
        if orderbook_ready_ts is None:
            orderbook_ready_ts = global_ts
        first_candidate_ready_ts = _epoch_stage_timestamp_seconds(
            payload,
            "first_candidate_ready_second",
            "first_tradable_seconds_remaining",
            at_keys=("first_tradable_at",),
        )
        latest_candidate_ready_record = (
            latest_candidate_ready_by_key_run.get((sync_key, run_id))
            or latest_candidate_ready_by_key.get(sync_key)
        )
        latest_candidate_ready_ts = latest_candidate_ready_record.get("timestamp_seconds") if latest_candidate_ready_record else None
        record_delay(first_candidate_ready_delays_ms, first_candidate_ready_ts, decision_created_ts)
        if record_delay(latest_candidate_ready_delays_ms, latest_candidate_ready_ts, decision_created_ts):
            if lifecycle == "ACTIVE_INVENTORY_TRADING":
                active_latest_candidate_ready_delays_ms.append(latest_candidate_ready_delays_ms[-1])
        else:
            latest_candidate_ready_unobservable += 1
        model_check_ts = _payload_timestamp_seconds(payload, "model_activation_checked_at", "model_eligibility_checked_at") or decision_ts
        add_stage_latency("market_snapshot_received_to_token_mapping_ready", global_ts, token_ready_ts)
        add_stage_latency("token_mapping_ready_to_orderbook_fetch_complete", token_ready_ts, orderbook_ready_ts)
        add_stage_latency("orderbook_fetch_complete_to_candidate_ready", orderbook_ready_ts, first_candidate_ready_ts)
        add_stage_latency("candidate_ready_to_decision_event_created", first_candidate_ready_ts, decision_created_ts)
        add_stage_latency("decision_event_created_to_decision_serialized", decision_created_ts, decision_ts)
        add_stage_latency("decision_serialized_to_model_eligibility_check", decision_ts, model_check_ts)
        add_stage_latency("market_snapshot_received_to_decision_serialized", global_ts, decision_ts)
        decay_reason: str | None = None
        if not decision_ready:
            global_ready_before_decision_but_local_incomplete += 1
            decay_reason = local_decay_reason(payload, orderbook_state)
            decay_classification[decay_reason] += 1
            lifecycle_decay_loss[lifecycle] += 1
            if delay_ms is not None and delay_ms > 10000:
                freshness_loss_by_stage["market_snapshot_received_to_decision_serialized"] += 1
            elif first_candidate_ready_ts is not None and decision_created_ts is not None and decision_created_ts >= first_candidate_ready_ts:
                freshness_loss_by_stage["candidate_ready_to_decision_event_created"] += 1
            else:
                freshness_loss_by_stage["unattributed_or_unobservable"] += 1
            if lifecycle == "FINAL_DERISK":
                final_derisk_freshness_loss += 1
        latency_attribution[attribution(payload, delay_ms, decay_reason)] += 1
        if _stage_candidate_ready(payload):
            latest_candidate_ready_by_key[sync_key_for_event] = {
                "timestamp_seconds": event_ts_for_ready,
                "run_id": run_id,
                "producer": producer,
            }
            latest_candidate_ready_by_key_run[(sync_key_for_event, run_id)] = latest_candidate_ready_by_key[sync_key_for_event]

    if decision_ready_count:
        classification = "DECISION_ORDERBOOK_READY_OBSERVED"
    elif global_ready_before_decision_but_local_incomplete:
        classification = "GLOBAL_READY_DECISION_LOCAL_INCOMPLETE"
    elif global_ready_event_count:
        classification = "GLOBAL_READY_DIFFERENT_CONTEXT_OR_NO_DECISION_MATCH"
    else:
        classification = "NO_GLOBAL_OR_DECISION_READY_EVIDENCE"

    delay_range: dict[str, Any] = {}
    if delays_ms:
        delay_range = {
            "min": min(delays_ms),
            "max": max(delays_ms),
            "avg": round(sum(delays_ms) / len(delays_ms), 2),
        }
    active_arrival_status = "NO_ACTIVE_MATCHED_GLOBAL_READY"
    if active_decisions_after_global_ready:
        active_late_share = active_decisions_exceeding_5s / active_decisions_after_global_ready
        active_arrival_status = "ACTIVE_DECISIONS_OFTEN_EXCEED_5S_WINDOW" if active_late_share >= 0.5 else "ACTIVE_DECISIONS_MOSTLY_WITHIN_5S_WINDOW"
    pipeline_stats = stage_stats()
    dominant_stage = "UNKNOWN"
    observable_stages = {
        stage: stats
        for stage, stats in pipeline_stats.items()
        if (
            stage != "market_snapshot_received_to_decision_serialized"
            and stats["median_ms"] is not None
            and stats["sample_count"] >= max(1, int(same_market_global_ready_before_decision * 0.5))
        )
    }
    if not observable_stages:
        observable_stages = {
            stage: stats
            for stage, stats in pipeline_stats.items()
            if stage != "market_snapshot_received_to_decision_serialized" and stats["median_ms"] is not None
        }
    if observable_stages:
        dominant_stage = max(observable_stages, key=lambda stage: observable_stages[stage]["median_ms"] or 0)

    return {
        "scope": "global_non_decision_orderbook_vs_decision_cycle_readiness",
        "global_ready_definition": (
            "non-decision producer reports ready orderbook state or positive YES/NO asks or a positive canonical best ask"
        ),
        "decision_ready_definition": (
            "decision_log candidate event has current-cycle orderbook-ready state plus executable ask evidence in that same event"
        ),
        "producer_state_counts": {
            producer: dict(counts.most_common(5))
            for producer, counts in sorted(producer_state_counts.items())
        },
        "ready_by_producer": dict(ready_by_producer.most_common()),
        "global_ready_event_count": global_ready_event_count,
        "decision_event_count": decision_event_count,
        "decision_ready_event_count": decision_ready_count,
        "same_market_global_ready_before_decision_count": same_market_global_ready_before_decision,
        "fresh_global_ready_before_decision_count": fresh_global_ready_before_decision,
        "global_ready_before_decision_but_local_incomplete_count": global_ready_before_decision_but_local_incomplete,
        "decision_without_prior_global_ready_count": decision_without_prior_global_ready,
        "global_to_decision_delay_ms_range": delay_range,
        "global_to_decision_latency_bucket_counts": dict(latency_buckets.most_common()),
        "median_executable_window_age_ms": _median(delays_ms),
        "executable_liquidity_decay_distribution": {
            "matched_decision_count": same_market_global_ready_before_decision,
            "within_1s_count": latency_buckets.get("<=1s", 0),
            "within_3s_count": latency_buckets.get("<=1s", 0) + latency_buckets.get("<=3s", 0),
            "within_5s_count": (
                latency_buckets.get("<=1s", 0)
                + latency_buckets.get("<=3s", 0)
                + latency_buckets.get("<=5s", 0)
            ),
            "within_10s_count": (
                latency_buckets.get("<=1s", 0)
                + latency_buckets.get("<=3s", 0)
                + latency_buckets.get("<=5s", 0)
                + latency_buckets.get("<=10s", 0)
            ),
            "over_10s_count": latency_buckets.get(">10s", 0),
            "unknown_timestamp_count": latency_buckets.get("unknown_timestamp", 0),
        },
        "local_decay_after_global_ready_counts": dict(decay_classification.most_common()),
        "lifecycle_latency_bucket_counts": {
            phase: dict(counts.most_common())
            for phase, counts in sorted(lifecycle_latency_buckets.items())
        },
        "lifecycle_freshness_loss_counts": dict(lifecycle_decay_loss.most_common()),
        "active_decisions_after_global_ready_count": active_decisions_after_global_ready,
        "active_decisions_exceeding_5s_count": active_decisions_exceeding_5s,
        "active_inventory_trading_arrival_status": active_arrival_status,
        "final_derisk_freshness_loss_count": final_derisk_freshness_loss,
        "executable_books_disappeared_before_decision_count": global_ready_before_decision_but_local_incomplete,
        "latency_pipeline_decomposition": {
            "stage_order": list(pipeline_stages),
            "stage_latency_stats_ms": pipeline_stats,
            "cumulative_observable_latency_ms": pipeline_stats["market_snapshot_received_to_decision_serialized"],
            "dominant_slow_stage": dominant_stage,
            "freshness_loss_by_stage_counts": dict(freshness_loss_by_stage.most_common()),
            "latency_attribution_counts": dict(latency_attribution.most_common()),
            "timestamp_semantics_split": {
                "first_candidate_ready_to_decision_event_created_ms": {
                    "sample_count": len(first_candidate_ready_delays_ms),
                    "median_ms": _median(first_candidate_ready_delays_ms),
                    "p95_ms": _p95(first_candidate_ready_delays_ms),
                    "range_ms": _range(first_candidate_ready_delays_ms),
                },
                "latest_candidate_ready_to_decision_event_created_ms": {
                    "sample_count": len(latest_candidate_ready_delays_ms),
                    "unobservable_count": latest_candidate_ready_unobservable,
                    "median_ms": _median(latest_candidate_ready_delays_ms),
                    "p95_ms": _p95(latest_candidate_ready_delays_ms),
                    "range_ms": _range(latest_candidate_ready_delays_ms),
                },
                "active_latest_candidate_ready_to_decision_event_created_ms": {
                    "sample_count": len(active_latest_candidate_ready_delays_ms),
                    "median_ms": _median(active_latest_candidate_ready_delays_ms),
                    "p95_ms": _p95(active_latest_candidate_ready_delays_ms),
                    "range_ms": _range(active_latest_candidate_ready_delays_ms),
                },
                "last_global_ready_to_decision_event_created_ms": {
                    "sample_count": len(last_global_ready_to_decision_created_ms),
                    "median_ms": _median(last_global_ready_to_decision_created_ms),
                    "p95_ms": _p95(last_global_ready_to_decision_created_ms),
                    "range_ms": _range(last_global_ready_to_decision_created_ms),
                },
                "same_run_last_global_ready_to_decision_event_created_ms": {
                    "sample_count": len(same_run_global_ready_to_decision_ms),
                    "median_ms": _median(same_run_global_ready_to_decision_ms),
                    "p95_ms": _p95(same_run_global_ready_to_decision_ms),
                    "range_ms": _range(same_run_global_ready_to_decision_ms),
                },
                "mixed_run_last_global_ready_to_decision_event_created_ms": {
                    "sample_count": len(mixed_run_global_ready_to_decision_ms),
                    "median_ms": _median(mixed_run_global_ready_to_decision_ms),
                    "p95_ms": _p95(mixed_run_global_ready_to_decision_ms),
                    "range_ms": _range(mixed_run_global_ready_to_decision_ms),
                },
                "active_same_run_last_global_ready_to_decision_event_created_ms": {
                    "sample_count": len(active_same_run_global_ready_to_decision_ms),
                    "median_ms": _median(active_same_run_global_ready_to_decision_ms),
                    "p95_ms": _p95(active_same_run_global_ready_to_decision_ms),
                    "range_ms": _range(active_same_run_global_ready_to_decision_ms),
                },
                "per_run_last_global_ready_to_decision_event_created_ms": {
                    run: {
                        "sample_count": len(values),
                        "median_ms": _median(values),
                        "p95_ms": _p95(values),
                        "range_ms": _range(values),
                    }
                    for run, values in sorted(per_run_global_ready_to_decision_ms.items())
                },
                "sticky_first_ready_warning": (
                    "first_candidate_ready_second is a lifecycle first-seen timestamp and can overstate current decision latency; "
                    "latest_candidate_ready and last_global_ready metrics use prior observed event timestamps when available."
                ),
            },
            "stage_observability_note": (
                "Stage durations use emitted timestamps only. Missing internal timestamps are counted as unobservable, not inferred."
            ),
        },
        "ask_synchronization_counts": dict(ask_sync.most_common()),
        "synchronization_mismatch_classification": classification,
        "interpretation": (
            "Global/dashboard readiness can be true while the decision cycle is not executable; "
            "this report distinguishes producer-level visibility from same-event decision readiness without loosening gates."
        ),
    }


def _age_bucket_ms(value: int | None) -> str:
    if value is None:
        return "unknown"
    if value <= 1000:
        return "<=1s"
    if value <= 3000:
        return "<=3s"
    if value <= 5000:
        return "<=5s"
    if value <= 10000:
        return "<=10s"
    if value <= 30000:
        return "<=30s"
    if value <= 60000:
        return "<=60s"
    return ">60s"


def _cadence_bucket_seconds(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value <= 1:
        return "<=1s"
    if value <= 5:
        return "<=5s"
    if value <= 15:
        return "<=15s"
    if value <= 30:
        return "<=30s"
    if value <= 60:
        return "<=60s"
    return ">60s"


def _orderbook_freshness_reuse_diagnostics(events: list[dict[str, Any]]) -> dict[str, Any]:
    decision_events = 0
    cadence_fields_observed = 0
    reuse_detected = 0
    stale_reuse = 0
    refresh_ages_ms: list[int] = []
    executable_ages_ms: list[int] = []
    cadence_seconds_values: list[int] = []
    cadence_buckets: Counter[str] = Counter()
    refresh_age_buckets: Counter[str] = Counter()
    executable_age_buckets: Counter[str] = Counter()
    refresh_sources: Counter[str] = Counter()
    refresh_triggers: Counter[str] = Counter()
    fetch_status_counts: Counter[str] = Counter()
    stale_reuse_source_counts: Counter[str] = Counter()
    token_pair_lineage_counts: Counter[str] = Counter()
    reuse_by_lifecycle: Counter[str] = Counter()
    drift_counts: Counter[str] = Counter()
    recovery_counts: Counter[str] = Counter()

    for event in events:
        payload = _payload(event)
        if not _decision_funnel_event(event, payload):
            continue
        decision_events += 1
        lifecycle = _lifecycle_context(payload)
        refresh_age = _int_or_none(payload.get("orderbook_snapshot_age_ms_at_decision"))
        executable_age = _int_or_none(payload.get("executable_book_last_seen_age_ms"))
        cadence = _float_or_none(payload.get("decision_cycle_interval_seconds"))
        source = str(payload.get("orderbook_refresh_source") or "unknown")
        trigger = str(payload.get("orderbook_refresh_trigger") or "unknown")
        fetch_status = str(payload.get("orderbook_current_fetch_status") or "unknown")
        reuse_source = str(payload.get("orderbook_stale_reuse_source") or "unknown")
        lineage_raw = payload.get("orderbook_lineage_match")
        if lineage_raw is True:
            lineage = "same_token_pair"
        elif lineage_raw is False:
            lineage = "different_or_unknown_token_pair"
        else:
            lineage = "unknown"
        reuse = _bool_true(payload.get("orderbook_reuse_detected"))

        if any(
            key in payload
            for key in (
                "last_orderbook_refresh_at",
                "orderbook_snapshot_age_ms_at_decision",
                "last_successful_yes_no_book_at",
                "decision_cycle_interval_seconds",
                "executable_book_last_seen_age_ms",
            )
        ):
            cadence_fields_observed += 1
        if cadence is not None:
            cadence_seconds_values.append(int(round(cadence)))
        cadence_buckets[_cadence_bucket_seconds(cadence)] += 1
        refresh_age_buckets[_age_bucket_ms(refresh_age)] += 1
        executable_age_buckets[_age_bucket_ms(executable_age)] += 1
        fetch_status_counts[fetch_status] += 1
        stale_reuse_source_counts[reuse_source] += 1
        token_pair_lineage_counts[lineage] += 1
        if refresh_age is not None:
            refresh_ages_ms.append(refresh_age)
        if executable_age is not None:
            executable_ages_ms.append(executable_age)
        refresh_sources[source] += 1
        refresh_triggers[trigger] += 1
        if reuse:
            reuse_detected += 1
            reuse_by_lifecycle[lifecycle] += 1
            if executable_age is not None and executable_age > 5000:
                stale_reuse += 1
        if refresh_age is not None and refresh_age > 5000:
            drift_counts["refresh_age_exceeds_5s"] += 1
        if executable_age is not None and executable_age > 5000:
            drift_counts["executable_book_age_exceeds_5s"] += 1
        if cadence is not None and refresh_age is not None and refresh_age > max(5000, cadence * 1000 * 2):
            drift_counts["refresh_age_exceeds_2x_decision_interval"] += 1
        if cadence is not None and cadence >= 30:
            drift_counts["decision_interval_ge_30s"] += 1
        if _bool_true(payload.get("empty_book_recovery_attempted")):
            recovery_counts["recovery_attempted"] += 1
        if _bool_true(payload.get("empty_book_recovery_failed")):
            recovery_counts["recovery_failed"] += 1
        if _bool_true(payload.get("empty_book_recovery_success")):
            recovery_counts["recovery_success"] += 1
        reason = str(payload.get("recovery_branch_skipped_reason") or payload.get("recovery_exit_reason") or "").strip()
        if reason:
            recovery_counts[f"recovery_reason:{reason}"] += 1

    median_refresh_age = _median(refresh_ages_ms)
    median_executable_age = _median(executable_ages_ms)
    median_cadence = _median(cadence_seconds_values)
    if decision_events == 0:
        hypothesis = "NO_DECISION_EVENTS"
    elif cadence_fields_observed == 0:
        hypothesis = "CADENCE_FIELDS_NOT_EMITTED"
    elif stale_reuse_source_counts.get("CURRENT_FETCH_FAILED_PRIOR_EXECUTABLE_SAME_TOKEN_PAIR", 0):
        hypothesis = "FRESH_FETCH_FAILED_AFTER_PRIOR_READY_SAME_TOKEN_PAIR"
    elif stale_reuse_source_counts.get("CURRENT_FETCH_NON_EXECUTABLE_PRIOR_EXECUTABLE_SAME_TOKEN_PAIR", 0):
        hypothesis = "FRESH_FETCH_NON_EXECUTABLE_AFTER_PRIOR_READY_SAME_TOKEN_PAIR"
    elif any(
        stale_reuse_source_counts.get(key, 0)
        for key in (
            "CURRENT_FETCH_FAILED_PRIOR_EXECUTABLE_DIFFERENT_OR_UNKNOWN_PAIR",
            "CURRENT_FETCH_NON_EXECUTABLE_PRIOR_EXECUTABLE_DIFFERENT_OR_UNKNOWN_PAIR",
            "NO_CURRENT_FETCH_PRIOR_EXECUTABLE_DIFFERENT_OR_UNKNOWN_PAIR",
        )
    ):
        hypothesis = "CACHE_KEY_OR_TOKEN_PAIR_LINEAGE_MISMATCH"
    elif median_cadence is not None and median_cadence >= 30:
        hypothesis = "STRUCTURALLY_POLLING_TOO_SLOW"
    elif stale_reuse:
        hypothesis = "OVER_REUSING_STALE_EXECUTABLE_BOOK_STATE"
    elif median_executable_age is not None and median_executable_age > 10000:
        hypothesis = "MISSING_EXECUTABLE_BOOKS_DUE_TO_CADENCE_DRIFT"
    elif recovery_counts.get("recovery_failed", 0) and not recovery_counts.get("recovery_success", 0):
        hypothesis = "EMPTY_BOOK_RECOVERY_NOT_RESTORING_EXECUTABLE_BOOK"
    else:
        hypothesis = "NO_STALE_REUSE_PROOF"

    return {
        "scope": "decision_cycle_orderbook_refresh_cadence_observability",
        "decision_event_count": decision_events,
        "cadence_fields_observed_count": cadence_fields_observed,
        "orderbook_reuse_detected_count": reuse_detected,
        "stale_orderbook_reuse_count": stale_reuse,
        "refresh_cadence_distribution": dict(cadence_buckets.most_common()),
        "orderbook_snapshot_age_at_decision_distribution": dict(refresh_age_buckets.most_common()),
        "executable_book_age_at_decision_distribution": dict(executable_age_buckets.most_common()),
        "refresh_source_counts": dict(refresh_sources.most_common()),
        "refresh_trigger_counts": dict(refresh_triggers.most_common()),
        "fresh_fetch_vs_cache_source_counts": dict(fetch_status_counts.most_common()),
        "stale_reuse_source_classification_counts": dict(stale_reuse_source_counts.most_common()),
        "token_pair_lineage_counts": dict(token_pair_lineage_counts.most_common()),
        "reuse_by_lifecycle_phase": dict(reuse_by_lifecycle.most_common()),
        "refresh_age_ms_stats": {
            "sample_count": len(refresh_ages_ms),
            "median_ms": median_refresh_age,
            "p95_ms": _p95(refresh_ages_ms),
            "range_ms": _range(refresh_ages_ms),
        },
        "executable_book_last_seen_age_ms_stats": {
            "sample_count": len(executable_ages_ms),
            "median_ms": median_executable_age,
            "p95_ms": _p95(executable_ages_ms),
            "range_ms": _range(executable_ages_ms),
        },
        "decision_cycle_interval_seconds_stats": {
            "sample_count": len(cadence_seconds_values),
            "median_seconds": median_cadence,
            "p95_seconds": _p95(cadence_seconds_values),
            "range_seconds": _range(cadence_seconds_values),
        },
        "polling_cycle_drift_diagnostics": dict(drift_counts.most_common()),
        "empty_book_recovery_delay_diagnostics": dict(recovery_counts.most_common()),
        "runtime_cadence_hypothesis": hypothesis,
        "interpretation": (
            "Offline observability only. These diagnostics compare emitted decision-cycle timing fields; "
            "they do not widen orderbook freshness, retry cadence, or model eligibility gates."
        ),
    }


def _scheduler_cadence_diagnostics(events: list[dict[str, Any]]) -> dict[str, Any]:
    decision_events = 0
    timing_fields_observed = 0
    evaluation_durations_ms: list[int] = []
    evaluation_offsets_ms: list[int] = []
    candidate_queue_ages_ms: list[int] = []
    recovery_durations_ms: list[int] = []
    decision_intervals_seconds: list[int] = []
    configured_intervals_seconds: list[int] = []
    effective_outer_intervals_seconds: list[int] = []
    intended_targets_seconds: list[int] = []
    snapshot_intervals_seconds: list[int] = []
    market_discovery_intervals_seconds: list[int] = []
    actual_market_revisit_seconds: list[int] = []
    sequence_index_counts: Counter[str] = Counter()
    sequence_count_distribution: Counter[str] = Counter()
    hot_path_sources: Counter[str] = Counter()
    cadence_sources: Counter[str] = Counter()
    asset_counts: Counter[str] = Counter()
    queue_ownership_counts: Counter[str] = Counter()
    revisit_source_counts: Counter[str] = Counter()
    hot_path_trigger_counts: Counter[str] = Counter()
    event_vs_polling_counts: Counter[str] = Counter()
    liquidity_event_role_counts: Counter[str] = Counter()
    pipeline_linkage_counts: Counter[str] = Counter()
    handoff_boundary_counts: Counter[str] = Counter()
    hot_path_wait_ms: list[int] = []
    cycle_markets: dict[str, list[tuple[int, int, int]]] = defaultdict(list)

    for event in events:
        payload = _payload(event)
        if not _decision_funnel_event(event, payload):
            continue
        decision_events += 1
        duration = _int_or_none(payload.get("market_evaluation_duration_ms"))
        offset = _int_or_none(payload.get("market_evaluation_started_ms_since_cycle"))
        queue_age = _int_or_none(payload.get("candidate_queue_age_ms"))
        recovery_duration = _int_or_none(payload.get("empty_book_recovery_duration_ms"))
        interval = _float_or_none(payload.get("decision_cycle_interval_seconds"))
        configured_interval = _float_or_none(payload.get("configured_decision_loop_interval_seconds"))
        effective_outer_interval = _float_or_none(payload.get("effective_outer_loop_interval_seconds"))
        intended_target = _float_or_none(payload.get("intended_decision_loop_target_seconds"))
        snapshot_interval = _float_or_none(payload.get("snapshot_sampling_interval_seconds"))
        discovery_interval = _float_or_none(payload.get("market_discovery_interval_seconds"))
        revisit_interval = _float_or_none(payload.get("actual_market_revisit_frequency_seconds"))
        sequence_index = _int_or_none(payload.get("market_sequence_index"))
        sequence_count = _int_or_none(payload.get("market_sequence_count"))
        admission_wait = _int_or_none(payload.get("hot_path_admission_wait_ms"))
        cycle_started = str(payload.get("decision_cycle_started_at") or "").strip()

        if any(
            value is not None
            for value in (duration, offset, queue_age, recovery_duration, sequence_index, sequence_count)
        ):
            timing_fields_observed += 1
        if duration is not None:
            evaluation_durations_ms.append(duration)
        if offset is not None:
            evaluation_offsets_ms.append(offset)
        if queue_age is not None:
            candidate_queue_ages_ms.append(queue_age)
        if recovery_duration is not None:
            recovery_durations_ms.append(recovery_duration)
        if interval is not None:
            decision_intervals_seconds.append(int(round(interval)))
        if configured_interval is not None:
            configured_intervals_seconds.append(int(round(configured_interval)))
        if effective_outer_interval is not None:
            effective_outer_intervals_seconds.append(int(round(effective_outer_interval)))
        if intended_target is not None:
            intended_targets_seconds.append(int(round(intended_target)))
        if snapshot_interval is not None:
            snapshot_intervals_seconds.append(int(round(snapshot_interval)))
        if discovery_interval is not None:
            market_discovery_intervals_seconds.append(int(round(discovery_interval)))
        if revisit_interval is not None:
            actual_market_revisit_seconds.append(int(round(revisit_interval)))
        if admission_wait is not None:
            hot_path_wait_ms.append(admission_wait)
        if sequence_index is not None:
            sequence_index_counts[str(sequence_index)] += 1
        if sequence_count is not None:
            sequence_count_distribution[str(sequence_count)] += 1
        source = str(payload.get("hot_path_timing_source") or "unknown")
        cadence_source = str(payload.get("scheduler_cadence_source") or "unknown")
        hot_path_sources[source] += 1
        cadence_sources[cadence_source] += 1
        queue_ownership_counts[str(payload.get("candidate_queue_ownership") or "unknown")] += 1
        revisit_source_counts[str(payload.get("candidate_revisit_scheduling_source") or "unknown")] += 1
        hot_path_trigger_counts[str(payload.get("hot_path_admission_trigger") or "unknown")] += 1
        event_vs_polling_counts[str(payload.get("event_vs_polling_classification") or "unknown")] += 1
        liquidity_event_role_counts[str(payload.get("executable_liquidity_event_role") or "unknown")] += 1
        pipeline_linkage_counts[str(payload.get("market_snapshot_decision_pipeline_linkage") or "unknown")] += 1
        handoff_boundary_counts[str(payload.get("candidate_handoff_boundary") or "unknown")] += 1
        asset = str(payload.get("market_evaluation_asset") or payload.get("asset") or payload.get("ticker") or "unknown")
        asset_counts[asset] += 1
        if cycle_started and offset is not None:
            cycle_markets[cycle_started].append(
                (
                    offset,
                    duration or 0,
                    sequence_index or 0,
                )
            )

    cycle_spans_ms: list[int] = []
    sequential_cycle_counts = 0
    for rows in cycle_markets.values():
        if len(rows) < 2:
            continue
        sequential_cycle_counts += 1
        starts = [row[0] for row in rows]
        ends = [row[0] + row[1] for row in rows]
        cycle_spans_ms.append(max(ends) - min(starts))

    median_interval = _median(decision_intervals_seconds)
    median_configured_interval = _median(configured_intervals_seconds)
    median_effective_outer_interval = _median(effective_outer_intervals_seconds)
    median_target = _median(intended_targets_seconds) or 1
    median_revisit = _median(actual_market_revisit_seconds)
    median_queue_age = _median(candidate_queue_ages_ms)
    median_hot_path_wait = _median(hot_path_wait_ms)
    median_recovery_duration = _median(recovery_durations_ms)
    median_eval_duration = _median(evaluation_durations_ms)
    p95_sequence_span = _p95(cycle_spans_ms)

    if decision_events == 0:
        dominant_bottleneck = "NO_DECISION_EVENTS"
    elif timing_fields_observed == 0:
        dominant_bottleneck = "SCHEDULER_TIMING_FIELDS_NOT_EMITTED"
    elif median_configured_interval is not None and median_configured_interval > median_target:
        dominant_bottleneck = "CONFIGURED_DECISION_INTERVAL_EXCEEDS_TARGET"
    elif median_effective_outer_interval is not None and median_effective_outer_interval > median_target:
        dominant_bottleneck = "EFFECTIVE_OUTER_LOOP_INTERVAL_EXCEEDS_TARGET"
    elif median_revisit is not None and median_revisit > median_target:
        dominant_bottleneck = "PER_MARKET_REVISIT_FREQUENCY_EXCEEDS_TARGET"
    elif median_interval is not None and median_interval >= 30 and median_queue_age is not None and median_queue_age > 5000:
        dominant_bottleneck = "EXTERNAL_INTERVAL_CADENCE_WAIT"
    elif median_recovery_duration is not None and median_recovery_duration > 5000:
        dominant_bottleneck = "EMPTY_BOOK_RECOVERY_CONSUMES_USABLE_WINDOW"
    elif p95_sequence_span is not None and p95_sequence_span > 5000:
        dominant_bottleneck = "SEQUENTIAL_MARKET_EVALUATION_CONSUMES_USABLE_WINDOW"
    elif median_eval_duration is not None and median_eval_duration > 5000:
        dominant_bottleneck = "PER_MARKET_EVALUATION_SLOW"
    elif (
        event_vs_polling_counts.get("polling_revisit_driven", 0)
        and liquidity_event_role_counts.get("passive_telemetry_only", 0)
        and (median_hot_path_wait or median_queue_age or 0) > 5000
    ):
        dominant_bottleneck = "PASSIVE_EXECUTABLE_BOOK_WAITING_FOR_POLLING_HOT_PATH"
    elif median_queue_age is not None and median_queue_age > 5000:
        dominant_bottleneck = "PRIOR_EXECUTABLE_BOOK_EXPIRED_BEFORE_FAST_DECISION_PATH"
    else:
        dominant_bottleneck = "NO_RUNTIME_CADENCE_BOTTLENECK_PROVEN"

    return {
        "scope": "decision_scheduler_hot_path_observability",
        "decision_event_count": decision_events,
        "scheduler_timing_fields_observed_count": timing_fields_observed,
        "dominant_scheduler_bottleneck": dominant_bottleneck,
        "market_evaluation_duration_ms_stats": {
            "sample_count": len(evaluation_durations_ms),
            "median_ms": median_eval_duration,
            "p95_ms": _p95(evaluation_durations_ms),
            "range_ms": _range(evaluation_durations_ms),
        },
        "market_evaluation_start_offset_ms_stats": {
            "sample_count": len(evaluation_offsets_ms),
            "median_ms": _median(evaluation_offsets_ms),
            "p95_ms": _p95(evaluation_offsets_ms),
            "range_ms": _range(evaluation_offsets_ms),
        },
        "candidate_queue_age_ms_stats": {
            "sample_count": len(candidate_queue_ages_ms),
            "median_ms": median_queue_age,
            "p95_ms": _p95(candidate_queue_ages_ms),
            "range_ms": _range(candidate_queue_ages_ms),
        },
        "hot_path_admission_wait_ms_stats": {
            "sample_count": len(hot_path_wait_ms),
            "median_ms": median_hot_path_wait,
            "p95_ms": _p95(hot_path_wait_ms),
            "range_ms": _range(hot_path_wait_ms),
        },
        "empty_book_recovery_duration_ms_stats": {
            "sample_count": len(recovery_durations_ms),
            "median_ms": median_recovery_duration,
            "p95_ms": _p95(recovery_durations_ms),
            "range_ms": _range(recovery_durations_ms),
        },
        "decision_cycle_interval_seconds_stats": {
            "sample_count": len(decision_intervals_seconds),
            "median_seconds": median_interval,
            "p95_seconds": _p95(decision_intervals_seconds),
            "range_seconds": _range(decision_intervals_seconds),
        },
        "configured_decision_loop_interval_seconds_stats": {
            "sample_count": len(configured_intervals_seconds),
            "median_seconds": median_configured_interval,
            "p95_seconds": _p95(configured_intervals_seconds),
            "range_seconds": _range(configured_intervals_seconds),
        },
        "effective_outer_loop_interval_seconds_stats": {
            "sample_count": len(effective_outer_intervals_seconds),
            "median_seconds": median_effective_outer_interval,
            "p95_seconds": _p95(effective_outer_intervals_seconds),
            "range_seconds": _range(effective_outer_intervals_seconds),
        },
        "actual_market_revisit_frequency_seconds_stats": {
            "sample_count": len(actual_market_revisit_seconds),
            "median_seconds": median_revisit,
            "p95_seconds": _p95(actual_market_revisit_seconds),
            "range_seconds": _range(actual_market_revisit_seconds),
        },
        "intended_architecture_cadence_seconds": {
            "decision_loop_target": median_target,
            "snapshot_sampling_median": _median(snapshot_intervals_seconds),
            "market_discovery_median": _median(market_discovery_intervals_seconds),
        },
        "btc_eth_sequencing_duration_ms_stats": {
            "sample_count": len(cycle_spans_ms),
            "median_ms": _median(cycle_spans_ms),
            "p95_ms": p95_sequence_span,
            "range_ms": _range(cycle_spans_ms),
            "sequential_cycle_count": sequential_cycle_counts,
        },
        "market_sequence_index_counts": dict(sequence_index_counts.most_common()),
        "market_sequence_count_distribution": dict(sequence_count_distribution.most_common()),
        "market_evaluation_asset_counts": dict(asset_counts.most_common()),
        "hot_path_timing_source_counts": dict(hot_path_sources.most_common()),
        "scheduler_cadence_source_counts": dict(cadence_sources.most_common()),
        "candidate_handoff_diagnostics": {
            "candidate_queue_ownership_counts": dict(queue_ownership_counts.most_common()),
            "candidate_revisit_scheduling_source_counts": dict(revisit_source_counts.most_common()),
            "hot_path_admission_trigger_counts": dict(hot_path_trigger_counts.most_common()),
            "event_vs_polling_classification_counts": dict(event_vs_polling_counts.most_common()),
            "executable_liquidity_event_role_counts": dict(liquidity_event_role_counts.most_common()),
            "market_snapshot_decision_pipeline_linkage_counts": dict(pipeline_linkage_counts.most_common()),
            "candidate_handoff_boundary_counts": dict(handoff_boundary_counts.most_common()),
            "dominant_candidate_aging_source": (
                "PASSIVE_EXECUTABLE_LIQUIDITY_WAITING_FOR_SCHEDULED_DECISION_REVISIT"
                if (
                    event_vs_polling_counts.get("polling_revisit_driven", 0)
                    and liquidity_event_role_counts.get("passive_telemetry_only", 0)
                    and (median_hot_path_wait or median_queue_age or 0) > 5000
                )
                else "INSUFFICIENT_HANDOFF_AGING_EVIDENCE"
            ),
            "minimal_future_architecture_direction": (
                "event_driven_executable_liquidity_hot_path_admission"
                if (
                    event_vs_polling_counts.get("polling_revisit_driven", 0)
                    and liquidity_event_role_counts.get("passive_telemetry_only", 0)
                )
                else "preserve_current_polling_until_more_evidence"
            ),
        },
        "root_candidate_flags": {
            "interval_is_root_candidate": bool(
                (
                    median_configured_interval is not None
                    and median_configured_interval > median_target
                )
                or (
                    median_effective_outer_interval is not None
                    and median_effective_outer_interval > median_target
                )
                or (
                    median_interval is not None and median_interval >= 30 and median_queue_age is not None and median_queue_age > 5000
                )
            ),
            "configured_interval_violates_decision_target": bool(
                median_configured_interval is not None and median_configured_interval > median_target
            ),
            "effective_outer_loop_violates_decision_target": bool(
                median_effective_outer_interval is not None and median_effective_outer_interval > median_target
            ),
            "market_revisit_frequency_violates_decision_target": bool(
                median_revisit is not None and median_revisit > median_target
            ),
            "recovery_retry_timing_is_root_candidate": bool(
                median_recovery_duration is not None and median_recovery_duration > 5000
            ),
            "sequential_btc_eth_evaluation_contributes": bool(
                p95_sequence_span is not None and p95_sequence_span > 5000
            ),
            "fast_decision_path_after_stale_prior_book": bool(
                median_queue_age is not None
                and median_queue_age > 5000
                and (median_eval_duration is None or median_eval_duration <= 5000)
            ),
            "polling_centric_candidate_handoff": bool(
                event_vs_polling_counts.get("polling_revisit_driven", 0)
            ),
            "executable_liquidity_is_passive_telemetry": bool(
                liquidity_event_role_counts.get("passive_telemetry_only", 0)
            ),
        },
        "interpretation": (
            "Offline observability only. Scheduler diagnostics split external interval cadence, "
            "per-market evaluation duration, sequential BTC/ETH evaluation, recovery waits, and prior executable-book age."
        ),
    }


def _candidate_timing_diagnostics(events: list[dict[str, Any]], ev_report: dict[str, Any]) -> dict[str, Any]:
    first_seen_seconds: list[int] = []
    first_orderbook_seconds: list[int] = []
    first_candidate_seconds: list[int] = []
    first_model_eligible_seconds: list[int] = []
    first_probability_output_seconds: list[int] = []
    lifecycle_durations: list[int] = []
    seconds_remaining_when_eligible: list[int] = []
    seconds_remaining_when_output: list[int] = []
    timing_bottlenecks: Counter[str] = Counter()
    lifecycle_counts: Counter[str] = Counter()
    all_event_lifecycle_counts: Counter[str] = Counter()
    lifecycle_unknown_reasons: Counter[str] = Counter()
    candidate_ready_phase_counts: Counter[str] = Counter()
    model_eligible_phase_counts: Counter[str] = Counter()
    model_output_phase_counts: Counter[str] = Counter()
    readiness_delay_seconds: list[int] = []
    orderbook_to_candidate_delay_seconds: list[int] = []
    candidate_ready_to_profit_management_seconds: list[int] = []
    candidate_ready_to_final_derisk_seconds: list[int] = []
    model_eligible_to_final_derisk_seconds: list[int] = []
    events_with_timing = 0
    candidate_relevant_events = 0
    active_events = 0
    final_derisk_events = 0
    candidate_ready_during_active_count = 0
    candidate_ready_before_final_derisk_count = 0
    candidate_ready_at_or_after_final_derisk_count = 0
    active_events_without_model_eligibility_count = 0
    active_candidate_ready_without_model_eligibility_count = 0
    model_eligible_during_active_count = 0
    model_output_during_active_count = 0
    final_derisk_before_orderbook_ready_count = 0
    final_derisk_before_candidate_ready_count = 0
    final_derisk_before_model_eligible_count = 0
    final_derisk_before_model_output_count = 0

    for event in events:
        payload = _payload(event)
        timing_seen = False
        lifecycle = str(payload.get("lifecycle_phase") or payload.get("model_activation_lifecycle_phase") or "UNKNOWN")
        lifecycle_upper = lifecycle.upper()
        all_event_lifecycle_counts[lifecycle] += 1
        relevant = _candidate_timing_relevant(event, payload)
        if not relevant:
            if lifecycle == "UNKNOWN":
                lifecycle_unknown_reasons[_lifecycle_unknown_reason(event, payload)] += 1
            continue
        candidate_relevant_events += 1
        lifecycle_counts[lifecycle] += 1
        if lifecycle == "UNKNOWN":
            lifecycle_unknown_reasons[_lifecycle_unknown_reason(event, payload)] += 1
        if lifecycle_upper == "ACTIVE_INVENTORY_TRADING":
            active_events += 1
        if lifecycle_upper == "FINAL_DERISK":
            final_derisk_events += 1

        first_seen = _int_or_none(payload.get("first_seen_second"))
        if first_seen is None:
            first_seen = _second_from_remaining(payload.get("first_seen_seconds_remaining"))
        if first_seen is not None:
            first_seen_seconds.append(first_seen)
            timing_seen = True

        orderbook_second = _int_or_none(payload.get("first_orderbook_ready_second"))
        if orderbook_second is None:
            orderbook_remaining = _int_or_none(payload.get("orderbook_ready_seconds_remaining"))
            orderbook_second = _second_from_remaining(orderbook_remaining) if orderbook_remaining else None
        if orderbook_second is not None:
            first_orderbook_seconds.append(orderbook_second)
            timing_seen = True

        candidate_second = _int_or_none(payload.get("first_candidate_ready_second"))
        if candidate_second is None:
            candidate_remaining = _int_or_none(payload.get("first_tradable_seconds_remaining"))
            candidate_second = _second_from_remaining(candidate_remaining) if candidate_remaining else None
        if candidate_second is not None:
            first_candidate_seconds.append(candidate_second)
            candidate_ready_phase_counts[_lifecycle_phase_from_second(candidate_second)] += 1
            candidate_ready_to_profit_management_seconds.append(
                LIFECYCLE_SECOND_BOUNDARIES["PROFIT_MANAGEMENT"] - candidate_second
            )
            candidate_ready_to_final_derisk_seconds.append(
                LIFECYCLE_SECOND_BOUNDARIES["FINAL_DERISK"] - candidate_second
            )
            if LIFECYCLE_SECOND_BOUNDARIES["ACTIVE_INVENTORY_TRADING"] <= candidate_second < LIFECYCLE_SECOND_BOUNDARIES["PROFIT_MANAGEMENT"]:
                candidate_ready_during_active_count += 1
            if candidate_second < LIFECYCLE_SECOND_BOUNDARIES["FINAL_DERISK"]:
                candidate_ready_before_final_derisk_count += 1
            else:
                candidate_ready_at_or_after_final_derisk_count += 1
            timing_seen = True
        if first_seen is not None and candidate_second is not None:
            readiness_delay_seconds.append(max(0, candidate_second - first_seen))
        if orderbook_second is not None and candidate_second is not None:
            orderbook_to_candidate_delay_seconds.append(max(0, candidate_second - orderbook_second))

        eligible_second = _int_or_none(payload.get("first_model_eligible_second"))
        if eligible_second is not None:
            first_model_eligible_seconds.append(eligible_second)
            model_eligible_phase_counts[_lifecycle_phase_from_second(eligible_second)] += 1
            model_eligible_to_final_derisk_seconds.append(
                LIFECYCLE_SECOND_BOUNDARIES["FINAL_DERISK"] - eligible_second
            )
            if LIFECYCLE_SECOND_BOUNDARIES["ACTIVE_INVENTORY_TRADING"] <= eligible_second < LIFECYCLE_SECOND_BOUNDARIES["PROFIT_MANAGEMENT"]:
                model_eligible_during_active_count += 1
            timing_seen = True

        output_second = _int_or_none(payload.get("first_probability_output_second"))
        if output_second is not None:
            first_probability_output_seconds.append(output_second)
            model_output_phase_counts[_lifecycle_phase_from_second(output_second)] += 1
            if LIFECYCLE_SECOND_BOUNDARIES["ACTIVE_INVENTORY_TRADING"] <= output_second < LIFECYCLE_SECOND_BOUNDARIES["PROFIT_MANAGEMENT"]:
                model_output_during_active_count += 1
            timing_seen = True

        duration = _int_or_none(payload.get("candidate_lifecycle_duration_seconds") or payload.get("candidate_lifecycle_duration"))
        if duration is not None:
            lifecycle_durations.append(duration)
            timing_seen = True

        eligible_remaining = _int_or_none(payload.get("seconds_remaining_when_eligible"))
        if eligible_remaining is not None:
            seconds_remaining_when_eligible.append(eligible_remaining)
        output_remaining = _int_or_none(payload.get("seconds_remaining_when_model_output_visible"))
        if output_remaining is not None:
            seconds_remaining_when_output.append(output_remaining)

        if lifecycle_upper == "ACTIVE_INVENTORY_TRADING":
            if eligible_second is None:
                active_events_without_model_eligibility_count += 1
            if candidate_second is not None and candidate_second < LIFECYCLE_SECOND_BOUNDARIES["PROFIT_MANAGEMENT"] and eligible_second is None:
                active_candidate_ready_without_model_eligibility_count += 1
        if lifecycle_upper == "FINAL_DERISK":
            if orderbook_second is None or orderbook_second >= LIFECYCLE_SECOND_BOUNDARIES["FINAL_DERISK"]:
                final_derisk_before_orderbook_ready_count += 1
            if candidate_second is None or candidate_second >= LIFECYCLE_SECOND_BOUNDARIES["FINAL_DERISK"]:
                final_derisk_before_candidate_ready_count += 1
            if eligible_second is None or eligible_second >= LIFECYCLE_SECOND_BOUNDARIES["FINAL_DERISK"]:
                final_derisk_before_model_eligible_count += 1
            if output_second is None or output_second >= LIFECYCLE_SECOND_BOUNDARIES["FINAL_DERISK"]:
                final_derisk_before_model_output_count += 1

        group = str(payload.get("model_activation_block_group") or "").upper()
        reason = str(payload.get("model_activation_block_reason") or payload.get("active_window_alignment_reason") or "").lower()
        if group in {"TIME_CUTOFF_GATE", "LIFECYCLE_PHASE_GATE"} or "hard_close" in reason or "cutoff" in reason:
            timing_bottlenecks["CUTOFF_OR_LIFECYCLE_BEFORE_MODEL"] += 1
        elif group == "ORDERBOOK_GATE":
            timing_bottlenecks["ORDERBOOK_READINESS_BEFORE_MODEL"] += 1
        elif group in {"LIQUIDITY_GATE", "SPREAD_GATE"}:
            timing_bottlenecks["MICROSTRUCTURE_READINESS_BEFORE_MODEL"] += 1
        elif eligible_second is not None and eligible_second >= 240:
            timing_bottlenecks["MODEL_ELIGIBLE_NEAR_FINAL_DERISK"] += 1
        elif output_second is not None and output_second >= 240:
            timing_bottlenecks["MODEL_OUTPUT_NEAR_FINAL_DERISK"] += 1

        if timing_seen:
            events_with_timing += 1

    fallback_gates = Counter({
        str(key): int(value)
        for key, value in dict(ev_report.get("model_attempt_gate_counts") or {}).items()
        if isinstance(value, (int, float)) and int(value)
    })
    if not timing_bottlenecks:
        if fallback_gates.get("TIME_CUTOFF_GATE") or fallback_gates.get("LIFECYCLE_PHASE_GATE"):
            timing_bottlenecks["CUTOFF_OR_LIFECYCLE_BEFORE_MODEL"] += fallback_gates.get("TIME_CUTOFF_GATE", 0) + fallback_gates.get("LIFECYCLE_PHASE_GATE", 0)
        if fallback_gates.get("ORDERBOOK_GATE"):
            timing_bottlenecks["ORDERBOOK_READINESS_BEFORE_MODEL"] += fallback_gates["ORDERBOOK_GATE"]

    dominant = timing_bottlenecks.most_common(1)[0][0] if timing_bottlenecks else "INSUFFICIENT_TIMING_EVIDENCE"
    eligible_late = sum(1 for value in seconds_remaining_when_eligible if value <= 60)
    output_late = sum(1 for value in seconds_remaining_when_output if value <= 60)
    if first_model_eligible_seconds:
        first_eligible = min(first_model_eligible_seconds)
        if model_eligible_during_active_count:
            eligibility_window_status = "MODEL_ELIGIBLE_DURING_ACTIVE"
        elif first_eligible >= LIFECYCLE_SECOND_BOUNDARIES["FINAL_DERISK"]:
            eligibility_window_status = "MODEL_ELIGIBLE_ONLY_IN_FINAL_DERISK_OR_LATER"
        elif first_eligible >= LIFECYCLE_SECOND_BOUNDARIES["PROFIT_MANAGEMENT"]:
            eligibility_window_status = "MODEL_ELIGIBLE_ONLY_AFTER_ACTIVE_PHASE"
        else:
            eligibility_window_status = "MODEL_ELIGIBILITY_VISIBLE_OUTSIDE_ACTIVE"
    elif candidate_ready_before_final_derisk_count:
        eligibility_window_status = "CANDIDATE_READY_BUT_MODEL_NEVER_ELIGIBLE"
    else:
        eligibility_window_status = "NO_MODEL_ELIGIBILITY_EVIDENCE"
    return {
        "events_with_timing_fields": events_with_timing,
        "candidate_relevant_events": candidate_relevant_events,
        "lifecycle_transition_timing": {
            "opening_scan_start_second": LIFECYCLE_SECOND_BOUNDARIES["OPENING_SCAN"],
            "active_inventory_trading_start_second": LIFECYCLE_SECOND_BOUNDARIES["ACTIVE_INVENTORY_TRADING"],
            "profit_management_start_second": LIFECYCLE_SECOND_BOUNDARIES["PROFIT_MANAGEMENT"],
            "final_derisk_start_second": LIFECYCLE_SECOND_BOUNDARIES["FINAL_DERISK"],
            "closed_or_unsafe_start_second": LIFECYCLE_SECOND_BOUNDARIES["CLOSED_OR_UNSAFE"],
            "active_phase_duration_seconds": LIFECYCLE_SECOND_BOUNDARIES["PROFIT_MANAGEMENT"] - LIFECYCLE_SECOND_BOUNDARIES["ACTIVE_INVENTORY_TRADING"],
            "active_to_final_derisk_elapsed_seconds": LIFECYCLE_SECOND_BOUNDARIES["FINAL_DERISK"] - LIFECYCLE_SECOND_BOUNDARIES["ACTIVE_INVENTORY_TRADING"],
            "profit_management_buffer_seconds": LIFECYCLE_SECOND_BOUNDARIES["FINAL_DERISK"] - LIFECYCLE_SECOND_BOUNDARIES["PROFIT_MANAGEMENT"],
            "final_derisk_window_seconds": LIFECYCLE_SECOND_BOUNDARIES["CLOSED_OR_UNSAFE"] - LIFECYCLE_SECOND_BOUNDARIES["FINAL_DERISK"],
        },
        "lifecycle_transition_summary": {
            "active_inventory_trading_event_count": active_events,
            "final_derisk_event_count": final_derisk_events,
            "candidate_ready_during_active_count": candidate_ready_during_active_count,
            "candidate_ready_before_final_derisk_count": candidate_ready_before_final_derisk_count,
            "candidate_ready_at_or_after_final_derisk_count": candidate_ready_at_or_after_final_derisk_count,
            "active_events_without_model_eligibility_count": active_events_without_model_eligibility_count,
            "active_candidate_ready_without_model_eligibility_count": active_candidate_ready_without_model_eligibility_count,
            "model_eligible_during_active_count": model_eligible_during_active_count,
            "model_output_during_active_count": model_output_during_active_count,
            "final_derisk_before_orderbook_ready_count": final_derisk_before_orderbook_ready_count,
            "final_derisk_before_candidate_ready_count": final_derisk_before_candidate_ready_count,
            "final_derisk_before_model_eligible_count": final_derisk_before_model_eligible_count,
            "final_derisk_before_model_output_count": final_derisk_before_model_output_count,
            "model_eligibility_window_status": eligibility_window_status,
        },
        "first_seen_second_range": _range(first_seen_seconds),
        "first_orderbook_ready_second_range": _range(first_orderbook_seconds),
        "first_candidate_ready_second_range": _range(first_candidate_seconds),
        "first_seen_to_candidate_ready_delay_seconds_range": _range(readiness_delay_seconds),
        "orderbook_to_candidate_ready_delay_seconds_range": _range(orderbook_to_candidate_delay_seconds),
        "candidate_ready_phase_counts": dict(candidate_ready_phase_counts.most_common()),
        "model_eligible_phase_counts": dict(model_eligible_phase_counts.most_common()),
        "model_output_phase_counts": dict(model_output_phase_counts.most_common()),
        "candidate_ready_to_profit_management_seconds_range": _range(candidate_ready_to_profit_management_seconds),
        "candidate_ready_to_final_derisk_seconds_range": _range(candidate_ready_to_final_derisk_seconds),
        "model_eligible_to_final_derisk_seconds_range": _range(model_eligible_to_final_derisk_seconds),
        "first_model_eligible_second_range": _range(first_model_eligible_seconds),
        "first_probability_output_second_range": _range(first_probability_output_seconds),
        "seconds_remaining_when_eligible_range": _range(seconds_remaining_when_eligible),
        "seconds_remaining_when_model_output_visible_range": _range(seconds_remaining_when_output),
        "candidate_lifecycle_duration_seconds_range": _range(lifecycle_durations),
        "eligible_inside_last_60s_count": eligible_late,
        "probability_output_inside_last_60s_count": output_late,
        "timing_bottleneck_counts": dict(timing_bottlenecks.most_common()),
        "dominant_timing_bottleneck": dominant,
        "lifecycle_phase_counts": dict(lifecycle_counts.most_common()),
        "all_event_lifecycle_phase_counts": dict(all_event_lifecycle_counts.most_common()),
        "lifecycle_unknown_reason_counts": dict(lifecycle_unknown_reasons.most_common()),
        "interpretation": "Timing diagnostics are observational only; they identify when candidates became visible, ready, eligible, or model-visible without changing gates.",
    }


def _root_cause_candidate(ev_status: dict[str, Any], ev_report: dict[str, Any], orderbook_health: dict[str, Any]) -> str:
    diagnostic_class = str(ev_report.get("ev_risk_chain_gap_diagnostics", {}).get("classification") or "")
    if diagnostic_class:
        return diagnostic_class
    if ev_status["EV_NEVER_VISIBLE"] and float(ev_status["risk_layer_trace_readiness"]) == 0.0:
        return "EV_AND_RISK_CHAIN_NOT_VISIBLE"
    if ev_status["EV_NEVER_VISIBLE"]:
        return "EV_NEVER_VISIBLE"
    if ev_report.get("dominant_model_attempt_gate"):
        return f"MODEL_GATE:{ev_report['dominant_model_attempt_gate']}"
    if orderbook_health.get("dominant_blocker") not in {"", "UNKNOWN"}:
        return f"ORDERBOOK:{orderbook_health['dominant_blocker']}"
    return "INSUFFICIENT_EVIDENCE"


def _recommended_patch(root_cause: str, ev_report: dict[str, Any]) -> str:
    if root_cause == "EV_AND_RISK_CHAIN_NOT_VISIBLE":
        return "offline replay continuity: decision_log->risk_log EV/risk trace annotations"
    if root_cause == "EV_NEVER_VISIBLE":
        return "EV producer observability: model attempt/emission reason coverage"
    if root_cause.startswith("MODEL_GATE:"):
        return "model attempt gate evidence: compact gate cause preservation"
    dominant_missing = ev_report.get("dominant_missing_producer")
    if dominant_missing:
        return f"producer field coverage: {dominant_missing}"
    return "no patch target until more fresh evidence exists"


def build_compact_run_summary(
    *,
    date: str,
    since: str | None = None,
    until: str | None = None,
    run_id: str | None = None,
    base_dir: str | Path = DEFAULT_QUANT_DATA_DIR,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
) -> dict[str, Any]:
    time_filter = build_time_filter(date_from=date, date_to=date, since=since, until=until, run_id=run_id)
    events, bad_json_lines = load_replay_events(
        base_dir=base_dir,
        date_from=date,
        date_to=date,
        since_utc=time_filter.get("since_utc"),
        until_utc=time_filter.get("until_utc"),
        run_id=run_id,
    )
    replay_report = analyze_replay(
        base_dir=base_dir,
        date=date,
        report_dir=report_dir,
        write_reports=False,
        write_csv=False,
        since=since,
        until=until,
        run_id=run_id,
    )
    replay_payload = replay_report.to_dict() if hasattr(replay_report, "to_dict") else dict(replay_report)
    runtime_report = evaluate_session_runtime(
        replay_report=replay_report,
        date=date,
        quant_data_dir=base_dir,
        load_offline_reports=False,
        since=since,
        until=until,
        run_id=run_id,
    )
    runtime_payload = runtime_report.to_dict() if hasattr(runtime_report, "to_dict") else dict(runtime_report)
    ev_report = build_ev_field_coverage_report(
        base_dir=base_dir,
        date=date,
        since=since,
        until=until,
        run_id=run_id,
    )
    run_id_label, run_ids_seen = _summarize_run_ids(events, run_id)
    event_identity = _identity_from_events(events)
    ev_status = _field_status_from_ev_report(ev_report)
    ev_risk_gap = _ev_risk_chain_gap(ev_report, ev_status)
    orderbook = _orderbook_health(events, replay_payload, ev_report)
    liquidity_spread, lifecycle_cutoff = _blockers(ev_report, replay_payload)
    model_activation = _model_activation_diagnostics(events, ev_report)
    model_handoff = _model_handoff_diagnostics(events)
    decision_funnel = _decision_runtime_eligibility_funnel(events)
    orderbook_readiness_audit = _decision_cycle_orderbook_readiness_audit(events)
    orderbook_sync_audit = _global_vs_decision_orderbook_sync_audit(events)
    orderbook_freshness_reuse = _orderbook_freshness_reuse_diagnostics(events)
    scheduler_cadence = _scheduler_cadence_diagnostics(events)
    candidate_timing = _candidate_timing_diagnostics(events, ev_report)
    root_cause = _root_cause_candidate(ev_status, ev_report, orderbook)
    summary = {
        "schema_version": "compact_run_summary_v1",
        "generated_at_utc": _utc_now(),
        "scope": "offline_compact_observability_only",
        "run_id": run_id_label,
        "run_ids_seen": run_ids_seen,
        "time_range": _time_range(date, since, until, events),
        "paper_activity": _paper_activity(events, replay_payload),
        "top_skip_reasons": _skip_reasons(events, replay_payload, runtime_payload),
        "ev_visibility": ev_status,
        "risk_layer_trace_readiness": ev_status["risk_layer_trace_readiness"],
        "candidate_chain_trace_confidence": ev_status["candidate_chain_trace_confidence"],
        "ev_risk_chain_gap_diagnostics": ev_risk_gap,
        "event_id_vs_chain_status": _event_chain_status(event_identity, ev_status),
        "orderbook_health": orderbook,
        "liquidity_spread_blockers": liquidity_spread,
        "lifecycle_cutoff_blockers": lifecycle_cutoff,
        "model_activation_diagnostics": model_activation,
        "model_handoff_diagnostics": model_handoff,
        "decision_runtime_eligibility_funnel": decision_funnel,
        "decision_cycle_orderbook_readiness_audit": orderbook_readiness_audit,
        "global_vs_decision_orderbook_sync_audit": orderbook_sync_audit,
        "orderbook_freshness_reuse_diagnostics": orderbook_freshness_reuse,
        "scheduler_cadence_diagnostics": scheduler_cadence,
        "candidate_timing_diagnostics": candidate_timing,
        "model_output_propagation": _model_output_propagation(events),
        "missing_fields_by_producer": _missing_fields_by_producer(events),
        "root_cause_candidate": root_cause,
        "recommended_next_codex_patch_target": _recommended_patch(root_cause, ev_report),
        "source_inputs": {
            "events_loaded": len(events),
            "bad_json_lines": bad_json_lines,
            "used_replay_analyzer": True,
            "used_session_runtime_evaluator": True,
            "used_ev_field_coverage": True,
        },
        "guardrails": {
            "offline_only": True,
            "runtime_behavior_changed": False,
            "strategy_risk_execution_changed": False,
        },
    }
    return summary


def write_compact_run_summary(summary: dict[str, Any], *, report_dir: str | Path = DEFAULT_REPORT_DIR) -> Path:
    date = str(summary.get("time_range", {}).get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"compact_run_summary_{date}.json"
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a compact offline run summary for prompt handoff.")
    parser.add_argument("--date", required=True, help="UTC date to summarize, YYYY-MM-DD.")
    parser.add_argument("--since", help="Optional UTC HH:MM start filter.")
    parser.add_argument("--until", help="Optional UTC HH:MM end filter.")
    parser.add_argument("--run-id", help="Optional run_id filter.")
    parser.add_argument("--base-dir", default=str(DEFAULT_QUANT_DATA_DIR), help="Quant data root directory.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Report output directory.")
    parser.add_argument("--write-report", action="store_true", help="Write runtime/reports/compact_run_summary_YYYY-MM-DD.json.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    summary = build_compact_run_summary(
        date=args.date,
        since=args.since,
        until=args.until,
        run_id=args.run_id,
        base_dir=args.base_dir,
        report_dir=args.report_dir,
    )
    if args.write_report:
        path = write_compact_run_summary(summary, report_dir=args.report_dir)
        summary["written_report"] = str(path)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
