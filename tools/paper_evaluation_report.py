from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_REPORT_DIR = Path("runtime/reports")

DECISION_PASS = "PASS"
DECISION_CAUTION = "CAUTION"
DECISION_FAIL = "FAIL"

DEFAULT_MIN_TRADES_FOR_PASS = 20
DEFAULT_MISSING_REQUIRED_THRESHOLD = 0
DEFAULT_EXECUTION_FAILURE_THRESHOLD = 0
DEFAULT_APPROVED_WITHOUT_TRADES_THRESHOLD = 5
DEFAULT_MAX_DRAWDOWN_PCT = 0.05
DEFAULT_MAX_SPREAD_FOR_PASS = 0.08
DEFAULT_SKIP_REASON_COUNT_THRESHOLD = 10
DEFAULT_SKIP_REASON_RATIO_THRESHOLD = 0.30

SEVERE_RISK_KEYS = (
    "severe_risk_events",
    "risk_events_severe",
    "severe_risk_event_count",
    "risk_incidents",
    "lockdown_events",
    "reconciliation_blocks",
    "fatal_risk_events",
)
SYSTEM_HEALTH_ERROR_KEYS = (
    "logger_errors",
    "logging_errors",
    "telegram_errors",
    "system_health_errors",
    "system_health_error_count",
    "logging_degraded_events",
    "telegram_degraded_events",
    "health_error_count",
)
SEVERE_REASON_TOKENS = (
    "lockdown",
    "reconciliation",
    "panic",
    "fatal",
    "unknown_state",
    "drawdown hard",
    "floor breach",
)
LIQUIDITY_SPREAD_TOKENS = ("liquidity", "spread", "depth", "orderbook")


@dataclass
class PaperEvaluationReport:
    decision: str
    date_from: str
    date_to: str
    generated_at_utc: str
    fail_reasons: list[str] = field(default_factory=list)
    caution_reasons: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    reports_used: dict[str, Any] = field(default_factory=dict)
    criteria: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _date_part(date: str | None = None, date_from: str | None = None, date_to: str | None = None) -> str:
    if date:
        return date
    if not date_from:
        date_from = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not date_to:
        date_to = date_from
    return date_from if date_from == date_to else f"{date_from}_to_{date_to}"


def _date_bounds(date: str | None = None, date_from: str | None = None, date_to: str | None = None) -> tuple[str, str]:
    if date:
        return date, date
    if not date_from:
        date_from = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not date_to:
        date_to = date_from
    return date_from, date_to


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        return None, f"missing_report:{path.name}"
    except json.JSONDecodeError as exc:
        return None, f"invalid_report_json:{path.name}:{exc}"
    except OSError as exc:
        return None, f"unreadable_report:{path.name}:{exc}"
    if not isinstance(payload, dict) or not payload:
        return None, f"empty_report:{path.name}"
    return payload, None


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


def _as_int(value: Any, default: int = 0) -> int:
    return int(_as_float(value, float(default)))


def _indicator_count(payload: dict[str, Any], keys: tuple[str, ...]) -> int:
    total = 0
    for key in keys:
        value = payload.get(key)
        if isinstance(value, bool):
            total += int(value)
        elif isinstance(value, (int, float)):
            total += int(value)
        elif isinstance(value, str):
            total += 1 if value.strip() else 0
        elif isinstance(value, list):
            total += len(value)
        elif isinstance(value, dict):
            total += len(value)
    return total


def _skip_reasons(payload: dict[str, Any]) -> list[tuple[str, int]]:
    reasons: list[tuple[str, int]] = []
    raw = payload.get("top_skip_reasons", [])
    if isinstance(raw, dict):
        raw = raw.items()
    if not isinstance(raw, list) and not hasattr(raw, "__iter__"):
        return reasons
    for item in raw:
        reason = ""
        count = 0
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            reason = str(item[0] or "")
            count = _as_int(item[1])
        elif isinstance(item, dict):
            reason = str(item.get("reason", "") or item.get("skip_reason", "") or "")
            count = _as_int(item.get("count", 1), 1)
        if reason:
            reasons.append((reason, count))
    return reasons


