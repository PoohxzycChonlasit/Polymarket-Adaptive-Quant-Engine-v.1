from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    from tools.replay_analyzer import build_phase2_coverage_from_events
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools.replay_analyzer import build_phase2_coverage_from_events


DEFAULT_QUANT_DATA_DIR = Path("runtime/quant_data")
DEFAULT_REPORT_DIR = Path("runtime/reports")
REQUIRED_FIELDS = (
    "timestamp_utc",
    "event_type",
    "mode",
    "run_id",
    "source_module",
    "schema_version",
)
VALID_MODES = {"paper", "live", "verify", "backtest", "hft"}
NUMERIC_FIELDS = {
    "price",
    "size",
    "shares",
    "pnl",
    "confidence",
    "edge",
    "spread",
    "liquidity",
}
REPLAY_CHAIN_CATEGORIES = (
    "market_snapshots",
    "decision_log",
    "risk_log",
    "execution_log",
)
RESEARCH_CATEGORY = "research_log"
MAX_REPORTED_GAPS = 25


@dataclass
class QuantDataQualityReport:
    date: str | None = None
    run_id: str = ""
    base_dir: str = ""
    files_scanned: int = 0
    lines_scanned: int = 0
    valid_events: int = 0
    bad_json_lines: int = 0
    missing_required_fields: int = 0
    invalid_timestamps: int = 0
    invalid_event_types: int = 0
    invalid_modes: int = 0
    invalid_numeric_fields: int = 0
    unreadable_files: int = 0
    empty_files: int = 0
    bad_lines_count: int = 0
    phase2_coverage: dict[str, Any] = field(default_factory=dict)
    category_counts: dict[str, int] = field(default_factory=dict)
    run_id_summary: dict[str, Any] = field(default_factory=dict)
    replay_continuity: dict[str, Any] = field(default_factory=dict)
    timestamp_ordering: dict[str, Any] = field(default_factory=dict)
    research_log_integrity: dict[str, Any] = field(default_factory=dict)
    malformed_json_impact: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)

    @property
    def bad_lines(self) -> int:
        return self.bad_lines_count + self.unreadable_files

    @property
    def ok(self) -> bool:
        return self.bad_lines == 0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["bad_lines"] = self.bad_lines
        data["ok"] = self.ok
        return data


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
    return parsed


def _is_numeric(value: Any) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str) and value.strip():
        try:
            float(value)
            return True
        except ValueError:
            return False
    return False


def _iter_numeric_field_values(value: Any) -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in NUMERIC_FIELDS:
                yield key, item
            yield from _iter_numeric_field_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_numeric_field_values(item)


def _safe_filename_token(value: Any) -> str:
    text = str(value or "").strip()
    return "".join(character if character.isalnum() or character in ("-", "_") else "_" for character in text)


def quant_jsonl_paths(base_dir: str | Path = DEFAULT_QUANT_DATA_DIR, date: str | None = None) -> list[Path]:
    root = Path(base_dir)
    if not root.exists():
        return []
    pattern = f"{date}.jsonl" if date else "*.jsonl"
    return sorted(path for path in root.glob(f"*/{pattern}") if path.is_file())


