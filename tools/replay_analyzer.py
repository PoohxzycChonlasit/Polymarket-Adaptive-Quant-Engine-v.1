from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date as date_type
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_QUANT_DATA_DIR = Path("runtime/quant_data")
DEFAULT_REPORT_DIR = Path("runtime/reports")
REPLAY_CATEGORIES = (
    "trade_journal",
    "decision_log",
    "execution_log",
    "risk_log",
    "market_snapshots",
    "system_health",
)

PHASE2_COVERAGE_REQUIREMENTS: tuple[dict[str, Any], ...] = (
    {
        "key": "lifecycle_phase_evidence",
        "direct": (
            "lifecycle_phase",
            "market_lifecycle_phase",
            "inventory_lifecycle_phase",
            "lifecycle_phase_transition_reason",
            "lifecycle_phase_entered_at",
            "lifecycle_phase_exited_at",
        ),
        "proxy": ("seconds_remaining", "seconds_since_open", "seconds_until_close"),
    },
    {
        "key": "first_tradable_first_evaluable_timing",
        "direct": (
            "first_tradable_second",
            "first_tradable_seconds_remaining",
            "first_tradable_at_utc",
            "first_tradable_at",
            "first_evaluable_at",
            "first_evaluable_seconds_remaining",
        ),
        "proxy": ("first_seen_seconds_remaining", "seconds_remaining"),
    },
    {
        "key": "token_orderbook_readiness",
        "direct": (
            "token_ready_at",
            "orderbook_ready_at",
            "token_id",
            "yes_token_id",
            "no_token_id",
            "condition_id",
            "orderbook_readiness_reason",
            "orderbook_unavailable_reason",
            "readiness_transition_reason",
            "market_readiness_state",
            "orderbook_state_classification",
        ),
        "proxy": ("orderbook_age_ms", "orderbook_age", "clob_error_category"),
    },
    {
        "key": "spread_normalization",
        "direct": ("spread_ready_at", "spread_normalized", "spread_gap_to_limit", "spread_limit", "max_spread", "max_allowed_spread"),
        "proxy": ("spread", "orderbook_spread", "ob_spread"),
    },
    {
        "key": "liquidity_readiness",
        "direct": ("liquidity_ready_at", "liquidity_state", "liquidity_ready", "depth_ready", "market_readiness_state"),
        "proxy": ("liquidity", "empty_book_recovery_attempted", "empty_book_recovery_success"),
    },
    {
        "key": "fair_value_ev_decay",
        "direct": ("fair_value", "true_probability", "ev_after_spread", "expected_value", "model_ev", "ev_candidate_ready", "model_output_ready"),
        "proxy": ("ev", "edge", "confidence", "bullish_probability", "bearish_probability"),
    },
    {
        "key": "side_specific_yes_no_price_path",
        "direct": (
            "yes_bid",
            "yes_ask",
            "no_bid",
            "no_ask",
            "yes_best_bid",
            "yes_best_ask",
            "no_best_bid",
            "no_best_ask",
            "yes_price",
            "no_price",
        ),
        "proxy": ("best_bid", "best_ask", "bid", "ask", "price", "entry_price"),
    },
    {
        "key": "candidate_identity_linkage",
        "direct": ("candidate_id", "signal_id", "opportunity_id", "replay_candidate_id", "candidate_survival_ms", "candidate_expiry_reason"),
        "proxy": ("position_id", "market_id", "condition_id"),
    },
    {
        "key": "starter_reload_unload_replay_support",
        "direct": (
            "starter_candidate",
            "reload_candidate",
            "unload_candidate",
            "final_derisk_candidate",
            "inventory_action",
            "lifecycle_action",
            "replay_action",
            "reload_id",
            "unload_id",
        ),
        "proxy": ("event", "side", "order_id", "position_id"),
    },
    {
        "key": "mfe_mae_support",
        "direct": (
            "mfe",
            "mae",
            "max_favorable_excursion",
            "max_adverse_excursion",
            "mfe_candidate_price",
            "mae_candidate_price",
            "candidate_peak_favorable",
            "candidate_peak_adverse",
        ),
        "proxy": (),
    },
    {
        "key": "exposure_final_derisk_pressure",
        "direct": (
            "exposure_before",
            "exposure_after",
            "risk_budget_used",
            "remaining_risk_budget",
            "open_exposure",
            "current_exposure",
            "target_exposure",
            "market_risk_used",
            "final_derisk_pressure",
            "derisk_action",
        ),
        "proxy": ("seconds_remaining", "cutoff_block_seconds_remaining", "late_entry_hard_block", "pnl"),
    },
)


@dataclass
class ReplayTrade:
    timestamp_utc: str
    position_id: str
    market_id: str
    ticker: str
    outcome: str
    side: str
    pnl: float
    holding_seconds: float | None = None


@dataclass
class RunIdSummary:
    run_id: str
    event_count: int = 0
    first_timestamp_utc: str = ""
    last_timestamp_utc: str = ""
    event_categories: list[str] = field(default_factory=list)
    modes: list[str] = field(default_factory=list)
    missing_run_id: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReplayReport:
    date_from: str | None = None
    date_to: str | None = None
    run_id: str = ""
    time_filter: dict[str, Any] = field(default_factory=dict)
    base_dir: str = ""
    events_loaded: int = 0
    bad_json_lines: int = 0
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    gross_pnl: float = 0.0
    average_pnl: float = 0.0
    max_win: float = 0.0
    max_loss: float = 0.0
    average_holding_time_seconds: float = 0.0
    skipped_decisions: int = 0
    top_skip_reasons: list[tuple[str, int]] = field(default_factory=list)
    approved_decisions: int = 0
    rejected_decisions: int = 0
    approved_vs_rejected_ratio: float = 0.0
    risk_reject_count: int = 0
    execution_failure_count: int = 0
    average_spread_at_entry: float = 0.0
    average_confidence_at_entry: float = 0.0
    average_seconds_remaining: float = 0.0
    min_seconds_remaining: float = 0.0
    average_seconds_since_open: float = 0.0
    average_seconds_until_close: float = 0.0
    first_seen_seconds_remaining: float = 0.0
    first_evaluable_seconds_remaining: float = 0.0
    active_window_alignment_reasons: list[tuple[str, int]] = field(default_factory=list)
    average_orderbook_age_ms: float = 0.0
    max_orderbook_age_ms: float = 0.0
    average_oracle_age_ms: float = 0.0
    max_oracle_age_ms: float = 0.0
    average_scan_cycle_duration_ms: float = 0.0
    max_scan_cycle_duration_ms: float = 0.0
    average_decision_latency_ms: float = 0.0
    max_decision_latency_ms: float = 0.0
    cutoff_block_count: int = 0
    average_cutoff_block_seconds_remaining: float = 0.0
    adaptive_cutoff_allowed_count: int = 0
    adaptive_cutoff_denied_count: int = 0
    late_entry_hard_block_count: int = 0
    adaptive_cutoff_reasons: list[tuple[str, int]] = field(default_factory=list)
    adaptive_cutoff_denied_reasons: list[tuple[str, int]] = field(default_factory=list)
    micro_timing_allowed_count: int = 0
    micro_timing_denied_count: int = 0
    micro_timing_branch_entered_count: int = 0
    micro_timing_candidate_count: int = 0
    micro_timing_denied_reasons: list[tuple[str, int]] = field(default_factory=list)
    micro_timing_branch_skipped_reasons: list[tuple[str, int]] = field(default_factory=list)
    orderbook_readiness_reasons: list[tuple[str, int]] = field(default_factory=list)
    clob_error_categories: list[tuple[str, int]] = field(default_factory=list)
    clob_exception_types: list[tuple[str, int]] = field(default_factory=list)
    clob_error_classes: list[tuple[str, int]] = field(default_factory=list)
    clob_backoff_active_count: int = 0
    clob_circuit_open_count: int = 0
    max_clob_error_rate: float = 0.0
    clob_recovery_count: int = 0
    empty_book_recovery_attempted_count: int = 0
    empty_book_recovery_success_count: int = 0
    empty_book_recovery_failed_count: int = 0
    empty_book_recovery_retry_count: int = 0
    liquidity_states: list[tuple[str, int]] = field(default_factory=list)
    pnl_by_outcome: dict[str, float] = field(default_factory=dict)
    pnl_by_asset: dict[str, float] = field(default_factory=dict)
    phase2_coverage: dict[str, Any] = field(default_factory=dict)
    partial_lifecycle_replay: dict[str, Any] = field(default_factory=dict)
    lifecycle_replay_confidence: str = "INSUFFICIENT"
    replay_supported_sections: list[dict[str, Any]] = field(default_factory=list)
    replay_unsupported_sections: list[dict[str, Any]] = field(default_factory=list)
    missed_starter_candidates: list[dict[str, Any]] = field(default_factory=list)
    timing_decay_summary: dict[str, Any] = field(default_factory=dict)
    spread_liquidity_readiness_summary: dict[str, Any] = field(default_factory=dict)
    trades: list[ReplayTrade] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["trades"] = [asdict(trade) for trade in self.trades]
        data["top_skip_reasons"] = [[reason, count] for reason, count in self.top_skip_reasons]
        data["adaptive_cutoff_reasons"] = [[reason, count] for reason, count in self.adaptive_cutoff_reasons]
        data["adaptive_cutoff_denied_reasons"] = [[reason, count] for reason, count in self.adaptive_cutoff_denied_reasons]
        data["micro_timing_denied_reasons"] = [[reason, count] for reason, count in self.micro_timing_denied_reasons]
        data["micro_timing_branch_skipped_reasons"] = [[reason, count] for reason, count in self.micro_timing_branch_skipped_reasons]
        data["orderbook_readiness_reasons"] = [[reason, count] for reason, count in self.orderbook_readiness_reasons]
        data["active_window_alignment_reasons"] = [[reason, count] for reason, count in self.active_window_alignment_reasons]
        data["clob_error_categories"] = [[reason, count] for reason, count in self.clob_error_categories]
        data["clob_exception_types"] = [[reason, count] for reason, count in self.clob_exception_types]
        data["clob_error_classes"] = [[reason, count] for reason, count in self.clob_error_classes]
        data["liquidity_states"] = [[state, count] for state, count in self.liquidity_states]
        return data


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _event_in_time_window(
    event: dict[str, Any],
    *,
    since_utc: datetime | None = None,
    until_utc: datetime | None = None,
    run_id: str | None = None,
) -> bool:
    if run_id is not None and str(event.get("run_id") or "") != run_id:
        return False
    if since_utc is None and until_utc is None:
        return True
    timestamp = _parse_timestamp(event.get("timestamp_utc"))
    if timestamp is None:
        return False
    if since_utc is not None and timestamp < since_utc:
        return False
    if until_utc is not None and timestamp >= until_utc:
        return False
    return True


