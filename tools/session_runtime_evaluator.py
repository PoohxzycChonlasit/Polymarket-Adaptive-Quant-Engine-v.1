from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, time as time_type, timezone
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from tools.no_entry_analyzer import (
    DEFAULT_QUANT_DATA_DIR,
    DEFAULT_REALTIME_LOG_DIR,
    DEFAULT_REPORT_DIR,
    NoEntryReport,
    analyze_no_entries,
)
from tools.paper_evaluation_report import DECISION_CAUTION, DECISION_FAIL, DECISION_PASS
from tools.replay_analyzer import (
    ReplayReport,
    analyze_replay,
    build_partial_lifecycle_replay_from_events,
    build_phase2_coverage_from_events,
    discover_run_ids,
    load_replay_events,
    print_run_id_summary,
)
from utils.no_entry_diagnostics import normalize_skip_reason


BOTTLENECKS = (
    "cutoff",
    "market_readiness",
    "stale_data",
    "latency",
    "risk_plan_zero",
    "strategy_thresholds",
    "execution_failures",
    "websocket_instability",
    "healthy_no_signal",
    "no_data",
)

HARDBLOCK_ORDERBOOK_REASONS = {
    "missing_token_id",
    "empty_book",
    "clob_error",
    "token_mapping_mismatch",
    "clob_http_error",
    "clob_timeout",
    "clob_rate_limited",
    "clob_parse_error",
    "clob_empty_response",
    "clob_token_not_found",
    "clob_client_not_connected",
    "clob_auth_or_client_issue",
}
WARMUP_ORDERBOOK_REASONS = {"warmup_pending"}
STALE_ORDERBOOK_REASONS = {"stale_book"}

BANKROLL_VISIBILITY_FIELDS = (
    "bankroll_tier_id",
    "bankroll_tier_name",
    "bankroll_family",
    "bankroll_risk_profile",
    "bankroll_tier_locked",
    "bankroll_hysteresis_active",
    "bankroll_mode",
    "micro_survival_active",
    "micro_position_size",
)

REGIME_EVENT_TYPES = {"decision", "market_snapshot"}
REGIME_CATEGORIES = {"decision_log", "market_snapshots"}
PROBABILITY_BUCKET_LABELS = ("0.00-0.45", "0.45-0.55", "0.55-0.65", "0.65-0.75", "0.75+")
CANDIDATE_GAP_DIAGNOSES = {
    "EV_TOO_LOW",
    "CONFIDENCE_TOO_LOW",
    "SPREAD_TOO_WIDE",
    "LIQUIDITY_NOT_READY",
    "CANDIDATE_TOO_LATE",
    "CUTOFF_TOO_STRICT",
    "REGIME_NO_EDGE",
    "INSUFFICIENT_CANDIDATE_DATA",
}
SPREAD_COMPRESSION_DIAGNOSES = {
    "SPREAD_NEVER_NORMALIZED",
    "SPREAD_NORMALIZED_TOO_LATE",
    "SPREAD_RECOVERED_BEFORE_CUTOFF",
    "REGIME_DEPENDENT_SPREAD_BEHAVIOR",
    "INSUFFICIENT_SPREAD_DATA",
}
REGIME_TRADEABILITY_CLASSIFICATIONS = {
    "TRADEABLE_REGIME",
    "WATCHLIST_REGIME",
    "AVOID_REGIME",
    "UNKNOWN_COVERAGE_GAP",
    "INSUFFICIENT_REGIME_SAMPLE",
}
MULTI_SESSION_SPREAD_INTERPRETATIONS = {
    "STRUCTURAL_SPREAD_LIMITATION",
    "REGIME_DEPENDENT_SPREAD_LIMITATION",
    "SESSION_SPECIFIC_SPREAD_FAILURE",
    "MICRO_BANKROLL_SENSITIVITY",
    "INSUFFICIENT_MULTI_SESSION_DATA",
}
LIQUIDITY_NOT_READY_STATES = {
    "EMPTY",
    "RECOVERING",
    "DEGRADED",
    "STALE",
    "UNKNOWN",
    "NOT_READY",
    "UNAVAILABLE",
}
SCANNER_RESET_PLAN = (
    "preload next BTC/ETH 5m markets -> cache token IDs early -> warm orderbooks immediately "
    "-> mark first tradable second -> evaluate continuously from the early window"
)