def validate_event(event: dict[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    missing = [field for field_name in REQUIRED_FIELDS if not event.get(field_name) for field in (field_name,)]
    if missing:
        errors.append({"type": "missing_required_fields", "fields": missing})

    if _parse_timestamp(event.get("timestamp_utc")) is None:
        errors.append({"type": "invalid_timestamp", "value": event.get("timestamp_utc")})

    if not str(event.get("event_type", "")).strip():
        errors.append({"type": "invalid_event_type", "value": event.get("event_type")})

    mode = str(event.get("mode", "")).strip().lower()
    if not mode or mode not in VALID_MODES:
        errors.append({"type": "invalid_mode", "value": event.get("mode")})

    invalid_numeric = [
        {"field": key, "value": value}
        for key, value in _iter_numeric_field_values(event)
        if not _is_numeric(value)
    ]
    if invalid_numeric:
        errors.append({"type": "invalid_numeric_fields", "fields": invalid_numeric})
    return errors


def scan_quant_data(
    *,
    base_dir: str | Path = DEFAULT_QUANT_DATA_DIR,
    date: str | None = None,
    run_id: str | None = None,
    report_dir: str | Path | None = None,
    write_report: bool = False,
) -> QuantDataQualityReport:
    scoped_run_id = str(run_id or "").strip()
    report = QuantDataQualityReport(date=date, run_id=scoped_run_id, base_dir=str(Path(base_dir)))
    paths = quant_jsonl_paths(base_dir, date)
    report.files_scanned = len(paths)
    phase2_events: list[dict[str, Any]] = []
    object_events_for_continuity: list[dict[str, Any]] = []
    category_counts: Counter[str] = Counter()
    category_bad_json: Counter[str] = Counter()
    unscoped_bad_json: Counter[str] = Counter()
    scoped_bad_json: Counter[str] = Counter()
    malformed_json_lines: list[dict[str, Any]] = []
    timestamp_order_violations: list[dict[str, Any]] = []

    for path in paths:
        file_lines = 0
        previous_timestamp: datetime | None = None
        previous_timestamp_text = ""
        try:
            with path.open(encoding="utf-8") as handle:
                for line_number, raw_line in enumerate(handle, start=1):
                    text = raw_line.strip()
                    if not text:
                        continue
                    file_lines += 1
                    report.lines_scanned += 1
                    try:
                        event = json.loads(text)
                    except json.JSONDecodeError as exc:
                        line_error = _line_error(path, line_number, "bad_json", str(exc), raw_line=text)
                        malformed_json_lines.append(line_error)
                        unscoped_bad_json[path.parent.name] += 1
                        if not scoped_run_id or scoped_run_id in text:
                            report.bad_json_lines += 1
                            report.bad_lines_count += 1
                            category_bad_json[path.parent.name] += 1
                            if scoped_run_id:
                                scoped_bad_json[path.parent.name] += 1
                            report.errors.append(line_error)
                        continue
                    if not isinstance(event, dict):
                        line_error = _line_error(path, line_number, "bad_json", "event is not an object", raw_line=text)
                        malformed_json_lines.append(line_error)
                        unscoped_bad_json[path.parent.name] += 1
                        if not scoped_run_id or scoped_run_id in text:
                            report.bad_json_lines += 1
                            report.bad_lines_count += 1
                            category_bad_json[path.parent.name] += 1
                            if scoped_run_id:
                                scoped_bad_json[path.parent.name] += 1
                            report.errors.append(line_error)
                        continue
                    if scoped_run_id and str(event.get("run_id") or "").strip() != scoped_run_id:
                        continue
                    event["_category"] = path.parent.name
                    event["_file"] = str(path)
                    event["_line"] = line_number
                    phase2_events.append(event)
                    object_events_for_continuity.append(event)
                    category_counts[path.parent.name] += 1

                    event_errors = validate_event(event)
                    if not event_errors:
                        report.valid_events += 1
                        current_timestamp = _parse_timestamp(event.get("timestamp_utc"))
                        timestamp_text = str(event.get("timestamp_utc") or "")
                        if current_timestamp is not None:
                            if previous_timestamp is not None and current_timestamp < previous_timestamp:
                                timestamp_order_violations.append(
                                    {
                                        "file": str(path),
                                        "line": line_number,
                                        "previous_timestamp_utc": previous_timestamp_text,
                                        "timestamp_utc": timestamp_text,
                                    }
                                )
                            previous_timestamp = current_timestamp
                            previous_timestamp_text = timestamp_text
                        continue
                    report.bad_lines_count += 1
                    for error in event_errors:
                        error_type = str(error.get("type", "unknown"))
                        if error_type == "missing_required_fields":
                            report.missing_required_fields += 1
                        elif error_type == "invalid_timestamp":
                            report.invalid_timestamps += 1
                        elif error_type == "invalid_event_type":
                            report.invalid_event_types += 1
                        elif error_type == "invalid_mode":
                            report.invalid_modes += 1
                        elif error_type == "invalid_numeric_fields":
                            report.invalid_numeric_fields += 1
                        report.errors.append(_line_error(path, line_number, error_type, error, raw_line=text))
        except OSError as exc:
            report.unreadable_files += 1
            report.errors.append({"file": str(path), "type": "unreadable_file", "error": str(exc)})
            continue
        if file_lines == 0:
            report.empty_files += 1

    report.category_counts = dict(sorted(category_counts.items()))
    report.timestamp_ordering = _build_timestamp_ordering_summary(timestamp_order_violations)
    report.run_id_summary = _build_run_id_summary(object_events_for_continuity)
    report.research_log_integrity = _build_research_log_integrity(category_counts, category_bad_json)
    report.malformed_json_impact = _build_malformed_json_impact(
        run_id=scoped_run_id,
        unscoped_bad_json=unscoped_bad_json,
        scoped_bad_json=scoped_bad_json,
        malformed_json_lines=malformed_json_lines,
    )
    report.replay_continuity = _build_replay_continuity_summary(
        report=report,
        events=object_events_for_continuity,
        timestamp_order_violations=timestamp_order_violations,
    )
    report.phase2_coverage = build_phase2_coverage_from_events(phase2_events)

    if write_report:
        write_quality_report(report, report_dir=report_dir)
    return report


def _line_error(path: Path, line_number: int, error_type: str, detail: Any, *, raw_line: str | None = None) -> dict[str, Any]:
    error = {
        "file": str(path),
        "line": line_number,
        "type": error_type,
        "detail": detail,
    }
    if raw_line is not None:
        preview = raw_line.strip()
        error["line_preview"] = preview[:240]
        error["line_length"] = len(raw_line)
    return error


def _build_timestamp_ordering_summary(violations: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "PASS" if not violations else "FAIL",
        "file_order_violation_count": len(violations),
        "file_order_violations": violations[:MAX_REPORTED_GAPS],
        "truncated": len(violations) > MAX_REPORTED_GAPS,
    }


def _build_run_id_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, dict[str, Any]] = {}
    missing_run_id_events = 0
    for event in events:
        raw_run_id = str(event.get("run_id") or "").strip()
        if not raw_run_id:
            missing_run_id_events += 1
        run_id = raw_run_id or "missing_run_id"
        item = grouped.setdefault(
            run_id,
            {
                "event_count": 0,
                "categories": Counter(),
                "modes": Counter(),
                "first_timestamp_utc": "",
                "last_timestamp_utc": "",
                "missing_run_id": not raw_run_id,
            },
        )
        item["event_count"] += 1
        category = str(event.get("_category") or event.get("event_type") or "unknown")
        mode = str(event.get("mode") or "").strip() or "unknown"
        item["categories"][category] += 1
        item["modes"][mode] += 1
        timestamp = str(event.get("timestamp_utc") or "").strip()
        if timestamp:
            if not item["first_timestamp_utc"] or timestamp < item["first_timestamp_utc"]:
                item["first_timestamp_utc"] = timestamp
            if not item["last_timestamp_utc"] or timestamp > item["last_timestamp_utc"]:
                item["last_timestamp_utc"] = timestamp

    run_ids: list[dict[str, Any]] = []
    mixed_mode_run_ids: list[str] = []
    single_category_run_ids: list[str] = []
    for run_id, item in sorted(grouped.items(), key=lambda pair: (pair[1]["first_timestamp_utc"], pair[0])):
        categories = dict(sorted(item["categories"].items()))
        modes = dict(sorted(item["modes"].items()))
        if len(modes) > 1:
            mixed_mode_run_ids.append(run_id)
        if len(categories) == 1:
            single_category_run_ids.append(run_id)
        run_ids.append(
            {
                "run_id": run_id,
                "event_count": item["event_count"],
                "first_timestamp_utc": item["first_timestamp_utc"],
                "last_timestamp_utc": item["last_timestamp_utc"],
                "categories": categories,
                "modes": modes,
                "missing_run_id": bool(item["missing_run_id"]),
            }
        )
    return {
        "run_id_count": len(grouped),
        "missing_run_id_events": missing_run_id_events,
        "mixed_mode_run_id_count": len(mixed_mode_run_ids),
        "mixed_mode_run_ids": mixed_mode_run_ids[:MAX_REPORTED_GAPS],
        "single_category_run_id_count": len(single_category_run_ids),
        "single_category_run_ids": single_category_run_ids[:MAX_REPORTED_GAPS],
        "run_ids": run_ids[:MAX_REPORTED_GAPS],
        "run_ids_truncated": len(run_ids) > MAX_REPORTED_GAPS,
    }


def _build_research_log_integrity(category_counts: Counter[str], category_bad_json: Counter[str]) -> dict[str, Any]:
    event_count = int(category_counts.get(RESEARCH_CATEGORY, 0))
    bad_json_count = int(category_bad_json.get(RESEARCH_CATEGORY, 0))
    if event_count == 0 and bad_json_count == 0:
        status = "MISSING"
    elif bad_json_count:
        status = "FAIL"
    else:
        status = "PASS"
    return {
        "status": status,
        "category": RESEARCH_CATEGORY,
        "valid_event_count": event_count,
        "bad_json_lines": bad_json_count,
    }


def _build_malformed_json_impact(
    *,
    run_id: str,
    unscoped_bad_json: Counter[str],
    scoped_bad_json: Counter[str],
    malformed_json_lines: list[dict[str, Any]],
) -> dict[str, Any]:
    total_bad_json_lines = int(sum(unscoped_bad_json.values()))
    scoped_bad_json_lines = int(sum(scoped_bad_json.values()))
    if not run_id:
        status = "GLOBAL_SCOPE"
        affects_selected_run = total_bad_json_lines > 0
        note = "No run_id scope was requested; all malformed JSONL lines affect the report verdict."
    elif scoped_bad_json_lines:
        status = "AFFECTS_SELECTED_RUN"
        affects_selected_run = True
        note = "At least one malformed line contains the selected run_id text and is counted against the scoped verdict."
    else:
        status = "NO_DIRECT_RUN_ID_MATCH"
        affects_selected_run = False
        note = "Malformed lines cannot be fully attributed after JSON parse failure, but none contain the selected run_id text."
    return {
        "status": status,
        "run_id": run_id,
        "affects_selected_run": affects_selected_run,
        "total_malformed_json_lines_in_scanned_files": total_bad_json_lines,
        "matching_run_id_malformed_json_lines": scoped_bad_json_lines,
        "malformed_json_by_category": dict(sorted(unscoped_bad_json.items())),
        "matching_run_id_malformed_json_by_category": dict(sorted(scoped_bad_json.items())),
        "sample_malformed_lines": malformed_json_lines[:MAX_REPORTED_GAPS],
        "sample_malformed_lines_truncated": len(malformed_json_lines) > MAX_REPORTED_GAPS,
        "note": note,
    }


def _build_replay_continuity_summary(
    *,
    report: QuantDataQualityReport,
    events: list[dict[str, Any]],
    timestamp_order_violations: list[dict[str, Any]],
) -> dict[str, Any]:
    run_categories: dict[str, set[str]] = {}
    for event in events:
        run_id = str(event.get("run_id") or "").strip()
        if not run_id:
            continue
        run_categories.setdefault(run_id, set()).add(str(event.get("_category") or "unknown"))

    chain_gaps: list[dict[str, Any]] = []
    for run_id, categories in sorted(run_categories.items()):
        observed_chain = [category for category in REPLAY_CHAIN_CATEGORIES if category in categories]
        missing_chain = [category for category in REPLAY_CHAIN_CATEGORIES if category not in categories]
        if missing_chain:
            chain_gaps.append(
                {
                    "run_id": run_id,
                    "observed_chain_categories": observed_chain,
                    "missing_chain_categories": missing_chain,
                }
            )

    status = "PASS"
    reasons: list[str] = []
    if report.bad_json_lines or report.unreadable_files:
        status = "FAIL"
        reasons.append("malformed_or_unreadable_jsonl")
    if report.invalid_timestamps:
        status = "FAIL"
        reasons.append("invalid_timestamps")
    if timestamp_order_violations:
        status = "FAIL"
        reasons.append("timestamp_order_violations")
    missing_run_ids = int(report.run_id_summary.get("missing_run_id_events", 0))
    if missing_run_ids:
        status = "FAIL"
        reasons.append("missing_run_id_events")
    if chain_gaps and status == "PASS":
        status = "CAUTION"
        reasons.append("replay_chain_category_gaps")

    return {
        "status": status,
        "reasons": reasons,
        "run_id_scope": report.run_id,
        "events_checked": len(events),
        "chain_categories_expected": list(REPLAY_CHAIN_CATEGORIES),
        "run_chain_gap_count": len(chain_gaps),
        "run_chain_gaps": chain_gaps[:MAX_REPORTED_GAPS],
        "run_chain_gaps_truncated": len(chain_gaps) > MAX_REPORTED_GAPS,
        "trustworthy_for_replay": status == "PASS",
        "notes": [
            "This is an offline evidence-quality verdict only.",
            "trade_journal is not required for continuity because no-entry runs can legitimately have no trades.",
        ],
    }


def write_quality_report(
    report: QuantDataQualityReport,
    *,
    report_dir: str | Path | None = None,
) -> Path:
    output_dir = Path(report_dir or DEFAULT_REPORT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    date_part = report.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if report.run_id:
        date_part = f"{date_part}_run_{_safe_filename_token(report.run_id)}"
    output_path = output_dir / f"quant_data_quality_{date_part}.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report.to_dict(), handle, indent=2, sort_keys=True, default=str)
    return output_path


def print_summary(report: QuantDataQualityReport) -> None:
    print("Quant Data Quality")
    print(f"date={report.date or 'all'} run_id={report.run_id or ''} base_dir={report.base_dir}")
    print(f"files={report.files_scanned} lines={report.lines_scanned} valid_events={report.valid_events}")
    print(
        "bad_json={bad_json} missing_required={missing} invalid_ts={ts} "
        "invalid_event={event} invalid_mode={mode} invalid_numeric={numeric} empty_files={empty}".format(
            bad_json=report.bad_json_lines,
            missing=report.missing_required_fields,
            ts=report.invalid_timestamps,
            event=report.invalid_event_types,
            mode=report.invalid_modes,
            numeric=report.invalid_numeric_fields,
            empty=report.empty_files,
        )
    )
    print(f"ok={report.ok} bad_lines={report.bad_lines}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate PolyTrade quant JSONL data.")
    parser.add_argument("--date", help="Date to scan in YYYY-MM-DD format.", default=None)
    parser.add_argument("--run-id", default=None, help="Exact run_id to isolate; other valid events are excluded.")
    parser.add_argument("--base-dir", default=str(DEFAULT_QUANT_DATA_DIR), help="Quant data root directory.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Output report directory.")
    parser.add_argument("--write-report", action="store_true", help="Write JSON report under runtime/reports.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = scan_quant_data(
        base_dir=args.base_dir,
        date=args.date,
        run_id=args.run_id,
        report_dir=args.report_dir,
        write_report=args.write_report,
    )
    print_summary(report)
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