def _parse_date(value: str) -> date_type:
    return datetime.strptime(value, "%Y-%m-%d").date()


def iter_dates(date_from: str, date_to: str) -> Iterable[str]:
    current = _parse_date(date_from)
    end = _parse_date(date_to)
    while current <= end:
        yield current.isoformat()
        current += timedelta(days=1)


def _parse_hhmm_utc(date_text: str, value: str | None, *, field_name: str) -> datetime | None:
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip()
    try:
        hour_text, minute_text = text.split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be HH:MM in UTC") from None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"{field_name} must be HH:MM in UTC")
    date_value = _parse_date(date_text)
    return datetime(date_value.year, date_value.month, date_value.day, hour, minute, tzinfo=timezone.utc)


def build_time_filter(
    *,
    date_from: str,
    date_to: str,
    since: str | None = None,
    until: str | None = None,
    since_utc: datetime | None = None,
    until_utc: datetime | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    if (since or until) and date_from != date_to:
        raise ValueError("--since/--until only support a single --date or same-day --from/--to")
    if since_utc is None:
        since_utc = _parse_hhmm_utc(date_from, since, field_name="--since")
    if until_utc is None:
        until_utc = _parse_hhmm_utc(date_from, until, field_name="--until")
    if since_utc is not None and until_utc is not None and since_utc >= until_utc:
        raise ValueError("--since must be earlier than --until")
    return {
        "since": since,
        "until": until,
        "since_utc": since_utc,
        "until_utc": until_utc,
        "run_id": run_id,
        "run_id_applied": bool(run_id),
        "applied": since_utc is not None or until_utc is not None,
        "semantics": "half_open_since_inclusive_until_exclusive",
    }


def _safe_filename_token(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    sanitized = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in text)
    return sanitized[:80] or "run"


def _report_date_part(date_from: str | None, date_to: str | None, time_filter: dict[str, Any], run_id: str = "") -> str:
    date_part = date_from if date_from == date_to else f"{date_from}_to_{date_to}"
    if time_filter.get("applied"):
        since = str(time_filter.get("since") or "start").replace(":", "")
        until = str(time_filter.get("until") or "end").replace(":", "")
        date_part = f"{date_part}_{since}_to_{until}"
    safe_run_id = _safe_filename_token(run_id or time_filter.get("run_id"))
    if safe_run_id:
        date_part = f"{date_part}_run_{safe_run_id}"
    return str(date_part)


def _as_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool) or value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def _append_numeric(values: list[float], value: Any) -> None:
    number = _as_float(value, default=float("nan"))
    if number == number:
        values.append(number)


def _append_age_ms(values: list[float], payload: dict[str, Any], *, prefix: str) -> None:
    ms_value = _get_nested(payload, f"{prefix}_age_ms", f"display.{prefix}_age_ms")
    if ms_value is not None:
        _append_numeric(values, ms_value)
        return
    seconds_value = _get_nested(payload, f"{prefix}_age", f"{prefix}_age_seconds", f"display.{prefix}_age", f"display.{prefix}_age_seconds")
    seconds = _as_float(seconds_value, default=float("nan"))
    if seconds == seconds:
        values.append(seconds * 1000.0)


def _get_nested(payload: dict[str, Any], *paths: str) -> Any:
    for path in paths:
        current: Any = payload
        found = True
        for part in path.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                found = False
                break
        if found:
            return current
    return None


def _payload_has_any(payload: dict[str, Any], paths: tuple[str, ...]) -> bool:
    display = payload.get("display")
    sources = [payload]
    if isinstance(display, dict):
        sources.append(display)
    for source in sources:
        for path in paths:
            value = _get_nested(source, path)
            if value is not None and value != "":
                return True
    return False


def _phase2_event_payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = _payload(event)
    if payload:
        return payload
    return event


def _first_value(payload: dict[str, Any], *paths: str) -> Any:
    display = payload.get("display")
    for path in paths:
        value = _get_nested(payload, path)
        if value is not None and value != "":
            return value
        if isinstance(display, dict):
            value = _get_nested(display, path)
            if value is not None and value != "":
                return value
    return None


def build_phase2_ev_null_reason_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    fields = ("fair_value", "market_price", "true_probability", "ev_after_spread")
    field_summary: dict[str, Any] = {}
    reason_counts: Counter[str] = Counter()
    stage_counts: Counter[str] = Counter()
    ev_stage_counts: Counter[str] = Counter()

    for field_name in fields:
        value_events = 0
        null_events = 0
        null_reason_events = 0
        missing_null_reason_events = 0
        null_reason_counter: Counter[str] = Counter()
        available_field = f"{field_name}_available"
        reason_field = f"{field_name}_null_reason"
        for event in events:
            payload = _phase2_event_payload(event)
            value = _first_value(payload, field_name)
            available_raw = _first_value(payload, available_field)
            available = _as_bool(available_raw) if available_raw is not None else value is not None
            reason = str(_first_value(payload, reason_field) or "").strip()
            if available:
                value_events += 1
                continue
            null_events += 1
            if reason:
                null_reason_events += 1
                null_reason_counter[reason] += 1
                reason_counts[reason] += 1
            else:
                missing_null_reason_events += 1
        field_summary[field_name] = {
            "value_events": int(value_events),
            "null_events": int(null_events),
            "null_reason_events": int(null_reason_events),
            "missing_null_reason_events": int(missing_null_reason_events),
            "null_reason_coverage_rate": round(null_reason_events / null_events, 4) if null_events else 1.0,
            "null_reasons": [[reason, count] for reason, count in null_reason_counter.most_common()],
        }

    for event in events:
        payload = _phase2_event_payload(event)
        stage = str(_first_value(payload, "probability_model_stage") or "").strip()
        ev_stage = str(_first_value(payload, "ev_calculation_stage") or "").strip()
        if stage:
            stage_counts[stage] += 1
        if ev_stage:
            ev_stage_counts[ev_stage] += 1

    total_nulls = sum(int(item["null_events"]) for item in field_summary.values())
    total_reasons = sum(int(item["null_reason_events"]) for item in field_summary.values())
    return {
        "status": "available" if total_reasons else "coverage_gap",
        "scope": "observability_null_reason_only",
        "events_checked": len(events),
        "total_null_value_events": int(total_nulls),
        "total_null_reason_events": int(total_reasons),
        "null_reason_coverage_rate": round(total_reasons / total_nulls, 4) if total_nulls else 1.0,
        "fields": field_summary,
        "null_reasons": [[reason, count] for reason, count in reason_counts.most_common()],
        "probability_model_stages": [[stage, count] for stage, count in stage_counts.most_common()],
        "ev_calculation_stages": [[stage, count] for stage, count in ev_stage_counts.most_common()],
        "does_not_claim_ev_available": True,
    }


