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
from tools.replay_analyzer import ReplayReport, analyze_replay, load_replay_events
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


@dataclass
class SessionRuntimeEvaluation:
    date: str
    generated_at_utc: str
    session_status: str
    primary_bottleneck: str
    secondary_bottleneck: str = "none"
    bottleneck_scores: dict[str, int] = field(default_factory=dict)
    health_summary: dict[str, Any] = field(default_factory=dict)
    skip_summary: dict[str, Any] = field(default_factory=dict)
    timing_quality: dict[str, Any] = field(default_factory=dict)
    cutoff_behavior: dict[str, Any] = field(default_factory=dict)
    risk_blocks: dict[str, Any] = field(default_factory=dict)
    execution_summary: dict[str, Any] = field(default_factory=dict)
    orderbook_readiness: dict[str, Any] = field(default_factory=dict)
    regime_summary: dict[str, Any] = field(default_factory=dict)
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
) -> dict[str, Any]:
    since_utc = _parse_hhmm_utc(date, since, field_name="--since")
    until_utc = _parse_hhmm_utc(date, until, field_name="--until")
    if since_utc is not None and until_utc is not None and since_utc >= until_utc:
        raise ValueError("--since must be earlier than --until")
    return {
        "timezone": "UTC",
        "since": since,
        "until": until,
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
) -> tuple[ReplayReport | None, str | None]:
    try:
        report = analyze_replay(
            base_dir=quant_data_dir,
            date=date,
            write_reports=False,
            write_csv=False,
            since_utc=since_utc,
            until_utc=until_utc,
        )
        return report, None
    except Exception as exc:
        return None, f"replay_analyzer_failed:{exc}"


def _safe_analyze_no_entries(
    *,
    date: str,
    quant_data_dir: str | Path,
    realtime_log_dir: str | Path,
) -> tuple[NoEntryReport | None, str | None]:
    try:
        report = analyze_no_entries(
            date=date,
            quant_data_dir=quant_data_dir,
            realtime_log_dir=realtime_log_dir,
            write_report=False,
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
) -> SessionRuntimeEvaluation:
    date = date or _today_utc()
    time_filter = _time_filter_payload(date=date, since=since, until=until)
    time_filter_applied = bool(time_filter.get("applied"))
    load_errors: list[str] = []
    replay_obj: ReplayReport | None = replay_report if isinstance(replay_report, ReplayReport) else None
    no_entry_obj: NoEntryReport | None = no_entry_report if isinstance(no_entry_report, NoEntryReport) else None

    if load_offline_reports and replay_obj is None:
        replay_obj, error = _safe_analyze_replay(
            date=date,
            quant_data_dir=quant_data_dir,
            since_utc=time_filter.get("since_utc"),
            until_utc=time_filter.get("until_utc"),
        )
        if error:
            load_errors.append(error)
    if load_offline_reports and no_entry_obj is None and not time_filter_applied:
        no_entry_obj, error = _safe_analyze_no_entries(
            date=date,
            quant_data_dir=quant_data_dir,
            realtime_log_dir=realtime_log_dir,
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

    no_data = bool(
        time_filter_applied
        and not session_summary
        and _as_int(replay_payload.get("events_loaded")) == 0
        and _as_int((raw_execution_summary or {}).get("execution_events_loaded")) == 0
        and not no_entry_payload
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

    top_skips = [[reason, count] for reason, count in skip_counts.most_common(10)]
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
    return SessionRuntimeEvaluation(
        date=date,
        generated_at_utc=_utc_now(),
        session_status=status,
        primary_bottleneck=primary,
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
        timing_quality={
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
        },
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
        risk_blocks={
            "risk_plan_zero_count": int(skip_counts.get("risk_plan_zero", 0)),
            "risk_reject_count": _as_int(replay_payload.get("risk_reject_count")),
            "risk_mode": str((session_summary or {}).get("risk_mode", "")),
            "risk_mode_allow_new_entries": (session_summary or {}).get("risk_mode_allow_new_entries"),
            **bankroll_visibility,
        },
        execution_summary={
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
        },
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
            "liquidity_states": replay_payload.get("liquidity_states", []),
            "average_orderbook_age_ms": _as_float(replay_payload.get("average_orderbook_age_ms", no_entry_payload.get("market_data_quality", {}).get("average_orderbook_age_ms", 0.0))),
            "max_orderbook_age_ms": _as_float(replay_payload.get("max_orderbook_age_ms")),
            "average_oracle_age_ms": _as_float(replay_payload.get("average_oracle_age_ms")),
            "token_mapping_warning_count": _as_int(no_entry_payload.get("market_data_quality", {}).get("token_mapping_warning_count", 0)),
        },
        regime_summary=regime_summary,
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
    return list(dict.fromkeys(recommendations))[:6]


def format_terminal_summary(evaluation: SessionRuntimeEvaluation) -> list[str]:
    health = evaluation.health_summary
    timing = evaluation.timing_quality
    cutoff = evaluation.cutoff_behavior
    orderbook = evaluation.orderbook_readiness
    regimes = evaluation.regime_summary
    risk = evaluation.risk_blocks
    execution = evaluation.execution_summary
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
            f"liquidity_states={orderbook.get('liquidity_states', [])}"
        ),
        (
            "regimes "
            f"events={regimes.get('events_counted', 0)} "
            f"volatility={regimes.get('volatility_regimes', [])} "
            f"trend={regimes.get('trend_regimes', [])}"
        ),
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
    output_path = output_dir / f"session_runtime_evaluation_{evaluation.date}{suffix}.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(evaluation.to_dict(), handle, indent=2, sort_keys=True)
    return output_path


def print_summary(evaluation: SessionRuntimeEvaluation) -> None:
    print("Session Runtime Evaluation")
    for line in format_terminal_summary(evaluation):
        print(line)
    print(f"recommendations={evaluation.recommendations}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate Polymarket paper session runtime bottlenecks.")
    parser.add_argument("--date", default=_today_utc(), help="Date in YYYY-MM-DD format.")
    parser.add_argument("--quant-data-dir", default=str(DEFAULT_QUANT_DATA_DIR), help="Quant data root directory.")
    parser.add_argument("--realtime-log-dir", default=str(DEFAULT_REALTIME_LOG_DIR), help="Realtime log root directory.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Report output directory.")
    parser.add_argument("--write-report", action="store_true", help="Write session_runtime_evaluation JSON under runtime/reports.")
    parser.add_argument("--since", default=None, help="UTC start time HH:MM for same-day filtering; inclusive.")
    parser.add_argument("--until", default=None, help="UTC end time HH:MM for same-day filtering; exclusive.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    evaluation = evaluate_session_runtime(
        date=args.date,
        quant_data_dir=args.quant_data_dir,
        realtime_log_dir=args.realtime_log_dir,
        load_offline_reports=True,
        since=args.since,
        until=args.until,
    )
    print_summary(evaluation)
    if args.write_report:
        path = write_session_runtime_report(evaluation, report_dir=args.report_dir)
        print(f"wrote_report={path}")
    return 0 if evaluation.session_status != DECISION_FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main())
