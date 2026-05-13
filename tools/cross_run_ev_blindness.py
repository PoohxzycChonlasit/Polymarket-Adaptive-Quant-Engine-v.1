from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from tools.replay_analyzer import DEFAULT_REPORT_DIR


SCHEMA_GENERATION_VERSION = "ev_field_coverage_post_fallback_condition_coverage_verification_v1"
IDENTITY_CONFIDENCE_LEVELS = ("DIRECT", "STRONG", "WEAK", "PROXY", "UNKNOWN")
TRACE_PRODUCER_ORDER = (
    "market_snapshots",
    "decision_log",
    "risk_log",
    "execution_log",
    "trade_journal",
)
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
    "WEAK": ("market_key", "lifecycle_phase", "candidate_seen_ts"),
    "PROXY": ("market_key", "candidate_seen_ts"),
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
FRESHNESS_REQUIRED_SUMMARY_FIELDS = (
    "candidate_trace_confidence_counts",
    "ev_visibility_attempted_count",
    "propagation_gap_detected_count",
    "identity_confidence_by_producer",
    "producer_transition_identity_gap_tables",
    "missing_envelope_fields_by_producer",
    "envelope_readiness_score",
    "risk_layer_envelope_gap_report",
)
FRESHNESS_REQUIRED_PAYLOAD_FIELDS = (
    "candidate_trace_confidence_schema",
    "candidate_trace_confidence_diagnostics",
    "direct_vs_proxy_identity_gap_schema",
    "candidate_trace_envelope_spec",
    "risk_layer_envelope_gap_schema",
    "decision_to_risk_boundary_schema",
    "pre_risk_block_cause_taxonomy_schema",
    "model_state_attempt_emission_gap_schema",
    "model_attempt_gate_taxonomy_schema",
    "candidate_identity_upgrade_requirements_schema",
    "candidate_trace_id_post_emission_verification_schema",
    "alias_normalization_coverage_schema",
    "post_condition_enrichment_verification_schema",
    "post_fallback_condition_coverage_verification_schema",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"date must be YYYY-MM-DD; got {value!r}") from exc


def _date_strings(date_from: str, date_to: str) -> list[str]:
    start = _parse_date(date_from)
    end = _parse_date(date_to)
    if start > end:
        raise ValueError("--from must be earlier than or equal to --to")
    dates: list[str] = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _safe_filename_token(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return ("".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in text)[:80]) or "run"


def _as_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool) or value is None:
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool) or value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _counter_dict(counter: Counter[str], *, limit: int | None = None) -> dict[str, int]:
    return {str(key): int(value) for key, value in counter.most_common(limit) if int(value) > 0}


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
            bucket[field] += _as_int(values.get(field))


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
        "guardrail": "spec/report only; does not emit runtime fields, reconstruct EV values, infer execution, or authorize trading decisions",
    }


def _merge_envelope_missing(target: dict[str, Counter[str]], source: Any) -> None:
    if not isinstance(source, dict):
        return
    for producer, fields in source.items():
        if not isinstance(fields, dict):
            continue
        bucket = target.setdefault(str(producer), Counter())
        for field, stats in fields.items():
            if not isinstance(stats, dict):
                continue
            bucket[f"{field}:missing"] += _as_int(stats.get("missing_count"))
            bucket[f"{field}:present"] += _as_int(stats.get("present_count"))
            bucket[f"{field}:required"] += _as_int(stats.get("required_count"))


def _envelope_summary_from_missing(raw: dict[str, Counter[str]]) -> dict[str, Any]:
    missing_by_producer: dict[str, Any] = {}
    readiness_by_producer: dict[str, Any] = {}
    runtime_needed: dict[str, list[str]] = {}
    total_required = 0
    total_present = 0
    for producer, counts in sorted(raw.items()):
        field_names = sorted({key.rsplit(":", 1)[0] for key in counts})
        producer_required = 0
        producer_present = 0
        field_missing: dict[str, Any] = {}
        needed: list[str] = []
        for field in field_names:
            required_count = int(counts.get(f"{field}:required", 0))
            present_count = int(counts.get(f"{field}:present", 0))
            missing_count = int(counts.get(f"{field}:missing", max(0, required_count - present_count)))
            producer_required += required_count
            producer_present += present_count
            if missing_count:
                needed.append(field)
            field_missing[field] = {
                "missing_count": missing_count,
                "present_count": present_count,
                "required_count": required_count,
                "missing_rate": round(missing_count / required_count, 4) if required_count else 0.0,
            }
        total_required += producer_required
        total_present += producer_present
        readiness_by_producer[producer] = {
            "envelope_readiness_score": round(producer_present / producer_required, 4) if producer_required else 0.0,
            "present_field_slots": producer_present,
            "required_field_slots": producer_required,
            "missing_field_slots": max(0, producer_required - producer_present),
        }
        missing_by_producer[producer] = field_missing
        runtime_needed[producer] = needed
    weakest = min(
        readiness_by_producer.items(),
        key=lambda item: (item[1]["envelope_readiness_score"], -item[1]["missing_field_slots"], item[0]),
    )[0] if readiness_by_producer else "none"
    return {
        "candidate_trace_envelope_spec": _candidate_trace_envelope_spec(),
        "missing_envelope_fields_by_producer": missing_by_producer,
        "envelope_readiness_by_producer": readiness_by_producer,
        "envelope_readiness_score": round(total_present / total_required, 4) if total_required else 0.0,
        "weakest_envelope_producer": {
            "producer": weakest,
            **readiness_by_producer.get(weakest, {}),
        },
        "runtime_observability_fields_needed": runtime_needed,
        "interpretation": "offline readiness audit for a future canonical trace envelope; no runtime emission is implemented",
    }


def _merge_risk_layer_report(target: dict[str, Any], source: Any) -> None:
    if not isinstance(source, dict):
        return
    count_fields = (
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
        "ev_related_pre_risk_block_count",
        "microstructure_related_pre_risk_block_count",
        "timing_related_pre_risk_block_count",
        "identity_related_pre_risk_block_count",
        "unknown_pre_risk_block_count",
        "model_attempt_visible_count",
        "model_output_serialized_count",
        "identity_blocked_model_link_count",
        "model_attempt_eligible_count",
        "model_gate_microstructure_count",
        "model_gate_timing_count",
        "model_gate_identity_count",
        "model_gate_unknown_count",
    )
    for field in count_fields:
        target[field] = _as_int(target.get(field)) + _as_int(source.get(field))
    readiness = _as_float(source.get("risk_layer_trace_readiness"))
    if readiness or source.get("risk_layer_trace_readiness") == 0:
        target["risk_layer_trace_readiness_values"].append(readiness)
    for field, target_key in (
        ("decision_to_risk_handoff_quality", "decision_to_risk_handoff_quality"),
        ("risk_to_execution_handoff_quality", "risk_to_execution_handoff_quality"),
        ("risk_layer_block_visibility", "risk_layer_block_visibility"),
        ("risk_visibility_failure_counts", "risk_visibility_failure_counts"),
        ("decision_to_risk_boundary_counts", "decision_to_risk_boundary_counts"),
        ("pre_risk_block_cause_counts", "pre_risk_block_cause_counts"),
        ("model_state_gap_counts", "model_state_gap_counts"),
        ("probability_state_gap_counts", "probability_state_gap_counts"),
        ("fair_value_state_gap_counts", "fair_value_state_gap_counts"),
        ("ev_state_gap_counts", "ev_state_gap_counts"),
        ("model_attempt_gate_counts", "model_attempt_gate_counts"),
        ("missing_fields_preventing_direct_identity", "missing_fields_preventing_direct_identity"),
        ("missing_fields_preventing_strong_identity", "missing_fields_preventing_strong_identity"),
        ("candidate_identity_upgrade_path_counts", "candidate_identity_upgrade_path_counts"),
    ):
        values = source.get(field)
        if isinstance(values, dict):
            for key, count in values.items():
                target[target_key][str(key)] += _as_int(count)
    for field in (
        "risk_reachability_rate",
        "risk_serialization_visibility_rate",
        "pre_risk_block_share",
        "no_decision_evidence_share",
    ):
        if field in source:
            target[f"{field}_values"].append(_as_float(source.get(field)))
    for field in source.get("runtime_observability_fields_needed_for_risk_layer", []):
        target["runtime_observability_fields_needed_for_risk_layer"][str(field)] += 1
    impact = source.get("hypothetical_identity_upgrade_impact")
    if isinstance(impact, dict):
        values = impact.get("field_impact_counts")
        if isinstance(values, dict):
            for key, count in values.items():
                target["hypothetical_identity_upgrade_field_impact_counts"][str(key)] += _as_int(count)


