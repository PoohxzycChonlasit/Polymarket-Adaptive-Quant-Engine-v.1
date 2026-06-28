from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from tools.unknown.candidate_continuity import (
    _parse_timestamp,
    build_candidate_continuity_report,
)
from tools.unknown.lifecycle_truth_tables import (
    _asset_from,
    _date_part,
    _first_value,
    _payload,
    _phase,
)
from tools.replay_analyzer import (
    DEFAULT_QUANT_DATA_DIR,
    DEFAULT_REPORT_DIR,
    build_phase2_coverage_from_events,
    build_time_filter,
    load_replay_events,
)


PATH_WINDOW_PAD_MS = 2_000
PRICE_FIELDS = (
    "market_price",
    "yes_price",
    "no_price",
    "yes_mid",
    "no_mid",
    "yes_best_bid",
    "yes_bid",
    "yes_best_ask",
    "yes_ask",
    "no_best_bid",
    "no_bid",
    "no_best_ask",
    "no_ask",
    "best_bid",
    "best_ask",
    "price",
)
EV_FIELDS = ("ev_after_spread", "expected_value", "model_ev", "ev", "edge")
FAIR_VALUE_FIELDS = ("fair_value", "true_probability")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _as_float_or_none(value: Any) -> float | None:
    if isinstance(value, bool) or value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(parsed) or math.isinf(parsed):
        return None
    return parsed


def _text(value: Any) -> str:
    return str(value or "").strip()


def _first_float(payload: dict[str, Any], *fields: str) -> tuple[float | None, str]:
    for field in fields:
        value = _as_float_or_none(_first_value(payload, field))
        if value is not None:
            return value, field
    return None, ""


def _event_identity_matches(chain: dict[str, Any], event: dict[str, Any], payload: dict[str, Any]) -> bool:
    candidate_id = _text(_first_value(payload, "candidate_id", "opportunity_id", "replay_candidate_id"))
    signal_id = _text(_first_value(payload, "signal_id"))
    if chain.get("candidate_id") and candidate_id == chain.get("candidate_id"):
        return True
    if chain.get("signal_id") and signal_id == chain.get("signal_id"):
        return True
    return False


def _event_market_matches(chain: dict[str, Any], event: dict[str, Any], payload: dict[str, Any]) -> bool:
    market_id = _text(_first_value(payload, "market_id", "condition_id", "market_slug"))
    chain_market = _text(chain.get("market_id"))
    if chain_market and market_id and chain_market == market_id:
        return True
    asset = _asset_from(event, payload)
    chain_asset = _text(chain.get("asset"))
    return bool(chain_asset and chain_asset != "UNKNOWN" and asset == chain_asset)


def _event_in_chain_window(chain: dict[str, Any], event: dict[str, Any]) -> bool:
    timestamp = _parse_timestamp(event.get("timestamp_utc"))
    first_seen = _parse_timestamp(chain.get("first_seen_at_utc"))
    last_seen = _parse_timestamp(chain.get("last_seen_at_utc"))
    if timestamp is None or first_seen is None or last_seen is None:
        return False
    pad = timedelta(milliseconds=PATH_WINDOW_PAD_MS)
    return first_seen - pad <= timestamp <= last_seen + pad


