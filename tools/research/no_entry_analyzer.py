from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from utils.no_entry_diagnostics import (
    TIMING_MISSING,
    TIMING_UNPARSEABLE,
    classify_time_bucket,
    classify_timing_status,
    normalize_skip_reason,
)
from tools.replay_analyzer import build_partial_lifecycle_replay_from_events, build_phase2_coverage_from_events, discover_run_ids, print_run_id_summary


DEFAULT_QUANT_DATA_DIR = Path("runtime/quant_data")
DEFAULT_REALTIME_LOG_DIR = Path("runtime/realtime_logs")
DEFAULT_REPORT_DIR = Path("runtime/reports")


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
}


DISCOVERY_SOURCE_LABELS = {
    "decision_log": "decision_log JSONL",
    "market_snapshots": "market_snapshots JSONL",
    "scan_csv": "scan_log CSV",
}


@dataclass
class NoEntryRecord:
    source: str
    asset: str
    decision: str
    skipped: bool
    raw_skip_reason: str
    normalized_skip_reason: str
    confidence: float
    ev: float
    seconds_remaining: int | None
    entry_cutoff_seconds: int | None
    time_bucket: str
    timing_status: str
    orderbook_readiness_reason: str = ""


@dataclass
class NoEntryReport:
    date: str
    run_id: str = ""
    time_filter: dict[str, Any] = field(default_factory=dict)
    quant_data_dir: str = ""
    realtime_log_dir: str = ""
    decision_events_loaded: int = 0
    scan_rows_loaded: int = 0
    execution_events_loaded: int = 0
    bad_json_lines: int = 0
    total_scanned: int = 0
    total_entered: int = 0
    total_skipped: int = 0
    skip_reason_counts: dict[str, int] = field(default_factory=dict)
    top_skip_reasons: list[list[Any]] = field(default_factory=list)
    skip_percentages: dict[str, float] = field(default_factory=dict)
    skip_by_asset: dict[str, dict[str, int]] = field(default_factory=dict)
    skip_by_time_bucket: dict[str, int] = field(default_factory=dict)
    missing_timing_count: int = 0
    missing_timing_percentage: float = 0.0
    unparseable_timing_count: int = 0
    unknown_timing_percentage: float = 0.0
    unknown_timing_by_cause: dict[str, int] = field(default_factory=dict)
    top_skip_reasons_with_missing_timing: list[list[Any]] = field(default_factory=list)
    average_confidence_by_skip_reason: dict[str, float] = field(default_factory=dict)
    average_ev_by_skip_reason: dict[str, float] = field(default_factory=dict)
    count_risk_plan_zero: int = 0
    count_confidence_too_low: int = 0
    count_ev_below_threshold: int = 0
    count_time_unsafe: int = 0
    count_orderbook_unavailable: int = 0
    count_orderbook_unavailable_or_stale: int = 0
    orderbook_readiness_reason_counts: dict[str, int] = field(default_factory=dict)
    count_delta_extreme: int = 0
    order_submit_attempt_count: int = 0
    paper_fill_count: int = 0
    execution_stage_attempt_count: int = 0
    execution_diagnostic_event_count: int = 0
    execution_analysis_exception_count: int = 0
    execution_failure_count: int = 0
    root_cause_category: str = "unknown"
    root_cause_counts: dict[str, int] = field(default_factory=dict)
    root_cause_details: list[str] = field(default_factory=list)
    market_data_quality: dict[str, Any] = field(default_factory=dict)
    phase2_coverage: dict[str, Any] = field(default_factory=dict)
    partial_lifecycle_replay: dict[str, Any] = field(default_factory=dict)
    lifecycle_replay_confidence: str = "INSUFFICIENT"
    replay_supported_sections: list[dict[str, Any]] = field(default_factory=list)
    replay_unsupported_sections: list[dict[str, Any]] = field(default_factory=list)
    missed_starter_candidates: list[dict[str, Any]] = field(default_factory=list)
    timing_decay_summary: dict[str, Any] = field(default_factory=dict)
    spread_liquidity_readiness_summary: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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


def _parse_hhmm_utc(date_text: str, value: str | None, *, field_name: str) -> datetime | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        hour_text, minute_text = str(value).strip().split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be HH:MM in UTC") from None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"{field_name} must be HH:MM in UTC")
    parsed_date = datetime.strptime(date_text, "%Y-%m-%d").date()
    return datetime(parsed_date.year, parsed_date.month, parsed_date.day, hour, minute, tzinfo=timezone.utc)


def build_time_filter(date: str, *, since: str | None = None, until: str | None = None, run_id: str | None = None) -> dict[str, Any]:
    since_utc = _parse_hhmm_utc(date, since, field_name="--since")
    until_utc = _parse_hhmm_utc(date, until, field_name="--until")
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


def _event_in_time_window(event: dict[str, Any], time_filter: dict[str, Any] | None = None) -> bool:
    time_filter = time_filter or {}
    run_id = time_filter.get("run_id")
    if run_id and str(event.get("run_id") or "") != str(run_id):
        return False
    if not time_filter.get("applied"):
        return True
    timestamp = _parse_event_timestamp(event.get("timestamp_utc"))
    if timestamp is None:
        payload = _payload(event)
        timestamp = _parse_event_timestamp(payload.get("timestamp_utc"))
    if timestamp is None:
        return False
    since_utc = time_filter.get("since_utc")
    until_utc = time_filter.get("until_utc")
    if since_utc is not None and timestamp < since_utc:
        return False
    if until_utc is not None and timestamp >= until_utc:
        return False
    return True