def build_phase2_coverage_from_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    total_events = len(events)
    categories = Counter(str(event.get("_category", "") or event.get("event_type", "") or "unknown") for event in events)
    requirements: dict[str, Any] = {}
    coverage_gaps: list[str] = []
    proxy_inferred: list[str] = []

    for requirement in PHASE2_COVERAGE_REQUIREMENTS:
        key = str(requirement["key"])
        direct_paths = tuple(requirement["direct"])
        proxy_paths = tuple(requirement["proxy"])
        direct_events = 0
        proxy_events = 0
        for event in events:
            payload = _phase2_event_payload(event)
            if _payload_has_any(payload, direct_paths):
                direct_events += 1
            elif proxy_paths and _payload_has_any(payload, proxy_paths):
                proxy_events += 1

        if direct_events:
            status = "available"
            inference = "direct_observed"
        elif proxy_events:
            status = "proxy_inferred"
            inference = "proxy_inferred"
            proxy_inferred.append(key)
        else:
            status = "coverage_gap"
            inference = "missing"
            coverage_gaps.append(key)

        requirements[key] = {
            "status": status,
            "inference": inference,
            "direct_events": int(direct_events),
            "proxy_events": int(proxy_events),
            "coverage_gap": status == "coverage_gap",
            "direct_fields_checked": list(direct_paths),
            "proxy_fields_checked": list(proxy_paths),
        }

    covered = sum(1 for item in requirements.values() if item["status"] == "available")
    inferred = sum(1 for item in requirements.values() if item["status"] == "proxy_inferred")
    if not total_events:
        overall_status = "INSUFFICIENT_PHASE2_COVERAGE"
    elif coverage_gaps:
        overall_status = "PARTIAL_PHASE2_COVERAGE"
    else:
        overall_status = "READY_FOR_PHASE2_REPLAY_RESEARCH"

    return {
        "status": overall_status,
        "scope": "offline_analyzer_only",
        "runtime_behavior_changed": False,
        "live_readiness_claim": False,
        "events_checked": int(total_events),
        "event_categories": [[name, count] for name, count in categories.most_common()],
        "requirements_checked": len(PHASE2_COVERAGE_REQUIREMENTS),
        "direct_requirements": int(covered),
        "proxy_inferred_requirements": int(inferred),
        "coverage_gap_count": len(coverage_gaps),
        "coverage_gaps": coverage_gaps,
        "proxy_inferred_items": proxy_inferred,
        "ev_null_reason_coverage": build_phase2_ev_null_reason_summary(events),
        "requirements": requirements,
    }


def _phase2_market_key(payload: dict[str, Any]) -> str:
    for path in ("market_id", "condition_id", "market", "market_slug", "ticker", "asset"):
        value = str(_first_value(payload, path) or "").strip()
        if value:
            return value
    return "UNKNOWN"


def _phase2_lifecycle_phase(payload: dict[str, Any]) -> tuple[str, str]:
    direct = str(_first_value(payload, "lifecycle_phase", "market_lifecycle_phase", "inventory_lifecycle_phase") or "").strip()
    if direct:
        return direct, "direct_observed"
    seconds = _as_float(_first_value(payload, "seconds_since_open"), default=float("nan"))
    if seconds != seconds:
        remaining = _as_float(
            _first_value(payload, "seconds_remaining", "seconds_until_close", "time_remaining_seconds"),
            default=float("nan"),
        )
        if remaining == remaining:
            seconds = max(0.0, 300.0 - remaining)
    if seconds != seconds:
        return "UNKNOWN", "coverage_gap"
    if seconds < 35:
        return "OPENING_SCAN", "proxy_inferred"
    if seconds < 240:
        return "ACTIVE_INVENTORY_TRADING", "proxy_inferred"
    if seconds < 270:
        return "PROFIT_MANAGEMENT", "proxy_inferred"
    if seconds <= 300:
        return "FINAL_DERISK", "proxy_inferred"
    return "CLOSED_OR_UNSAFE", "proxy_inferred"


def _phase2_side_price_path_status(payload: dict[str, Any]) -> str:
    if _payload_has_any(
        payload,
        (
            "yes_bid",
            "yes_ask",
            "no_bid",
            "no_ask",
            "yes_best_bid",
            "yes_best_ask",
            "no_best_bid",
            "no_best_ask",
            "yes_price",
            "no_price",
        ),
    ):
        return "available"
    if _payload_has_any(payload, ("best_bid", "best_ask", "bid", "ask", "price", "entry_price")):
        return "proxy_inferred"
    return "coverage_gap"


def _phase2_bool_status(payload: dict[str, Any], direct: tuple[str, ...], proxy: tuple[str, ...] = ()) -> str:
    if _payload_has_any(payload, direct):
        return "available"
    if proxy and _payload_has_any(payload, proxy):
        return "proxy_inferred"
    return "coverage_gap"


def _phase2_candidate_key(payload: dict[str, Any], event: dict[str, Any]) -> tuple[str, str]:
    direct = str(_first_value(payload, "candidate_id", "signal_id", "opportunity_id", "replay_candidate_id") or "").strip()
    if direct:
        return direct, "direct_observed"
    key = "|".join([
        _phase2_market_key(payload),
        str(_first_value(payload, "outcome", "side", "best_side", "best_candidate_side") or ""),
        str(event.get("timestamp_utc", "") or ""),
    ])
    return key, "proxy_inferred" if key.strip("|") else "coverage_gap"


def _phase2_spread_normalized(payload: dict[str, Any]) -> tuple[bool | None, str]:
    direct = _first_value(payload, "spread_normalized")
    if direct is not None:
        return _as_bool(direct), "direct_observed"
    gap = _first_value(payload, "spread_gap_to_limit")
    if gap is not None:
        return _as_float(gap, default=1.0) <= 0, "proxy_inferred"
    spread = _first_value(payload, "spread", "orderbook_spread", "ob_spread")
    limit = _first_value(payload, "spread_limit", "max_spread", "max_allowed_spread", "max_orderbook_spread")
    if spread is not None:
        return _as_float(spread) <= _as_float(limit, default=0.10), "proxy_inferred"
    return None, "coverage_gap"


def _phase2_missed_starter_candidate(event: dict[str, Any]) -> dict[str, Any] | None:
    payload = _phase2_event_payload(event)
    event_type = str(event.get("event_type", "") or "")
    category = str(event.get("_category", "") or "")
    if event_type != "decision" and category != "decision_log":
        return None
    skipped = _as_bool(_first_value(payload, "skipped")) or str(_first_value(payload, "decision") or "").lower() in {"skip", "skipped"}
    if not skipped:
        return None
    reason = str(_first_value(payload, "normalized_skip_reason", "skip_reason", "raw_skip_reason") or "").strip()
    seconds_remaining = _as_float(
        _first_value(payload, "seconds_remaining", "seconds_until_close", "time_remaining_seconds"),
        default=float("nan"),
    )
    cutoff = _as_float(_first_value(payload, "effective_cutoff_seconds", "entry_cutoff_seconds"), default=90.0)
    if seconds_remaining != seconds_remaining or seconds_remaining <= cutoff:
        return None
    candidate_key, candidate_inference = _phase2_candidate_key(payload, event)
    spread_ok, spread_inference = _phase2_spread_normalized(payload)
    phase, phase_inference = _phase2_lifecycle_phase(payload)
    liquidity_state = str(_first_value(payload, "liquidity_state") or "UNKNOWN").upper()
    return {
        "candidate_key": candidate_key,
        "candidate_key_inference": candidate_inference,
        "timestamp_utc": str(event.get("timestamp_utc", "") or ""),
        "market_key": _phase2_market_key(payload),
        "lifecycle_phase": phase,
        "lifecycle_phase_inference": phase_inference,
        "seconds_remaining": seconds_remaining,
        "seconds_remaining_inference": "direct_observed",
        "skip_reason": reason,
        "skip_reason_inference": "direct_observed" if reason else "coverage_gap",
        "spread_normalized_proxy": spread_ok,
        "spread_normalized_inference": spread_inference,
        "liquidity_state": liquidity_state,
        "liquidity_state_inference": "direct_observed" if liquidity_state != "UNKNOWN" else "coverage_gap",
        "ev_proxy": _as_float(_first_value(payload, "ev", "edge", "model_ev", "expected_value"), default=0.0),
        "ev_inference": "proxy_inferred",
        "fair_value_support": _phase2_bool_status(
            payload,
            ("fair_value", "true_probability", "ev_after_spread", "expected_value", "model_ev"),
            ("ev", "edge", "confidence", "bullish_probability", "bearish_probability"),
        ),
        "starter_replay_label": "missed_starter_proxy",
        "starter_replay_inference": "proxy_inferred",
    }


