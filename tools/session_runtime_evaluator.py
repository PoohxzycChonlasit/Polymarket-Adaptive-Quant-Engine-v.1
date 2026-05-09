from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
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
from tools.replay_analyzer import ReplayReport, analyze_replay
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
)


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
    recommendations: list[str] = field(default_factory=list)
    reports_used: dict[str, Any] = field(default_factory=dict)
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
) -> tuple[ReplayReport | None, str | None]:
    try:
        report = analyze_replay(base_dir=quant_data_dir, date=date, write_reports=False, write_csv=False)
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


def _build_scores(
    *,
    skip_counts: Counter[str],
    replay: ReplayReport | None,
    no_entry: NoEntryReport | None,
    execution_failure_count: int = 0,
) -> dict[str, int]:
    scores = {key: 0 for key in BOTTLENECKS}
    scores["cutoff"] += skip_counts.get("time_unsafe", 0)
    scores["risk_plan_zero"] += skip_counts.get("risk_plan_zero", 0)
    scores["strategy_thresholds"] += sum(
        skip_counts.get(reason, 0)
        for reason in ("confidence_too_low", "ev_below_threshold", "delta_extreme", "scanner_no_best_trade")
    )
    scores["market_readiness"] += sum(
        count
        for reason, count in skip_counts.items()
        if reason in {"orderbook_unavailable", "no_orderbook"} or "token_mapping" in reason
    )
    scores["stale_data"] += sum(count for reason, count in skip_counts.items() if "stale" in reason)
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