def _row_in_time_window(row: dict[str, Any], time_filter: dict[str, Any] | None = None) -> bool:
    time_filter = time_filter or {}
    run_id = time_filter.get("run_id")
    if run_id and str(row.get("run_id") or "") != str(run_id):
        return False
    if not time_filter.get("applied"):
        return True
    timestamp = None
    for key in ("timestamp_utc", "timestamp", "time"):
        timestamp = _parse_event_timestamp(row.get(key))
        if timestamp is not None:
            break
    if timestamp is None:
        return False
    since_utc = time_filter.get("since_utc")
    until_utc = time_filter.get("until_utc")
    if since_utc is not None and timestamp < since_utc:
        return False
    if until_utc is not None and timestamp >= until_utc:
        return False
    return True


def _serializable_time_filter(time_filter: dict[str, Any]) -> dict[str, Any]:
    since_utc = time_filter.get("since_utc")
    until_utc = time_filter.get("until_utc")
    return {
        "since": time_filter.get("since"),
        "until": time_filter.get("until"),
        "since_utc": since_utc.isoformat().replace("+00:00", "Z") if isinstance(since_utc, datetime) else None,
        "until_utc": until_utc.isoformat().replace("+00:00", "Z") if isinstance(until_utc, datetime) else None,
        "run_id": time_filter.get("run_id"),
        "run_id_applied": bool(time_filter.get("run_id")),
        "applied": bool(time_filter.get("applied")),
        "semantics": time_filter.get("semantics"),
    }


def _safe_filename_token(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    sanitized = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in text)
    return sanitized[:80] or "run"


def _as_int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload")
    return payload if isinstance(payload, dict) else {}


def _asset_from_payload(payload: dict[str, Any]) -> str:
    for key in ("asset", "ticker", "market_id", "market_slug"):
        value = str(payload.get(key, "") or "").upper()
        if "BTC" in value:
            return "BTC"
        if "ETH" in value:
            return "ETH"
    return ""


def decision_log_path(base_dir: str | Path, date: str) -> Path:
    return Path(base_dir) / "decision_log" / f"{date}.jsonl"


def market_snapshot_path(base_dir: str | Path, date: str) -> Path:
    return Path(base_dir) / "market_snapshots" / f"{date}.jsonl"


def execution_log_path(base_dir: str | Path, date: str) -> Path:
    return Path(base_dir) / "execution_log" / f"{date}.jsonl"


def scan_log_paths(log_dir: str | Path, date: str) -> list[Path]:
    day_dir = Path(log_dir) / date
    if not day_dir.exists():
        return []
    return sorted(path for path in day_dir.glob("scan_log*.csv") if path.is_file())


def realtime_day_path(log_dir: str | Path, date: str) -> Path:
    return Path(log_dir) / date


def discover_available_dates(
    *,
    quant_data_dir: str | Path = DEFAULT_QUANT_DATA_DIR,
    realtime_log_dir: str | Path = DEFAULT_REALTIME_LOG_DIR,
) -> dict[str, dict[str, int]]:
    dates: dict[str, Counter[str]] = defaultdict(Counter)
    quant_root = Path(quant_data_dir)
    realtime_root = Path(realtime_log_dir)

    for path in (quant_root / "decision_log").glob("*.jsonl"):
        if path.is_file():
            dates[path.stem]["decision_log"] += 1
    for path in (quant_root / "market_snapshots").glob("*.jsonl"):
        if path.is_file():
            dates[path.stem]["market_snapshots"] += 1
    if realtime_root.exists():
        for day_dir in realtime_root.iterdir():
            if not day_dir.is_dir():
                continue
            count = sum(1 for path in day_dir.glob("scan_log*.csv") if path.is_file())
            if count:
                dates[day_dir.name]["scan_csv"] += count

    return {
        date: dict(counter)
        for date, counter in sorted(dates.items())
    }


def available_date_lines(available_dates: dict[str, dict[str, int]]) -> list[str]:
    lines: list[str] = []
    for date, sources in available_dates.items():
        source_bits = [
            f"{DISCOVERY_SOURCE_LABELS.get(source, source)}={count}"
            for source, count in sorted(sources.items())
        ]
        lines.append(f"{date}: {', '.join(source_bits)}")
    return lines


def nearest_available_date(target_date: str, available_dates: dict[str, dict[str, int]]) -> str:
    if not available_dates:
        return ""
    try:
        target = datetime.fromisoformat(target_date).date()
    except ValueError:
        return sorted(available_dates)[-1]

    def sort_key(date_text: str) -> tuple[int, str]:
        try:
            candidate = datetime.fromisoformat(date_text).date()
            return abs((candidate - target).days), date_text
        except ValueError:
            return 999999, date_text

    return min(available_dates, key=sort_key)


def print_available_dates(available_dates: dict[str, dict[str, int]]) -> None:
    print("Available no-entry data dates")
    if not available_dates:
        print("(none)")
        return
    for line in available_date_lines(available_dates):
        print(f"- {line}")