def build_partial_lifecycle_replay_from_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    coverage = build_phase2_coverage_from_events(events)
    requirements = coverage.get("requirements", {})
    supported_sections = [
        {
            "section": section,
            "status": data.get("status"),
            "inference": data.get("inference"),
        }
        for section, data in sorted(requirements.items())
        if data.get("status") in {"available", "proxy_inferred"}
        and section
        not in {
            "mfe_mae_support",
        }
    ]
    unsupported_sections = [
        {
            "section": section,
            "status": "coverage_gap",
            "reason": "direct evidence unavailable in current generated data",
        }
        for section, data in sorted(requirements.items())
        if data.get("status") == "coverage_gap"
    ]
    for section in ("reload_unload_truth", "final_derisk_truth", "real_inventory_execution_readiness"):
        unsupported_sections.append({
            "section": section,
            "status": "coverage_gap",
            "reason": "explicitly unsupported by partial proxy replay",
        })

    by_market: dict[str, dict[str, Any]] = {}
    seconds_values: list[float] = []
    first_evaluable_values: list[float] = []
    spread_events = 0
    spread_normalized = 0
    liquidity_counts: Counter[str] = Counter()
    readiness_counts: Counter[str] = Counter()
    missed_starters: list[dict[str, Any]] = []

    for event in events:
        payload = _phase2_event_payload(event)
        market_key = _phase2_market_key(payload)
        market = by_market.setdefault(
            market_key,
            {
                "market_key": market_key,
                "event_count": 0,
                "lifecycle_phase_counts": Counter(),
                "first_seen_seconds_remaining": None,
                "first_evaluable_seconds_remaining": None,
                "readiness": {
                    "token_orderbook": "coverage_gap",
                    "liquidity": "coverage_gap",
                    "side_specific_yes_no_price_path": "coverage_gap",
                    "spread_normalization": "coverage_gap",
                    "fair_value_ev_decay": "coverage_gap",
                    "candidate_linkage": "coverage_gap",
                },
                "inference": "proxy_inferred",
            },
        )
        market["event_count"] += 1
        phase, phase_inference = _phase2_lifecycle_phase(payload)
        market["lifecycle_phase_counts"][phase] += 1
        market["lifecycle_phase_inference"] = phase_inference if phase_inference == "direct_observed" else "proxy_inferred"

        seconds = _as_float(_first_value(payload, "seconds_remaining", "seconds_until_close"), default=float("nan"))
        if seconds == seconds:
            seconds_values.append(seconds)
            current_first = market["first_seen_seconds_remaining"]
            market["first_seen_seconds_remaining"] = max(seconds, _as_float(current_first, default=0.0)) if current_first is not None else seconds
        first_eval = _as_float(_first_value(payload, "first_evaluable_seconds_remaining"), default=float("nan"))
        if first_eval == first_eval:
            first_evaluable_values.append(first_eval)
            current_eval = market["first_evaluable_seconds_remaining"]
            market["first_evaluable_seconds_remaining"] = max(first_eval, _as_float(current_eval, default=0.0)) if current_eval is not None else first_eval

        for key, status in (
            ("token_orderbook", _phase2_bool_status(
                payload,
                (
                    "token_ready_at",
                    "orderbook_ready_at",
                    "token_id",
                    "yes_token_id",
                    "no_token_id",
                    "condition_id",
                    "orderbook_readiness_reason",
                    "orderbook_unavailable_reason",
                ),
                ("orderbook_age_ms", "orderbook_age", "clob_error_category"),
            )),
            ("liquidity", _phase2_bool_status(payload, ("liquidity_ready_at", "liquidity_state", "liquidity_ready", "depth_ready"), ("liquidity",))),
            ("side_specific_yes_no_price_path", _phase2_side_price_path_status(payload)),
            ("fair_value_ev_decay", _phase2_bool_status(
                payload,
                ("fair_value", "true_probability", "ev_after_spread", "expected_value", "model_ev"),
                ("ev", "edge", "confidence", "bullish_probability", "bearish_probability"),
            )),
            ("candidate_linkage", _phase2_bool_status(
                payload,
                ("candidate_id", "signal_id", "opportunity_id", "replay_candidate_id"),
                ("position_id", "market_id", "condition_id"),
            )),
        ):
            if status == "available" or (status == "proxy_inferred" and market["readiness"][key] == "coverage_gap"):
                market["readiness"][key] = status

        spread_status = _phase2_bool_status(
            payload,
            ("spread_ready_at", "spread_normalized", "spread_gap_to_limit", "spread_limit", "max_spread", "max_allowed_spread"),
            ("spread", "orderbook_spread", "ob_spread"),
        )
        if spread_status != "coverage_gap":
            spread_events += 1
            is_normalized, _spread_inference = _phase2_spread_normalized(payload)
            if is_normalized:
                spread_normalized += 1
            if spread_status == "available" or market["readiness"]["spread_normalization"] == "coverage_gap":
                market["readiness"]["spread_normalization"] = spread_status

        liquidity_state = str(_first_value(payload, "liquidity_state") or "").upper()
        if liquidity_state:
            liquidity_counts[liquidity_state] += 1
        readiness_reason = str(_first_value(payload, "orderbook_readiness_reason", "orderbook_unavailable_reason") or "")
        if readiness_reason:
            readiness_counts[readiness_reason] += 1

        missed = _phase2_missed_starter_candidate(event)
        if missed is not None:
            missed_starters.append(missed)

    lifecycle_rows: list[dict[str, Any]] = []
    for market in by_market.values():
        phase_counts = market.pop("lifecycle_phase_counts")
        lifecycle_rows.append({
            **market,
            "lifecycle_phase_counts": [[phase, count] for phase, count in phase_counts.most_common()],
            "unsupported_inventory_metrics": [
                {"metric": "mfe_mae", "status": "coverage_gap"},
                {"metric": "reload_unload_truth", "status": "coverage_gap"},
                {"metric": "final_derisk_truth", "status": "coverage_gap"},
            ],
        })

    direct = _as_float(coverage.get("direct_requirements"))
    proxy = _as_float(coverage.get("proxy_inferred_requirements"))
    gaps = _as_float(coverage.get("coverage_gap_count"))
    if not events:
        confidence = "INSUFFICIENT"
    elif gaps <= 1 and direct >= 4:
        confidence = "MEDIUM_PROXY"
    elif direct + proxy >= 5:
        confidence = "LOW_PROXY"
    else:
        confidence = "INSUFFICIENT"

    return {
        "status": "PARTIAL_PROXY_REPLAY" if events else "INSUFFICIENT_DATA",
        "scope": "offline_analyzer_only",
        "runtime_behavior_changed": False,
        "live_readiness_claim": False,
        "inventory_execution_readiness_claim": False,
        "lifecycle_replay_confidence": confidence,
        "replay_supported_sections": supported_sections,
        "replay_unsupported_sections": unsupported_sections,
        "partial_lifecycle_replay": lifecycle_rows[:50],
        "missed_starter_candidates": missed_starters[:50],
        "timing_decay_summary": {
            "status": "proxy_inferred",
            "events_with_seconds_remaining": len(seconds_values),
            "first_seen_seconds_remaining": max(seconds_values) if seconds_values else None,
            "first_evaluable_seconds_remaining": max(first_evaluable_values) if first_evaluable_values else None,
            "avg_seconds_remaining": round(sum(seconds_values) / len(seconds_values), 2) if seconds_values else 0.0,
            "min_seconds_remaining": min(seconds_values) if seconds_values else None,
            "max_seconds_remaining": max(seconds_values) if seconds_values else None,
        },
        "spread_liquidity_readiness_summary": {
            "status": "proxy_inferred",
            "spread_events": int(spread_events),
            "spread_normalized_events": int(spread_normalized),
            "spread_normalization_rate": round(spread_normalized / spread_events, 4) if spread_events else 0.0,
            "liquidity_states": [[state, count] for state, count in liquidity_counts.most_common()],
            "orderbook_readiness_reasons": [[reason, count] for reason, count in readiness_counts.most_common()],
        },
    }


