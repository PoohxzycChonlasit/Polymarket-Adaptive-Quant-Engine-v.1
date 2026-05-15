from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any

try:
    from polymarket.probability_model import ProbabilityModelInput, estimate_probability

    REAL_MODEL_IMPORT_ERROR = ""
except Exception as exc:  # pragma: no cover - defensive offline audit path
    ProbabilityModelInput = None  # type: ignore[assignment]
    estimate_probability = None  # type: ignore[assignment]
    REAL_MODEL_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"

try:  # pragma: no cover - direct script execution path
    from tools.event_driven_admission_simulation import (
        ACTIVE_MODEL_PHASES,
        DEFAULT_MAX_BOOK_AGE_MS,
        DEFAULT_MAX_SIDE_SPREAD,
        DEFAULT_QUANT_DATA_DIR,
        DEFAULT_REPORT_DIR,
        _field_group_available,
        _float_or_none,
        _freshness_ok,
        _is_executable_book_event,
        _lifecycle_phase,
        _payload,
        _positive_float,
        _producer,
        _rate,
        _source_event_allowed,
        _spread_ok,
        _token_pair_lineage_ok,
        build_time_filter,
        load_replay_events,
    )
except ModuleNotFoundError:  # pragma: no cover - `python tools/...` path
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from tools.event_driven_admission_simulation import (
        ACTIVE_MODEL_PHASES,
        DEFAULT_MAX_BOOK_AGE_MS,
        DEFAULT_MAX_SIDE_SPREAD,
        DEFAULT_QUANT_DATA_DIR,
        DEFAULT_REPORT_DIR,
        _field_group_available,
        _float_or_none,
        _freshness_ok,
        _is_executable_book_event,
        _lifecycle_phase,
        _payload,
        _positive_float,
        _producer,
        _rate,
        _source_event_allowed,
        _spread_ok,
        _token_pair_lineage_ok,
        build_time_filter,
        load_replay_events,
    )