def print_missing_date_diagnostics(
    *,
    date: str,
    quant_data_dir: str | Path = DEFAULT_QUANT_DATA_DIR,
    realtime_log_dir: str | Path = DEFAULT_REALTIME_LOG_DIR,
) -> None:
    available_dates = discover_available_dates(
        quant_data_dir=quant_data_dir,
        realtime_log_dir=realtime_log_dir,
    )
    nearest = nearest_available_date(date, available_dates)
    print("No data found for requested date.")
    print(f"searched decision_log path: {decision_log_path(quant_data_dir, date)}")
    print(f"searched market_snapshots path: {market_snapshot_path(quant_data_dir, date)}")
    print(f"searched realtime_logs path: {realtime_day_path(realtime_log_dir, date)}")
    print("available dates:")
    if available_dates:
        for line in available_date_lines(available_dates):
            print(f"- {line}")
    else:
        print("- (none)")
    print(f"nearest date with data: {nearest or '(none)'}")
    if nearest:
        print(f"suggestion: python -m tools.research.no_entry_analyzer --date {nearest}")
    else:
        print("suggestion: run python -m tools.research.no_entry_analyzer --list-dates after the bot writes logs")


def _load_jsonl_events(path: Path, *, time_filter: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], int]:
    if not path.is_file():
        return [], 0
    events: list[dict[str, Any]] = []
    bad_json_lines = 0
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
                if not _event_in_time_window(event, time_filter):
                    continue
                events.append(event)
            else:
                bad_json_lines += 1
    return events, bad_json_lines


def load_decision_records(base_dir: str | Path, date: str, *, time_filter: dict[str, Any] | None = None) -> list[NoEntryRecord]:
    records: list[NoEntryRecord] = []
    events, _bad_json_lines = _load_jsonl_events(decision_log_path(base_dir, date), time_filter=time_filter)
    for event in events:
        payload = _payload(event)
        decision = str(payload.get("decision", "") or "").lower()
        skipped = bool(payload.get("skipped", False)) or decision in {"skip", "skipped"}
        raw_reason = str(
            payload.get("raw_skip_reason")
            or payload.get("skip_reason")
            or _nested(payload, "display.raw_skip_reason")
            or _nested(payload, "display.skip_reason")
            or ""
        )
        normalized = str(payload.get("normalized_skip_reason") or normalize_skip_reason(raw_reason))
        raw_seconds_remaining = _first_present(payload.get("seconds_remaining"), _nested(payload, "display.seconds_remaining"))
        raw_entry_cutoff = _first_present(payload.get("entry_cutoff_seconds"), _nested(payload, "display.entry_cutoff_seconds"))
        seconds_remaining = _as_int_or_none(raw_seconds_remaining)
        entry_cutoff = _as_int_or_none(raw_entry_cutoff)
        timing_status = classify_timing_status(raw_seconds_remaining)
        records.append(
            NoEntryRecord(
                source="decision_log",
                asset=_asset_from_payload(payload),
                decision=decision,
                skipped=skipped,
                raw_skip_reason=raw_reason,
                normalized_skip_reason=normalized,
                confidence=_as_float(payload.get("confidence")),
                ev=_as_float(payload.get("ev", payload.get("edge", _nested(payload, "display.ev")))),
                seconds_remaining=seconds_remaining,
                entry_cutoff_seconds=entry_cutoff,
                time_bucket=str(
                    payload.get("time_bucket")
                    or _nested(payload, "display.time_bucket")
                    or classify_time_bucket(seconds_remaining, entry_cutoff)
                ),
                timing_status=timing_status,
                orderbook_readiness_reason=str(
                    payload.get("orderbook_unavailable_reason")
                    or payload.get("orderbook_readiness_reason")
                    or _nested(payload, "display.orderbook_unavailable_reason")
                    or _nested(payload, "display.orderbook_readiness_reason")
                    or payload.get("clob_error_category")
                    or _nested(payload, "display.clob_error_category")
                    or ""
                ),
            )
        )
    return records