def _track_clob_error(
    payload: dict[str, Any],
    category_counts: Counter[str],
    exception_type_counts: Counter[str],
    class_counts: Counter[str],
    report: ReplayReport,
) -> None:
    category = str(_get_nested(payload, "clob_error_category", "display.clob_error_category") or "")
    exception_type = str(_get_nested(payload, "clob_exception_type", "display.clob_exception_type") or "")
    error_class = str(_get_nested(payload, "clob_error_class", "display.clob_error_class") or "")
    if category:
        category_counts[category] += 1
    if exception_type:
        exception_type_counts[exception_type] += 1
    if error_class:
        class_counts[error_class] += 1
    if _as_bool(_get_nested(payload, "clob_backoff_active", "display.clob_backoff_active")):
        report.clob_backoff_active_count += 1
    if _as_bool(_get_nested(payload, "clob_circuit_open", "display.clob_circuit_open")):
        report.clob_circuit_open_count += 1
    report.max_clob_error_rate = max(
        report.max_clob_error_rate,
        _as_float(_get_nested(payload, "clob_error_rate", "display.clob_error_rate")),
    )
    report.clob_recovery_count = max(
        report.clob_recovery_count,
        int(_as_float(_get_nested(payload, "clob_recovery_count", "display.clob_recovery_count"))),
    )


def _track_empty_book_recovery(
    payload: dict[str, Any],
    liquidity_states: Counter[str],
    report: ReplayReport,
) -> None:
    if _as_bool(_get_nested(payload, "empty_book_recovery_attempted", "display.empty_book_recovery_attempted")):
        report.empty_book_recovery_attempted_count += 1
    if _as_bool(_get_nested(payload, "empty_book_recovery_success", "display.empty_book_recovery_success")):
        report.empty_book_recovery_success_count += 1
    if _as_bool(_get_nested(payload, "empty_book_recovery_failed", "display.empty_book_recovery_failed")):
        report.empty_book_recovery_failed_count += 1
    report.empty_book_recovery_retry_count += int(_as_float(_get_nested(
        payload,
        "empty_book_recovery_retry_count",
        "display.empty_book_recovery_retry_count",
    )))
    liquidity_state = str(_get_nested(payload, "liquidity_state", "display.liquidity_state") or "").upper()
    if liquidity_state:
        liquidity_states[liquidity_state] += 1


def _payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload")
    return payload if isinstance(payload, dict) else {}


def _asset_from_payload(payload: dict[str, Any]) -> str:
    for key in ("ticker", "asset", "market", "market_id"):
        value = str(payload.get(key, "") or "").upper()
        if "BTC" in value:
            return "BTC"
        if "ETH" in value:
            return "ETH"
    return ""


def _trade_key(payload: dict[str, Any]) -> str:
    position_id = str(payload.get("position_id", "") or "").strip()
    if position_id:
        return f"position:{position_id}"
    market_id = str(payload.get("market_id", "") or payload.get("market", "") or "").strip()
    outcome = str(payload.get("outcome", "") or payload.get("side", "") or "").strip().upper()
    ticker = _asset_from_payload(payload)
    return f"market:{market_id}:{ticker}:{outcome}"


def replay_jsonl_paths(
    *,
    base_dir: str | Path = DEFAULT_QUANT_DATA_DIR,
    date_from: str,
    date_to: str,
) -> list[Path]:
    root = Path(base_dir)
    if not root.exists():
        return []
    dates = set(iter_dates(date_from, date_to))
    paths: list[Path] = []
    for category in REPLAY_CATEGORIES:
        category_dir = root / category
        if not category_dir.exists():
            continue
        for date_str in dates:
            path = category_dir / f"{date_str}.jsonl"
            if path.is_file():
                paths.append(path)
    return sorted(paths)


