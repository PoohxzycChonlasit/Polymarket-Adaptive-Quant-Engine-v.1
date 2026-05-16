"""Offline lifecycle timing analytics for replay evidence.

This tool reads completed quant JSONL replay evidence and writes timing-only
reports. It is intentionally offline-only: it does not change strategy, risk,
execution, runtime cadence, wallet behavior, or paper/live configuration.

Usage:
    python -m tools.lifecycle_timing_report --date 2026-05-15 --write-report
    python -m tools.lifecycle_timing_report --date 2026-05-15 --run-id <run_id> --write-report
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

if __package__ in {None, ""}:
    _repo_root = Path(__file__).resolve().parents[1]
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))

from tools.replay_analyzer import (  # noqa: E402
    DEFAULT_QUANT_DATA_DIR,
    DEFAULT_REPORT_DIR,
    build_time_filter,
    iter_dates,
    load_replay_events,
)


LIFECYCLE_PHASES = (
    "OPENING_SCAN",
    "ACTIVE_INVENTORY_TRADING",
    "PROFIT_MANAGEMENT",
    "FINAL_DERISK",
    "CLOSED_OR_UNSAFE",
)

CUTOFF_BUCKETS = (
    ("<15s", None, 15.0),
    ("15-30s", 15.0, 30.0),
    ("30-45s", 30.0, 45.0),
    ("45-60s", 45.0, 60.0),
    ("60-90s", 60.0, 90.0),
    ("90-120s", 90.0, 120.0),
    ("120-180s", 120.0, 180.0),
    ("180s+", 180.0, None),
)


@dataclass
class CandidateTiming:
    key: str
    first_seen_ts: datetime | None = None
    first_executable_ts: datetime | None = None
    first_ev_visible_ts: datetime | None = None
    first_probability_visible_ts: datetime | None = None
    first_trade_attempt_ts: datetime | None = None
    first_cutoff_ts: datetime | None = None
    first_skip_ts: datetime | None = None
    first_final_derisk_ts: datetime | None = None
    event_timestamps: list[datetime] = field(default_factory=list)
    decision_timestamps: list[datetime] = field(default_factory=list)
    skip_reasons: Counter[str] = field(default_factory=Counter)
    lifecycle_phases: Counter[str] = field(default_factory=Counter)
    cutoff_seconds_remaining: list[float] = field(default_factory=list)


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        number = float(value)
        if number > 1_000_000_000_000:
            number = number / 1000.0
        try:
            return datetime.fromtimestamp(number, tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return _parse_timestamp(float(text))
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _seconds_between(start: datetime | None, end: datetime | None) -> float | None:
    if start is None or end is None:
        return None
    return round((end - start).total_seconds(), 3)


def _set_earliest(current: datetime | None, candidate: datetime | None) -> datetime | None:
    if candidate is None:
        return current
    if current is None or candidate < current:
        return candidate
    return current


def _payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload")
    return payload if isinstance(payload, dict) else {}


def _get_nested(data: dict[str, Any], *paths: str) -> Any:
    for path in paths:
        current: Any = data
        found = True
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                found = False
                break
            current = current.get(part)
        if found and current not in (None, ""):
            return current
    return None


def _as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "ok", "ready", "available"}


def _first_text(payload: dict[str, Any], *paths: str) -> str:
    value = _get_nested(payload, *paths)
    return str(value or "").strip()


def _candidate_key(event: dict[str, Any], payload: dict[str, Any]) -> str:
    stable = _first_text(
        payload,
        "candidate_trace_id",
        "replay_candidate_id",
        "candidate_id",
        "opportunity_id",
        "signal_id",
        "market_key",
        "condition_id",
        "market_id",
        "display.market_key",
        "display.condition_id",
    )
    if stable:
        return stable
    ticker = _first_text(payload, "ticker", "asset", "display.ticker", "display.asset").upper()
    epoch = _first_text(payload, "market_epoch_start", "epoch_start", "event_start_ts", "display.market_epoch_start")
    side = _first_text(payload, "side", "outcome", "decision", "display.side").upper()
    if ticker or epoch or side:
        return f"derived:{ticker or 'UNKNOWN'}:{epoch or 'no_epoch'}:{side or 'no_side'}"
    category = str(event.get("_category") or event.get("event_type") or "event").strip()
    ts = str(event.get("timestamp_utc") or "").strip()
    return f"unkeyed:{category}:{ts}"


def _all_reason_text(payload: dict[str, Any]) -> str:
    keys = (
        "skip_reason",
        "block_reason",
        "main_blocker",
        "risk_reason",
        "reason",
        "decision_reason",
        "cutoff_reason",
        "adaptive_cutoff_denied_reason",
        "micro_timing_denied_reason",
        "active_window_alignment_reason",
        "display.skip_reason",
        "display.block_reason",
        "display.main_blocker",
    )
    values = [_first_text(payload, key) for key in keys]
    return " ".join(value for value in values if value).lower()


def _skip_reason_text(payload: dict[str, Any]) -> str:
    keys = (
        "skip_reason",
        "actual_skip_reason",
        "normalized_skip_reason",
        "block_reason",
        "main_blocker",
        "risk_reason",
        "reason",
        "display.skip_reason",
        "display.normalized_skip_reason",
        "display.block_reason",
        "display.main_blocker",
    )
    values = [_first_text(payload, key) for key in keys]
    return " ".join(value for value in values if value).lower()


def _lifecycle_phase(payload: dict[str, Any]) -> str:
    phase = _first_text(
        payload,
        "lifecycle_phase",
        "market_lifecycle_phase",
        "inventory_lifecycle_phase",
        "display.lifecycle_phase",
        "phase",
    ).upper()
    return phase if phase in LIFECYCLE_PHASES else phase


def _seconds_remaining(payload: dict[str, Any]) -> float | None:
    return _as_float(
        _get_nested(
            payload,
            "seconds_remaining",
            "seconds_until_close",
            "cutoff_block_seconds_remaining",
            "time_remaining_seconds",
            "display.seconds_remaining",
            "display.time_remaining_seconds",
        )
    )


def _event_timestamp(event: dict[str, Any]) -> datetime | None:
    return _parse_timestamp(event.get("timestamp_utc") or event.get("timestamp") or event.get("ts"))


def _candidate_seen_timestamp(event_ts: datetime | None, payload: dict[str, Any]) -> datetime | None:
    seen = _parse_timestamp(
        _get_nested(
            payload,
            "first_seen_ts",
            "candidate_first_seen_ts",
            "candidate_seen_ts",
            "first_seen_at",
            "first_seen_at_utc",
            "display.first_seen_ts",
        )
    )
    return seen or event_ts


def _is_executable(payload: dict[str, Any], event_type: str) -> bool:
    lowered_event = event_type.lower()
    if lowered_event in {"trade_open", "paper_fill", "order_submit_attempt", "order_intent_approved"}:
        return True
    direct = _get_nested(
        payload,
        "executable",
        "candidate_executable",
        "executable_candidate",
        "ev_candidate_ready",
        "model_output_ready",
        "first_executable_before_cutoff",
        "executable_state_persisted_to_decision",
        "display.executable",
    )
    if direct is not None and _as_bool(direct):
        return True
    decision_type = _first_text(payload, "decision_type", "decision", "display.decision").lower()
    state = _first_text(payload, "candidate_state", "readiness_state", "display.candidate_state").upper()
    if decision_type in {"approved", "enter", "buy", "entry"} or state == "READY":
        return True
    executable_book_state = _first_text(payload, "executable_book_state", "executable_book_state_best_seen").upper()
    orderbook_state = _first_text(payload, "orderbook_state_classification", "display.orderbook_state_classification").upper()
    if executable_book_state in {"TRADABLE", "READY", "EXECUTABLE"} or orderbook_state == "READY":
        return True
    return bool(
        _as_bool(_get_nested(payload, "orderbook_ready", "display.orderbook_ready"))
        and _as_bool(_get_nested(payload, "liquidity_ready", "display.liquidity_ready", "depth_ready"))
    )


def _has_ev(payload: dict[str, Any]) -> bool:
    for key in (
        "ev",
        "expected_value",
        "ev_after_spread",
        "model_ev",
        "best_ev",
        "ev_yes",
        "ev_no",
        "display.ev",
        "display.expected_value",
    ):
        if _get_nested(payload, key) is not None:
            return True
    return _as_bool(_get_nested(payload, "ev_visible", "ev_available", "ev_after_spread_available"))


def _has_probability(payload: dict[str, Any]) -> bool:
    for key in (
        "probability",
        "true_probability",
        "probability_yes",
        "probability_no",
        "model_probability",
        "bullish_probability",
        "bearish_probability",
        "display.probability",
        "display.true_probability",
    ):
        if _get_nested(payload, key) is not None:
            return True
    return _as_bool(_get_nested(payload, "probability_visible", "probability_available", "true_probability_available"))


def _is_trade_attempt(payload: dict[str, Any], event_type: str, category: str) -> bool:
    marker = " ".join(
        [
            event_type,
            category,
            _first_text(payload, "event", "execution_event", "action", "status"),
        ]
    ).lower()
    return any(
        token in marker
        for token in (
            "order_submit_attempt",
            "submit_attempt",
            "order_intent_approved",
            "paper_fill",
            "paper_order_created",
            "trade_open",
        )
    )


def _is_skipped(payload: dict[str, Any]) -> bool:
    decision_type = _first_text(payload, "decision_type", "decision", "display.decision").lower()
    actual_decision = _first_text(payload, "actual_decision", "side", "display.side").lower()
    return (
        _as_bool(_get_nested(payload, "skipped", "blocked", "display.skipped"))
        or decision_type in {"skipped", "skip", "blocked", "rejected", "risk_rejected"}
        or actual_decision in {"skip", "skipped", "blocked"}
    )


def load_research_events(
    *,
    base_dir: str | Path,
    date_from: str,
    date_to: str,
    since_utc: datetime | None = None,
    until_utc: datetime | None = None,
    run_id: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    events: list[dict[str, Any]] = []
    bad_json_lines = 0
    root = Path(base_dir)
    for date_text in iter_dates(date_from, date_to):
        path = root / "research_log" / f"{date_text}.jsonl"
        if not path.is_file():
            continue
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
                    if not isinstance(event, dict):
                        bad_json_lines += 1
                        continue
                    if run_id is not None and str(event.get("run_id") or "") != run_id:
                        continue
                    timestamp = _event_timestamp(event)
                    if since_utc is not None and (timestamp is None or timestamp < since_utc):
                        continue
                    if until_utc is not None and (timestamp is None or timestamp >= until_utc):
                        continue
                    event["_category"] = "research_log"
                    events.append(event)
        except OSError:
            continue
    return sorted(events, key=lambda event: str(event.get("timestamp_utc", ""))), bad_json_lines


def _bucket_seconds(value: float | None) -> str:
    if value is None:
        return "unknown"
    for label, low, high in CUTOFF_BUCKETS:
        if (low is None or value >= low) and (high is None or value < high):
            return label
    return "unknown"


def _histogram(values: list[float], buckets: tuple[tuple[str, float | None, float | None], ...]) -> list[list[Any]]:
    counts: Counter[str] = Counter()
    for value in values:
        label = "unknown"
        for bucket_label, low, high in buckets:
            if (low is None or value >= low) and (high is None or value < high):
                label = bucket_label
                break
        counts[label] += 1
    return [[label, counts.get(label, 0)] for label, _low, _high in buckets] + [["unknown", counts.get("unknown", 0)]]


def _stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "min": None, "max": None, "avg": None, "p50": None, "p90": None}
    ordered = sorted(values)

    def percentile(pct: float) -> float:
        if len(ordered) == 1:
            return ordered[0]
        index = (len(ordered) - 1) * pct
        low = int(index)
        high = min(low + 1, len(ordered) - 1)
        fraction = index - low
        return ordered[low] + (ordered[high] - ordered[low]) * fraction

    return {
        "count": len(values),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
        "avg": round(mean(values), 3),
        "p50": round(percentile(0.50), 3),
        "p90": round(percentile(0.90), 3),
    }


def _transition_summary(phase_events: list[tuple[datetime, str]]) -> list[dict[str, Any]]:
    transitions: list[dict[str, Any]] = []
    previous_phase = ""
    previous_ts: datetime | None = None
    for ts, phase in sorted(phase_events, key=lambda item: item[0]):
        if not phase or phase == previous_phase:
            continue
        transitions.append(
            {
                "from": previous_phase or None,
                "to": phase,
                "timestamp_utc": _iso(ts),
                "seconds_since_previous_phase": _seconds_between(previous_ts, ts),
            }
        )
        previous_phase = phase
        previous_ts = ts
    return transitions


def analyze_lifecycle_timing(
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

    time_filter = build_time_filter(date_from=date_from, date_to=date_to, since=since, until=until)
    events, bad_json_lines = load_replay_events(
        base_dir=base_dir,
        date_from=date_from,
        date_to=date_to,
        since_utc=time_filter.get("since_utc"),
        until_utc=time_filter.get("until_utc"),
        run_id=run_id,
    )
    research_events, research_bad_json_lines = load_research_events(
        base_dir=base_dir,
        date_from=date_from,
        date_to=date_to,
        since_utc=time_filter.get("since_utc"),
        until_utc=time_filter.get("until_utc"),
        run_id=run_id,
    )
    events = sorted([*events, *research_events], key=lambda event: str(event.get("timestamp_utc", "")))
    bad_json_lines += research_bad_json_lines

    candidates: dict[str, CandidateTiming] = {}
    category_counts: Counter[str] = Counter()
    event_type_counts: Counter[str] = Counter()
    skip_reason_counts: Counter[str] = Counter()
    lifecycle_counts: Counter[str] = Counter()
    cutoff_histogram_counts: Counter[str] = Counter()
    actual_revisit_frequencies: list[float] = []
    candidate_queue_age_seconds: list[float] = []
    hot_path_admission_wait_seconds: list[float] = []
    executable_to_decision_seconds: list[float] = []
    configured_loop_seconds: list[float] = []
    effective_loop_seconds: list[float] = []
    cooldown_skip_count = 0
    cooldown_cutoff_collision_count = 0
    missing_timestamp_events = 0
    timestamp_order_warnings = 0
    previous_ts: datetime | None = None
    phase_events: list[tuple[datetime, str]] = []

    for event in events:
        payload = _payload(event)
        event_ts = _event_timestamp(event)
        if event_ts is None:
            missing_timestamp_events += 1
            continue
        if previous_ts is not None and event_ts < previous_ts:
            timestamp_order_warnings += 1
        previous_ts = event_ts

        category = str(event.get("_category") or "").strip()
        event_type = str(event.get("event_type") or "").strip()
        category_counts[category or "unknown"] += 1
        event_type_counts[event_type or "unknown"] += 1

        key = _candidate_key(event, payload)
        candidate = candidates.setdefault(key, CandidateTiming(key=key))
        candidate.event_timestamps.append(event_ts)
        candidate.first_seen_ts = _set_earliest(candidate.first_seen_ts, _candidate_seen_timestamp(event_ts, payload))

        if category == "decision_log" or event_type.lower() == "decision":
            candidate.decision_timestamps.append(event_ts)

        phase = _lifecycle_phase(payload)
        if phase:
            lifecycle_counts[phase] += 1
            candidate.lifecycle_phases[phase] += 1
            phase_events.append((event_ts, phase))
            if phase == "FINAL_DERISK":
                candidate.first_final_derisk_ts = _set_earliest(candidate.first_final_derisk_ts, event_ts)

        reason_text = _all_reason_text(payload)
        skip_reason_text = _skip_reason_text(payload)
        seconds_remaining = _seconds_remaining(payload)
        explicit_executable_ts = _parse_timestamp(
            _get_nested(
                payload,
                "executable_state_first_seen_ts",
                "first_tradable_at_utc",
                "first_tradable_at",
                "first_tradable_ts",
                "display.first_tradable_at_utc",
                "display.first_tradable_at",
            )
        )
        if explicit_executable_ts is not None:
            candidate.first_executable_ts = _set_earliest(candidate.first_executable_ts, explicit_executable_ts)
        if _is_executable(payload, event_type):
            candidate.first_executable_ts = _set_earliest(candidate.first_executable_ts, explicit_executable_ts or event_ts)
        if _has_ev(payload):
            candidate.first_ev_visible_ts = _set_earliest(candidate.first_ev_visible_ts, event_ts)
        if _has_probability(payload):
            candidate.first_probability_visible_ts = _set_earliest(candidate.first_probability_visible_ts, event_ts)
        if _is_trade_attempt(payload, event_type, category):
            candidate.first_trade_attempt_ts = _set_earliest(candidate.first_trade_attempt_ts, event_ts)

        if _is_skipped(payload):
            candidate.first_skip_ts = _set_earliest(candidate.first_skip_ts, event_ts)
            reason = skip_reason_text or reason_text or "unknown_skip"
            candidate.skip_reasons[reason] += 1
            skip_reason_counts[reason] += 1

        cutoff_related = any(token in reason_text for token in ("time_unsafe", "cutoff", "hard_close", "too_late"))
        if cutoff_related:
            candidate.first_cutoff_ts = _set_earliest(candidate.first_cutoff_ts, event_ts)
            if seconds_remaining is not None:
                candidate.cutoff_seconds_remaining.append(seconds_remaining)
            cutoff_histogram_counts[_bucket_seconds(seconds_remaining)] += 1

        cooldown_related = "frequency_cooldown" in reason_text or "cooldown" in reason_text
        if cooldown_related:
            cooldown_skip_count += 1
            if seconds_remaining is not None and seconds_remaining <= 90:
                cooldown_cutoff_collision_count += 1

        actual_revisit = _as_float(_get_nested(payload, "actual_market_revisit_frequency_seconds"))
        if actual_revisit is not None and actual_revisit >= 0:
            actual_revisit_frequencies.append(actual_revisit)
        queue_age_ms = _as_float(_get_nested(payload, "candidate_queue_age_ms"))
        if queue_age_ms is not None and queue_age_ms >= 0:
            candidate_queue_age_seconds.append(queue_age_ms / 1000.0)
        admission_wait_ms = _as_float(_get_nested(payload, "hot_path_admission_wait_ms"))
        if admission_wait_ms is not None and admission_wait_ms >= 0:
            hot_path_admission_wait_seconds.append(admission_wait_ms / 1000.0)
        executable_to_decision_ms = _as_float(_get_nested(payload, "executable_to_decision_ms"))
        if executable_to_decision_ms is not None and executable_to_decision_ms >= 0:
            executable_to_decision_seconds.append(executable_to_decision_ms / 1000.0)
        configured_interval = _as_float(_get_nested(payload, "configured_decision_loop_interval_seconds"))
        if configured_interval is not None and configured_interval > 0:
            configured_loop_seconds.append(configured_interval)
        effective_interval = _as_float(_get_nested(payload, "effective_outer_loop_interval_seconds"))
        if effective_interval is not None and effective_interval > 0:
            effective_loop_seconds.append(effective_interval)

    executable_age_before_skip: list[float] = []
    revisit_delays: list[float] = []
    time_to_final_derisk: list[float] = []
    candidate_rows: list[dict[str, Any]] = []
    executable_candidates = 0
    executable_cutoff_candidates = 0
    executable_trade_attempt_candidates = 0

    for candidate in candidates.values():
        if candidate.first_executable_ts is not None:
            executable_candidates += 1
            if candidate.first_cutoff_ts is not None:
                executable_cutoff_candidates += 1
            if candidate.first_trade_attempt_ts is not None:
                executable_trade_attempt_candidates += 1

        age = _seconds_between(candidate.first_executable_ts, candidate.first_skip_ts or candidate.first_cutoff_ts)
        if age is not None and age >= 0:
            executable_age_before_skip.append(age)

        decision_times = sorted(set(candidate.decision_timestamps))
        for prev, current in zip(decision_times, decision_times[1:]):
            delay = _seconds_between(prev, current)
            if delay is not None and delay >= 0:
                revisit_delays.append(delay)

        derisk = _seconds_between(candidate.first_seen_ts, candidate.first_final_derisk_ts)
        if derisk is not None and derisk >= 0:
            time_to_final_derisk.append(derisk)

        if candidate.first_cutoff_ts or candidate.first_trade_attempt_ts or candidate.first_executable_ts:
            candidate_rows.append(
                {
                    "candidate_key": candidate.key,
                    "first_seen_ts": _iso(candidate.first_seen_ts),
                    "first_executable_ts": _iso(candidate.first_executable_ts),
                    "first_ev_visible_ts": _iso(candidate.first_ev_visible_ts),
                    "first_probability_visible_ts": _iso(candidate.first_probability_visible_ts),
                    "first_trade_attempt_ts": _iso(candidate.first_trade_attempt_ts),
                    "cutoff_ts": _iso(candidate.first_cutoff_ts),
                    "executable_age_before_skip_seconds": age,
                    "top_skip_reasons": [[reason, count] for reason, count in candidate.skip_reasons.most_common(3)],
                    "lifecycle_phases": [[phase, count] for phase, count in candidate.lifecycle_phases.most_common()],
                    "cutoff_seconds_remaining": candidate.cutoff_seconds_remaining[:10],
                }
            )

    cooldown_collision_rate = (
        round(cooldown_cutoff_collision_count / cooldown_skip_count, 4) if cooldown_skip_count else 0.0
    )
    cutoff_survival_rate = (
        round(executable_trade_attempt_candidates / executable_candidates, 4) if executable_candidates else 0.0
    )
    cutoff_starvation_rate = (
        round(executable_cutoff_candidates / executable_candidates, 4) if executable_candidates else 0.0
    )
    cutoff_starvation_confirmed = executable_cutoff_candidates > 0 or cutoff_histogram_counts.total() > 0
    queue_age_stats = _stats(candidate_queue_age_seconds)
    revisit_stats = _stats(revisit_delays)
    actual_revisit_stats = _stats(actual_revisit_frequencies)
    configured_loop_avg = round(mean(configured_loop_seconds), 3) if configured_loop_seconds else None
    effective_loop_avg = round(mean(effective_loop_seconds), 3) if effective_loop_seconds else None
    median_queue_age = queue_age_stats.get("p50")
    median_revisit = actual_revisit_stats.get("p50") or revisit_stats.get("p50")
    p90_revisit = actual_revisit_stats.get("p90") or revisit_stats.get("p90")
    executable_to_decision_stats = _stats(executable_to_decision_seconds)
    p50_executable_to_decision = executable_to_decision_stats.get("p50")
    p90_executable_to_decision = executable_to_decision_stats.get("p90")
    revisit_cadence_pressure = bool(
        (cooldown_skip_count > 0 and (cooldown_collision_rate > 0 or "frequency_cooldown" in " ".join(skip_reason_counts.keys())))
        or (cutoff_starvation_confirmed and isinstance(median_queue_age, (int, float)) and median_queue_age >= 30)
        or (
            configured_loop_avg
            and isinstance(median_revisit, (int, float))
            and median_revisit >= configured_loop_avg * 1.1
        )
        or (
            cutoff_starvation_confirmed
            and isinstance(p90_revisit, (int, float))
            and p90_revisit >= 60
        )
        or (
            cutoff_starvation_confirmed
            and isinstance(p50_executable_to_decision, (int, float))
            and p50_executable_to_decision >= 25
        )
        or (
            cutoff_starvation_confirmed
            and isinstance(p90_executable_to_decision, (int, float))
            and p90_executable_to_decision >= 60
        )
    )

    return {
        "generated_at_utc": _iso(datetime.now(timezone.utc)),
        "scope": "offline_replay_lifecycle_timing_only",
        "runtime_behavior_changed": False,
        "live_behavior_changed": False,
        "date_from": date_from,
        "date_to": date_to,
        "run_id": run_id or "",
        "time_filter": {
            "since_utc": _iso(time_filter.get("since_utc")),
            "until_utc": _iso(time_filter.get("until_utc")),
        },
        "events_loaded": len(events),
        "bad_json_lines": bad_json_lines,
        "missing_timestamp_events": missing_timestamp_events,
        "timestamp_order_warnings": timestamp_order_warnings,
        "event_categories": [[key, value] for key, value in category_counts.most_common()],
        "event_types": [[key, value] for key, value in event_type_counts.most_common()],
        "candidate_count": len(candidates),
        "candidate_timing_coverage": {
            "first_seen": sum(1 for item in candidates.values() if item.first_seen_ts is not None),
            "first_executable": executable_candidates,
            "first_ev_visible": sum(1 for item in candidates.values() if item.first_ev_visible_ts is not None),
            "first_probability_visible": sum(
                1 for item in candidates.values() if item.first_probability_visible_ts is not None
            ),
            "first_trade_attempt": executable_trade_attempt_candidates,
            "cutoff_ts": sum(1 for item in candidates.values() if item.first_cutoff_ts is not None),
        },
        "lifecycle_phase_distribution": [[phase, count] for phase, count in lifecycle_counts.most_common()],
        "lifecycle_phase_transitions": _transition_summary(phase_events)[:100],
        "timing_metrics": {
            "executable_age_before_skip_seconds": _stats(executable_age_before_skip),
            "revisit_delay_distribution_seconds": revisit_stats,
            "actual_market_revisit_frequency_seconds": actual_revisit_stats,
            "candidate_queue_age_seconds": queue_age_stats,
            "hot_path_admission_wait_seconds": _stats(hot_path_admission_wait_seconds),
            "executable_to_decision_seconds": executable_to_decision_stats,
            "configured_decision_loop_interval_seconds_avg": configured_loop_avg,
            "effective_outer_loop_interval_seconds_avg": effective_loop_avg,
            "time_to_FINAL_DERISK_seconds": _stats(time_to_final_derisk),
            "cooldown_skip_count": cooldown_skip_count,
            "cooldown_cutoff_collision_count": cooldown_cutoff_collision_count,
            "cooldown_collision_rate": cooldown_collision_rate,
            "executable_candidate_count": executable_candidates,
            "executable_cutoff_candidate_count": executable_cutoff_candidates,
            "executable_trade_attempt_candidate_count": executable_trade_attempt_candidates,
            "cutoff_survival_rate": cutoff_survival_rate,
            "cutoff_starvation_rate": cutoff_starvation_rate,
        },
        "histograms": {
            "cutoff_pressure_seconds_remaining": [
                [label, cutoff_histogram_counts.get(label, 0)]
                for label in [bucket[0] for bucket in CUTOFF_BUCKETS] + ["unknown"]
            ],
            "revisit_delay_seconds": _histogram(
                revisit_delays,
                (
                    ("<5s", None, 5.0),
                    ("5-10s", 5.0, 10.0),
                    ("10-30s", 10.0, 30.0),
                    ("30-60s", 30.0, 60.0),
                    ("60-120s", 60.0, 120.0),
                    ("120s+", 120.0, None),
                ),
            ),
            "executable_age_before_skip_seconds": _histogram(
                executable_age_before_skip,
                (
                    ("<5s", None, 5.0),
                    ("5-15s", 5.0, 15.0),
                    ("15-30s", 15.0, 30.0),
                    ("30-60s", 30.0, 60.0),
                    ("60-120s", 60.0, 120.0),
                    ("120s+", 120.0, None),
                ),
            ),
        },
        "top_skip_reasons": [[reason, count] for reason, count in skip_reason_counts.most_common(20)],
        "candidate_samples": sorted(
            candidate_rows,
            key=lambda item: (
                item.get("cutoff_ts") is None,
                item.get("first_trade_attempt_ts") is None,
                item.get("candidate_key") or "",
            ),
        )[:50],
        "interpretation": {
            "cutoff_starvation_confirmed": cutoff_starvation_confirmed,
            "revisit_cadence_pressure": revisit_cadence_pressure,
            "notes": [
                "offline evidence only; does not alter runtime timing or cutoff behavior",
                "candidate identity may be derived when replay fields lack direct candidate_trace_id",
                "cooldown collision uses visible frequency_cooldown/cooldown reasons with <=90 seconds remaining",
            ],
        },
    }


def _date_part(date_from: str, date_to: str, run_id: str | None) -> str:
    part = date_from if date_from == date_to else f"{date_from}_to_{date_to}"
    return f"{part}_run_{run_id}" if run_id else part


def _write_json(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _markdown_table(rows: list[list[Any]]) -> str:
    if not rows:
        return "| value | count |\n|---|---|\n"
    lines = ["| value | count |", "|---|---|"]
    for value, count in rows:
        lines.append(f"| {value} | {count} |")
    return "\n".join(lines)


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report.get("timing_metrics", {})
    coverage = report.get("candidate_timing_coverage", {})
    interpretation = report.get("interpretation", {})
    histograms = report.get("histograms", {})
    lifecycle = report.get("lifecycle_phase_distribution", [])
    lines = [
        "# Lifecycle Timing Report",
        "",
        f"- generated_at_utc: {report.get('generated_at_utc')}",
        f"- date: {report.get('date_from')} to {report.get('date_to')}",
        f"- run_id: {report.get('run_id') or '(all)'}",
        f"- events_loaded: {report.get('events_loaded')}",
        f"- bad_json_lines: {report.get('bad_json_lines')}",
        f"- candidates: {report.get('candidate_count')}",
        f"- cutoff_starvation_confirmed: {interpretation.get('cutoff_starvation_confirmed')}",
        f"- revisit_cadence_pressure: {interpretation.get('revisit_cadence_pressure')}",
        f"- runtime_behavior_changed: {report.get('runtime_behavior_changed')}",
        "",
        "## Candidate Timing Coverage",
        "",
        _markdown_table([[key, value] for key, value in coverage.items()]),
        "",
        "## Timing Metrics",
        "",
        f"- cooldown_skip_count: {metrics.get('cooldown_skip_count')}",
        f"- cooldown_collision_rate: {metrics.get('cooldown_collision_rate')}",
        f"- cutoff_survival_rate: {metrics.get('cutoff_survival_rate')}",
        f"- cutoff_starvation_rate: {metrics.get('cutoff_starvation_rate')}",
        f"- executable_age_before_skip_seconds: {metrics.get('executable_age_before_skip_seconds')}",
        f"- revisit_delay_distribution_seconds: {metrics.get('revisit_delay_distribution_seconds')}",
        f"- actual_market_revisit_frequency_seconds: {metrics.get('actual_market_revisit_frequency_seconds')}",
        f"- candidate_queue_age_seconds: {metrics.get('candidate_queue_age_seconds')}",
        f"- hot_path_admission_wait_seconds: {metrics.get('hot_path_admission_wait_seconds')}",
        f"- executable_to_decision_seconds: {metrics.get('executable_to_decision_seconds')}",
        f"- configured_decision_loop_interval_seconds_avg: {metrics.get('configured_decision_loop_interval_seconds_avg')}",
        f"- effective_outer_loop_interval_seconds_avg: {metrics.get('effective_outer_loop_interval_seconds_avg')}",
        f"- time_to_FINAL_DERISK_seconds: {metrics.get('time_to_FINAL_DERISK_seconds')}",
        "",
        "## Lifecycle Phase Distribution",
        "",
        _markdown_table(lifecycle),
        "",
        "## Cutoff Pressure Histogram",
        "",
        _markdown_table(histograms.get("cutoff_pressure_seconds_remaining", [])),
        "",
        "## Revisit Delay Histogram",
        "",
        _markdown_table(histograms.get("revisit_delay_seconds", [])),
        "",
        "## Top Skip Reasons",
        "",
        _markdown_table(report.get("top_skip_reasons", [])[:20]),
        "",
        "## Guardrails",
        "",
        "- Offline report only.",
        "- Does not modify runtime cadence, strategy, risk sizing, execution, wallet, or live config.",
        "- Does not wire replay evidence into runtime decisions.",
        "",
    ]
    return "\n".join(lines)


def write_reports(report: dict[str, Any], *, report_dir: str | Path = DEFAULT_REPORT_DIR) -> tuple[Path, Path]:
    output_dir = Path(report_dir)
    date_from = str(report.get("date_from") or "")
    date_to = str(report.get("date_to") or date_from)
    run_id = str(report.get("run_id") or "") or None
    part = _date_part(date_from, date_to, run_id)
    json_path = output_dir / f"lifecycle_timing_report_{part}.json"
    markdown_path = output_dir / f"lifecycle_timing_report_{part}.md"
    _write_json(json_path, report)
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def print_summary(report: dict[str, Any], paths: tuple[Path, Path] | None = None) -> None:
    metrics = report.get("timing_metrics", {})
    interpretation = report.get("interpretation", {})
    print("Lifecycle timing report")
    print(f"date={report.get('date_from')}..{report.get('date_to')} run_id={report.get('run_id') or '(all)'}")
    print(f"events={report.get('events_loaded')} candidates={report.get('candidate_count')} bad_json={report.get('bad_json_lines')}")
    print(f"cutoff_starvation_confirmed={interpretation.get('cutoff_starvation_confirmed')}")
    print(f"revisit_cadence_pressure={interpretation.get('revisit_cadence_pressure')}")
    print(f"cooldown_collision_rate={metrics.get('cooldown_collision_rate')}")
    print(f"cutoff_survival_rate={metrics.get('cutoff_survival_rate')}")
    print(f"cutoff_starvation_rate={metrics.get('cutoff_starvation_rate')}")
    if paths:
        print(f"json_report={paths[0]}")
        print(f"markdown_report={paths[1]}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline lifecycle timing replay report.")
    parser.add_argument("--date", help="Single UTC date YYYY-MM-DD.")
    parser.add_argument("--date-from", help="Start UTC date YYYY-MM-DD.")
    parser.add_argument("--date-to", help="End UTC date YYYY-MM-DD.")
    parser.add_argument("--since", help="Optional HH:MM UTC lower bound for --date/--date-from.")
    parser.add_argument("--until", help="Optional HH:MM UTC upper bound for --date/--date-from.")
    parser.add_argument("--run-id", help="Optional run_id scope.")
    parser.add_argument("--base-dir", default=str(DEFAULT_QUANT_DATA_DIR), help="Quant JSONL base directory.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Output report directory.")
    parser.add_argument("--write-report", action="store_true", help="Write JSON and Markdown reports.")
    args = parser.parse_args(argv)

    report = analyze_lifecycle_timing(
        base_dir=args.base_dir,
        date=args.date,
        date_from=args.date_from,
        date_to=args.date_to,
        since=args.since,
        until=args.until,
        run_id=args.run_id,
    )
    paths = write_reports(report, report_dir=args.report_dir) if args.write_report else None
    print_summary(report, paths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