def _observable_path_event(chain: dict[str, Any], event: dict[str, Any]) -> dict[str, Any] | None:
    if not _event_in_chain_window(chain, event):
        return None
    payload = _payload(event)
    identity_match = _event_identity_matches(chain, event, payload)
    market_match = _event_market_matches(chain, event, payload)
    if not identity_match and not market_match:
        return None

    ev_value, ev_source = _first_float(payload, *EV_FIELDS)
    price_value, price_source = _first_float(payload, *PRICE_FIELDS)
    fair_value, fair_source = _first_float(payload, *FAIR_VALUE_FIELDS)
    edge_value = ev_value
    edge_source = ev_source
    if edge_value is None and fair_value is not None and price_value is not None:
        edge_value = fair_value - price_value
        edge_source = "fair_value_minus_price_proxy"
    if ev_value is None and edge_value is not None:
        ev_value = edge_value
        ev_source = edge_source

    if ev_value is None and price_value is None and fair_value is None:
        return None

    phase, phase_inference = _phase(payload)
    timestamp = _text(event.get("timestamp_utc") or _first_value(payload, "timestamp_utc"))
    return {
        "timestamp_utc": timestamp,
        "timestamp": _parse_timestamp(timestamp),
        "event_category": _text(event.get("_category")),
        "event_type": _text(event.get("event_type")),
        "match_inference": "direct_identity" if identity_match else "market_window_proxy",
        "lifecycle_phase": phase,
        "lifecycle_phase_inference": phase_inference,
        "ev_value": ev_value,
        "ev_source": ev_source,
        "edge_value": edge_value,
        "edge_source": edge_source,
        "price_value": price_value,
        "price_source": price_source,
        "fair_value": fair_value,
        "fair_value_source": fair_source,
        "yes_no_price_path": {
            "yes_bid": _first_value(payload, "yes_bid", "yes_best_bid"),
            "yes_ask": _first_value(payload, "yes_ask", "yes_best_ask"),
            "no_bid": _first_value(payload, "no_bid", "no_best_bid"),
            "no_ask": _first_value(payload, "no_ask", "no_best_ask"),
            "yes_price": _first_value(payload, "yes_price", "yes_mid"),
            "no_price": _first_value(payload, "no_price", "no_mid"),
        },
    }


def _compact_path_event(event: dict[str, Any], birth_ev: float | None) -> dict[str, Any]:
    ev_value = event.get("ev_value")
    ev_delta = ev_value - birth_ev if ev_value is not None and birth_ev is not None else None
    return {
        "timestamp_utc": event["timestamp_utc"],
        "event_category": event["event_category"],
        "event_type": event["event_type"],
        "match_inference": event["match_inference"],
        "lifecycle_phase": event["lifecycle_phase"],
        "ev_value": ev_value,
        "ev_delta_from_birth": round(ev_delta, 6) if ev_delta is not None else None,
        "edge_value": event.get("edge_value"),
        "price_value": event.get("price_value"),
        "fair_value": event.get("fair_value"),
        "yes_no_price_path": event.get("yes_no_price_path", {}),
    }


def _stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = sum(values) / len(values)
    return math.sqrt(sum((value - avg) ** 2 for value in values) / len(values))


def _path_confidence(path_events: list[dict[str, Any]], chain: dict[str, Any]) -> tuple[str, str]:
    if len(path_events) >= 3 and all(event["match_inference"] == "direct_identity" for event in path_events):
        return "HIGH_DIRECT", "direct_candidate_path_with_multiple_observations"
    if len(path_events) >= 2 and any(event["match_inference"] == "direct_identity" for event in path_events):
        return "MEDIUM_DIRECT", "mixed_direct_candidate_path"
    if len(path_events) >= 2:
        return "LOW_PROXY", "market_window_proxy_path"
    if path_events and chain.get("continuity_confidence") in {"HIGH_DIRECT", "MEDIUM_DIRECT"}:
        return "LOW_EVIDENCE", "single_path_observation"
    return "INSUFFICIENT", "missing_path_observations"


def _path_quality(path_events: list[dict[str, Any]], confidence: str) -> str:
    ev_count = sum(1 for event in path_events if event.get("ev_value") is not None)
    price_count = sum(1 for event in path_events if event.get("price_value") is not None)
    fair_count = sum(1 for event in path_events if event.get("fair_value") is not None)
    if confidence in {"HIGH_DIRECT", "MEDIUM_DIRECT"} and ev_count >= 2:
        return "OBSERVABLE_EV_PATH"
    if ev_count >= 2:
        return "PROXY_EV_PATH"
    if price_count >= 2 or fair_count >= 2:
        return "PRICE_ONLY_PROXY_PATH"
    if path_events:
        return "SPARSE_SINGLE_POINT_PATH"
    return "INSUFFICIENT_PATH_FIELDS"


