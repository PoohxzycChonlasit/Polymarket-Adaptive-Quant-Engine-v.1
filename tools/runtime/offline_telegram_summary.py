from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from html import escape
from pathlib import Path
from typing import Any


DEFAULT_REPORT_DIR = Path("runtime/reports")


def _safe_filename_token(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    sanitized = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in text)
    return sanitized[:80] or "run"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _report_path(report_dir: Path, prefix: str, date: str, run_id: str = "") -> Path:
    suffix = f"_run_{_safe_filename_token(run_id)}" if run_id else ""
    return report_dir / f"{prefix}_{date}{suffix}.json"


def _load_reports(*, date: str, run_id: str, report_dir: str | Path = DEFAULT_REPORT_DIR) -> dict[str, dict[str, Any]]:
    root = Path(report_dir)
    reports = {
        "quality": _load_json(_report_path(root, "quant_data_quality", date, run_id)),
        "no_entry": _load_json(_report_path(root, "no_entry_report", date, run_id)),
        "session": _load_json(_report_path(root, "session_runtime_evaluation", date, run_id)),
        "admission": _load_json(root / f"market_readiness_admission_probe_{date}.json"),
    }
    admission = reports["admission"]
    if admission and str(admission.get("run_id_filter") or "") != str(run_id or ""):
        reports["admission"] = {}
    return reports


def _counter_from_pairs(value: Any) -> Counter[str]:
    counter: Counter[str] = Counter()
    if isinstance(value, dict):
        for key, count in value.items():
            if isinstance(count, dict):
                counter[str(key)] += sum(_as_int(item) for item in count.values())
            else:
                counter[str(key)] += _as_int(count)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                counter[str(item[0])] += _as_int(item[1])
    return counter


def _as_int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _as_pct(value: Any) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "n/a"


def _fmt_counter(counter: Counter[str], *, limit: int = 4) -> str:
    if not counter:
        return "unknown"
    return ", ".join(f"{key}={count}" for key, count in counter.most_common(limit))


def _extract_lifecycle(reports: dict[str, dict[str, Any]]) -> Counter[str]:
    admission = reports.get("admission", {})
    lifecycle_probe = admission.get("lifecycle_phase_probe_distribution")
    counter = _counter_from_pairs(lifecycle_probe)
    if counter:
        return counter

    no_entry = reports.get("no_entry", {})
    partial = no_entry.get("partial_lifecycle_replay", {})
    replay_rows = partial.get("partial_lifecycle_replay") if isinstance(partial, dict) else []
    if isinstance(replay_rows, list):
        for row in replay_rows:
            if isinstance(row, dict):
                counter.update(_counter_from_pairs(row.get("lifecycle_phase_counts")))
    return counter


def _extract_liquidity_orderbook(reports: dict[str, dict[str, Any]]) -> str:
    no_entry = reports.get("no_entry", {})
    session = reports.get("session", {})
    market_quality = no_entry.get("market_data_quality") or {}
    market_readiness = session.get("market_readiness") or {}
    spread_liquidity = no_entry.get("spread_liquidity_readiness_summary") or session.get("spread_liquidity_readiness_summary") or {}
    liquidity = _counter_from_pairs(spread_liquidity.get("liquidity_states"))

    unavailable = _as_int(market_quality.get("orderbook_unavailable_count"))
    stale = _as_int(market_quality.get("stale_data_count"))
    ready = _as_int(market_readiness.get("orderbook_ready_count"))
    spread_rate = spread_liquidity.get("spread_normalization_rate")
    spread_text = _as_pct(spread_rate) if spread_rate is not None else "n/a"
    return (
        f"orderbook_ready={ready or 'n/a'}, unavailable={unavailable}, stale={stale}; "
        f"liquidity={_fmt_counter(liquidity, limit=2)}; spread_norm={spread_text}"
    )