def _resolved_execution_failure_count(
    *,
    replay_payload: dict[str, Any],
    no_entry_payload: dict[str, Any],
) -> int:
    """Resolve true execution failures without treating total execution events as failures."""
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
) -> tuple[str, list[str], list[str]]:
    fail_reasons: list[str] = []
    caution_reasons: list[str] = []
    if load_errors:
        caution_reasons.extend(load_errors)
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
) -> SessionRuntimeEvaluation:
    date = date or _today_utc()
    load_errors: list[str] = []
    replay_obj: ReplayReport | None = replay_report if isinstance(replay_report, ReplayReport) else None
    no_entry_obj: NoEntryReport | None = no_entry_report if isinstance(no_entry_report, NoEntryReport) else None

    if load_offline_reports and replay_obj is None:
        replay_obj, error = _safe_analyze_replay(date=date, quant_data_dir=quant_data_dir)
        if error:
            load_errors.append(error)
    if load_offline_reports and no_entry_obj is None:
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

    execution_failure_count = _resolved_execution_failure_count(
        replay_payload=replay_payload,
        no_entry_payload=no_entry_payload,
    )

    scores = _build_scores(
        skip_counts=skip_counts,
        replay=replay_obj,
        no_entry=no_entry_obj,
        execution_failure_count=execution_failure_count,
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
    primary, secondary = _rank_bottlenecks(scores)
    status, fail_reasons, caution_reasons = _status_for(
        primary=primary,
        scores=scores,
        replay=replay_obj,
        no_entry=no_entry_obj,
        replay_payload=replay_payload,
        no_entry_payload=no_entry_payload,
        load_errors=load_errors,
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
    recommendations = _recommendations(primary, secondary, status, no_entry_obj, replay_obj)
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
        },
        risk_blocks={
            "risk_plan_zero_count": int(skip_counts.get("risk_plan_zero", 0)),
            "risk_reject_count": _as_int(replay_payload.get("risk_reject_count")),
            "risk_mode": str((session_summary or {}).get("risk_mode", "")),
            "risk_mode_allow_new_entries": (session_summary or {}).get("risk_mode_allow_new_entries"),
        },
        execution_summary={
            "execution_failure_count": execution_failure_count,
            "execution_events_loaded": _as_int(no_entry_payload.get("execution_events_loaded")),
            "approved_decisions": _as_int(replay_payload.get("approved_decisions")),
            "rejected_decisions": _as_int(replay_payload.get("rejected_decisions")),
            "order_submit_attempt_count": _as_int(no_entry_payload.get("order_submit_attempt_count")),
            "paper_fill_count": _as_int(no_entry_payload.get("paper_fill_count")),
        },
        orderbook_readiness={
            "orderbook_unavailable_count": int(skip_counts.get("orderbook_unavailable", 0) + skip_counts.get("no_orderbook", 0)),
            "stale_data_count": int(skip_counts.get("stale_data", 0)),
            "average_orderbook_age_ms": _as_float(replay_payload.get("average_orderbook_age_ms", no_entry_payload.get("market_data_quality", {}).get("average_orderbook_age_ms", 0.0))),
            "max_orderbook_age_ms": _as_float(replay_payload.get("max_orderbook_age_ms")),
            "average_oracle_age_ms": _as_float(replay_payload.get("average_oracle_age_ms")),
            "token_mapping_warning_count": _as_int(no_entry_payload.get("market_data_quality", {}).get("token_mapping_warning_count", 0)),
        },
        recommendations=recommendations,
        reports_used={
            "session_summary": bool(session_summary),
            "replay_report": bool(replay_payload),
            "no_entry_report": bool(no_entry_payload),
            "load_errors": load_errors,
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
    if secondary not in {"none", primary}:
        recommendations.append(f"Secondary bottleneck to monitor: {secondary}.")
    if no_entry and no_entry.recommendations:
        recommendations.extend(no_entry.recommendations[:2])
    if replay and replay.execution_failure_count:
        recommendations.append("Execution failures were present; keep live execution disabled and inspect execution_log.")
    return list(dict.fromkeys(recommendations))[:6]


def format_terminal_summary(evaluation: SessionRuntimeEvaluation) -> list[str]:
    health = evaluation.health_summary
    timing = evaluation.timing_quality
    cutoff = evaluation.cutoff_behavior
    orderbook = evaluation.orderbook_readiness
    risk = evaluation.risk_blocks
    execution = evaluation.execution_summary
    return [
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
            f"avg_cycle_ms={timing.get('average_scan_cycle_duration_ms', 0.0):.2f} "
            f"avg_decision_latency_ms={timing.get('average_decision_latency_ms', 0.0):.2f}"
        ),
        (
            "cutoff "
            f"time_unsafe={cutoff.get('time_unsafe_count', 0)} "
            f"blocks={cutoff.get('cutoff_block_count', 0)} "
            f"adaptive_allowed={cutoff.get('adaptive_cutoff_allowed_count', 0)} "
            f"adaptive_denied={cutoff.get('adaptive_cutoff_denied_count', 0)}"
        ),
        (
            "orderbook "
            f"unavailable={orderbook.get('orderbook_unavailable_count', 0)} "
            f"stale={orderbook.get('stale_data_count', 0)} "
            f"avg_age_ms={orderbook.get('average_orderbook_age_ms', 0.0):.2f}"
        ),
        (
            "risk_execution "
            f"risk_plan_zero={risk.get('risk_plan_zero_count', 0)} "
            f"risk_rejects={risk.get('risk_reject_count', 0)} "
            f"execution_failures={execution.get('execution_failure_count', 0)}"
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
    output_path = output_dir / f"session_runtime_evaluation_{evaluation.date}.json"
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
    return parser


def main() -> int:
    args = build_parser().parse_args()
    evaluation = evaluate_session_runtime(
        date=args.date,
        quant_data_dir=args.quant_data_dir,
        realtime_log_dir=args.realtime_log_dir,
        load_offline_reports=True,
    )
    print_summary(evaluation)
    if args.write_report:
        path = write_session_runtime_report(evaluation, report_dir=args.report_dir)
        print(f"wrote_report={path}")
    return 0 if evaluation.session_status != DECISION_FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main())