def _count_skip_reasons_with_tokens(payload: dict[str, Any], tokens: tuple[str, ...]) -> int:
    total = 0
    for reason, count in _skip_reasons(payload):
        reason_lower = reason.lower()
        if any(token in reason_lower for token in tokens):
            total += count
    return total


def _has_severe_skip_reason(payload: dict[str, Any]) -> bool:
    return any(
        any(token in reason.lower() for token in SEVERE_REASON_TOKENS)
        for reason, _count in _skip_reasons(payload)
    )


def _drawdown_pct(payload: dict[str, Any]) -> float:
    for key in ("max_drawdown_pct", "drawdown_pct", "daily_drawdown_pct", "total_drawdown_pct"):
        if key in payload:
            return abs(_as_float(payload.get(key)))
    return 0.0


def _quality_metrics(quality_report: dict[str, Any] | None) -> dict[str, int]:
    quality_report = quality_report or {}
    return {
        "bad_json_lines": _as_int(quality_report.get("bad_json_lines")),
        "missing_required_fields": _as_int(quality_report.get("missing_required_fields")),
        "invalid_timestamps": _as_int(quality_report.get("invalid_timestamps")),
        "invalid_event_types": _as_int(quality_report.get("invalid_event_types")),
        "invalid_modes": _as_int(quality_report.get("invalid_modes")),
        "invalid_numeric_fields": _as_int(quality_report.get("invalid_numeric_fields")),
        "unreadable_files": _as_int(quality_report.get("unreadable_files")),
    }


def _aggregate_quality_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    aggregate: dict[str, Any] = {
        "files_scanned": 0,
        "lines_scanned": 0,
        "valid_events": 0,
        "bad_json_lines": 0,
        "missing_required_fields": 0,
        "invalid_timestamps": 0,
        "invalid_event_types": 0,
        "invalid_modes": 0,
        "invalid_numeric_fields": 0,
        "unreadable_files": 0,
    }
    for report in reports:
        for key in aggregate:
            aggregate[key] += _as_int(report.get(key))
    return aggregate


