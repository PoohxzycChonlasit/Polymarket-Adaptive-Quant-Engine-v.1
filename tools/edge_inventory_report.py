"""Offline Edge Inventory Report V1.

Reads paper trade-open/trade-close JSONL evidence and builds descriptive
closed-trade summaries. It has no runtime, strategy, risk, or execution role.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any, Iterable


DEFAULT_TRADE_JOURNAL_DIR = Path("runtime/quant_data/trade_journal")
DEFAULT_REPORT_DIR = Path("runtime/reports")
DEFAULT_EXPORT_DIR = Path("runtime/research_exports")

ATTRIBUTION_FIELDS = (
    "candidate_id",
    "candidate_trace_id",
    "candidate_instance_id",
    "candidate_instance_trace_id",
    "candidate_instance_created_at",
    "candidate_instance_identity_schema_version",
    "candidate_instance_identity_source",
    "legacy_candidate_identity_source",
    "signal_name",
    "signal_reason",
    "strategy_signal_name",
    "strategy_signal_reason",
    "paper_trade_replay_key",
    "entry_ev",
    "entry_probability",
    "selected_side",
)

IDENTITY_REQUIRED_FIELDS = (
    "candidate_id",
    "candidate_trace_id",
    "candidate_instance_id",
    "candidate_instance_trace_id",
    "candidate_instance_created_at",
    "candidate_instance_identity_schema_version",
    "candidate_instance_identity_source",
    "legacy_candidate_identity_source",
    "signal_name",
    "signal_reason",
    "paper_trade_replay_key",
    "selected_side",
)

NOT_READY_METRICS = (
    "MFE",
    "MAE",
    "slippage",
    "adverse_selection",
    "true_net_ev_after_costs",
    "official_outcome_truth",
    "live_profitability",
    "causal_signal_edge",
)


def _payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload")
    return payload if isinstance(payload, dict) else {}


def _available(value: Any) -> bool:
    return value is not None and value != ""


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pnl(payload: dict[str, Any]) -> float | None:
    for field in ("pnl_usdc", "pnl", "realized_pnl"):
        value = _as_float(payload.get(field))
        if value is not None:
            return value
    return None


def _is_partial(payload: dict[str, Any]) -> bool:
    value = payload.get("partial", False)
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return bool(value)


def _attribution(payload: dict[str, Any]) -> dict[str, Any] | None:
    value = payload.get("entry_attribution")
    if not isinstance(value, dict):
        return None
    val = dict(value)
    if "strategy_signal_name" not in val or val["strategy_signal_name"] is None:
        val["strategy_signal_name"] = val.get("signal_name") or "UNKNOWN_STRATEGY_SIGNAL"
    if "strategy_signal_reason" not in val or val["strategy_signal_reason"] is None:
        val["strategy_signal_reason"] = val.get("signal_reason") or "unknown_strategy_reason"
    return val


def _attribution_is_malformed(value: dict[str, Any] | None) -> bool:
    return value is None or any(not _available(value.get(field)) for field in IDENTITY_REQUIRED_FIELDS)


def _attribution_complete(value: dict[str, Any] | None) -> bool:
    return value is not None and all(_available(value.get(field)) for field in ATTRIBUTION_FIELDS)


def _join_key(event: dict[str, Any]) -> tuple[str, str] | None:
    run_id = str(event.get("run_id") or _payload(event).get("run_id") or "").strip()
    position_id = str(_payload(event).get("position_id") or "").strip()
    return (run_id, position_id) if run_id and position_id else None


def _timestamp(event: dict[str, Any]) -> str:
    return str(event.get("timestamp_utc") or "").strip()


def load_trade_journal_events(
    trade_journal_dir: str | Path = DEFAULT_TRADE_JOURNAL_DIR,
    *,
    date_from: str,
    date_to: str,
) -> list[dict[str, Any]]:
    """Load only paper trade-open/trade-close rows for the inclusive date range."""
    events: list[dict[str, Any]] = []
    root = Path(trade_journal_dir)
    for path in sorted(root.glob("*.jsonl")):
        date_part = path.stem
        if date_part < date_from or date_part > date_to:
            continue
        try:
            with path.open(encoding="utf-8") as handle:
                for line_number, raw_line in enumerate(handle, start=1):
                    try:
                        event = json.loads(raw_line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(event, dict):
                        continue
                    if event.get("mode") != "paper":
                        continue
                    if event.get("event_type") not in {"trade_open", "trade_close"}:
                        continue
                    event["_source_file"] = f"{path}:{line_number}"
                    events.append(event)
        except OSError:
            continue
    return events


def _quarantine_record(
    reason: str,
    *,
    key: tuple[str, str] | None = None,
    event: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "run_id": key[0] if key else str((event or {}).get("run_id") or ""),
        "position_id": key[1] if key else str(_payload(event or {}).get("position_id") or ""),
        "validation_status": "QUARANTINED",
        "quarantine_reason": reason,
        "source_file": str((event or {}).get("_source_file") or ""),
    }


def _build_closed_row(
    key: tuple[str, str],
    open_event: dict[str, Any],
    close_events: list[dict[str, Any]],
    *,
    legacy: bool,
) -> dict[str, Any]:
    open_payload = _payload(open_event)
    terminal = [event for event in close_events if not _is_partial(_payload(event))][0]
    terminal_payload = _payload(terminal)
    attribution = _attribution(open_payload)
    pnl_values = [value for event in close_events for value in [_pnl(_payload(event))] if value is not None]
    realized_pnl = sum(pnl_values)
    outcome = "win" if realized_pnl > 0 else "loss" if realized_pnl < 0 else "breakeven"
    row: dict[str, Any] = {
        "run_id": key[0],
        "position_id": key[1],
        "entry_timestamp": _timestamp(open_event),
        "exit_timestamp": _timestamp(terminal),
        "entry_attribution_status": "missing_legacy" if legacy else str(
            open_payload.get("entry_attribution_status") or "ready"
        ),
        "entry_attribution": attribution,
        "realized_pnl": realized_pnl,
        "outcome": outcome,
        "partial_close_count": sum(1 for event in close_events if _is_partial(_payload(event))),
        "validation_status": "LEGACY" if legacy else "VALID",
        "quarantine_reason": "",
    }
    if attribution is not None:
        row.update({field: attribution.get(field) for field in ATTRIBUTION_FIELDS})
    return row


def _metric_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pnls = [value for row in rows for value in [_as_float(row.get("realized_pnl"))] if value is not None]
    evs = [value for row in rows for value in [_as_float(row.get("entry_ev"))] if value is not None]
    probabilities = [
        value for row in rows for value in [_as_float(row.get("entry_probability"))] if value is not None
    ]
    count = len(rows)
    wins = sum(1 for row in rows if row.get("outcome") == "win")
    return {
        "closed_trade_count": count,
        "win_count": wins,
        "loss_count": sum(1 for row in rows if row.get("outcome") == "loss"),
        "breakeven_count": sum(1 for row in rows if row.get("outcome") == "breakeven"),
        "win_rate": wins / count if count else 0.0,
        "total_realized_pnl": sum(pnls),
        "avg_realized_pnl": mean(pnls) if pnls else None,
        "avg_realized_pnl_denominator": len(pnls),
        "missing_realized_pnl_count": count - len(pnls),
        "avg_entry_ev": mean(evs) if evs else None,
        "avg_entry_ev_denominator": len(evs),
        "missing_entry_ev_count": count - len(evs),
        "avg_entry_probability": mean(probabilities) if probabilities else None,
        "avg_entry_probability_denominator": len(probabilities),
        "missing_entry_probability_count": count - len(probabilities),
        "replay_key_coverage": (
            sum(1 for row in rows if _available(row.get("paper_trade_replay_key"))) / count if count else 0.0
        ),
        "attribution_complete_rate": (
            sum(1 for row in rows if _attribution_complete(row.get("entry_attribution"))) / count if count else 0.0
        ),
    }


def _group_table(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = tuple(str(row.get(field) or "") for field in fields)
        grouped[key].append(row)
    return [
        {**dict(zip(fields, key)), **_metric_row(items)}
        for key, items in sorted(grouped.items())
    ]


def _readiness(valid_attributed_count: int, attributed_complete_rate: float, closed_count: int) -> str:
    if closed_count == 0:
        return "NO_CLOSED_TRADES"
    if attributed_complete_rate < 0.95:
        return "ATTRIBUTION_NOT_READY"
    if valid_attributed_count < 30:
        return "INSUFFICIENT_EVIDENCE"
    if valid_attributed_count < 100:
        return "EXPLORATORY_ONLY"
    if valid_attributed_count < 200:
        return "DESCRIPTIVE_MONITORING"
    return "FORMAL_REVIEW_ELIGIBLE"


def build_report(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Build an in-memory report from paper trade-journal events."""
    filtered = [
        event
        for event in events
        if event.get("mode") == "paper" and event.get("event_type") in {"trade_open", "trade_close"}
    ]
    opens: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    closes: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    quarantined: list[dict[str, Any]] = []
    for event in filtered:
        key = _join_key(event)
        if key is None:
            quarantined.append(_quarantine_record("missing_position_id", event=event))
            continue
        target = opens if event.get("event_type") == "trade_open" else closes
        target[key].append(event)

    closed_rows: list[dict[str, Any]] = []
    open_only_count = 0
    for key in sorted(set(opens) | set(closes)):
        open_events = sorted(opens.get(key, []), key=_timestamp)
        close_events = sorted(closes.get(key, []), key=_timestamp)
        terminal_closes = [event for event in close_events if not _is_partial(_payload(event))]
        if not open_events or not terminal_closes:
            if open_events:
                open_only_count += 1
            elif close_events:
                quarantined.append(_quarantine_record("missing_trade_open", key=key, event=close_events[0]))
            continue
        reasons: list[str] = []
        if len(open_events) > 1:
            reasons.append("duplicate_open")
        if len(terminal_closes) > 1:
            reasons.append("duplicate_terminal_close")
        if any(_pnl(_payload(event)) is None for event in close_events):
            reasons.append("missing_close_pnl")
        open_payload = _payload(open_events[0])
        legacy = open_payload.get("entry_attribution_status") == "missing_legacy"
        open_attribution = _attribution(open_payload)
        close_attributions = [_attribution(_payload(event)) for event in close_events]
        if legacy:
            if any(value is not None for value in close_attributions):
                reasons.append("conflicting_attribution")
        else:
            if _attribution_is_malformed(open_attribution) or any(
                _attribution_is_malformed(value) for value in close_attributions
            ):
                reasons.append("malformed_attribution")
            elif any(value != open_attribution for value in close_attributions):
                reasons.append("conflicting_attribution")
        if reasons:
            quarantined.append(_quarantine_record("|".join(reasons), key=key, event=open_events[0]))
            continue
        closed_rows.append(_build_closed_row(key, open_events[0], close_events, legacy=legacy))

    attributed_rows = [row for row in closed_rows if row.get("validation_status") == "VALID"]
    legacy_rows = [row for row in closed_rows if row.get("validation_status") == "LEGACY"]
    overall_metrics = _metric_row(closed_rows)
    verdict = _readiness(
        len(attributed_rows),
        _metric_row(attributed_rows)["attribution_complete_rate"] if attributed_rows else 0.0,
        len(closed_rows),
    )
    return {
        "metadata": {
            "report_name": "EDGE_INVENTORY_REPORT_V1",
            "schema_version": "1.0",
            "offline_only": True,
            "evidence_inventory_only": True,
            "not_ready_metrics": list(NOT_READY_METRICS),
        },
        "summary": {
            "paper_event_count": len(filtered),
            "trade_open_count": sum(len(value) for value in opens.values()),
            "trade_close_count": sum(len(value) for value in closes.values()),
            "closed_trade_count": len(closed_rows),
            "valid_attributed_trade_count": len(attributed_rows),
            "legacy_trade_count": len(legacy_rows),
            "quarantined_trade_count": len(quarantined),
            "open_only_count": open_only_count,
            **overall_metrics,
        },
        "closed_trades": closed_rows,
        "signal_edge_summary": _group_table(attributed_rows, ("signal_name",)),
        "signal_reason_summary": _group_table(attributed_rows, ("signal_name", "signal_reason")),
        "strategy_signal_edge_summary": _group_table(attributed_rows, ("strategy_signal_name",)),
        "strategy_signal_reason_summary": _group_table(attributed_rows, ("strategy_signal_name", "strategy_signal_reason")),
        "logical_candidate_summary": _group_table(attributed_rows, ("candidate_id",)),
        "candidate_instance_summary": _group_table(attributed_rows, ("candidate_instance_id",)),
        "unattributed_legacy_trades": legacy_rows,
        "quarantined_trades": quarantined,
        "report_readiness_verdict": verdict,
    }


