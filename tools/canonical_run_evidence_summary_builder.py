"""Build conservative per-run evidence summaries from existing JSONL logs.

Offline-only. This module intentionally imports only the Python standard
library and does not call runtime trading modules.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = "canonical_run_evidence_summary.v1"

DEFAULT_STREAMS = (
    "decision_log",
    "execution_log",
    "trade_journal",
    "market_snapshots",
    "risk_log",
    "path_truth",
    "system_health",
    "research_log",
)

CANONICAL_TIME_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "market_window_start_utc": (
        "epoch_start_utc",
        "market_epoch_start_utc",
        "market_epoch_start",
        "epoch_start_ts",
        "epoch_start",
        "market_start_time",
    ),
    "market_window_end_utc": (
        "epoch_end_utc",
        "market_epoch_end_utc",
        "market_epoch_end",
        "epoch_end_ts",
        "market_end_time",
        "market_close_timestamp",
    ),
    "chainlink_reference_ts_utc": (
        "price_to_beat_timestamp_utc",
        "ptb_timestamp_utc",
        "oracle_timestamp_utc",
        "chainlink_ts_utc",
    ),
    "source_orderbook_ts_utc": (
        "orderbook_ts_utc",
        "last_orderbook_refresh_at",
        "last_successful_yes_no_book_at",
        "candidate_seen_ts",
        "quote_capture_ts",
    ),
    "local_receive_ts_utc": ("timestamp_utc", "ts", "received_at_utc"),
    "decision_ts_utc": (
        "decision_cycle_started_at",
        "decision_timestamp",
        "decision_complete_ts",
        "timestamp_utc",
    ),
    "order_submit_ts_utc": (
        "submitted_at_utc",
        "order_submit_timestamp_utc",
        "order_submit_ts",
        "timestamp_utc",
    ),
    "order_ack_ts_utc": (
        "order_ack_timestamp_utc",
        "receipt_timestamp_utc",
        "order_ack_ts",
    ),
    "fill_ts_utc": ("fill_timestamp_utc", "fill_ts", "timestamp_utc"),
    "close_ts_utc": ("exit_timestamp", "close_timestamp_utc", "timestamp_utc"),
    "settlement_ts_utc": (
        "resolution_timestamp_utc",
        "settled_at_utc",
        "settlement_timestamp_utc",
    ),
    "data_age_ms": (
        "quote_age_ms",
        "orderbook_age_ms",
        "last_orderbook_age_ms",
        "clob_book_freshness_ms",
        "market_feed_age_ms",
    ),
    "decision_latency_ms": (
        "candidate_queue_age_ms",
        "decision_cycle_duration_ms",
    ),
    "submit_latency_ms": ("order_submit_latency_ms",),
    "fill_latency_ms": ("paper_fill_latency_ms",),
    "clock_drift_status": ("clock_status",),
    "seconds_since_open": ("window_delta", "seconds_elapsed"),
    "seconds_to_expiry": (
        "seconds_remaining",
        "time_remaining_seconds",
        "countdown",
        "seconds_until_close",
    ),
}

NO_TRADE_REASON_KEYS = (
    "skip_reason",
    "normalized_skip_reason",
    "raw_skip_reason",
    "model_not_run_reason",
    "risk_plan_zero_reason",
    "risk_block_reason",
    "skip_reason_primary",
    "candidate_block_reason",
    "reason",
)

# Report-only blocker lineage constants. Provenance:
# BOOK_WARMING_ROOT_CAUSE_AND_MARKET_LIFECYCLE_AUDIT_001 found that raw
# runtime blockers must remain visible before classifier-derived labels.
RAW_RUNTIME_BLOCKER_KEYS = (
    "skip_reason",
    "normalized_skip_reason",
    "raw_skip_reason",
    "model_not_run_reason",
)
CLASSIFIED_BLOCKER_KEYS = (
    "skip_reason_primary",
    "timing_block_reason",
    "skip_reason_category",
)
RISK_SAFETY_BLOCKER_PRIORITY_KEYS = (
    "raw_skip_reason",
    "skip_reason",
    "normalized_skip_reason",
    "model_not_run_reason",
)
RUNTIME_SAFETY_HINTS = ("risk", "drawdown", "lockdown", "safety")
RUNTIME_SAFETY_GATE_BLOCK_GROUP = "RUNTIME_SAFETY_GATE"
CLASSIFIER_TIMING_CATEGORY = "timing"
BLOCKER_SOURCE_PRIORITY = "raw_runtime_first"
CONFLICT_WARNING_CLASSIFIER_DIFFERS = "classifier_primary_differs_from_raw_runtime_blocker"
CONFLICT_WARNING_SAFETY_GATE_TIMING = "runtime_safety_gate_with_classifier_timing_blocker"
EVIDENCE_BLOCKER_CONFLICT = "RAW_CLASSIFIED_CONFLICT"
EVIDENCE_BLOCKER_ALIGNED = "RAW_RUNTIME_ALIGNED"
EVIDENCE_BLOCKER_MISSING = "NO_RUNTIME_BLOCKER_OBSERVED"
MAX_REASON_COUNT_ITEMS = 10
MAX_BLOCKER_CONFLICT_EXAMPLES = 5

# Report-only paper open reconciliation constants. Provenance:
# CANONICAL_PAPER_OPEN_COUNT_RECONCILIATION_001 found that CLOB-valid
# paper_fill rows can include both ENTRY and EXIT fills, so they must not be
# treated as actual opened-position truth.
PAPER_FILL_EVENT = "paper_fill"
POSITION_OPENED_EVENT = "position_opened_v1"
POSITION_CLOSED_EVENT = "position_closed_v1"
ENTRY_INTENT = "ENTRY"
EXIT_INTENT = "EXIT"
OPEN_RECONCILIATION_MATCH = "MATCH"
OPEN_RECONCILIATION_MISMATCH = "MISMATCH"
OPEN_COUNT_WARNING_CLOB_DIFFERS_FROM_ACTUAL = (
    "clob_cleared_count_differs_from_actual_position_opened_count"
)
OPEN_COUNT_WARNING_TRADE_JOURNAL_DIFFERS_FROM_EVENT_STREAM = (
    "trade_journal_open_count_differs_from_event_stream_position_opened_count"
)
CLOSE_COUNT_WARNING_TRADE_JOURNAL_DIFFERS_FROM_EVENT_STREAM = (
    "trade_journal_close_count_differs_from_event_stream_position_closed_count"
)

IGNORED_REASON_VALUES = {
    "",
    "normal",
    "current",
    "cycle_start",
    "preloaded_current",
    "not_blocked",
    "none",
    "n/a",
}


def normalized_reason(value: Any) -> str:
    if value is None:
        return ""
    reason = str(value).strip()
    if reason.lower() in IGNORED_REASON_VALUES:
        return ""
    return reason


def reason_count_items(counter: Counter[str], *, limit: int = MAX_REASON_COUNT_ITEMS) -> list[dict[str, Any]]:
    return [{"reason": reason, "count": count} for reason, count in counter.most_common(limit)]


def first_reason(flat: Mapping[str, Any], keys: Sequence[str]) -> str:
    for key in keys:
        reason = normalized_reason(flat.get(key))
        if reason:
            return reason
    return ""


def reason_field_counts(records: Sequence[Mapping[str, Any]], key: str) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for record in records:
        if not is_decision(record):
            continue
        reason = normalized_reason(flattened_record(record).get(key))
        if reason:
            counter[reason] += 1
    return reason_count_items(counter)


def confidence_field_counts(records: Sequence[Mapping[str, Any]], key: str) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for record in records:
        if not is_decision(record):
            continue
        value = flattened_record(record).get(key)
        if value in (None, ""):
            continue
        counter[str(value)] += 1
    return [{"value": value, "count": count} for value, count in counter.most_common(MAX_REASON_COUNT_ITEMS)]


def is_risk_safety_reason(reason: str) -> bool:
    lowered = reason.lower()
    return any(hint in lowered for hint in RUNTIME_SAFETY_HINTS)


def add_warning_once(warnings: list[str], warning: str) -> None:
    if warning not in warnings:
        warnings.append(warning)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def normalize_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def nested_values(record: Mapping[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}

    def visit(prefix: str, obj: Any) -> None:
        if isinstance(obj, Mapping):
            for key, value in obj.items():
                if isinstance(key, str):
                    values.setdefault(key, value)
                    visit(f"{prefix}.{key}" if prefix else key, value)
        elif prefix:
            values.setdefault(prefix, obj)

    visit("", record)
    return values


def flattened_record(record: Mapping[str, Any]) -> dict[str, Any]:
    flat = dict(record)
    payload = record.get("payload")
    if isinstance(payload, Mapping):
        flat.update(payload)
        display = payload.get("display")
        if isinstance(display, Mapping):
            for key, value in display.items():
                flat.setdefault(key, value)
    return flat


def record_run_id(record: Mapping[str, Any]) -> Any:
    flat = flattened_record(record)
    return flat.get("run_id") or flat.get("runtime_session_id")


def record_event_type(record: Mapping[str, Any]) -> str:
    flat = flattened_record(record)
    event_type = flat.get("event_type") or flat.get("producer_event_type") or flat.get("event")
    if event_type is None:
        return ""
    return str(event_type).strip().lower()


def record_timestamp(record: Mapping[str, Any]) -> datetime | None:
    flat = flattened_record(record)
    for key in ("timestamp_utc", "decision_timestamp", "decision_complete_ts", "exit_timestamp"):
        parsed = parse_timestamp(flat.get(key))
        if parsed is not None:
            return parsed
    return None


def load_jsonl(path: Path, source_stream: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path}:{line_no}: {exc}") from exc
            if isinstance(record, dict):
                record.setdefault("_source_stream", source_stream)
                records.append(record)
    return records


def load_run_records(
    base_dir: Path | str,
    *,
    date: str,
    run_id: str,
    input_paths: Sequence[Path | str] | None = None,
) -> list[dict[str, Any]]:
    """Load and run-id filter JSONL records from canonical quant data streams."""

    paths: list[tuple[Path, str]] = []
    if input_paths:
        for raw_path in input_paths:
            path = Path(raw_path)
            paths.append((path, path.parent.name or "input"))
    else:
        root = Path(base_dir)
        for stream in DEFAULT_STREAMS:
            paths.append((root / stream / f"{date}.jsonl", stream))

    records: list[dict[str, Any]] = []
    for path, stream in paths:
        for record in load_jsonl(path, stream):
            if record_run_id(record) == run_id:
                records.append(record)

    return sorted(records, key=lambda record: record_timestamp(record) or datetime.min.replace(tzinfo=timezone.utc))


def field_presence(records: Sequence[Mapping[str, Any]], field: str, aliases: Sequence[str]) -> dict[str, Any]:
    exact_examples: list[str] = []
    exact_unknown: list[str] = []
    alias_examples: list[str] = []
    alias_unknown: list[str] = []
    for record in records:
        values = nested_values(record)
        if field in values:
            value = values[field]
            if value not in (None, "", "UNKNOWN", "unknown"):
                exact_examples.append(field)
                continue
            else:
                exact_unknown.append(field)
        
        found_alias = False
        for alias in aliases:
            if alias in values:
                alias_value = values[alias]
                if alias_value not in (None, "", "UNKNOWN", "unknown"):
                    alias_examples.append(alias)
                    found_alias = True
                    break
                else:
                    alias_unknown.append(alias)
        if found_alias:
            continue

    if exact_examples:
        return {"status": "KNOWN_PRESENT", "aliases": [], "observed_keys": sorted(set(exact_examples))}
    if exact_unknown:
        return {"status": "PRESENT_UNKNOWN", "aliases": [], "observed_keys": sorted(set(exact_unknown))}
    if alias_examples:
        return {
            "status": "ALIAS_PRESENT",
            "aliases": sorted(set(alias_examples)),
            "observed_keys": sorted(set(alias_examples)),
        }
    if alias_unknown:
        return {
            "status": "PRESENT_UNKNOWN",
            "aliases": sorted(set(alias_unknown)),
            "observed_keys": sorted(set(alias_unknown)),
        }
    return {"status": "MISSING", "aliases": list(aliases), "observed_keys": []}


def build_market_time_truth_field_map(records: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        field: field_presence(records, field, aliases)
        for field, aliases in CANONICAL_TIME_FIELD_ALIASES.items()
    }


def is_decision(record: Mapping[str, Any]) -> bool:
    return record_event_type(record) == "decision" or flattened_record(record).get("_source_stream") == "decision_log"


def is_execution(record: Mapping[str, Any]) -> bool:
    return record_event_type(record) == "execution" or flattened_record(record).get("_source_stream") == "execution_log"


def is_trade_open(record: Mapping[str, Any]) -> bool:
    return record_event_type(record) == "trade_open"


def is_trade_close(record: Mapping[str, Any]) -> bool:
    return record_event_type(record) == "trade_close"


def is_position_opened_event(record: Mapping[str, Any]) -> bool:
    return record_event_type(record) == POSITION_OPENED_EVENT


def is_position_closed_event(record: Mapping[str, Any]) -> bool:
    return record_event_type(record) == POSITION_CLOSED_EVENT


def truthy_ready(value: Any) -> bool:
    return isinstance(value, str) and value.strip().lower() in {
        "ready",
        "tradable",
        "active",
        "strong",
        "acceptable",
        "yes",
        "true",
    }


def market_identifier(flat: Mapping[str, Any]) -> str | None:
    for key in ("market_id", "market_key", "market_slug", "source_market_id", "condition_id"):
        value = flat.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def candidate_identifier(flat: Mapping[str, Any]) -> str | None:
    for key in ("candidate_id", "candidate_trace_id", "candidate_instance_id", "signal_id", "decision_id"):
        value = flat.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def is_tradable(flat: Mapping[str, Any]) -> bool:
    readiness_keys = (
        "market_readiness_state",
        "orderbook_state_classification",
        "executable_book_state",
        "liquidity_depth_state",
    )
    return any(truthy_ready(flat.get(key)) for key in readiness_keys)


def ev_passed(flat: Mapping[str, Any]) -> bool:
    ev = as_float(flat.get("ev_after_spread"))
    if ev is None:
        ev = as_float(flat.get("ev"))
    if ev is None:
        return False
    min_ev = as_float(flat.get("min_ev"))
    if min_ev is not None:
        return ev >= min_ev
    if flat.get("ev_gate_reached") is True and flat.get("ev_candidate_ready") is True:
        return True
    return ev > 0


def risk_approved(flat: Mapping[str, Any]) -> bool:
    if flat.get("risk_approved") is True:
        return True
    if str(flat.get("reason", "")).strip().lower() == "entry_approved":
        return True
    if str(flat.get("risk_state", "")).strip().lower() == "approved" and str(
        flat.get("intent", "")
    ).upper() == "ENTRY":
        return True
    return False


def has_order_intent(flat: Mapping[str, Any]) -> bool:
    if flat.get("intent") not in (None, "") or flat.get("order_intent") not in (None, ""):
        return True
    return str(flat.get("event", "")).strip().lower() in {"order_intent_approved", "order_intent_rejected"}


def order_sent(flat: Mapping[str, Any]) -> bool:
    event = str(flat.get("event", "")).strip().lower()
    event_type = str(flat.get("event_type", "")).strip().lower()
    return event in {"order_submit_attempt", "order_submitted", "live_order_submitted"} or event_type in {
        "order_submitted",
        "paper_order",
        "live_order_submitted",
    }


def is_fill(flat: Mapping[str, Any]) -> bool:
    event = str(flat.get("event", "")).strip().lower()
    event_type = str(flat.get("event_type", "")).strip().lower()
    return "fill" in event or event_type in {"paper_fill", "fill"}


def is_paper_fill(flat: Mapping[str, Any]) -> bool:
    event = str(flat.get("event", "")).strip().lower()
    event_type = str(flat.get("event_type", "")).strip().lower()
    return event == PAPER_FILL_EVENT or event_type == PAPER_FILL_EVENT


def paper_fill_intent(flat: Mapping[str, Any]) -> str:
    return str(flat.get("intent") or flat.get("order_intent") or "").strip().upper()


def clob_cleared(flat: Mapping[str, Any]) -> bool:
    return flat.get("clob_size_valid") is True and flat.get("clob_tick_valid") is True


def close_reason(flat: Mapping[str, Any]) -> str:
    return str(flat.get("exit_reason") or flat.get("reason") or "").strip().lower()


def pnl_value(flat: Mapping[str, Any]) -> float:
    for key in ("realized_pnl", "pnl_usdc", "pnl", "profit_loss"):
        value = as_float(flat.get(key))
        if value is not None:
            return value
    return 0.0


def build_paper_open_count_reconciliation(
    *,
    clob_cleared_candidate_count: int,
    clob_cleared_fill_count: int,
    actual_position_opened_count: int,
    actual_position_closed_count: int,
    trade_journal_opened_count: int,
    trade_journal_closed_count: int,
    event_stream_position_opened_count: int,
    event_stream_position_closed_count: int,
) -> dict[str, Any]:
    warnings: list[str] = []
    if clob_cleared_candidate_count != actual_position_opened_count:
        add_warning_once(warnings, OPEN_COUNT_WARNING_CLOB_DIFFERS_FROM_ACTUAL)
    if (
        event_stream_position_opened_count
        and trade_journal_opened_count != event_stream_position_opened_count
    ):
        add_warning_once(warnings, OPEN_COUNT_WARNING_TRADE_JOURNAL_DIFFERS_FROM_EVENT_STREAM)
    if (
        event_stream_position_closed_count
        and trade_journal_closed_count != event_stream_position_closed_count
    ):
        add_warning_once(warnings, CLOSE_COUNT_WARNING_TRADE_JOURNAL_DIFFERS_FROM_EVENT_STREAM)

    return {
        "schema_version": "paper_open_count_reconciliation_v1",
        "status": OPEN_RECONCILIATION_MISMATCH if warnings else OPEN_RECONCILIATION_MATCH,
        "clob_cleared_candidate_count": clob_cleared_candidate_count,
        "clob_cleared_fill_count": clob_cleared_fill_count,
        "actual_position_opened_count": actual_position_opened_count,
        "actual_position_closed_count": actual_position_closed_count,
        "trade_journal_opened_count": trade_journal_opened_count,
        "trade_journal_closed_count": trade_journal_closed_count,
        "event_stream_position_opened_count": event_stream_position_opened_count,
        "event_stream_position_closed_count": event_stream_position_closed_count,
        "clob_cleared_minus_actual_opened": clob_cleared_candidate_count - actual_position_opened_count,
        "warnings": warnings,
    }


def top_no_trade_reasons(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for record in records:
        if not is_decision(record):
            continue
        flat = flattened_record(record)
        for key in NO_TRADE_REASON_KEYS:
            normalized = normalized_reason(flat.get(key))
            if not normalized:
                continue
            counter[normalized] += 1
            break
    return reason_count_items(counter)


def build_raw_runtime_blocker_summary(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    risk_safety_counter: Counter[str] = Counter()
    for record in records:
        if not is_decision(record):
            continue
        flat = flattened_record(record)
        reason = first_reason(flat, RISK_SAFETY_BLOCKER_PRIORITY_KEYS)
        if reason and is_risk_safety_reason(reason):
            risk_safety_counter[reason] += 1

    return {
        "skip_reason_counts": reason_field_counts(records, "skip_reason"),
        "normalized_skip_reason_counts": reason_field_counts(records, "normalized_skip_reason"),
        "raw_skip_reason_counts": reason_field_counts(records, "raw_skip_reason"),
        "model_not_run_reason_counts": reason_field_counts(records, "model_not_run_reason"),
        "risk_safety_blocker_counts": reason_count_items(risk_safety_counter),
    }


def build_classified_blocker_summary(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "skip_reason_primary_counts": reason_field_counts(records, "skip_reason_primary"),
        "timing_block_reason_counts": reason_field_counts(records, "timing_block_reason"),
        "skip_reason_category_counts": reason_field_counts(records, "skip_reason_category"),
        "no_entry_root_cause_confidence_counts": confidence_field_counts(
            records,
            "no_entry_root_cause_confidence",
        ),
    }


def build_blocker_conflict_summary(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    conflict_count = 0
    warnings: list[str] = []
    examples: list[dict[str, Any]] = []
    decision_count = 0

    for record in records:
        if not is_decision(record):
            continue
        decision_count += 1
        flat = flattened_record(record)
        raw_blocker = first_reason(flat, RAW_RUNTIME_BLOCKER_KEYS)
        classifier_blocker = first_reason(flat, ("skip_reason_primary",))
        classifier_category = normalized_reason(flat.get("skip_reason_category"))
        timing_blocker = normalized_reason(flat.get("timing_block_reason"))

        if raw_blocker and classifier_blocker and raw_blocker != classifier_blocker:
            conflict_count += 1
            add_warning_once(warnings, CONFLICT_WARNING_CLASSIFIER_DIFFERS)
            if len(examples) < MAX_BLOCKER_CONFLICT_EXAMPLES:
                examples.append(
                    {
                        "timestamp_utc": flat.get("timestamp_utc"),
                        "ticker": flat.get("ticker") or flat.get("asset"),
                        "market_slug": flat.get("market_slug") or flat.get("slug"),
                        "raw_runtime_blocker": raw_blocker,
                        "skip_reason": flat.get("skip_reason"),
                        "normalized_skip_reason": flat.get("normalized_skip_reason"),
                        "raw_skip_reason": flat.get("raw_skip_reason"),
                        "model_not_run_reason": flat.get("model_not_run_reason"),
                        "classifier_blocker": classifier_blocker,
                        "timing_block_reason": flat.get("timing_block_reason"),
                        "skip_reason_category": flat.get("skip_reason_category"),
                        "no_entry_root_cause_confidence": flat.get("no_entry_root_cause_confidence"),
                    }
                )

        if (
            normalized_reason(flat.get("model_activation_block_group")) == RUNTIME_SAFETY_GATE_BLOCK_GROUP
            and (classifier_category == CLASSIFIER_TIMING_CATEGORY or timing_blocker)
        ):
            add_warning_once(warnings, CONFLICT_WARNING_SAFETY_GATE_TIMING)

    conflict_rate = round(conflict_count / decision_count, 3) if decision_count else 0.0
    return {
        "conflict_count": conflict_count,
        "decision_count": decision_count,
        "conflict_rate": conflict_rate,
        "warnings": warnings,
        "examples": examples,
    }


def duration_minutes(start: datetime | None, end: datetime | None) -> float | None:
    if start is None or end is None or end < start:
        return None
    return round((end - start).total_seconds() / 60.0, 3)


def rate_per_hour(count: int, duration: float | None) -> float:
    if not duration or duration <= 0:
        return 0.0
    return round(count / (duration / 60.0), 3)


def build_evidence_validity(
    records: Sequence[Mapping[str, Any]],
    field_map: Mapping[str, Mapping[str, Any]],
    *,
    decisions: int,
    opens: int,
    closes: int,
    **kwargs: Any,
) -> dict[str, Any]:
    labels: list[str] = []
    timing_missing = any(
        field_map[field]["status"] == "MISSING"
        for field in (
            "chainlink_reference_ts_utc",
            "order_ack_ts_utc",
            "settlement_ts_utc",
            "submit_latency_ms",
            "fill_latency_ms",
            "clock_drift_status",
        )
    )
    timing_partial = any(value["status"] == "ALIAS_PRESENT" for value in field_map.values()) or timing_missing
    settlement_missing = field_map["settlement_ts_utc"]["status"] == "MISSING"
    sizing_realism_missing = True
    cost_truth_missing = True
    
    # Analyze realism metrics
    paper_executable = kwargs.get("paper_executable_candidate_count", 0)
    paper_dust_rejected = kwargs.get("paper_dust_rejected_count", 0)
    if paper_dust_rejected > 0 or paper_executable > 0:
        sizing_realism_missing = False


    if decisions > 0:
        labels.append("VALID_FOR_BLOCKER_DIAGNOSIS")
    if opens > 0 or closes > 0:
        labels.append("VALID_FOR_ACCOUNTING_CHECK")
    if records and timing_partial:
        labels.append("PARTIAL_FOR_MARKET_REALISM")
    if not records:
        labels.append("UNKNOWN")
    if timing_missing or sizing_realism_missing or cost_truth_missing or settlement_missing:
        labels.append("INVALID_FOR_PROFIT_CLAIM")
    elif paper_executable == 0:
        # User requirement 6: If no executable paper trades exist, keep INVALID_FOR_PROFIT_CLAIM.
        labels.append("INVALID_FOR_PROFIT_CLAIM")


    return {
        "schema_version": "evidence_validity_v1",
        "labels": labels,
        "rules": {
            "timing_truth_missing_or_ambiguous": timing_missing or timing_partial,
            "sizing_realism_missing": sizing_realism_missing,
            "fee_slippage_latency_costs_missing": cost_truth_missing,
            "settlement_truth_missing": settlement_missing,
            "profit_claim_allowed": False,
        },
    }


def build_dashboard_data_availability(
    *,
    decisions: int,
    top_reasons: Sequence[Mapping[str, Any]],
    field_map: Mapping[str, Mapping[str, Any]],
    opens: int,
    closes: int,
    fills: int,
    records: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    any_time_truth = any(value["status"] != "MISSING" for value in field_map.values())
    missing_time_truth = any(value["status"] == "MISSING" for value in field_map.values())
    has_market_realism = any(
        field_map[field]["status"] != "MISSING"
        for field in ("source_orderbook_ts_utc", "data_age_ms", "seconds_to_expiry")
    )
    has_accounting = opens > 0 or closes > 0 or fills > 0

    return {
        "Profit Engine Header": "PARTIAL" if records else "UNKNOWN",
        "Trade Funnel": "AVAILABLE" if decisions and has_accounting else ("PARTIAL" if decisions else "MISSING"),
        "Gate Blocker Board": "AVAILABLE" if top_reasons else ("PARTIAL" if decisions else "MISSING"),
        "Quant Metrics Board": "PARTIAL" if decisions or has_accounting else "MISSING",
        "Market/Sizing Reality Board": "PARTIAL" if has_market_realism else "MISSING",
        "Time Truth Board": "PARTIAL" if any_time_truth and missing_time_truth else ("AVAILABLE" if any_time_truth else "MISSING"),
        "Operator Action Panel": "AVAILABLE" if records else "UNKNOWN",
    }


def build_trade_funnel_summary(
    records: Sequence[Mapping[str, Any]],
    *,
    run_id: str,
    field_map: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    flat_records = [flattened_record(record) for record in records]
    timestamps = [record_timestamp(record) for record in records]
    timestamps = [timestamp for timestamp in timestamps if timestamp is not None]
    start = min(timestamps) if timestamps else None
    end = max(timestamps) if timestamps else None
    duration = duration_minutes(start, end)
    decisions = sum(1 for record in records if is_decision(record))
    active_markets = {
        market_id for market_id in (market_identifier(flat) for flat in flat_records) if market_id is not None
    }
    tradable_markets = {
        market_identifier(flat)
        for flat in flat_records
        if market_identifier(flat) is not None and is_tradable(flat)
    }
    candidates = {
        candidate_id
        for candidate_id in (candidate_identifier(flat) for flat in flat_records)
        if candidate_id is not None
    }
    ev_pass_count = sum(1 for record in records if is_decision(record) and ev_passed(flattened_record(record)))
    risk_approved_count = sum(1 for flat in flat_records if risk_approved(flat))
    order_intents = sum(1 for flat in flat_records if has_order_intent(flat))
    orders_sent = sum(1 for flat in flat_records if order_sent(flat))
    fills = sum(1 for flat in flat_records if is_fill(flat))
    opens = sum(1 for record in records if is_trade_open(record))
    close_records = [record for record in records if is_trade_close(record)]
    closes = len(close_records)
    close_flats = [flattened_record(record) for record in close_records]
    tp_count = sum(1 for flat in close_flats if close_reason(flat) == "take_profit")
    sl_count = sum(1 for flat in close_flats if close_reason(flat) == "stop_loss")
    net_pnl = round(sum(pnl_value(flat) for flat in close_flats), 6)
    top_reasons = top_no_trade_reasons(records)
    raw_runtime_blockers = build_raw_runtime_blocker_summary(records)
    classified_blockers = build_classified_blocker_summary(records)
    blocker_conflicts = build_blocker_conflict_summary(records)
    primary_runtime_blocker = (
        raw_runtime_blockers["skip_reason_counts"][0]["reason"]
        if raw_runtime_blockers["skip_reason_counts"]
        else ""
    )
    primary_classifier_blocker = (
        classified_blockers["skip_reason_primary_counts"][0]["reason"]
        if classified_blockers["skip_reason_primary_counts"]
        else ""
    )
    raw_vs_classified_conflict = bool(blocker_conflicts["conflict_count"])
    evidence_blocker_truth_status = (
        EVIDENCE_BLOCKER_CONFLICT
        if raw_vs_classified_conflict
        else EVIDENCE_BLOCKER_ALIGNED
        if primary_runtime_blocker
        else EVIDENCE_BLOCKER_MISSING
    )
    paper_dust_rejected_count = sum(1 for flat in flat_records if flat.get("event") == "paper_order_rejected" and flat.get("paper_reject_reason") == "dust_unexecutable_min_order")
    min_order_rejected_count = sum(1 for flat in flat_records if flat.get("event") == "paper_order_rejected")
    clob_cleared_candidate_count = sum(
        1
        for record in records
        if (is_decision(record) or is_execution(record)) and clob_cleared(flattened_record(record))
    )
    paper_executable_candidate_count = clob_cleared_candidate_count
    clob_cleared_fill_count = sum(
        1
        for record in records
        if is_execution(record)
        and is_paper_fill(flattened_record(record))
        and clob_cleared(flattened_record(record))
    )
    paper_entry_fill_count = sum(
        1
        for record in records
        if is_execution(record)
        and is_paper_fill(flattened_record(record))
        and clob_cleared(flattened_record(record))
        and paper_fill_intent(flattened_record(record)) == ENTRY_INTENT
    )
    paper_exit_fill_count = sum(
        1
        for record in records
        if is_execution(record)
        and is_paper_fill(flattened_record(record))
        and clob_cleared(flattened_record(record))
        and paper_fill_intent(flattened_record(record)) == EXIT_INTENT
    )
    paper_opened_after_clob_constraints_count = clob_cleared_fill_count
    trade_journal_opened_count = opens
    trade_journal_closed_count = closes
    event_stream_position_opened_count = sum(1 for record in records if is_position_opened_event(record))
    event_stream_position_closed_count = sum(1 for record in records if is_position_closed_event(record))
    actual_position_opened_count = event_stream_position_opened_count or trade_journal_opened_count
    actual_position_closed_count = event_stream_position_closed_count or trade_journal_closed_count
    paper_open_count_reconciliation = build_paper_open_count_reconciliation(
        clob_cleared_candidate_count=clob_cleared_candidate_count,
        clob_cleared_fill_count=clob_cleared_fill_count,
        actual_position_opened_count=actual_position_opened_count,
        actual_position_closed_count=actual_position_closed_count,
        trade_journal_opened_count=trade_journal_opened_count,
        trade_journal_closed_count=trade_journal_closed_count,
        event_stream_position_opened_count=event_stream_position_opened_count,
        event_stream_position_closed_count=event_stream_position_closed_count,
    )
    
    validity = build_evidence_validity(
        records,
        field_map,
        decisions=decisions,
        opens=opens,
        closes=closes,
        paper_executable_candidate_count=paper_executable_candidate_count,
        paper_dust_rejected_count=paper_dust_rejected_count,
    )

    capital_basis = next((flat.get("capital_basis") for flat in flat_records if flat.get("capital_basis") is not None), "UNKNOWN")
    paper_research_bankroll_usd = next((flat.get("paper_research_bankroll_usd") for flat in flat_records if flat.get("paper_research_bankroll_usd") is not None), None)
    live_reference_bankroll_usd = next((flat.get("live_reference_bankroll_usd") for flat in flat_records if flat.get("live_reference_bankroll_usd") is not None), None)
    valid_for_live_reference_bankroll_claim = next((flat.get("valid_for_live_reference_bankroll_claim") for flat in flat_records if "valid_for_live_reference_bankroll_claim" in flat), None)
    deprecated_valid_for_live_20_bankroll_claim = next((flat.get("deprecated_valid_for_live_20_bankroll_claim") for flat in flat_records if "deprecated_valid_for_live_20_bankroll_claim" in flat), None)
    
    if valid_for_live_reference_bankroll_claim is None:
        # Fallback to older format if present in legacy logs
        valid_for_live_reference_bankroll_claim = next((flat.get("valid_for_live_20_bankroll_claim") for flat in flat_records if "valid_for_live_20_bankroll_claim" in flat), None)
        
    valid_for_strategy_edge_research = next((flat.get("valid_for_strategy_edge_research") for flat in flat_records if flat.get("valid_for_strategy_edge_research") is not None), None)
    pnl_denominator_usd = paper_research_bankroll_usd if capital_basis == "PAPER_RESEARCH_BANKROLL" else live_reference_bankroll_usd

    out_dict = {
        "schema_version": "trade_funnel_summary_v1",
        "run_id": run_id,
        "mode": next((str(flat.get("mode")) for flat in flat_records if flat.get("mode")), "unknown"),
        "start_time_utc": normalize_timestamp(start),
        "end_time_utc": normalize_timestamp(end),
        "duration_minutes": duration,
        "decisions": decisions,
        "active_markets_seen": len(active_markets),
        "tradable_markets": len({item for item in tradable_markets if item is not None}),
        "candidates": len(candidates),
        "ev_pass_count": ev_pass_count,
        "risk_approved_count": risk_approved_count,
        "order_intents": order_intents,
        "orders_sent": orders_sent,
        "fills": fills,
        "opens": opens,
        "closes": closes,
        "tp_count": tp_count,
        "sl_count": sl_count,
        "net_pnl": net_pnl,
        "entry_rate_per_hour": rate_per_hour(opens, duration),
        "close_rate_per_hour": rate_per_hour(closes, duration),
        "paper_dust_rejected_count": paper_dust_rejected_count,
        "min_order_rejected_count": min_order_rejected_count,
        "paper_executable_candidate_count": paper_executable_candidate_count,
        "paper_opened_after_clob_constraints_count": paper_opened_after_clob_constraints_count,
        "clob_cleared_candidate_count": clob_cleared_candidate_count,
        "clob_cleared_fill_count": clob_cleared_fill_count,
        "paper_entry_fill_count": paper_entry_fill_count,
        "paper_exit_fill_count": paper_exit_fill_count,
        "actual_position_opened_count": actual_position_opened_count,
        "actual_position_closed_count": actual_position_closed_count,
        "trade_journal_opened_count": trade_journal_opened_count,
        "trade_journal_closed_count": trade_journal_closed_count,
        "event_stream_position_opened_count": event_stream_position_opened_count,
        "event_stream_position_closed_count": event_stream_position_closed_count,
        "paper_open_count_reconciliation": paper_open_count_reconciliation,
        "top_no_trade_reasons": top_reasons,
        "primary_runtime_blocker": primary_runtime_blocker,
        "primary_classifier_blocker": primary_classifier_blocker,
        "blocker_source_priority": BLOCKER_SOURCE_PRIORITY,
        "raw_vs_classified_blocker_conflict": raw_vs_classified_conflict,
        "raw_vs_classified_conflict_count": blocker_conflicts["conflict_count"],
        "raw_vs_classified_conflict_rate": blocker_conflicts["conflict_rate"],
        "evidence_blocker_truth_status": evidence_blocker_truth_status,
        "raw_runtime_blocker_summary": raw_runtime_blockers,
        "classified_blocker_summary": classified_blockers,
        "blocker_conflict_summary": blocker_conflicts,
        "evidence_validity": validity["labels"],
        "capital_basis": capital_basis,
        "paper_research_bankroll_usd": paper_research_bankroll_usd,
        "live_reference_bankroll_usd": live_reference_bankroll_usd,
        "valid_for_live_reference_bankroll_claim": valid_for_live_reference_bankroll_claim,
        "deprecated_valid_for_live_20_bankroll_claim": deprecated_valid_for_live_20_bankroll_claim,
        "valid_for_strategy_edge_research": valid_for_strategy_edge_research,
        "pnl_denominator_usd": pnl_denominator_usd,
    }

    if live_reference_bankroll_usd is not None and live_reference_bankroll_usd != 20.0 and deprecated_valid_for_live_20_bankroll_claim is not None:
        out_dict["capital_reference_warning"] = f"live_reference_bankroll_usd is {live_reference_bankroll_usd}, but deprecated live_20_bankroll claim field exists."

    return out_dict


def build_canonical_run_evidence_summary(
    records: Sequence[Mapping[str, Any]],
    *,
    run_id: str,
) -> dict[str, Any]:
    field_map = build_market_time_truth_field_map(records)
    trade_funnel = build_trade_funnel_summary(records, run_id=run_id, field_map=field_map)
    evidence_validity = build_evidence_validity(
        records,
        field_map,
        decisions=trade_funnel["decisions"],
        opens=trade_funnel["opens"],
        closes=trade_funnel["closes"],
    )
    dashboard = build_dashboard_data_availability(
        decisions=trade_funnel["decisions"],
        top_reasons=trade_funnel["top_no_trade_reasons"],
        field_map=field_map,
        opens=trade_funnel["opens"],
        closes=trade_funnel["closes"],
        fills=trade_funnel["fills"],
        records=records,
    )
    trade_funnel["evidence_validity"] = evidence_validity["labels"]

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": utc_now_iso(),
        "run_id": run_id,
        "record_count": len(records),
        "source_streams": sorted(
            {
                str(flattened_record(record).get("_source_stream"))
                for record in records
                if flattened_record(record).get("_source_stream")
            }
        ),
        "trade_funnel_summary_v1": trade_funnel,
        "market_time_truth_field_map_v1": field_map,
        "dashboard_data_availability_v1": dashboard,
        "evidence_validity_v1": evidence_validity,
    }


def write_summary(summary: Mapping[str, Any], output_dir: Path | str, *, pretty: bool = False) -> Path:
    run_id = str(summary.get("run_id") or summary.get("trade_funnel_summary_v1", {}).get("run_id") or "unknown")
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    output_path = directory / f"{run_id}_canonical_evidence_summary.json"
    indent = 2 if pretty else None
    output_path.write_text(json.dumps(summary, indent=indent, sort_keys=pretty) + "\n", encoding="utf-8")
    return output_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True, help="UTC date for canonical stream files, e.g. 2026-06-30")
    parser.add_argument("--run-id", required=True, help="Run id to filter")
    parser.add_argument("--base-dir", default="runtime/quant_data", help="Quant data root")
    parser.add_argument(
        "--input",
        action="append",
        dest="input_paths",
        default=None,
        help="Explicit JSONL input path. May be repeated. Overrides stream discovery.",
    )
    parser.add_argument("--output-dir", default="docs/reports/run_evidence", help="Summary output directory")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print output JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    records = load_run_records(
        Path(args.base_dir),
        date=args.date,
        run_id=args.run_id,
        input_paths=[Path(item) for item in args.input_paths] if args.input_paths else None,
    )
    summary = build_canonical_run_evidence_summary(records, run_id=args.run_id)
    output_path = write_summary(summary, Path(args.output_dir), pretty=args.pretty)
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
