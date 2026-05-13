from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from tools.lifecycle_truth_tables import (
    _asset_from,
    _blocked_after_ev,
    _blocked_before_ev,
    _candidate_classification,
    _candidate_key,
    _date_part,
    _decision_state,
    _ev_available,
    _first_value,
    _null_reasons,
    _payload,
    _phase,
    _safe_filename_token,
    _skip_reason,
)
from tools.replay_analyzer import (
    DEFAULT_QUANT_DATA_DIR,
    DEFAULT_REPORT_DIR,
    build_phase2_coverage_from_events,
    build_time_filter,
    load_replay_events,
)


PHASE_ORDER = {
    "OPENING_SCAN": 0,
    "ACTIVE_INVENTORY_TRADING": 1,
    "PROFIT_MANAGEMENT": 2,
    "FINAL_DERISK": 3,
    "CLOSED_OR_UNSAFE": 4,
}
BREAK_GAP_MS = 65_000
WEAK_TERMINAL_REASONS = {"", "unknown", "not_blocked", "unavailable", "none"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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
    return parsed.astimezone(timezone.utc)


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
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def _text(value: Any) -> str:
    return str(value or "").strip()


def _continuity_identity(event: dict[str, Any], payload: dict[str, Any]) -> tuple[str, str, str, str]:
    candidate_id = _text(_first_value(payload, "candidate_id", "opportunity_id", "replay_candidate_id"))
    signal_id = _text(_first_value(payload, "signal_id"))
    helper_key, helper_inference = _candidate_key(event, payload)
    if candidate_id:
        return f"candidate::{candidate_id}", "direct_candidate_id", candidate_id, signal_id
    if signal_id:
        return f"signal::{signal_id}", "direct_signal_id", "", signal_id
    return f"proxy::{helper_key}", helper_inference, "", ""


def _event_record(event: dict[str, Any]) -> dict[str, Any]:
    payload = _payload(event)
    phase, phase_inference = _phase(payload)
    chain_key, identity_inference, candidate_id, signal_id = _continuity_identity(event, payload)
    before_ev, before_inference = _blocked_before_ev(payload)
    after_ev, after_inference = _blocked_after_ev(payload)
    classification = _candidate_classification(event)
    timestamp = _text(event.get("timestamp_utc") or _first_value(payload, "timestamp_utc"))
    readiness_state = _text(
        _first_value(
            payload,
            "market_readiness_state",
            "orderbook_state_classification",
            "liquidity_state",
            "orderbook_readiness_reason",
            "orderbook_unavailable_reason",
        )
    )
    block_stage = _text(_first_value(payload, "candidate_block_stage"))
    block_reason = _text(_first_value(payload, "candidate_block_reason", "normalized_skip_reason", "skip_reason"))
    expiry_reason = _text(_first_value(payload, "candidate_expiry_reason"))
    direct_survival = _first_value(payload, "candidate_survival_ms")
    return {
        "timestamp_utc": timestamp,
        "timestamp": _parse_timestamp(timestamp),
        "run_id": _text(event.get("run_id")),
        "event_category": _text(event.get("_category")),
        "event_type": _text(event.get("event_type")),
        "asset": _asset_from(event, payload),
        "market_id": _text(_first_value(payload, "market_id", "condition_id", "market_slug")),
        "continuity_chain_key": chain_key,
        "identity_inference": identity_inference,
        "candidate_id": candidate_id,
        "signal_id": signal_id,
        "lifecycle_phase": phase,
        "lifecycle_phase_inference": phase_inference,
        "decision_state": _decision_state(payload),
        "readiness_state": readiness_state,
        "readiness_transition_reason": _text(_first_value(payload, "readiness_transition_reason")),
        "block_stage": block_stage,
        "block_reason": block_reason,
        "skip_reason": _skip_reason(payload),
        "candidate_survival_ms": direct_survival,
        "candidate_expiry_reason": expiry_reason,
        "ev_available": _ev_available(payload),
        "ev_null_reasons": _null_reasons(payload),
        "probability_model_stage": _text(_first_value(payload, "probability_model_stage")),
        "ev_calculation_stage": _text(_first_value(payload, "ev_calculation_stage")),
        "pre_ev_blocked": before_ev,
        "pre_ev_block_inference": before_inference,
        "post_ev_blocked": after_ev,
        "post_ev_block_inference": after_inference,
        "classification_reason": classification["candidate_classification_reason"],
        "classification_confidence": classification["candidate_classification_confidence"],
        "terminal_flags": {
            "ev_candidate_ready": _first_value(payload, "ev_candidate_ready"),
            "model_output_ready": _first_value(payload, "model_output_ready"),
            "starter_candidate": _as_bool(_first_value(payload, "starter_candidate")),
            "reload_candidate": _as_bool(_first_value(payload, "reload_candidate")),
            "unload_candidate": _as_bool(_first_value(payload, "unload_candidate")),
            "final_derisk_candidate": _as_bool(_first_value(payload, "final_derisk_candidate")),
        },
    }


def _compact_event(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp_utc": record["timestamp_utc"],
        "event_category": record["event_category"],
        "event_type": record["event_type"],
        "lifecycle_phase": record["lifecycle_phase"],
        "decision_state": record["decision_state"],
        "readiness_state": record["readiness_state"],
        "block_stage": record["block_stage"],
        "block_reason": record["block_reason"],
        "candidate_expiry_reason": record["candidate_expiry_reason"],
        "ev_available": record["ev_available"],
    }


def _dedupe_sequence(values: list[str]) -> list[str]:
    sequence: list[str] = []
    for value in values:
        if not sequence or sequence[-1] != value:
            sequence.append(value)
    return sequence


def _phase_regression(sequence: list[str]) -> bool:
    known = [PHASE_ORDER[phase] for phase in sequence if phase in PHASE_ORDER]
    return any(current < previous for previous, current in zip(known, known[1:]))


def _skipped_phase_transition(sequence: list[str]) -> bool:
    known = [PHASE_ORDER[phase] for phase in sequence if phase in PHASE_ORDER]
    return any(current - previous > 1 for previous, current in zip(known, known[1:]))


def _max_event_gap_ms(records: list[dict[str, Any]]) -> float:
    timestamps = [record["timestamp"] for record in records if record.get("timestamp") is not None]
    if len(timestamps) < 2:
        return 0.0
    gaps = [
        max(0.0, (current - previous).total_seconds() * 1000.0)
        for previous, current in zip(timestamps, timestamps[1:])
    ]
    return max(gaps, default=0.0)


def _survival_ms(records: list[dict[str, Any]]) -> tuple[float, str]:
    direct_values = [
        _as_float(record.get("candidate_survival_ms"), default=float("nan"))
        for record in records
        if record.get("candidate_survival_ms") not in {None, ""}
    ]
    direct_values = [value for value in direct_values if value == value]
    if direct_values:
        return max(direct_values), "direct_observed"
    timestamps = [record["timestamp"] for record in records if record.get("timestamp") is not None]
    if len(timestamps) >= 2:
        return max(0.0, (timestamps[-1] - timestamps[0]).total_seconds() * 1000.0), "event_span_proxy"
    return 0.0, "coverage_gap"


def _terminal_from_records(records: list[dict[str, Any]]) -> tuple[str, str]:
    last = records[-1]
    expiry_reasons = [_text(record.get("candidate_expiry_reason")) for record in records]
    expiry_reasons = [reason for reason in expiry_reasons if reason.lower() not in WEAK_TERMINAL_REASONS]
    if expiry_reasons:
        return "EXPIRED", expiry_reasons[-1]
    post_ev = [record for record in records if record.get("post_ev_blocked")]
    if post_ev:
        return "BLOCKED_POST_EV", _text(post_ev[-1].get("block_reason")) or "post_ev_block"
    pre_ev = [record for record in records if record.get("pre_ev_blocked")]
    if pre_ev:
        return "BLOCKED_PRE_EV", _text(pre_ev[-1].get("block_reason")) or "pre_ev_block"
    if last["lifecycle_phase"] == "CLOSED_OR_UNSAFE":
        return "CLOSED_OR_UNSAFE", "closed_or_unsafe_phase"
    readiness_text = " ".join(_text(record.get("readiness_state")).lower() for record in records)
    if any(token in readiness_text for token in ("empty", "stale", "not_ready", "unavailable", "degraded")):
        return "READINESS_DEGRADED", "readiness_degraded_without_terminal_candidate_event"
    return "LAST_SEEN_ONLY", "last_seen_without_terminal_event"


def _continuity_status(
    *,
    terminal_state: str,
    identity_inference: str,
    event_count: int,
    phase_sequence: list[str],
    max_gap_ms: float,
) -> tuple[str, str]:
    if event_count == 0:
        return "NO_EVIDENCE", "no_candidate_events"
    if identity_inference.startswith("proxy") or identity_inference == "coverage_gap":
        return "ORPHAN_OR_PROXY", "proxy_identity_cannot_prove_continuity"
    if _phase_regression(phase_sequence):
        return "CONTINUITY_BREAK", "lifecycle_phase_regression"
    if max_gap_ms > BREAK_GAP_MS:
        return "CONTINUITY_BREAK", "event_gap_exceeded_continuity_window"
    if terminal_state in {"EXPIRED", "BLOCKED_PRE_EV", "BLOCKED_POST_EV", "CLOSED_OR_UNSAFE", "READINESS_DEGRADED"}:
        return "TERMINATED", terminal_state.lower()
    if event_count == 1:
        return "DISAPPEARED", "single_event_without_terminal_state"
    return "SURVIVED_TO_LAST_SEEN", "no_break_observed"


def _continuity_confidence(
    *,
    identity_inference: str,
    event_count: int,
    survival_inference: str,
    terminal_state: str,
    phase_sequence: list[str],
) -> str:
    if identity_inference == "direct_candidate_id" and event_count >= 2 and terminal_state != "LAST_SEEN_ONLY":
        return "HIGH_DIRECT"
    if identity_inference in {"direct_candidate_id", "direct_signal_id"} and event_count >= 2:
        return "MEDIUM_DIRECT"
    if identity_inference in {"direct_candidate_id", "direct_signal_id"} and survival_inference == "direct_observed":
        return "MEDIUM_DIRECT"
    if identity_inference.startswith("proxy") or len(phase_sequence) <= 1:
        return "LOW_PROXY"
    return "LOW_EVIDENCE"


def _chain_from_records(chain_key: str, records: list[dict[str, Any]], index: int) -> dict[str, Any]:
    records = sorted(records, key=lambda item: item["timestamp_utc"])
    first = records[0]
    last = records[-1]
    phase_sequence = _dedupe_sequence([record["lifecycle_phase"] for record in records])
    transition_sequence = [
        {"from": previous, "to": current}
        for previous, current in zip(phase_sequence, phase_sequence[1:])
    ]
    terminal_state, terminal_reason = _terminal_from_records(records)
    max_gap_ms = _max_event_gap_ms(records)
    continuity_status, break_reason = _continuity_status(
        terminal_state=terminal_state,
        identity_inference=first["identity_inference"],
        event_count=len(records),
        phase_sequence=phase_sequence,
        max_gap_ms=max_gap_ms,
    )
    if break_reason == "no_break_observed" and _skipped_phase_transition(phase_sequence):
        break_reason = "lifecycle_phase_jump_observed"
    survival_ms, survival_inference = _survival_ms(records)
    confidence = _continuity_confidence(
        identity_inference=first["identity_inference"],
        event_count=len(records),
        survival_inference=survival_inference,
        terminal_state=terminal_state,
        phase_sequence=phase_sequence,
    )
    direct_identity = first["candidate_id"] or first["signal_id"]
    chain_id_source = direct_identity or chain_key
    chain_id = f"cc-{index:04d}-{_safe_filename_token(chain_id_source)}"
    pre_ev_events = sum(1 for record in records if record["pre_ev_blocked"] or not record["ev_available"])
    post_ev_events = sum(1 for record in records if record["post_ev_blocked"] or record["ev_available"])
    return {
        "continuity_chain_id": chain_id,
        "candidate_id": first["candidate_id"],
        "signal_id": first["signal_id"],
        "identity_inference": first["identity_inference"],
        "asset": first["asset"],
        "market_id": first["market_id"],
        "first_seen_at_utc": first["timestamp_utc"],
        "last_seen_at_utc": last["timestamp_utc"],
        "event_count": len(records),
        "lifecycle_phase_sequence": phase_sequence,
        "lifecycle_transition_sequence": transition_sequence,
        "lifecycle_degradation": {
            "phase_regression_observed": _phase_regression(phase_sequence),
            "phase_jump_observed": _skipped_phase_transition(phase_sequence),
            "max_event_gap_ms": round(max_gap_ms, 3),
            "gap_threshold_ms": BREAK_GAP_MS,
        },
        "candidate_survival_ms": round(survival_ms, 3),
        "candidate_survival_inference": survival_inference,
        "continuity_status": continuity_status,
        "continuity_break_reason": break_reason,
        "candidate_last_seen_phase": last["lifecycle_phase"],
        "candidate_terminal_state": terminal_state,
        "candidate_terminal_reason": terminal_reason,
        "continuity_confidence": confidence,
        "pre_ev_event_count": pre_ev_events,
        "post_ev_event_count": post_ev_events,
        "readiness_states": sorted({record["readiness_state"] for record in records if record["readiness_state"]}),
        "block_stages": sorted({record["block_stage"] for record in records if record["block_stage"]}),
        "block_reasons": sorted({record["block_reason"] for record in records if record["block_reason"]}),
        "ev_null_reasons": sorted({reason for record in records for reason in record["ev_null_reasons"]}),
        "compact_events": [_compact_event(record) for record in records[:12]],
    }


def _counter_dict(counter: Counter[str]) -> dict[str, int]:
    return dict(counter.most_common())


def _chain_summaries(chains: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts: Counter[str] = Counter()
    break_counts: Counter[str] = Counter()
    terminal_counts: Counter[str] = Counter()
    confidence_counts: Counter[str] = Counter()
    last_phase_counts: Counter[str] = Counter()
    phase_persistence: defaultdict[str, Counter[str]] = defaultdict(Counter)
    expiry_topology: defaultdict[str, Counter[str]] = defaultdict(Counter)
    survival_pre_ev: list[float] = []
    survival_post_ev: list[float] = []
    orphan_patterns: Counter[str] = Counter()

    for chain in chains:
        status_counts[chain["continuity_status"]] += 1
        break_counts[chain["continuity_break_reason"]] += 1
        terminal_counts[chain["candidate_terminal_state"]] += 1
        confidence_counts[chain["continuity_confidence"]] += 1
        last_phase_counts[chain["candidate_last_seen_phase"]] += 1
        for phase in chain["lifecycle_phase_sequence"]:
            phase_persistence[phase][chain["continuity_status"]] += 1
        terminal_reason = chain["candidate_terminal_reason"] or chain["continuity_break_reason"]
        expiry_topology[chain["candidate_terminal_state"]][terminal_reason] += 1
        if chain["pre_ev_event_count"]:
            survival_pre_ev.append(float(chain["candidate_survival_ms"]))
        if chain["post_ev_event_count"]:
            survival_post_ev.append(float(chain["candidate_survival_ms"]))
        if chain["continuity_status"] in {"ORPHAN_OR_PROXY", "DISAPPEARED"}:
            orphan_patterns[chain["continuity_break_reason"]] += 1

    def avg(values: list[float]) -> float:
        return round(sum(values) / len(values), 3) if values else 0.0

    return {
        "candidate_continuity_chains": len(chains),
        "continuity_status_counts": _counter_dict(status_counts),
        "continuity_break_reason_counts": _counter_dict(break_counts),
        "terminal_state_counts": _counter_dict(terminal_counts),
        "continuity_confidence_counts": _counter_dict(confidence_counts),
        "candidate_last_seen_phase_counts": _counter_dict(last_phase_counts),
        "candidate_expiry_topology": {
            state: _counter_dict(counter)
            for state, counter in sorted(expiry_topology.items())
        },
        "pre_ev_vs_post_ev_survival": {
            "pre_ev_chain_count": len(survival_pre_ev),
            "post_ev_chain_count": len(survival_post_ev),
            "avg_pre_ev_survival_ms": avg(survival_pre_ev),
            "avg_post_ev_survival_ms": avg(survival_post_ev),
            "survival_source": "direct_candidate_survival_ms_or_event_span_proxy",
        },
        "candidate_persistence_by_lifecycle_phase": {
            phase: _counter_dict(counter)
            for phase, counter in sorted(phase_persistence.items(), key=lambda item: PHASE_ORDER.get(item[0], 99))
        },
        "orphan_disappearing_candidate_patterns": _counter_dict(orphan_patterns),
    }


def build_candidate_continuity_report(
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
    candidate_events = [event for event in events if _candidate_classification(event)["is_candidate_event"]]
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in candidate_events:
        record = _event_record(event)
        grouped[record["continuity_chain_key"]].append(record)

    chains = [
        _chain_from_records(chain_key, records, index)
        for index, (chain_key, records) in enumerate(sorted(grouped.items()), start=1)
    ]
    chains.sort(key=lambda chain: (chain["first_seen_at_utc"], chain["continuity_chain_id"]))
    summary = _chain_summaries(chains)
    phase2_coverage = build_phase2_coverage_from_events(events)
    coverage_gaps = list(phase2_coverage.get("coverage_gaps", []))
    if not events:
        report_confidence = "INSUFFICIENT"
    elif summary["continuity_confidence_counts"].get("HIGH_DIRECT"):
        report_confidence = "HIGH_DIRECT"
    elif summary["continuity_confidence_counts"].get("MEDIUM_DIRECT"):
        report_confidence = "MEDIUM_DIRECT"
    elif chains:
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
        "schema_version": "candidate_continuity_v1",
        "does_not_claim_profitability": True,
        "does_not_authorize_runtime_decisions": True,
        "does_not_infer_inventory_truth": True,
        "events_loaded": len(events),
        "candidate_events": len(candidate_events),
        "bad_json_lines": bad_json_lines,
        "continuity_confidence": report_confidence,
        "phase2_coverage_status": phase2_coverage.get("status"),
        "coverage_gaps": coverage_gaps,
        "summary": summary,
        "chains": chains[:100],
        "research_questions": {
            "candidate_survival": {
                "answer": "chains_present" if chains else "not_observed",
                "chain_count": len(chains),
                "uncertainty": "survival uses direct candidate_survival_ms when available; otherwise event span proxy",
            },
            "candidate_expiry_topology": summary["candidate_expiry_topology"],
            "pre_ev_vs_post_ev_survival": summary["pre_ev_vs_post_ev_survival"],
            "candidate_persistence_by_lifecycle_phase": summary["candidate_persistence_by_lifecycle_phase"],
            "orphan_disappearing_candidate_patterns": summary["orphan_disappearing_candidate_patterns"],
            "replay_truth_impact": {
                "candidate_identity_linkage": phase2_coverage.get("requirements", {}).get("candidate_identity_linkage", {}),
                "continuity_confidence": report_confidence,
                "guardrail": "evidence only; no runtime execution decision authority",
            },
        },
    }


def write_candidate_continuity_report(report: dict[str, Any], *, report_dir: str | Path = DEFAULT_REPORT_DIR) -> Path:
    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    date_part = _date_part(
        str(report.get("date_from")),
        str(report.get("date_to")),
        dict(report.get("time_filter", {})),
        str(report.get("run_id") or ""),
    )
    output_path = output_dir / f"candidate_continuity_{date_part}.json"
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return output_path


def print_summary(report: dict[str, Any]) -> None:
    summary = report.get("summary", {})
    print("Candidate Continuity Diagnostics")
    print(
        "range={start}..{end} run_id={run_id} events={events} candidates={candidates} chains={chains} confidence={confidence}".format(
            start=report.get("date_from"),
            end=report.get("date_to"),
            run_id=report.get("run_id") or "",
            events=report.get("events_loaded"),
            candidates=report.get("candidate_events"),
            chains=summary.get("candidate_continuity_chains", 0),
            confidence=report.get("continuity_confidence"),
        )
    )
    print(f"continuity_status_counts={summary.get('continuity_status_counts', {})}")
    print(f"break_reason_counts={summary.get('continuity_break_reason_counts', {})}")
    print(f"terminal_state_counts={summary.get('terminal_state_counts', {})}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build offline candidate continuity diagnostics from quant JSONL replay evidence.")
    parser.add_argument("--date", default=None, help="Single date in YYYY-MM-DD format.")
    parser.add_argument("--from", dest="date_from", default=None, help="Start date in YYYY-MM-DD format.")
    parser.add_argument("--to", dest="date_to", default=None, help="End date in YYYY-MM-DD format.")
    parser.add_argument("--since", default=None, help="UTC start time HH:MM for same-day filtering; inclusive.")
    parser.add_argument("--until", default=None, help="UTC end time HH:MM for same-day filtering; exclusive.")
    parser.add_argument("--run-id", default=None, help="Exact run_id to isolate; events without this run_id are excluded.")
    parser.add_argument("--base-dir", default=str(DEFAULT_QUANT_DATA_DIR), help="Quant data root directory.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Output report directory.")
    parser.add_argument("--no-write", action="store_true", help="Do not write candidate_continuity JSON.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_candidate_continuity_report(
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
        path = write_candidate_continuity_report(report, report_dir=args.report_dir)
        print(f"wrote_report={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