def _date_bounds(date: str | None, date_from: str | None, date_to: str | None) -> tuple[str, str]:
    if date:
        return date, date
    start = date_from or datetime.now(UTC).strftime("%Y-%m-%d")
    return start, date_to or start


def _filename(base: str, date_from: str, date_to: str, extension: str) -> str:
    suffix = "" if date_from == date_to else f"_{date_from}_to_{date_to}"
    return f"{base}{suffix}.{extension}"


def _write_json(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = (
        "run_id",
        "position_id",
        "entry_timestamp",
        "exit_timestamp",
        "entry_attribution_status",
        *ATTRIBUTION_FIELDS,
        "realized_pnl",
        "outcome",
        "partial_close_count",
        "validation_status",
        "quarantine_reason",
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _markdown_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_No rows_"
    columns = list(rows[0])
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join(lines)


def _write_md(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Edge Inventory Report V1",
        "",
        f"- Verdict: `{report['report_readiness_verdict']}`",
        f"- Closed trades: {report['summary']['closed_trade_count']}",
        f"- Attributed trades: {report['summary']['valid_attributed_trade_count']}",
        f"- Legacy trades: {report['summary']['legacy_trade_count']}",
        f"- Quarantined records: {report['summary']['quarantined_trade_count']}",
        "",
    ]
    for title, key in (
        ("Signal Edge Summary", "signal_edge_summary"),
        ("Signal Reason Summary", "signal_reason_summary"),
        ("Strategy Signal Summary", "strategy_signal_edge_summary"),
        ("Strategy Signal Reason Summary", "strategy_signal_reason_summary"),
        ("Logical Candidate Summary", "logical_candidate_summary"),
        ("Candidate Instance Summary", "candidate_instance_summary"),
        ("Unattributed / Legacy Trades", "unattributed_legacy_trades"),
    ):
        lines.extend([f"## {title}", "", _markdown_table(report[key]), ""])
    lines.extend([
        "## Not-Ready Metrics",
        "",
        ", ".join(report["metadata"]["not_ready_metrics"]),
        "",
        "This report is offline evidence inventory only and has no runtime decision authority.",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build offline Edge Inventory Report V1.")
    dates = parser.add_mutually_exclusive_group()
    dates.add_argument("--date")
    dates.add_argument("--from", dest="date_from")
    parser.add_argument("--to", dest="date_to")
    parser.add_argument("--trade-journal-dir", default=str(DEFAULT_TRADE_JOURNAL_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--export-dir", default=str(DEFAULT_EXPORT_DIR))
    parser.add_argument("--write-json", action="store_true")
    parser.add_argument("--write-csv", action="store_true")
    parser.add_argument("--write-md", action="store_true")
    args = parser.parse_args(argv)

    date_from, date_to = _date_bounds(args.date, args.date_from, args.date_to)
    events = load_trade_journal_events(args.trade_journal_dir, date_from=date_from, date_to=date_to)
    report = build_report(events)
    report["metadata"].update({"date_from": date_from, "date_to": date_to})
    report_dir = Path(args.report_dir)
    export_dir = Path(args.export_dir)
    if args.write_json:
        _write_json(report, report_dir / _filename("edge_inventory_report_v1", date_from, date_to, "json"))
    if args.write_md:
        _write_md(report, report_dir / _filename("edge_inventory_report_v1", date_from, date_to, "md"))
    if args.write_csv:
        _write_csv(
            report["closed_trades"],
            export_dir / _filename("edge_inventory_closed_trades_v1", date_from, date_to, "csv"),
        )
    print(f"date_from={date_from} date_to={date_to}")
    print(f"closed_trade_count={report['summary']['closed_trade_count']}")
    print(f"valid_attributed_trade_count={report['summary']['valid_attributed_trade_count']}")
    print(f"legacy_trade_count={report['summary']['legacy_trade_count']}")
    print(f"quarantined_trade_count={report['summary']['quarantined_trade_count']}")
    print(f"report_readiness_verdict={report['report_readiness_verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