def evaluate_reports(
    *,
    replay_report: dict[str, Any] | None,
    quality_reports: list[dict[str, Any]],
    date_from: str,
    date_to: str,
    missing_or_load_errors: list[str] | None = None,
) -> PaperEvaluationReport:
    fail_reasons: list[str] = list(missing_or_load_errors or [])
    caution_reasons: list[str] = []

    quality_report = _aggregate_quality_reports(quality_reports)
    quality = _quality_metrics(quality_report)
    replay = replay_report or {}

    if not quality_reports:
        fail_reasons.append("missing_or_empty_data_quality_report")
    if not replay:
        fail_reasons.append("missing_or_empty_replay_report")

    if quality["bad_json_lines"] > 0:
        fail_reasons.append("data_quality_bad_json_lines")
    if quality["missing_required_fields"] > DEFAULT_MISSING_REQUIRED_THRESHOLD:
        fail_reasons.append("data_quality_missing_required_fields")
    if quality["unreadable_files"] > 0:
        fail_reasons.append("data_quality_unreadable_files")
    if any(
        quality[key] > 0
        for key in ("invalid_timestamps", "invalid_event_types", "invalid_modes", "invalid_numeric_fields")
    ):
        fail_reasons.append("data_quality_invalid_fields")

    total_trades = _as_int(replay.get("total_trades"))
    approved_decisions = _as_int(replay.get("approved_decisions"))
    skipped_decisions = _as_int(replay.get("skipped_decisions"))
    execution_failures = _as_int(replay.get("execution_failure_count"))
    gross_pnl = _as_float(replay.get("gross_pnl"))
    win_rate = _as_float(replay.get("win_rate"))
    average_spread = _as_float(replay.get("average_spread_at_entry"))
    drawdown_pct = _drawdown_pct(replay)
    severe_risk_count = _indicator_count(replay, SEVERE_RISK_KEYS)
    health_error_count = _indicator_count(replay, SYSTEM_HEALTH_ERROR_KEYS)
    severe_skip_reason = _has_severe_skip_reason(replay)
    liquidity_spread_skips = _count_skip_reasons_with_tokens(replay, LIQUIDITY_SPREAD_TOKENS)

    if execution_failures > DEFAULT_EXECUTION_FAILURE_THRESHOLD:
        fail_reasons.append("execution_failures_above_threshold")
    if severe_risk_count > 0 or severe_skip_reason:
        fail_reasons.append("severe_risk_events_present")
    if total_trades == 0 and approved_decisions >= DEFAULT_APPROVED_WITHOUT_TRADES_THRESHOLD:
        fail_reasons.append("approved_decisions_without_trades")
    if gross_pnl < 0 and drawdown_pct > DEFAULT_MAX_DRAWDOWN_PCT:
        fail_reasons.append("negative_pnl_with_high_drawdown")
    if health_error_count > 0:
        fail_reasons.append("system_health_errors_present")

    if total_trades < DEFAULT_MIN_TRADES_FOR_PASS:
        caution_reasons.append("sample_size_too_small")
    if total_trades > 0 and gross_pnl < 0:
        caution_reasons.append("negative_gross_pnl")
    if average_spread > DEFAULT_MAX_SPREAD_FOR_PASS:
        caution_reasons.append("average_entry_spread_too_high")
    if liquidity_spread_skips >= DEFAULT_SKIP_REASON_COUNT_THRESHOLD:
        caution_reasons.append("too_many_liquidity_or_spread_skips")
    elif skipped_decisions > 0 and (liquidity_spread_skips / skipped_decisions) >= DEFAULT_SKIP_REASON_RATIO_THRESHOLD:
        caution_reasons.append("liquidity_or_spread_skip_ratio_high")

    confidence_correlation = replay.get("confidence_pnl_correlation", replay.get("confidence_correlation"))
    if confidence_correlation is not None and _as_float(confidence_correlation) <= 0:
        caution_reasons.append("confidence_not_positively_correlated_with_pnl")
    if 0 < total_trades < 30 and win_rate <= 0.50:
        caution_reasons.append("win_rate_unstable")

    decision = DECISION_FAIL if fail_reasons else DECISION_CAUTION if caution_reasons else DECISION_PASS
    metrics = {
        "quality": quality,
        "total_trades": total_trades,
        "win_rate": win_rate,
        "gross_pnl": gross_pnl,
        "average_pnl": _as_float(replay.get("average_pnl")),
        "max_drawdown_pct": drawdown_pct,
        "approved_decisions": approved_decisions,
        "rejected_decisions": _as_int(replay.get("rejected_decisions")),
        "skipped_decisions": skipped_decisions,
        "risk_reject_count": _as_int(replay.get("risk_reject_count")),
        "severe_risk_count": severe_risk_count,
        "execution_failure_count": execution_failures,
        "average_spread_at_entry": average_spread,
        "average_confidence_at_entry": _as_float(replay.get("average_confidence_at_entry")),
        "liquidity_spread_skips": liquidity_spread_skips,
        "system_health_error_count": health_error_count,
    }
    criteria = {
        "min_trades_for_pass": DEFAULT_MIN_TRADES_FOR_PASS,
        "missing_required_threshold": DEFAULT_MISSING_REQUIRED_THRESHOLD,
        "execution_failure_threshold": DEFAULT_EXECUTION_FAILURE_THRESHOLD,
        "approved_without_trades_threshold": DEFAULT_APPROVED_WITHOUT_TRADES_THRESHOLD,
        "max_drawdown_pct": DEFAULT_MAX_DRAWDOWN_PCT,
        "max_average_spread_for_pass": DEFAULT_MAX_SPREAD_FOR_PASS,
        "skip_reason_count_threshold": DEFAULT_SKIP_REASON_COUNT_THRESHOLD,
        "skip_reason_ratio_threshold": DEFAULT_SKIP_REASON_RATIO_THRESHOLD,
    }
    return PaperEvaluationReport(
        decision=decision,
        date_from=date_from,
        date_to=date_to,
        generated_at_utc=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        fail_reasons=sorted(set(fail_reasons)),
        caution_reasons=sorted(set(caution_reasons)),
        metrics=metrics,
        reports_used={},
        criteria=criteria,
    )