def _extract_ev_visibility(reports: dict[str, dict[str, Any]]) -> str:
    admission = reports.get("admission", {})
    funnel = admission.get("gate_funnel") or {}
    if funnel:
        total = _as_int(funnel.get("total"))
        model = _as_int(funnel.get("model_gate_reached"))
        ev = _as_int(funnel.get("ev_gate_reached"))
        return f"model_gate={model}/{total}, ev_gate={ev}/{total}"

    no_entry = reports.get("no_entry", {})
    ev_coverage = ((no_entry.get("phase2_coverage") or {}).get("ev_null_reason_coverage") or {})
    fields = ev_coverage.get("fields") or {}
    ev_field = fields.get("ev_after_spread") or {}
    true_prob = fields.get("true_probability") or {}
    return (
        "status={status}, ev_values={ev_values}, true_prob_values={prob_values}, null_reason_coverage={coverage}".format(
            status=ev_coverage.get("status", "unknown"),
            ev_values=_as_int(ev_field.get("value_events")),
            prob_values=_as_int(true_prob.get("value_events")),
            coverage=_as_pct(ev_coverage.get("null_reason_coverage_rate")),
        )
    )


def _extract_bad_json_warning(reports: dict[str, dict[str, Any]]) -> str:
    quality = reports.get("quality", {})
    no_entry = reports.get("no_entry", {})
    malformed = quality.get("malformed_json_impact") or {}
    affects = bool(malformed.get("affects_selected_run"))
    scoped = _as_int(quality.get("bad_json_lines"))
    scanned_total = _as_int(malformed.get("total_malformed_json_lines_in_scanned_files"))
    no_entry_bad = _as_int(no_entry.get("bad_json_lines"))
    if affects or scoped:
        return f"SCOPED WARNING: scoped_bad_json={scoped}, day_total={scanned_total}, no_entry_warning={no_entry_bad}"
    if scanned_total or no_entry_bad:
        return f"day warning only: scoped_bad_json=0, day_total={scanned_total}, no_entry_warning={no_entry_bad}"
    return "none"


def build_offline_telegram_summary_message(
    *,
    date: str,
    run_id: str,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
) -> str:
    reports = _load_reports(date=date, run_id=run_id, report_dir=report_dir)
    quality = reports.get("quality", {})
    no_entry = reports.get("no_entry", {})

    continuity = ((quality.get("replay_continuity") or {}).get("status") or "UNKNOWN")
    root = no_entry.get("root_cause_category") or "unknown"
    time_unsafe = _as_int(no_entry.get("count_time_unsafe"))
    risk_plan_zero = _as_int(no_entry.get("count_risk_plan_zero"))
    root_counts = no_entry.get("root_cause_counts") or {}

    lines = [
        "<b>Offline Paper Evidence Summary</b>",
        f"Date: <code>{escape(date)}</code>",
        f"Run: <code>{escape(run_id)}</code>",
        f"Continuity: <b>{escape(str(continuity))}</b>",
        f"Root cause: <b>{escape(str(root))}</b> <code>{escape(json.dumps(root_counts, sort_keys=True))}</code>",
        f"Blocks: <code>time_unsafe={time_unsafe}</code> <code>risk_plan_zero={risk_plan_zero}</code>",
        f"Lifecycle: <code>{escape(_fmt_counter(_extract_lifecycle(reports)))}</code>",
        f"Liquidity/Orderbook: <code>{escape(_extract_liquidity_orderbook(reports))}</code>",
        f"EV visibility: <code>{escape(_extract_ev_visibility(reports))}</code>",
        f"Bad JSON: <code>{escape(_extract_bad_json_warning(reports))}</code>",
        "<i>Offline report summary only. No runtime, strategy, risk, execution, wallet, or live config changes.</i>",
    ]
    return "\n".join(lines)


def send_offline_telegram_summary(message: str) -> bool:
    from utils.telegram_reporter import send_message_direct

    return bool(send_message_direct(message))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build/send an offline Telegram summary from generated reports.")
    parser.add_argument("--date", required=True, help="Report date in YYYY-MM-DD format.")
    parser.add_argument("--run-id", required=True, help="Run id to summarize.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Generated reports directory.")
    parser.add_argument("--send", action="store_true", help="Actually send the message via configured Telegram.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    message = build_offline_telegram_summary_message(
        date=args.date,
        run_id=args.run_id,
        report_dir=args.report_dir,
    )
    if args.send:
        return 0 if send_offline_telegram_summary(message) else 1
    sys.stdout.write(message)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