def load_market_snapshot_payloads(base_dir: str | Path, date: str, *, time_filter: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    events, _bad_json_lines = _load_jsonl_events(market_snapshot_path(base_dir, date), time_filter=time_filter)
    for event in events:
        payload = _payload(event)
        if payload:
            payloads.append(payload)
    return payloads


def load_execution_summary(base_dir: str | Path, date: str, *, time_filter: dict[str, Any] | None = None) -> dict[str, int]:
    events, _bad_json_lines = _load_jsonl_events(execution_log_path(base_dir, date), time_filter=time_filter)
    summary = {
        "execution_events_loaded": len(events),
        "order_submit_attempt_count": 0,
        "paper_fill_count": 0,
        "execution_stage_attempt_count": 0,
        "execution_diagnostic_event_count": 0,
        "execution_analysis_exception_count": 0,
        "execution_failure_count": 0,
    }
    for event in events:
        payload = _payload(event)
        event_name = str(payload.get("event", "") or "").lower()
        status = str(payload.get("status", "") or "").lower()
        if _is_execution_stage_attempt(event_name, status):
            summary["execution_stage_attempt_count"] += 1
        else:
            summary["execution_diagnostic_event_count"] += 1
        if event_name == "market_analysis_exception":
            summary["execution_analysis_exception_count"] += 1
        if event_name == "order_submit_attempt":
            summary["order_submit_attempt_count"] += 1
        if event_name == "paper_fill":
            summary["paper_fill_count"] += 1
        if _is_true_execution_failure(event_name, status):
            summary["execution_failure_count"] += 1
    return summary


def _is_execution_stage_attempt(event_name: str, status: str = "") -> bool:
    if event_name in {
        "order_submit_attempt",
        "order_submit",
        "order_submit_failed",
        "live_order_submitted",
        "paper_fill",
        "cancel_order",
        "cancel_order_failed",
        "order_cancel_failed",
    }:
        return True
    if event_name.endswith("_submitted") or event_name.endswith("_filled"):
        return True
    return _is_true_execution_failure(event_name, status) and "analysis" not in event_name


def _is_true_execution_failure(event_name: str, status: str = "") -> bool:
    if event_name == "order_intent_reject":
        return False
    if event_name in {"order_submit_failed", "cancel_order_failed", "order_cancel_failed"}:
        return True
    if event_name == "cancel_order" and status in {"failed", "error", "rejected"}:
        return True
    if event_name in {"live_order_submitted", "order_submit"} and status in {"failed", "error", "rejected"}:
        return True
    return event_name.endswith("_failed") or event_name.endswith("_failure")


def count_bad_json_lines(base_dir: str | Path, date: str) -> int:
    paths = [
        decision_log_path(base_dir, date),
        market_snapshot_path(base_dir, date),
        execution_log_path(base_dir, date),
    ]
    return sum(_load_jsonl_events(path)[1] for path in paths)


def load_scan_records(log_dir: str | Path, date: str, *, time_filter: dict[str, Any] | None = None) -> list[NoEntryRecord]:
    records: list[NoEntryRecord] = []
    for path in scan_log_paths(log_dir, date):
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if not _row_in_time_window(row, time_filter):
                    continue
                decision = str(row.get("decision", "") or "").lower()
                skipped = decision not in {"buy", "long", "approved", "enter", "entered"}
                raw_reason = str(row.get("raw_skip_reason") or row.get("skip_reason") or "")
                normalized = str(row.get("normalized_skip_reason") or normalize_skip_reason(raw_reason))
                raw_seconds_remaining = row.get("seconds_remaining")
                seconds_remaining = _as_int_or_none(raw_seconds_remaining)
                entry_cutoff = _as_int_or_none(row.get("entry_cutoff_seconds"))
                timing_status = classify_timing_status(raw_seconds_remaining)
                records.append(
                    NoEntryRecord(
                        source="scan_csv",
                        asset=str(row.get("asset", "") or "").upper(),
                        decision=decision,
                        skipped=skipped,
                        raw_skip_reason=raw_reason,
                        normalized_skip_reason=normalized,
                        confidence=_as_float(row.get("confidence")),
                        ev=_as_float(row.get("edge")),
                        seconds_remaining=seconds_remaining,
                        entry_cutoff_seconds=entry_cutoff,
                        time_bucket=str(row.get("time_bucket") or classify_time_bucket(seconds_remaining, entry_cutoff)),
                        timing_status=timing_status,
                        orderbook_readiness_reason=str(row.get("orderbook_readiness_reason") or row.get("orderbook_unavailable_reason") or ""),
                    )
                )
    return records


def _nested(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def analyze_no_entries(
    *,
    date: str,
    quant_data_dir: str | Path = DEFAULT_QUANT_DATA_DIR,
    realtime_log_dir: str | Path = DEFAULT_REALTIME_LOG_DIR,
    report_dir: str | Path | None = None,
    write_report: bool = False,
    since: str | None = None,
    until: str | None = None,
    run_id: str | None = None,
) -> NoEntryReport:
    time_filter = build_time_filter(date, since=since, until=until, run_id=run_id)
    decision_records = load_decision_records(quant_data_dir, date, time_filter=time_filter)
    scan_records = load_scan_records(realtime_log_dir, date, time_filter=time_filter)
    market_snapshots = load_market_snapshot_payloads(quant_data_dir, date, time_filter=time_filter)
    execution_summary = load_execution_summary(quant_data_dir, date, time_filter=time_filter)
    primary_records = decision_records if decision_records else scan_records

    report = NoEntryReport(
        date=date,
        run_id=str(run_id or ""),
        time_filter=_serializable_time_filter(time_filter),
        quant_data_dir=str(Path(quant_data_dir)),
        realtime_log_dir=str(Path(realtime_log_dir)),
        decision_events_loaded=len(decision_records),
        scan_rows_loaded=len(scan_records),
        execution_events_loaded=execution_summary["execution_events_loaded"],
        bad_json_lines=count_bad_json_lines(quant_data_dir, date),
        total_scanned=max(len(decision_records), len(scan_records)),
    )
    _aggregate_records(report, primary_records)
    report.order_submit_attempt_count = execution_summary["order_submit_attempt_count"]
    report.paper_fill_count = execution_summary["paper_fill_count"]
    report.execution_stage_attempt_count = execution_summary["execution_stage_attempt_count"]
    report.execution_diagnostic_event_count = execution_summary["execution_diagnostic_event_count"]
    report.execution_analysis_exception_count = execution_summary["execution_analysis_exception_count"]
    report.execution_failure_count = execution_summary["execution_failure_count"]
    report.market_data_quality = build_market_data_quality(report, market_snapshots)
    phase2_events = _phase2_no_entry_events(
        quant_data_dir=quant_data_dir,
        date=date,
        scan_records=scan_records,
        time_filter=time_filter,
    )
    report.phase2_coverage = build_phase2_coverage_from_events(phase2_events)
    lifecycle_replay = build_partial_lifecycle_replay_from_events(phase2_events)
    report.partial_lifecycle_replay = lifecycle_replay
    report.lifecycle_replay_confidence = str(lifecycle_replay.get("lifecycle_replay_confidence", "INSUFFICIENT"))
    report.replay_supported_sections = list(lifecycle_replay.get("replay_supported_sections", []))
    report.replay_unsupported_sections = list(lifecycle_replay.get("replay_unsupported_sections", []))
    report.missed_starter_candidates = list(lifecycle_replay.get("missed_starter_candidates", []))
    report.timing_decay_summary = dict(lifecycle_replay.get("timing_decay_summary", {}))
    report.spread_liquidity_readiness_summary = dict(lifecycle_replay.get("spread_liquidity_readiness_summary", {}))
    classify_root_cause(report)
    report.recommendations = build_recommendations(report)

    if write_report:
        write_no_entry_report(report, report_dir=report_dir)
    return report


def _phase2_no_entry_events(
    *,
    quant_data_dir: str | Path,
    date: str,
    scan_records: list[NoEntryRecord],
    time_filter: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    decision_events, _decision_bad = _load_jsonl_events(decision_log_path(quant_data_dir, date), time_filter=time_filter)
    snapshot_events, _snapshot_bad = _load_jsonl_events(market_snapshot_path(quant_data_dir, date), time_filter=time_filter)
    events = [*decision_events, *snapshot_events]
    if decision_events:
        return events
    for record in scan_records:
        events.append({
            "event_type": "decision",
            "_category": "scan_csv",
            "payload": {
                "asset": record.asset,
                "decision": record.decision,
                "skipped": record.skipped,
                "skip_reason": record.raw_skip_reason,
                "normalized_skip_reason": record.normalized_skip_reason,
                "confidence": record.confidence,
                "ev": record.ev,
                "seconds_remaining": record.seconds_remaining,
                "entry_cutoff_seconds": record.entry_cutoff_seconds,
                "time_bucket": record.time_bucket,
                "orderbook_readiness_reason": record.orderbook_readiness_reason,
            },
        })
    return events


def _aggregate_records(report: NoEntryReport, records: list[NoEntryRecord]) -> None:
    skip_counts: Counter[str] = Counter()
    bucket_counts: Counter[str] = Counter()
    unknown_timing_by_cause: Counter[str] = Counter()
    missing_timing_by_reason: Counter[str] = Counter()
    by_asset: defaultdict[str, Counter[str]] = defaultdict(Counter)
    confidence_values: defaultdict[str, list[float]] = defaultdict(list)
    ev_values: defaultdict[str, list[float]] = defaultdict(list)
    orderbook_readiness_counts: Counter[str] = Counter()

    entered = 0
    skipped = 0
    for record in records:
        if record.skipped:
            skipped += 1
            reason = record.normalized_skip_reason or "unknown"
            skip_counts[reason] += 1
            time_bucket = record.time_bucket or "unknown"
            bucket_counts[time_bucket] += 1
            if record.timing_status == TIMING_MISSING:
                missing_timing_by_reason[reason] += 1
                if time_bucket == "unknown":
                    unknown_timing_by_cause[TIMING_MISSING] += 1
            elif record.timing_status == TIMING_UNPARSEABLE and time_bucket == "unknown":
                unknown_timing_by_cause[TIMING_UNPARSEABLE] += 1
            elif time_bucket == "unknown":
                unknown_timing_by_cause["unknown"] += 1
            asset = record.asset or "UNKNOWN"
            by_asset[asset][reason] += 1
            confidence_values[reason].append(record.confidence)
            ev_values[reason].append(record.ev)
            if record.orderbook_readiness_reason:
                orderbook_readiness_counts[record.orderbook_readiness_reason] += 1
        else:
            entered += 1

    report.total_entered = entered
    report.total_skipped = skipped
    report.skip_reason_counts = dict(skip_counts.most_common())
    report.top_skip_reasons = [
        [reason, count]
        for reason, count in skip_counts.most_common(10)
    ]
    report.skip_percentages = {
        reason: round(count / skipped, 4) if skipped else 0.0
        for reason, count in report.skip_reason_counts.items()
    }
    report.skip_by_asset = {
        asset: dict(counter.most_common())
        for asset, counter in sorted(by_asset.items())
    }
    report.skip_by_time_bucket = dict(bucket_counts.most_common())
    report.missing_timing_count = sum(1 for record in records if record.skipped and record.timing_status == TIMING_MISSING)
    report.missing_timing_percentage = round(report.missing_timing_count / skipped, 4) if skipped else 0.0
    report.unparseable_timing_count = sum(1 for record in records if record.skipped and record.timing_status == TIMING_UNPARSEABLE)
    unknown_timing_count = report.missing_timing_count + report.unparseable_timing_count
    report.unknown_timing_percentage = round(unknown_timing_count / skipped, 4) if skipped else 0.0
    report.unknown_timing_by_cause = dict(unknown_timing_by_cause.most_common())
    report.top_skip_reasons_with_missing_timing = [
        [reason, count]
        for reason, count in missing_timing_by_reason.most_common(10)
    ]
    report.average_confidence_by_skip_reason = {
        reason: round(sum(values) / len(values), 6)
        for reason, values in sorted(confidence_values.items())
        if values
    }
    report.average_ev_by_skip_reason = {
        reason: round(sum(values) / len(values), 6)
        for reason, values in sorted(ev_values.items())
        if values
    }
    report.count_risk_plan_zero = skip_counts.get("risk_plan_zero", 0)
    report.count_confidence_too_low = skip_counts.get("confidence_too_low", 0)
    report.count_ev_below_threshold = skip_counts.get("ev_below_threshold", 0)
    report.count_time_unsafe = skip_counts.get("time_unsafe", 0)
    report.orderbook_readiness_reason_counts = dict(orderbook_readiness_counts.most_common())
    hard_unavailable = sum(
        orderbook_readiness_counts.get(reason, 0)
        for reason in HARDBLOCK_ORDERBOOK_REASONS
    )
    report.count_orderbook_unavailable = hard_unavailable or skip_counts.get("orderbook_unavailable", 0)
    report.count_orderbook_unavailable_or_stale = (
        report.count_orderbook_unavailable + skip_counts.get("stale_data", 0) + orderbook_readiness_counts.get("stale_book", 0)
    )
    report.count_delta_extreme = skip_counts.get("delta_extreme", 0)


def classify_root_cause(report: NoEntryReport) -> None:
    risk_count = report.count_risk_plan_zero + _count_reasons_containing(
        report.skip_reason_counts,
        ("risk", "floor", "balance", "drawdown", "reconciliation", "lockdown"),
        exclude=("risk_plan_zero",),
    )
    data_count = report.count_orderbook_unavailable_or_stale + report.bad_json_lines
    if report.market_data_quality.get("token_mapping_warning_count", 0):
        data_count += int(report.market_data_quality["token_mapping_warning_count"])
    strategy_count = (
        report.count_confidence_too_low
        + report.count_ev_below_threshold
        + report.count_delta_extreme
    )
    cutoff_count = report.count_time_unsafe
    execution_count = report.execution_failure_count
    if report.total_entered > 0 and report.order_submit_attempt_count == 0:
        execution_count += report.total_entered
    if report.order_submit_attempt_count > 0 and report.paper_fill_count == 0:
        execution_count += report.order_submit_attempt_count

    category_counts = {
        "data": data_count,
        "strategy": strategy_count,
        "risk": risk_count,
        "cutoff": cutoff_count,
        "execution": execution_count,
    }
    report.root_cause_counts = category_counts
    if report.total_scanned == 0:
        report.root_cause_category = "data"
        report.root_cause_details = ["No decision_log JSONL or scan_log CSV rows were available for analysis."]
        return

    top_category, top_count = max(category_counts.items(), key=lambda item: item[1])
    report.root_cause_category = top_category if top_count > 0 else "unknown"
    report.root_cause_details = _root_cause_details(report)


def _count_reasons_containing(counts: dict[str, int], tokens: tuple[str, ...], *, exclude: tuple[str, ...] = ()) -> int:
    total = 0
    for reason, count in counts.items():
        if reason in exclude:
            continue
        reason_lower = reason.lower()
        if any(token in reason_lower for token in tokens):
            total += count
    return total


def _root_cause_details(report: NoEntryReport) -> list[str]:
    details: list[str] = []
    if report.count_orderbook_unavailable_or_stale:
        details.append(f"data: orderbook unavailable/stale skips={report.count_orderbook_unavailable_or_stale}")
    if report.bad_json_lines:
        details.append(f"data: malformed JSONL lines={report.bad_json_lines}")
    if report.count_confidence_too_low:
        details.append(f"strategy: confidence_too_low skips={report.count_confidence_too_low}")
    if report.count_ev_below_threshold:
        details.append(f"strategy: ev_below_threshold skips={report.count_ev_below_threshold}")
    if report.count_delta_extreme:
        details.append(f"strategy: delta_extreme skips={report.count_delta_extreme}")
    if report.count_risk_plan_zero:
        details.append(f"risk: zero-size risk plans={report.count_risk_plan_zero}")
    if report.count_time_unsafe:
        details.append(f"cutoff: time_unsafe skips={report.count_time_unsafe}")
    if report.execution_failure_count:
        details.append(f"execution: failures={report.execution_failure_count}")
    if report.execution_diagnostic_event_count:
        details.append(
            "execution_log: diagnostic/non-attempt events={count} analysis_exceptions={exceptions}".format(
                count=report.execution_diagnostic_event_count,
                exceptions=report.execution_analysis_exception_count,
            )
        )
    if report.total_entered > 0 and report.order_submit_attempt_count == 0:
        details.append("execution: approved/enter decisions had no matching order_submit_attempt events")
    if report.order_submit_attempt_count > 0 and report.paper_fill_count == 0:
        details.append("execution: order_submit_attempt events had no matching paper_fill events")
    return details


def build_market_data_quality(report: NoEntryReport, snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    orderbook_ages: list[float] = []
    token_mapping_warning_count = 0
    snapshot_reason_counts: Counter[str] = Counter()
    clob_error_categories: Counter[str] = Counter()
    clob_exception_types: Counter[str] = Counter()
    for payload in snapshots:
        for key in ("orderbook_age_ms", "yes_orderbook_age_ms", "no_orderbook_age_ms"):
            value = _as_float(payload.get(key), default=0.0)
            if value > 0:
                orderbook_ages.append(value)
        if payload.get("token_mapping_warning"):
            token_mapping_warning_count += 1
        reason = str(
            payload.get("orderbook_readiness_reason")
            or payload.get("orderbook_unavailable_reason")
            or payload.get("clob_error_category")
            or ""
        )
        if reason:
            snapshot_reason_counts[reason] += 1
        clob_category = str(payload.get("clob_error_category") or "")
        if clob_category:
            clob_error_categories[clob_category] += 1
        clob_exception_type = str(payload.get("clob_exception_type") or "")
        if clob_exception_type:
            clob_exception_types[clob_exception_type] += 1
    average_age = round(sum(orderbook_ages) / len(orderbook_ages), 2) if orderbook_ages else 0.0
    reason_counts = Counter(report.orderbook_readiness_reason_counts)
    reason_counts.update(snapshot_reason_counts)
    return {
        "market_snapshots_loaded": len(snapshots),
        "stale_data_count": int(report.skip_reason_counts.get("stale_data", 0)),
        "orderbook_unavailable_count": int(report.count_orderbook_unavailable),
        "orderbook_readiness_reason_counts": dict(reason_counts.most_common()),
        "clob_error_categories": dict(clob_error_categories.most_common()),
        "clob_exception_types": dict(clob_exception_types.most_common()),
        "average_orderbook_age_ms": average_age,
        "token_mapping_warning_count": token_mapping_warning_count,
    }


def build_recommendations(report: NoEntryReport) -> list[str]:
    recommendations: list[str] = []
    if report.total_scanned == 0:
        return ["No decision_log JSONL or scan_log CSV rows found for this date."]
    if report.bad_json_lines:
        recommendations.append("Malformed JSONL lines were skipped; run quant_data_quality before trusting this no-entry diagnosis.")
    if report.total_entered > 0:
        recommendations.append("Entries occurred; review skip mix but this is not a pure no-entry run.")
    if report.root_cause_category != "unknown":
        recommendations.append(f"Dominant root cause category: {report.root_cause_category}.")
    if report.market_data_quality.get("token_mapping_warning_count", 0):
        recommendations.append("Token mapping warnings appear; verify YES/UP and NO/DOWN token IDs, condition_id, and market slug before trusting entries.")
    top_reason = next(iter(report.skip_reason_counts), "")
    if report.unknown_timing_percentage > 0.20:
        recommendations.append("Unknown timing exceeds 20%; fix timing instrumentation before interpreting skip-by-time-bucket results.")
    if top_reason == "time_unsafe":
        recommendations.append("Time unsafe is the top skip reason; test a shorter scan interval or review entry cutoff seconds before changing strategy.")
    elif report.skip_reason_counts.get("time_unsafe", 0):
        recommendations.append("Time unsafe skips appear; compare scan cadence and market discovery timing against entry cutoff seconds.")
    if report.total_skipped and report.count_orderbook_unavailable / report.total_skipped > 0.10:
        recommendations.append("Orderbook unavailable exceeds 10%; review orderbook diagnostics, token IDs, freshness, and retry behavior offline.")
    elif report.count_orderbook_unavailable:
        recommendations.append("Orderbook unavailable skips appear; inspect token IDs, orderbook freshness, and market snapshot JSONL before changing strategy.")
    if report.count_delta_extreme:
        recommendations.append("Delta extreme skips appear; review market regimes and delta diagnostics, not risk sizing.")
    if report.skip_reason_counts.get("confidence_too_low", 0):
        recommendations.append("Confidence is below current strategy threshold; collect more paper evidence before considering any strategy change.")
    if report.count_risk_plan_zero:
        recommendations.append("Risk plan zero skips appear; inspect sizing diagnostics, bankroll tier, risk mode, minimum position size, and order manager blocked reasons.")
    if report.skip_reason_counts.get("ev_below_threshold", 0):
        recommendations.append("EV threshold skips appear; review EV distribution by asset/time bucket offline before changing thresholds.")
    if not recommendations:
        recommendations.append("No dominant no-entry blocker found; inspect raw skip reason distribution and source data quality.")
    return recommendations


def write_no_entry_report(report: NoEntryReport, *, report_dir: str | Path | None = None) -> Path:
    output_dir = Path(report_dir or DEFAULT_REPORT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = ""
    if report.time_filter.get("applied"):
        since = str(report.time_filter.get("since") or "start").replace(":", "")
        until = str(report.time_filter.get("until") or "end").replace(":", "")
        suffix = f"_{since}_to_{until}"
    safe_run_id = _safe_filename_token(report.run_id or report.time_filter.get("run_id"))
    if safe_run_id:
        suffix = f"{suffix}_run_{safe_run_id}"
    output_path = output_dir / f"no_entry_report_{report.date}{suffix}.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report.to_dict(), handle, indent=2, sort_keys=True)
    return output_path


def print_summary(report: NoEntryReport) -> None:
    print("No-Entry Diagnostics")
    if report.time_filter.get("applied"):
        print(
            "date={date} filter={since}..{until} run_id={run_id} semantics={semantics} scanned={scanned} entered={entered} skipped={skipped}".format(
                date=report.date,
                since=report.time_filter.get("since_utc"),
                until=report.time_filter.get("until_utc"),
                run_id=report.run_id or "",
                semantics=report.time_filter.get("semantics"),
                scanned=report.total_scanned,
                entered=report.total_entered,
                skipped=report.total_skipped,
            )
        )
    else:
        print(f"date={report.date} run_id={report.run_id or ''} scanned={report.total_scanned} entered={report.total_entered} skipped={report.total_skipped}")
    print(
        "decision_events={decision_events} scan_rows={scan_rows} execution_events={execution_events} "
        "bad_json={bad_json}".format(
            decision_events=report.decision_events_loaded,
            scan_rows=report.scan_rows_loaded,
            execution_events=report.execution_events_loaded,
            bad_json=report.bad_json_lines,
        )
    )
    print(f"root_cause_category={report.root_cause_category} root_cause_counts={report.root_cause_counts}")
    print(
        "zero_size={zero_size} confidence_too_low={confidence} ev_below_threshold={ev} "
        "time_unsafe={time_unsafe} orderbook_unavailable_or_stale={orderbook} "
        "execution_failures={execution_failures}".format(
            zero_size=report.count_risk_plan_zero,
            confidence=report.count_confidence_too_low,
            ev=report.count_ev_below_threshold,
            time_unsafe=report.count_time_unsafe,
            orderbook=report.count_orderbook_unavailable_or_stale,
            execution_failures=report.execution_failure_count,
        )
    )
    print(f"top_skip_reasons={report.top_skip_reasons}")
    print(f"skip_by_time_bucket={report.skip_by_time_bucket}")
    print(
        "timing_missing="
        f"{report.missing_timing_count} ({report.missing_timing_percentage:.2%}) "
        f"unparseable={report.unparseable_timing_count}"
    )
    print(f"market_data_quality={report.market_data_quality}")


def resolve_requested_date(args: argparse.Namespace) -> str:
    if getattr(args, "today_local", False):
        return datetime.now().astimezone().strftime("%Y-%m-%d")
    if getattr(args, "today_utc", False):
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return str(args.date)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze why PolyTrade paper runs did not enter trades.")
    parser.add_argument("--date", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"), help="Date in YYYY-MM-DD format.")
    parser.add_argument("--today-local", action="store_true", help="Use today's date in the local timezone.")
    parser.add_argument("--today-utc", action="store_true", help="Use today's date in UTC.")
    parser.add_argument("--since", default=None, help="UTC start time HH:MM for same-day filtering; inclusive.")
    parser.add_argument("--until", default=None, help="UTC end time HH:MM for same-day filtering; exclusive.")
    parser.add_argument("--run-id", default=None, help="Exact run_id to isolate; events without this run_id are excluded.")
    parser.add_argument("--list-run-ids", action="store_true", help="List available run_id values for the selected date.")
    parser.add_argument("--list-dates", action="store_true", help="List available dates from decision logs, market snapshots, and scan CSVs.")
    parser.add_argument("--quant-data-dir", default=str(DEFAULT_QUANT_DATA_DIR), help="Quant data root directory.")
    parser.add_argument("--realtime-log-dir", default=str(DEFAULT_REALTIME_LOG_DIR), help="Realtime log root directory.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Report directory for programmatic/test runs.")
    parser.add_argument("--write-report", action="store_true", help="Write no_entry_report JSON under runtime/reports.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.today_local and args.today_utc:
        raise SystemExit("--today-local and --today-utc are mutually exclusive.")
    if args.list_dates:
        print_available_dates(discover_available_dates(
            quant_data_dir=args.quant_data_dir,
            realtime_log_dir=args.realtime_log_dir,
        ))
        return 0

    requested_date = resolve_requested_date(args)
    if args.list_run_ids:
        print_run_id_summary(discover_run_ids(
            base_dir=args.quant_data_dir,
            date=requested_date,
            since=args.since,
            until=args.until,
        ))
        return 0
    output_report_dir = DEFAULT_REPORT_DIR if args.write_report else Path(args.report_dir)
    report = analyze_no_entries(
        date=requested_date,
        quant_data_dir=args.quant_data_dir,
        realtime_log_dir=args.realtime_log_dir,
        report_dir=output_report_dir,
        write_report=args.write_report,
        since=args.since,
        until=args.until,
        run_id=args.run_id,
    )
    print_summary(report)
    if args.write_report:
        suffix = ""
        if args.since or args.until:
            suffix = f"_{str(args.since or 'start').replace(':', '')}_to_{str(args.until or 'end').replace(':', '')}"
        safe_run_id = _safe_filename_token(args.run_id)
        if safe_run_id:
            suffix = f"{suffix}_run_{safe_run_id}"
        print(f"report={DEFAULT_REPORT_DIR / f'no_entry_report_{requested_date}{suffix}.json'}")
    if report.total_scanned == 0 and report.market_data_quality.get("market_snapshots_loaded", 0) == 0:
        print_missing_date_diagnostics(
            date=requested_date,
            quant_data_dir=args.quant_data_dir,
            realtime_log_dir=args.realtime_log_dir,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