def _risk_layer_report_dict(raw: dict[str, Any]) -> dict[str, Any]:
    readiness_values = raw.get("risk_layer_trace_readiness_values", [])
    failure_counts = raw.get("risk_visibility_failure_counts", Counter())
    weakest = failure_counts.most_common(1)[0][0] if failure_counts else "none"
    needed_counter = raw.get("runtime_observability_fields_needed_for_risk_layer", Counter())
    boundary_counts = raw.get("decision_to_risk_boundary_counts", Counter())
    for category in DECISION_TO_RISK_BOUNDARY_CATEGORIES:
        boundary_counts.setdefault(category, 0)
    dominant_boundary = boundary_counts.most_common(1)[0][0] if boundary_counts else "LEGACY_OR_UNKNOWN"
    pre_risk_cause_counts = raw.get("pre_risk_block_cause_counts", Counter())
    for cause in PRE_RISK_BLOCK_CAUSES:
        pre_risk_cause_counts.setdefault(cause, 0)
    total_pre_risk_blocks = int(boundary_counts.get("BLOCKED_BEFORE_RISK", 0))
    dominant_pre_risk_cause = pre_risk_cause_counts.most_common(1)[0][0] if total_pre_risk_blocks else "none"
    pre_risk_cause_share = {
        cause: _identity_rate(count, total_pre_risk_blocks) if total_pre_risk_blocks else 0.0
        for cause, count in pre_risk_cause_counts.most_common()
    }
    model_state_gap_counts = raw.get("model_state_gap_counts", Counter())
    probability_state_gap_counts = raw.get("probability_state_gap_counts", Counter())
    fair_value_state_gap_counts = raw.get("fair_value_state_gap_counts", Counter())
    ev_state_gap_counts = raw.get("ev_state_gap_counts", Counter())
    for gap in MODEL_STATE_GAP_CATEGORIES:
        model_state_gap_counts.setdefault(gap, 0)
        probability_state_gap_counts.setdefault(gap, 0)
        fair_value_state_gap_counts.setdefault(gap, 0)
        ev_state_gap_counts.setdefault(gap, 0)
    total_candidates = max(1, sum(boundary_counts.values()))
    dominant_model_state_gap = model_state_gap_counts.most_common(1)[0][0] if total_candidates else "none"
    model_attempt_gate_counts = raw.get("model_attempt_gate_counts", Counter())
    for gate in MODEL_ATTEMPT_GATE_CAUSES:
        model_attempt_gate_counts.setdefault(gate, 0)
    total_model_gated_candidates = (
        int(model_state_gap_counts.get("MODEL_NOT_ATTEMPTED", 0))
        + int(model_state_gap_counts.get("BLOCKED_BEFORE_MODEL", 0))
    )
    dominant_model_attempt_gate = model_attempt_gate_counts.most_common(1)[0][0] if total_model_gated_candidates else "none"
    missing_direct_identity_fields = raw.get("missing_fields_preventing_direct_identity", Counter())
    missing_strong_identity_fields = raw.get("missing_fields_preventing_strong_identity", Counter())
    identity_upgrade_path_counts = raw.get("candidate_identity_upgrade_path_counts", Counter())
    direct_identity_blocker_rank = [
        {"field": field, "missing_count": int(count), "share": _identity_rate(int(count), total_candidates)}
        for field, count in missing_direct_identity_fields.most_common()
    ]
    strong_identity_blocker_rank = [
        {"field": field, "missing_count": int(count), "share": _identity_rate(int(count), total_candidates)}
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

    def avg_metric(field: str) -> float:
        values = raw.get(f"{field}_values", [])
        return round(sum(values) / len(values), 4) if values else 0.0
    return {
        "risk_log_identity_missing_count": _as_int(raw.get("risk_log_identity_missing_count")),
        "risk_log_market_key_missing_count": _as_int(raw.get("risk_log_market_key_missing_count")),
        "risk_log_lifecycle_phase_missing_count": _as_int(raw.get("risk_log_lifecycle_phase_missing_count")),
        "risk_log_risk_state_missing_count": _as_int(raw.get("risk_log_risk_state_missing_count")),
        "no_risk_event_exists_count": _as_int(raw.get("no_risk_event_exists_count")),
        "risk_event_exists_but_lacks_candidate_identity_count": _as_int(raw.get("risk_event_exists_but_lacks_candidate_identity_count")),
        "risk_event_exists_but_lacks_risk_state_count": _as_int(raw.get("risk_event_exists_but_lacks_risk_state_count")),
        "candidate_blocked_before_risk_visibility_count": _as_int(raw.get("candidate_blocked_before_risk_visibility_count")),
        "ev_visible_before_risk_missing_after_count": _as_int(raw.get("ev_visible_before_risk_missing_after_count")),
        "risk_producer_not_responsible_count": _as_int(raw.get("risk_producer_not_responsible_count")),
        "stale_legacy_schema_count": _as_int(raw.get("stale_legacy_schema_count")),
        "decision_to_risk_handoff_quality": _counter_dict(raw.get("decision_to_risk_handoff_quality", Counter())),
        "risk_to_execution_handoff_quality": _counter_dict(raw.get("risk_to_execution_handoff_quality", Counter())),
        "risk_layer_trace_readiness": round(sum(readiness_values) / len(readiness_values), 4) if readiness_values else 0.0,
        "risk_layer_block_visibility": _counter_dict(raw.get("risk_layer_block_visibility", Counter())),
        "weakest_risk_gap_reason": weakest,
        "dominant_risk_visibility_failure": weakest,
        "risk_visibility_failure_counts": _counter_dict(failure_counts),
        "runtime_observability_fields_needed_for_risk_layer": [
            field for field, _count in needed_counter.most_common()
        ],
        "decision_to_risk_boundary_categories": list(DECISION_TO_RISK_BOUNDARY_CATEGORIES),
        "decision_to_risk_boundary_counts": _counter_dict(boundary_counts),
        "risk_reachability_rate": avg_metric("risk_reachability_rate"),
        "risk_serialization_visibility_rate": avg_metric("risk_serialization_visibility_rate"),
        "pre_risk_block_share": avg_metric("pre_risk_block_share"),
        "no_decision_evidence_share": avg_metric("no_decision_evidence_share"),
        "dominant_decision_to_risk_boundary_failure": dominant_boundary,
        "decision_to_risk_boundary_interpretation": (
            "risk reach is counted only when a serialized risk event or explicit risk-state evidence exists; "
            "absence of a risk event is not treated as a risk-layer failure by itself"
        ),
        "pre_risk_block_cause_taxonomy": list(PRE_RISK_BLOCK_CAUSES),
        "pre_risk_block_cause_counts": _counter_dict(pre_risk_cause_counts),
        "dominant_pre_risk_block_cause": dominant_pre_risk_cause,
        "pre_risk_block_cause_share": pre_risk_cause_share,
        "ev_related_pre_risk_block_count": _as_int(raw.get("ev_related_pre_risk_block_count")),
        "microstructure_related_pre_risk_block_count": _as_int(raw.get("microstructure_related_pre_risk_block_count")),
        "timing_related_pre_risk_block_count": _as_int(raw.get("timing_related_pre_risk_block_count")),
        "identity_related_pre_risk_block_count": _as_int(raw.get("identity_related_pre_risk_block_count")),
        "unknown_pre_risk_block_count": _as_int(raw.get("unknown_pre_risk_block_count")),
        "ev_related_pre_risk_block_share": _identity_rate(_as_int(raw.get("ev_related_pre_risk_block_count")), total_pre_risk_blocks),
        "microstructure_related_pre_risk_block_share": _identity_rate(
            _as_int(raw.get("microstructure_related_pre_risk_block_count")), total_pre_risk_blocks
        ),
        "timing_related_pre_risk_block_share": _identity_rate(_as_int(raw.get("timing_related_pre_risk_block_count")), total_pre_risk_blocks),
        "identity_related_pre_risk_block_share": _identity_rate(
            _as_int(raw.get("identity_related_pre_risk_block_count")), total_pre_risk_blocks
        ),
        "unknown_pre_risk_block_share": _identity_rate(_as_int(raw.get("unknown_pre_risk_block_count")), total_pre_risk_blocks),
        "model_state_gap_taxonomy": list(MODEL_STATE_GAP_CATEGORIES),
        "model_state_gap_counts": _counter_dict(model_state_gap_counts),
        "probability_state_gap_counts": _counter_dict(probability_state_gap_counts),
        "fair_value_state_gap_counts": _counter_dict(fair_value_state_gap_counts),
        "ev_state_gap_counts": _counter_dict(ev_state_gap_counts),
        "model_attempt_visible_count": _as_int(raw.get("model_attempt_visible_count")),
        "model_output_serialized_count": _as_int(raw.get("model_output_serialized_count")),
        "identity_blocked_model_link_count": _as_int(raw.get("identity_blocked_model_link_count")),
        "model_attempt_visibility_rate": _identity_rate(_as_int(raw.get("model_attempt_visible_count")), total_candidates),
        "model_output_serialization_rate": _identity_rate(_as_int(raw.get("model_output_serialized_count")), total_candidates),
        "identity_blocked_model_link_rate": _identity_rate(_as_int(raw.get("identity_blocked_model_link_count")), total_candidates),
        "dominant_model_state_gap": dominant_model_state_gap,
        "model_attempt_gate_taxonomy": list(MODEL_ATTEMPT_GATE_CAUSES),
        "model_attempt_gate_counts": _counter_dict(model_attempt_gate_counts),
        "dominant_model_attempt_gate": dominant_model_attempt_gate,
        "model_gate_microstructure_share": _identity_rate(
            _as_int(raw.get("model_gate_microstructure_count")),
            total_model_gated_candidates,
        ),
        "model_gate_timing_share": _identity_rate(
            _as_int(raw.get("model_gate_timing_count")),
            total_model_gated_candidates,
        ),
        "model_gate_identity_share": _identity_rate(
            _as_int(raw.get("model_gate_identity_count")),
            total_model_gated_candidates,
        ),
        "model_gate_unknown_share": _identity_rate(
            _as_int(raw.get("model_gate_unknown_count")),
            total_model_gated_candidates,
        ),
        "model_gate_microstructure_count": _as_int(raw.get("model_gate_microstructure_count")),
        "model_gate_timing_count": _as_int(raw.get("model_gate_timing_count")),
        "model_gate_identity_count": _as_int(raw.get("model_gate_identity_count")),
        "model_gate_unknown_count": _as_int(raw.get("model_gate_unknown_count")),
        "model_attempt_eligible_count": _as_int(raw.get("model_attempt_eligible_count")),
        "model_attempt_eligibility_rate": _identity_rate(_as_int(raw.get("model_attempt_eligible_count")), total_candidates),
        "identity_confidence_requirements": {
            level: list(fields)
            for level, fields in IDENTITY_CONFIDENCE_REQUIREMENTS.items()
        },
        "identity_upgrade_required_fields": list(IDENTITY_UPGRADE_FIELDS),
        "missing_fields_preventing_direct_identity": _counter_dict(missing_direct_identity_fields),
        "missing_fields_preventing_strong_identity": _counter_dict(missing_strong_identity_fields),
        "candidate_identity_upgrade_path_counts": _counter_dict(identity_upgrade_path_counts),
        "easiest_identity_upgrade_field": easiest_identity_upgrade_field,
        "highest_impact_identity_field": highest_impact_identity_field,
        "direct_identity_blocker_rank": direct_identity_blocker_rank,
        "strong_identity_blocker_rank": strong_identity_blocker_rank,
        "hypothetical_identity_upgrade_impact": {
            "field_impact_counts": _counter_dict(raw.get("hypothetical_identity_upgrade_field_impact_counts", Counter())),
            "rule": "hypothetical missing-field impact only; actual candidate_trace_confidence remains unchanged",
        },
        "transition_analysis": {
            "decision_log->risk_log": _counter_dict(raw.get("decision_to_risk_handoff_quality", Counter())),
            "risk_log->execution_log": _counter_dict(raw.get("risk_to_execution_handoff_quality", Counter())),
        },
        "guardrail": "offline replay observability only; does not change risk logic, sizing, execution, or runtime emission",
    }


def _date_from_payload_or_path(payload: dict[str, Any], path: Path) -> str:
    for key in ("date_from", "date", "session_date"):
        value = str(payload.get(key) or "").strip()
        if len(value) >= 10:
            return value[:10]
    for part in path.name.split("_"):
        if len(part) == 10 and part[4] == "-" and part[7] == "-":
            return part
    return ""


def _run_id(payload: dict[str, Any]) -> str:
    run_id = str(payload.get("run_id") or "").strip()
    if run_id:
        return run_id
    time_filter = payload.get("time_filter")
    if isinstance(time_filter, dict):
        return str(time_filter.get("run_id") or "").strip()
    return ""


def _is_ev_field_coverage_report(payload: dict[str, Any], path: Path) -> bool:
    return path.name.startswith("ev_field_coverage_") or payload.get("schema_version") == "ev_field_coverage_v1"


def _schema_freshness(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    trace_summary = (
        summary.get("ev_candidate_lifecycle_trace_summary")
        if isinstance(summary.get("ev_candidate_lifecycle_trace_summary"), dict)
        else {}
    )
    diagnostics = payload.get("candidate_trace_confidence_diagnostics")
    diagnostics = diagnostics if isinstance(diagnostics, dict) else {}
    missing: list[str] = []
    if payload.get("schema_generation_version") != SCHEMA_GENERATION_VERSION:
        missing.append("schema_generation_version")
    for field in FRESHNESS_REQUIRED_PAYLOAD_FIELDS:
        if field not in payload:
            missing.append(field)
    for field in FRESHNESS_REQUIRED_SUMMARY_FIELDS:
        if field in {"ev_visibility_attempted_count", "propagation_gap_detected_count"}:
            if field not in diagnostics and field not in summary:
                missing.append(field)
        elif field not in summary and field not in payload and field not in trace_summary:
            missing.append(field)
    stale = bool(missing)
    return {
        "schema_generation_version": str(payload.get("schema_generation_version") or "legacy_or_unknown"),
        "replay_schema_freshness": "stale" if stale else "fresh",
        "stale_schema_detected": stale,
        "stale_report_reason": ",".join(missing) if stale else "",
        "schema_compatible": not stale,
    }


def _merge_counter(counter: Counter[str], value: Any) -> None:
    if not isinstance(value, dict):
        return
    for key, count in value.items():
        counter[str(key)] += _as_int(count)


def _merge_presence_table(target: dict[str, Counter[str]], source: Any, field: str) -> None:
    if not isinstance(source, dict):
        return
    bucket = target.setdefault(field, Counter())
    for producer, stats in source.items():
        if not isinstance(stats, dict):
            continue
        producer = str(producer)
        bucket[f"{producer}:present"] += _as_int(stats.get("present_count"))
        bucket[f"{producer}:missing"] += _as_int(stats.get("missing_count"))
        bucket[f"{producer}:total"] += _as_int(stats.get("total_events"))


def _presence_table_from_raw(raw: dict[str, Counter[str]], field: str) -> dict[str, Any]:
    counts = raw.get(field, Counter())
    producers = {
        key.rsplit(":", 1)[0]
        for key in counts
        if key.endswith(":total")
    }
    output: dict[str, Any] = {}
    for producer in sorted(set(TRACE_PRODUCER_ORDER) | producers):
        total = _as_int(counts.get(f"{producer}:total"))
        present = _as_int(counts.get(f"{producer}:present"))
        output[producer] = {
            "present_count": present,
            "missing_count": _as_int(counts.get(f"{producer}:missing")),
            "total_events": total,
            "presence_rate": _identity_rate(present, total),
        }
    return output


def _merge_post_emission_verification(target: dict[str, Any], source: Any) -> None:
    if not isinstance(source, dict):
        return
    for key in (
        "events_scanned",
        "candidate_trace_id_present_count",
        "candidate_trace_id_missing_count",
        "post_emission_direct_identity_candidates",
        "post_emission_strong_identity_candidates",
        "post_emission_proxy_candidates",
    ):
        target[key] = _as_int(target.get(key)) + _as_int(source.get(key))
    if source.get("post_emission_data_exists"):
        target["post_emission_data_exists_count"] += 1
    _merge_counter(target["fields_still_preventing_direct_identity"], source.get("fields_still_preventing_direct_identity"))
    for field, source_key in (
        ("candidate_trace_id", "candidate_trace_id_presence_by_producer"),
        ("parent_candidate_trace_id", "parent_candidate_trace_id_presence_by_producer"),
        ("trace_link_reason", "trace_link_reason_presence_by_producer"),
        ("market_key", "market_key_presence_by_producer"),
        ("condition_id", "condition_id_presence_by_producer"),
        ("token_id", "token_id_presence_by_producer"),
        ("side", "side_presence_by_producer"),
    ):
        _merge_presence_table(target["presence_by_producer"], source.get(source_key), field)


def _post_emission_verification_dict(raw: dict[str, Any]) -> dict[str, Any]:
    present = _as_int(raw.get("candidate_trace_id_present_count"))
    total = _as_int(raw.get("events_scanned"))
    status = "POST_EMISSION_DATA_FOUND" if present else "POST_EMISSION_DATA_NOT_FOUND"
    presence = raw.get("presence_by_producer", {})
    return {
        "post_emission_data_status": status,
        "post_emission_data_exists": bool(present),
        "reports_with_post_emission_data": _as_int(raw.get("post_emission_data_exists_count")),
        "events_scanned": total,
        "candidate_trace_id_present_count": present,
        "candidate_trace_id_missing_count": _as_int(raw.get("candidate_trace_id_missing_count")),
        "candidate_trace_id_presence_by_producer": _presence_table_from_raw(presence, "candidate_trace_id"),
        "parent_candidate_trace_id_presence_by_producer": _presence_table_from_raw(presence, "parent_candidate_trace_id"),
        "trace_link_reason_presence_by_producer": _presence_table_from_raw(presence, "trace_link_reason"),
        "market_key_presence_by_producer": _presence_table_from_raw(presence, "market_key"),
        "condition_id_presence_by_producer": _presence_table_from_raw(presence, "condition_id"),
        "token_id_presence_by_producer": _presence_table_from_raw(presence, "token_id"),
        "side_presence_by_producer": _presence_table_from_raw(presence, "side"),
        "post_emission_direct_identity_candidates": _as_int(raw.get("post_emission_direct_identity_candidates")),
        "post_emission_strong_identity_candidates": _as_int(raw.get("post_emission_strong_identity_candidates")),
        "post_emission_proxy_candidates": _as_int(raw.get("post_emission_proxy_candidates")),
        "direct_identity_improvement_possible": bool(present),
        "fields_still_preventing_direct_identity": _counter_dict(raw.get("fields_still_preventing_direct_identity", Counter())),
        "interpretation": (
            "fresh post-emission trace fields found in EV coverage inputs"
            if present
            else "POST_EMISSION_DATA_NOT_FOUND; no candidate_trace_id-bearing fresh EV coverage inputs were found"
        ),
        "guardrail": "offline verification only; historical reports are not treated as post-emission evidence",
    }


def _merge_alias_normalization_verification(target: dict[str, Any], source: Any) -> None:
    if not isinstance(source, dict):
        return
    for key in (
        "events_scanned",
        "trace_events_scanned",
        "trace_events_with_candidate_trace_id",
        "trace_events_with_condition_id",
        "trace_events_with_token_id",
        "trace_events_with_side",
        "trace_events_direct_ready",
        "trace_events_strong_ready",
    ):
        target[key] = _as_int(target.get(key)) + _as_int(source.get(key))
    if source.get("post_normalization_data_exists"):
        target["post_normalization_data_exists_count"] += 1
    _merge_counter(target["alias_normalized_field_counts"], source.get("alias_normalized_field_counts"))
    _merge_counter(target["alias_source_field_counts"], source.get("alias_source_field_counts"))
    _merge_counter(target["fields_still_missing_after_alias_normalization"], source.get("fields_still_missing_after_alias_normalization"))

    canonical = source.get("canonical_identity_field_presence_after_normalization")
    if isinstance(canonical, dict):
        for field, stats in canonical.items():
            if not isinstance(stats, dict):
                continue
            bucket = target["canonical_identity_field_presence_after_normalization"].setdefault(str(field), Counter())
            for key in ("present_count", "missing_count", "total_events"):
                bucket[key] += _as_int(stats.get(key))
            origins = stats.get("origin_counts") if isinstance(stats.get("origin_counts"), dict) else {}
            for origin, count in origins.items():
                bucket[f"origin:{origin}"] += _as_int(count)

    producer_alias = source.get("producer_alias_dependency_counts")
    if isinstance(producer_alias, dict):
        for producer, fields in producer_alias.items():
            if not isinstance(fields, dict):
                continue
            bucket = target["producer_alias_dependency_counts"].setdefault(str(producer), Counter())
            for field, count in fields.items():
                bucket[str(field)] += _as_int(count)

    producer_presence = source.get("producer_canonical_presence_counts")
    if isinstance(producer_presence, dict):
        for producer, fields in producer_presence.items():
            if not isinstance(fields, dict):
                continue
            bucket = target["producer_canonical_presence_counts"].setdefault(str(producer), Counter())
            for field, stats in fields.items():
                if not isinstance(stats, dict):
                    continue
                for key in ("present_count", "missing_count", "total_events"):
                    bucket[f"{field}:{key}"] += _as_int(stats.get(key))


def _alias_normalization_verification_dict(raw: dict[str, Any]) -> dict[str, Any]:
    trace_events = _as_int(raw.get("trace_events_with_candidate_trace_id"))
    status = "POST_NORMALIZATION_DATA_FOUND" if trace_events else "POST_NORMALIZATION_DATA_NOT_FOUND"
    canonical_output: dict[str, Any] = {}
    canonical_raw = raw.get("canonical_identity_field_presence_after_normalization", {})
    if isinstance(canonical_raw, dict):
        for field in sorted(set(ALIAS_NORMALIZATION_FIELDS) | set(canonical_raw)):
            counts = canonical_raw.get(field, Counter())
            present = _as_int(counts.get("present_count"))
            total = _as_int(counts.get("total_events"))
            canonical_output[field] = {
                "present_count": present,
                "missing_count": _as_int(counts.get("missing_count")),
                "total_events": total,
                "presence_rate": _identity_rate(present, total),
                "origin_counts": {
                    "original_canonical": _as_int(counts.get("origin:original_canonical")),
                    "normalized_alias": _as_int(counts.get("origin:normalized_alias")),
                    "missing": _as_int(counts.get("origin:missing")),
                },
            }

    producer_alias = {
        producer: _counter_dict(counts)
        for producer, counts in sorted(raw.get("producer_alias_dependency_counts", {}).items())
    }
    producer_presence: dict[str, Any] = {}
    for producer, counts in sorted(raw.get("producer_canonical_presence_counts", {}).items()):
        producer_presence[producer] = {}
        for field in ALIAS_NORMALIZATION_FIELDS:
            present = _as_int(counts.get(f"{field}:present_count"))
            total = _as_int(counts.get(f"{field}:total_events"))
            producer_presence[producer][field] = {
                "present_count": present,
                "missing_count": _as_int(counts.get(f"{field}:missing_count")),
                "total_events": total,
                "presence_rate": _identity_rate(present, total),
            }

    return {
        "post_normalization_data_status": status,
        "post_normalization_data_exists": bool(trace_events),
        "reports_with_post_normalization_data": _as_int(raw.get("post_normalization_data_exists_count")),
        "events_scanned": _as_int(raw.get("events_scanned")),
        "trace_events_scanned": _as_int(raw.get("trace_events_scanned")),
        "alias_normalized_field_counts": _counter_dict(raw.get("alias_normalized_field_counts", Counter())),
        "alias_source_field_counts": _counter_dict(raw.get("alias_source_field_counts", Counter())),
        "canonical_identity_field_presence_after_normalization": canonical_output if trace_events else {},
        "producer_alias_dependency_counts": producer_alias if trace_events else {},
        "producer_canonical_presence_counts": producer_presence if trace_events else {},
        "trace_events_with_candidate_trace_id": trace_events,
        "trace_events_with_condition_id": _as_int(raw.get("trace_events_with_condition_id")) if trace_events else 0,
        "trace_events_with_token_id": _as_int(raw.get("trace_events_with_token_id")) if trace_events else 0,
        "trace_events_with_side": _as_int(raw.get("trace_events_with_side")) if trace_events else 0,
        "trace_events_direct_ready": _as_int(raw.get("trace_events_direct_ready")) if trace_events else 0,
        "trace_events_strong_ready": _as_int(raw.get("trace_events_strong_ready")) if trace_events else 0,
        "fields_still_missing_after_alias_normalization": _counter_dict(raw.get("fields_still_missing_after_alias_normalization", Counter())) if trace_events else {},
        "interpretation": (
            "fresh post-normalization trace fields found in EV coverage inputs"
            if trace_events
            else "POST_NORMALIZATION_DATA_NOT_FOUND; no candidate_trace_id-bearing fresh EV coverage inputs were found"
        ),
        "guardrail": "offline alias coverage verification only; historical reports are not treated as post-normalization evidence",
    }


def _merge_post_condition_enrichment_verification(target: dict[str, Any], source: Any) -> None:
    if not isinstance(source, dict):
        return
    for key in (
        "events_scanned",
        "trace_events_scanned",
        "traced_events_with_condition_id_after_enrichment",
        "condition_id_enrichment_candidate_count",
        "trace_events_direct_ready_after_condition_enrichment",
        "trace_events_strong_ready_after_condition_enrichment",
    ):
        target[key] = _as_int(target.get(key)) + _as_int(source.get(key))
    if source.get("post_condition_enrichment_data_exists"):
        target["post_condition_enrichment_data_exists_count"] += 1
    _merge_presence_table(
        target["condition_id_presence_by_producer_after_enrichment"],
        source.get("condition_id_presence_by_producer_after_enrichment"),
        "condition_id",
    )
    _merge_counter(
        target["fields_still_preventing_direct_identity_after_condition_enrichment"],
        source.get("fields_still_preventing_direct_identity_after_condition_enrichment"),
    )
    _merge_counter(
        target["fields_still_preventing_strong_identity_after_condition_enrichment"],
        source.get("fields_still_preventing_strong_identity_after_condition_enrichment"),
    )


def _post_condition_enrichment_verification_dict(raw: dict[str, Any]) -> dict[str, Any]:
    condition_count = _as_int(raw.get("traced_events_with_condition_id_after_enrichment"))
    direct_ready = _as_int(raw.get("trace_events_direct_ready_after_condition_enrichment")) if condition_count else 0
    strong_ready = _as_int(raw.get("trace_events_strong_ready_after_condition_enrichment")) if condition_count else 0
    status = (
        "POST_CONDITION_ENRICHMENT_DATA_FOUND"
        if condition_count
        else "POST_CONDITION_ENRICHMENT_DATA_NOT_FOUND"
    )
    return {
        "post_condition_enrichment_data_status": status,
        "post_condition_enrichment_data_exists": bool(condition_count),
        "reports_with_post_condition_enrichment_data": _as_int(raw.get("post_condition_enrichment_data_exists_count")),
        "events_scanned": _as_int(raw.get("events_scanned")),
        "trace_events_scanned": _as_int(raw.get("trace_events_scanned")),
        "pre_patch_traced_events_with_condition_id": 0,
        "pre_patch_trace_events_direct_ready": 0,
        "pre_patch_trace_events_strong_ready": 0,
        "traced_events_with_condition_id_after_enrichment": condition_count,
        "condition_id_presence_by_producer_after_enrichment": _presence_table_from_raw(
            raw.get("condition_id_presence_by_producer_after_enrichment", {}),
            "condition_id",
        ),
        "condition_id_enrichment_candidate_count": _as_int(raw.get("condition_id_enrichment_candidate_count")) if condition_count else 0,
        "trace_events_direct_ready_after_condition_enrichment": direct_ready,
        "trace_events_strong_ready_after_condition_enrichment": strong_ready,
        "condition_enrichment_delta": {
            "traced_events_with_condition_id_delta": condition_count,
            "trace_events_direct_ready_delta": direct_ready,
            "trace_events_strong_ready_delta": strong_ready,
        },
        "fields_still_preventing_direct_identity_after_condition_enrichment": (
            _counter_dict(raw.get("fields_still_preventing_direct_identity_after_condition_enrichment", Counter()))
            if condition_count
            else {}
        ),
        "fields_still_preventing_strong_identity_after_condition_enrichment": (
            _counter_dict(raw.get("fields_still_preventing_strong_identity_after_condition_enrichment", Counter()))
            if condition_count
            else {}
        ),
        "interpretation": (
            "fresh EV coverage inputs contain candidate_trace_id-bearing events with canonical condition_id"
            if condition_count
            else "POST_CONDITION_ENRICHMENT_DATA_NOT_FOUND; no candidate_trace_id-bearing fresh EV coverage inputs with canonical condition_id were found"
        ),
        "guardrail": "offline verification only; old reports are not reinterpreted as post-condition-enrichment evidence",
    }


def _merge_post_fallback_condition_coverage_verification(target: dict[str, Any], source: Any) -> None:
    if not isinstance(source, dict):
        return
    for key in (
        "trace_events_with_candidate_trace_id",
        "traced_events_with_condition_id",
        "trace_events_direct_ready",
        "trace_events_strong_ready",
    ):
        target[key] = _as_int(target.get(key)) + _as_int(source.get(key))
    if source.get("post_fallback_data_exists"):
        target["post_fallback_data_exists_count"] += 1
    _merge_presence_table(
        target["condition_id_presence_by_producer"],
        source.get("condition_id_presence_by_producer"),
        "condition_id",
    )
    _merge_counter(target["remaining_identity_blockers"], source.get("remaining_identity_blockers"))


def _post_fallback_condition_coverage_verification_dict(raw: dict[str, Any]) -> dict[str, Any]:
    condition_count = _as_int(raw.get("traced_events_with_condition_id"))
    direct_ready = _as_int(raw.get("trace_events_direct_ready")) if condition_count else 0
    strong_ready = _as_int(raw.get("trace_events_strong_ready")) if condition_count else 0
    status = "POST_FALLBACK_DATA_FOUND" if condition_count else "POST_FALLBACK_DATA_NOT_FOUND"
    return {
        "post_fallback_data_status": status,
        "post_fallback_data_exists": bool(condition_count),
        "reports_with_post_fallback_data": _as_int(raw.get("post_fallback_data_exists_count")),
        "pre_fallback_condition_id": 0,
        "pre_fallback_direct_ready": 0,
        "pre_fallback_strong_ready": 0,
        "trace_events_with_candidate_trace_id": _as_int(raw.get("trace_events_with_candidate_trace_id")),
        "traced_events_with_condition_id": condition_count,
        "condition_id_presence_by_producer": _presence_table_from_raw(
            raw.get("condition_id_presence_by_producer", {}),
            "condition_id",
        ),
        "trace_events_direct_ready": direct_ready,
        "trace_events_strong_ready": strong_ready,
        "remaining_identity_blockers": _counter_dict(raw.get("remaining_identity_blockers", Counter())),
        "post_fallback_delta": {
            "condition_id_delta": condition_count,
            "direct_ready_delta": direct_ready,
            "strong_ready_delta": strong_ready,
        },
        "interpretation": (
            "fresh EV coverage inputs contain post-fallback candidate_trace_id-bearing events with canonical condition_id"
            if condition_count
            else "POST_FALLBACK_DATA_NOT_FOUND; no fresh EV coverage input contains candidate_trace_id-bearing events with canonical condition_id"
        ),
        "guardrail": "offline cross-run verification only; condition_id and candidate_trace_id are not used for runtime decisions",
    }


def _merge_crosstab(target: dict[str, Counter[str]], source: Any) -> None:
    if not isinstance(source, dict):
        return
    for context, reason_counts in source.items():
        if not isinstance(reason_counts, dict):
            continue
        if context not in target:
            target[str(context)] = Counter()
        for reason, count in reason_counts.items():
            target[str(context)][str(reason)] += _as_int(count)


def _merge_producer_missing(target: dict[str, Counter[str]], source: Any) -> None:
    if not isinstance(source, dict):
        return
    for category, counts in source.items():
        if not isinstance(counts, dict):
            continue
        if category not in target:
            target[str(category)] = Counter()
        for key in ("field_not_emitted", "legacy_missing_reason", "missing_uncertain_ev_fields", "total_ev_field_slots"):
            target[str(category)][key] += _as_int(counts.get(key))


def _merge_producer_visibility(target: dict[str, dict[str, Any]], source: Any) -> None:
    if not isinstance(source, dict):
        return
    by_category = source.get("by_event_category") if isinstance(source.get("by_event_category"), dict) else {}
    for category, stats in by_category.items():
        if not isinstance(stats, dict):
            continue
        if category not in target:
            target[str(category)] = {
                "event_count": 0,
                "total_ev_field_slots": 0,
                "visible_ev_field_slots": 0,
                "ev_visible_event_count": 0,
                "missing_reason_counts": Counter(),
            }
        bucket = target[str(category)]
        bucket["event_count"] += _as_int(stats.get("event_count"))
        bucket["total_ev_field_slots"] += _as_int(stats.get("total_ev_field_slots"))
        bucket["visible_ev_field_slots"] += _as_int(stats.get("visible_ev_field_slots"))
        bucket["ev_visible_event_count"] += _as_int(stats.get("ev_visible_event_count"))
        reasons = stats.get("missing_reason_counts") if isinstance(stats.get("missing_reason_counts"), dict) else {}
        for reason, count in reasons.items():
            bucket["missing_reason_counts"][str(reason)] += _as_int(count)


def _merge_trace_summary(target: dict[str, Any], source: Any) -> None:
    if not isinstance(source, dict):
        return
    target["traceable_candidates"] += _as_int(source.get("traceable_candidates"))
    avg_score = _as_float(source.get("avg_ev_lifecycle_visibility_score"))
    avg_survival = _as_float(source.get("avg_continuity_survival_rate"))
    if avg_score:
        target["visibility_scores"].append(avg_score)
    if avg_survival:
        target["survival_rates"].append(avg_survival)
    counter_fields = (
        "first_ev_visible_phase_counts",
        "last_ev_visible_phase_counts",
        "ev_disappearance_phase_counts",
        "ev_disappearance_reason_counts",
        "ev_trace_break_phase_counts",
        "producer_handoff_quality_counts",
        "lifecycle_observability_quality_counts",
        "candidate_trace_confidence_counts",
    )
    for field in counter_fields:
        bucket = target.setdefault(field, Counter())
        values = source.get(field)
        if not isinstance(values, dict):
            continue
        for key, count in values.items():
            bucket[str(key)] += _as_int(count)


def _trace_summary_dict(trace: dict[str, Any]) -> dict[str, Any]:
    scores = trace.get("visibility_scores", [])
    survival_rates = trace.get("survival_rates", [])
    return {
        "traceable_candidates": _as_int(trace.get("traceable_candidates")),
        "avg_ev_lifecycle_visibility_score": round(sum(scores) / len(scores), 4) if scores else 0.0,
        "avg_continuity_survival_rate": round(sum(survival_rates) / len(survival_rates), 4) if survival_rates else 0.0,
        "first_ev_visible_phase_counts": _counter_dict(trace.get("first_ev_visible_phase_counts", Counter())),
        "last_ev_visible_phase_counts": _counter_dict(trace.get("last_ev_visible_phase_counts", Counter())),
        "ev_disappearance_phase_counts": _counter_dict(trace.get("ev_disappearance_phase_counts", Counter())),
        "ev_disappearance_reason_counts": _counter_dict(trace.get("ev_disappearance_reason_counts", Counter())),
        "ev_trace_break_phase_counts": _counter_dict(trace.get("ev_trace_break_phase_counts", Counter())),
        "producer_handoff_quality_counts": _counter_dict(trace.get("producer_handoff_quality_counts", Counter())),
        "lifecycle_observability_quality_counts": _counter_dict(trace.get("lifecycle_observability_quality_counts", Counter())),
        "candidate_trace_confidence_counts": _counter_dict(trace.get("candidate_trace_confidence_counts", Counter())),
    }


def _producer_summary(
    missing: dict[str, Counter[str]],
    visibility: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    categories = sorted(set(missing) | set(visibility))
    missing_by_category: dict[str, Any] = {}
    producer_level: dict[str, Any] = {}
    missing_counter: Counter[str] = Counter()
    total_uncertain = 0
    best_category = "none"
    best_rate = 0.0
    for category in categories:
        miss = missing.get(category, Counter())
        visible = visibility.get(category, {})
        field_not_emitted = _as_int(miss.get("field_not_emitted"))
        legacy_missing = _as_int(miss.get("legacy_missing_reason"))
        uncertain = _as_int(miss.get("missing_uncertain_ev_fields"), field_not_emitted + legacy_missing)
        slots = _as_int(miss.get("total_ev_field_slots")) or _as_int(visible.get("total_ev_field_slots"))
        visible_slots = _as_int(visible.get("visible_ev_field_slots"))
        rate = round(visible_slots / slots, 4) if slots else 0.0
        total_uncertain += uncertain
        missing_counter[category] = uncertain
        missing_by_category[category] = {
            "field_not_emitted": field_not_emitted,
            "legacy_missing_reason": legacy_missing,
            "missing_uncertain_ev_fields": uncertain,
            "total_ev_field_slots": slots,
            "missing_uncertain_share_of_slots": round(uncertain / slots, 4) if slots else 0.0,
        }
        producer_level[category] = {
            "event_count": _as_int(visible.get("event_count")),
            "total_ev_field_slots": slots,
            "visible_ev_field_slots": visible_slots,
            "ev_visible_event_count": _as_int(visible.get("ev_visible_event_count")),
            "ev_field_continuity_rate": rate,
            "missing_reason_counts": _counter_dict(visible.get("missing_reason_counts", Counter())),
        }
        if rate > best_rate:
            best_category = category
            best_rate = rate
    dominant_category, dominant_count = missing_counter.most_common(1)[0] if missing_counter else ("none", 0)
    return {
        "ev_field_missing_by_event_category": missing_by_category,
        "dominant_missing_producer": {
            "event_category": dominant_category,
            "missing_uncertain_ev_fields": int(dominant_count),
            "share": round(dominant_count / total_uncertain, 4) if total_uncertain else 0.0,
        },
        "producer_missing_share": {
            category: round(count / total_uncertain, 4) if total_uncertain else 0.0
            for category, count in missing_counter.most_common()
        },
        "producer_level_ev_visibility": {
            "best_ev_continuity_producer": {
                "event_category": best_category,
                "ev_field_continuity_rate": best_rate,
            },
            "by_event_category": producer_level,
        },
    }


def _crosstab_dict(table: dict[str, Counter[str]], *, limit: int | None = None) -> dict[str, dict[str, int]]:
    return {context: _counter_dict(counts, limit=limit) for context, counts in sorted(table.items())}


def discover_ev_field_coverage_reports(
    *,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    date_from: str,
    date_to: str,
    run_id: str | None = None,
) -> list[tuple[Path, dict[str, Any]]]:
    dates = set(_date_strings(date_from, date_to))
    reports: list[tuple[Path, dict[str, Any]]] = []
    root = Path(report_dir)
    if not root.exists():
        return reports
    for date in sorted(dates):
        for path in sorted(root.glob(f"ev_field_coverage_*{date}*.json")):
            payload = _load_json(path)
            if payload is None or not _is_ev_field_coverage_report(payload, path):
                continue
            if run_id and _run_id(payload) != run_id:
                continue
            reports.append((path, payload))
    return reports


def _top_counter_label(counter: Counter[str]) -> str:
    return counter.most_common(1)[0][0] if counter else "none"


def _top_context(crosstabs: dict[str, dict[str, Counter[str]]], total_nulls: int) -> dict[str, Any]:
    dominant = {
        "dimension": "none",
        "context": "unknown",
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


def _trend(first: float, last: float, *, epsilon: float = 0.005) -> str:
    if last > first + epsilon:
        return "increasing"
    if last < first - epsilon:
        return "decreasing"
    return "flat"


def _visibility_maturity(runs: list[dict[str, Any]], legacy_total: int, total_nulls: int) -> str:
    if not runs:
        return "NO_EV_COVERAGE_REPORTS"
    avg_rate = sum(_as_float(run.get("avg_ev_field_continuity_rate")) for run in runs) / len(runs)
    blind_runs = sum(1 for run in runs if run.get("dominant_visibility_state") == "EV_NEVER_VISIBLE")
    legacy_rate = legacy_total / total_nulls if total_nulls else 0.0
    if avg_rate >= 0.75 and legacy_rate < 0.2:
        return "EV_OBSERVABILITY_MATURE"
    if avg_rate >= 0.25:
        return "PARTIAL_EV_OBSERVABILITY"
    if blind_runs == len(runs):
        return "EV_BLIND_ACROSS_RUNS"
    if legacy_rate >= 0.5:
        return "LOW_EV_OBSERVABILITY_LEGACY_HEAVY"
    return "LOW_EV_OBSERVABILITY"


def _run_summary(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary")
    summary = summary if isinstance(summary, dict) else {}
    freshness = _schema_freshness(payload)
    null_counts = summary.get("ev_null_reason_counts") if isinstance(summary.get("ev_null_reason_counts"), dict) else {}
    visibility_counts = (
        summary.get("candidate_ev_visibility_state_counts")
        if isinstance(summary.get("candidate_ev_visibility_state_counts"), dict)
        else {}
    )
    dominant_context = payload.get("dominant_ev_blindness_context")
    if not isinstance(dominant_context, dict):
        dominant_context = summary.get("dominant_ev_blindness_context") if isinstance(summary.get("dominant_ev_blindness_context"), dict) else {}
    return {
        "source_report": path.as_posix(),
        "date": _date_from_payload_or_path(payload, path),
        "run_id": _run_id(payload) or "missing_run_id",
        **freshness,
        "events_loaded": _as_int(payload.get("events_loaded")),
        "continuity_chains_loaded": _as_int(payload.get("continuity_chains_loaded")),
        "candidate_ev_coverage_rows": _as_int(summary.get("candidate_ev_coverage_rows")),
        "avg_ev_field_continuity_rate": _as_float(summary.get("avg_ev_field_continuity_rate")),
        "avg_ev_visibility_duration_ms": _as_float(summary.get("avg_ev_visibility_duration_ms")),
        "dominant_visibility_state": _top_counter_label(Counter({str(k): _as_int(v) for k, v in visibility_counts.items()})),
        "ev_null_reason_counts": {str(key): _as_int(count) for key, count in null_counts.items()},
        "dominant_ev_blindness_context": {
            "dimension": str(dominant_context.get("dimension") or "none"),
            "context": str(dominant_context.get("context") or "unknown"),
            "reason": str(dominant_context.get("reason") or "no_ev_null_evidence"),
            "count": _as_int(dominant_context.get("count")),
            "share": _as_float(dominant_context.get("share")),
        },
        "ev_blindness_root_cause_confidence": str(
            payload.get("ev_blindness_root_cause_confidence")
            or summary.get("ev_blindness_root_cause_confidence")
            or "UNREPORTED"
        ),
        "does_not_claim_profitability": bool(payload.get("does_not_claim_profitability", True)),
        "does_not_authorize_runtime_decisions": bool(payload.get("does_not_authorize_runtime_decisions", True)),
        "does_not_infer_execution": bool(payload.get("does_not_infer_execution", True)),
        "does_not_claim_mfe_mae": bool(payload.get("does_not_claim_mfe_mae", True)),
    }


def _recurring_patterns(
    *,
    null_counts: Counter[str],
    lifecycle: dict[str, Counter[str]],
    block_stage: dict[str, Counter[str]],
    readiness: dict[str, Counter[str]],
    orderbook: dict[str, Counter[str]],
    runs_analyzed: int,
) -> list[dict[str, Any]]:
    patterns: list[dict[str, Any]] = []
    for reason, count in null_counts.most_common(10):
        patterns.append({
            "pattern": f"ev_null_reason:{reason}",
            "count": int(count),
            "runs_observed": min(runs_analyzed, int(count)),
            "uncertainty": "preserved" if reason == "legacy_missing_reason" else "direct_or_normalized_reason",
        })
    for label, table in (
        ("lifecycle_phase", lifecycle),
        ("candidate_block_stage", block_stage),
        ("market_readiness_state", readiness),
        ("orderbook_state_classification", orderbook),
    ):
        for context, counts in sorted(table.items()):
            if not counts:
                continue
            reason, count = counts.most_common(1)[0]
            patterns.append({
                "pattern": f"{label}:{context}",
                "dominant_reason": reason,
                "count": int(count),
                "runs_observed": min(runs_analyzed, int(count)),
                "uncertainty": "context_aggregated_from_ev_coverage_reports",
            })
    return sorted(patterns, key=lambda item: (-_as_int(item.get("count")), str(item.get("pattern"))))[:20]


def build_cross_run_ev_blindness_report(
    *,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    date: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    run_id: str | None = None,
    migration_before_fresh_reports: int | None = None,
    migration_before_stale_reports: int | None = None,
    migration_before_schema_compatible_candidates: int | None = None,
    migration_before_stale_schema_candidates: int | None = None,
    reports_regenerated: int | None = None,
) -> dict[str, Any]:
    if date:
        date_from = date_to = date
    if not date_from:
        date_from = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not date_to:
        date_to = date_from

    report_pairs = discover_ev_field_coverage_reports(
        report_dir=report_dir,
        date_from=date_from,
        date_to=date_to,
        run_id=run_id,
    )
    runs = [_run_summary(path, payload) for path, payload in report_pairs]

    null_counts: Counter[str] = Counter()
    visibility_states: Counter[str] = Counter()
    root_confidence: Counter[str] = Counter()
    lifecycle: dict[str, Counter[str]] = {}
    block_stage: dict[str, Counter[str]] = {}
    block_reason: dict[str, Counter[str]] = {}
    readiness: dict[str, Counter[str]] = {}
    orderbook: dict[str, Counter[str]] = {}
    producer_missing: dict[str, Counter[str]] = {}
    producer_visibility: dict[str, dict[str, Any]] = {}
    identity_by_producer_raw: dict[str, Counter[str]] = {}
    transition_identity_raw: dict[str, Counter[str]] = {}
    envelope_missing_raw: dict[str, Counter[str]] = {}
    risk_layer_raw: dict[str, Any] = {
        "decision_to_risk_handoff_quality": Counter(),
        "risk_to_execution_handoff_quality": Counter(),
        "risk_layer_block_visibility": Counter(),
        "risk_visibility_failure_counts": Counter(),
        "decision_to_risk_boundary_counts": Counter(),
        "pre_risk_block_cause_counts": Counter(),
        "model_state_gap_counts": Counter(),
        "probability_state_gap_counts": Counter(),
        "fair_value_state_gap_counts": Counter(),
        "ev_state_gap_counts": Counter(),
        "model_attempt_gate_counts": Counter(),
        "missing_fields_preventing_direct_identity": Counter(),
        "missing_fields_preventing_strong_identity": Counter(),
        "candidate_identity_upgrade_path_counts": Counter(),
        "hypothetical_identity_upgrade_field_impact_counts": Counter(),
        "runtime_observability_fields_needed_for_risk_layer": Counter(),
        "risk_layer_trace_readiness_values": [],
        "risk_reachability_rate_values": [],
        "risk_serialization_visibility_rate_values": [],
        "pre_risk_block_share_values": [],
        "no_decision_evidence_share_values": [],
    }
    post_emission_raw: dict[str, Any] = {
        "presence_by_producer": {},
        "fields_still_preventing_direct_identity": Counter(),
        "post_emission_data_exists_count": 0,
    }
    alias_normalization_raw: dict[str, Any] = {
        "alias_normalized_field_counts": Counter(),
        "alias_source_field_counts": Counter(),
        "canonical_identity_field_presence_after_normalization": {},
        "producer_alias_dependency_counts": {},
        "producer_canonical_presence_counts": {},
        "fields_still_missing_after_alias_normalization": Counter(),
        "post_normalization_data_exists_count": 0,
    }
    post_condition_enrichment_raw: dict[str, Any] = {
        "condition_id_presence_by_producer_after_enrichment": {},
        "fields_still_preventing_direct_identity_after_condition_enrichment": Counter(),
        "fields_still_preventing_strong_identity_after_condition_enrichment": Counter(),
        "post_condition_enrichment_data_exists_count": 0,
    }
    post_fallback_condition_coverage_raw: dict[str, Any] = {
        "condition_id_presence_by_producer": {},
        "remaining_identity_blockers": Counter(),
        "post_fallback_data_exists_count": 0,
    }
    trace_summary: dict[str, Any] = {
        "traceable_candidates": 0,
        "visibility_scores": [],
        "survival_rates": [],
    }
    trace_diagnostics: Counter[str] = Counter()
    rates: list[float] = []
    visibility_durations: list[float] = []
    fresh_rates: list[float] = []
    fresh_visibility_durations: list[float] = []
    stale_reports: list[dict[str, Any]] = []
    fresh_report_count = 0
    schema_compatible_candidate_count = 0
    stale_schema_candidate_count = 0
    trend_points: list[dict[str, Any]] = []

    for path, payload in report_pairs:
        summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
        run = _run_summary(path, payload)
        is_fresh = run["replay_schema_freshness"] == "fresh"
        candidate_count = _as_int(summary.get("candidate_ev_coverage_rows"))
        if is_fresh:
            fresh_report_count += 1
            schema_compatible_candidate_count += candidate_count
        else:
            stale_schema_candidate_count += candidate_count
            stale_reports.append({
                "source_report": path.as_posix(),
                "run_id": run["run_id"],
                "date": run["date"],
                "schema_generation_version": run["schema_generation_version"],
                "stale_report_reason": run["stale_report_reason"],
                "candidate_ev_coverage_rows": candidate_count,
            })
        _merge_counter(null_counts, summary.get("ev_null_reason_counts"))
        visibility_states[run["dominant_visibility_state"]] += 1
        root_confidence[run["ev_blindness_root_cause_confidence"]] += 1
        _merge_crosstab(lifecycle, payload.get("ev_null_by_lifecycle_phase") or summary.get("ev_null_by_lifecycle_phase"))
        _merge_crosstab(block_stage, payload.get("ev_null_by_block_stage") or summary.get("ev_null_by_block_stage"))
        _merge_crosstab(block_reason, payload.get("ev_null_by_block_reason") or summary.get("ev_null_by_block_reason"))
        _merge_crosstab(readiness, payload.get("ev_null_by_market_readiness") or summary.get("ev_null_by_market_readiness"))
        _merge_crosstab(orderbook, payload.get("ev_null_by_orderbook_state") or summary.get("ev_null_by_orderbook_state"))
        _merge_producer_missing(producer_missing, payload.get("ev_field_missing_by_event_category") or summary.get("ev_field_missing_by_event_category"))
        _merge_producer_visibility(producer_visibility, payload.get("producer_level_ev_visibility") or summary.get("producer_level_ev_visibility"))
        if is_fresh:
            _merge_trace_summary(trace_summary, payload.get("ev_candidate_lifecycle_trace_summary") or summary.get("ev_candidate_lifecycle_trace_summary"))
            _merge_identity_table(identity_by_producer_raw, payload.get("identity_confidence_by_producer") or summary.get("identity_confidence_by_producer"))
            _merge_identity_table(
                transition_identity_raw,
                payload.get("producer_transition_identity_gap_tables") or summary.get("producer_transition_identity_gap_tables"),
            )
            _merge_envelope_missing(
                envelope_missing_raw,
                payload.get("missing_envelope_fields_by_producer") or summary.get("missing_envelope_fields_by_producer"),
            )
            _merge_risk_layer_report(
                risk_layer_raw,
                payload.get("risk_layer_envelope_gap_report") or summary.get("risk_layer_envelope_gap_report"),
            )
            _merge_post_emission_verification(
                post_emission_raw,
                payload.get("candidate_trace_id_post_emission_verification")
                or summary.get("candidate_trace_id_post_emission_verification"),
            )
            _merge_alias_normalization_verification(
                alias_normalization_raw,
                payload.get("candidate_trace_alias_normalization_verification")
                or summary.get("candidate_trace_alias_normalization_verification"),
            )
            _merge_post_condition_enrichment_verification(
                post_condition_enrichment_raw,
                payload.get("post_condition_enrichment_verification")
                or summary.get("post_condition_enrichment_verification"),
            )
            _merge_post_fallback_condition_coverage_verification(
                post_fallback_condition_coverage_raw,
                payload.get("post_fallback_condition_coverage_verification")
                or summary.get("post_fallback_condition_coverage_verification"),
            )
            diagnostics = payload.get("candidate_trace_confidence_diagnostics")
            if not isinstance(diagnostics, dict):
                diagnostics = summary if isinstance(summary, dict) else {}
            for key in (
                "identity_fragmentation_detected_count",
                "propagation_gap_detected_count",
                "lifecycle_propagation_interruption_count",
                "candidate_seen_but_never_evaluable_count",
                "candidate_blocked_before_ev_count",
                "ev_attempted_but_not_visible_count",
                "ev_visibility_attempted_count",
                "ev_visibility_confirmed_count",
            ):
                trace_diagnostics[key] += _as_int(diagnostics.get(key))
            fresh_rates.append(run["avg_ev_field_continuity_rate"])
            fresh_visibility_durations.append(run["avg_ev_visibility_duration_ms"])
        rates.append(run["avg_ev_field_continuity_rate"])
        visibility_durations.append(run["avg_ev_visibility_duration_ms"])
        total_run_nulls = sum(run["ev_null_reason_counts"].values())
        trend_points.append({
            "date": run["date"],
            "run_id": run["run_id"],
            "avg_ev_field_continuity_rate": run["avg_ev_field_continuity_rate"],
            "avg_ev_visibility_duration_ms": run["avg_ev_visibility_duration_ms"],
            "total_ev_nulls": total_run_nulls,
            "legacy_missing_reason": run["ev_null_reason_counts"].get("legacy_missing_reason", 0),
            "no_probability_model_output": run["ev_null_reason_counts"].get("no_probability_model_output", 0),
            "no_market_price": run["ev_null_reason_counts"].get("no_market_price", 0),
            "dominant_ev_blindness_context": run["dominant_ev_blindness_context"],
            "ev_blindness_root_cause_confidence": run["ev_blindness_root_cause_confidence"],
        })

    total_nulls = sum(null_counts.values())
    dominant_context = _top_context(
        {
            "lifecycle_phase": lifecycle,
            "candidate_block_stage": block_stage,
            "candidate_block_reason": block_reason,
            "market_readiness_state": readiness,
            "orderbook_state_classification": orderbook,
        },
        total_nulls,
    )
    legacy_total = int(null_counts.get("legacy_missing_reason", 0))
    model_total = int(null_counts.get("no_probability_model_output", 0))
    market_total = int(null_counts.get("no_market_price", 0))
    ordered_trend = sorted(trend_points, key=lambda item: (item["date"], item["run_id"]))
    visibility_rate_trend = _trend(rates[0], rates[-1]) if len(rates) >= 2 else "insufficient_runs"
    legacy_trend = _trend(
        ordered_trend[0]["legacy_missing_reason"],
        ordered_trend[-1]["legacy_missing_reason"],
        epsilon=0.5,
    ) if len(ordered_trend) >= 2 else "insufficient_runs"
    model_trend = _trend(
        ordered_trend[0]["no_probability_model_output"],
        ordered_trend[-1]["no_probability_model_output"],
        epsilon=0.5,
    ) if len(ordered_trend) >= 2 else "insufficient_runs"

    recurring_patterns = _recurring_patterns(
        null_counts=null_counts,
        lifecycle=lifecycle,
        block_stage=block_stage,
        readiness=readiness,
        orderbook=orderbook,
        runs_analyzed=len(runs),
    )
    producer = _producer_summary(producer_missing, producer_visibility)
    trace = _trace_summary_dict(trace_summary)
    identity_by_producer = _identity_table_dict(identity_by_producer_raw)
    transition_identity = _identity_table_dict(transition_identity_raw)
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
    strongest_available_identity_by_transition = {}
    for transition, stats in transition_identity.items():
        for level in IDENTITY_CONFIDENCE_LEVELS:
            if stats.get(level):
                strongest_available_identity_by_transition[transition] = level
                break
        else:
            strongest_available_identity_by_transition[transition] = "UNKNOWN"
        if "->" in transition:
            left, right = transition.split("->", 1)
            stats["from_producer"] = left
            stats["to_producer"] = right
        stats["strongest_available_identity"] = strongest_available_identity_by_transition[transition]
    weakest_identity_transition = _dominant_identity_table_item(
        transition_identity,
        metric="strong_or_direct_rate",
        lowest=True,
    )
    dominant_identity_failure_transition = _dominant_identity_table_item(
        transition_identity,
        metric="identity_gap_count",
    )
    identity_gap_tables = {
        "freshness_filter": "fresh_reports_only",
        "identity_confidence_by_producer": identity_by_producer,
        "identity_gap_by_producer": identity_gap_by_producer,
        "proxy_dependency_by_producer": proxy_dependency_by_producer,
        "direct_identity_absence_by_producer": direct_identity_absence_by_producer,
        "producer_transition_identity_gap_tables": transition_identity,
        "strongest_available_identity_by_transition": strongest_available_identity_by_transition,
        "weakest_identity_transition": weakest_identity_transition,
        "dominant_identity_failure_transition": dominant_identity_failure_transition,
        "interpretation": "PROXY and WEAK remain uncertainty and are not counted as confirmed continuity",
    }
    envelope_summary = _envelope_summary_from_missing(envelope_missing_raw)
    risk_layer_report = _risk_layer_report_dict(risk_layer_raw)
    post_emission_verification = _post_emission_verification_dict(post_emission_raw)
    alias_normalization_verification = _alias_normalization_verification_dict(alias_normalization_raw)
    post_condition_enrichment_verification = _post_condition_enrichment_verification_dict(post_condition_enrichment_raw)
    post_fallback_condition_coverage_verification = _post_fallback_condition_coverage_verification_dict(
        post_fallback_condition_coverage_raw
    )
    break_phase_counter = Counter(trace.get("ev_trace_break_phase_counts", {}))
    dominant_trace_break_phase, dominant_trace_break_count = (
        break_phase_counter.most_common(1)[0] if break_phase_counter else ("none", 0)
    )
    before_fresh = _as_int(migration_before_fresh_reports)
    before_stale = _as_int(migration_before_stale_reports)
    before_compatible = _as_int(migration_before_schema_compatible_candidates)
    before_stale_candidates = _as_int(migration_before_stale_schema_candidates)
    regenerated = _as_int(reports_regenerated)
    migration_summary = {
        "reports_regenerated": regenerated,
        "reports_remaining_stale": len(stale_reports),
        "stale_to_fresh_candidate_count": max(0, schema_compatible_candidate_count - before_compatible),
        "schema_migration_completed": bool(regenerated and len(stale_reports) == 0),
        "post_migration_fresh_report_count": fresh_report_count,
        "post_migration_schema_compatible_candidates": schema_compatible_candidate_count,
        "before_after_schema_migration_comparison": {
            "stale_report_count_before": before_stale,
            "fresh_report_count_before": before_fresh,
            "stale_report_count_after": len(stale_reports),
            "fresh_report_count_after": fresh_report_count,
            "schema_compatible_candidate_count_before": before_compatible,
            "stale_schema_candidate_count_before": before_stale_candidates,
            "schema_compatible_candidate_count_after": schema_compatible_candidate_count,
            "stale_schema_candidate_count_after": stale_schema_candidate_count,
            "confidence_counts_after": trace.get("candidate_trace_confidence_counts", {}),
            "lifecycle_visibility_metrics_after": {
                "avg_ev_field_continuity_rate": round(sum(fresh_rates) / len(fresh_rates), 4) if fresh_rates else 0.0,
                "avg_ev_visibility_duration_ms": round(sum(fresh_visibility_durations) / len(fresh_visibility_durations), 3)
                if fresh_visibility_durations
                else 0.0,
                "avg_ev_lifecycle_visibility_score": trace["avg_ev_lifecycle_visibility_score"],
                "avg_continuity_survival_rate": trace["avg_continuity_survival_rate"],
            },
        },
    }
    return {
        "generated_at_utc": _utc_now(),
        "date_from": date_from,
        "date_to": date_to,
        "run_id_filter": run_id or "",
        "scope": "offline_research_replay_only",
        "schema_version": "cross_run_ev_blindness_v1",
        "schema_generation_version": SCHEMA_GENERATION_VERSION,
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
            "origin_classes": ["original_canonical", "normalized_alias", "missing"],
            "rule": "cross-run aggregation of fresh post-normalization EV coverage reports only; stale reports remain visible but excluded",
        },
        "post_condition_enrichment_verification_schema": {
            "version": "post_condition_enrichment_verification_v1",
            "pre_patch_baseline": {
                "pre_patch_traced_events_with_condition_id": 0,
                "pre_patch_trace_events_direct_ready": 0,
                "pre_patch_trace_events_strong_ready": 0,
            },
            "rule": "cross-run aggregation of fresh EV coverage reports with post-condition-enrichment verification only; stale reports remain visible but excluded",
        },
        "post_fallback_condition_coverage_verification_schema": {
            "version": "post_fallback_condition_coverage_verification_v1",
            "pre_fallback_baseline": {
                "pre_fallback_condition_id": 0,
                "pre_fallback_direct_ready": 0,
                "pre_fallback_strong_ready": 0,
            },
            "rule": "cross-run aggregation of schema-fresh post-fallback EV coverage reports only; stale reports remain visible but excluded",
        },
        "does_not_claim_profitability": True,
        "does_not_authorize_runtime_decisions": True,
        "does_not_infer_execution": True,
        "does_not_claim_mfe_mae": True,
        "source_inputs": {
            "ev_field_coverage_reports": [path.as_posix() for path, _payload in report_pairs],
            "counts": {"ev_field_coverage_reports": len(report_pairs)},
        },
        "runs_analyzed": runs,
        "schema_freshness": {
            "required_schema_generation_version": SCHEMA_GENERATION_VERSION,
            "fresh_reports": fresh_report_count,
            "stale_reports": len(stale_reports),
            "stale_schema_detected": bool(stale_reports),
            "schema_compatible_candidate_count": schema_compatible_candidate_count,
            "stale_schema_candidate_count": stale_schema_candidate_count,
            "stale_reports_detail": stale_reports[:100],
            "freshness_rule": "reports missing candidate_trace_confidence, ev_visibility_attempted, or propagation_gap_detected are visible but excluded from confidence and lifecycle-continuity aggregation",
        },
        "schema_migration_summary": migration_summary,
        "aggregate": {
            "runs_analyzed": len(runs),
            "total_ev_nulls": total_nulls,
            "avg_ev_field_continuity_rate": round(sum(rates) / len(rates), 4) if rates else 0.0,
            "avg_ev_visibility_duration_ms": round(sum(visibility_durations) / len(visibility_durations), 3) if visibility_durations else 0.0,
            "recurring_ev_null_reasons": _counter_dict(null_counts),
            "visibility_state_counts": _counter_dict(visibility_states),
            "root_cause_confidence_counts": _counter_dict(root_confidence),
        },
        "freshness_filtered_cross_run_metrics": {
            "fresh_reports_analyzed": fresh_report_count,
            "stale_reports_excluded_from_continuity": len(stale_reports),
            "schema_compatible_candidate_count": schema_compatible_candidate_count,
            "avg_ev_field_continuity_rate": round(sum(fresh_rates) / len(fresh_rates), 4) if fresh_rates else 0.0,
            "avg_ev_visibility_duration_ms": round(sum(fresh_visibility_durations) / len(fresh_visibility_durations), 3)
            if fresh_visibility_durations
            else 0.0,
            "avg_ev_lifecycle_visibility_score": trace["avg_ev_lifecycle_visibility_score"],
            "avg_continuity_survival_rate": trace["avg_continuity_survival_rate"],
            "freshness_aware_confidence_counts": trace.get("candidate_trace_confidence_counts", {}),
            "candidate_trace_confidence_diagnostics": _counter_dict(trace_diagnostics),
            "identity_confidence_by_producer": identity_by_producer,
            "producer_transition_identity_gap_tables": transition_identity,
            "weakest_identity_transition": weakest_identity_transition,
            "dominant_identity_failure_transition": dominant_identity_failure_transition,
            "candidate_trace_envelope": envelope_summary,
            "risk_layer_envelope_gap_report": risk_layer_report,
            "candidate_trace_id_post_emission_verification": post_emission_verification,
            "alias_normalization_coverage_verification": alias_normalization_verification,
            "post_condition_enrichment_verification": post_condition_enrichment_verification,
            "post_fallback_condition_coverage_verification": post_fallback_condition_coverage_verification,
        },
        "recurring_ev_blindness_patterns": recurring_patterns,
        "ev_visibility_maturity": _visibility_maturity(runs, legacy_total, total_nulls),
        "dominant_cross_run_ev_failure": {
            "reason": _top_counter_label(null_counts),
            "context": dominant_context,
            "preserves_uncertainty": bool(legacy_total),
        },
        "recurring_lifecycle_ev_failures": _crosstab_dict(lifecycle),
        "recurring_model_output_failures": {
            "reason": "no_probability_model_output",
            "count": model_total,
            "trend": model_trend,
        },
        "recurring_market_price_failures": {
            "reason": "no_market_price",
            "count": market_total,
            "trend": _trend(
                ordered_trend[0]["no_market_price"],
                ordered_trend[-1]["no_market_price"],
                epsilon=0.5,
            ) if len(ordered_trend) >= 2 else "insufficient_runs",
        },
        "recurring_legacy_uncertainty": {
            "reason": "legacy_missing_reason",
            "count": legacy_total,
            "share_of_ev_nulls": round(legacy_total / total_nulls, 4) if total_nulls else 0.0,
            "trend": legacy_trend,
            "interpretation": "uncertainty preserved; not converted into a fake root cause",
        },
        "producer_attribution": {
            **producer,
            "ev_producer_observability_quality": (
                "HAS_PRODUCER_ATTRIBUTION" if producer["ev_field_missing_by_event_category"] else "NO_PRODUCER_ATTRIBUTION"
            ),
        },
        "cross_run_identity_gap_tables": identity_gap_tables,
        "candidate_trace_envelope_spec": envelope_summary["candidate_trace_envelope_spec"],
        "producer_required_fields": {
            producer: [
                field
                for field, stats in fields.items()
                if isinstance(stats, dict) and _as_int(stats.get("required_count")) > 0
            ]
            for producer, fields in envelope_summary["missing_envelope_fields_by_producer"].items()
        },
        "missing_envelope_fields_by_producer": envelope_summary["missing_envelope_fields_by_producer"],
        "envelope_readiness_by_producer": envelope_summary["envelope_readiness_by_producer"],
        "envelope_readiness_score": envelope_summary["envelope_readiness_score"],
        "weakest_envelope_producer": envelope_summary["weakest_envelope_producer"],
        "runtime_observability_fields_needed": envelope_summary["runtime_observability_fields_needed"],
        "cross_run_candidate_trace_envelope": envelope_summary,
        "risk_layer_envelope_gap_report": risk_layer_report,
        "risk_log_identity_missing_count": risk_layer_report["risk_log_identity_missing_count"],
        "risk_log_market_key_missing_count": risk_layer_report["risk_log_market_key_missing_count"],
        "risk_log_lifecycle_phase_missing_count": risk_layer_report["risk_log_lifecycle_phase_missing_count"],
        "risk_log_risk_state_missing_count": risk_layer_report["risk_log_risk_state_missing_count"],
        "decision_to_risk_handoff_quality": risk_layer_report["decision_to_risk_handoff_quality"],
        "risk_to_execution_handoff_quality": risk_layer_report["risk_to_execution_handoff_quality"],
        "risk_layer_trace_readiness": risk_layer_report["risk_layer_trace_readiness"],
        "risk_layer_block_visibility": risk_layer_report["risk_layer_block_visibility"],
        "candidate_blocked_before_risk_visibility_count": risk_layer_report["candidate_blocked_before_risk_visibility_count"],
        "ev_visible_before_risk_missing_after_count": risk_layer_report["ev_visible_before_risk_missing_after_count"],
        "weakest_risk_gap_reason": risk_layer_report["weakest_risk_gap_reason"],
        "dominant_risk_visibility_failure": risk_layer_report["dominant_risk_visibility_failure"],
        "runtime_observability_fields_needed_for_risk_layer": risk_layer_report["runtime_observability_fields_needed_for_risk_layer"],
        "decision_to_risk_boundary_counts": risk_layer_report["decision_to_risk_boundary_counts"],
        "risk_reachability_rate": risk_layer_report["risk_reachability_rate"],
        "risk_serialization_visibility_rate": risk_layer_report["risk_serialization_visibility_rate"],
        "pre_risk_block_share": risk_layer_report["pre_risk_block_share"],
        "no_decision_evidence_share": risk_layer_report["no_decision_evidence_share"],
        "dominant_decision_to_risk_boundary_failure": risk_layer_report["dominant_decision_to_risk_boundary_failure"],
        "pre_risk_block_cause_counts": risk_layer_report["pre_risk_block_cause_counts"],
        "dominant_pre_risk_block_cause": risk_layer_report["dominant_pre_risk_block_cause"],
        "pre_risk_block_cause_share": risk_layer_report["pre_risk_block_cause_share"],
        "ev_related_pre_risk_block_share": risk_layer_report["ev_related_pre_risk_block_share"],
        "microstructure_related_pre_risk_block_share": risk_layer_report["microstructure_related_pre_risk_block_share"],
        "timing_related_pre_risk_block_share": risk_layer_report["timing_related_pre_risk_block_share"],
        "identity_related_pre_risk_block_share": risk_layer_report["identity_related_pre_risk_block_share"],
        "unknown_pre_risk_block_share": risk_layer_report["unknown_pre_risk_block_share"],
        "model_state_gap_counts": risk_layer_report["model_state_gap_counts"],
        "probability_state_gap_counts": risk_layer_report["probability_state_gap_counts"],
        "fair_value_state_gap_counts": risk_layer_report["fair_value_state_gap_counts"],
        "ev_state_gap_counts": risk_layer_report["ev_state_gap_counts"],
        "model_attempt_visibility_rate": risk_layer_report["model_attempt_visibility_rate"],
        "model_output_serialization_rate": risk_layer_report["model_output_serialization_rate"],
        "identity_blocked_model_link_rate": risk_layer_report["identity_blocked_model_link_rate"],
        "model_attempt_visible_count": risk_layer_report["model_attempt_visible_count"],
        "model_output_serialized_count": risk_layer_report["model_output_serialized_count"],
        "identity_blocked_model_link_count": risk_layer_report["identity_blocked_model_link_count"],
        "dominant_model_state_gap": risk_layer_report["dominant_model_state_gap"],
        "model_attempt_gate_counts": risk_layer_report["model_attempt_gate_counts"],
        "dominant_model_attempt_gate": risk_layer_report["dominant_model_attempt_gate"],
        "model_gate_microstructure_share": risk_layer_report["model_gate_microstructure_share"],
        "model_gate_timing_share": risk_layer_report["model_gate_timing_share"],
        "model_gate_identity_share": risk_layer_report["model_gate_identity_share"],
        "model_gate_unknown_share": risk_layer_report["model_gate_unknown_share"],
        "model_gate_microstructure_count": risk_layer_report["model_gate_microstructure_count"],
        "model_gate_timing_count": risk_layer_report["model_gate_timing_count"],
        "model_gate_identity_count": risk_layer_report["model_gate_identity_count"],
        "model_gate_unknown_count": risk_layer_report["model_gate_unknown_count"],
        "model_attempt_eligible_count": risk_layer_report["model_attempt_eligible_count"],
        "model_attempt_eligibility_rate": risk_layer_report["model_attempt_eligibility_rate"],
        "identity_confidence_requirements": risk_layer_report["identity_confidence_requirements"],
        "identity_upgrade_required_fields": risk_layer_report["identity_upgrade_required_fields"],
        "missing_fields_preventing_direct_identity": risk_layer_report["missing_fields_preventing_direct_identity"],
        "missing_fields_preventing_strong_identity": risk_layer_report["missing_fields_preventing_strong_identity"],
        "candidate_identity_upgrade_path_counts": risk_layer_report["candidate_identity_upgrade_path_counts"],
        "easiest_identity_upgrade_field": risk_layer_report["easiest_identity_upgrade_field"],
        "highest_impact_identity_field": risk_layer_report["highest_impact_identity_field"],
        "direct_identity_blocker_rank": risk_layer_report["direct_identity_blocker_rank"],
        "strong_identity_blocker_rank": risk_layer_report["strong_identity_blocker_rank"],
        "hypothetical_identity_upgrade_impact": risk_layer_report["hypothetical_identity_upgrade_impact"],
        "candidate_trace_id_post_emission_verification": post_emission_verification,
        "candidate_trace_alias_normalization_verification": alias_normalization_verification,
        "post_condition_enrichment_verification": post_condition_enrichment_verification,
        "post_fallback_condition_coverage_verification": post_fallback_condition_coverage_verification,
        "post_emission_data_status": post_emission_verification["post_emission_data_status"],
        "post_emission_data_exists": post_emission_verification["post_emission_data_exists"],
        "post_normalization_data_status": alias_normalization_verification["post_normalization_data_status"],
        "post_normalization_data_exists": alias_normalization_verification["post_normalization_data_exists"],
        "post_condition_enrichment_data_status": post_condition_enrichment_verification["post_condition_enrichment_data_status"],
        "post_condition_enrichment_data_exists": post_condition_enrichment_verification["post_condition_enrichment_data_exists"],
        "post_fallback_data_status": post_fallback_condition_coverage_verification["post_fallback_data_status"],
        "post_fallback_data_exists": post_fallback_condition_coverage_verification["post_fallback_data_exists"],
        "alias_normalized_field_counts": alias_normalization_verification["alias_normalized_field_counts"],
        "alias_source_field_counts": alias_normalization_verification["alias_source_field_counts"],
        "canonical_identity_field_presence_after_normalization": alias_normalization_verification["canonical_identity_field_presence_after_normalization"],
        "producer_alias_dependency_counts": alias_normalization_verification["producer_alias_dependency_counts"],
        "producer_canonical_presence_counts": alias_normalization_verification["producer_canonical_presence_counts"],
        "trace_events_with_candidate_trace_id": alias_normalization_verification["trace_events_with_candidate_trace_id"],
        "trace_events_with_condition_id": alias_normalization_verification["trace_events_with_condition_id"],
        "trace_events_with_token_id": alias_normalization_verification["trace_events_with_token_id"],
        "trace_events_with_side": alias_normalization_verification["trace_events_with_side"],
        "trace_events_direct_ready": alias_normalization_verification["trace_events_direct_ready"],
        "trace_events_strong_ready": alias_normalization_verification["trace_events_strong_ready"],
        "fields_still_missing_after_alias_normalization": alias_normalization_verification["fields_still_missing_after_alias_normalization"],
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
        "pre_fallback_condition_id": post_fallback_condition_coverage_verification["pre_fallback_condition_id"],
        "pre_fallback_direct_ready": post_fallback_condition_coverage_verification["pre_fallback_direct_ready"],
        "pre_fallback_strong_ready": post_fallback_condition_coverage_verification["pre_fallback_strong_ready"],
        "traced_events_with_condition_id": post_fallback_condition_coverage_verification["traced_events_with_condition_id"],
        "post_fallback_condition_id_presence_by_producer": post_fallback_condition_coverage_verification["condition_id_presence_by_producer"],
        "post_fallback_trace_events_direct_ready": post_fallback_condition_coverage_verification["trace_events_direct_ready"],
        "post_fallback_trace_events_strong_ready": post_fallback_condition_coverage_verification["trace_events_strong_ready"],
        "remaining_identity_blockers": post_fallback_condition_coverage_verification["remaining_identity_blockers"],
        "post_fallback_delta": post_fallback_condition_coverage_verification["post_fallback_delta"],
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
        "cross_run_ev_candidate_lifecycle_trace": {
            **trace,
            "candidate_identity_upgrade_requirements": {
                "requirements": risk_layer_report["identity_confidence_requirements"],
                "missing_fields_preventing_direct_identity": risk_layer_report["missing_fields_preventing_direct_identity"],
                "missing_fields_preventing_strong_identity": risk_layer_report["missing_fields_preventing_strong_identity"],
                "candidate_identity_upgrade_path_counts": risk_layer_report["candidate_identity_upgrade_path_counts"],
                "highest_impact_identity_field": risk_layer_report["highest_impact_identity_field"],
                "easiest_identity_upgrade_field": risk_layer_report["easiest_identity_upgrade_field"],
                "rule": "hypothetical upgrade impact only; PROXY remains non-confirming",
            },
            "candidate_trace_id_post_emission_verification": post_emission_verification,
            "alias_normalization_coverage_verification": alias_normalization_verification,
            "post_condition_enrichment_verification": post_condition_enrichment_verification,
            "post_fallback_condition_coverage_verification": post_fallback_condition_coverage_verification,
            "candidate_trace_confidence_diagnostics": _counter_dict(trace_diagnostics),
            "dominant_ev_trace_break": {
                "phase": dominant_trace_break_phase,
                "count": int(dominant_trace_break_count),
                "share": round(dominant_trace_break_count / max(1, sum(break_phase_counter.values())), 4),
            },
            "interpretation": "offline trace of where EV visibility disappears across producer handoffs; no EV values are reconstructed",
            "freshness_filter": "fresh_reports_only",
        },
        "ev_observability_trend": {
            "visibility_rate_trend": visibility_rate_trend,
            "legacy_uncertainty_trend": legacy_trend,
            "model_output_failure_trend": model_trend,
            "points": ordered_trend[:100],
        },
        "cross_tabs": {
            "ev_null_by_lifecycle_phase": _crosstab_dict(lifecycle),
            "ev_null_by_block_stage": _crosstab_dict(block_stage),
            "ev_null_by_block_reason": _crosstab_dict(block_reason),
            "ev_null_by_market_readiness": _crosstab_dict(readiness),
            "ev_null_by_orderbook_state": _crosstab_dict(orderbook),
        },
        "research_questions": {
            "recurring_ev_null_reasons": _counter_dict(null_counts, limit=8),
            "recurring_lifecycle_phases_with_ev_blindness": _crosstab_dict(lifecycle, limit=5),
            "recurring_candidate_block_stages": _crosstab_dict(block_stage, limit=5),
            "recurring_readiness_states": _crosstab_dict(readiness, limit=5),
            "recurring_orderbook_states": _crosstab_dict(orderbook, limit=5),
            "ev_field_missing_by_event_category": producer["ev_field_missing_by_event_category"],
            "dominant_missing_producer": producer["dominant_missing_producer"],
            "dominant_ev_trace_break": {
                "phase": dominant_trace_break_phase,
                "count": int(dominant_trace_break_count),
            },
            "candidate_trace_confidence_counts": trace.get("candidate_trace_confidence_counts", {}),
            "candidate_trace_confidence_diagnostics": _counter_dict(trace_diagnostics),
            "direct_vs_proxy_identity_gap": identity_gap_tables,
            "candidate_trace_envelope": envelope_summary,
            "risk_layer_envelope_gap": risk_layer_report,
            "decision_to_risk_boundary": {
                "counts": risk_layer_report["decision_to_risk_boundary_counts"],
                "risk_reachability_rate": risk_layer_report["risk_reachability_rate"],
                "risk_serialization_visibility_rate": risk_layer_report["risk_serialization_visibility_rate"],
                "dominant_failure": risk_layer_report["dominant_decision_to_risk_boundary_failure"],
                "interpretation": risk_layer_report["decision_to_risk_boundary_interpretation"],
            },
            "pre_risk_block_cause_taxonomy": {
                "counts": risk_layer_report["pre_risk_block_cause_counts"],
                "dominant_cause": risk_layer_report["dominant_pre_risk_block_cause"],
                "cause_share": risk_layer_report["pre_risk_block_cause_share"],
                "ev_related_share": risk_layer_report["ev_related_pre_risk_block_share"],
                "microstructure_related_share": risk_layer_report["microstructure_related_pre_risk_block_share"],
                "timing_related_share": risk_layer_report["timing_related_pre_risk_block_share"],
                "identity_related_share": risk_layer_report["identity_related_pre_risk_block_share"],
                "unknown_share": risk_layer_report["unknown_pre_risk_block_share"],
            },
            "model_state_attempt_vs_emission_gap": {
                "model_state_gap_counts": risk_layer_report["model_state_gap_counts"],
                "probability_state_gap_counts": risk_layer_report["probability_state_gap_counts"],
                "fair_value_state_gap_counts": risk_layer_report["fair_value_state_gap_counts"],
                "ev_state_gap_counts": risk_layer_report["ev_state_gap_counts"],
                "model_attempt_visibility_rate": risk_layer_report["model_attempt_visibility_rate"],
                "model_output_serialization_rate": risk_layer_report["model_output_serialization_rate"],
                "identity_blocked_model_link_rate": risk_layer_report["identity_blocked_model_link_rate"],
                "dominant_model_state_gap": risk_layer_report["dominant_model_state_gap"],
            },
            "model_attempt_gate_taxonomy": {
                "counts": risk_layer_report["model_attempt_gate_counts"],
                "dominant_gate": risk_layer_report["dominant_model_attempt_gate"],
                "microstructure_share": risk_layer_report["model_gate_microstructure_share"],
                "timing_share": risk_layer_report["model_gate_timing_share"],
                "identity_share": risk_layer_report["model_gate_identity_share"],
                "unknown_share": risk_layer_report["model_gate_unknown_share"],
                "eligibility_rate": risk_layer_report["model_attempt_eligibility_rate"],
            },
            "candidate_identity_upgrade_requirements": {
                "requirements": risk_layer_report["identity_confidence_requirements"],
                "missing_fields_preventing_direct_identity": risk_layer_report["missing_fields_preventing_direct_identity"],
                "missing_fields_preventing_strong_identity": risk_layer_report["missing_fields_preventing_strong_identity"],
                "candidate_identity_upgrade_path_counts": risk_layer_report["candidate_identity_upgrade_path_counts"],
                "highest_impact_identity_field": risk_layer_report["highest_impact_identity_field"],
                "easiest_identity_upgrade_field": risk_layer_report["easiest_identity_upgrade_field"],
                "rule": "hypothetical upgrade impact only; PROXY remains non-confirming",
            },
            "candidate_trace_id_post_emission_verification": post_emission_verification,
            "alias_normalization_coverage_verification": alias_normalization_verification,
            "post_fallback_condition_coverage_verification": post_fallback_condition_coverage_verification,
            "schema_freshness": {
                "fresh_reports": fresh_report_count,
                "stale_reports": len(stale_reports),
                "schema_compatible_candidate_count": schema_compatible_candidate_count,
            },
            "schema_migration_summary": migration_summary,
            "ev_visibility_trend_over_time": visibility_rate_trend,
            "legacy_uncertainty_trend": legacy_trend,
            "model_output_failure_trend": model_trend,
        },
    }


def _output_date_part(report: dict[str, Any]) -> str:
    date_from = str(report.get("date_from") or "")
    date_to = str(report.get("date_to") or date_from)
    text = date_from if date_from == date_to else f"{date_from}_to_{date_to}"
    run_id = _safe_filename_token(report.get("run_id_filter"))
    if run_id:
        text = f"{text}_run_{run_id}"
    return text


def write_cross_run_ev_blindness_report(
    report: dict[str, Any],
    *,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
) -> Path:
    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"cross_run_ev_blindness_{_output_date_part(report)}.json"
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return output_path


def print_summary(report: dict[str, Any]) -> None:
    aggregate = report.get("aggregate", {})
    print("Cross-Run EV Blindness Trend Analysis")
    print(
        "range={start}..{end} run_id_filter={run_id} reports={reports} runs={runs} maturity={maturity}".format(
            start=report.get("date_from"),
            end=report.get("date_to"),
            run_id=report.get("run_id_filter") or "",
            reports=report.get("source_inputs", {}).get("counts", {}).get("ev_field_coverage_reports", 0),
            runs=aggregate.get("runs_analyzed", 0),
            maturity=report.get("ev_visibility_maturity"),
        )
    )
    print(
        "total_ev_nulls={nulls} avg_rate={rate} dominant_failure={failure}".format(
            nulls=aggregate.get("total_ev_nulls", 0),
            rate=aggregate.get("avg_ev_field_continuity_rate", 0.0),
            failure=report.get("dominant_cross_run_ev_failure", {}).get("reason", "none"),
        )
    )
    trace = report.get("cross_run_ev_candidate_lifecycle_trace", {})
    print(f"dominant_ev_trace_break={trace.get('dominant_ev_trace_break', {})}")
    identity = report.get("cross_run_identity_gap_tables", {})
    print(f"weakest_identity_transition={identity.get('weakest_identity_transition', {})}")
    print(f"envelope_readiness_score={report.get('envelope_readiness_score', 0.0)}")
    print(f"weakest_envelope_producer={report.get('weakest_envelope_producer', {})}")
    print(f"risk_layer_trace_readiness={report.get('risk_layer_trace_readiness', 0.0)}")
    print(f"dominant_risk_visibility_failure={report.get('dominant_risk_visibility_failure', '')}")
    print(f"decision_to_risk_boundary_counts={report.get('decision_to_risk_boundary_counts', {})}")
    print(f"dominant_decision_to_risk_boundary_failure={report.get('dominant_decision_to_risk_boundary_failure', '')}")
    print(f"pre_risk_block_cause_counts={report.get('pre_risk_block_cause_counts', {})}")
    print(f"dominant_pre_risk_block_cause={report.get('dominant_pre_risk_block_cause', '')}")
    print(f"model_state_gap_counts={report.get('model_state_gap_counts', {})}")
    print(f"dominant_model_state_gap={report.get('dominant_model_state_gap', '')}")
    print(f"model_attempt_gate_counts={report.get('model_attempt_gate_counts', {})}")
    print(f"dominant_model_attempt_gate={report.get('dominant_model_attempt_gate', '')}")
    print(f"highest_impact_identity_field={report.get('highest_impact_identity_field', {})}")
    print(f"easiest_identity_upgrade_field={report.get('easiest_identity_upgrade_field', {})}")
    print(f"post_emission_data_status={report.get('post_emission_data_status', '')}")
    print(f"candidate_trace_id_present_count={report.get('candidate_trace_id_present_count', 0)}")
    print(f"post_normalization_data_status={report.get('post_normalization_data_status', '')}")
    print(f"alias_normalized_field_counts={report.get('alias_normalized_field_counts', {})}")
    print(f"post_condition_enrichment_data_status={report.get('post_condition_enrichment_data_status', '')}")
    print(f"traced_events_with_condition_id_after_enrichment={report.get('traced_events_with_condition_id_after_enrichment', 0)}")
    print(f"post_fallback_data_status={report.get('post_fallback_data_status', '')}")
    print(f"traced_events_with_condition_id={report.get('traced_events_with_condition_id', 0)}")
    print(f"post_fallback_trace_events_strong_ready={report.get('post_fallback_trace_events_strong_ready', 0)}")
    freshness = report.get("schema_freshness", {})
    print(
        "schema_freshness=fresh:{fresh} stale:{stale} compatible_candidates:{candidates}".format(
            fresh=freshness.get("fresh_reports", 0),
            stale=freshness.get("stale_reports", 0),
            candidates=freshness.get("schema_compatible_candidate_count", 0),
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aggregate EV blindness context across offline EV field coverage reports.")
    parser.add_argument("--date", default=None, help="Single date in YYYY-MM-DD format.")
    parser.add_argument("--from", dest="date_from", default=None, help="Start date in YYYY-MM-DD format.")
    parser.add_argument("--to", dest="date_to", default=None, help="End date in YYYY-MM-DD format.")
    parser.add_argument("--run-id", default=None, help="Optional exact run_id filter.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Input/output report directory.")
    parser.add_argument("--no-write", action="store_true", help="Do not write cross-run EV blindness JSON report.")
    parser.add_argument("--migration-before-fresh-reports", type=int, default=None, help="Pre-migration fresh report count for schema migration summaries.")
    parser.add_argument("--migration-before-stale-reports", type=int, default=None, help="Pre-migration stale report count for schema migration summaries.")
    parser.add_argument("--migration-before-schema-compatible-candidates", type=int, default=None, help="Pre-migration schema-compatible candidate count.")
    parser.add_argument("--migration-before-stale-schema-candidates", type=int, default=None, help="Pre-migration stale-schema candidate count.")
    parser.add_argument("--reports-regenerated", type=int, default=None, help="Number of EV coverage reports regenerated during schema migration.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.date and (args.date_from or args.date_to):
        raise SystemExit("--date cannot be combined with --from/--to")
    if (args.date_from or args.date_to) and not (args.date_from and args.date_to):
        raise SystemExit("--from and --to must be provided together")
    report = build_cross_run_ev_blindness_report(
        report_dir=args.report_dir,
        date=args.date,
        date_from=args.date_from,
        date_to=args.date_to,
        run_id=args.run_id,
        migration_before_fresh_reports=args.migration_before_fresh_reports,
        migration_before_stale_reports=args.migration_before_stale_reports,
        migration_before_schema_compatible_candidates=args.migration_before_schema_compatible_candidates,
        migration_before_stale_schema_candidates=args.migration_before_stale_schema_candidates,
        reports_regenerated=args.reports_regenerated,
    )
    print_summary(report)
    if not args.no_write:
        path = write_cross_run_ev_blindness_report(report, report_dir=args.report_dir)
        print(f"wrote_report={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
