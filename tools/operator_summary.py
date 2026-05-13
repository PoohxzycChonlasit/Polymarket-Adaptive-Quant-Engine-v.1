from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_REPORT_DIR = Path("runtime/reports")
UNKNOWN = "--"


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _get(payload: dict[str, Any], path: str, default: Any = UNKNOWN) -> Any:
    value: Any = payload
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return default
        value = value[part]
    return default if value is None or value == "" else value


def _count(payload: dict[str, Any], path: str, default: int = 0) -> int:
    value = _get(payload, path, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(payload: dict[str, Any], path: str, default: float = 0.0) -> float:
    value = _get(payload, path, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _first_count(payload: dict[str, Any], paths: tuple[str, ...], default: int = 0) -> int:
    for path in paths:
        value = _get(payload, path, None)
        if value is not None:
            return _count(payload, path, default)
    return default


def _first_text(payload: dict[str, Any], paths: tuple[str, ...], default: str = UNKNOWN) -> str:
    for path in paths:
        value = _get(payload, path, None)
        if value not in (None, ""):
            return str(value)
    return default


def _top_key(mapping: Any, default: str = UNKNOWN) -> str:
    if not isinstance(mapping, dict) or not mapping:
        return default
    numeric_items: list[tuple[str, float]] = []
    for key, value in mapping.items():
        try:
            numeric_items.append((str(key), float(value)))
        except (TypeError, ValueError):
            continue
    if not numeric_items:
        return default
    return max(numeric_items, key=lambda item: item[1])[0]


def _short_counts(mapping: Any, limit: int = 3) -> str:
    if not isinstance(mapping, dict) or not mapping:
        return UNKNOWN
    items: list[tuple[str, float]] = []
    for key, value in mapping.items():
        try:
            items.append((str(key), float(value)))
        except (TypeError, ValueError):
            continue
    if not items:
        return UNKNOWN
    ordered = sorted(items, key=lambda item: item[1], reverse=True)[:limit]
    return ", ".join(f"{key}:{int(value) if value.is_integer() else value:g}" for key, value in ordered)


def _compact_text(value: Any, default: str = UNKNOWN) -> str:
    if value in (None, ""):
        return default
    if isinstance(value, dict):
        parts: list[str] = []
        for key, item in list(value.items())[:5]:
            if isinstance(item, (dict, list, tuple, set)):
                continue
            parts.append(f"{key}={item}")
        return " ".join(parts) if parts else default
    text = str(value)
    if "{" in text and "}" in text:
        prefix = text[: text.find("{")].rstrip()
        inner = text[text.find("{") + 1 : text.rfind("}")]
        compact_inner = (
            inner
            .replace("}", "")
            .replace("'", "")
            .replace(": ", "=")
            .replace(", ", " ")
        )
        text = f"{prefix} {compact_inner}".strip()
    return text


def _fmt_ms(value: Any) -> str:
    try:
        ms = float(value)
    except (TypeError, ValueError):
        return UNKNOWN
    if ms >= 1000:
        return f"{ms / 1000:.2f}s"
    return f"{ms:.0f}ms"


def load_summary(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("compact_run_summary JSON must be an object")
    return payload


def extract_operator_metrics(summary: dict[str, Any]) -> dict[str, Any]:
    paper = _as_dict(summary.get("paper_activity"))
    ev = _as_dict(summary.get("ev_visibility"))
    model = _as_dict(summary.get("model_handoff_diagnostics"))
    funnel = _as_dict(summary.get("decision_runtime_eligibility_funnel"))
    decision_book = _as_dict(summary.get("decision_cycle_orderbook_readiness_audit"))
    sync = _as_dict(summary.get("global_vs_decision_orderbook_sync_audit"))
    timing = _as_dict(summary.get("candidate_timing_diagnostics"))
    timing_summary = _as_dict(timing.get("lifecycle_transition_summary"))
    latency = _as_dict(sync.get("latency_pipeline_decomposition"))

    probability_model_called = _first_count(
        summary,
        (
            "model_handoff_diagnostics.probability_model_call_counts.called",
            "decision_runtime_eligibility_funnel.stages.probability_model_called.survivor_count",
        ),
    )
    model_output_visible = _first_count(
        summary,
        (
            "model_handoff_diagnostics.probability_model_output_visibility_counts.visible",
            "decision_runtime_eligibility_funnel.stages.model_output_visible.survivor_count",
        ),
    )
    decision_ready = _first_count(
        summary,
        (
            "global_vs_decision_orderbook_sync_audit.decision_ready_event_count",
            "decision_cycle_orderbook_readiness_audit.current_cycle_orderbook_ready_count",
            "decision_runtime_eligibility_funnel.stages.orderbook_ready.survivor_count",
        ),
    )
    decision_events = _first_count(
        summary,
        (
            "decision_cycle_orderbook_readiness_audit.decision_candidate_event_count",
            "global_vs_decision_orderbook_sync_audit.decision_event_count",
            "decision_runtime_eligibility_funnel.decision_candidate_event_count",
        ),
    )

    active_losses = (
        _count(timing_summary, "active_candidate_ready_without_model_eligibility_count")
        or _count(timing_summary, "active_events_without_model_eligibility_count")
        or _count(sync, "lifecycle_freshness_loss_counts.ACTIVE_INVENTORY_TRADING")
    )
    final_losses = (
        _count(timing_summary, "final_derisk_before_model_output_count")
        or _count(sync, "lifecycle_freshness_loss_counts.FINAL_DERISK")
        or _count(sync, "final_derisk_freshness_loss_count")
    )

    dominant_blocker = _first_text(
        summary,
        (
            "decision_runtime_eligibility_funnel.dominant_decision_path_blocker",
            "decision_cycle_orderbook_readiness_audit.dominant_decision_cycle_orderbook_blocker",
            "orderbook_health.dominant_blocker",
            "candidate_timing_diagnostics.dominant_timing_bottleneck",
        ),
    )
    if dominant_blocker in {"NONE", "UNKNOWN", UNKNOWN}:
        dominant_blocker = _first_text(
            summary,
            (
                "decision_cycle_orderbook_readiness_audit.dominant_decision_cycle_orderbook_blocker",
                "candidate_timing_diagnostics.dominant_timing_bottleneck",
            ),
        )

    return {
        "run_id": str(summary.get("run_id") or UNKNOWN),
        "date": str(_get(summary, "time_range.date")),
        "time_range": f"{_get(summary, 'time_range.first_event_utc')} -> {_get(summary, 'time_range.last_event_utc')}",
        "events_loaded": _count(summary, "source_inputs.events_loaded", _count(summary, "time_range.events_loaded")),
        "guardrail": "offline-only; runtime_behavior_changed=false",
        "decision_candidate_event_count": decision_events,
        "decision_ready_event_count": decision_ready,
        "candidate_ready_count": _first_count(
            summary,
            (
                "decision_cycle_orderbook_readiness_audit.lifecycle_candidate_ready_count",
                "decision_runtime_eligibility_funnel.stages.candidate_ready.independent_observed_count",
            ),
        ),
        "probability_model_called": probability_model_called,
        "model_output_visible": model_output_visible,
        "ev_visibility": str(ev.get("ev_visibility_status") or UNKNOWN),
        "ev_never_visible": int(ev.get("EV_NEVER_VISIBLE") or 0),
        "ev_confirmed": int(ev.get("ev_visibility_confirmed") or 0),
        "risk_layer_trace_readiness": _float(summary, "risk_layer_trace_readiness"),
        "chain_confidence": _short_counts(summary.get("candidate_chain_trace_confidence")),
        "global_ready_event_count": _count(sync, "global_ready_event_count"),
        "decision_ready_event_count_sync": _count(sync, "decision_ready_event_count"),
        "global_vs_local_mismatch": str(sync.get("synchronization_mismatch_classification") or UNKNOWN),
        "freshness_decay_median": _fmt_ms(sync.get("median_executable_window_age_ms")),
        "same_market_prior_global_ready": _count(sync, "same_market_global_ready_before_decision_count"),
        "fresh_global_ready_within_5s": _count(sync, "fresh_global_ready_before_decision_count"),
        "dominant_latency_stage": str(latency.get("dominant_slow_stage") or UNKNOWN),
        "orderbook_states": _short_counts(_get(summary, "orderbook_health.state_counts", {})),
        "dominant_blocker": dominant_blocker,
        "dominant_model_gap": _first_text(
            summary,
            (
                "ev_visibility.dominant_model_gap",
                "model_activation_diagnostics.dominant_model_activation_block_group",
            ),
        ),
        "model_gate_top": _top_key(model.get("pre_model_gate_counts")),
        "active_vs_final_derisk_losses": f"ACTIVE:{active_losses} FINAL_DERISK:{final_losses}",
        "orders": int(paper.get("orders") or 0),
        "fills": int(paper.get("fills") or 0),
        "exits": int(paper.get("exits") or 0),
        "trades": int(paper.get("replay_total_trades") or 0),
        "root_cause": _compact_text(summary.get("root_cause_candidate")),
        "recommended_next_action": _compact_text(summary.get("recommended_next_codex_patch_target")),
    }


def _section(title: str, lines: list[str]) -> str:
    return "\n".join([title, *lines])


def render_operator_summary(summary: dict[str, Any], *, compact: bool = False, telegram: bool = False) -> str:
    metrics = extract_operator_metrics(summary)
    if telegram:
        return (
            f"SYSTEM {metrics['run_id']} {metrics['date']} events={metrics['events_loaded']}\n"
            f"FUNNEL decision_ready_event_count={metrics['decision_ready_event_count']}/{metrics['decision_candidate_event_count']} "
            f"probability_model_called={metrics['probability_model_called']} model_output_visible={metrics['model_output_visible']}\n"
            f"BOOK freshness_decay_median={metrics['freshness_decay_median']} "
            f"global_vs_local_mismatch={metrics['global_vs_local_mismatch']} blocker={metrics['dominant_blocker']}\n"
            f"MODEL gap={metrics['dominant_model_gap']} gate={metrics['model_gate_top']} "
            f"ACTIVE_vs_FINAL={metrics['active_vs_final_derisk_losses']}\n"
            f"RISK_EV ev_visibility={metrics['ev_visibility']} EV_NEVER_VISIBLE={metrics['ev_never_visible']} "
            f"risk_layer_trace_readiness={metrics['risk_layer_trace_readiness']:.4f}\n"
            f"EXEC orders={metrics['orders']} fills={metrics['fills']} exits={metrics['exits']} trades={metrics['trades']}\n"
            f"ROOT {metrics['root_cause']}\n"
            f"NEXT {metrics['recommended_next_action']}"
        )

    if compact:
        return "\n".join(
            [
                f"SYSTEM STATUS: run={metrics['run_id']} date={metrics['date']} events={metrics['events_loaded']}",
                f"DECISION FUNNEL: decision_ready_event_count={metrics['decision_ready_event_count']}/{metrics['decision_candidate_event_count']} candidate_ready={metrics['candidate_ready_count']}",
                f"ORDERBOOK / FRESHNESS: median={metrics['freshness_decay_median']} mismatch={metrics['global_vs_local_mismatch']} blocker={metrics['dominant_blocker']}",
                f"MODEL STATUS: probability_model_called={metrics['probability_model_called']} model_output_visible={metrics['model_output_visible']} gap={metrics['dominant_model_gap']}",
                f"RISK / EV STATUS: ev_visibility={metrics['ev_visibility']} EV_NEVER_VISIBLE={metrics['ev_never_visible']} risk_layer_trace_readiness={metrics['risk_layer_trace_readiness']:.4f}",
                f"EXECUTION STATUS: orders={metrics['orders']} fills={metrics['fills']} exits={metrics['exits']} trades={metrics['trades']}",
                f"DOMINANT ROOT CAUSE: {metrics['root_cause']}",
                f"RECOMMENDED NEXT ACTION: {metrics['recommended_next_action']}",
            ]
        )

    sections = [
        _section(
            "SYSTEM STATUS",
            [
                f"run_id: {metrics['run_id']}",
                f"time_range: {metrics['time_range']}",
                f"events_loaded: {metrics['events_loaded']} ({metrics['guardrail']})",
            ],
        ),
        _section(
            "DECISION FUNNEL",
            [
                f"decision_ready_event_count: {metrics['decision_ready_event_count']} / {metrics['decision_candidate_event_count']}",
                f"candidate_ready_count: {metrics['candidate_ready_count']}",
                f"dominant_blocker: {metrics['dominant_blocker']}",
            ],
        ),
        _section(
            "ORDERBOOK / FRESHNESS",
            [
                f"freshness_decay_median: {metrics['freshness_decay_median']}",
                f"global_vs_local_mismatch: {metrics['global_vs_local_mismatch']}",
                f"global_ready: {metrics['global_ready_event_count']} prior_same_market: {metrics['same_market_prior_global_ready']} fresh_within_5s: {metrics['fresh_global_ready_within_5s']}",
                f"orderbook_states: {metrics['orderbook_states']}",
            ],
        ),
        _section(
            "MODEL STATUS",
            [
                f"probability_model_called: {metrics['probability_model_called']}",
                f"model_output_visible: {metrics['model_output_visible']}",
                f"dominant_model_gap: {metrics['dominant_model_gap']}",
                f"top_model_gate: {metrics['model_gate_top']}",
            ],
        ),
        _section(
            "RISK / EV STATUS",
            [
                f"ev_visibility: {metrics['ev_visibility']} confirmed={metrics['ev_confirmed']} EV_NEVER_VISIBLE={metrics['ev_never_visible']}",
                f"risk_layer_trace_readiness: {metrics['risk_layer_trace_readiness']:.4f}",
                f"candidate_chain_trace_confidence: {metrics['chain_confidence']}",
            ],
        ),
        _section(
            "EXECUTION STATUS",
            [
                f"orders: {metrics['orders']} fills: {metrics['fills']} exits: {metrics['exits']} trades: {metrics['trades']}",
                f"ACTIVE_vs_FINAL_DERISK_losses: {metrics['active_vs_final_derisk_losses']}",
                f"dominant_latency_stage: {metrics['dominant_latency_stage']}",
            ],
        ),
        _section("DOMINANT ROOT CAUSE", [metrics["root_cause"]]),
        _section("RECOMMENDED NEXT ACTION", [metrics["recommended_next_action"]]),
    ]
    return "\n\n".join(sections)


def _summary_path(args: argparse.Namespace) -> Path:
    if args.summary_json:
        return Path(args.summary_json)
    if args.date:
        return Path(args.report_dir) / f"compact_run_summary_{args.date}.json"
    raise SystemExit("Provide compact summary JSON path or --date YYYY-MM-DD.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a human-sized operator summary from compact_run_summary JSON."
    )
    parser.add_argument("summary_json", nargs="?", help="Path to compact_run_summary_YYYY-MM-DD.json.")
    parser.add_argument("--date", help="Load runtime/reports/compact_run_summary_YYYY-MM-DD.json.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Directory for --date lookup.")
    parser.add_argument("--compact", action="store_true", help="Print one line per required section.")
    parser.add_argument("--telegram", action="store_true", help="Print a single compact text block for Telegram.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    path = _summary_path(args)
    summary = load_summary(path)
    print(render_operator_summary(summary, compact=args.compact, telegram=args.telegram))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