@dataclass
class SessionRuntimeEvaluation:
    date: str
    generated_at_utc: str
    session_status: str
    primary_bottleneck: str
    run_id: str = ""
    secondary_bottleneck: str = "none"
    bottleneck_scores: dict[str, int] = field(default_factory=dict)
    health_summary: dict[str, Any] = field(default_factory=dict)
    skip_summary: dict[str, Any] = field(default_factory=dict)
    timing_quality: dict[str, Any] = field(default_factory=dict)
    scanner_lifecycle: dict[str, Any] = field(default_factory=dict)
    market_readiness: dict[str, Any] = field(default_factory=dict)
    candidate_timing: dict[str, Any] = field(default_factory=dict)
    cutoff_behavior: dict[str, Any] = field(default_factory=dict)
    cutoff_summary: dict[str, Any] = field(default_factory=dict)
    cutoff_by_regime: dict[str, Any] = field(default_factory=dict)
    candidate_gap_summary: dict[str, Any] = field(default_factory=dict)
    spread_compression_summary: dict[str, Any] = field(default_factory=dict)
    regime_replay_summary: dict[str, Any] = field(default_factory=dict)
    regime_coverage_audit: dict[str, Any] = field(default_factory=dict)
    regime_probability_summary: dict[str, Any] = field(default_factory=dict)
    risk_blocks: dict[str, Any] = field(default_factory=dict)
    execution_summary: dict[str, Any] = field(default_factory=dict)
    orderbook_readiness: dict[str, Any] = field(default_factory=dict)
    regime_summary: dict[str, Any] = field(default_factory=dict)
    phase2_coverage: dict[str, Any] = field(default_factory=dict)
    inventory_replay_readiness: dict[str, Any] = field(default_factory=dict)
    partial_lifecycle_replay: dict[str, Any] = field(default_factory=dict)
    lifecycle_replay_confidence: str = "INSUFFICIENT"
    replay_supported_sections: list[dict[str, Any]] = field(default_factory=list)
    replay_unsupported_sections: list[dict[str, Any]] = field(default_factory=list)
    missed_starter_candidates: list[dict[str, Any]] = field(default_factory=list)
    timing_decay_summary: dict[str, Any] = field(default_factory=dict)
    spread_liquidity_readiness_summary: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    reports_used: dict[str, Any] = field(default_factory=dict)
    time_filter: dict[str, Any] = field(default_factory=dict)
    fail_reasons: list[str] = field(default_factory=list)
    caution_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_telegram_payload(self) -> dict[str, Any]:
        return {
            "title": "Paper Session Runtime Evaluation",
            "session_status": self.session_status,
            "primary_bottleneck": self.primary_bottleneck,
            "secondary_bottleneck": self.secondary_bottleneck,
            "scanned": self.health_summary.get("scanned", 0),
            "entered": self.health_summary.get("entered", 0),
            "skipped": self.health_summary.get("skipped", 0),
            "top_skip_reasons": self.skip_summary.get("top_skip_reasons", []),
            "recommendations": self.recommendations[:3],
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _parse_event_timestamp(value: Any) -> datetime | None:
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
    return parsed.astimezone(timezone.utc)


def _parse_hhmm_utc(date: str, value: str | None, *, field_name: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed_time = time_type.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be HH:MM in UTC; got {value!r}") from exc
    if parsed_time.second or parsed_time.microsecond:
        raise ValueError(f"{field_name} must be HH:MM in UTC; got {value!r}")
    parsed_date = datetime.strptime(date, "%Y-%m-%d").date()
    return datetime.combine(parsed_date, parsed_time, tzinfo=timezone.utc)


def _time_filter_payload(
    *,
    date: str,
    since: str | None = None,
    until: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    since_utc = _parse_hhmm_utc(date, since, field_name="--since")
    until_utc = _parse_hhmm_utc(date, until, field_name="--until")
    if since_utc is not None and until_utc is not None and since_utc >= until_utc:
        raise ValueError("--since must be earlier than --until")
    return {
        "timezone": "UTC",
        "since": since,
        "until": until,
        "run_id": run_id,
        "run_id_applied": bool(run_id),
        "since_utc": since_utc,
        "until_utc": until_utc,
        "applied": since_utc is not None or until_utc is not None,
        "display": _format_filter_range(date=date, since_utc=since_utc, until_utc=until_utc),
    }


def _format_filter_range(
    *,
    date: str,
    since_utc: datetime | None,
    until_utc: datetime | None,
) -> str:
    start = since_utc or datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end = until_utc or datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc).replace(hour=23, minute=59, second=59)
    return f"{start.isoformat().replace('+00:00', 'Z')}..{end.isoformat().replace('+00:00', 'Z')}"


def _event_in_time_filter(event: dict[str, Any], time_filter: dict[str, Any]) -> bool:
    run_id = time_filter.get("run_id")
    if run_id and str(event.get("run_id") or "") != str(run_id):
        return False
    if not time_filter.get("applied"):
        return True
    timestamp = _parse_event_timestamp(event.get("timestamp_utc"))
    if timestamp is None:
        return False
    since_utc = time_filter.get("since_utc")
    until_utc = time_filter.get("until_utc")
    if since_utc is not None and timestamp < since_utc:
        return False
    if until_utc is not None and timestamp >= until_utc:
        return False
    return True


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


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _safe_filename_token(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    sanitized = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in text)
    return sanitized[:80] or "run"


def _normalize_top_skip_reasons(items: Any) -> list[list[Any]]:
    normalized: list[list[Any]] = []
    if isinstance(items, dict):
        iterator = items.items()
    else:
        iterator = items or []
    for item in iterator:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            reason, count = item[0], item[1]
        else:
            continue
        normalized.append([normalize_skip_reason(str(reason)), _as_int(count)])
    return normalized


def _skip_counts_from_session(summary: dict[str, Any] | None) -> Counter[str]:
    counts: Counter[str] = Counter()
    if not summary:
        return counts
    raw_counts = summary.get("skipped_trade_reasons", {})
    if isinstance(raw_counts, dict):
        for reason, count in raw_counts.items():
            counts[normalize_skip_reason(str(reason))] += _as_int(count)
    for reason, count in _normalize_top_skip_reasons(summary.get("top_skip_reasons", [])):
        counts[reason] += 0 if reason in counts else _as_int(count)
    return counts


def _skip_counts_from_replay(report: ReplayReport | dict[str, Any] | None) -> Counter[str]:
    if report is None:
        return Counter()
    payload = report.to_dict() if hasattr(report, "to_dict") else dict(report)
    counts: Counter[str] = Counter()
    for reason, count in _normalize_top_skip_reasons(payload.get("top_skip_reasons", [])):
        counts[reason] += _as_int(count)
    return counts


def _safe_analyze_replay(
    *,
    date: str,
    quant_data_dir: str | Path,
    since_utc: datetime | None = None,
    until_utc: datetime | None = None,
    run_id: str | None = None,
) -> tuple[ReplayReport | None, str | None]:
    try:
        report = analyze_replay(
            base_dir=quant_data_dir,
            date=date,
            write_reports=False,
            write_csv=False,
            since_utc=since_utc,
            until_utc=until_utc,
            run_id=run_id,
        )
        return report, None
    except Exception as exc:
        return None, f"replay_analyzer_failed:{exc}"


def _safe_analyze_no_entries(
    *,
    date: str,
    quant_data_dir: str | Path,
    realtime_log_dir: str | Path,
    run_id: str | None = None,
) -> tuple[NoEntryReport | None, str | None]:
    try:
        report = analyze_no_entries(
            date=date,
            quant_data_dir=quant_data_dir,
            realtime_log_dir=realtime_log_dir,
            write_report=False,
            run_id=run_id,
        )
        return report, None
    except Exception as exc:
        return None, f"no_entry_analyzer_failed:{exc}"


def _execution_log_paths(base_dir: str | Path, date: str) -> list[Path]:
    base_path = Path(base_dir)
    direct_candidates = [
        base_path / "execution_log" / f"{date}.jsonl",
        base_path / f"execution_log_{date}.jsonl",
        base_path / f"{date}_execution_log.jsonl",
        base_path / "execution" / f"{date}.jsonl",
    ]
    existing_direct = [path for path in direct_candidates if path.exists()]
    if existing_direct:
        return existing_direct

    if not base_path.exists():
        return []

    discovered: list[Path] = []
    for path in base_path.rglob("*.jsonl"):
        relative = str(path.relative_to(base_path)).lower()
        if date not in relative:
            continue
        if "execution" not in relative:
            continue
        if "report" in relative or "cache" in relative:
            continue
        discovered.append(path)
    return sorted(discovered)


def _payload_from_event(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload")
    if isinstance(payload, dict):
        return payload
    return event


def _bankroll_visibility_sources(payload: dict[str, Any]) -> list[dict[str, Any]]:
    sources = [payload]
    for key in ("display", "risk_blocks", "health_summary"):
        value = payload.get(key)
        if isinstance(value, dict):
            sources.append(value)
    return sources


def _bankroll_visibility_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    visibility: dict[str, Any] = {}
    for source in _bankroll_visibility_sources(payload):
        for field_name in BANKROLL_VISIBILITY_FIELDS:
            if field_name not in source:
                continue
            value = source.get(field_name)
            if field_name in {"bankroll_tier_locked", "bankroll_hysteresis_active", "micro_survival_active"}:
                visibility[field_name] = bool(value)
            elif field_name == "micro_position_size":
                visibility[field_name] = _as_float(value)
            elif str(value or "").strip():
                visibility[field_name] = str(value)
    return visibility


def _load_bankroll_visibility_from_events(
    *,
    base_dir: str | Path,
    date: str,
    time_filter: dict[str, Any],
) -> dict[str, Any]:
    try:
        events, _bad_lines = load_replay_events(
            base_dir=base_dir,
            date_from=date,
            date_to=date,
            since_utc=time_filter.get("since_utc"),
            until_utc=time_filter.get("until_utc"),
            run_id=time_filter.get("run_id"),
        )
    except Exception:
        return {}

    visibility: dict[str, Any] = {}
    for event in events:
        payload = _payload_from_event(event)
        if not payload:
            continue
        event_visibility = _bankroll_visibility_from_payload(payload)
        if event_visibility:
            visibility.update(event_visibility)
    return visibility


def _merge_bankroll_visibility(
    *,
    session_summary: dict[str, Any] | None,
    event_visibility: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(event_visibility)
    if session_summary:
        summary_visibility = _bankroll_visibility_from_payload(session_summary)
        merged.update(summary_visibility)
    return {
        "bankroll_tier_id": str(merged.get("bankroll_tier_id", "")),
        "bankroll_tier_name": str(merged.get("bankroll_tier_name", "")),
        "bankroll_family": str(merged.get("bankroll_family", "")),
        "bankroll_risk_profile": str(merged.get("bankroll_risk_profile", "")),
        "bankroll_tier_locked": bool(merged.get("bankroll_tier_locked", False)),
        "bankroll_hysteresis_active": bool(merged.get("bankroll_hysteresis_active", False)),
        "bankroll_mode": str(merged.get("bankroll_mode", "")),
        "micro_survival_active": bool(merged.get("micro_survival_active", False)),
        "micro_position_size": _as_float(merged.get("micro_position_size")),
    }


def _counter_from_pairs(value: Any) -> Counter[str]:
    counts: Counter[str] = Counter()
    if isinstance(value, dict):
        iterator = value.items()
    else:
        iterator = value or []
    for item in iterator:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            key, count = item[0], item[1]
        else:
            continue
        label = str(key or "UNKNOWN").strip() or "UNKNOWN"
        counts[label] += _as_int(count)
    return counts


def _regime_value_from_payload(payload: dict[str, Any], field_name: str) -> str:
    if field_name in payload and str(payload.get(field_name) or "").strip():
        return str(payload.get(field_name)).strip()
    display = payload.get("display")
    if isinstance(display, dict) and str(display.get(field_name) or "").strip():
        return str(display.get(field_name)).strip()
    return "UNKNOWN"


def _payload_value(payload: dict[str, Any], *keys: str) -> Any:
    display = payload.get("display")
    for key in keys:
        if key in payload:
            value = payload.get(key)
            if value is not None and value != "":
                return value
        if isinstance(display, dict) and key in display:
            value = display.get(key)
            if value is not None and value != "":
                return value
    return None


def _probability_bucket(value: Any) -> str:
    parsed = _as_float(value, default=float("nan"))
    if parsed != parsed:
        return "UNKNOWN"
    if parsed < 0.45:
        return "0.00-0.45"
    if parsed < 0.55:
        return "0.45-0.55"
    if parsed < 0.65:
        return "0.55-0.65"
    if parsed < 0.75:
        return "0.65-0.75"
    return "0.75+"


def _market_regime_from_payload(payload: dict[str, Any]) -> str:
    market_regime = _regime_value_from_payload(payload, "market_regime")
    if market_regime != "UNKNOWN":
        return market_regime
    volatility = _regime_value_from_payload(payload, "volatility_regime")
    trend = _regime_value_from_payload(payload, "trend_regime")
    if volatility != "UNKNOWN" or trend != "UNKNOWN":
        return f"{trend}+{volatility}"
    return "UNKNOWN"


def _phase_probability_record(event: dict[str, Any]) -> dict[str, Any] | None:
    event_type = str(event.get("event_type", "") or "")
    category = str(event.get("_category", "") or "")
    if event_type not in REGIME_EVENT_TYPES and category not in REGIME_CATEGORIES:
        return None
    payload = _payload_from_event(event)
    if not payload:
        return None

    decision_type = str(_payload_value(payload, "decision_type") or "").strip().lower()
    decision = str(_payload_value(payload, "decision") or "").strip().lower()
    skipped = _as_bool(_payload_value(payload, "skipped"))
    skip_reason_raw = str(_payload_value(payload, "normalized_skip_reason", "raw_skip_reason", "skip_reason") or "")
    skip_reason = normalize_skip_reason(skip_reason_raw)
    if decision_type in {"approved", "enter", "entered"} or (decision in {"buy", "enter", "approved"} and not skipped):
        decision_state = "ENTER_CANDIDATE"
    elif skipped or decision_type in {"skipped", "rejected", "risk_rejected"} or decision == "skip":
        decision_state = "SKIP"
    else:
        decision_state = "OBSERVED"

    bullish_probability = _first_candidate_float(payload, "bullish_probability", "p_bullish", "yes_probability")
    bearish_probability = _first_candidate_float(payload, "bearish_probability", "p_bearish", "no_probability")
    probability_values = [value for value in (bullish_probability, bearish_probability) if value is not None]
    candidate_probability = max(probability_values) if probability_values else None
    seconds_remaining = _payload_value(payload, "seconds_remaining", "seconds_until_close", "time_remaining_seconds")
    indicator_evidence = _payload_value(payload, "indicator_evidence")
    return {
        "timestamp_utc": str(event.get("timestamp_utc", "") or ""),
        "event_type": event_type,
        "category": category,
        "decision_state": decision_state,
        "market_regime": _market_regime_from_payload(payload),
        "volatility_regime": _regime_value_from_payload(payload, "volatility_regime"),
        "trend_regime": _regime_value_from_payload(payload, "trend_regime"),
        "skip_reason": skip_reason or skip_reason_raw,
        "bullish_probability": bullish_probability,
        "bearish_probability": bearish_probability,
        "candidate_probability": candidate_probability,
        "probability_bucket": _probability_bucket(candidate_probability),
        "trend_strength": _first_candidate_float(payload, "trend_strength"),
        "reversal_risk": _first_candidate_float(payload, "reversal_risk"),
        "volatility_score": _first_candidate_float(payload, "volatility_score"),
        "compression_score": _first_candidate_float(payload, "compression_score"),
        "seconds_remaining": _as_float(seconds_remaining, default=float("nan")),
        "timing_bucket": _candidate_timing_bucket(seconds_remaining),
        "indicator_evidence_keys": sorted(str(key) for key in indicator_evidence.keys()) if isinstance(indicator_evidence, dict) else [],
    }


def _average(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _summarize_timing_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    seconds_values = [
        _as_float(record.get("seconds_remaining"), default=float("nan"))
        for record in records
    ]
    seconds_values = [value for value in seconds_values if value == value]
    timing_buckets = Counter(str(record.get("timing_bucket") or "unknown") for record in records)
    return {
        "events": int(len(records)),
        "avg_seconds_remaining": _average(seconds_values),
        "closest_seconds_remaining": round(min(seconds_values), 2) if seconds_values else None,
        "timing_buckets": dict(timing_buckets.most_common()),
    }


def _summarize_regime_probability_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {}

    skip_records = [record for record in records if record.get("decision_state") == "SKIP"]
    enter_records = [record for record in records if record.get("decision_state") == "ENTER_CANDIDATE"]
    candidate_records = skip_records + enter_records
    probability_records = [record for record in records if record.get("candidate_probability") is not None]
    market_regime_counts = Counter(str(record.get("market_regime") or "UNKNOWN") for record in records)
    skip_by_regime = Counter(str(record.get("market_regime") or "UNKNOWN") for record in skip_records)
    enter_by_regime = Counter(str(record.get("market_regime") or "UNKNOWN") for record in enter_records)
    skip_reason_by_regime: dict[str, Counter[str]] = {}
    candidate_timing_by_regime: dict[str, list[dict[str, Any]]] = {}
    indicator_keys: Counter[str] = Counter()
    for record in records:
        indicator_keys.update(record.get("indicator_evidence_keys", []))
    for record in skip_records:
        regime = str(record.get("market_regime") or "UNKNOWN")
        reason = str(record.get("skip_reason") or "UNKNOWN")
        skip_reason_by_regime.setdefault(regime, Counter())[reason] += 1
    for record in candidate_records:
        candidate_timing_by_regime.setdefault(str(record.get("market_regime") or "UNKNOWN"), []).append(record)

    bucket_stats: dict[str, dict[str, Any]] = {
        label: {
            "events": 0,
            "blocked_candidates": 0,
            "enter_candidates": 0,
            "bullish_values": [],
            "bearish_values": [],
            "market_regimes": Counter(),
        }
        for label in PROBABILITY_BUCKET_LABELS
    }
    bucket_stats["UNKNOWN"] = {
        "events": 0,
        "blocked_candidates": 0,
        "enter_candidates": 0,
        "bullish_values": [],
        "bearish_values": [],
        "market_regimes": Counter(),
    }
    for record in records:
        bucket = str(record.get("probability_bucket") or "UNKNOWN")
        stats = bucket_stats.setdefault(bucket, {
            "events": 0,
            "blocked_candidates": 0,
            "enter_candidates": 0,
            "bullish_values": [],
            "bearish_values": [],
            "market_regimes": Counter(),
        })
        stats["events"] += 1
        stats["market_regimes"][str(record.get("market_regime") or "UNKNOWN")] += 1
        if record.get("decision_state") == "SKIP":
            stats["blocked_candidates"] += 1
        if record.get("decision_state") == "ENTER_CANDIDATE":
            stats["enter_candidates"] += 1
        if record.get("bullish_probability") is not None:
            stats["bullish_values"].append(_as_float(record.get("bullish_probability")))
        if record.get("bearish_probability") is not None:
            stats["bearish_values"].append(_as_float(record.get("bearish_probability")))

    probability_buckets = {
        bucket: {
            "events": int(stats["events"]),
            "blocked_candidates": int(stats["blocked_candidates"]),
            "enter_candidates": int(stats["enter_candidates"]),
            "avg_bullish_probability": _average(stats["bullish_values"]),
            "avg_bearish_probability": _average(stats["bearish_values"]),
            "top_market_regimes": [[label, count] for label, count in stats["market_regimes"].most_common(3)],
        }
        for bucket, stats in bucket_stats.items()
        if stats["events"]
    }

    compression_skip = [
        _as_float(record.get("compression_score"), default=float("nan"))
        for record in skip_records
    ]
    compression_enter = [
        _as_float(record.get("compression_score"), default=float("nan"))
        for record in enter_records
    ]
    compression_skip = [value for value in compression_skip if value == value]
    compression_enter = [value for value in compression_enter if value == value]
    high_compression_skips = [value for value in compression_skip if value >= 0.65]
    defensive_reasons = {"risk_plan_zero", "risk_mode_lockdown", "defensive_mode", "confidence_too_low"}
    defensive_skip_records = [
        record
        for record in skip_records
        if str(record.get("skip_reason") or "") in defensive_reasons
        or "risk" in str(record.get("skip_reason") or "")
        or "lockdown" in str(record.get("skip_reason") or "")
        or "defensive" in str(record.get("skip_reason") or "")
    ]
    high_reversal_defensive = [
        record
        for record in defensive_skip_records
        if _as_float(record.get("reversal_risk"), default=float("nan")) >= 0.65
    ]
    candidate_seconds = [
        _as_float(record.get("seconds_remaining"), default=float("nan"))
        for record in candidate_records
    ]
    candidate_seconds = [value for value in candidate_seconds if value == value]
    late_candidate_count = sum(1 for value in candidate_seconds if value <= 90)
    unknown_regime_count = market_regime_counts.get("UNKNOWN", 0)
    probability_coverage = len(probability_records) / len(records) if records else 0.0
    unknown_regime_share = unknown_regime_count / len(records) if records else 0.0
    if probability_coverage >= 0.5 and unknown_regime_share < 0.5 and candidate_records:
        phase2_readiness = "READY_FOR_PHASE_2_REPLAY_RESEARCH"
    elif probability_records:
        phase2_readiness = "PARTIAL_PHASE_2_SIGNAL"
    else:
        phase2_readiness = "INSUFFICIENT_DIAGNOSTIC_COVERAGE"

    dominant_blocked_bucket = ""
    blocked_bucket_counts = {
        bucket: stats["blocked_candidates"]
        for bucket, stats in probability_buckets.items()
        if stats.get("blocked_candidates", 0)
    }
    if blocked_bucket_counts:
        dominant_blocked_bucket = max(blocked_bucket_counts.items(), key=lambda item: item[1])[0]

    return {
        "events_counted": int(len(records)),
        "events_with_probability_fields": int(len(probability_records)),
        "events_with_indicator_evidence": int(sum(1 for record in records if record.get("indicator_evidence_keys"))),
        "market_regimes": [[label, count] for label, count in market_regime_counts.most_common()],
        "skip_decisions_by_regime": dict(skip_by_regime.most_common()),
        "enter_candidates_by_regime": dict(enter_by_regime.most_common()),
        "probability_buckets": probability_buckets,
        "blocked_candidates_by_probability_bucket": [[label, count] for label, count in sorted(blocked_bucket_counts.items())],
        "dominant_blocked_probability_bucket": dominant_blocked_bucket,
        "skip_reasons_by_regime": {
            regime: [[reason, count] for reason, count in reasons.most_common(5)]
            for regime, reasons in sorted(skip_reason_by_regime.items())
        },
        "candidate_timing_by_regime": {
            regime: _summarize_timing_records(group)
            for regime, group in sorted(candidate_timing_by_regime.items())
        },
        "compression_no_entry_correlation": {
            "events_with_compression_score": int(len(compression_skip) + len(compression_enter)),
            "blocked_candidates_with_compression": int(len(compression_skip)),
            "high_compression_blocked_count": int(len(high_compression_skips)),
            "high_compression_blocked_share": round(len(high_compression_skips) / len(compression_skip), 4) if compression_skip else 0.0,
            "avg_compression_score_blocked": _average(compression_skip),
            "avg_compression_score_enter": _average(compression_enter),
        },
        "reversal_defensive_skip_correlation": {
            "defensive_skip_count": int(len(defensive_skip_records)),
            "high_reversal_defensive_skip_count": int(len(high_reversal_defensive)),
            "high_reversal_defensive_skip_share": round(len(high_reversal_defensive) / len(defensive_skip_records), 4) if defensive_skip_records else 0.0,
        },
        "candidate_cutoff_timing": {
            "candidate_events_with_seconds_remaining": int(len(candidate_seconds)),
            "late_candidate_count": int(late_candidate_count),
            "late_candidate_share": round(late_candidate_count / len(candidate_seconds), 4) if candidate_seconds else 0.0,
            "closest_candidate_seconds_remaining": round(min(candidate_seconds), 2) if candidate_seconds else None,
            "diagnosis": (
                "CANDIDATES_TOO_CLOSE_TO_CUTOFF"
                if candidate_seconds and late_candidate_count / len(candidate_seconds) >= 0.5
                else "CANDIDATE_TIMING_MIXED_OR_EARLY"
                if candidate_seconds
                else "INSUFFICIENT_TIMING_DATA"
            ),
        },
        "diagnostic_usefulness_for_inventory_replay": phase2_readiness,
        "research_questions": {
            "most_skip_regime": skip_by_regime.most_common(1)[0][0] if skip_by_regime else "",
            "most_enter_candidate_regime": enter_by_regime.most_common(1)[0][0] if enter_by_regime else "",
            "blocked_probability_bucket": dominant_blocked_bucket,
            "compression_correlates_with_no_entry": bool(compression_skip and len(high_compression_skips) / len(compression_skip) >= 0.5),
            "reversal_risk_explains_defensive_skips": bool(defensive_skip_records and len(high_reversal_defensive) / len(defensive_skip_records) >= 0.5),
            "candidates_too_close_to_cutoff": bool(candidate_seconds and late_candidate_count / len(candidate_seconds) >= 0.5),
            "phase2_inventory_replay_useful": phase2_readiness,
        },
        "indicator_evidence": {
            "events_with_indicator_evidence": int(sum(1 for record in records if record.get("indicator_evidence_keys"))),
            "top_indicator_keys": [[label, count] for label, count in indicator_keys.most_common(10)],
        },
    }


def _load_regime_probability_summary_from_events(
    *,
    base_dir: str | Path,
    date: str,
    time_filter: dict[str, Any],
) -> dict[str, Any]:
    try:
        events, _bad_lines = load_replay_events(
            base_dir=base_dir,
            date_from=date,
            date_to=date,
            since_utc=time_filter.get("since_utc"),
            until_utc=time_filter.get("until_utc"),
            run_id=time_filter.get("run_id"),
        )
    except Exception:
        return {}

    records: list[dict[str, Any]] = []
    for event in events:
        record = _phase_probability_record(event)
        if record is not None:
            records.append(record)
    return _summarize_regime_probability_records(records)


def _load_regime_summary_from_events(
    *,
    base_dir: str | Path,
    date: str,
    time_filter: dict[str, Any],
) -> dict[str, Any]:
    try:
        events, _bad_lines = load_replay_events(
            base_dir=base_dir,
            date_from=date,
            date_to=date,
            since_utc=time_filter.get("since_utc"),
            until_utc=time_filter.get("until_utc"),
            run_id=time_filter.get("run_id"),
        )
    except Exception:
        return {}

    volatility_counts: Counter[str] = Counter()
    trend_counts: Counter[str] = Counter()
    events_counted = 0
    for event in events:
        event_type = str(event.get("event_type", "") or "")
        category = str(event.get("_category", "") or "")
        if event_type not in REGIME_EVENT_TYPES and category not in REGIME_CATEGORIES:
            continue
        payload = _payload_from_event(event)
        events_counted += 1
        volatility_counts[_regime_value_from_payload(payload, "volatility_regime")] += 1
        trend_counts[_regime_value_from_payload(payload, "trend_regime")] += 1

    if not events_counted:
        return {}
    return {
        "events_counted": events_counted,
        "volatility_regimes": [[name, count] for name, count in volatility_counts.most_common()],
        "trend_regimes": [[name, count] for name, count in trend_counts.most_common()],
    }


def _is_cutoff_payload(payload: dict[str, Any]) -> bool:
    raw_reason = str(
        _payload_value(payload, "normalized_skip_reason", "raw_skip_reason", "skip_reason")
        or ""
    )
    if normalize_skip_reason(raw_reason) == "time_unsafe":
        return True
    cutoff_seconds = _payload_value(payload, "cutoff_block_seconds_remaining")
    if cutoff_seconds is not None and str(cutoff_seconds).strip():
        return True
    if _as_bool(_payload_value(payload, "late_entry_hard_block")):
        return True
    if str(_payload_value(payload, "micro_timing_denied_reason") or "").strip():
        return True
    if str(_payload_value(payload, "adaptive_cutoff_denied_reason") or "").strip():
        return True
    return False


def _record_cutoff_regime_group(group: dict[str, Any], payload: dict[str, Any]) -> None:
    group["blocks"] += 1
    seconds_remaining = _payload_value(payload, "seconds_remaining", "seconds_until_close")
    if seconds_remaining is not None:
        group["seconds_remaining_values"].append(_as_float(seconds_remaining))
    decision_latency = _payload_value(payload, "decision_latency_ms")
    if decision_latency is not None:
        group["decision_latency_values"].append(_as_float(decision_latency))
    micro_reason = str(_payload_value(payload, "micro_timing_denied_reason") or "").strip()
    if micro_reason:
        group["micro_deny_reasons"][micro_reason] += 1


def _blocked_side(payload: dict[str, Any]) -> str:
    for key in ("outcome", "side", "best_side"):
        value = str(_payload_value(payload, key) or "").upper()
        if value in {"YES", "NO"}:
            return value
    return ""


def _market_key(payload: dict[str, Any]) -> str:
    market_id = str(_payload_value(payload, "market_id") or "").strip()
    if market_id:
        return f"market:{market_id}"
    ticker = str(_payload_value(payload, "ticker", "asset") or "").strip().upper()
    epoch = str(_payload_value(payload, "market_epoch_start", "epoch_start", "epoch_start_ts") or "").strip()
    if ticker and epoch:
        return f"{ticker}:{epoch}"
    return ticker


def _probability_for_side(payload: dict[str, Any], side: str) -> float | None:
    keys = (
        ("yes_mid", "p_yes", "yes_ask")
        if side == "YES"
        else ("no_mid", "p_no", "no_ask")
    )
    for key in keys:
        value = _payload_value(payload, key)
        if value is None:
            continue
        probability = _as_float(value, default=-1.0)
        if 0.0 <= probability <= 1.0:
            return probability
    ask_price = _payload_value(payload, "ask_price", "entry_price")
    if ask_price is not None:
        probability = _as_float(ask_price, default=-1.0)
        if 0.0 <= probability <= 1.0:
            return probability
    return None


def _snapshot_record(event: dict[str, Any]) -> dict[str, Any] | None:
    payload = _payload_from_event(event)
    timestamp = _parse_event_timestamp(event.get("timestamp_utc"))
    key = _market_key(payload)
    if timestamp is None or not key:
        return None
    return {"timestamp": timestamp, "payload": payload}


def _empty_late_opportunity_group() -> dict[str, Any]:
    return {
        "blocks": 0,
        "priced_blocks": 0,
        "missing_price_data_blocks": 0,
        "unknown_side_blocks": 0,
        "favorable_moves": [],
        "adverse_moves": [],
        "reached_plus_0_05": 0,
        "reached_plus_0_10": 0,
        "reached_plus_0_20": 0,
        "adverse_instead_count": 0,
    }


def _record_late_opportunity(
    group: dict[str, Any],
    *,
    block_payload: dict[str, Any],
    block_timestamp: datetime | None,
    future_snapshots: list[dict[str, Any]],
) -> None:
    group["blocks"] += 1
    side = _blocked_side(block_payload)
    if not side:
        group["unknown_side_blocks"] += 1
        group["missing_price_data_blocks"] += 1
        return
    start_probability = _probability_for_side(block_payload, side)
    if start_probability is None:
        group["missing_price_data_blocks"] += 1
        return

    future_probabilities: list[float] = []
    block_seconds = _as_float(_payload_value(block_payload, "seconds_remaining", "seconds_until_close"), default=0.0)
    for snapshot in future_snapshots:
        if block_timestamp is not None and snapshot["timestamp"] <= block_timestamp:
            continue
        snapshot_payload = snapshot["payload"]
        snapshot_seconds = _payload_value(snapshot_payload, "seconds_remaining", "seconds_until_close")
        if snapshot_seconds is not None and _as_float(snapshot_seconds, default=999.0) > block_seconds:
            continue
        probability = _probability_for_side(snapshot_payload, side)
        if probability is not None:
            future_probabilities.append(probability)

    if not future_probabilities:
        group["missing_price_data_blocks"] += 1
        return

    max_favorable_move = max(max(future_probabilities) - start_probability, 0.0)
    max_adverse_move = max(start_probability - min(future_probabilities), 0.0)
    group["priced_blocks"] += 1
    group["favorable_moves"].append(max_favorable_move)
    group["adverse_moves"].append(max_adverse_move)
    if max_favorable_move >= 0.05:
        group["reached_plus_0_05"] += 1
    if max_favorable_move >= 0.10:
        group["reached_plus_0_10"] += 1
    if max_favorable_move >= 0.20:
        group["reached_plus_0_20"] += 1
    if max_adverse_move > max_favorable_move:
        group["adverse_instead_count"] += 1


def _summarize_late_opportunity_groups(groups: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for label, group in sorted(groups.items()):
        favorable_moves = group["favorable_moves"]
        adverse_moves = group["adverse_moves"]
        summary[label] = {
            "blocks": int(group["blocks"]),
            "priced_blocks": int(group["priced_blocks"]),
            "missing_price_data_blocks": int(group["missing_price_data_blocks"]),
            "unknown_side_blocks": int(group["unknown_side_blocks"]),
            "avg_max_favorable_move": round(sum(favorable_moves) / len(favorable_moves), 4) if favorable_moves else 0.0,
            "max_favorable_move": round(max(favorable_moves), 4) if favorable_moves else 0.0,
            "avg_max_adverse_move": round(sum(adverse_moves) / len(adverse_moves), 4) if adverse_moves else 0.0,
            "max_adverse_move": round(max(adverse_moves), 4) if adverse_moves else 0.0,
            "reached_plus_0_05": int(group["reached_plus_0_05"]),
            "reached_plus_0_10": int(group["reached_plus_0_10"]),
            "reached_plus_0_20": int(group["reached_plus_0_20"]),
            "adverse_instead_count": int(group["adverse_instead_count"]),
        }
    return summary


def _late_window_regime_strength(
    *,
    label: str,
    group: dict[str, Any],
    move_key: str,
) -> dict[str, Any]:
    return {
        "regime": label,
        "priced_blocks": int(group.get("priced_blocks", 0)),
        "max_favorable_move": _as_float(group.get("max_favorable_move")),
        "max_adverse_move": _as_float(group.get("max_adverse_move")),
        "reached_plus_0_05": _as_int(group.get("reached_plus_0_05")),
        "adverse_instead_count": _as_int(group.get("adverse_instead_count")),
        "score": _as_float(group.get(move_key)),
    }


def _summarize_late_window_interpretation(
    combo_summary: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    total_blocks = sum(_as_int(group.get("blocks")) for group in combo_summary.values())
    total_priced = sum(_as_int(group.get("priced_blocks")) for group in combo_summary.values())
    total_missing = sum(_as_int(group.get("missing_price_data_blocks")) for group in combo_summary.values())
    positive_regimes = [
        label
        for label, group in sorted(combo_summary.items())
        if _as_int(group.get("reached_plus_0_05")) > 0
    ]
    adverse_regimes = [
        label
        for label, group in sorted(combo_summary.items())
        if _as_int(group.get("adverse_instead_count")) > 0
    ]

    missed_candidates = {
        label: group
        for label, group in combo_summary.items()
        if _as_int(group.get("reached_plus_0_05")) > 0
    }
    protective_candidates = {
        label: group
        for label, group in combo_summary.items()
        if _as_int(group.get("adverse_instead_count")) > 0
    }
    strongest_missed = (
        max(
            missed_candidates.items(),
            key=lambda item: (
                _as_float(item[1].get("max_favorable_move")),
                _as_int(item[1].get("reached_plus_0_05")),
                _as_int(item[1].get("priced_blocks")),
            ),
        )
        if missed_candidates
        else None
    )
    strongest_protective = (
        max(
            protective_candidates.items(),
            key=lambda item: (
                _as_float(item[1].get("max_adverse_move")),
                _as_int(item[1].get("adverse_instead_count")),
                _as_int(item[1].get("priced_blocks")),
            ),
        )
        if protective_candidates
        else None
    )

    if total_blocks == 0:
        diagnosis = "NO_LATE_WINDOW_SAMPLE"
    elif total_priced == 0 or total_missing > total_priced:
        diagnosis = "INSUFFICIENT_PRICE_DATA"
    elif positive_regimes and adverse_regimes:
        diagnosis = "MIXED_REGIME_DEPENDENT"
    elif positive_regimes:
        diagnosis = "CUTOFF_MISSED_OPPORTUNITY"
    else:
        diagnosis = "CUTOFF_PROTECTED_CAPITAL"

    return {
        "total_late_window_blocks": int(total_blocks),
        "total_priced_blocks": int(total_priced),
        "total_missing_price_data_blocks": int(total_missing),
        "regimes_with_positive_followthrough": positive_regimes,
        "regimes_with_adverse_followthrough": adverse_regimes,
        "strongest_missed_opportunity_regime": (
            _late_window_regime_strength(
                label=strongest_missed[0],
                group=strongest_missed[1],
                move_key="max_favorable_move",
            )
            if strongest_missed
            else None
        ),
        "strongest_protective_cutoff_regime": (
            _late_window_regime_strength(
                label=strongest_protective[0],
                group=strongest_protective[1],
                move_key="max_adverse_move",
            )
            if strongest_protective
            else None
        ),
        "late_window_diagnosis": diagnosis,
    }


def _empty_cutoff_regime_group() -> dict[str, Any]:
    return {
        "blocks": 0,
        "seconds_remaining_values": [],
        "decision_latency_values": [],
        "micro_deny_reasons": Counter(),
    }


def _summarize_cutoff_regime_groups(groups: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for label, group in sorted(groups.items()):
        seconds_values = group["seconds_remaining_values"]
        latency_values = group["decision_latency_values"]
        summary[label] = {
            "blocks": int(group["blocks"]),
            "avg_seconds_remaining": round(sum(seconds_values) / len(seconds_values), 2) if seconds_values else 0.0,
            "min_seconds_remaining": round(min(seconds_values), 2) if seconds_values else 0.0,
            "avg_decision_latency_ms": round(sum(latency_values) / len(latency_values), 2) if latency_values else 0.0,
            "top_micro_deny_reasons": [
                [reason, count]
                for reason, count in group["micro_deny_reasons"].most_common(5)
            ],
        }
    return summary


def _load_cutoff_by_regime_from_events(
    *,
    base_dir: str | Path,
    date: str,
    time_filter: dict[str, Any],
) -> dict[str, Any]:
    try:
        events, _bad_lines = load_replay_events(
            base_dir=base_dir,
            date_from=date,
            date_to=date,
            since_utc=time_filter.get("since_utc"),
            until_utc=time_filter.get("until_utc"),
            run_id=time_filter.get("run_id"),
        )
    except Exception:
        return {}

    snapshots_by_market: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        event_type = str(event.get("event_type", "") or "")
        category = str(event.get("_category", "") or "")
        if event_type != "market_snapshot" and category != "market_snapshots":
            continue
        snapshot = _snapshot_record(event)
        if snapshot is None:
            continue
        snapshots_by_market.setdefault(_market_key(snapshot["payload"]), []).append(snapshot)
    for snapshots in snapshots_by_market.values():
        snapshots.sort(key=lambda item: item["timestamp"])

    by_volatility: dict[str, dict[str, Any]] = {}
    by_trend: dict[str, dict[str, Any]] = {}
    by_combo: dict[str, dict[str, Any]] = {}
    late_opportunity_by_combo: dict[str, dict[str, Any]] = {}
    events_counted = 0
    for event in events:
        event_type = str(event.get("event_type", "") or "")
        category = str(event.get("_category", "") or "")
        if event_type != "decision" and category != "decision_log":
            continue
        payload = _payload_from_event(event)
        if not _is_cutoff_payload(payload):
            continue
        events_counted += 1
        volatility = _regime_value_from_payload(payload, "volatility_regime")
        trend = _regime_value_from_payload(payload, "trend_regime")
        combo = f"{trend}+{volatility}"
        _record_cutoff_regime_group(by_volatility.setdefault(volatility, _empty_cutoff_regime_group()), payload)
        _record_cutoff_regime_group(by_trend.setdefault(trend, _empty_cutoff_regime_group()), payload)
        _record_cutoff_regime_group(by_combo.setdefault(combo, _empty_cutoff_regime_group()), payload)
        seconds_remaining = _as_float(_payload_value(payload, "seconds_remaining", "seconds_until_close"), default=0.0)
        if 1.0 <= seconds_remaining <= 45.0:
            _record_late_opportunity(
                late_opportunity_by_combo.setdefault(combo, _empty_late_opportunity_group()),
                block_payload=payload,
                block_timestamp=_parse_event_timestamp(event.get("timestamp_utc")),
                future_snapshots=snapshots_by_market.get(_market_key(payload), []),
            )

    late_opportunity_combo = _summarize_late_opportunity_groups(late_opportunity_by_combo)
    return {
        "events_counted": events_counted,
        "volatility_regime": _summarize_cutoff_regime_groups(by_volatility),
        "trend_regime": _summarize_cutoff_regime_groups(by_trend),
        "combo": _summarize_cutoff_regime_groups(by_combo),
        "late_window_opportunity": {
            "seconds_remaining_min": 1,
            "seconds_remaining_max": 45,
            "probability_move_thresholds": [0.05, 0.10, 0.20],
            **_summarize_late_window_interpretation(late_opportunity_combo),
            "combo": late_opportunity_combo,
        },
    }


def _candidate_timing_bucket(seconds_remaining: Any) -> str:
    seconds = _as_float(seconds_remaining, default=-1.0)
    if seconds < 0:
        return "unknown"
    if seconds >= 180:
        return "180s+"
    if seconds >= 120:
        return "120-180s"
    if seconds >= 90:
        return "90-120s"
    if seconds >= 45:
        return "45-90s"
    return "<45s"


def _candidate_side_from_payload(payload: dict[str, Any]) -> str:
    for key in ("best_candidate_side", "best_side", "side", "outcome"):
        value = str(_payload_value(payload, key) or "").strip().upper()
        if value in {"YES", "NO"}:
            return value
    return ""


def _first_candidate_float(payload: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = _payload_value(payload, key)
        if value is None:
            continue
        parsed = _as_float(value, default=float("nan"))
        if parsed == parsed:
            return parsed
    return None


def _gap_to_threshold(value: float | None, threshold: float | None) -> float | None:
    if value is None or threshold is None:
        return None
    return round(threshold - value, 6)


def _spread_gap_to_limit(spread: float | None, limit: float | None) -> float | None:
    if spread is None:
        return None
    if limit is None:
        limit = 0.10
    return round(spread - limit, 6)


def _candidate_gap_record(event: dict[str, Any]) -> dict[str, Any] | None:
    payload = _payload_from_event(event)
    if not payload:
        return None
    seconds_remaining = _payload_value(payload, "seconds_remaining", "seconds_until_close", "time_remaining_seconds")
    effective_cutoff = _payload_value(payload, "effective_cutoff_seconds", "entry_cutoff_seconds")
    if effective_cutoff is None:
        effective_cutoff = 90

    raw_reason = str(_payload_value(payload, "normalized_skip_reason", "raw_skip_reason", "skip_reason") or "")
    normalized_reason = normalize_skip_reason(raw_reason)
    ev = _first_candidate_float(payload, "ev", "edge", "model_ev", "expected_value")
    ev_threshold = _first_candidate_float(payload, "ev_threshold", "min_ev", "min_ev_required", "required_ev", "minimum_ev")
    confidence = _first_candidate_float(payload, "confidence", "confidence_score")
    confidence_threshold = _first_candidate_float(
        payload,
        "confidence_threshold",
        "min_confidence",
        "minimum_confidence",
        "min_confidence_required",
        "confidence_required",
    )
    spread = _first_candidate_float(payload, "spread", "orderbook_spread", "ob_spread")
    spread_limit = _first_candidate_float(payload, "spread_limit", "max_spread", "max_allowed_spread", "max_orderbook_spread")
    liquidity_state_raw = _payload_value(payload, "liquidity_state")
    liquidity_state = str(liquidity_state_raw or "").strip().upper()
    side = _candidate_side_from_payload(payload)
    seconds = _as_float(seconds_remaining, default=-1.0)
    cutoff = _as_float(effective_cutoff, default=90.0)
    if not any(value is not None for value in (ev, ev_threshold, confidence, confidence_threshold, spread)) and not side and not normalized_reason:
        return None

    ev_gap = _first_candidate_float(payload, "ev_gap_to_threshold")
    if ev_gap is None:
        ev_gap = _gap_to_threshold(ev, ev_threshold)
    confidence_gap = _first_candidate_float(payload, "confidence_gap_to_threshold")
    if confidence_gap is None:
        confidence_gap = _gap_to_threshold(confidence, confidence_threshold)
    spread_gap = _first_candidate_float(payload, "spread_gap_to_limit")
    if spread_gap is None:
        spread_gap = _spread_gap_to_limit(spread, spread_limit)

    return {
        "timestamp_utc": str(event.get("timestamp_utc", "") or ""),
        "market_id": str(_payload_value(payload, "market_id") or ""),
        "ticker": str(_payload_value(payload, "ticker", "asset") or ""),
        "timing_bucket": _candidate_timing_bucket(seconds_remaining),
        "seconds_remaining": seconds if seconds >= 0 else None,
        "entry_cutoff_seconds": cutoff,
        "before_cutoff": seconds > cutoff if seconds >= 0 else False,
        "is_cutoff_block": _is_cutoff_payload(payload) or (seconds >= 0 and seconds <= cutoff),
        "best_candidate_side": side,
        "ev_gap_to_threshold": ev_gap,
        "confidence_gap_to_threshold": confidence_gap,
        "spread_gap_to_limit": spread_gap,
        "liquidity_state": liquidity_state,
        "volatility_regime": _regime_value_from_payload(payload, "volatility_regime"),
        "trend_regime": _regime_value_from_payload(payload, "trend_regime"),
        "final_pre_cutoff_block_reason": normalized_reason or raw_reason,
    }


def _candidate_gap_types(record: dict[str, Any]) -> list[str]:
    reason = str(record.get("final_pre_cutoff_block_reason", "") or "").lower()
    gap_types: list[str] = []
    if _as_float(record.get("ev_gap_to_threshold"), default=0.0) > 0 or reason == "ev_below_threshold":
        gap_types.append("EV_TOO_LOW")
    if _as_float(record.get("confidence_gap_to_threshold"), default=0.0) > 0 or reason == "confidence_too_low":
        gap_types.append("CONFIDENCE_TOO_LOW")
    if _as_float(record.get("spread_gap_to_limit"), default=0.0) > 0 or reason == "spread_too_wide":
        gap_types.append("SPREAD_TOO_WIDE")
    liquidity_state = str(record.get("liquidity_state", "") or "").upper()
    if (
        liquidity_state in LIQUIDITY_NOT_READY_STATES
        or reason in {"orderbook_unavailable", "no_orderbook", "stale_data", "liquidity_too_low"}
    ):
        gap_types.append("LIQUIDITY_NOT_READY")
    if reason in {"delta_extreme", "scanner_no_best_trade", "no_signal"} or "probability_model" in reason:
        gap_types.append("REGIME_NO_EDGE")
    return gap_types


def _candidate_quality_score(record: dict[str, Any]) -> tuple[float, float, float]:
    gaps = [
        max(_as_float(record.get("ev_gap_to_threshold"), default=0.0), 0.0),
        max(_as_float(record.get("confidence_gap_to_threshold"), default=0.0), 0.0),
        max(_as_float(record.get("spread_gap_to_limit"), default=0.0), 0.0),
    ]
    return (max(gaps), sum(gaps), -_as_float(record.get("seconds_remaining"), default=0.0))


def _candidate_has_enough_threshold_data(record: dict[str, Any]) -> bool:
    known = sum(
        record.get(key) is not None
        for key in ("ev_gap_to_threshold", "confidence_gap_to_threshold", "spread_gap_to_limit")
    )
    return known >= 2 or bool(_candidate_gap_types(record))


def _candidate_is_passable(record: dict[str, Any]) -> bool:
    if not _candidate_has_enough_threshold_data(record):
        return False
    if _candidate_gap_types(record):
        return False
    return bool(record.get("best_candidate_side"))


def _compact_candidate_record(record: dict[str, Any] | None) -> dict[str, Any] | None:
    if not record:
        return None
    return {
        "timestamp_utc": record.get("timestamp_utc", ""),
        "market_id": record.get("market_id", ""),
        "ticker": record.get("ticker", ""),
        "timing_bucket": record.get("timing_bucket", "unknown"),
        "best_candidate_side": record.get("best_candidate_side", ""),
        "ev_gap_to_threshold": record.get("ev_gap_to_threshold"),
        "confidence_gap_to_threshold": record.get("confidence_gap_to_threshold"),
        "spread_gap_to_limit": record.get("spread_gap_to_limit"),
        "liquidity_state": record.get("liquidity_state", "UNKNOWN"),
        "volatility_regime": record.get("volatility_regime", "UNKNOWN"),
        "trend_regime": record.get("trend_regime", "UNKNOWN"),
        "final_pre_cutoff_block_reason": record.get("final_pre_cutoff_block_reason", ""),
        "seconds_remaining": record.get("seconds_remaining"),
    }


def _summarize_candidate_gap_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    pre_cutoff = [record for record in records if record.get("before_cutoff")]
    cutoff_or_late = [record for record in records if record.get("is_cutoff_block")]
    timing_counts: Counter[str] = Counter(str(record.get("timing_bucket") or "unknown") for record in records)
    gap_counts: Counter[str] = Counter()
    for record in pre_cutoff:
        gap_counts.update(_candidate_gap_types(record))

    closest = min(pre_cutoff, key=_candidate_quality_score) if pre_cutoff else None
    final_pre_cutoff = (
        max(
            pre_cutoff,
            key=lambda record: _parse_event_timestamp(str(record.get("timestamp_utc") or "")) or datetime.min.replace(tzinfo=timezone.utc),
        )
        if pre_cutoff
        else None
    )
    dominant_gap = gap_counts.most_common(1)[0][0] if gap_counts else ""

    if not records or not any(_candidate_has_enough_threshold_data(record) for record in records):
        diagnosis = "INSUFFICIENT_CANDIDATE_DATA"
    elif pre_cutoff and closest and _candidate_is_passable(closest) and cutoff_or_late:
        diagnosis = "CUTOFF_TOO_STRICT"
    elif not pre_cutoff and cutoff_or_late:
        diagnosis = "CANDIDATE_TOO_LATE"
    elif dominant_gap in CANDIDATE_GAP_DIAGNOSES:
        diagnosis = dominant_gap
    else:
        diagnosis = "REGIME_NO_EDGE"

    if diagnosis == "CUTOFF_TOO_STRICT":
        cutoff_interpretation = "ROOT_CAUSE"
    elif diagnosis in {"CANDIDATE_TOO_LATE", "INSUFFICIENT_CANDIDATE_DATA"}:
        cutoff_interpretation = "UNKNOWN"
    else:
        cutoff_interpretation = "FINAL_SYMPTOM"

    closest_compact = _compact_candidate_record(closest)
    return {
        "events_counted": int(len(records)),
        "pre_cutoff_candidate_count": int(len(pre_cutoff)),
        "cutoff_or_late_candidate_count": int(len(cutoff_or_late)),
        "avg_seconds_remaining_at_candidate": round(
            sum(_as_float(record.get("seconds_remaining")) for record in records if record.get("seconds_remaining") is not None)
            / max(1, sum(1 for record in records if record.get("seconds_remaining") is not None)),
            2,
        ) if records else 0.0,
        "closest_valid_candidate_seconds_remaining": (
            _as_float(closest.get("seconds_remaining"))
            if closest and _candidate_is_passable(closest)
            else None
        ),
        "dominant_gap_type": dominant_gap or diagnosis,
        "candidate_gap_diagnosis": diagnosis,
        "cutoff_interpretation": cutoff_interpretation,
        "closest_candidate_bucket": (closest_compact or {}).get("timing_bucket", ""),
        "seconds_remaining_at_closest_candidate": (closest_compact or {}).get("seconds_remaining"),
        "final_pre_cutoff_block_reason": (
            str(final_pre_cutoff.get("final_pre_cutoff_block_reason", "") or "")
            if final_pre_cutoff
            else ""
        ),
        "timing_bucket_counts": dict(timing_counts),
        "gap_type_counts": dict(gap_counts.most_common()),
        "closest_candidate_before_cutoff": closest_compact,
    }


def _load_candidate_gap_summary_from_events(
    *,
    base_dir: str | Path,
    date: str,
    time_filter: dict[str, Any],
) -> dict[str, Any]:
    try:
        events, _bad_lines = load_replay_events(
            base_dir=base_dir,
            date_from=date,
            date_to=date,
            since_utc=time_filter.get("since_utc"),
            until_utc=time_filter.get("until_utc"),
            run_id=time_filter.get("run_id"),
        )
    except Exception:
        return {}

    records: list[dict[str, Any]] = []
    for event in events:
        event_type = str(event.get("event_type", "") or "")
        category = str(event.get("_category", "") or "")
        if event_type != "decision" and category != "decision_log":
            continue
        record = _candidate_gap_record(event)
        if record is not None:
            records.append(record)
    return _summarize_candidate_gap_records(records)


def _spread_market_key(payload: dict[str, Any]) -> str:
    key = _market_key(payload)
    if key:
        return key
    ticker = str(_payload_value(payload, "ticker", "asset") or "").strip().upper()
    return ticker or "UNKNOWN"


def _spread_record(event: dict[str, Any]) -> dict[str, Any] | None:
    payload = _payload_from_event(event)
    if not payload:
        return None
    spread = _first_candidate_float(payload, "spread", "orderbook_spread", "ob_spread")
    if spread is None or spread < 0:
        return None
    timestamp = _parse_event_timestamp(event.get("timestamp_utc"))
    seconds_remaining = _payload_value(payload, "seconds_remaining", "seconds_until_close", "time_remaining_seconds")
    effective_cutoff = _payload_value(payload, "effective_cutoff_seconds", "entry_cutoff_seconds")
    if effective_cutoff is None:
        effective_cutoff = 90
    cutoff = _as_float(effective_cutoff, default=90.0)
    seconds = _as_float(seconds_remaining, default=-1.0)
    spread_limit = _first_candidate_float(payload, "spread_limit", "max_spread", "max_allowed_spread", "max_orderbook_spread")
    if spread_limit is None:
        spread_limit = 0.10
    spread_gap = _first_candidate_float(payload, "spread_gap_to_limit")
    if spread_gap is None:
        spread_gap = _spread_gap_to_limit(spread, spread_limit)
    event_type = str(event.get("event_type", "") or "")
    category = str(event.get("_category", "") or "")
    source = "market_snapshot" if event_type == "market_snapshot" or category == "market_snapshots" else "decision"
    return {
        "timestamp_utc": str(event.get("timestamp_utc", "") or ""),
        "timestamp": timestamp,
        "source": source,
        "market_key": _spread_market_key(payload),
        "market_id": str(_payload_value(payload, "market_id") or ""),
        "ticker": str(_payload_value(payload, "ticker", "asset") or ""),
        "timing_bucket": _candidate_timing_bucket(seconds_remaining),
        "seconds_remaining": seconds if seconds >= 0 else None,
        "entry_cutoff_seconds": cutoff,
        "before_cutoff": seconds > cutoff if seconds >= 0 else False,
        "spread": round(float(spread), 6),
        "spread_limit": round(float(spread_limit), 6),
        "spread_gap_to_limit": spread_gap,
        "spread_normalized": bool(spread_gap is not None and spread_gap <= 0),
        "best_candidate_side": _candidate_side_from_payload(payload),
        "final_pre_cutoff_block_reason": str(
            _payload_value(payload, "normalized_skip_reason", "raw_skip_reason", "skip_reason") or ""
        ),
        "liquidity_state": str(_payload_value(payload, "liquidity_state") or "").strip().upper(),
        "volatility_regime": _regime_value_from_payload(payload, "volatility_regime"),
        "trend_regime": _regime_value_from_payload(payload, "trend_regime"),
    }


def _summarize_spread_group(records: list[dict[str, Any]]) -> dict[str, Any]:
    gaps = [_as_float(record.get("spread_gap_to_limit")) for record in records if record.get("spread_gap_to_limit") is not None]
    spreads = [_as_float(record.get("spread")) for record in records if record.get("spread") is not None]
    normalized = [record for record in records if record.get("spread_normalized")]
    return {
        "events": int(len(records)),
        "normalized_events": int(len(normalized)),
        "recovery_rate": round(len(normalized) / len(records), 4) if records else 0.0,
        "avg_spread": round(sum(spreads) / len(spreads), 6) if spreads else 0.0,
        "avg_spread_gap": round(sum(gaps) / len(gaps), 6) if gaps else 0.0,
        "min_spread_gap": round(min(gaps), 6) if gaps else 0.0,
        "max_spread_gap": round(max(gaps), 6) if gaps else 0.0,
    }


def _spread_group_summaries(records: list[dict[str, Any]], key_func) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(str(key_func(record) or "UNKNOWN"), []).append(record)
    return {
        label: _summarize_spread_group(group)
        for label, group in sorted(grouped.items())
    }


def _spread_velocity(records: list[dict[str, Any]]) -> tuple[float, dict[str, float]]:
    velocities: list[float] = []
    regime_velocities: dict[str, list[float]] = {}
    by_market: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        if record.get("timestamp") is None:
            continue
        by_market.setdefault(str(record.get("market_key") or "UNKNOWN"), []).append(record)
    for market_records in by_market.values():
        market_records.sort(key=lambda record: record["timestamp"])
        for previous, current in zip(market_records, market_records[1:]):
            delta_seconds = (current["timestamp"] - previous["timestamp"]).total_seconds()
            if delta_seconds <= 0:
                continue
            velocity = (_as_float(previous.get("spread")) - _as_float(current.get("spread"))) / delta_seconds
            velocities.append(velocity)
            combo = f"{current.get('trend_regime', 'UNKNOWN')}+{current.get('volatility_regime', 'UNKNOWN')}"
            regime_velocities.setdefault(combo, []).append(velocity)
    avg_velocity = round(sum(velocities) / len(velocities), 6) if velocities else 0.0
    avg_by_regime = {
        label: round(sum(values) / len(values), 6)
        for label, values in sorted(regime_velocities.items())
        if values
    }
    return avg_velocity, avg_by_regime


def _spread_normalization_seconds(records: list[dict[str, Any]]) -> float | None:
    normalized = [
        record
        for record in records
        if record.get("spread_normalized") and record.get("seconds_remaining") is not None
    ]
    if not normalized:
        return None
    return round(max(_as_float(record.get("seconds_remaining")) for record in normalized), 2)


def _closest_spread_before_cutoff(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    pre_cutoff = [
        record
        for record in records
        if record.get("before_cutoff") and record.get("spread_gap_to_limit") is not None
    ]
    if not pre_cutoff:
        return None
    closest = min(pre_cutoff, key=lambda record: (abs(_as_float(record.get("spread_gap_to_limit"))), -_as_float(record.get("seconds_remaining"))))
    return {
        "timestamp_utc": closest.get("timestamp_utc", ""),
        "market_id": closest.get("market_id", ""),
        "ticker": closest.get("ticker", ""),
        "timing_bucket": closest.get("timing_bucket", ""),
        "seconds_remaining": closest.get("seconds_remaining"),
        "spread": closest.get("spread"),
        "spread_limit": closest.get("spread_limit"),
        "spread_gap_to_limit": closest.get("spread_gap_to_limit"),
        "spread_normalized": closest.get("spread_normalized"),
        "volatility_regime": closest.get("volatility_regime", "UNKNOWN"),
        "trend_regime": closest.get("trend_regime", "UNKNOWN"),
    }


def _spread_timeline(records: list[dict[str, Any]], *, limit: int = 20) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    for record in sorted(records, key=lambda item: item.get("timestamp") or datetime.min.replace(tzinfo=timezone.utc)):
        timeline.append({
            "timestamp_utc": record.get("timestamp_utc", ""),
            "source": record.get("source", ""),
            "market_id": record.get("market_id", ""),
            "ticker": record.get("ticker", ""),
            "timing_bucket": record.get("timing_bucket", ""),
            "seconds_remaining": record.get("seconds_remaining"),
            "best_candidate_side": record.get("best_candidate_side", ""),
            "spread": record.get("spread"),
            "spread_gap_to_limit": record.get("spread_gap_to_limit"),
            "spread_normalized": record.get("spread_normalized"),
            "final_pre_cutoff_block_reason": record.get("final_pre_cutoff_block_reason", ""),
            "volatility_regime": record.get("volatility_regime", "UNKNOWN"),
            "trend_regime": record.get("trend_regime", "UNKNOWN"),
        })
    return timeline[:limit]


def _spread_compression_diagnosis(records: list[dict[str, Any]]) -> str:
    if not records:
        return "INSUFFICIENT_SPREAD_DATA"
    pre_cutoff = [record for record in records if record.get("before_cutoff")]
    normalized_pre_cutoff = [record for record in pre_cutoff if record.get("spread_normalized")]
    normalized_late = [record for record in records if record.get("spread_normalized") and not record.get("before_cutoff")]
    if not any(record.get("spread_gap_to_limit") is not None for record in records):
        return "INSUFFICIENT_SPREAD_DATA"
    regime_summary = _spread_group_summaries(records, lambda record: f"{record.get('trend_regime', 'UNKNOWN')}+{record.get('volatility_regime', 'UNKNOWN')}")
    regime_rates = {label: group.get("recovery_rate", 0.0) for label, group in regime_summary.items() if group.get("events", 0)}
    if len(regime_rates) >= 2 and max(regime_rates.values()) > 0 and min(regime_rates.values()) == 0:
        return "REGIME_DEPENDENT_SPREAD_BEHAVIOR"
    if normalized_pre_cutoff:
        return "SPREAD_RECOVERED_BEFORE_CUTOFF"
    if normalized_late:
        return "SPREAD_NORMALIZED_TOO_LATE"
    return "SPREAD_NEVER_NORMALIZED"


def _summarize_spread_compression_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    avg_velocity, avg_velocity_by_regime = _spread_velocity(records)
    spread_gap_by_timing_bucket = _spread_group_summaries(records, lambda record: record.get("timing_bucket", "unknown"))
    spread_gap_by_volatility = _spread_group_summaries(records, lambda record: record.get("volatility_regime", "UNKNOWN"))
    spread_gap_by_trend = _spread_group_summaries(records, lambda record: record.get("trend_regime", "UNKNOWN"))
    spread_gap_by_combo = _spread_group_summaries(records, lambda record: f"{record.get('trend_regime', 'UNKNOWN')}+{record.get('volatility_regime', 'UNKNOWN')}")
    normalized_count = sum(1 for record in records if record.get("spread_normalized"))
    pre_cutoff = [record for record in records if record.get("before_cutoff")]
    pre_cutoff_wide = [record for record in pre_cutoff if not record.get("spread_normalized")]
    pre_cutoff_normalized = [record for record in pre_cutoff if record.get("spread_normalized")]
    if not records:
        spread_state = "NO_SPREAD_DATA"
    elif pre_cutoff_normalized and pre_cutoff_wide:
        spread_state = "MIXED_PRE_CUTOFF"
    elif pre_cutoff_normalized:
        spread_state = "NORMALIZED_PRE_CUTOFF"
    elif pre_cutoff_wide:
        spread_state = "WIDE_PRE_CUTOFF"
    else:
        spread_state = "NO_PRE_CUTOFF_SPREAD"
    return {
        "events_counted": int(len(records)),
        "pre_cutoff_spread_events": int(len(pre_cutoff)),
        "normalized_spread_events": int(normalized_count),
        "avg_spread_velocity": avg_velocity,
        "avg_spread_velocity_by_combo_regime": avg_velocity_by_regime,
        "spread_normalization_seconds": _spread_normalization_seconds(records),
        "closest_spread_gap_before_cutoff": _closest_spread_before_cutoff(records),
        "spread_gap_by_timing_bucket": spread_gap_by_timing_bucket,
        "spread_gap_by_regime": {
            "volatility_regime": spread_gap_by_volatility,
            "trend_regime": spread_gap_by_trend,
            "combo_regime": spread_gap_by_combo,
        },
        "spread_recovery_rate": round(normalized_count / len(records), 4) if records else 0.0,
        "candidate_vs_spread_gap_timeline": _spread_timeline(records),
        "spread_state_before_cutoff": spread_state,
        "spread_compression_diagnosis": _spread_compression_diagnosis(records),
    }


def _load_spread_compression_summary_from_events(
    *,
    base_dir: str | Path,
    date: str,
    time_filter: dict[str, Any],
) -> dict[str, Any]:
    try:
        events, _bad_lines = load_replay_events(
            base_dir=base_dir,
            date_from=date,
            date_to=date,
            since_utc=time_filter.get("since_utc"),
            until_utc=time_filter.get("until_utc"),
            run_id=time_filter.get("run_id"),
        )
    except Exception:
        return {}

    records: list[dict[str, Any]] = []
    for event in events:
        event_type = str(event.get("event_type", "") or "")
        category = str(event.get("_category", "") or "")
        if event_type not in REGIME_EVENT_TYPES and category not in REGIME_CATEGORIES:
            continue
        record = _spread_record(event)
        if record is not None:
            records.append(record)
    return _summarize_spread_compression_records(records)


def _regime_combo(volatility: str, trend: str) -> str:
    return f"{volatility or 'UNKNOWN'}+{trend or 'UNKNOWN'}"


def _regime_replay_event(event: dict[str, Any]) -> dict[str, Any] | None:
    event_type = str(event.get("event_type", "") or "")
    category = str(event.get("_category", "") or "")
    if event_type not in REGIME_EVENT_TYPES and category not in REGIME_CATEGORIES:
        return None
    payload = _payload_from_event(event)
    if not payload:
        return None

    volatility = _regime_value_from_payload(payload, "volatility_regime")
    trend = _regime_value_from_payload(payload, "trend_regime")
    seconds_remaining = _payload_value(payload, "seconds_remaining", "seconds_until_close", "time_remaining_seconds")
    effective_cutoff = _payload_value(payload, "effective_cutoff_seconds", "entry_cutoff_seconds")
    cutoff = _as_float(effective_cutoff, default=90.0)
    seconds = _as_float(seconds_remaining, default=-1.0)
    candidate = _candidate_gap_record(event) if event_type == "decision" or category == "decision_log" else None
    spread = _spread_record(event)
    is_late_window = bool(_is_cutoff_payload(payload) and seconds >= 0 and seconds <= cutoff)
    if candidate is None and spread is None and not is_late_window:
        return None
    return {
        "timestamp_utc": str(event.get("timestamp_utc", "") or ""),
        "volatility_regime": volatility,
        "trend_regime": trend,
        "combo_regime": _regime_combo(volatility, trend),
        "timing_bucket": _candidate_timing_bucket(seconds_remaining),
        "seconds_remaining": seconds if seconds >= 0 else None,
        "candidate": candidate,
        "spread": spread,
        "late_window": is_late_window,
    }


def _regime_replay_group() -> dict[str, Any]:
    return {
        "events": 0,
        "candidate_events": 0,
        "spread_events": 0,
        "spread_normalized_events": 0,
        "spread_gap_values": [],
        "liquidity_ready_events": 0,
        "liquidity_not_ready_events": 0,
        "candidate_gap_counts": Counter(),
        "timing_bucket_counts": Counter(),
        "closest_candidate": None,
        "no_entry_events": 0,
        "late_window_blocks": 0,
    }


def _add_regime_replay_event(group: dict[str, Any], record: dict[str, Any]) -> None:
    group["events"] += 1
    group["timing_bucket_counts"][str(record.get("timing_bucket") or "unknown")] += 1
    if record.get("late_window"):
        group["late_window_blocks"] += 1

    candidate = record.get("candidate")
    if isinstance(candidate, dict):
        group["candidate_events"] += 1
        gap_types = _candidate_gap_types(candidate)
        group["candidate_gap_counts"].update(gap_types or ["NO_GAP_CLASSIFIED"])
        if gap_types or not _candidate_is_passable(candidate):
            group["no_entry_events"] += 1
        if "LIQUIDITY_NOT_READY" in gap_types:
            group["liquidity_not_ready_events"] += 1
        else:
            liquidity_state = str(candidate.get("liquidity_state", "") or "").upper()
            if liquidity_state and liquidity_state not in LIQUIDITY_NOT_READY_STATES:
                group["liquidity_ready_events"] += 1
        closest = group.get("closest_candidate")
        if closest is None or _candidate_quality_score(candidate) < _candidate_quality_score(closest):
            group["closest_candidate"] = candidate

    spread = record.get("spread")
    if isinstance(spread, dict):
        group["spread_events"] += 1
        if spread.get("spread_normalized"):
            group["spread_normalized_events"] += 1
        if spread.get("spread_gap_to_limit") is not None:
            group["spread_gap_values"].append(_as_float(spread.get("spread_gap_to_limit")))
        liquidity_state = str(spread.get("liquidity_state", "") or "").upper()
        if liquidity_state in LIQUIDITY_NOT_READY_STATES:
            group["liquidity_not_ready_events"] += 1
        elif liquidity_state:
            group["liquidity_ready_events"] += 1


def _regime_group_summary(group: dict[str, Any], *, event_share: float = 0.0, label: str = "") -> dict[str, Any]:
    candidate_events = _as_int(group.get("candidate_events"))
    spread_events = _as_int(group.get("spread_events"))
    liquidity_total = _as_int(group.get("liquidity_ready_events")) + _as_int(group.get("liquidity_not_ready_events"))
    gap_values = group.get("spread_gap_values", [])
    gap_counts = group.get("candidate_gap_counts", Counter())
    closest = _compact_candidate_record(group.get("closest_candidate"))
    recovery_rate = (
        round(_as_int(group.get("spread_normalized_events")) / spread_events, 4)
        if spread_events
        else 0.0
    )
    liquidity_not_ready_rate = (
        round(_as_int(group.get("liquidity_not_ready_events")) / liquidity_total, 4)
        if liquidity_total
        else 0.0
    )
    dominant_gap = gap_counts.most_common(1)[0][0] if gap_counts else ""
    classification = _classify_regime_tradeability(
        label=label,
        events=_as_int(group.get("events")),
        event_share=event_share,
        candidate_events=candidate_events,
        spread_events=spread_events,
        spread_recovery_rate=recovery_rate,
        liquidity_not_ready_rate=liquidity_not_ready_rate,
        dominant_gap=dominant_gap,
        closest_candidate_seconds=(closest or {}).get("seconds_remaining"),
    )
    return {
        "events": _as_int(group.get("events")),
        "event_share": round(event_share, 4),
        "candidate_events": candidate_events,
        "spread_events": spread_events,
        "spread_normalized_events": _as_int(group.get("spread_normalized_events")),
        "spread_recovery_rate": recovery_rate,
        "avg_spread_gap": round(sum(gap_values) / len(gap_values), 6) if gap_values else 0.0,
        "liquidity_ready_events": _as_int(group.get("liquidity_ready_events")),
        "liquidity_not_ready_events": _as_int(group.get("liquidity_not_ready_events")),
        "liquidity_not_ready_rate": liquidity_not_ready_rate,
        "candidate_gap_counts": dict(gap_counts.most_common()),
        "dominant_candidate_gap": dominant_gap,
        "timing_bucket_counts": dict(group.get("timing_bucket_counts", Counter()).most_common()),
        "closest_candidate_seconds": (closest or {}).get("seconds_remaining"),
        "closest_candidate_bucket": (closest or {}).get("timing_bucket", ""),
        "no_entry_events": _as_int(group.get("no_entry_events")),
        "late_window_blocks": _as_int(group.get("late_window_blocks")),
        "regime_tradeability_classification": classification,
    }


def _classify_regime_tradeability(
    *,
    label: str,
    events: int,
    event_share: float,
    candidate_events: int,
    spread_events: int,
    spread_recovery_rate: float,
    liquidity_not_ready_rate: float,
    dominant_gap: str,
    closest_candidate_seconds: Any,
) -> str:
    upper_label = str(label or "").upper()
    if "UNKNOWN" in upper_label and (event_share >= 0.25 or events >= 20):
        return "UNKNOWN_COVERAGE_GAP"
    if events < 5 or (candidate_events < 2 and spread_events < 2):
        return "INSUFFICIENT_REGIME_SAMPLE"
    if candidate_events == 0:
        return "WATCHLIST_REGIME"
    if spread_recovery_rate < 0.50 and (
        liquidity_not_ready_rate >= 0.50 or dominant_gap == "LIQUIDITY_NOT_READY"
    ):
        return "AVOID_REGIME"
    if spread_recovery_rate < 0.75 or liquidity_not_ready_rate >= 0.35:
        return "WATCHLIST_REGIME"
    if spread_recovery_rate >= 0.85 and liquidity_not_ready_rate <= 0.25:
        if closest_candidate_seconds is None or _as_float(closest_candidate_seconds) >= 90:
            return "TRADEABLE_REGIME"
    return "WATCHLIST_REGIME"


def _regime_replay_dimension_summary(
    records: list[dict[str, Any]],
    *,
    key: str,
) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    total = len(records)
    for record in records:
        label = str(record.get(key) or "UNKNOWN")
        group = groups.setdefault(label, _regime_replay_group())
        _add_regime_replay_event(group, record)
    return {
        label: _regime_group_summary(group, event_share=(group["events"] / total if total else 0.0), label=label)
        for label, group in sorted(groups.items())
    }


def _regime_replay_table(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    total = len(records)
    for record in records:
        key = (str(record.get("combo_regime") or "UNKNOWN+UNKNOWN"), str(record.get("timing_bucket") or "unknown"))
        group = groups.setdefault(key, _regime_replay_group())
        _add_regime_replay_event(group, record)
    rows: list[dict[str, Any]] = []
    for (combo, timing_bucket), group in sorted(groups.items()):
        summary = _regime_group_summary(group, event_share=(group["events"] / total if total else 0.0), label=combo)
        summary["combo_regime"] = combo
        summary["timing_bucket"] = timing_bucket
        rows.append(summary)
    return rows


def _unknown_regime_coverage(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    unknown_volatility = sum(1 for record in records if record.get("volatility_regime") == "UNKNOWN")
    unknown_trend = sum(1 for record in records if record.get("trend_regime") == "UNKNOWN")
    unknown_combo = sum(1 for record in records if record.get("combo_regime") == "UNKNOWN+UNKNOWN")
    unknown_combo_share = round(unknown_combo / total, 4) if total else 0.0
    return {
        "events_counted": int(total),
        "unknown_volatility_events": int(unknown_volatility),
        "unknown_volatility_share": round(unknown_volatility / total, 4) if total else 0.0,
        "unknown_trend_events": int(unknown_trend),
        "unknown_trend_share": round(unknown_trend / total, 4) if total else 0.0,
        "unknown_combo_events": int(unknown_combo),
        "unknown_combo_share": unknown_combo_share,
        "classification": "UNKNOWN_COVERAGE_GAP" if unknown_combo_share >= 0.25 else "TRADEABLE_REGIME",
    }


def _summarize_regime_replay_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        empty_dimensions = {
            "volatility_regime": {},
            "trend_regime": {},
            "combo_regime": {},
            "timing_bucket": {},
        }
        return {
            "events_counted": 0,
            "regime_replay_table": [],
            "candidate_gap_by_regime": empty_dimensions,
            "liquidity_readiness_by_regime": empty_dimensions,
            "spread_recovery_by_regime": empty_dimensions,
            "closest_candidate_timing_by_regime": empty_dimensions,
            "no_entry_by_regime": empty_dimensions,
            "late_window_by_regime": empty_dimensions,
            "unknown_regime_coverage": _unknown_regime_coverage([]),
            "regime_tradeability_classification": "INSUFFICIENT_REGIME_SAMPLE",
        }

    dimension_summaries = {
        "volatility_regime": _regime_replay_dimension_summary(records, key="volatility_regime"),
        "trend_regime": _regime_replay_dimension_summary(records, key="trend_regime"),
        "combo_regime": _regime_replay_dimension_summary(records, key="combo_regime"),
        "timing_bucket": _regime_replay_dimension_summary(records, key="timing_bucket"),
    }
    tradeability_counts = Counter(
        summary.get("regime_tradeability_classification", "INSUFFICIENT_REGIME_SAMPLE")
        for summary in dimension_summaries["combo_regime"].values()
    )
    if tradeability_counts.get("UNKNOWN_COVERAGE_GAP", 0):
        overall = "UNKNOWN_COVERAGE_GAP"
    elif tradeability_counts.get("AVOID_REGIME", 0):
        overall = "AVOID_REGIME"
    elif tradeability_counts.get("WATCHLIST_REGIME", 0):
        overall = "WATCHLIST_REGIME"
    elif tradeability_counts.get("TRADEABLE_REGIME", 0):
        overall = "TRADEABLE_REGIME"
    else:
        overall = "INSUFFICIENT_REGIME_SAMPLE"

    candidate_gap_by_regime = {
        dimension: {
            label: {
                "candidate_events": summary.get("candidate_events", 0),
                "candidate_gap_counts": summary.get("candidate_gap_counts", {}),
                "dominant_candidate_gap": summary.get("dominant_candidate_gap", ""),
                "regime_tradeability_classification": summary.get("regime_tradeability_classification", ""),
            }
            for label, summary in groups.items()
        }
        for dimension, groups in dimension_summaries.items()
    }
    liquidity_readiness_by_regime = {
        dimension: {
            label: {
                "liquidity_ready_events": summary.get("liquidity_ready_events", 0),
                "liquidity_not_ready_events": summary.get("liquidity_not_ready_events", 0),
                "liquidity_not_ready_rate": summary.get("liquidity_not_ready_rate", 0.0),
                "regime_tradeability_classification": summary.get("regime_tradeability_classification", ""),
            }
            for label, summary in groups.items()
        }
        for dimension, groups in dimension_summaries.items()
    }
    spread_recovery_by_regime = {
        dimension: {
            label: {
                "spread_events": summary.get("spread_events", 0),
                "spread_recovery_rate": summary.get("spread_recovery_rate", 0.0),
                "avg_spread_gap": summary.get("avg_spread_gap", 0.0),
                "regime_tradeability_classification": summary.get("regime_tradeability_classification", ""),
            }
            for label, summary in groups.items()
        }
        for dimension, groups in dimension_summaries.items()
    }
    closest_candidate_timing_by_regime = {
        dimension: {
            label: {
                "closest_candidate_seconds": summary.get("closest_candidate_seconds"),
                "closest_candidate_bucket": summary.get("closest_candidate_bucket", ""),
                "timing_bucket_counts": summary.get("timing_bucket_counts", {}),
            }
            for label, summary in groups.items()
        }
        for dimension, groups in dimension_summaries.items()
    }
    no_entry_by_regime = {
        dimension: {
            label: {
                "no_entry_events": summary.get("no_entry_events", 0),
                "candidate_events": summary.get("candidate_events", 0),
                "regime_tradeability_classification": summary.get("regime_tradeability_classification", ""),
            }
            for label, summary in groups.items()
        }
        for dimension, groups in dimension_summaries.items()
    }
    late_window_by_regime = {
        dimension: {
            label: {
                "late_window_blocks": summary.get("late_window_blocks", 0),
                "events": summary.get("events", 0),
                "regime_tradeability_classification": summary.get("regime_tradeability_classification", ""),
            }
            for label, summary in groups.items()
        }
        for dimension, groups in dimension_summaries.items()
    }
    return {
        "events_counted": int(len(records)),
        "regime_replay_table": _regime_replay_table(records),
        "candidate_gap_by_regime": candidate_gap_by_regime,
        "liquidity_readiness_by_regime": liquidity_readiness_by_regime,
        "spread_recovery_by_regime": spread_recovery_by_regime,
        "closest_candidate_timing_by_regime": closest_candidate_timing_by_regime,
        "no_entry_by_regime": no_entry_by_regime,
        "late_window_by_regime": late_window_by_regime,
        "unknown_regime_coverage": _unknown_regime_coverage(records),
        "regime_tradeability_classification": overall,
    }


def _load_regime_replay_summary_from_events(
    *,
    base_dir: str | Path,
    date: str,
    time_filter: dict[str, Any],
) -> dict[str, Any]:
    try:
        events, _bad_lines = load_replay_events(
            base_dir=base_dir,
            date_from=date,
            date_to=date,
            since_utc=time_filter.get("since_utc"),
            until_utc=time_filter.get("until_utc"),
            run_id=time_filter.get("run_id"),
        )
    except Exception:
        return {}

    records: list[dict[str, Any]] = []
    for event in events:
        record = _regime_replay_event(event)
        if record is not None:
            records.append(record)
    return _summarize_regime_replay_records(records)


REGIME_AUDIT_CATEGORIES = {
    "market_snapshots",
    "decision_log",
    "execution_log",
    "risk_log",
    "system_health",
    "trade_journal",
}


def _iter_regime_field_paths(value: Any, *, prefix: str = "payload") -> list[tuple[str, Any]]:
    paths: list[tuple[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{prefix}.{key}" if prefix else str(key)
            if key in {"volatility_regime", "trend_regime"}:
                paths.append((child_path, child))
            if isinstance(child, dict):
                paths.extend(_iter_regime_field_paths(child, prefix=child_path))
    return paths


def _is_known_regime_value(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(text and text.upper() != "UNKNOWN")


def _event_regime_presence(event: dict[str, Any]) -> tuple[bool, bool, list[str], list[str]]:
    payload = _payload_from_event(event)
    field_paths = _iter_regime_field_paths(payload)
    volatility_paths = [
        path
        for path, value in field_paths
        if path.endswith(".volatility_regime") and _is_known_regime_value(value)
    ]
    trend_paths = [
        path
        for path, value in field_paths
        if path.endswith(".trend_regime") and _is_known_regime_value(value)
    ]
    return bool(volatility_paths), bool(trend_paths), volatility_paths, trend_paths


def _source_module_for_event(event: dict[str, Any]) -> str:
    payload = _payload_from_event(event)
    return str(
        event.get("source_module")
        or payload.get("source_module")
        or "UNKNOWN_SOURCE"
    )


def _event_family(event: dict[str, Any]) -> str:
    category = str(event.get("_category", "") or "")
    if category:
        return category
    event_type = str(event.get("event_type", "") or "")
    if event_type in {"trade_open", "trade_close"}:
        return "trade_journal"
    if event_type == "risk_event":
        return "risk_log"
    if event_type == "execution":
        return "execution_log"
    if event_type == "decision":
        return "decision_log"
    if event_type == "market_snapshot":
        return "market_snapshots"
    return event_type or "UNKNOWN_CATEGORY"


def _coverage_bucket() -> dict[str, int]:
    return {
        "events_checked": 0,
        "missing_volatility_regime": 0,
        "missing_trend_regime": 0,
        "missing_both": 0,
    }


def _coverage_add(bucket: dict[str, int], *, has_volatility: bool, has_trend: bool) -> None:
    bucket["events_checked"] += 1
    if not has_volatility:
        bucket["missing_volatility_regime"] += 1
    if not has_trend:
        bucket["missing_trend_regime"] += 1
    if not has_volatility and not has_trend:
        bucket["missing_both"] += 1


def _has_market_context(payload: dict[str, Any]) -> bool:
    for key in ("market_id", "ticker", "asset", "token_id", "source_market_id", "position_id"):
        value = payload.get(key)
        if str(value or "").strip():
            return True
    return False


def _regime_not_applicable_reason(event: dict[str, Any]) -> str:
    category = _event_family(event)
    payload = _payload_from_event(event)
    if category == "system_health":
        return "system_health_regime_agnostic"
    if category == "risk_log" and not _has_market_context(payload):
        return "portfolio_risk_event_without_market"
    return ""


def _summarize_coverage_counter(groups: dict[str, dict[str, int]]) -> dict[str, dict[str, Any]]:
    summarized: dict[str, dict[str, Any]] = {}
    for label, bucket in sorted(groups.items()):
        checked = _as_int(bucket.get("events_checked"))
        summarized[label] = {
            **bucket,
            "missing_volatility_share": round(bucket["missing_volatility_regime"] / checked, 4) if checked else 0.0,
            "missing_trend_share": round(bucket["missing_trend_regime"] / checked, 4) if checked else 0.0,
            "missing_both_share": round(bucket["missing_both"] / checked, 4) if checked else 0.0,
        }
    return summarized


def _suspected_missing_sources(
    missing_sources: Counter[tuple[str, str, str]],
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    suspected: list[dict[str, Any]] = []
    for (category, event_type, source_module), count in missing_sources.most_common(limit):
        suspected.append({
            "jsonl_category": category,
            "event_type": event_type,
            "source_module": source_module,
            "missing_both_events": int(count),
        })
    return suspected


def _recommended_regime_field_mapping_fixes(
    *,
    missing_by_category: dict[str, dict[str, int]],
    available_paths: Counter[str],
    not_applicable_by_category: Counter[str],
) -> list[str]:
    recommendations: list[str] = []
    if missing_by_category.get("decision_log", {}).get("missing_both", 0):
        recommendations.append(
            "decision_log: ensure decision payloads include volatility_regime and trend_regime at payload root or payload.display."
        )
    if missing_by_category.get("market_snapshots", {}).get("missing_both", 0):
        recommendations.append(
            "market_snapshots: pass existing snapshot regime diagnostics through as volatility_regime and trend_regime."
        )
    if missing_by_category.get("execution_log", {}).get("missing_both", 0):
        recommendations.append(
            "execution_log: include the decision/snapshot regime fields when logging execution attempts or fills."
        )
    if missing_by_category.get("risk_log", {}).get("missing_both", 0):
        recommendations.append(
            "risk_log: add regime fields only when the risk event is tied to a market decision; leave portfolio-only risk events unclassified."
        )
    if not_applicable_by_category.get("system_health", 0):
        recommendations.append(
            "system_health: likely expected to be regime-agnostic; exclude or separately label it in regime research tables."
        )
    if missing_by_category.get("trade_journal", {}).get("missing_both", 0):
        recommendations.append(
            "trade_journal: copy entry decision regime fields into trade_open/trade_close metadata when available."
        )
    if available_paths:
        recommendations.append(
            "evaluator: recognized regime paths are present in JSONL; prefer canonical payload.volatility_regime and payload.trend_regime for future logs."
        )
    return recommendations[:8]


def _summarize_regime_coverage_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    family_events = [event for event in events if _event_family(event) in REGIME_AUDIT_CATEGORIES]
    checked_events: list[dict[str, Any]] = []
    not_applicable_by_category: Counter[str] = Counter()
    not_applicable_by_event_type: Counter[str] = Counter()
    not_applicable_by_reason: Counter[str] = Counter()
    for event in family_events:
        reason = _regime_not_applicable_reason(event)
        if reason:
            not_applicable_by_category[_event_family(event)] += 1
            not_applicable_by_event_type[str(event.get("event_type", "") or "UNKNOWN_EVENT")] += 1
            not_applicable_by_reason[reason] += 1
            continue
        checked_events.append(event)
    missing_by_event_type: dict[str, dict[str, int]] = {}
    missing_by_source_module: dict[str, dict[str, int]] = {}
    missing_by_category: dict[str, dict[str, int]] = {}
    available_paths: Counter[str] = Counter()
    missing_sources: Counter[tuple[str, str, str]] = Counter()
    total = complete = missing_volatility = missing_trend = missing_both = 0

    for event in checked_events:
        total += 1
        event_type = str(event.get("event_type", "") or "UNKNOWN_EVENT")
        category = _event_family(event)
        source_module = _source_module_for_event(event)
        has_volatility, has_trend, volatility_paths, trend_paths = _event_regime_presence(event)
        for path in volatility_paths + trend_paths:
            available_paths[path] += 1
        if has_volatility and has_trend:
            complete += 1
        if not has_volatility:
            missing_volatility += 1
        if not has_trend:
            missing_trend += 1
        if not has_volatility and not has_trend:
            missing_both += 1
            missing_sources[(category, event_type, source_module)] += 1

        for groups, label in (
            (missing_by_event_type, event_type),
            (missing_by_source_module, source_module),
            (missing_by_category, category),
        ):
            bucket = groups.setdefault(label, _coverage_bucket())
            _coverage_add(bucket, has_volatility=has_volatility, has_trend=has_trend)

    return {
        "total_events_seen": int(len(family_events)),
        "regime_not_applicable_events": int(sum(not_applicable_by_reason.values())),
        "regime_not_applicable_by_jsonl_category": dict(not_applicable_by_category.most_common()),
        "regime_not_applicable_by_event_type": dict(not_applicable_by_event_type.most_common()),
        "regime_not_applicable_reasons": dict(not_applicable_by_reason.most_common()),
        "total_events_checked": int(total),
        "events_with_complete_regime": int(complete),
        "events_missing_volatility_regime": int(missing_volatility),
        "events_missing_trend_regime": int(missing_trend),
        "events_missing_both": int(missing_both),
        "unknown_regime_share": round(missing_both / total, 4) if total else 0.0,
        "missing_by_event_type": _summarize_coverage_counter(missing_by_event_type),
        "missing_by_source_module": _summarize_coverage_counter(missing_by_source_module),
        "missing_by_jsonl_category": _summarize_coverage_counter(missing_by_category),
        "available_regime_field_paths": dict(available_paths.most_common()),
        "suspected_missing_payload_sources": _suspected_missing_sources(missing_sources),
        "recommended_field_mapping_fixes": _recommended_regime_field_mapping_fixes(
            missing_by_category=missing_by_category,
            available_paths=available_paths,
            not_applicable_by_category=not_applicable_by_category,
        ),
    }


def _load_regime_coverage_audit_from_events(
    *,
    base_dir: str | Path,
    date: str,
    time_filter: dict[str, Any],
) -> dict[str, Any]:
    try:
        events, _bad_lines = load_replay_events(
            base_dir=base_dir,
            date_from=date,
            date_to=date,
            since_utc=time_filter.get("since_utc"),
            until_utc=time_filter.get("until_utc"),
            run_id=time_filter.get("run_id"),
        )
    except Exception:
        return {}
    return _summarize_regime_coverage_events(events)


def _summarize_liquidity_recovery_grace_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    entered = success = failed = recovered_before_cutoff = survived = research_mode = 0
    branch_seen = branch_preempted = branch_mode_disabled = branch_enter_failed = 0
    wait_values: list[float] = []
    exit_reasons: Counter[str] = Counter()
    branch_skipped_reasons: Counter[str] = Counter()
    for event in events:
        payload = _payload_from_event(event)
        if not payload:
            continue
        if _as_bool(_payload_value(payload, "empty_book_recovery_research_mode")):
            research_mode += 1
        if _as_bool(_payload_value(payload, "recovery_branch_candidate_seen")):
            branch_seen += 1
        if _as_bool(_payload_value(payload, "recovery_branch_preempted_by_cutoff")):
            branch_preempted += 1
        if _as_bool(_payload_value(payload, "recovery_branch_mode_disabled")):
            branch_mode_disabled += 1
        if _as_bool(_payload_value(payload, "recovery_branch_enter_condition_failed")):
            branch_enter_failed += 1
        grace_entered = _as_bool(_payload_value(payload, "liquidity_recovery_grace_entered"))
        grace_success = _as_bool(_payload_value(payload, "liquidity_recovery_grace_success"))
        grace_failed = _as_bool(_payload_value(payload, "liquidity_recovery_grace_failed"))
        if grace_entered:
            entered += 1
        if grace_success:
            success += 1
        if grace_failed:
            failed += 1
        if _as_bool(_payload_value(payload, "recovered_before_cutoff")):
            recovered_before_cutoff += 1
        if _as_bool(_payload_value(payload, "candidate_survived_recovery")):
            survived += 1
        exit_reason = str(_payload_value(payload, "recovery_exit_reason") or "").strip()
        if exit_reason:
            exit_reasons[exit_reason] += 1
        branch_skipped_reason = str(_payload_value(payload, "recovery_branch_skipped_reason") or "").strip()
        if branch_skipped_reason:
            branch_skipped_reasons[branch_skipped_reason] += 1
        if grace_entered or grace_success or grace_failed or exit_reason:
            wait_value = _payload_value(payload, "recovery_wait_seconds")
            if wait_value is not None:
                wait_values.append(_as_float(wait_value))
    return {
        "liquidity_recovery_research_mode_events": int(research_mode),
        "recovery_branch_candidate_seen": int(branch_seen),
        "recovery_branch_preempted_by_cutoff": int(branch_preempted),
        "recovery_branch_mode_disabled": int(branch_mode_disabled),
        "recovery_branch_enter_condition_failed": int(branch_enter_failed),
        "liquidity_recovery_grace_entered": int(entered),
        "liquidity_recovery_grace_success": int(success),
        "liquidity_recovery_grace_failed": int(failed),
        "average_recovery_wait_seconds": round(sum(wait_values) / len(wait_values), 3) if wait_values else 0.0,
        "max_recovery_wait_seconds": round(max(wait_values), 3) if wait_values else 0.0,
        "recovered_before_cutoff": int(recovered_before_cutoff),
        "candidate_survived_recovery": int(survived),
        "dominant_recovery_exit_reason": exit_reasons.most_common(1)[0][0] if exit_reasons else "",
        "recovery_exit_reasons": [[reason, count] for reason, count in exit_reasons.most_common()],
        "recovery_branch_skipped_reasons": [[reason, count] for reason, count in branch_skipped_reasons.most_common()],
    }


def _load_liquidity_recovery_grace_summary_from_events(
    *,
    base_dir: str | Path,
    date: str,
    time_filter: dict[str, Any],
) -> dict[str, Any]:
    try:
        events, _bad_lines = load_replay_events(
            base_dir=base_dir,
            date_from=date,
            date_to=date,
            since_utc=time_filter.get("since_utc"),
            until_utc=time_filter.get("until_utc"),
            run_id=time_filter.get("run_id"),
        )
    except Exception:
        return {}
    return _summarize_liquidity_recovery_grace_events(events)


def _evaluation_payload(evaluation: SessionRuntimeEvaluation | dict[str, Any]) -> dict[str, Any]:
    if isinstance(evaluation, SessionRuntimeEvaluation):
        return evaluation.to_dict()
    return dict(evaluation or {})


def _session_spread_row(evaluation: SessionRuntimeEvaluation | dict[str, Any]) -> dict[str, Any]:
    payload = _evaluation_payload(evaluation)
    spread = payload.get("spread_compression_summary", {})
    candidate = payload.get("candidate_gap_summary", {})
    health = payload.get("health_summary", {})
    cutoff = payload.get("cutoff_by_regime", {})
    risk = payload.get("risk_blocks", {})
    late_window = cutoff.get("late_window_opportunity", {}) if isinstance(cutoff, dict) else {}
    closest = candidate.get("closest_candidate_before_cutoff", {}) if isinstance(candidate, dict) else {}
    closest_spread = spread.get("closest_spread_gap_before_cutoff", {}) if isinstance(spread, dict) else {}
    return {
        "date": str(payload.get("date", "")),
        "entered": _as_int(health.get("entered")) if isinstance(health, dict) else 0,
        "spread_diagnosis": str(spread.get("spread_compression_diagnosis", "") or "UNKNOWN") if isinstance(spread, dict) else "UNKNOWN",
        "candidate_gap_diagnosis": str(candidate.get("candidate_gap_diagnosis", "") or "UNKNOWN") if isinstance(candidate, dict) else "UNKNOWN",
        "cutoff_interpretation": str(candidate.get("cutoff_interpretation", "") or "") if isinstance(candidate, dict) else "",
        "spread_normalization_seconds": spread.get("spread_normalization_seconds") if isinstance(spread, dict) else None,
        "avg_spread_velocity": _as_float(spread.get("avg_spread_velocity")) if isinstance(spread, dict) else 0.0,
        "spread_recovery_rate": _as_float(spread.get("spread_recovery_rate")) if isinstance(spread, dict) else 0.0,
        "pre_cutoff_spread_events": _as_int(spread.get("pre_cutoff_spread_events")) if isinstance(spread, dict) else 0,
        "events_counted": _as_int(spread.get("events_counted")) if isinstance(spread, dict) else 0,
        "closest_candidate_seconds": (
            candidate.get("seconds_remaining_at_closest_candidate")
            if isinstance(candidate, dict)
            else None
        ),
        "closest_candidate_bucket": str(candidate.get("closest_candidate_bucket", "") or "") if isinstance(candidate, dict) else "",
        "closest_candidate_regime": (
            f"{closest.get('trend_regime', 'UNKNOWN')}+{closest.get('volatility_regime', 'UNKNOWN')}"
            if isinstance(closest, dict)
            else "UNKNOWN+UNKNOWN"
        ),
        "closest_spread_gap": closest_spread.get("spread_gap_to_limit") if isinstance(closest_spread, dict) else None,
        "late_window_blocks": _as_int(late_window.get("total_late_window_blocks")) if isinstance(late_window, dict) else 0,
        "late_window_diagnosis": str(late_window.get("late_window_diagnosis", "") or "") if isinstance(late_window, dict) else "",
        "bankroll_family": str(risk.get("bankroll_family", "") or "") if isinstance(risk, dict) else "",
        "bankroll_mode": str(risk.get("bankroll_mode", "") or "") if isinstance(risk, dict) else "",
        "spread_gap_by_regime": spread.get("spread_gap_by_regime", {}) if isinstance(spread, dict) else {},
    }


def _multi_group_accumulator() -> dict[str, Any]:
    return {
        "sessions": 0,
        "events": 0,
        "normalized_events": 0,
        "avg_spread_sum": 0.0,
        "avg_spread_gap_sum": 0.0,
        "normalization_seconds_values": [],
        "closest_candidate_seconds_values": [],
    }


def _add_multi_spread_group(
    accumulator: dict[str, Any],
    *,
    group: dict[str, Any],
    session_normalization_seconds: Any,
    closest_candidate_seconds: Any,
) -> None:
    events = _as_int(group.get("events"))
    if events <= 0:
        return
    accumulator["sessions"] += 1
    accumulator["events"] += events
    accumulator["normalized_events"] += _as_int(group.get("normalized_events"))
    accumulator["avg_spread_sum"] += _as_float(group.get("avg_spread")) * events
    accumulator["avg_spread_gap_sum"] += _as_float(group.get("avg_spread_gap")) * events
    if session_normalization_seconds is not None:
        accumulator["normalization_seconds_values"].append(_as_float(session_normalization_seconds))
    if closest_candidate_seconds is not None:
        accumulator["closest_candidate_seconds_values"].append(_as_float(closest_candidate_seconds))


def _finalize_multi_spread_group(accumulator: dict[str, Any]) -> dict[str, Any]:
    events = _as_int(accumulator.get("events"))
    normalization_values = accumulator.get("normalization_seconds_values", [])
    candidate_values = accumulator.get("closest_candidate_seconds_values", [])
    return {
        "sessions": _as_int(accumulator.get("sessions")),
        "events": events,
        "normalized_events": _as_int(accumulator.get("normalized_events")),
        "recovery_rate": round(_as_int(accumulator.get("normalized_events")) / events, 4) if events else 0.0,
        "avg_spread": round(_as_float(accumulator.get("avg_spread_sum")) / events, 6) if events else 0.0,
        "avg_spread_gap": round(_as_float(accumulator.get("avg_spread_gap_sum")) / events, 6) if events else 0.0,
        "avg_normalization_seconds": round(sum(normalization_values) / len(normalization_values), 2) if normalization_values else None,
        "avg_closest_candidate_seconds": round(sum(candidate_values) / len(candidate_values), 2) if candidate_values else None,
    }


def _trend_family(label: str) -> str:
    upper = str(label or "").upper()
    if "SIDEWAY" in upper or "RANGE" in upper or "FLAT" in upper:
        return "SIDEWAY"
    if upper in {"", "UNKNOWN"}:
        return "UNKNOWN"
    return "TREND"


def _volatility_family(label: str) -> str:
    upper = str(label or "").upper()
    if "EXTREME" in upper:
        return "EXTREME_VOL"
    if "NORMAL" in upper:
        return "NORMAL_VOL"
    if upper in {"", "UNKNOWN"}:
        return "UNKNOWN"
    return "OTHER_VOL"


def _regime_spread_matrix(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    accumulators: dict[str, dict[str, dict[str, Any]]] = {
        "volatility_regime": {},
        "trend_regime": {},
        "combo_regime": {},
        "volatility_family": {},
        "trend_family": {},
    }
    for row in rows:
        regime_summary = row.get("spread_gap_by_regime", {})
        if not isinstance(regime_summary, dict):
            continue
        for section in ("volatility_regime", "trend_regime", "combo_regime"):
            groups = regime_summary.get(section, {})
            if not isinstance(groups, dict):
                continue
            for label, group in groups.items():
                if not isinstance(group, dict):
                    continue
                accumulator = accumulators[section].setdefault(str(label), _multi_group_accumulator())
                _add_multi_spread_group(
                    accumulator,
                    group=group,
                    session_normalization_seconds=row.get("spread_normalization_seconds"),
                    closest_candidate_seconds=row.get("closest_candidate_seconds"),
                )
                if section == "trend_regime":
                    family = _trend_family(str(label))
                    family_accumulator = accumulators["trend_family"].setdefault(family, _multi_group_accumulator())
                    _add_multi_spread_group(
                        family_accumulator,
                        group=group,
                        session_normalization_seconds=row.get("spread_normalization_seconds"),
                        closest_candidate_seconds=row.get("closest_candidate_seconds"),
                    )
                if section == "volatility_regime":
                    family = _volatility_family(str(label))
                    family_accumulator = accumulators["volatility_family"].setdefault(family, _multi_group_accumulator())
                    _add_multi_spread_group(
                        family_accumulator,
                        group=group,
                        session_normalization_seconds=row.get("spread_normalization_seconds"),
                        closest_candidate_seconds=row.get("closest_candidate_seconds"),
                    )
    return {
        section: {
            label: _finalize_multi_spread_group(accumulator)
            for label, accumulator in sorted(groups.items())
        }
        for section, groups in accumulators.items()
    }


def _frequency(counter: Counter[str]) -> dict[str, int]:
    return {label: int(count) for label, count in counter.most_common()}


def _avg_optional(values: list[Any]) -> float | None:
    numeric = [_as_float(value) for value in values if value is not None]
    if not numeric:
        return None
    return round(sum(numeric) / len(numeric), 6)


def _spread_failure_clusters(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clusters: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        key = (
            row.get("spread_diagnosis", "UNKNOWN"),
            row.get("candidate_gap_diagnosis", "UNKNOWN"),
            row.get("closest_candidate_bucket", "") or "unknown",
        )
        cluster = clusters.setdefault(
            key,
            {
                "spread_diagnosis": key[0],
                "candidate_gap_diagnosis": key[1],
                "closest_candidate_bucket": key[2],
                "sessions": 0,
                "no_entry_sessions": 0,
                "dates": [],
                "recovery_rates": [],
                "closest_candidate_seconds_values": [],
            },
        )
        cluster["sessions"] += 1
        if _as_int(row.get("entered")) == 0:
            cluster["no_entry_sessions"] += 1
        if row.get("date"):
            cluster["dates"].append(row["date"])
        cluster["recovery_rates"].append(_as_float(row.get("spread_recovery_rate")))
        if row.get("closest_candidate_seconds") is not None:
            cluster["closest_candidate_seconds_values"].append(_as_float(row.get("closest_candidate_seconds")))

    finalized: list[dict[str, Any]] = []
    for cluster in clusters.values():
        recovery_rates = cluster.pop("recovery_rates")
        closest_values = cluster.pop("closest_candidate_seconds_values")
        cluster["avg_spread_recovery_rate"] = round(sum(recovery_rates) / len(recovery_rates), 4) if recovery_rates else 0.0
        cluster["avg_closest_candidate_seconds"] = round(sum(closest_values) / len(closest_values), 2) if closest_values else None
        finalized.append(cluster)
    return sorted(finalized, key=lambda item: (-_as_int(item.get("sessions")), str(item.get("spread_diagnosis"))))


def _repeated_no_entry_patterns(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    patterns: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in rows:
        if _as_int(row.get("entered")) > 0:
            continue
        key = (
            row.get("candidate_gap_diagnosis", "UNKNOWN"),
            row.get("spread_diagnosis", "UNKNOWN"),
            row.get("late_window_diagnosis", "") or "NO_LATE_WINDOW_DIAGNOSIS",
            row.get("bankroll_mode", "") or "UNKNOWN_BANKROLL_MODE",
        )
        pattern = patterns.setdefault(
            key,
            {
                "candidate_gap_diagnosis": key[0],
                "spread_diagnosis": key[1],
                "late_window_diagnosis": key[2],
                "bankroll_mode": key[3],
                "sessions": 0,
                "dates": [],
            },
        )
        pattern["sessions"] += 1
        if row.get("date"):
            pattern["dates"].append(row["date"])
    return sorted(patterns.values(), key=lambda item: (-_as_int(item.get("sessions")), str(item.get("spread_diagnosis"))))


def _multi_session_interpretation(rows: list[dict[str, Any]], regime_matrix: dict[str, dict[str, dict[str, Any]]]) -> str:
    if len(rows) < 2 or sum(_as_int(row.get("events_counted")) for row in rows) == 0:
        return "INSUFFICIENT_MULTI_SESSION_DATA"

    failure_diagnoses = {"SPREAD_NEVER_NORMALIZED", "SPREAD_NORMALIZED_TOO_LATE"}
    failure_rows = [row for row in rows if row.get("spread_diagnosis") in failure_diagnoses]
    recovered_rows = [row for row in rows if row.get("spread_diagnosis") == "SPREAD_RECOVERED_BEFORE_CUTOFF"]
    regime_dependent_rows = [row for row in rows if row.get("spread_diagnosis") == "REGIME_DEPENDENT_SPREAD_BEHAVIOR"]
    no_entry_rows = [row for row in rows if _as_int(row.get("entered")) == 0]
    micro_rows = [
        row
        for row in rows
        if "MICRO" in str(row.get("bankroll_family", "")).upper()
        or "MICRO" in str(row.get("bankroll_mode", "")).upper()
    ]
    micro_failure_rows = [row for row in micro_rows if row in failure_rows and _as_int(row.get("entered")) == 0]

    if micro_rows and micro_failure_rows and len(micro_failure_rows) == len(no_entry_rows) and len(micro_rows) < len(rows):
        return "MICRO_BANKROLL_SENSITIVITY"

    combo_rates = [
        _as_float(group.get("recovery_rate"))
        for group in regime_matrix.get("combo_regime", {}).values()
        if _as_int(group.get("events")) > 0
    ]
    trend_family = regime_matrix.get("trend_family", {})
    vol_family = regime_matrix.get("volatility_family", {})
    family_spread = 0.0
    if trend_family.get("SIDEWAY") and trend_family.get("TREND"):
        family_spread = max(
            family_spread,
            abs(_as_float(trend_family["SIDEWAY"].get("recovery_rate")) - _as_float(trend_family["TREND"].get("recovery_rate"))),
        )
    if vol_family.get("EXTREME_VOL") and vol_family.get("NORMAL_VOL"):
        family_spread = max(
            family_spread,
            abs(_as_float(vol_family["EXTREME_VOL"].get("recovery_rate")) - _as_float(vol_family["NORMAL_VOL"].get("recovery_rate"))),
        )

    if regime_dependent_rows:
        return "REGIME_DEPENDENT_SPREAD_LIMITATION"
    if failure_rows and len(failure_rows) >= max(2, int(len(rows) * 0.67)):
        return "STRUCTURAL_SPREAD_LIMITATION"
    if (combo_rates and max(combo_rates) > 0 and min(combo_rates) == 0) or family_spread >= 0.5:
        return "REGIME_DEPENDENT_SPREAD_LIMITATION"
    if failure_rows and recovered_rows:
        return "SESSION_SPECIFIC_SPREAD_FAILURE"
    if failure_rows:
        return "SESSION_SPECIFIC_SPREAD_FAILURE"
    return "INSUFFICIENT_MULTI_SESSION_DATA"


def build_multi_session_spread_summary(
    evaluations: list[SessionRuntimeEvaluation | dict[str, Any]],
) -> dict[str, Any]:
    rows = [_session_spread_row(evaluation) for evaluation in evaluations]
    spread_counter: Counter[str] = Counter(row["spread_diagnosis"] for row in rows)
    candidate_counter: Counter[str] = Counter(row["candidate_gap_diagnosis"] for row in rows)
    regime_matrix = _regime_spread_matrix(rows)
    interpretation = _multi_session_interpretation(rows, regime_matrix)
    no_entry_sessions = sum(1 for row in rows if _as_int(row.get("entered")) == 0)
    late_window_sessions = sum(1 for row in rows if _as_int(row.get("late_window_blocks")) > 0)
    normalization_values = [row.get("spread_normalization_seconds") for row in rows]
    velocity_values = [row.get("avg_spread_velocity") for row in rows]
    recovery_values = [row.get("spread_recovery_rate") for row in rows]
    closest_candidate_values = [row.get("closest_candidate_seconds") for row in rows]
    spread_normalization_by_regime = {
        section: {
            label: {
                "sessions": group.get("sessions", 0),
                "avg_normalization_seconds": group.get("avg_normalization_seconds"),
                "recovery_rate": group.get("recovery_rate", 0.0),
            }
            for label, group in groups.items()
        }
        for section, groups in regime_matrix.items()
    }
    candidate_timing_by_regime = {
        section: {
            label: {
                "sessions": group.get("sessions", 0),
                "avg_closest_candidate_seconds": group.get("avg_closest_candidate_seconds"),
            }
            for label, group in groups.items()
        }
        for section, groups in regime_matrix.items()
    }
    return {
        "multi_session_spread_summary": {
            "sessions_counted": int(len(rows)),
            "no_entry_sessions": int(no_entry_sessions),
            "no_entry_frequency": round(no_entry_sessions / len(rows), 4) if rows else 0.0,
            "late_window_sessions": int(late_window_sessions),
            "late_window_frequency": round(late_window_sessions / len(rows), 4) if rows else 0.0,
            "avg_spread_normalization_seconds": _avg_optional(normalization_values),
            "avg_spread_velocity": _avg_optional(velocity_values),
            "avg_closest_candidate_seconds": _avg_optional(closest_candidate_values),
            "avg_spread_recovery_rate": _avg_optional(recovery_values),
            "structural_vs_regime_dependent_interpretation": interpretation,
        },
        "spread_diagnosis_frequency": _frequency(spread_counter),
        "candidate_gap_diagnosis_frequency": _frequency(candidate_counter),
        "regime_spread_matrix": regime_matrix,
        "spread_normalization_by_regime": spread_normalization_by_regime,
        "candidate_timing_by_regime": candidate_timing_by_regime,
        "spread_failure_clusters": _spread_failure_clusters(rows),
        "repeated_no_entry_patterns": _repeated_no_entry_patterns(rows),
        "structural_vs_regime_dependent_interpretation": interpretation,
    }


def _merge_regime_summary(
    *,
    replay_payload: dict[str, Any],
    event_summary: dict[str, Any],
) -> dict[str, Any]:
    if event_summary:
        return event_summary

    volatility_counts = _counter_from_pairs(replay_payload.get("volatility_regimes"))
    trend_counts = _counter_from_pairs(replay_payload.get("trend_regimes"))
    if not volatility_counts and not trend_counts:
        return {
            "events_counted": 0,
            "volatility_regimes": [],
            "trend_regimes": [],
        }
    events_counted = max(sum(volatility_counts.values()), sum(trend_counts.values()))
    return {
        "events_counted": int(events_counted),
        "volatility_regimes": [[name, count] for name, count in volatility_counts.most_common()],
        "trend_regimes": [[name, count] for name, count in trend_counts.most_common()],
    }


def _has_failure_detail(payload: dict[str, Any]) -> bool:
    return any(bool(payload.get(key)) for key in ("error", "exception", "message", "traceback"))


def _is_true_execution_failure_event(event_name: str, status: str = "", payload: dict[str, Any] | None = None) -> bool:
    event = event_name.lower()
    event_status = status.lower()
    event_payload = payload or {}
    if event == "order_intent_reject":
        return False
    if event == "order_submit_failed":
        return True
    if event == "market_analysis_exception":
        return event_status in {"failed", "error", "rejected"} or _has_failure_detail(event_payload)
    if event == "cancel_order" and event_status in {"failed", "error", "rejected"}:
        return True
    if event in {"live_order_submitted", "order_submit"} and event_status in {"failed", "error", "rejected"}:
        return True
    if event.endswith("_failed") or event.endswith("_failure"):
        return event_status in {"failed", "error", "rejected"} or _has_failure_detail(event_payload)
    return False


def _load_execution_jsonl_summary(
    base_dir: str | Path,
    date: str,
    *,
    time_filter: dict[str, Any] | None = None,
) -> dict[str, int] | None:
    paths = _execution_log_paths(base_dir, date)
    if not paths:
        return None

    summary = {
        "execution_events_loaded": 0,
        "execution_failure_count": 0,
    }
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, dict):
                    continue
                if time_filter and not _event_in_time_filter(event, time_filter):
                    continue
                payload = _payload_from_event(event)
                summary["execution_events_loaded"] += 1
                event_name = str(payload.get("event", "") or event.get("event", "") or "").lower()
                status = str(payload.get("status", "") or event.get("status", "") or "").lower()
                if _is_true_execution_failure_event(event_name, status, payload):
                    summary["execution_failure_count"] += 1
    return summary


def _load_phase2_coverage_from_events(
    *,
    base_dir: str | Path,
    date: str,
    time_filter: dict[str, Any],
) -> dict[str, Any]:
    try:
        events, _bad_lines = load_replay_events(
            base_dir=base_dir,
            date_from=date,
            date_to=date,
            since_utc=time_filter.get("since_utc"),
            until_utc=time_filter.get("until_utc"),
            run_id=time_filter.get("run_id"),
        )
    except Exception:
        return build_phase2_coverage_from_events([])
    return build_phase2_coverage_from_events(events)


def _load_partial_lifecycle_replay_from_events(
    *,
    base_dir: str | Path,
    date: str,
    time_filter: dict[str, Any],
) -> dict[str, Any]:
    try:
        events, _bad_lines = load_replay_events(
            base_dir=base_dir,
            date_from=date,
            date_to=date,
            since_utc=time_filter.get("since_utc"),
            until_utc=time_filter.get("until_utc"),
            run_id=time_filter.get("run_id"),
        )
    except Exception:
        return build_partial_lifecycle_replay_from_events([])
    return build_partial_lifecycle_replay_from_events(events)


def _build_inventory_replay_readiness(phase2_coverage: dict[str, Any]) -> dict[str, Any]:
    coverage_gaps = list(phase2_coverage.get("coverage_gaps", []))
    proxy_items = list(phase2_coverage.get("proxy_inferred_items", []))
    return {
        "status": str(phase2_coverage.get("status", "INSUFFICIENT_PHASE2_COVERAGE")),
        "scope": "offline_analyzer_only",
        "runtime_behavior_changed": False,
        "live_readiness_claim": False,
        "ready_for_runtime_inventory": False,
        "coverage_gap_count": len(coverage_gaps),
        "coverage_gaps": coverage_gaps,
        "proxy_inferred_items": proxy_items,
        "notes": [
            "Missing research fields are coverage_gap only; they are not runtime failures.",
            "Proxy items are inferred from existing diagnostics and are not trade approvals.",
            "This report does not authorize live trading or inventory execution.",
        ],
    }


def _build_scores(
    *,
    skip_counts: Counter[str],
    replay: ReplayReport | None,
    no_entry: NoEntryReport | None,
    execution_failure_count: int = 0,
    no_data: bool = False,
) -> dict[str, int]:
    scores = {key: 0 for key in BOTTLENECKS}
    if no_data:
        scores["no_data"] = 1
        return scores
    scores["cutoff"] += skip_counts.get("time_unsafe", 0)
    scores["risk_plan_zero"] += skip_counts.get("risk_plan_zero", 0)
    scores["strategy_thresholds"] += sum(
        skip_counts.get(reason, 0)
        for reason in ("confidence_too_low", "ev_below_threshold", "delta_extreme", "scanner_no_best_trade")
    )
    scores["market_readiness"] += sum(
        count
        for reason, count in skip_counts.items()
        if reason in {"orderbook_unavailable", "no_orderbook", *HARDBLOCK_ORDERBOOK_REASONS} or "token_mapping" in reason
    )
    scores["stale_data"] += sum(count for reason, count in skip_counts.items() if "stale" in reason or reason in STALE_ORDERBOOK_REASONS)
    scores["websocket_instability"] += sum(
        count
        for reason, count in skip_counts.items()
        if "websocket" in reason or "oracle" in reason or "feed" in reason
    )

    scores["execution_failures"] = max(0, int(execution_failure_count))

    if replay is not None:
        if replay.average_decision_latency_ms > 2000 or replay.average_scan_cycle_duration_ms > 2500:
            scores["latency"] += max(1, int(replay.skipped_decisions or 1))
        if replay.max_orderbook_age_ms > 3000 or replay.max_oracle_age_ms > 10000:
            scores["stale_data"] += max(1, int(replay.skipped_decisions or 1))
        scores["cutoff"] += int(replay.cutoff_block_count)
        scores["cutoff"] += int(replay.late_entry_hard_block_count)
    if no_entry is not None:
        scores["market_readiness"] += int(no_entry.market_data_quality.get("token_mapping_warning_count", 0) or 0)
        if no_entry.total_scanned > 0 and no_entry.total_skipped == 0 and no_entry.total_entered == 0:
            scores["healthy_no_signal"] += 1

    if not any(value > 0 for key, value in scores.items() if key != "healthy_no_signal"):
        scores["healthy_no_signal"] = 1
    return scores


def _rank_bottlenecks(scores: dict[str, int]) -> tuple[str, str]:
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    primary = ranked[0][0] if ranked and ranked[0][1] > 0 else "healthy_no_signal"
    secondary = "none"
    for name, score in ranked[1:]:
        if score > 0:
            secondary = name
            break
    return primary, secondary


def _orderbook_reason_counts(
    *,
    replay_payload: dict[str, Any],
    no_entry_payload: dict[str, Any],
    skip_counts: Counter[str],
) -> Counter[str]:
    counts: Counter[str] = Counter()
    for item in replay_payload.get("orderbook_readiness_reasons", []) or []:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            counts[str(item[0])] += _as_int(item[1])

    market_quality = no_entry_payload.get("market_data_quality", {}) if no_entry_payload else {}
    if isinstance(market_quality, dict):
        reason_payload = market_quality.get("orderbook_readiness_reason_counts", {})
        if isinstance(reason_payload, dict):
            for reason, count in reason_payload.items():
                counts[str(reason)] += _as_int(count)
        else:
            for item in reason_payload or []:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    counts[str(item[0])] += _as_int(item[1])

    for reason in HARDBLOCK_ORDERBOOK_REASONS | WARMUP_ORDERBOOK_REASONS | STALE_ORDERBOOK_REASONS:
        if skip_counts.get(reason):
            counts[reason] += skip_counts[reason]
    return counts


def _top_pairs_from_payloads(*payloads: dict[str, Any], key: str) -> list[list[Any]]:
    counts: Counter[str] = Counter()
    for payload in payloads:
        if not payload:
            continue
        value = payload.get(key)
        if isinstance(value, dict):
            for reason, count in value.items():
                counts[str(reason)] += _as_int(count)
        else:
            for item in value or []:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    counts[str(item[0])] += _as_int(item[1])
        market_quality = payload.get("market_data_quality", {})
        if isinstance(market_quality, dict):
            nested = market_quality.get(key, {})
            if isinstance(nested, dict):
                for reason, count in nested.items():
                    counts[str(reason)] += _as_int(count)
    return [[reason, count] for reason, count in counts.most_common()]


def _resolved_execution_failure_count(
    *,
    replay_payload: dict[str, Any],
    no_entry_payload: dict[str, Any],
    raw_execution_summary: dict[str, int] | None = None,
) -> int:
    """Resolve true execution failures without treating total execution events as failures."""
    if raw_execution_summary is not None:
        return _as_int(raw_execution_summary.get("execution_failure_count"))

    if replay_payload:
        return _as_int(replay_payload.get("execution_failure_count"))

    if not no_entry_payload:
        return 0

    failure_count = _as_int(no_entry_payload.get("execution_failure_count"))
    execution_events_loaded = _as_int(no_entry_payload.get("execution_events_loaded"))
    no_order_activity = (
        _as_int(no_entry_payload.get("total_entered")) == 0
        and _as_int(no_entry_payload.get("order_submit_attempt_count")) == 0
        and _as_int(no_entry_payload.get("paper_fill_count")) == 0
    )
    if failure_count > 0 and failure_count == execution_events_loaded and no_order_activity:
        return 0
    return failure_count


def _status_for(
    *,
    primary: str,
    scores: dict[str, int],
    replay: ReplayReport | None,
    no_entry: NoEntryReport | None,
    replay_payload: dict[str, Any] | None = None,
    no_entry_payload: dict[str, Any] | None = None,
    load_errors: list[str],
    no_data: bool = False,
) -> tuple[str, list[str], list[str]]:
    fail_reasons: list[str] = []
    caution_reasons: list[str] = []
    if load_errors:
        caution_reasons.extend(load_errors)
    if no_data:
        caution_reasons.append("no_data_for_time_filter")
    if replay is not None and replay.bad_json_lines > 0:
        fail_reasons.append("bad_json_lines_present")
    if no_entry is not None and no_entry.bad_json_lines > 0:
        fail_reasons.append("no_entry_bad_json_lines_present")
    if _as_int((replay_payload or {}).get("bad_json_lines")) > 0:
        fail_reasons.append("bad_json_lines_present")
    if _as_int((no_entry_payload or {}).get("bad_json_lines")) > 0:
        fail_reasons.append("no_entry_bad_json_lines_present")
    if scores.get("execution_failures", 0) > 0:
        fail_reasons.append("execution_failures_present")
    if scores.get("websocket_instability", 0) >= 5:
        fail_reasons.append("websocket_instability_high")
    if scores.get("stale_data", 0) >= 5:
        fail_reasons.append("stale_data_high")

    if primary not in {"healthy_no_signal"}:
        caution_reasons.append(f"primary_bottleneck:{primary}")
    if replay is not None and replay.total_trades == 0 and replay.skipped_decisions > 0:
        caution_reasons.append("zero_trades_with_skips")
    if no_entry is not None and no_entry.total_scanned == 0:
        caution_reasons.append("no_session_rows_found")
    if replay is None and _as_int((replay_payload or {}).get("total_trades")) == 0 and _as_int((replay_payload or {}).get("skipped_decisions")) > 0:
        caution_reasons.append("zero_trades_with_skips")
    if no_entry is None and no_entry_payload and _as_int(no_entry_payload.get("total_scanned")) == 0:
        caution_reasons.append("no_session_rows_found")

    status = DECISION_FAIL if fail_reasons else DECISION_CAUTION if caution_reasons else DECISION_PASS
    return status, sorted(set(fail_reasons)), sorted(set(caution_reasons))


def _pairs_total(pairs: Any, *, exclude: set[str] | None = None) -> int:
    exclude = exclude or set()
    total = 0
    for item in pairs or []:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        label = str(item[0] or "").upper()
        if label in exclude:
            continue
        total += _as_int(item[1])
    return total


def _build_market_readiness_summary(
    *,
    markets_seen: int,
    orderbook_reason_counts: Counter[str],
    skip_counts: Counter[str],
    replay_payload: dict[str, Any],
    no_entry_payload: dict[str, Any],
    spread_compression_summary: dict[str, Any],
) -> dict[str, Any]:
    missing_token_count = _as_int(orderbook_reason_counts.get("missing_token_id"))
    stale_book_count = _as_int(skip_counts.get("stale_data")) + sum(
        _as_int(orderbook_reason_counts.get(reason))
        for reason in STALE_ORDERBOOK_REASONS
    )
    empty_book_count = max(
        _as_int(orderbook_reason_counts.get("empty_book")),
        _as_int(replay_payload.get("empty_book_recovery_attempted_count")),
    )
    unavailable_count = sum(
        _as_int(orderbook_reason_counts.get(reason))
        for reason in HARDBLOCK_ORDERBOOK_REASONS
    )
    warmup_count = _as_int(orderbook_reason_counts.get("warmup_pending"))
    liquidity_ready_count = _pairs_total(
        replay_payload.get("liquidity_states", []),
        exclude=LIQUIDITY_NOT_READY_STATES,
    )
    spread_ready_count = _as_int(spread_compression_summary.get("normalized_spread_events"))
    observed_markets = max(
        _as_int(markets_seen),
        _as_int(spread_compression_summary.get("events_counted")),
        unavailable_count + warmup_count + stale_book_count,
    )
    token_mapping_warnings = _as_int(no_entry_payload.get("market_data_quality", {}).get("token_mapping_warning_count", 0))
    token_ready_count = max(0, observed_markets - missing_token_count - token_mapping_warnings)
    orderbook_ready_count = max(0, observed_markets - unavailable_count - warmup_count - stale_book_count)
    return {
        "token_ready_count": int(token_ready_count),
        "orderbook_ready_count": int(orderbook_ready_count),
        "empty_book_count": int(empty_book_count),
        "stale_book_count": int(stale_book_count),
        "liquidity_ready_count": int(liquidity_ready_count),
        "spread_ready_count": int(spread_ready_count),
    }


def _build_candidate_timing_summary(candidate_gap_summary: dict[str, Any]) -> dict[str, Any]:
    candidates_seen = _as_int(candidate_gap_summary.get("events_counted"))
    pre_cutoff = _as_int(candidate_gap_summary.get("pre_cutoff_candidate_count"))
    late = _as_int(candidate_gap_summary.get("cutoff_or_late_candidate_count"))
    closest_valid = candidate_gap_summary.get("closest_valid_candidate_seconds_remaining")
    if closest_valid is None:
        closest_valid = candidate_gap_summary.get("seconds_remaining_at_closest_candidate")
    return {
        "candidates_seen": int(candidates_seen),
        "pre_cutoff_candidates": int(pre_cutoff),
        "late_candidates": int(late),
        "avg_seconds_remaining_at_candidate": _as_float(candidate_gap_summary.get("avg_seconds_remaining_at_candidate")),
        "closest_valid_candidate_seconds_remaining": closest_valid,
    }


def _classify_cutoff_root_or_symptom(candidate_gap_summary: dict[str, Any], *, cutoff_blocks: int, late_candidates: int) -> str:
    interpretation = str(candidate_gap_summary.get("cutoff_interpretation", "") or "").upper()
    diagnosis = str(candidate_gap_summary.get("candidate_gap_diagnosis", "") or "").upper()
    if interpretation == "ROOT_CAUSE" or diagnosis == "CUTOFF_TOO_STRICT":
        return "ROOT_CAUSE"
    if interpretation == "FINAL_SYMPTOM":
        return "FINAL_SYMPTOM"
    if cutoff_blocks and late_candidates:
        return "MIXED"
    return "INSUFFICIENT_DATA"


def _build_cutoff_summary(
    *,
    skip_counts: Counter[str],
    replay_payload: dict[str, Any],
    candidate_gap_summary: dict[str, Any],
) -> dict[str, Any]:
    cutoff_blocks = max(
        _as_int(replay_payload.get("cutoff_block_count")),
        _as_int(skip_counts.get("time_unsafe")),
    )
    hard_close_blocks = _as_int(replay_payload.get("late_entry_hard_block_count"))
    hard_close_blocks += sum(
        count
        for reason, count in _counter_from_pairs(replay_payload.get("adaptive_cutoff_denied_reasons", [])).items()
        if "hard_close" in reason
    )
    hard_close_blocks += sum(
        count
        for reason, count in _counter_from_pairs(replay_payload.get("micro_timing_denied_reasons", [])).items()
        if "hard_close" in reason
    )
    late_candidates = _as_int(candidate_gap_summary.get("cutoff_or_late_candidate_count"))
    return {
        "cutoff_blocks": int(cutoff_blocks),
        "hard_close_blocks": int(hard_close_blocks),
        "cutoff_after_late_candidate": bool(cutoff_blocks and late_candidates),
        "cutoff_as_root_or_symptom": _classify_cutoff_root_or_symptom(
            candidate_gap_summary,
            cutoff_blocks=cutoff_blocks,
            late_candidates=late_candidates,
        ),
    }


def _classify_lifecycle_bottleneck(
    *,
    timing_quality: dict[str, Any],
    market_readiness: dict[str, Any],
    candidate_timing: dict[str, Any],
    cutoff_summary: dict[str, Any],
    orderbook_reason_counts: Counter[str],
    candidate_gap_summary: dict[str, Any],
    spread_compression_summary: dict[str, Any],
    risk_blocks: dict[str, Any],
    execution_summary: dict[str, Any],
    no_data: bool,
) -> str:
    if no_data:
        return "INSUFFICIENT_DATA"
    first_seen = _as_float(timing_quality.get("first_seen_seconds_remaining"))
    first_evaluable = _as_float(timing_quality.get("first_evaluable_seconds_remaining"))
    if first_seen and first_seen <= 120:
        return "MARKET_DISCOVERY_DELAY"
    if _as_int(orderbook_reason_counts.get("missing_token_id")):
        return "TOKEN_ID_DELAY"
    if _as_int(orderbook_reason_counts.get("warmup_pending")):
        return "ORDERBOOK_WARMUP_DELAY"
    if _as_int(market_readiness.get("empty_book_count")):
        return "EMPTY_BOOK_DELAY"
    if (
        str(candidate_gap_summary.get("candidate_gap_diagnosis", "")) == "SPREAD_TOO_WIDE"
        or str(spread_compression_summary.get("spread_state_before_cutoff", "")) == "WIDE_PRE_CUTOFF"
        or str(spread_compression_summary.get("spread_compression_diagnosis", "")) in {"SPREAD_NEVER_NORMALIZED", "SPREAD_NORMALIZED_TOO_LATE"}
    ):
        return "SPREAD_READINESS_DELAY"
    if str(candidate_gap_summary.get("candidate_gap_diagnosis", "")) == "LIQUIDITY_NOT_READY":
        return "LIQUIDITY_READINESS_DELAY"
    if first_evaluable and first_evaluable <= 120:
        return "ORDERBOOK_WARMUP_DELAY"
    if _as_int(candidate_timing.get("late_candidates")) and not _as_int(candidate_timing.get("pre_cutoff_candidates")):
        return "LATE_CANDIDATE"
    if cutoff_summary.get("cutoff_as_root_or_symptom") == "FINAL_SYMPTOM":
        return "CUTOFF_FINAL_SYMPTOM"
    if _as_int(risk_blocks.get("risk_plan_zero_count")) or _as_int(risk_blocks.get("risk_reject_count")) or _as_int(execution_summary.get("execution_failure_count")):
        return "RISK_EXECUTION_BLOCK"
    if _as_float(timing_quality.get("average_decision_latency_ms")) > 2000:
        return "SIGNAL_EVALUATION_DELAY"
    return "INSUFFICIENT_DATA"


def _build_scanner_lifecycle_summary(
    *,
    markets_seen: int,
    timing_quality: dict[str, Any],
    market_readiness: dict[str, Any],
    candidate_timing: dict[str, Any],
    cutoff_summary: dict[str, Any],
    orderbook_reason_counts: Counter[str],
    candidate_gap_summary: dict[str, Any],
    spread_compression_summary: dict[str, Any],
    risk_blocks: dict[str, Any],
    execution_summary: dict[str, Any],
    no_data: bool,
) -> dict[str, Any]:
    return {
        "markets_seen": int(markets_seen),
        "first_seen_seconds_remaining": _as_float(timing_quality.get("first_seen_seconds_remaining")),
        "first_evaluable_seconds_remaining": _as_float(timing_quality.get("first_evaluable_seconds_remaining")),
        "avg_seconds_remaining": _as_float(timing_quality.get("average_seconds_remaining")),
        "min_seconds_remaining": _as_float(timing_quality.get("min_seconds_remaining")),
        "dominant_lifecycle_bottleneck": _classify_lifecycle_bottleneck(
            timing_quality=timing_quality,
            market_readiness=market_readiness,
            candidate_timing=candidate_timing,
            cutoff_summary=cutoff_summary,
            orderbook_reason_counts=orderbook_reason_counts,
            candidate_gap_summary=candidate_gap_summary,
            spread_compression_summary=spread_compression_summary,
            risk_blocks=risk_blocks,
            execution_summary=execution_summary,
            no_data=no_data,
        ),
    }


def evaluate_session_runtime(
    *,
    session_summary: dict[str, Any] | None = None,
    replay_report: ReplayReport | dict[str, Any] | None = None,
    no_entry_report: NoEntryReport | dict[str, Any] | None = None,
    date: str | None = None,
    quant_data_dir: str | Path = DEFAULT_QUANT_DATA_DIR,
    realtime_log_dir: str | Path = DEFAULT_REALTIME_LOG_DIR,
    load_offline_reports: bool = True,
    since: str | None = None,
    until: str | None = None,
    run_id: str | None = None,
) -> SessionRuntimeEvaluation:
    date = date or _today_utc()
    time_filter = _time_filter_payload(date=date, since=since, until=until, run_id=run_id)
    time_filter_applied = bool(time_filter.get("applied"))
    run_id_applied = bool(time_filter.get("run_id_applied"))
    load_errors: list[str] = []
    replay_obj: ReplayReport | None = replay_report if isinstance(replay_report, ReplayReport) else None
    no_entry_obj: NoEntryReport | None = no_entry_report if isinstance(no_entry_report, NoEntryReport) else None

    if load_offline_reports and replay_obj is None:
        replay_obj, error = _safe_analyze_replay(
            date=date,
            quant_data_dir=quant_data_dir,
            since_utc=time_filter.get("since_utc"),
            until_utc=time_filter.get("until_utc"),
            run_id=time_filter.get("run_id"),
        )
        if error:
            load_errors.append(error)
    if load_offline_reports and no_entry_obj is None and (run_id_applied or not time_filter_applied):
        no_entry_obj, error = _safe_analyze_no_entries(
            date=date,
            quant_data_dir=quant_data_dir,
            realtime_log_dir=realtime_log_dir,
            run_id=time_filter.get("run_id"),
        )
        if error:
            load_errors.append(error)

    replay_payload = (
        replay_obj.to_dict()
        if replay_obj is not None
        else dict(replay_report or {}) if isinstance(replay_report, dict) else {}
    )
    no_entry_payload = (
        no_entry_obj.to_dict()
        if no_entry_obj is not None
        else dict(no_entry_report or {}) if isinstance(no_entry_report, dict) else {}
    )

    if no_entry_payload.get("skip_reason_counts"):
        skip_counts = Counter({str(k): _as_int(v) for k, v in dict(no_entry_payload["skip_reason_counts"]).items()})
    else:
        replay_counts = _skip_counts_from_replay(replay_obj or replay_payload)
        skip_counts = replay_counts if replay_counts else _skip_counts_from_session(session_summary)

    raw_execution_summary = (
        _load_execution_jsonl_summary(quant_data_dir, date, time_filter=time_filter)
        if load_offline_reports and replay_report is None and no_entry_report is None
        else None
    )
    execution_failure_count = _resolved_execution_failure_count(
        replay_payload=replay_payload,
        no_entry_payload=no_entry_payload,
        raw_execution_summary=raw_execution_summary,
    )
    bankroll_visibility = _merge_bankroll_visibility(
        session_summary=session_summary,
        event_visibility=_load_bankroll_visibility_from_events(
            base_dir=quant_data_dir,
            date=date,
            time_filter=time_filter,
        ),
    )
    regime_summary = _merge_regime_summary(
        replay_payload=replay_payload,
        event_summary=(
            _load_regime_summary_from_events(
                base_dir=quant_data_dir,
                date=date,
                time_filter=time_filter,
            )
            if load_offline_reports
            else {}
        ),
    )
    cutoff_by_regime = (
        _load_cutoff_by_regime_from_events(
            base_dir=quant_data_dir,
            date=date,
            time_filter=time_filter,
        )
        if load_offline_reports
        else dict(replay_payload.get("cutoff_by_regime", {})) if isinstance(replay_payload.get("cutoff_by_regime"), dict) else {}
    )
    candidate_gap_summary = (
        _load_candidate_gap_summary_from_events(
            base_dir=quant_data_dir,
            date=date,
            time_filter=time_filter,
        )
        if load_offline_reports
        else dict(replay_payload.get("candidate_gap_summary", {})) if isinstance(replay_payload.get("candidate_gap_summary"), dict) else {}
    )
    spread_compression_summary = (
        _load_spread_compression_summary_from_events(
            base_dir=quant_data_dir,
            date=date,
            time_filter=time_filter,
        )
        if load_offline_reports
        else dict(replay_payload.get("spread_compression_summary", {})) if isinstance(replay_payload.get("spread_compression_summary"), dict) else {}
    )
    regime_replay_summary = (
        _load_regime_replay_summary_from_events(
            base_dir=quant_data_dir,
            date=date,
            time_filter=time_filter,
        )
        if load_offline_reports
        else dict(replay_payload.get("regime_replay_summary", {})) if isinstance(replay_payload.get("regime_replay_summary"), dict) else {}
    )
    regime_coverage_audit = (
        _load_regime_coverage_audit_from_events(
            base_dir=quant_data_dir,
            date=date,
            time_filter=time_filter,
        )
        if load_offline_reports
        else dict(replay_payload.get("regime_coverage_audit", {})) if isinstance(replay_payload.get("regime_coverage_audit"), dict) else {}
    )
    regime_probability_summary = (
        _load_regime_probability_summary_from_events(
            base_dir=quant_data_dir,
            date=date,
            time_filter=time_filter,
        )
        if load_offline_reports
        else dict(replay_payload.get("regime_probability_summary", {})) if isinstance(replay_payload.get("regime_probability_summary"), dict) else {}
    )
    liquidity_recovery_grace_summary = (
        _load_liquidity_recovery_grace_summary_from_events(
            base_dir=quant_data_dir,
            date=date,
            time_filter=time_filter,
        )
        if load_offline_reports
        else {}
    )
    phase2_coverage = (
        _load_phase2_coverage_from_events(
            base_dir=quant_data_dir,
            date=date,
            time_filter=time_filter,
        )
        if load_offline_reports
        else dict(
            replay_payload.get(
                "phase2_coverage",
                no_entry_payload.get("phase2_coverage", {}),
            )
        )
        if isinstance(replay_payload.get("phase2_coverage", no_entry_payload.get("phase2_coverage", {})), dict)
        else {}
    )
    if not phase2_coverage:
        phase2_coverage = build_phase2_coverage_from_events([])
    inventory_replay_readiness = _build_inventory_replay_readiness(phase2_coverage)
    partial_lifecycle_replay = (
        _load_partial_lifecycle_replay_from_events(
            base_dir=quant_data_dir,
            date=date,
            time_filter=time_filter,
        )
        if load_offline_reports
        else dict(
            replay_payload.get(
                "partial_lifecycle_replay",
                no_entry_payload.get("partial_lifecycle_replay", {}),
            )
        )
        if isinstance(
            replay_payload.get(
                "partial_lifecycle_replay",
                no_entry_payload.get("partial_lifecycle_replay", {}),
            ),
            dict,
        )
        else {}
    )
    if not partial_lifecycle_replay:
        partial_lifecycle_replay = build_partial_lifecycle_replay_from_events([])

    no_data = bool(
        (time_filter_applied or run_id_applied)
        and not session_summary
        and _as_int(replay_payload.get("events_loaded")) == 0
        and _as_int((raw_execution_summary or {}).get("execution_events_loaded")) == 0
        and _as_int(no_entry_payload.get("total_scanned")) == 0
    )
    scores = _build_scores(
        skip_counts=skip_counts,
        replay=replay_obj,
        no_entry=no_entry_obj,
        execution_failure_count=execution_failure_count,
        no_data=no_data,
    )
    if replay_obj is None and replay_payload:
        scores["cutoff"] += _as_int(replay_payload.get("cutoff_block_count"))
        scores["cutoff"] += _as_int(replay_payload.get("late_entry_hard_block_count"))
        if (
            _as_float(replay_payload.get("average_decision_latency_ms")) > 2000
            or _as_float(replay_payload.get("average_scan_cycle_duration_ms")) > 2500
        ):
            scores["latency"] += max(1, _as_int(replay_payload.get("skipped_decisions"), 1))
        if _as_float(replay_payload.get("max_orderbook_age_ms")) > 3000 or _as_float(replay_payload.get("max_oracle_age_ms")) > 10000:
            scores["stale_data"] += max(1, _as_int(replay_payload.get("skipped_decisions"), 1))
    if no_entry_obj is None and no_entry_payload:
        market_quality = no_entry_payload.get("market_data_quality", {})
        if isinstance(market_quality, dict):
            scores["market_readiness"] += _as_int(market_quality.get("token_mapping_warning_count"))
    orderbook_reason_counts = _orderbook_reason_counts(
        replay_payload=replay_payload,
        no_entry_payload=no_entry_payload,
        skip_counts=skip_counts,
    )
    if orderbook_reason_counts:
        scores["market_readiness"] += sum(orderbook_reason_counts.get(reason, 0) for reason in HARDBLOCK_ORDERBOOK_REASONS)
        scores["stale_data"] += sum(orderbook_reason_counts.get(reason, 0) for reason in STALE_ORDERBOOK_REASONS)
    primary, secondary = _rank_bottlenecks(scores)
    status, fail_reasons, caution_reasons = _status_for(
        primary=primary,
        scores=scores,
        replay=replay_obj,
        no_entry=no_entry_obj,
        replay_payload=replay_payload,
        no_entry_payload=no_entry_payload,
        load_errors=load_errors,
        no_data=no_data,
    )

    scanned = _as_int((session_summary or {}).get("total_markets_scanned"))
    entered = _as_int((session_summary or {}).get("total_trades_simulated"))
    skipped = sum(skip_counts.values())
    if no_entry_payload:
        scanned = max(scanned, _as_int(no_entry_payload.get("total_scanned")))
        entered = max(entered, _as_int(no_entry_payload.get("total_entered")))
        skipped = max(skipped, _as_int(no_entry_payload.get("total_skipped")))
    if replay_payload:
        skipped = max(skipped, _as_int(replay_payload.get("skipped_decisions")))

    top_skips = [[reason, count] for reason, count in skip_counts.most_common(5)]
    hard_orderbook_unavailable_count = (
        sum(orderbook_reason_counts.get(reason, 0) for reason in HARDBLOCK_ORDERBOOK_REASONS)
        if orderbook_reason_counts
        else skip_counts.get("orderbook_unavailable", 0) + skip_counts.get("no_orderbook", 0)
    )
    stale_orderbook_count = sum(orderbook_reason_counts.get(reason, 0) for reason in STALE_ORDERBOOK_REASONS)
    recommendations = _recommendations(
        primary,
        secondary,
        status,
        no_entry_obj,
        replay_obj,
        execution_failure_count=execution_failure_count,
    )
    timing_quality = {
        "average_seconds_remaining": _as_float(replay_payload.get("average_seconds_remaining")),
        "min_seconds_remaining": _as_float(replay_payload.get("min_seconds_remaining")),
        "average_seconds_since_open": _as_float(replay_payload.get("average_seconds_since_open")),
        "average_seconds_until_close": _as_float(replay_payload.get("average_seconds_until_close")),
        "first_seen_seconds_remaining": _as_float(replay_payload.get("first_seen_seconds_remaining")),
        "first_evaluable_seconds_remaining": _as_float(replay_payload.get("first_evaluable_seconds_remaining")),
        "active_window_alignment_reasons": replay_payload.get("active_window_alignment_reasons", []),
        "average_scan_cycle_duration_ms": _as_float(replay_payload.get("average_scan_cycle_duration_ms")),
        "average_decision_latency_ms": _as_float(replay_payload.get("average_decision_latency_ms")),
        "max_decision_latency_ms": _as_float(replay_payload.get("max_decision_latency_ms")),
    }
    risk_blocks = {
        "risk_plan_zero_count": int(skip_counts.get("risk_plan_zero", 0)),
        "risk_reject_count": _as_int(replay_payload.get("risk_reject_count")),
        "risk_mode": str((session_summary or {}).get("risk_mode", "")),
        "risk_mode_allow_new_entries": (session_summary or {}).get("risk_mode_allow_new_entries"),
        **bankroll_visibility,
    }
    execution_summary = {
        "execution_failure_count": execution_failure_count,
        "execution_events_loaded": _as_int(
            (raw_execution_summary or {}).get(
                "execution_events_loaded",
                no_entry_payload.get("execution_events_loaded"),
            )
        ),
        "approved_decisions": _as_int(replay_payload.get("approved_decisions")),
        "rejected_decisions": _as_int(replay_payload.get("rejected_decisions")),
        "order_submit_attempt_count": _as_int(no_entry_payload.get("order_submit_attempt_count")),
        "paper_fill_count": _as_int(no_entry_payload.get("paper_fill_count")),
    }
    market_readiness = _build_market_readiness_summary(
        markets_seen=scanned,
        orderbook_reason_counts=orderbook_reason_counts,
        skip_counts=skip_counts,
        replay_payload=replay_payload,
        no_entry_payload=no_entry_payload,
        spread_compression_summary=spread_compression_summary,
    )
    candidate_timing = _build_candidate_timing_summary(candidate_gap_summary)
    cutoff_summary = _build_cutoff_summary(
        skip_counts=skip_counts,
        replay_payload=replay_payload,
        candidate_gap_summary=candidate_gap_summary,
    )
    scanner_lifecycle = _build_scanner_lifecycle_summary(
        markets_seen=scanned,
        timing_quality=timing_quality,
        market_readiness=market_readiness,
        candidate_timing=candidate_timing,
        cutoff_summary=cutoff_summary,
        orderbook_reason_counts=orderbook_reason_counts,
        candidate_gap_summary=candidate_gap_summary,
        spread_compression_summary=spread_compression_summary,
        risk_blocks=risk_blocks,
        execution_summary=execution_summary,
        no_data=no_data,
    )
    return SessionRuntimeEvaluation(
        date=date,
        generated_at_utc=_utc_now(),
        session_status=status,
        primary_bottleneck=primary,
        run_id=str(run_id or ""),
        secondary_bottleneck=secondary,
        bottleneck_scores=scores,
        health_summary={
            "scanned": scanned,
            "entered": entered,
            "skipped": skipped,
            "paper_orders_created": _as_int((session_summary or {}).get("paper_orders_created")),
            "paper_fills": _as_int((session_summary or {}).get("paper_fills")),
            "paper_exits": _as_int((session_summary or {}).get("paper_exits")),
            "gross_pnl": _as_float(replay_payload.get("gross_pnl", (session_summary or {}).get("simulated_pnl", 0.0))),
            "max_drawdown": _as_float((session_summary or {}).get("max_drawdown", 0.0)),
        },
        skip_summary={
            "top_skip_reasons": top_skips,
            "skip_reason_counts": dict(skip_counts.most_common()),
        },
        timing_quality=timing_quality,
        scanner_lifecycle=scanner_lifecycle,
        market_readiness=market_readiness,
        candidate_timing=candidate_timing,
        cutoff_behavior={
            "time_unsafe_count": int(skip_counts.get("time_unsafe", 0)),
            "cutoff_block_count": _as_int(replay_payload.get("cutoff_block_count")),
            "adaptive_cutoff_allowed_count": _as_int(replay_payload.get("adaptive_cutoff_allowed_count")),
            "adaptive_cutoff_denied_count": _as_int(replay_payload.get("adaptive_cutoff_denied_count")),
            "late_entry_hard_block_count": _as_int(replay_payload.get("late_entry_hard_block_count")),
            "adaptive_cutoff_reasons": replay_payload.get("adaptive_cutoff_reasons", []),
            "adaptive_cutoff_denied_reasons": replay_payload.get(
                "adaptive_cutoff_denied_reasons",
                replay_payload.get("adaptive_cutoff_reasons", []),
            ),
            "micro_timing_allowed_count": _as_int(replay_payload.get("micro_timing_allowed_count")),
            "micro_timing_denied_count": _as_int(replay_payload.get("micro_timing_denied_count")),
            "micro_timing_branch_entered_count": _as_int(replay_payload.get("micro_timing_branch_entered_count")),
            "micro_timing_candidate_count": _as_int(replay_payload.get("micro_timing_candidate_count")),
            "micro_timing_denied_reasons": replay_payload.get("micro_timing_denied_reasons", []),
            "micro_timing_branch_skipped_reasons": replay_payload.get("micro_timing_branch_skipped_reasons", []),
        },
        cutoff_summary=cutoff_summary,
        cutoff_by_regime=cutoff_by_regime,
        candidate_gap_summary=candidate_gap_summary,
        spread_compression_summary=spread_compression_summary,
        regime_replay_summary=regime_replay_summary,
        regime_coverage_audit=regime_coverage_audit,
        regime_probability_summary=regime_probability_summary,
        risk_blocks=risk_blocks,
        execution_summary=execution_summary,
        orderbook_readiness={
            "orderbook_unavailable_count": int(hard_orderbook_unavailable_count),
            "warmup_pending_count": int(orderbook_reason_counts.get("warmup_pending", 0)),
            "stale_data_count": int(skip_counts.get("stale_data", 0) + stale_orderbook_count),
            "reason_breakdown": [[reason, count] for reason, count in orderbook_reason_counts.most_common()],
            "clob_error_categories": _top_pairs_from_payloads(
                replay_payload,
                no_entry_payload,
                key="clob_error_categories",
            ),
            "clob_exception_types": _top_pairs_from_payloads(
                replay_payload,
                no_entry_payload,
                key="clob_exception_types",
            ),
            "clob_error_classes": _top_pairs_from_payloads(
                replay_payload,
                no_entry_payload,
                key="clob_error_classes",
            ),
            "clob_backoff_active_count": _as_int(replay_payload.get("clob_backoff_active_count")),
            "clob_circuit_open_count": _as_int(replay_payload.get("clob_circuit_open_count")),
            "max_clob_error_rate": _as_float(replay_payload.get("max_clob_error_rate")),
            "clob_recovery_count": _as_int(replay_payload.get("clob_recovery_count")),
            "empty_book_recovery_attempted": _as_int(replay_payload.get("empty_book_recovery_attempted_count")),
            "empty_book_recovery_success": _as_int(replay_payload.get("empty_book_recovery_success_count")),
            "empty_book_recovery_failed": _as_int(replay_payload.get("empty_book_recovery_failed_count")),
            "empty_book_recovery_retry_count": _as_int(replay_payload.get("empty_book_recovery_retry_count")),
            "liquidity_recovery_research_mode_events": _as_int(liquidity_recovery_grace_summary.get("liquidity_recovery_research_mode_events")),
            "recovery_branch_candidate_seen": _as_int(liquidity_recovery_grace_summary.get("recovery_branch_candidate_seen")),
            "recovery_branch_preempted_by_cutoff": _as_int(liquidity_recovery_grace_summary.get("recovery_branch_preempted_by_cutoff")),
            "recovery_branch_mode_disabled": _as_int(liquidity_recovery_grace_summary.get("recovery_branch_mode_disabled")),
            "recovery_branch_enter_condition_failed": _as_int(liquidity_recovery_grace_summary.get("recovery_branch_enter_condition_failed")),
            "liquidity_recovery_grace_entered": _as_int(liquidity_recovery_grace_summary.get("liquidity_recovery_grace_entered")),
            "liquidity_recovery_grace_success": _as_int(liquidity_recovery_grace_summary.get("liquidity_recovery_grace_success")),
            "liquidity_recovery_grace_failed": _as_int(liquidity_recovery_grace_summary.get("liquidity_recovery_grace_failed")),
            "recovery_wait_seconds": _as_float(liquidity_recovery_grace_summary.get("average_recovery_wait_seconds")),
            "average_recovery_wait_seconds": _as_float(liquidity_recovery_grace_summary.get("average_recovery_wait_seconds")),
            "max_recovery_wait_seconds": _as_float(liquidity_recovery_grace_summary.get("max_recovery_wait_seconds")),
            "recovered_before_cutoff": _as_int(liquidity_recovery_grace_summary.get("recovered_before_cutoff")),
            "candidate_survived_recovery": _as_int(liquidity_recovery_grace_summary.get("candidate_survived_recovery")),
            "recovery_exit_reason": str(liquidity_recovery_grace_summary.get("dominant_recovery_exit_reason", "")),
            "recovery_exit_reasons": liquidity_recovery_grace_summary.get("recovery_exit_reasons", []),
            "recovery_branch_skipped_reasons": liquidity_recovery_grace_summary.get("recovery_branch_skipped_reasons", []),
            "liquidity_states": replay_payload.get("liquidity_states", []),
            "average_orderbook_age_ms": _as_float(replay_payload.get("average_orderbook_age_ms", no_entry_payload.get("market_data_quality", {}).get("average_orderbook_age_ms", 0.0))),
            "max_orderbook_age_ms": _as_float(replay_payload.get("max_orderbook_age_ms")),
            "average_oracle_age_ms": _as_float(replay_payload.get("average_oracle_age_ms")),
            "token_mapping_warning_count": _as_int(no_entry_payload.get("market_data_quality", {}).get("token_mapping_warning_count", 0)),
        },
        regime_summary=regime_summary,
        phase2_coverage=phase2_coverage,
        inventory_replay_readiness=inventory_replay_readiness,
        partial_lifecycle_replay=partial_lifecycle_replay,
        lifecycle_replay_confidence=str(partial_lifecycle_replay.get("lifecycle_replay_confidence", "INSUFFICIENT")),
        replay_supported_sections=list(partial_lifecycle_replay.get("replay_supported_sections", [])),
        replay_unsupported_sections=list(partial_lifecycle_replay.get("replay_unsupported_sections", [])),
        missed_starter_candidates=list(partial_lifecycle_replay.get("missed_starter_candidates", [])),
        timing_decay_summary=dict(partial_lifecycle_replay.get("timing_decay_summary", {})),
        spread_liquidity_readiness_summary=dict(partial_lifecycle_replay.get("spread_liquidity_readiness_summary", {})),
        recommendations=recommendations,
        reports_used={
            "session_summary": bool(session_summary),
            "replay_report": bool(replay_payload),
            "no_entry_report": bool(no_entry_payload),
            "execution_log_recomputed": raw_execution_summary is not None,
            "load_errors": load_errors,
        },
        time_filter={
            "applied": bool(time_filter_applied),
            "timezone": "UTC",
            "since": since,
            "until": until,
            "run_id": run_id,
            "run_id_applied": bool(run_id_applied),
            "range": str(time_filter.get("display") or ""),
            "semantics": "half_open_since_inclusive_until_exclusive",
        },
        fail_reasons=fail_reasons,
        caution_reasons=caution_reasons,
    )


def _recommendations(
    primary: str,
    secondary: str,
    status: str,
    no_entry: NoEntryReport | None,
    replay: ReplayReport | None,
    *,
    execution_failure_count: int = 0,
) -> list[str]:
    recommendations: list[str] = []
    if status == DECISION_FAIL:
        recommendations.append("Preserve runtime evidence and review failures before trusting the session.")
    if primary == "cutoff":
        recommendations.append("Cutoff remains the dominant bottleneck; compare adaptive cutoff outcomes against seconds_remaining before changing strategy.")
    elif primary == "market_readiness":
        recommendations.append("Market readiness is dominant; inspect token IDs, orderbook availability, and active-window discovery.")
    elif primary == "risk_plan_zero":
        recommendations.append("Risk plan zero is dominant; inspect bankroll tier, minimum order size, and sizing diagnostics without loosening risk.")
    elif primary == "strategy_thresholds":
        recommendations.append("Strategy thresholds are dominant; collect more paper evidence before considering research changes.")
    elif primary == "latency":
        recommendations.append("Latency is elevated; inspect cycle duration and decision latency before changing cutoffs.")
    elif primary == "healthy_no_signal":
        recommendations.append("No severe bottleneck found; this may be a healthy no-signal session.")
    elif primary == "no_data":
        recommendations.append("No events matched the UTC time filter; adjust --since/--until or evaluate the full date.")
    if secondary not in {"none", primary}:
        recommendations.append(f"Secondary bottleneck to monitor: {secondary}.")
    if no_entry and no_entry.recommendations:
        no_entry_recommendations = no_entry.recommendations
        if not execution_failure_count:
            no_entry_recommendations = [
                item for item in no_entry_recommendations if "execution" not in item.lower()
            ]
        recommendations.extend(no_entry_recommendations[:2])
    if execution_failure_count:
        recommendations.append("Execution failures were present; keep live execution disabled and inspect execution_log.")
    return list(dict.fromkeys(recommendations))[:3]


def _format_compact_terminal_summary(evaluation: SessionRuntimeEvaluation) -> list[str]:
    health = evaluation.health_summary
    lifecycle = evaluation.scanner_lifecycle
    readiness = evaluation.market_readiness
    candidate_timing = evaluation.candidate_timing
    cutoff_summary = evaluation.cutoff_summary
    regime_probability = evaluation.regime_probability_summary
    risk = evaluation.risk_blocks
    execution = evaluation.execution_summary
    time_filter = evaluation.time_filter or {}
    research = regime_probability.get("research_questions", {}) if isinstance(regime_probability, dict) else {}
    return [
        (
            f"filter={time_filter.get('range', 'none')} "
            f"timezone={time_filter.get('timezone', 'UTC')} "
            f"semantics={time_filter.get('semantics', 'none')}"
        ),
        (
            f"SESSION_STATUS={evaluation.session_status} "
            f"PRIMARY_BOTTLENECK={evaluation.primary_bottleneck} "
            f"SECONDARY_BOTTLENECK={evaluation.secondary_bottleneck}"
        ),
        (
            "session_health "
            f"scanned={health.get('scanned', 0)} entered={health.get('entered', 0)} "
            f"skipped={health.get('skipped', 0)} orders={health.get('paper_orders_created', 0)} "
            f"fills={health.get('paper_fills', 0)}"
        ),
        (
            "scanner_lifecycle "
            f"markets_seen={lifecycle.get('markets_seen', 0)} "
            f"first_seen={lifecycle.get('first_seen_seconds_remaining', 0.0):.2f} "
            f"first_evaluable={lifecycle.get('first_evaluable_seconds_remaining', 0.0):.2f} "
            f"avg_seconds_remaining={lifecycle.get('avg_seconds_remaining', 0.0):.2f} "
            f"min_seconds_remaining={lifecycle.get('min_seconds_remaining', 0.0):.2f} "
            f"dominant={lifecycle.get('dominant_lifecycle_bottleneck', '')}"
        ),
        (
            "market_readiness "
            f"token_ready={readiness.get('token_ready_count', 0)} "
            f"orderbook_ready={readiness.get('orderbook_ready_count', 0)} "
            f"empty_book={readiness.get('empty_book_count', 0)} "
            f"stale_book={readiness.get('stale_book_count', 0)} "
            f"liquidity_ready={readiness.get('liquidity_ready_count', 0)} "
            f"spread_ready={readiness.get('spread_ready_count', 0)}"
        ),
        (
            "candidate_timing "
            f"candidates_seen={candidate_timing.get('candidates_seen', 0)} "
            f"pre_cutoff={candidate_timing.get('pre_cutoff_candidates', 0)} "
            f"late={candidate_timing.get('late_candidates', 0)} "
            f"avg_candidate_seconds={candidate_timing.get('avg_seconds_remaining_at_candidate', 0.0):.2f} "
            f"closest_valid_seconds={candidate_timing.get('closest_valid_candidate_seconds_remaining')}"
        ),
        (
            "cutoff_summary "
            f"cutoff_blocks={cutoff_summary.get('cutoff_blocks', 0)} "
            f"hard_close_blocks={cutoff_summary.get('hard_close_blocks', 0)} "
            f"cutoff_after_late_candidate={str(bool(cutoff_summary.get('cutoff_after_late_candidate', False))).lower()} "
            f"cutoff_as_root_or_symptom={cutoff_summary.get('cutoff_as_root_or_symptom', '')}"
        ),
        (
            "regime_probability "
            f"market_regimes={regime_probability.get('market_regimes', [])[:5]} "
            f"probability_fields={regime_probability.get('events_with_probability_fields', 0)} "
            f"top_skip_regime={research.get('most_skip_regime', '')} "
            f"phase2_signal={regime_probability.get('diagnostic_usefulness_for_inventory_replay', '')}"
        ),
        (
            "risk_execution "
            f"risk_plan_zero={risk.get('risk_plan_zero_count', 0)} "
            f"risk_rejects={risk.get('risk_reject_count', 0)} "
            f"execution_failures={execution.get('execution_failure_count', 0)} "
            f"paper_orders={health.get('paper_orders_created', 0)} "
            f"paper_fills={health.get('paper_fills', 0)} "
            f"tier_id={risk.get('bankroll_tier_id', '')} "
            f"family={risk.get('bankroll_family', '')} "
            f"bankroll_mode={risk.get('bankroll_mode', '')} "
            f"micro_survival_active={str(bool(risk.get('micro_survival_active', False))).lower()}"
        ),
        f"top_skip_reasons={evaluation.skip_summary.get('top_skip_reasons', [])}",
        f"recommendations={evaluation.recommendations[:3]}",
    ]


def format_terminal_summary(evaluation: SessionRuntimeEvaluation, *, verbose: bool = False) -> list[str]:
    if not verbose:
        return _format_compact_terminal_summary(evaluation)
    health = evaluation.health_summary
    timing = evaluation.timing_quality
    cutoff = evaluation.cutoff_behavior
    cutoff_by_regime = evaluation.cutoff_by_regime
    candidate_gap = evaluation.candidate_gap_summary
    spread_compression = evaluation.spread_compression_summary
    regime_replay = evaluation.regime_replay_summary
    regime_coverage = evaluation.regime_coverage_audit
    regime_probability = evaluation.regime_probability_summary
    orderbook = evaluation.orderbook_readiness
    regimes = evaluation.regime_summary
    risk = evaluation.risk_blocks
    execution = evaluation.execution_summary
    phase2 = evaluation.inventory_replay_readiness
    lifecycle_replay = evaluation.partial_lifecycle_replay
    time_filter = evaluation.time_filter or {}
    return [
        (
            f"filter={time_filter.get('range', 'none')} "
            f"timezone={time_filter.get('timezone', 'UTC')} "
            f"semantics={time_filter.get('semantics', 'none')}"
        ),
        (
            f"SESSION_STATUS={evaluation.session_status} "
            f"PRIMARY_BOTTLENECK={evaluation.primary_bottleneck} "
            f"SECONDARY_BOTTLENECK={evaluation.secondary_bottleneck}"
        ),
        (
            "session_health "
            f"scanned={health.get('scanned', 0)} entered={health.get('entered', 0)} "
            f"skipped={health.get('skipped', 0)} orders={health.get('paper_orders_created', 0)} "
            f"fills={health.get('paper_fills', 0)}"
        ),
        (
            "timing "
            f"avg_seconds_remaining={timing.get('average_seconds_remaining', 0.0):.2f} "
            f"min_seconds_remaining={timing.get('min_seconds_remaining', 0.0):.2f} "
            f"first_seen_seconds_remaining={timing.get('first_seen_seconds_remaining', 0.0):.2f} "
            f"first_evaluable_seconds_remaining={timing.get('first_evaluable_seconds_remaining', 0.0):.2f} "
            f"alignment_reasons={timing.get('active_window_alignment_reasons', [])} "
            f"avg_cycle_ms={timing.get('average_scan_cycle_duration_ms', 0.0):.2f} "
            f"avg_decision_latency_ms={timing.get('average_decision_latency_ms', 0.0):.2f}"
        ),
        (
            "cutoff "
            f"time_unsafe={cutoff.get('time_unsafe_count', 0)} "
            f"blocks={cutoff.get('cutoff_block_count', 0)} "
            f"adaptive_allowed={cutoff.get('adaptive_cutoff_allowed_count', 0)} "
            f"adaptive_denied={cutoff.get('adaptive_cutoff_denied_count', 0)} "
            f"deny_reasons={cutoff.get('adaptive_cutoff_denied_reasons', [])} "
            f"micro_timing_allowed={cutoff.get('micro_timing_allowed_count', 0)} "
            f"micro_timing_denied={cutoff.get('micro_timing_denied_count', 0)} "
            f"micro_branch_entered={cutoff.get('micro_timing_branch_entered_count', 0)} "
            f"micro_candidates={cutoff.get('micro_timing_candidate_count', 0)} "
            f"micro_deny_reasons={cutoff.get('micro_timing_denied_reasons', [])} "
            f"micro_branch_skips={cutoff.get('micro_timing_branch_skipped_reasons', [])}"
        ),
        (
            "cutoff_by_regime "
            f"events={cutoff_by_regime.get('events_counted', 0)} "
            f"volatility={cutoff_by_regime.get('volatility_regime', {})} "
            f"trend={cutoff_by_regime.get('trend_regime', {})} "
            f"combo={cutoff_by_regime.get('combo', {})} "
            f"late_window_opportunity={cutoff_by_regime.get('late_window_opportunity', {})}"
        ),
        (
            "candidate_gap "
            f"events={candidate_gap.get('events_counted', 0)} "
            f"pre_cutoff={candidate_gap.get('pre_cutoff_candidate_count', 0)} "
            f"late={candidate_gap.get('cutoff_or_late_candidate_count', 0)} "
            f"dominant={candidate_gap.get('dominant_gap_type', '')} "
            f"diagnosis={candidate_gap.get('candidate_gap_diagnosis', '')} "
            f"cutoff_interpretation={candidate_gap.get('cutoff_interpretation', '')} "
            f"closest_bucket={candidate_gap.get('closest_candidate_bucket', '')} "
            f"closest_seconds={candidate_gap.get('seconds_remaining_at_closest_candidate')} "
            f"final_pre_cutoff_reason={candidate_gap.get('final_pre_cutoff_block_reason', '')}"
        ),
        (
            "spread_compression "
            f"events={spread_compression.get('events_counted', 0)} "
            f"pre_cutoff={spread_compression.get('pre_cutoff_spread_events', 0)} "
            f"recovery_rate={spread_compression.get('spread_recovery_rate', 0.0):.4f} "
            f"avg_velocity={spread_compression.get('avg_spread_velocity', 0.0):.6f} "
            f"normalization_seconds={spread_compression.get('spread_normalization_seconds')} "
            f"state={spread_compression.get('spread_state_before_cutoff', '')} "
            f"diagnosis={spread_compression.get('spread_compression_diagnosis', '')} "
            f"closest_gap={spread_compression.get('closest_spread_gap_before_cutoff')}"
        ),
        (
            "regime_replay "
            f"events={regime_replay.get('events_counted', 0)} "
            f"classification={regime_replay.get('regime_tradeability_classification', '')} "
            f"unknown_coverage={regime_replay.get('unknown_regime_coverage', {})}"
        ),
        (
            "regime_coverage_audit "
            f"checked={regime_coverage.get('total_events_checked', 0)} "
            f"complete={regime_coverage.get('events_with_complete_regime', 0)} "
            f"missing_both={regime_coverage.get('events_missing_both', 0)} "
            f"unknown_share={regime_coverage.get('unknown_regime_share', 0.0):.4f} "
            f"sources={regime_coverage.get('suspected_missing_payload_sources', [])[:3]}"
        ),
        (
            "regime_probability "
            f"events={regime_probability.get('events_counted', 0)} "
            f"probability_fields={regime_probability.get('events_with_probability_fields', 0)} "
            f"skip_by_regime={regime_probability.get('skip_decisions_by_regime', {})} "
            f"enter_by_regime={regime_probability.get('enter_candidates_by_regime', {})} "
            f"blocked_bucket={regime_probability.get('dominant_blocked_probability_bucket', '')} "
            f"cutoff_timing={regime_probability.get('candidate_cutoff_timing', {}).get('diagnosis', '')} "
            f"phase2={regime_probability.get('diagnostic_usefulness_for_inventory_replay', '')}"
        ),
        (
            "orderbook "
            f"unavailable={orderbook.get('orderbook_unavailable_count', 0)} "
            f"warmup_pending={orderbook.get('warmup_pending_count', 0)} "
            f"stale={orderbook.get('stale_data_count', 0)} "
            f"avg_age_ms={orderbook.get('average_orderbook_age_ms', 0.0):.2f} "
            f"reasons={orderbook.get('reason_breakdown', [])} "
            f"clob_categories={orderbook.get('clob_error_categories', [])} "
            f"clob_error_rate={orderbook.get('max_clob_error_rate', 0.0):.4f} "
            f"backoff_active={orderbook.get('clob_backoff_active_count', 0)} "
            f"circuit_open={orderbook.get('clob_circuit_open_count', 0)} "
            f"empty_recovery_attempted={orderbook.get('empty_book_recovery_attempted', 0)} "
            f"empty_recovery_success={orderbook.get('empty_book_recovery_success', 0)} "
            f"empty_recovery_failed={orderbook.get('empty_book_recovery_failed', 0)} "
            f"empty_recovery_retries={orderbook.get('empty_book_recovery_retry_count', 0)} "
            f"recovery_branch_seen={orderbook.get('recovery_branch_candidate_seen', 0)} "
            f"recovery_branch_mode_disabled={orderbook.get('recovery_branch_mode_disabled', 0)} "
            f"recovery_branch_preempted_by_cutoff={orderbook.get('recovery_branch_preempted_by_cutoff', 0)} "
            f"liquidity_grace_entered={orderbook.get('liquidity_recovery_grace_entered', 0)} "
            f"liquidity_grace_success={orderbook.get('liquidity_recovery_grace_success', 0)} "
            f"liquidity_grace_failed={orderbook.get('liquidity_recovery_grace_failed', 0)} "
            f"candidate_survived_recovery={orderbook.get('candidate_survived_recovery', 0)} "
            f"recovery_exit_reason={orderbook.get('recovery_exit_reason', '')} "
            f"liquidity_states={orderbook.get('liquidity_states', [])}"
        ),
        (
            "regimes "
            f"events={regimes.get('events_counted', 0)} "
            f"volatility={regimes.get('volatility_regimes', [])} "
            f"trend={regimes.get('trend_regimes', [])}"
        ),
        (
            "inventory_replay_readiness "
            f"status={phase2.get('status', '')} "
            f"coverage_gaps={phase2.get('coverage_gap_count', 0)} "
            f"proxy_inferred={phase2.get('proxy_inferred_items', [])}"
        ),
        (
            "partial_lifecycle_replay "
            f"status={lifecycle_replay.get('status', '')} "
            f"confidence={lifecycle_replay.get('lifecycle_replay_confidence', '')} "
            f"missed_starters={len(lifecycle_replay.get('missed_starter_candidates', []))}"
        ),
        f"scanner_reset_plan={SCANNER_RESET_PLAN}",
        (
            "risk_execution "
            f"risk_plan_zero={risk.get('risk_plan_zero_count', 0)} "
            f"risk_rejects={risk.get('risk_reject_count', 0)} "
            f"execution_failures={execution.get('execution_failure_count', 0)} "
            f"tier_id={risk.get('bankroll_tier_id', '')} "
            f"tier_name={risk.get('bankroll_tier_name', '')} "
            f"family={risk.get('bankroll_family', '')} "
            f"profile={risk.get('bankroll_risk_profile', '')} "
            f"tier_locked={str(bool(risk.get('bankroll_tier_locked', False))).lower()} "
            f"hysteresis={str(bool(risk.get('bankroll_hysteresis_active', False))).lower()} "
            f"bankroll_mode={risk.get('bankroll_mode', '')} "
            f"micro_survival_active={str(bool(risk.get('micro_survival_active', False))).lower()} "
            f"micro_position_size={risk.get('micro_position_size', 0.0):.4f}"
        ),
        f"top_skip_reasons={evaluation.skip_summary.get('top_skip_reasons', [])}",
    ]


def write_session_runtime_report(
    evaluation: SessionRuntimeEvaluation,
    *,
    report_dir: str | Path | None = None,
) -> Path:
    output_dir = Path(report_dir or DEFAULT_REPORT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = ""
    time_filter = evaluation.time_filter or {}
    if time_filter.get("applied"):
        since = str(time_filter.get("since") or "start").replace(":", "")
        until = str(time_filter.get("until") or "end").replace(":", "")
        suffix = f"_{since}_to_{until}"
    safe_run_id = _safe_filename_token(evaluation.run_id or time_filter.get("run_id"))
    if safe_run_id:
        suffix = f"{suffix}_run_{safe_run_id}"
    output_path = output_dir / f"session_runtime_evaluation_{evaluation.date}{suffix}.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(evaluation.to_dict(), handle, indent=2, sort_keys=True)
    return output_path


def print_summary(evaluation: SessionRuntimeEvaluation, *, verbose: bool = False) -> None:
    print("Session Runtime Evaluation")
    for line in format_terminal_summary(evaluation, verbose=verbose):
        print(line)
    if verbose:
        print(f"recommendations={evaluation.recommendations[:3]}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate Polymarket paper session runtime bottlenecks.")
    parser.add_argument("--date", default=_today_utc(), help="Date in YYYY-MM-DD format.")
    parser.add_argument("--quant-data-dir", default=str(DEFAULT_QUANT_DATA_DIR), help="Quant data root directory.")
    parser.add_argument("--realtime-log-dir", default=str(DEFAULT_REALTIME_LOG_DIR), help="Realtime log root directory.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Report output directory.")
    parser.add_argument("--write-report", action="store_true", help="Write session_runtime_evaluation JSON under runtime/reports.")
    parser.add_argument("--since", default=None, help="UTC start time HH:MM for same-day filtering; inclusive.")
    parser.add_argument("--until", default=None, help="UTC end time HH:MM for same-day filtering; exclusive.")
    parser.add_argument("--run-id", default=None, help="Exact run_id to isolate; events without this run_id are excluded.")
    parser.add_argument("--list-run-ids", action="store_true", help="List available run_id values for the selected date.")
    parser.add_argument("--verbose", action="store_true", help="Print deep diagnostic sections in addition to compact scanner-first fields.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.list_run_ids:
        print_run_id_summary(discover_run_ids(
            base_dir=args.quant_data_dir,
            date=args.date,
            since=args.since,
            until=args.until,
        ))
        return 0
    evaluation = evaluate_session_runtime(
        date=args.date,
        quant_data_dir=args.quant_data_dir,
        realtime_log_dir=args.realtime_log_dir,
        load_offline_reports=True,
        since=args.since,
        until=args.until,
        run_id=args.run_id,
    )
    print_summary(evaluation, verbose=args.verbose)
    if args.write_report:
        path = write_session_runtime_report(evaluation, report_dir=args.report_dir)
        print(f"wrote_report={path}")
    return 0 if evaluation.session_status != DECISION_FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main())