def load_replay_events(
    *,
    base_dir: str | Path = DEFAULT_QUANT_DATA_DIR,
    date_from: str,
    date_to: str,
    since_utc: datetime | None = None,
    until_utc: datetime | None = None,
    run_id: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    events: list[dict[str, Any]] = []
    bad_json_lines = 0
    for path in replay_jsonl_paths(base_dir=base_dir, date_from=date_from, date_to=date_to):
        try:
            with path.open(encoding="utf-8") as handle:
                for raw_line in handle:
                    text = raw_line.strip()
                    if not text:
                        continue
                    try:
                        event = json.loads(text)
                    except json.JSONDecodeError:
                        bad_json_lines += 1
                        continue
                    if isinstance(event, dict):
                        event["_category"] = path.parent.name
                        if _event_in_time_window(event, since_utc=since_utc, until_utc=until_utc, run_id=run_id):
                            events.append(event)
                    else:
                        bad_json_lines += 1
        except OSError:
            continue
    return sorted(events, key=lambda event: str(event.get("timestamp_utc", ""))), bad_json_lines


def summarize_run_ids_from_events(events: list[dict[str, Any]]) -> list[RunIdSummary]:
    grouped: dict[str, dict[str, Any]] = {}
    for event in events:
        raw_run_id = str(event.get("run_id") or "").strip()
        missing = not raw_run_id
        run_id = raw_run_id or "missing_run_id"
        item = grouped.setdefault(
            run_id,
            {
                "event_count": 0,
                "timestamps": [],
                "categories": set(),
                "modes": set(),
                "missing_run_id": missing,
            },
        )
        item["event_count"] += 1
        timestamp = str(event.get("timestamp_utc") or "").strip()
        if timestamp:
            item["timestamps"].append(timestamp)
        category = str(event.get("_category") or event.get("event_type") or "").strip()
        if category:
            item["categories"].add(category)
        mode = str(event.get("mode") or "").strip()
        if mode:
            item["modes"].add(mode)

    summaries: list[RunIdSummary] = []
    for run_id, item in grouped.items():
        timestamps = sorted(item["timestamps"])
        summaries.append(
            RunIdSummary(
                run_id=run_id,
                event_count=int(item["event_count"]),
                first_timestamp_utc=timestamps[0] if timestamps else "",
                last_timestamp_utc=timestamps[-1] if timestamps else "",
                event_categories=sorted(item["categories"]),
                modes=sorted(item["modes"]),
                missing_run_id=bool(item["missing_run_id"]),
            )
        )
    return sorted(summaries, key=lambda item: (item.missing_run_id, item.first_timestamp_utc, item.run_id))


def discover_run_ids(
    *,
    base_dir: str | Path = DEFAULT_QUANT_DATA_DIR,
    date: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    since: str | None = None,
    until: str | None = None,
) -> list[RunIdSummary]:
    if date:
        date_from = date_to = date
    if not date_from:
        date_from = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not date_to:
        date_to = date_from
    time_filter = build_time_filter(date_from=date_from, date_to=date_to, since=since, until=until)
    events, _bad_json_lines = load_replay_events(
        base_dir=base_dir,
        date_from=date_from,
        date_to=date_to,
        since_utc=time_filter.get("since_utc"),
        until_utc=time_filter.get("until_utc"),
    )
    return summarize_run_ids_from_events(events)


def print_run_id_summary(summaries: list[RunIdSummary]) -> None:
    print("Available run IDs")
    if not summaries:
        print("(none)")
        return
    for summary in summaries:
        marker = " missing_run_id=true" if summary.missing_run_id else ""
        categories = ",".join(summary.event_categories) if summary.event_categories else "-"
        modes = ",".join(summary.modes) if summary.modes else "-"
        print(
            "run_id={run_id}{marker} event_count={count} first={first} last={last} categories={categories} mode={modes}".format(
                run_id=summary.run_id,
                marker=marker,
                count=summary.event_count,
                first=summary.first_timestamp_utc or "-",
                last=summary.last_timestamp_utc or "-",
                categories=categories,
                modes=modes,
            )
        )


def analyze_replay(
    *,
    base_dir: str | Path = DEFAULT_QUANT_DATA_DIR,
    date: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    report_dir: str | Path | None = None,
    write_reports: bool = False,
    write_csv: bool = False,
    since_utc: datetime | None = None,
    until_utc: datetime | None = None,
    since: str | None = None,
    until: str | None = None,
    run_id: str | None = None,
) -> ReplayReport:
    if date:
        date_from = date_to = date
    if not date_from:
        date_from = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not date_to:
        date_to = date_from
    time_filter = build_time_filter(
        date_from=date_from,
        date_to=date_to,
        since=since,
        until=until,
        since_utc=since_utc,
        until_utc=until_utc,
        run_id=run_id,
    )
    since_utc = time_filter.get("since_utc")
    until_utc = time_filter.get("until_utc")

    events, bad_json_lines = load_replay_events(
        base_dir=base_dir,
        date_from=date_from,
        date_to=date_to,
        since_utc=since_utc,
        until_utc=until_utc,
        run_id=run_id,
    )
    report = ReplayReport(
        date_from=date_from,
        date_to=date_to,
        run_id=str(run_id or ""),
        time_filter={
            "since": since,
            "until": until,
            "since_utc": since_utc.isoformat().replace("+00:00", "Z") if since_utc else None,
            "until_utc": until_utc.isoformat().replace("+00:00", "Z") if until_utc else None,
            "run_id": run_id,
            "run_id_applied": bool(run_id),
            "applied": bool(time_filter.get("applied")),
            "semantics": time_filter.get("semantics"),
        },
        base_dir=str(Path(base_dir)),
        events_loaded=len(events),
        bad_json_lines=bad_json_lines,
    )

    skip_reasons: Counter[str] = Counter()
    opens: dict[str, tuple[datetime, dict[str, Any]]] = {}
    spreads: list[float] = []
    confidences: list[float] = []
    holding_times: list[float] = []
    closed_pnls: list[float] = []
    pnl_by_outcome: defaultdict[str, float] = defaultdict(float)
    pnl_by_asset: defaultdict[str, float] = defaultdict(float)
    latest_market_snapshot: dict[str, dict[str, Any]] = {}
    latest_confidence_by_asset: dict[str, float] = {}
    seconds_remaining_values: list[float] = []
    seconds_since_open_values: list[float] = []
    seconds_until_close_values: list[float] = []
    first_seen_seconds_remaining_values: list[float] = []
    first_evaluable_seconds_remaining_values: list[float] = []
    orderbook_age_ms_values: list[float] = []
    oracle_age_ms_values: list[float] = []
    scan_cycle_duration_ms_values: list[float] = []
    decision_latency_ms_values: list[float] = []
    cutoff_block_seconds_remaining_values: list[float] = []
    adaptive_cutoff_reasons: Counter[str] = Counter()
    micro_timing_denied_reasons: Counter[str] = Counter()
    micro_timing_branch_skipped_reasons: Counter[str] = Counter()
    active_window_alignment_reasons: Counter[str] = Counter()
    orderbook_readiness_reasons: Counter[str] = Counter()
    clob_error_categories: Counter[str] = Counter()
    clob_exception_types: Counter[str] = Counter()
    clob_error_classes: Counter[str] = Counter()
    liquidity_states: Counter[str] = Counter()

    for event in events:
        event_type = str(event.get("event_type", "") or "")
        category = str(event.get("_category", "") or "")
        payload = _payload(event)

        if category == "decision_log" or event_type == "decision":
            _analyze_decision(payload, report, skip_reasons)
            readiness_reason = str(
                _get_nested(
                    payload,
                    "orderbook_unavailable_reason",
                    "display.orderbook_unavailable_reason",
                    "orderbook_readiness_reason",
                    "display.orderbook_readiness_reason",
                    "clob_error_category",
                    "display.clob_error_category",
                )
                or ""
            )
            if readiness_reason:
                orderbook_readiness_reasons[readiness_reason] += 1
            _track_clob_error(payload, clob_error_categories, clob_exception_types, clob_error_classes, report)
            _track_empty_book_recovery(payload, liquidity_states, report)
            _append_numeric(seconds_remaining_values, _get_nested(payload, "seconds_remaining", "display.seconds_remaining"))
            _append_numeric(seconds_since_open_values, _get_nested(payload, "seconds_since_open", "display.seconds_since_open"))
            _append_numeric(seconds_until_close_values, _get_nested(payload, "seconds_until_close", "display.seconds_until_close"))
            _append_numeric(first_seen_seconds_remaining_values, _get_nested(payload, "first_seen_seconds_remaining", "display.first_seen_seconds_remaining"))
            _append_numeric(first_evaluable_seconds_remaining_values, _get_nested(payload, "first_evaluable_seconds_remaining", "display.first_evaluable_seconds_remaining"))
            alignment_reason = str(_get_nested(payload, "active_window_alignment_reason", "display.active_window_alignment_reason") or "")
            if alignment_reason:
                active_window_alignment_reasons[alignment_reason] += 1
            _append_age_ms(orderbook_age_ms_values, payload, prefix="orderbook")
            _append_age_ms(oracle_age_ms_values, payload, prefix="oracle")
            _append_numeric(decision_latency_ms_values, _get_nested(payload, "decision_latency_ms", "display.decision_latency_ms"))
            _append_numeric(scan_cycle_duration_ms_values, _get_nested(payload, "scan_cycle_duration_ms", "display.scan_cycle_duration_ms"))
            cutoff_seconds = _get_nested(payload, "cutoff_block_seconds_remaining", "display.cutoff_block_seconds_remaining")
            if cutoff_seconds is not None:
                _append_numeric(cutoff_block_seconds_remaining_values, cutoff_seconds)
            cutoff_policy = str(_get_nested(payload, "cutoff_policy", "display.cutoff_policy") or "").lower()
            cutoff_reason = str(
                _get_nested(
                    payload,
                    "adaptive_cutoff_denied_reason",
                    "display.adaptive_cutoff_denied_reason",
                    "adaptive_cutoff_reason",
                    "display.adaptive_cutoff_reason",
                )
                or ""
            )
            if cutoff_policy == "adaptive":
                if _as_bool(_get_nested(payload, "adaptive_cutoff_allowed", "display.adaptive_cutoff_allowed")):
                    report.adaptive_cutoff_allowed_count += 1
                elif cutoff_reason:
                    report.adaptive_cutoff_denied_count += 1
                if cutoff_reason:
                    adaptive_cutoff_reasons[cutoff_reason] += 1
            if _as_bool(_get_nested(payload, "late_entry_hard_block", "display.late_entry_hard_block")):
                report.late_entry_hard_block_count += 1
            if _as_bool(_get_nested(payload, "micro_timing_allowed", "display.micro_timing_allowed")):
                report.micro_timing_allowed_count += 1
            if _as_bool(_get_nested(payload, "micro_timing_branch_entered", "display.micro_timing_branch_entered")):
                report.micro_timing_branch_entered_count += 1
            if _as_bool(_get_nested(payload, "micro_timing_candidate", "display.micro_timing_candidate")):
                report.micro_timing_candidate_count += 1
            micro_denied_reason = str(_get_nested(payload, "micro_timing_denied_reason", "display.micro_timing_denied_reason") or "")
            if micro_denied_reason:
                report.micro_timing_denied_count += 1
                micro_timing_denied_reasons[micro_denied_reason] += 1
            micro_skipped_reason = str(_get_nested(payload, "micro_timing_branch_skipped_reason", "display.micro_timing_branch_skipped_reason") or "")
            if micro_skipped_reason:
                micro_timing_branch_skipped_reasons[micro_skipped_reason] += 1
            asset = _asset_from_payload(payload)
            confidence = _as_float(payload.get("confidence"), default=float("nan"))
            if asset and confidence == confidence:
                latest_confidence_by_asset[asset] = confidence
            continue

        if category == "execution_log" or event_type == "execution":
            if _is_execution_failure(payload):
                report.execution_failure_count += 1
            continue

        if category == "market_snapshots" or event_type == "market_snapshot":
            _append_numeric(seconds_remaining_values, _get_nested(payload, "seconds_remaining", "display.seconds_remaining"))
            _append_numeric(seconds_since_open_values, _get_nested(payload, "seconds_since_open", "display.seconds_since_open"))
            _append_numeric(seconds_until_close_values, _get_nested(payload, "seconds_until_close", "display.seconds_until_close"))
            _append_numeric(first_seen_seconds_remaining_values, _get_nested(payload, "first_seen_seconds_remaining", "display.first_seen_seconds_remaining"))
            _append_numeric(first_evaluable_seconds_remaining_values, _get_nested(payload, "first_evaluable_seconds_remaining", "display.first_evaluable_seconds_remaining"))
            alignment_reason = str(_get_nested(payload, "active_window_alignment_reason", "display.active_window_alignment_reason") or "")
            if alignment_reason:
                active_window_alignment_reasons[alignment_reason] += 1
            _append_age_ms(orderbook_age_ms_values, payload, prefix="orderbook")
            _append_age_ms(oracle_age_ms_values, payload, prefix="oracle")
            readiness_reason = str(_get_nested(payload, "orderbook_readiness_reason", "orderbook_unavailable_reason", "clob_error_category") or "")
            if readiness_reason:
                orderbook_readiness_reasons[readiness_reason] += 1
            _track_clob_error(payload, clob_error_categories, clob_exception_types, clob_error_classes, report)
            _track_empty_book_recovery(payload, liquidity_states, report)
            asset = _asset_from_payload(payload)
            if asset:
                latest_market_snapshot[asset] = payload
            continue

        if category == "system_health" or event_type == "system_health":
            _append_numeric(scan_cycle_duration_ms_values, payload.get("scan_cycle_duration_ms"))
            _append_numeric(seconds_since_open_values, _get_nested(payload, "seconds_since_open", "display.seconds_since_open"))
            _append_numeric(seconds_until_close_values, _get_nested(payload, "seconds_until_close", "display.seconds_until_close", "seconds_remaining"))
            _append_numeric(first_seen_seconds_remaining_values, _get_nested(payload, "first_seen_seconds_remaining", "display.first_seen_seconds_remaining"))
            _append_numeric(first_evaluable_seconds_remaining_values, _get_nested(payload, "first_evaluable_seconds_remaining", "display.first_evaluable_seconds_remaining"))
            alignment_reason = str(_get_nested(payload, "active_window_alignment_reason", "display.active_window_alignment_reason") or "")
            if alignment_reason:
                active_window_alignment_reasons[alignment_reason] += 1
            continue

        if category == "trade_journal" and event_type == "trade_open":
            asset = _asset_from_payload(payload)
            opened_at = _parse_timestamp(event.get("timestamp_utc"))
            if opened_at is not None:
                opens[_trade_key(payload)] = (opened_at, payload)
            spread_value = _get_nested(payload, "spread", "entry_spread", "display.spread")
            if spread_value is None and asset in latest_market_snapshot:
                spread_value = _get_nested(latest_market_snapshot[asset], "spread", "orderbook.spread")
            spread = _as_float(spread_value, default=float("nan"))
            if spread == spread:
                spreads.append(spread)
            confidence_value = _get_nested(payload, "confidence", "entry_confidence", "display.confidence", "metadata.confidence")
            if confidence_value is None and asset in latest_confidence_by_asset:
                confidence_value = latest_confidence_by_asset[asset]
            confidence = _as_float(confidence_value, default=float("nan"))
            if confidence == confidence:
                confidences.append(confidence)
            continue

        if category == "trade_journal" and event_type == "trade_close":
            pnl = _as_float(payload.get("pnl"))
            closed_pnls.append(pnl)
            closed_at = _parse_timestamp(event.get("timestamp_utc"))
            open_item = opens.get(_trade_key(payload))
            holding_seconds: float | None = None
            if open_item and closed_at is not None:
                holding_seconds = max(0.0, (closed_at - open_item[0]).total_seconds())
                holding_times.append(holding_seconds)
            outcome = str(payload.get("outcome", "") or "").upper()
            asset = _asset_from_payload(payload)
            if outcome:
                pnl_by_outcome[outcome] += pnl
            if asset:
                pnl_by_asset[asset] += pnl
            report.trades.append(
                ReplayTrade(
                    timestamp_utc=str(event.get("timestamp_utc", "") or ""),
                    position_id=str(payload.get("position_id", "") or ""),
                    market_id=str(payload.get("market_id", "") or payload.get("market", "") or ""),
                    ticker=asset,
                    outcome=outcome,
                    side=str(payload.get("side", "") or ""),
                    pnl=pnl,
                    holding_seconds=holding_seconds,
                )
            )

    report.total_trades = len(closed_pnls)
    report.wins = sum(1 for pnl in closed_pnls if pnl > 0)
    report.losses = sum(1 for pnl in closed_pnls if pnl < 0)
    report.win_rate = report.wins / report.total_trades if report.total_trades else 0.0
    report.gross_pnl = sum(closed_pnls)
    report.average_pnl = report.gross_pnl / report.total_trades if report.total_trades else 0.0
    report.max_win = max([pnl for pnl in closed_pnls if pnl > 0], default=0.0)
    report.max_loss = min([pnl for pnl in closed_pnls if pnl < 0], default=0.0)
    report.average_holding_time_seconds = sum(holding_times) / len(holding_times) if holding_times else 0.0
    report.top_skip_reasons = skip_reasons.most_common(10)
    report.approved_vs_rejected_ratio = (
        report.approved_decisions / report.rejected_decisions if report.rejected_decisions else float(report.approved_decisions)
    )
    report.average_spread_at_entry = sum(spreads) / len(spreads) if spreads else 0.0
    report.average_confidence_at_entry = sum(confidences) / len(confidences) if confidences else 0.0
    report.average_seconds_remaining = sum(seconds_remaining_values) / len(seconds_remaining_values) if seconds_remaining_values else 0.0
    report.min_seconds_remaining = min(seconds_remaining_values) if seconds_remaining_values else 0.0
    report.average_seconds_since_open = sum(seconds_since_open_values) / len(seconds_since_open_values) if seconds_since_open_values else 0.0
    report.average_seconds_until_close = sum(seconds_until_close_values) / len(seconds_until_close_values) if seconds_until_close_values else 0.0
    report.first_seen_seconds_remaining = max(first_seen_seconds_remaining_values) if first_seen_seconds_remaining_values else 0.0
    report.first_evaluable_seconds_remaining = max(first_evaluable_seconds_remaining_values) if first_evaluable_seconds_remaining_values else 0.0
    report.average_orderbook_age_ms = sum(orderbook_age_ms_values) / len(orderbook_age_ms_values) if orderbook_age_ms_values else 0.0
    report.max_orderbook_age_ms = max(orderbook_age_ms_values) if orderbook_age_ms_values else 0.0
    report.average_oracle_age_ms = sum(oracle_age_ms_values) / len(oracle_age_ms_values) if oracle_age_ms_values else 0.0
    report.max_oracle_age_ms = max(oracle_age_ms_values) if oracle_age_ms_values else 0.0
    report.average_scan_cycle_duration_ms = (
        sum(scan_cycle_duration_ms_values) / len(scan_cycle_duration_ms_values)
        if scan_cycle_duration_ms_values
        else 0.0
    )
    report.max_scan_cycle_duration_ms = max(scan_cycle_duration_ms_values) if scan_cycle_duration_ms_values else 0.0
    report.average_decision_latency_ms = (
        sum(decision_latency_ms_values) / len(decision_latency_ms_values)
        if decision_latency_ms_values
        else 0.0
    )
    report.max_decision_latency_ms = max(decision_latency_ms_values) if decision_latency_ms_values else 0.0
    report.cutoff_block_count = len(cutoff_block_seconds_remaining_values)
    report.average_cutoff_block_seconds_remaining = (
        sum(cutoff_block_seconds_remaining_values) / len(cutoff_block_seconds_remaining_values)
        if cutoff_block_seconds_remaining_values
        else 0.0
    )
    report.adaptive_cutoff_reasons = adaptive_cutoff_reasons.most_common(10)
    report.adaptive_cutoff_denied_reasons = adaptive_cutoff_reasons.most_common(10)
    report.micro_timing_denied_reasons = micro_timing_denied_reasons.most_common(10)
    report.micro_timing_branch_skipped_reasons = micro_timing_branch_skipped_reasons.most_common(10)
    report.active_window_alignment_reasons = active_window_alignment_reasons.most_common(10)
    report.orderbook_readiness_reasons = orderbook_readiness_reasons.most_common(10)
    report.clob_error_categories = clob_error_categories.most_common(10)
    report.clob_exception_types = clob_exception_types.most_common(10)
    report.clob_error_classes = clob_error_classes.most_common(10)
    report.liquidity_states = liquidity_states.most_common(10)
    report.pnl_by_outcome = dict(sorted(pnl_by_outcome.items()))
    report.pnl_by_asset = dict(sorted(pnl_by_asset.items()))
    report.phase2_coverage = build_phase2_coverage_from_events(events)
    lifecycle_replay = build_partial_lifecycle_replay_from_events(events)
    report.partial_lifecycle_replay = lifecycle_replay
    report.lifecycle_replay_confidence = str(lifecycle_replay.get("lifecycle_replay_confidence", "INSUFFICIENT"))
    report.replay_supported_sections = list(lifecycle_replay.get("replay_supported_sections", []))
    report.replay_unsupported_sections = list(lifecycle_replay.get("replay_unsupported_sections", []))
    report.missed_starter_candidates = list(lifecycle_replay.get("missed_starter_candidates", []))
    report.timing_decay_summary = dict(lifecycle_replay.get("timing_decay_summary", {}))
    report.spread_liquidity_readiness_summary = dict(lifecycle_replay.get("spread_liquidity_readiness_summary", {}))

    if write_reports:
        write_replay_report(report, report_dir=report_dir)
    if write_csv:
        write_replay_trades_csv(report, report_dir=report_dir)
    return report


def _analyze_decision(payload: dict[str, Any], report: ReplayReport, skip_reasons: Counter[str]) -> None:
    decision_type = str(payload.get("decision_type", "") or "").lower()
    skipped = bool(payload.get("skipped", False))
    reason = str(payload.get("skip_reason", "") or _get_nested(payload, "display.skip_reason") or "").strip()

    if decision_type == "approved" or (not skipped and str(payload.get("decision", "")).lower() not in {"skip", ""}):
        report.approved_decisions += 1
    elif decision_type in {"rejected", "risk_rejected"} or skipped:
        report.rejected_decisions += 1

    if skipped or decision_type == "skipped":
        report.skipped_decisions += 1
        if reason:
            skip_reasons[reason] += 1

    if decision_type == "risk_rejected" or _looks_like_risk_reason(reason):
        report.risk_reject_count += 1


def _looks_like_risk_reason(reason: str) -> bool:
    text = reason.lower()
    return any(token in text for token in ("risk", "floor", "balance", "drawdown", "reconciliation", "lockdown"))


def _is_execution_failure(payload: dict[str, Any]) -> bool:
    event = str(payload.get("event", "") or "").lower()
    status = str(payload.get("status", "") or "").lower()
    if event == "order_intent_reject":
        return False
    if event in {"order_submit_failed", "market_analysis_exception"}:
        return True
    if event == "cancel_order" and status in {"failed", "error", "rejected"}:
        return True
    if event in {"live_order_submitted", "order_submit"} and status in {"failed", "error", "rejected"}:
        return True
    return event.endswith("_failed") or event.endswith("_failure")


def write_replay_report(report: ReplayReport, *, report_dir: str | Path | None = None) -> Path:
    output_dir = Path(report_dir or DEFAULT_REPORT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    date_part = _report_date_part(report.date_from, report.date_to, report.time_filter, report.run_id)
    output_path = output_dir / f"replay_report_{date_part}.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report.to_dict(), handle, indent=2, sort_keys=True, default=str)
    return output_path


def write_replay_trades_csv(report: ReplayReport, *, report_dir: str | Path | None = None) -> Path:
    output_dir = Path(report_dir or DEFAULT_REPORT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    date_part = _report_date_part(report.date_from, report.date_to, report.time_filter, report.run_id)
    output_path = output_dir / f"replay_trades_{date_part}.csv"
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "timestamp_utc",
                "position_id",
                "market_id",
                "ticker",
                "outcome",
                "side",
                "pnl",
                "holding_seconds",
            ],
        )
        writer.writeheader()
        for trade in report.trades:
            writer.writerow(asdict(trade))
    return output_path


def print_summary(report: ReplayReport) -> None:
    print("Replay Analyzer")
    if report.time_filter.get("applied"):
        print(
            "range={start}..{end} filter={since}..{until} run_id={run_id} semantics={semantics} events={events} bad_json={bad_json}".format(
                start=report.date_from,
                end=report.date_to,
                since=report.time_filter.get("since_utc"),
                until=report.time_filter.get("until_utc"),
                run_id=report.run_id or "",
                semantics=report.time_filter.get("semantics"),
                events=report.events_loaded,
                bad_json=report.bad_json_lines,
            )
        )
    else:
        print(f"range={report.date_from}..{report.date_to} run_id={report.run_id or ''} events={report.events_loaded} bad_json={report.bad_json_lines}")
    print(
        "trades={trades} win_rate={win_rate:.2%} gross_pnl={gross:.4f} avg_pnl={avg:.4f} "
        "max_win={max_win:.4f} max_loss={max_loss:.4f}".format(
            trades=report.total_trades,
            win_rate=report.win_rate,
            gross=report.gross_pnl,
            avg=report.average_pnl,
            max_win=report.max_win,
            max_loss=report.max_loss,
        )
    )
    print(
        "skipped={skipped} approved={approved} rejected={rejected} risk_rejects={risk} exec_failures={exec_fail}".format(
            skipped=report.skipped_decisions,
            approved=report.approved_decisions,
            rejected=report.rejected_decisions,
            risk=report.risk_reject_count,
            exec_fail=report.execution_failure_count,
        )
    )
    print(
        "avg_holding_s={holding:.2f} avg_spread_entry={spread:.4f} avg_confidence_entry={confidence:.4f}".format(
            holding=report.average_holding_time_seconds,
            spread=report.average_spread_at_entry,
            confidence=report.average_confidence_at_entry,
        )
    )
    print(
        "avg_seconds_remaining={seconds:.2f} min_seconds_remaining={min_seconds:.2f} "
        "avg_orderbook_age_ms={ob_age:.2f} avg_oracle_age_ms={oracle_age:.2f} "
        "avg_cycle_ms={cycle:.2f} avg_decision_latency_ms={latency:.2f} cutoff_blocks={cutoff}".format(
            seconds=report.average_seconds_remaining,
            min_seconds=report.min_seconds_remaining,
            ob_age=report.average_orderbook_age_ms,
            oracle_age=report.average_oracle_age_ms,
            cycle=report.average_scan_cycle_duration_ms,
            latency=report.average_decision_latency_ms,
            cutoff=report.cutoff_block_count,
        )
    )
    print(
        "adaptive_cutoff_allowed={allowed} adaptive_cutoff_denied={denied} "
        "late_entry_hard_blocks={hard_blocks} adaptive_denied_reasons={reasons}".format(
            allowed=report.adaptive_cutoff_allowed_count,
            denied=report.adaptive_cutoff_denied_count,
            hard_blocks=report.late_entry_hard_block_count,
            reasons=report.adaptive_cutoff_denied_reasons,
        )
    )
    print(f"orderbook_readiness_reasons={report.orderbook_readiness_reasons}")
    print(f"clob_error_categories={report.clob_error_categories}")
    print(f"clob_exception_types={report.clob_exception_types}")
    print(
        "clob_health error_classes={classes} backoff_active={backoff} circuit_open={circuit} "
        "max_error_rate={error_rate:.4f} recovery_count={recovery}".format(
            classes=report.clob_error_classes,
            backoff=report.clob_backoff_active_count,
            circuit=report.clob_circuit_open_count,
            error_rate=report.max_clob_error_rate,
            recovery=report.clob_recovery_count,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze offline PolyTrade quant JSONL replay data.")
    parser.add_argument("--date", help="Single date to analyze in YYYY-MM-DD format.", default=None)
    parser.add_argument("--from", dest="date_from", help="Start date in YYYY-MM-DD format.", default=None)
    parser.add_argument("--to", dest="date_to", help="End date in YYYY-MM-DD format.", default=None)
    parser.add_argument("--since", default=None, help="UTC start time HH:MM for same-day filtering; inclusive.")
    parser.add_argument("--until", default=None, help="UTC end time HH:MM for same-day filtering; exclusive.")
    parser.add_argument("--run-id", default=None, help="Exact run_id to isolate; events without this run_id are excluded.")
    parser.add_argument("--list-run-ids", action="store_true", help="List available run_id values for the selected date/range.")
    parser.add_argument("--base-dir", default=str(DEFAULT_QUANT_DATA_DIR), help="Quant data root directory.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Output report directory.")
    parser.add_argument("--no-json", action="store_true", help="Do not write replay_report JSON.")
    parser.add_argument("--csv", action="store_true", help="Write replay_trades CSV.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.list_run_ids:
        summaries = discover_run_ids(
            base_dir=args.base_dir,
            date=args.date,
            date_from=args.date_from,
            date_to=args.date_to,
            since=args.since,
            until=args.until,
        )
        print_run_id_summary(summaries)
        return 0
    report = analyze_replay(
        base_dir=args.base_dir,
        date=args.date,
        date_from=args.date_from,
        date_to=args.date_to,
        report_dir=args.report_dir,
        write_reports=not args.no_json,
        write_csv=args.csv,
        since=args.since,
        until=args.until,
        run_id=args.run_id,
    )
    print_summary(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