def evaluate_paper_run(
    *,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    date: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    write_report: bool = True,
) -> PaperEvaluationReport:
    start, end = _date_bounds(date=date, date_from=date_from, date_to=date_to)
    date_part = _date_part(date=date, date_from=start, date_to=end)
    output_dir = Path(report_dir)
    load_errors: list[str] = []

    replay_path = output_dir / f"replay_report_{date_part}.json"
    replay_report, replay_error = _read_json(replay_path)
    if replay_error:
        load_errors.append(replay_error)

    quality_paths = [output_dir / f"quant_data_quality_{date_part}.json"]
    if start != end and not quality_paths[0].exists():
        quality_paths = sorted(output_dir.glob("quant_data_quality_*.json"))
        quality_paths = [
            path for path in quality_paths
            if start <= path.stem.replace("quant_data_quality_", "") <= end
        ]

    quality_reports: list[dict[str, Any]] = []
    for quality_path in quality_paths:
        quality_report, quality_error = _read_json(quality_path)
        if quality_error:
            load_errors.append(quality_error)
        elif quality_report is not None:
            quality_reports.append(quality_report)

    evaluation = evaluate_reports(
        replay_report=replay_report,
        quality_reports=quality_reports,
        date_from=start,
        date_to=end,
        missing_or_load_errors=load_errors,
    )
    evaluation.reports_used = {
        "replay_report": str(replay_path),
        "data_quality_reports": [str(path) for path in quality_paths],
        "paper_evaluation_report": str(output_dir / f"paper_evaluation_{date_part}.json"),
    }

    if write_report:
        write_evaluation_report(evaluation, report_dir=output_dir, date_part=date_part)
    return evaluation


def write_evaluation_report(
    report: PaperEvaluationReport,
    *,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    date_part: str | None = None,
) -> Path:
    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if date_part is None:
        date_part = report.date_from if report.date_from == report.date_to else f"{report.date_from}_to_{report.date_to}"
    output_path = output_dir / f"paper_evaluation_{date_part}.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report.to_dict(), handle, indent=2, sort_keys=True, default=str)
    return output_path


def print_summary(report: PaperEvaluationReport) -> None:
    metrics = report.metrics
    print("Paper Evaluation")
    print(f"range={report.date_from}..{report.date_to} decision={report.decision}")
    print(
        "trades={trades} win_rate={win_rate:.2%} gross_pnl={gross_pnl:.4f} "
        "drawdown_pct={drawdown:.2%} exec_failures={exec_failures}".format(
            trades=metrics.get("total_trades", 0),
            win_rate=metrics.get("win_rate", 0.0),
            gross_pnl=metrics.get("gross_pnl", 0.0),
            drawdown=metrics.get("max_drawdown_pct", 0.0),
            exec_failures=metrics.get("execution_failure_count", 0),
        )
    )
    if report.fail_reasons:
        print("fail_reasons=" + ", ".join(report.fail_reasons))
    if report.caution_reasons:
        print("caution_reasons=" + ", ".join(report.caution_reasons))
    output_path = report.reports_used.get("paper_evaluation_report")
    if output_path:
        print(f"report={output_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate offline paper trading reports for live-test readiness.")
    parser.add_argument("--date", help="Single date to evaluate in YYYY-MM-DD format.", default=None)
    parser.add_argument("--from", dest="date_from", help="Start date in YYYY-MM-DD format.", default=None)
    parser.add_argument("--to", dest="date_to", help="End date in YYYY-MM-DD format.", default=None)
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Report directory.")
    parser.add_argument("--no-json", action="store_true", help="Do not write paper_evaluation JSON.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = evaluate_paper_run(
        report_dir=args.report_dir,
        date=args.date,
        date_from=args.date_from,
        date_to=args.date_to,
        write_report=not args.no_json,
    )
    print_summary(report)
    return 0 if report.decision != DECISION_FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main())