PROBABILITY_METHOD = {
    "name": "offline_placeholder_logistic_price_to_beat_v1",
    "scope": "research_only_not_runtime_model",
    "reason": "Runtime probability model is not imported; this avoids side effects and prevents hidden strategy changes.",
    "assumption": "YES is treated as the above/up outcome and NO as its complement.",
}
REAL_MODEL_METHOD = {
    "name": "real_model_offline_adapter_v1",
    "scope": "offline_replay_adapter_only",
    "reason": "Uses polymarket.probability_model.estimate_probability with packet fields only; no trader, network, websocket, or runtime state.",
    "safe_to_import_offline": REAL_MODEL_IMPORT_ERROR == "",
    "import_error": REAL_MODEL_IMPORT_ERROR,
}
PROBABILITY_METHODS = {
    "placeholder": PROBABILITY_METHOD,
    "real_model": REAL_MODEL_METHOD,
    "compare": {
        "name": "placeholder_vs_real_model_comparison_v1",
        "scope": "offline_replay_comparison_only",
        "reason": "Computes placeholder and real-model EV side by side without changing runtime behavior.",
        "safe_to_import_offline": REAL_MODEL_IMPORT_ERROR == "",
        "import_error": REAL_MODEL_IMPORT_ERROR,
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _value(payload: dict[str, Any], aliases: tuple[str, ...]) -> float | None:
    for key in aliases:
        value = _float_or_none(payload.get(key))
        if value is not None:
            return value
    return None


def _yes_no_top_of_book(payload: dict[str, Any]) -> dict[str, float] | None:
    yes_bid = _positive_float(payload.get("yes_bid") or payload.get("yes_best_bid"))
    yes_ask = _positive_float(payload.get("yes_ask") or payload.get("yes_best_ask"))
    no_bid = _positive_float(payload.get("no_bid") or payload.get("no_best_bid"))
    no_ask = _positive_float(payload.get("no_ask") or payload.get("no_best_ask"))
    if None in {yes_bid, yes_ask, no_bid, no_ask}:
        return None
    return {
        "yes_bid": float(yes_bid),
        "yes_ask": float(yes_ask),
        "no_bid": float(no_bid),
        "no_ask": float(no_ask),
    }


def _liquidity_pass(payload: dict[str, Any]) -> bool:
    for key in ("liquidity_state", "depth_ready", "liquidity_ready"):
        raw = payload.get(key)
        if isinstance(raw, bool):
            return raw
        if raw is not None:
            state = str(raw).strip().lower()
            if state in {"ready", "ok", "pass", "true", "sufficient", "liquid"}:
                return True
            if state in {"blocked", "not_ready", "false", "insufficient", "thin", "empty"}:
                return False
    liquidity = _float_or_none(payload.get("liquidity") or payload.get("liquidity_usd"))
    if liquidity is not None:
        return liquidity > 0
    return _field_group_available(payload, "liquidity")


def _placeholder_probability_yes(underlying_price: float, target_price: float, seconds_remaining: float) -> float:
    if target_price <= 0 or underlying_price <= 0:
        return 0.5
    seconds = max(1.0, min(300.0, seconds_remaining))
    distance_pct = (underlying_price - target_price) / target_price
    time_scale = max(0.0005, 0.0025 * math.sqrt(seconds / 300.0))
    z_score = max(-8.0, min(8.0, distance_pct / time_scale))
    probability = 1.0 / (1.0 + math.exp(-z_score))
    return round(max(0.01, min(0.99, probability)), 6)


def _max_spread(payload: dict[str, Any], book: dict[str, float]) -> float:
    spreads = [
        max(0.0, book["yes_ask"] - book["yes_bid"]),
        max(0.0, book["no_ask"] - book["no_bid"]),
    ]
    explicit_spread = _float_or_none(payload.get("spread") or payload.get("spread_normalized"))
    if explicit_spread is not None:
        spreads.append(abs(explicit_spread))
    return max(spreads)


def _liquidity_value(payload: dict[str, Any]) -> float:
    liquidity = _float_or_none(payload.get("liquidity") or payload.get("liquidity_usd"))
    if liquidity is not None:
        return max(0.0, liquidity)
    return 1_000.0 if _liquidity_pass(payload) else 0.0


def _book_age_seconds(payload: dict[str, Any]) -> float:
    age_ms = _float_or_none(
        payload.get("orderbook_age_ms")
        or payload.get("book_event_age_ms")
        or payload.get("yes_orderbook_age_ms")
        or payload.get("no_orderbook_age_ms")
    )
    if age_ms is None:
        return 0.0
    return max(0.0, age_ms / 1000.0)


def _real_model_probability_yes(
    payload: dict[str, Any],
    *,
    book: dict[str, float],
    underlying_price: float,
    target_price: float,
    seconds_remaining: float,
) -> tuple[float | None, dict[str, Any] | None, str]:
    if ProbabilityModelInput is None or estimate_probability is None:
        return None, None, REAL_MODEL_IMPORT_ERROR or "real_model_unavailable"
    try:
        implied = (book["yes_ask"] + (1.0 - book["no_ask"])) / 2.0
        model_input = ProbabilityModelInput(
            underlying_price=underlying_price,
            target_price=target_price,
            distance_to_target=underlying_price - target_price,
            time_remaining_seconds=int(max(0.0, seconds_remaining)),
            orderbook_bid=book["yes_bid"],
            orderbook_ask=book["yes_ask"],
            spread=_max_spread(payload, book),
            liquidity=_liquidity_value(payload),
            yes_ask=book["yes_ask"],
            no_ask=book["no_ask"],
            market_implied_probability=implied,
            data_age_seconds=_book_age_seconds(payload),
        )
        result = estimate_probability(model_input)
    except Exception as exc:  # pragma: no cover - defensive offline audit path
        return None, None, f"{type(exc).__name__}: {exc}"
    return (
        round(float(result.p_yes), 6),
        {
            "confidence_score": round(float(result.confidence_score), 6),
            "model_reason": result.model_reason,
            "skipped": bool(result.skipped),
            "skip_reason": result.skip_reason,
        },
        "",
    )


def _eligible_for_model_probe(payload: dict[str, Any], *, max_book_age_ms: float, max_side_spread: float) -> tuple[bool, str]:
    if not _is_executable_book_event(payload):
        return False, "not_executable_book_event"
    if not _token_pair_lineage_ok(payload):
        return False, "token_pair_lineage_ok"
    phase = _lifecycle_phase(payload)
    if phase not in ACTIVE_MODEL_PHASES:
        return False, "lifecycle_window_ok"
    freshness, freshness_reason = _freshness_ok(payload, max_book_age_ms)
    if not freshness:
        return False, freshness_reason
    spread, spread_reason = _spread_ok(payload, max_side_spread)
    if not spread:
        return False, spread_reason
    return True, "model_eligible"


def _missing_ev_inputs(payload: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if _value(
        payload,
        (
            "underlying_price",
            "current_price",
            "oracle_price",
            "index_price",
            "spot_price",
            "asset_price",
            "mark_price",
            "last_price",
            "binance_price",
            "reference_price",
        ),
    ) is None:
        missing.append("underlying_price")
    if _value(
        payload,
        (
            "target_price",
            "price_to_beat",
            "ptb_price",
            "strike",
            "strike_price",
            "event_boundary_price",
            "boundary_price",
            "price_target",
            "market_strike",
        ),
    ) is None:
        missing.append("target_price")
    if _value(payload, ("seconds_remaining", "seconds_until_close", "time_remaining")) is None:
        missing.append("seconds_remaining")
    if _yes_no_top_of_book(payload) is None:
        missing.append("yes_no_bid_ask")
    if not _field_group_available(payload, "spread"):
        missing.append("spread")
    if not _field_group_available(payload, "liquidity"):
        missing.append("liquidity")
    return missing


def _simulate_packet_ev(payload: dict[str, Any], *, probability_method: str = "placeholder") -> dict[str, Any] | None:
    missing = _missing_ev_inputs(payload)
    if missing:
        return None
    book = _yes_no_top_of_book(payload)
    if book is None:
        return None
    underlying_price = _value(
        payload,
        (
            "underlying_price",
            "current_price",
            "oracle_price",
            "index_price",
            "spot_price",
            "asset_price",
            "mark_price",
            "last_price",
            "binance_price",
            "reference_price",
        ),
    )
    target_price = _value(
        payload,
        (
            "target_price",
            "price_to_beat",
            "ptb_price",
            "strike",
            "strike_price",
            "event_boundary_price",
            "boundary_price",
            "price_target",
            "market_strike",
        ),
    )
    seconds_remaining = _value(payload, ("seconds_remaining", "seconds_until_close", "time_remaining"))
    if underlying_price is None or target_price is None or seconds_remaining is None:
        return None

    model_metadata: dict[str, Any] = {}
    model_error = ""
    if probability_method == "real_model":
        probability_yes, model_metadata, model_error = _real_model_probability_yes(
            payload,
            book=book,
            underlying_price=underlying_price,
            target_price=target_price,
            seconds_remaining=seconds_remaining,
        )
        if probability_yes is None:
            return {
                "lifecycle_phase": _lifecycle_phase(payload),
                "model_error": model_error or "real_model_probability_unavailable",
                "probability_method": "real_model",
            }
    else:
        probability_yes = _placeholder_probability_yes(underlying_price, target_price, seconds_remaining)
    probability_no = round(1.0 - probability_yes, 6)
    yes_mid = (book["yes_bid"] + book["yes_ask"]) / 2.0
    no_mid = (book["no_bid"] + book["no_ask"]) / 2.0
    fair_value_yes = probability_yes
    fair_value_no = probability_no
    raw_ev_yes = fair_value_yes - yes_mid
    raw_ev_no = fair_value_no - no_mid
    ev_after_spread_yes = fair_value_yes - book["yes_ask"]
    ev_after_spread_no = fair_value_no - book["no_ask"]
    best_side = "YES" if ev_after_spread_yes >= ev_after_spread_no else "NO"
    best_ev_after_spread = ev_after_spread_yes if best_side == "YES" else ev_after_spread_no
    best_raw_ev = max(raw_ev_yes, raw_ev_no)
    return {
        "lifecycle_phase": _lifecycle_phase(payload),
        "probability_yes": probability_yes,
        "probability_no": probability_no,
        "probability_method": probability_method,
        "fair_value_yes": round(fair_value_yes, 6),
        "fair_value_no": round(fair_value_no, 6),
        "market_price_yes": book["yes_ask"],
        "market_price_no": book["no_ask"],
        "ev_yes": round(raw_ev_yes, 6),
        "ev_no": round(raw_ev_no, 6),
        "ev_after_spread_yes": round(ev_after_spread_yes, 6),
        "ev_after_spread_no": round(ev_after_spread_no, 6),
        "ev_after_spread": round(best_ev_after_spread, 6),
        "best_side": best_side,
        "positive_ev": best_ev_after_spread > 0,
        "spread_killed": best_raw_ev > 0 and best_ev_after_spread <= 0,
        "liquidity_pass": _liquidity_pass(payload),
        "model_metadata": model_metadata or {},
        "model_error": model_error,
    }


def _phase_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_phase: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_phase[record["lifecycle_phase"]].append(record)
    summary: dict[str, Any] = {}
    for phase, phase_records in sorted(by_phase.items()):
        evs = [float(record["ev_after_spread"]) for record in phase_records]
        positives = sum(1 for record in phase_records if record["positive_ev"])
        spread_killed = sum(1 for record in phase_records if record["spread_killed"])
        liquidity_pass = sum(1 for record in phase_records if record["liquidity_pass"])
        summary[phase] = {
            "count": len(phase_records),
            "positive_ev_count": positives,
            "positive_ev_rate": _rate(positives, len(phase_records)),
            "average_ev_after_spread": round(mean(evs), 6) if evs else None,
            "median_ev_after_spread": round(median(evs), 6) if evs else None,
            "spread_killed_count": spread_killed,
            "liquidity_eligible_count": liquidity_pass,
        }
    return summary


def _ev_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    usable_records = [record for record in records if not record.get("model_error")]
    ev_values = [float(record["ev_after_spread"]) for record in usable_records]
    positive_ev_count = sum(1 for record in usable_records if record["positive_ev"])
    spread_killed_count = sum(1 for record in usable_records if record["spread_killed"])
    liquidity_eligible_count = sum(1 for record in usable_records if record["liquidity_pass"])
    return {
        "packet_count": len(usable_records),
        "probability_available_count": len(usable_records),
        "positive_ev_count": positive_ev_count,
        "positive_ev_rate": _rate(positive_ev_count, len(usable_records)),
        "average_ev_after_spread": round(mean(ev_values), 6) if ev_values else None,
        "median_ev_after_spread": round(median(ev_values), 6) if ev_values else None,
        "spread_killed_count": spread_killed_count,
        "spread_kill_rate": _rate(spread_killed_count, len(usable_records)),
        "liquidity_eligible_count": liquidity_eligible_count,
        "liquidity_pass_rate": _rate(liquidity_eligible_count, len(usable_records)),
        "ev_distribution_by_lifecycle_phase": _phase_summary(usable_records),
    }


def _model_error_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        error = str(record.get("model_error") or "").strip()
        if error:
            counts[error] += 1
    return dict(counts)


def _comparison_summary(
    *,
    placeholder_records: list[dict[str, Any]],
    real_records: list[dict[str, Any]],
    excluded_real_model_input_missing: int,
) -> dict[str, Any]:
    placeholder = _ev_summary(placeholder_records)
    real = _ev_summary(real_records)
    return {
        "placeholder_packet_count": placeholder["packet_count"],
        "real_model_packet_count": len(real_records),
        "real_model_probability_available_count": real["probability_available_count"],
        "positive_ev_count_placeholder": placeholder["positive_ev_count"],
        "positive_ev_rate_placeholder": placeholder["positive_ev_rate"],
        "average_ev_after_spread_placeholder": placeholder["average_ev_after_spread"],
        "median_ev_after_spread_placeholder": placeholder["median_ev_after_spread"],
        "positive_ev_count_real_model": real["positive_ev_count"],
        "positive_ev_rate_real_model": real["positive_ev_rate"],
        "average_ev_after_spread_real_model": real["average_ev_after_spread"],
        "median_ev_after_spread_real_model": real["median_ev_after_spread"],
        "excluded_real_model_input_missing": excluded_real_model_input_missing,
        "model_error_counts": _model_error_counts(real_records),
    }


def _recommended_next_patch(
    *,
    full_input_count: int,
    positive_ev_count: int,
    missing_counts: Counter[str],
    probability_method: str,
) -> str:
    if full_input_count == 0:
        if missing_counts:
            return f"Improve offline packet coverage for {missing_counts.most_common(1)[0][0]} before EV simulation."
        return "Collect executable-liquidity packets with full EV inputs before interpreting opportunity quality."
    if probability_method in {"real_model", "compare"} and positive_ev_count > 0:
        return "Run cross-session real-model EV replay before any paper hot-path design; keep runtime trading unchanged."
    if positive_ev_count > 0:
        return "Validate placeholder-positive EV packets against the real probability model offline before any paper hot-path design."
    return "Audit whether spread/liquidity or placeholder probability assumptions eliminate all simulated edge."


def _run_id_from_event(event: dict[str, Any]) -> str:
    raw = str(event.get("run_id") or "").strip()
    if raw:
        return raw
    payload = _payload(event)
    raw = str(payload.get("run_id") or "").strip()
    return raw or "missing_run_id"


def _window_summary(report: dict[str, Any], *, window_id: str) -> dict[str, Any]:
    return {
        "window_id": window_id,
        "run_id": report["time_filter"].get("run_id"),
        "since": report["time_filter"].get("since"),
        "until": report["time_filter"].get("until"),
        "packets_loaded": report["packets_loaded"],
        "executable_liquidity_event_count": report["executable_liquidity_event_count"],
        "model_eligibility_would_be_reached_count": report["model_eligibility_would_be_reached_count"],
        "full_ev_input_packets": report["packets_with_full_ev_inputs"],
        "positive_ev_count_real_model": report["positive_ev_count_real_model"],
        "positive_ev_rate_real_model": report["positive_ev_rate_real_model"],
        "median_ev_after_spread_real_model": report["median_ev_after_spread_real_model"],
        "average_ev_after_spread_real_model": report["average_ev_after_spread_real_model"],
        "spread_kill_rate": report["spread_kill_rate"],
        "lifecycle_ev_split": report["ev_distribution_by_lifecycle_phase"],
        "missing_price_input_exclusions": report["excluded_missing_price"],
        "missing_field_exclusions": report["missing_field_exclusions"],
        "model_error_counts": report["model_error_counts"],
    }


def _weighted_average(items: list[dict[str, Any]], value_key: str, weight_key: str) -> float | None:
    weighted_sum = 0.0
    total_weight = 0
    for item in items:
        value = _float_or_none(item.get(value_key))
        weight = int(item.get(weight_key) or 0)
        if value is None or weight <= 0:
            continue
        weighted_sum += value * weight
        total_weight += weight
    if total_weight <= 0:
        return None
    return round(weighted_sum / total_weight, 6)


def _median_of_window_medians(items: list[dict[str, Any]], key: str) -> float | None:
    values = [_float_or_none(item.get(key)) for item in items]
    present = [value for value in values if value is not None]
    if not present:
        return None
    return round(median(present), 6)


def _classify_cross_session_stability(windows: list[dict[str, Any]]) -> str:
    eligible = [window for window in windows if int(window.get("full_ev_input_packets") or 0) > 0]
    if len(eligible) < 2:
        return "INSUFFICIENT_COVERAGE"
    rates = [_float_or_none(window.get("positive_ev_rate_real_model")) for window in eligible]
    medians = [_float_or_none(window.get("median_ev_after_spread_real_model")) for window in eligible]
    usable_rates = [rate for rate in rates if rate is not None]
    usable_medians = [value for value in medians if value is not None]
    if len(usable_rates) != len(eligible) or len(usable_medians) != len(eligible):
        return "INSUFFICIENT_COVERAGE"
    if all(rate >= 0.70 for rate in usable_rates) and all(value > 0 for value in usable_medians):
        return "ROBUST_POSITIVE_EV_REPLAY"
    if any(rate >= 0.70 and value > 0 for rate, value in zip(usable_rates, usable_medians)):
        return "SESSION_SPECIFIC_EV_REPLAY"
    return "UNSTABLE_OR_NEGATIVE_EV_REPLAY"


def build_event_driven_fair_value_cross_session_report(
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
    run_ids = sorted({_run_id_from_event(event) for event in events})
    events_by_run_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        events_by_run_id[_run_id_from_event(event)].append(event)
    windows: list[dict[str, Any]] = []
    for item_run_id in run_ids:
        if item_run_id == "missing_run_id" and len(run_ids) > 1:
            continue
        effective_run_id = None if item_run_id == "missing_run_id" else item_run_id
        if run_id and effective_run_id != run_id:
            continue
        window_report = build_event_driven_fair_value_simulation_report(
            date=date,
            base_dir=base_dir,
            since=since,
            until=until,
            run_id=effective_run_id,
            max_book_age_ms=max_book_age_ms,
            max_side_spread=max_side_spread,
            probability_method="compare",
            events_override=events_by_run_id[item_run_id],
            bad_json_lines_override=0,
        )
        windows.append(_window_summary(window_report, window_id=item_run_id))

    total_full = sum(int(window.get("full_ev_input_packets") or 0) for window in windows)
    total_positive = sum(int(window.get("positive_ev_count_real_model") or 0) for window in windows)
    total_missing_price = sum(int(window.get("missing_price_input_exclusions") or 0) for window in windows)
    total_loaded = sum(int(window.get("packets_loaded") or 0) for window in windows)
    total_executable = sum(int(window.get("executable_liquidity_event_count") or 0) for window in windows)
    total_model_eligible = sum(int(window.get("model_eligibility_would_be_reached_count") or 0) for window in windows)
    windows_with_full_inputs = sum(1 for window in windows if int(window.get("full_ev_input_packets") or 0) > 0)
    return {
        "schema_version": "event_driven_fair_value_cross_session_v1",
        "scope": "offline_cross_session_replay_only",
        "generated_at_utc": _utc_now(),
        "date": date,
        "time_filter": {"since": since, "until": until, "run_id": run_id},
        "guardrails": {
            "offline_only": True,
            "runtime_behavior_changed": False,
            "strategy_changed": False,
            "risk_changed": False,
            "execution_changed": False,
            "order_intent_changed": False,
            "scheduling_changed": False,
            "live_behavior_changed": False,
            "simulation_wired_to_trading": False,
            "probability_model_logic_changed": False,
        },
        "source_events_loaded": len(events),
        "bad_json_lines": bad_json_lines,
        "runs_windows_analyzed": len(windows),
        "windows_with_full_ev_inputs": windows_with_full_inputs,
        "run_ids_analyzed": [window["window_id"] for window in windows],
        "packets_loaded_total": total_loaded,
        "executable_liquidity_event_count_total": total_executable,
        "model_eligibility_would_be_reached_count_total": total_model_eligible,
        "full_ev_input_packets_total": total_full,
        "positive_ev_count_real_model_total": total_positive,
        "positive_ev_rate_real_model_total": _rate(total_positive, total_full),
        "median_ev_after_spread_real_model_by_window_median": _median_of_window_medians(
            windows,
            "median_ev_after_spread_real_model",
        ),
        "average_ev_after_spread_real_model_weighted": _weighted_average(
            windows,
            "average_ev_after_spread_real_model",
            "full_ev_input_packets",
        ),
        "spread_kill_rate_weighted": _weighted_average(windows, "spread_kill_rate", "full_ev_input_packets"),
        "missing_price_input_exclusions_total": total_missing_price,
        "windows": windows,
        "stability_classification": _classify_cross_session_stability(windows),
        "recommended_next_patch": (
            "Design a paper-only event-driven admission probe only after confirming cross-session stability and keeping all gates downstream."
            if _classify_cross_session_stability(windows) == "ROBUST_POSITIVE_EV_REPLAY"
            else "Collect more fresh real-model EV replay windows before any paper hot-path design."
        ),
    }


def build_event_driven_fair_value_simulation_report(
    *,
    date: str,
    base_dir: str | Path = DEFAULT_QUANT_DATA_DIR,
    since: str | None = None,
    until: str | None = None,
    run_id: str | None = None,
    max_book_age_ms: float = DEFAULT_MAX_BOOK_AGE_MS,
    max_side_spread: float = DEFAULT_MAX_SIDE_SPREAD,
    probability_method: str = "placeholder",
    events_override: list[dict[str, Any]] | None = None,
    bad_json_lines_override: int = 0,
) -> dict[str, Any]:
    if probability_method not in PROBABILITY_METHODS:
        raise ValueError(f"Unsupported probability_method: {probability_method}")
    if events_override is None:
        time_filter = build_time_filter(date_from=date, date_to=date, since=since, until=until, run_id=run_id)
        events, bad_json_lines = load_replay_events(
            base_dir=base_dir,
            date_from=date,
            date_to=date,
            since_utc=time_filter.get("since_utc"),
            until_utc=time_filter.get("until_utc"),
            run_id=run_id,
        )
    else:
        events = events_override
        bad_json_lines = bad_json_lines_override
    source_event_counts = Counter(_producer(event) for event in events)
    executable_count = 0
    model_eligible_count = 0
    missing_counts: Counter[str] = Counter()
    gate_exclusions: Counter[str] = Counter()
    placeholder_records: list[dict[str, Any]] = []
    real_model_records: list[dict[str, Any]] = []
    excluded_missing_price_packets = 0

    for event in events:
        payload = _payload(event)
        if not _source_event_allowed(event, payload):
            continue
        if not _is_executable_book_event(payload):
            continue
        executable_count += 1
        eligible, reason = _eligible_for_model_probe(
            payload,
            max_book_age_ms=max_book_age_ms,
            max_side_spread=max_side_spread,
        )
        if not eligible:
            gate_exclusions[reason] += 1
            continue
        model_eligible_count += 1
        missing = _missing_ev_inputs(payload)
        if missing:
            missing_counts.update(missing)
            if "underlying_price" in missing or "target_price" in missing:
                excluded_missing_price_packets += 1
            continue
        placeholder_record = _simulate_packet_ev(payload, probability_method="placeholder")
        if placeholder_record is None:
            missing_counts["simulation_input_unusable"] += 1
            continue
        placeholder_records.append(placeholder_record)
        if probability_method in {"real_model", "compare"}:
            real_record = _simulate_packet_ev(payload, probability_method="real_model")
            if real_record is not None:
                real_model_records.append(real_record)

    primary_records = real_model_records if probability_method == "real_model" else placeholder_records
    primary_summary = _ev_summary(primary_records)
    probability_comparison = _comparison_summary(
        placeholder_records=placeholder_records,
        real_records=real_model_records,
        excluded_real_model_input_missing=excluded_missing_price_packets,
    )
    return {
        "schema_version": "event_driven_fair_value_simulation_v1",
        "scope": "offline_research_simulation_only",
        "generated_at_utc": _utc_now(),
        "date": date,
        "time_filter": {"since": since, "until": until, "run_id": run_id},
        "guardrails": {
            "offline_only": True,
            "runtime_behavior_changed": False,
            "strategy_changed": False,
            "risk_changed": False,
            "execution_changed": False,
            "order_intent_changed": False,
            "scheduling_changed": False,
            "live_behavior_changed": False,
            "simulation_wired_to_trading": False,
        },
        "packets_loaded": len(events),
        "bad_json_lines": bad_json_lines,
        "source_event_counts_by_producer": dict(source_event_counts),
        "executable_liquidity_event_count": executable_count,
        "model_eligibility_would_be_reached_count": model_eligible_count,
        "packets_with_full_ev_inputs": len(placeholder_records),
        "excluded_missing_price": excluded_missing_price_packets,
        "missing_field_exclusions": dict(missing_counts),
        "gate_exclusions": dict(gate_exclusions),
        "probability_method": PROBABILITY_METHODS[probability_method],
        "probability_method_requested": probability_method,
        "probability_model_audit": {
            "real_model_safe_to_import_offline": REAL_MODEL_IMPORT_ERROR == "",
            "real_model_import_error": REAL_MODEL_IMPORT_ERROR,
            "requires_runtime_state": False,
            "requires_network": False,
            "requires_trader_instance": False,
            "mutates_global_runtime_state": False,
            "input_mapping": {
                "underlying_price": "packet underlying_price/current_price aliases -> ProbabilityModelInput.underlying_price",
                "target_price": "packet target_price/price_to_beat aliases -> ProbabilityModelInput.target_price",
                "seconds_remaining": "packet seconds_remaining/time_remaining aliases -> ProbabilityModelInput.time_remaining_seconds",
                "yes_bid/yes_ask": "YES top-of-book -> orderbook_bid/orderbook_ask and yes_ask",
                "no_ask": "NO ask -> no_ask and market implied probability complement",
                "spread": "max derived YES/NO bid-ask spread -> ProbabilityModelInput.spread",
                "liquidity": "numeric liquidity if present, otherwise ready state -> conservative numeric proxy",
                "orderbook_age_ms": "packet orderbook age -> ProbabilityModelInput.data_age_seconds",
            },
            "model_output": "ProbabilityModelResult.p_yes and p_no",
        },
        "positive_ev_count": primary_summary["positive_ev_count"],
        "positive_ev_rate": primary_summary["positive_ev_rate"],
        "average_ev_after_spread": primary_summary["average_ev_after_spread"],
        "median_ev_after_spread": primary_summary["median_ev_after_spread"],
        "ev_distribution_by_lifecycle_phase": primary_summary["ev_distribution_by_lifecycle_phase"],
        "spread_killed_count": primary_summary["spread_killed_count"],
        "spread_kill_rate": primary_summary["spread_kill_rate"],
        "liquidity_eligible_count": primary_summary["liquidity_eligible_count"],
        "liquidity_pass_rate": primary_summary["liquidity_pass_rate"],
        "probability_comparison": probability_comparison,
        "real_model_probability_available_count": probability_comparison["real_model_probability_available_count"],
        "positive_ev_count_real_model": probability_comparison["positive_ev_count_real_model"],
        "positive_ev_rate_real_model": probability_comparison["positive_ev_rate_real_model"],
        "average_ev_after_spread_real_model": probability_comparison["average_ev_after_spread_real_model"],
        "median_ev_after_spread_real_model": probability_comparison["median_ev_after_spread_real_model"],
        "excluded_real_model_input_missing": probability_comparison["excluded_real_model_input_missing"],
        "model_error_counts": probability_comparison["model_error_counts"],
        "recommended_next_patch": _recommended_next_patch(
            full_input_count=primary_summary["packet_count"],
            positive_ev_count=primary_summary["positive_ev_count"],
            missing_counts=missing_counts,
            probability_method=probability_method,
        ),
        "paper_promotion_gates": [
            "Treat positive EV as placeholder evidence only until the real probability model is replayed offline.",
            "Require fresh-schema packet coverage before interpreting missing-price exclusions.",
            "Compare simulated EV after spread across multiple paper sessions before any paper hot-path design.",
            "Keep risk, OrderIntent, reconciliation, execution, and live behavior out of scope.",
        ],
    }


def write_event_driven_fair_value_simulation_report(
    report: dict[str, Any],
    report_dir: str | Path = DEFAULT_REPORT_DIR,
) -> Path:
    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"event_driven_fair_value_simulation_{report['date']}.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_event_driven_fair_value_cross_session_report(
    report: dict[str, Any],
    report_dir: str | Path = DEFAULT_REPORT_DIR,
) -> Path:
    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"event_driven_fair_value_cross_session_{report['date']}.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _summary_view(report: dict[str, Any]) -> dict[str, Any]:
    if report.get("schema_version") == "event_driven_fair_value_cross_session_v1":
        return {
            "schema_version": report["schema_version"],
            "date": report["date"],
            "runs_windows_analyzed": report["runs_windows_analyzed"],
            "windows_with_full_ev_inputs": report["windows_with_full_ev_inputs"],
            "full_ev_input_packets_total": report["full_ev_input_packets_total"],
            "positive_ev_count_real_model_total": report["positive_ev_count_real_model_total"],
            "positive_ev_rate_real_model_total": report["positive_ev_rate_real_model_total"],
            "median_ev_after_spread_real_model_by_window_median": report[
                "median_ev_after_spread_real_model_by_window_median"
            ],
            "missing_price_input_exclusions_total": report["missing_price_input_exclusions_total"],
            "stability_classification": report["stability_classification"],
            "recommended_next_patch": report["recommended_next_patch"],
        }
    return {
        "schema_version": report["schema_version"],
        "date": report["date"],
        "probability_method_requested": report["probability_method_requested"],
        "packets_with_full_ev_inputs": report["packets_with_full_ev_inputs"],
        "positive_ev_count_real_model": report["positive_ev_count_real_model"],
        "positive_ev_rate_real_model": report["positive_ev_rate_real_model"],
        "median_ev_after_spread_real_model": report["median_ev_after_spread_real_model"],
        "excluded_real_model_input_missing": report["excluded_real_model_input_missing"],
        "recommended_next_patch": report["recommended_next_patch"],
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline event-driven fair-value / EV simulation.")
    parser.add_argument("--date", required=True, help="Replay date in YYYY-MM-DD format.")
    parser.add_argument("--since", help="Optional HH:MM UTC lower bound.")
    parser.add_argument("--until", help="Optional HH:MM UTC upper bound.")
    parser.add_argument("--run-id", help="Optional replay run_id filter.")
    parser.add_argument("--base-dir", default=str(DEFAULT_QUANT_DATA_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--summary", action="store_true", help="Print compact operator-oriented JSON output.")
    parser.add_argument("--cross-session", action="store_true", help="Aggregate real-model EV replay by run/window.")
    parser.add_argument("--max-book-age-ms", type=float, default=DEFAULT_MAX_BOOK_AGE_MS)
    parser.add_argument("--max-side-spread", type=float, default=DEFAULT_MAX_SIDE_SPREAD)
    parser.add_argument(
        "--probability-method",
        choices=sorted(PROBABILITY_METHODS),
        default="placeholder",
        help="Probability estimator for offline EV simulation.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.cross_session:
        report = build_event_driven_fair_value_cross_session_report(
            date=args.date,
            base_dir=args.base_dir,
            since=args.since,
            until=args.until,
            run_id=args.run_id,
            max_book_age_ms=args.max_book_age_ms,
            max_side_spread=args.max_side_spread,
        )
        if args.write_report:
            path = write_event_driven_fair_value_cross_session_report(report, report_dir=args.report_dir)
            print(path)
        else:
            print(json.dumps(_summary_view(report) if args.summary else report, indent=2, sort_keys=True))
        return 0

    report = build_event_driven_fair_value_simulation_report(
        date=args.date,
        base_dir=args.base_dir,
        since=args.since,
        until=args.until,
        run_id=args.run_id,
        max_book_age_ms=args.max_book_age_ms,
        max_side_spread=args.max_side_spread,
        probability_method=args.probability_method,
    )
    if args.write_report:
        path = write_event_driven_fair_value_simulation_report(report, report_dir=args.report_dir)
        print(path)
    else:
        print(json.dumps(_summary_view(report) if args.summary else report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