def _terminal_path_state(chain: dict[str, Any], path_events: list[dict[str, Any]], birth_ev: float | None) -> str:
    if not path_events:
        return "NO_PATH_OBSERVED"
    last_ev = path_events[-1].get("ev_value")
    if birth_ev is None or last_ev is None:
        return "TERMINAL_EV_UNKNOWN"
    delta = last_ev - birth_ev
    if delta > 0:
        return "TERMINAL_EDGE_EXPANDED"
    if delta < 0:
        return "TERMINAL_EDGE_DECAYED"
    return "TERMINAL_EDGE_FLAT"


def _build_path_row(chain: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    path_events = [
        item
        for item in (_observable_path_event(chain, event) for event in events)
        if item is not None
    ]
    path_events.sort(key=lambda event: event["timestamp_utc"])
    ev_values = [event["ev_value"] for event in path_events if event.get("ev_value") is not None]
    birth_ev = ev_values[0] if ev_values else None
    peak_ev = max(ev_values) if ev_values else None
    worst_ev = min(ev_values) if ev_values else None
    peak_favorable = peak_ev - birth_ev if peak_ev is not None and birth_ev is not None else None
    peak_adverse = worst_ev - birth_ev if worst_ev is not None and birth_ev is not None else None
    confidence, confidence_reason = _path_confidence(path_events, chain)
    quality = _path_quality(path_events, confidence)
    compact_events = [_compact_path_event(event, birth_ev) for event in path_events[:16]]
    return {
        "continuity_chain_id": chain["continuity_chain_id"],
        "candidate_id": chain.get("candidate_id", ""),
        "signal_id": chain.get("signal_id", ""),
        "asset": chain.get("asset", ""),
        "market_id": chain.get("market_id", ""),
        "continuity_status": chain.get("continuity_status", ""),
        "continuity_confidence": chain.get("continuity_confidence", ""),
        "candidate_terminal_state": chain.get("candidate_terminal_state", ""),
        "candidate_survival_ms": chain.get("candidate_survival_ms", 0.0),
        "path_observation_count": len(path_events),
        "path_confidence": confidence,
        "path_confidence_reason": confidence_reason,
        "path_observability_quality": quality,
        "mfe_candidate_path": compact_events,
        "mae_candidate_path": compact_events,
        "birth_ev": birth_ev,
        "peak_favorable_move": round(peak_favorable, 6) if peak_favorable is not None else None,
        "peak_adverse_move": round(peak_adverse, 6) if peak_adverse is not None else None,
        "peak_ev_after_birth": peak_ev,
        "worst_ev_after_birth": worst_ev,
        "path_volatility": {
            "ev_range": round((peak_ev - worst_ev), 6) if peak_ev is not None and worst_ev is not None else None,
            "ev_stddev": round(_stddev(ev_values), 6) if ev_values else None,
            "observed_ev_points": len(ev_values),
        },
        "candidate_terminal_path_state": _terminal_path_state(chain, path_events, birth_ev),
        "pre_ev_vs_post_ev_path": {
            "chain_pre_ev_event_count": chain.get("pre_ev_event_count", 0),
            "chain_post_ev_event_count": chain.get("post_ev_event_count", 0),
            "observed_ev_points": len(ev_values),
            "classification": "post_ev_observable" if ev_values else "pre_ev_or_ev_unobservable",
        },
        "low_confidence_label": None if confidence in {"HIGH_DIRECT", "MEDIUM_DIRECT"} else "LOW_CONFIDENCE_PATH_CONTINUITY",
    }


def _summary(path_rows: list[dict[str, Any]]) -> dict[str, Any]:
    confidence_counts: Counter[str] = Counter()
    quality_counts: Counter[str] = Counter()
    terminal_counts: Counter[str] = Counter()
    expanded = 0
    decayed = 0
    flat = 0
    favorable_values: list[float] = []
    adverse_values: list[float] = []
    for row in path_rows:
        confidence_counts[row["path_confidence"]] += 1
        quality_counts[row["path_observability_quality"]] += 1
        terminal_counts[row["candidate_terminal_path_state"]] += 1
        fav = row.get("peak_favorable_move")
        adv = row.get("peak_adverse_move")
        if fav is not None:
            favorable_values.append(float(fav))
            if fav > 0:
                expanded += 1
            elif fav == 0:
                flat += 1
        if adv is not None:
            adverse_values.append(float(adv))
            if adv < 0:
                decayed += 1
    return {
        "candidate_paths": len(path_rows),
        "path_confidence_counts": dict(confidence_counts.most_common()),
        "path_observability_quality_counts": dict(quality_counts.most_common()),
        "candidate_terminal_path_state_counts": dict(terminal_counts.most_common()),
        "edge_expansion_chain_count": expanded,
        "edge_decay_chain_count": decayed,
        "flat_or_single_point_chain_count": flat,
        "avg_peak_favorable_move": round(sum(favorable_values) / len(favorable_values), 6) if favorable_values else 0.0,
        "avg_peak_adverse_move": round(sum(adverse_values) / len(adverse_values), 6) if adverse_values else 0.0,
    }


def build_candidate_path_observability_report(
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

    time_filter = build_time_filter(date_from=date_from, date_to=date_to, since=since, until=until, run_id=run_id)
    events, bad_json_lines = load_replay_events(
        base_dir=base_dir,
        date_from=date_from,
        date_to=date_to,
        since_utc=time_filter.get("since_utc"),
        until_utc=time_filter.get("until_utc"),
        run_id=run_id,
    )
    continuity_report = build_candidate_continuity_report(
        base_dir=base_dir,
        date_from=date_from,
        date_to=date_to,
        since=since,
        until=until,
        run_id=run_id,
    )
    chains = list(continuity_report.get("chains", []))
    path_rows = [_build_path_row(chain, events) for chain in chains]
    path_summary = _summary(path_rows)
    phase2_coverage = build_phase2_coverage_from_events(events)
    if not events:
        report_confidence = "INSUFFICIENT"
    elif path_summary["path_confidence_counts"].get("HIGH_DIRECT"):
        report_confidence = "HIGH_DIRECT"
    elif path_summary["path_confidence_counts"].get("MEDIUM_DIRECT"):
        report_confidence = "MEDIUM_DIRECT"
    elif path_rows:
        report_confidence = "LOW_PROXY"
    else:
        report_confidence = "LOW_EVIDENCE"

    return {
        "generated_at_utc": _utc_now(),
        "date_from": date_from,
        "date_to": date_to,
        "run_id": run_id or "",
        "time_filter": {
            "since": since,
            "until": until,
            "since_utc": time_filter.get("since_utc").isoformat().replace("+00:00", "Z") if time_filter.get("since_utc") else None,
            "until_utc": time_filter.get("until_utc").isoformat().replace("+00:00", "Z") if time_filter.get("until_utc") else None,
            "run_id": run_id,
            "run_id_applied": bool(run_id),
            "applied": bool(time_filter.get("applied")),
            "semantics": time_filter.get("semantics"),
        },
        "scope": "offline_research_replay_only",
        "schema_version": "candidate_path_observability_v1",
        "does_not_claim_profitability": True,
        "does_not_authorize_runtime_decisions": True,
        "does_not_infer_execution": True,
        "does_not_infer_inventory_truth": True,
        "events_loaded": len(events),
        "bad_json_lines": bad_json_lines,
        "continuity_chains_loaded": len(chains),
        "path_confidence": report_confidence,
        "phase2_coverage_status": phase2_coverage.get("status"),
        "coverage_gaps": list(phase2_coverage.get("coverage_gaps", [])),
        "summary": path_summary,
        "candidate_paths": path_rows[:100],
        "research_questions": {
            "candidate_favorable_excursion": {
                "answer": "observable" if path_summary["edge_expansion_chain_count"] else "not_observed_or_unavailable",
                "avg_peak_favorable_move": path_summary["avg_peak_favorable_move"],
                "uncertainty": "candidate path uses observed EV/edge fields when present; otherwise fair_value-price proxy",
            },
            "candidate_adverse_excursion": {
                "answer": "observable" if path_summary["edge_decay_chain_count"] else "not_observed_or_unavailable",
                "avg_peak_adverse_move": path_summary["avg_peak_adverse_move"],
                "uncertainty": "adverse path is not a fill or PnL claim",
            },
            "ev_expansion_decay_after_birth": {
                "expanded_chains": path_summary["edge_expansion_chain_count"],
                "decayed_chains": path_summary["edge_decay_chain_count"],
                "terminal_path_states": path_summary["candidate_terminal_path_state_counts"],
            },
            "continuity_path_confidence": {
                "path_confidence": report_confidence,
                "path_confidence_counts": path_summary["path_confidence_counts"],
                "path_observability_quality_counts": path_summary["path_observability_quality_counts"],
                "guardrail": "evidence only; no fake fills, inferred execution, or inventory truth",
            },
        },
    }


def write_candidate_path_observability_report(report: dict[str, Any], *, report_dir: str | Path = DEFAULT_REPORT_DIR) -> Path:
    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    date_part = _date_part(
        str(report.get("date_from")),
        str(report.get("date_to")),
        dict(report.get("time_filter", {})),
        str(report.get("run_id") or ""),
    )
    output_path = output_dir / f"candidate_path_observability_{date_part}.json"
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return output_path


def print_summary(report: dict[str, Any]) -> None:
    summary = report.get("summary", {})
    print("Candidate Path Observability")
    print(
        "range={start}..{end} run_id={run_id} events={events} chains={chains} paths={paths} confidence={confidence}".format(
            start=report.get("date_from"),
            end=report.get("date_to"),
            run_id=report.get("run_id") or "",
            events=report.get("events_loaded"),
            chains=report.get("continuity_chains_loaded"),
            paths=summary.get("candidate_paths", 0),
            confidence=report.get("path_confidence"),
        )
    )
    print(f"path_confidence_counts={summary.get('path_confidence_counts', {})}")
    print(f"path_quality_counts={summary.get('path_observability_quality_counts', {})}")
    print(f"terminal_path_states={summary.get('candidate_terminal_path_state_counts', {})}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build offline candidate MFE/MAE path observability from quant JSONL replay evidence.")
    parser.add_argument("--date", default=None, help="Single date in YYYY-MM-DD format.")
    parser.add_argument("--from", dest="date_from", default=None, help="Start date in YYYY-MM-DD format.")
    parser.add_argument("--to", dest="date_to", default=None, help="End date in YYYY-MM-DD format.")
    parser.add_argument("--since", default=None, help="UTC start time HH:MM for same-day filtering; inclusive.")
    parser.add_argument("--until", default=None, help="UTC end time HH:MM for same-day filtering; exclusive.")
    parser.add_argument("--run-id", default=None, help="Exact run_id to isolate; events without this run_id are excluded.")
    parser.add_argument("--base-dir", default=str(DEFAULT_QUANT_DATA_DIR), help="Quant data root directory.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Output report directory.")
    parser.add_argument("--no-write", action="store_true", help="Do not write candidate_path_observability JSON.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_candidate_path_observability_report(
        base_dir=args.base_dir,
        date=args.date,
        date_from=args.date_from,
        date_to=args.date_to,
        since=args.since,
        until=args.until,
        run_id=args.run_id,
    )
    print_summary(report)
    if not args.no_write:
        path = write_candidate_path_observability_report(report, report_dir=args.report_dir)
        print(f"wrote_report={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
