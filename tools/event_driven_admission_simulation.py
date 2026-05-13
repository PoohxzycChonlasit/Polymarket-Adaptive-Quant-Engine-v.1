from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:  # pragma: no cover - direct script execution path
    from tools.replay_analyzer import (
        DEFAULT_QUANT_DATA_DIR,
        DEFAULT_REPORT_DIR,
        build_time_filter,
        load_replay_events,
    )
except ModuleNotFoundError:  # pragma: no cover - `python tools/...` path
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from tools.replay_analyzer import (
        DEFAULT_QUANT_DATA_DIR,
        DEFAULT_REPORT_DIR,
        build_time_filter,
        load_replay_events,
    )


ACTIVE_MODEL_PHASES = {"ACTIVE_INVENTORY_TRADING", "PROFIT_MANAGEMENT"}
TERMINAL_OR_OBSERVE_ONLY_PHASES = {"OPENING_SCAN", "FINAL_DERISK", "CLOSED_OR_UNSAFE", "UNKNOWN"}
DEFAULT_MAX_BOOK_AGE_MS = 3_000.0
DEFAULT_MAX_SIDE_SPREAD = 0.10
MODEL_REQUIRED_FIELD_GROUPS = {
    "underlying_price": ("current_price", "underlying_price", "oracle_price", "index_price"),
    "target_price": ("price_to_beat", "target_price", "ptb_price"),
    "seconds_remaining": ("seconds_remaining", "seconds_until_close", "time_remaining"),
    "market_price": ("market_price", "yes_ask", "no_ask", "ask_price"),
    "spread": ("spread", "spread_normalized", "yes_spread", "no_spread"),
    "liquidity": ("liquidity", "liquidity_usd", "liquidity_state", "depth_ready"),
    "token_pair_identity": ("condition_id", "yes_token_id", "no_token_id"),
}
RISK_OBSERVABILITY_FIELDS = (
    "risk_state",
    "risk_decision",
    "risk_mode",
    "risk_block_reason",
    "available_risk_budget",
    "remaining_risk_budget",
    "risk_budget_used",
    "current_exposure",
    "target_exposure",
    "reconciliation_state",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _payload(event: dict[str, Any]) -> dict[str, Any]:
    raw_payload = event.get("payload")
    if isinstance(raw_payload, dict):
        payload = dict(raw_payload)
        for key in ("run_id", "timestamp_utc", "event_type", "mode", "_category"):
            if key in event and key not in payload:
                payload[key] = event[key]
        return payload
    return dict(event)


def _producer(event: dict[str, Any]) -> str:
    return str(event.get("_category") or event.get("event_category") or event.get("producer") or "unknown")


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        normalized = value.strip()
        return bool(normalized) and normalized.upper() not in {"UNKNOWN", "--", "NONE", "NULL"}
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


def _float_or_none(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _positive_float(value: Any) -> float | None:
    number = _float_or_none(value)
    if number is None or number <= 0:
        return None
    return number


def _top(counter: Counter[str], limit: int = 8) -> dict[str, int]:
    return {key: count for key, count in counter.most_common(limit)}


def _source_event_allowed(event: dict[str, Any], payload: dict[str, Any]) -> bool:
    producer = _producer(event)
    if producer == "market_snapshots":
        return True
    return str(payload.get("executable_liquidity_event_role") or "").strip() == "passive_telemetry_only"


def _is_executable_book_event(payload: dict[str, Any]) -> bool:
    yes_bid = _positive_float(payload.get("yes_bid") or payload.get("yes_best_bid"))
    yes_ask = _positive_float(payload.get("yes_ask") or payload.get("yes_best_ask"))
    no_bid = _positive_float(payload.get("no_bid") or payload.get("no_best_bid"))
    no_ask = _positive_float(payload.get("no_ask") or payload.get("no_best_ask"))
    return yes_bid is not None and yes_ask is not None and no_bid is not None and no_ask is not None


def _token_pair_lineage_ok(payload: dict[str, Any]) -> bool:
    if payload.get("orderbook_lineage_match") is False or payload.get("token_pair_lineage_match") is False:
        return False
    has_pair = _present(payload.get("yes_token_id")) and _present(payload.get("no_token_id"))
    has_market_key = any(
        _present(payload.get(key))
        for key in ("condition_id", "market_slug", "market_id", "source_market_id", "market_key")
    )
    return bool(has_pair and has_market_key)


def _lifecycle_phase(payload: dict[str, Any]) -> str:
    raw_phase = payload.get("lifecycle_phase") or payload.get("model_activation_lifecycle_phase")
    if _present(raw_phase):
        return str(raw_phase).strip().upper()
    seconds_remaining = _float_or_none(payload.get("seconds_remaining") or payload.get("seconds_until_close"))
    if seconds_remaining is None:
        return "UNKNOWN"
    elapsed = max(0.0, 300.0 - seconds_remaining)
    if elapsed < 35:
        return "OPENING_SCAN"
    if elapsed < 240:
        return "ACTIVE_INVENTORY_TRADING"
    if elapsed < 270:
        return "PROFIT_MANAGEMENT"
    if elapsed < 300:
        return "FINAL_DERISK"
    return "CLOSED_OR_UNSAFE"


def _book_age_ms(payload: dict[str, Any]) -> float | None:
    ages = [
        _float_or_none(payload.get("yes_orderbook_age_ms")),
        _float_or_none(payload.get("no_orderbook_age_ms")),
        _float_or_none(payload.get("orderbook_age_ms")),
        _float_or_none(payload.get("book_event_age_ms")),
        _float_or_none(payload.get("executable_book_last_seen_age_ms")),
    ]
    present_ages = [age for age in ages if age is not None]
    if not present_ages:
        return None
    return max(present_ages)


def _freshness_ok(payload: dict[str, Any], max_age_ms: float) -> tuple[bool, str]:
    age = _book_age_ms(payload)
    if age is None:
        return False, "freshness_missing"
    if age > max_age_ms:
        return False, "stale_executable_book"
    return True, "fresh"


def _spread_ok(payload: dict[str, Any], max_side_spread: float) -> tuple[bool, str]:
    spreads: list[float] = []
    yes_bid = _positive_float(payload.get("yes_bid") or payload.get("yes_best_bid"))
    yes_ask = _positive_float(payload.get("yes_ask") or payload.get("yes_best_ask"))
    no_bid = _positive_float(payload.get("no_bid") or payload.get("no_best_bid"))
    no_ask = _positive_float(payload.get("no_ask") or payload.get("no_best_ask"))
    if yes_bid is not None and yes_ask is not None:
        spreads.append(max(0.0, yes_ask - yes_bid))
    if no_bid is not None and no_ask is not None:
        spreads.append(max(0.0, no_ask - no_bid))
    explicit_spread = _float_or_none(payload.get("spread") or payload.get("spread_normalized"))
    if explicit_spread is not None:
        spreads.append(abs(explicit_spread))
    if not spreads:
        return False, "spread_missing_or_invalid"
    if max(spreads) > max_side_spread:
        return False, "spread_too_wide"
    return True, "spread_ok"


def _risk_gate_observable(payload: dict[str, Any]) -> bool:
    return any(_present(payload.get(key)) for key in RISK_OBSERVABILITY_FIELDS)


def _missing_model_required_groups(payload: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for group, keys in MODEL_REQUIRED_FIELD_GROUPS.items():
        if group == "token_pair_identity":
            has_identity = _present(payload.get("condition_id")) and _present(payload.get("yes_token_id")) and _present(
                payload.get("no_token_id")
            )
            if not has_identity:
                missing.append(group)
            continue
        if group == "spread":
            yes_bid = _positive_float(payload.get("yes_bid") or payload.get("yes_best_bid"))
            yes_ask = _positive_float(payload.get("yes_ask") or payload.get("yes_best_ask"))
            no_bid = _positive_float(payload.get("no_bid") or payload.get("no_best_bid"))
            no_ask = _positive_float(payload.get("no_ask") or payload.get("no_best_ask"))
            if (yes_bid is not None and yes_ask is not None) or (no_bid is not None and no_ask is not None):
                continue
        if not any(_present(payload.get(key)) for key in keys):
            missing.append(group)
    return missing


def build_event_driven_admission_simulation_report(
    *,
    date: str,
    base_dir: str | Path = DEFAULT_QUANT_DATA_DIR,
    since: str | None = None,
    until: str | None = None,
    run_id: str | None = None,
    max_book_age_ms: float = DEFAULT_MAX_BOOK_AGE_MS,
    max_side_spread: float = DEFAULT_MAX_SIDE_SPREAD,
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

    source_event_counts_by_producer: Counter[str] = Counter()
    lifecycle_split: Counter[str] = Counter()
    fail_counts_by_gate: Counter[str] = Counter()
    fail_reasons: Counter[str] = Counter()
    phase_fail_counts: Counter[str] = Counter()
    model_required_missing: Counter[str] = Counter()
    risk_observable_count = 0
    executable_event_count = 0
    same_token_pair_count = 0
    model_eligibility_would_be_reached_count = 0
    observed_probability_model_called_count = 0

    for event in events:
        payload = _payload(event)
        if _bool_true(payload.get("probability_model_called")):
            observed_probability_model_called_count += 1
        if not _source_event_allowed(event, payload):
            continue
        source_event_counts_by_producer[_producer(event)] += 1
        if not _is_executable_book_event(payload):
            continue

        executable_event_count += 1
        phase = _lifecycle_phase(payload)
        lifecycle_split[phase] += 1

        if not _token_pair_lineage_ok(payload):
            fail_counts_by_gate["token_pair_lineage_ok"] += 1
            fail_reasons["missing_or_mismatched_token_pair_lineage"] += 1
            phase_fail_counts[f"{phase}:token_pair_lineage_ok"] += 1
            continue
        same_token_pair_count += 1

        if phase not in ACTIVE_MODEL_PHASES:
            fail_counts_by_gate["lifecycle_window_ok"] += 1
            fail_reasons[f"phase_{phase.lower()}"] += 1
            phase_fail_counts[f"{phase}:lifecycle_window_ok"] += 1
            continue

        fresh, freshness_reason = _freshness_ok(payload, max_book_age_ms)
        if not fresh:
            fail_counts_by_gate["freshness_ok"] += 1
            fail_reasons[freshness_reason] += 1
            phase_fail_counts[f"{phase}:freshness_ok"] += 1
            continue

        spread, spread_reason = _spread_ok(payload, max_side_spread)
        if not spread:
            fail_counts_by_gate["spread_ok"] += 1
            fail_reasons[spread_reason] += 1
            phase_fail_counts[f"{phase}:spread_ok"] += 1
            continue

        model_eligibility_would_be_reached_count += 1
        if _risk_gate_observable(payload):
            risk_observable_count += 1
        for missing_group in _missing_model_required_groups(payload):
            model_required_missing[missing_group] += 1

    estimated_uplift = max(0, model_eligibility_would_be_reached_count - observed_probability_model_called_count)
    dominant_gate = fail_counts_by_gate.most_common(1)[0][0] if fail_counts_by_gate else "NONE"
    dominant_reason = fail_reasons.most_common(1)[0][0] if fail_reasons else "NONE"
    active_profit_final_split = {
        "ACTIVE_INVENTORY_TRADING": lifecycle_split.get("ACTIVE_INVENTORY_TRADING", 0),
        "PROFIT_MANAGEMENT": lifecycle_split.get("PROFIT_MANAGEMENT", 0),
        "FINAL_DERISK": lifecycle_split.get("FINAL_DERISK", 0),
    }

    return {
        "schema_version": "event_driven_admission_simulation_v1",
        "scope": "offline_replay_simulation_only",
        "generated_at_utc": _utc_now(),
        "date": date,
        "time_filter": {
            "since": since,
            "until": until,
            "run_id": run_id,
        },
        "guardrails": {
            "offline_only": True,
            "runtime_behavior_changed": False,
            "strategy_changed": False,
            "risk_changed": False,
            "execution_changed": False,
            "live_behavior_changed": False,
            "simulation_wired_to_trading": False,
        },
        "source_events_loaded": len(events),
        "bad_json_lines": bad_json_lines,
        "source_event_counts_by_producer": dict(source_event_counts_by_producer),
        "simulation_funnel": {
            "executable_liquidity_event_count": executable_event_count,
            "same_token_pair_count": same_token_pair_count,
            "token_pair_lineage_ok_count": same_token_pair_count,
            "model_eligibility_would_be_reached_count": model_eligibility_would_be_reached_count,
            "risk_gate_observable_count": risk_observable_count,
            "EV_fields_required_event_count": model_eligibility_would_be_reached_count,
        },
        "fail_counts_by_gate": dict(fail_counts_by_gate),
        "fail_reasons": _top(fail_reasons),
        "active_profit_final_derisk_phase_split": active_profit_final_split,
        "lifecycle_phase_split": dict(lifecycle_split),
        "phase_gate_fail_counts": _top(phase_fail_counts, limit=12),
        "estimated_probability_model_called_uplift": estimated_uplift,
        "observed_probability_model_called_count": observed_probability_model_called_count,
        "model_ev_required_field_missing_counts": dict(model_required_missing),
        "required_missing_fields": sorted(model_required_missing),
        "dominant_blocker": {
            "gate": dominant_gate,
            "reason": dominant_reason,
        },
        "recommended_next_patch": _recommended_next_patch(
            executable_event_count=executable_event_count,
            model_eligibility_would_be_reached_count=model_eligibility_would_be_reached_count,
            fail_counts_by_gate=fail_counts_by_gate,
            missing_fields=model_required_missing,
        ),
        "paper_promotion_gates": [
            "Run the simulator across multiple fresh paper sessions before any runtime admission patch.",
            "Only promote to paper runtime design if simulated model eligibility is consistently non-zero.",
            "Prove risk gates remain observable before allowing an event-driven paper hot path.",
            "Keep live mode out of scope until paper-only event admission has replay evidence and targeted tests.",
        ],
    }


def _recommended_next_patch(
    *,
    executable_event_count: int,
    model_eligibility_would_be_reached_count: int,
    fail_counts_by_gate: Counter[str],
    missing_fields: Counter[str],
) -> str:
    if executable_event_count == 0:
        return "Collect fresh market_snapshot JSONL with YES/NO bid/ask fields before simulating admission."
    if model_eligibility_would_be_reached_count > 0 and missing_fields:
        top_missing = missing_fields.most_common(1)[0][0]
        return f"Add offline/reporting support for missing EV input group: {top_missing}."
    if model_eligibility_would_be_reached_count > 0:
        return "Design the smallest paper-only event admission probe; do not change gates or live behavior."
    if fail_counts_by_gate:
        top_gate = fail_counts_by_gate.most_common(1)[0][0]
        return f"Investigate simulated admission blocker {top_gate} before any runtime design."
    return "No actionable admission pattern found in this replay slice."


def write_event_driven_admission_simulation_report(report: dict[str, Any], report_dir: str | Path = DEFAULT_REPORT_DIR) -> Path:
    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"event_driven_admission_simulation_{report['date']}.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline event-driven executable-liquidity admission simulation.")
    parser.add_argument("--date", required=True, help="Replay date in YYYY-MM-DD format.")
    parser.add_argument("--since", help="Optional HH:MM UTC lower bound.")
    parser.add_argument("--until", help="Optional HH:MM UTC upper bound.")
    parser.add_argument("--run-id", help="Optional replay run_id filter.")
    parser.add_argument("--base-dir", default=str(DEFAULT_QUANT_DATA_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--max-book-age-ms", type=float, default=DEFAULT_MAX_BOOK_AGE_MS)
    parser.add_argument("--max-side-spread", type=float, default=DEFAULT_MAX_SIDE_SPREAD)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = build_event_driven_admission_simulation_report(
        date=args.date,
        base_dir=args.base_dir,
        since=args.since,
        until=args.until,
        run_id=args.run_id,
        max_book_age_ms=args.max_book_age_ms,
        max_side_spread=args.max_side_spread,
    )
    if args.write_report:
        path = write_event_driven_admission_simulation_report(report, report_dir=args.report_dir)
        print(path)
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
