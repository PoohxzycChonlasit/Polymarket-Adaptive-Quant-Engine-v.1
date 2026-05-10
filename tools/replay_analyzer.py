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
class ReplayReport:
    date_from: str | None = None
    date_to: str | None = None
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
) -> bool:
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
                        if _event_in_time_window(event, since_utc=since_utc, until_utc=until_utc):
                            events.append(event)
                    else:
                        bad_json_lines += 1
        except OSError:
            continue
    return sorted(events, key=lambda event: str(event.get("timestamp_utc", ""))), bad_json_lines


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
) -> ReplayReport:
    if date:
        date_from = date_to = date
    if not date_from:
        date_from = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not date_to:
        date_to = date_from

    events, bad_json_lines = load_replay_events(
        base_dir=base_dir,
        date_from=date_from,
        date_to=date_to,
        since_utc=since_utc,
        until_utc=until_utc,
    )
    report = ReplayReport(
        date_from=date_from,
        date_to=date_to,
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
    date_part = report.date_from if report.date_from == report.date_to else f"{report.date_from}_to_{report.date_to}"
    output_path = output_dir / f"replay_report_{date_part}.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report.to_dict(), handle, indent=2, sort_keys=True, default=str)
    return output_path


def write_replay_trades_csv(report: ReplayReport, *, report_dir: str | Path | None = None) -> Path:
    output_dir = Path(report_dir or DEFAULT_REPORT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    date_part = report.date_from if report.date_from == report.date_to else f"{report.date_from}_to_{report.date_to}"
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
    print(f"range={report.date_from}..{report.date_to} events={report.events_loaded} bad_json={report.bad_json_lines}")
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
    parser.add_argument("--base-dir", default=str(DEFAULT_QUANT_DATA_DIR), help="Quant data root directory.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Output report directory.")
    parser.add_argument("--no-json", action="store_true", help="Do not write replay_report JSON.")
    parser.add_argument("--csv", action="store_true", help="Write replay_trades CSV.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = analyze_replay(
        base_dir=args.base_dir,
        date=args.date,
        date_from=args.date_from,
        date_to=args.date_to,
        report_dir=args.report_dir,
        write_reports=not args.no_json,
        write_csv=args.csv,
    )
    print_summary(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
