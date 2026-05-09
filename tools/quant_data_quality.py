from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


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


@dataclass
class QuantDataQualityReport:
    date: str | None = None
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
    report_dir: str | Path | None = None,
    write_report: bool = False,
) -> QuantDataQualityReport:
    report = QuantDataQualityReport(date=date, base_dir=str(Path(base_dir)))
    paths = quant_jsonl_paths(base_dir, date)
    report.files_scanned = len(paths)

    for path in paths:
        file_lines = 0
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
                        report.bad_json_lines += 1
                        report.bad_lines_count += 1
                        report.errors.append(_line_error(path, line_number, "bad_json", str(exc)))
                        continue
                    if not isinstance(event, dict):
                        report.bad_json_lines += 1
                        report.bad_lines_count += 1
                        report.errors.append(_line_error(path, line_number, "bad_json", "event is not an object"))
                        continue

                    event_errors = validate_event(event)
                    if not event_errors:
                        report.valid_events += 1
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
                        report.errors.append(_line_error(path, line_number, error_type, error))
        except OSError as exc:
            report.unreadable_files += 1
            report.errors.append({"file": str(path), "type": "unreadable_file", "error": str(exc)})
            continue
        if file_lines == 0:
            report.empty_files += 1

    if write_report:
        write_quality_report(report, report_dir=report_dir)
    return report


def _line_error(path: Path, line_number: int, error_type: str, detail: Any) -> dict[str, Any]:
    return {
        "file": str(path),
        "line": line_number,
        "type": error_type,
        "detail": detail,
    }


def write_quality_report(
    report: QuantDataQualityReport,
    *,
    report_dir: str | Path | None = None,
) -> Path:
    output_dir = Path(report_dir or DEFAULT_REPORT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    date_part = report.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_path = output_dir / f"quant_data_quality_{date_part}.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report.to_dict(), handle, indent=2, sort_keys=True, default=str)
    return output_path


def print_summary(report: QuantDataQualityReport) -> None:
    print("Quant Data Quality")
    print(f"date={report.date or 'all'} base_dir={report.base_dir}")
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
    parser.add_argument("--base-dir", default=str(DEFAULT_QUANT_DATA_DIR), help="Quant data root directory.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Output report directory.")
    parser.add_argument("--write-report", action="store_true", help="Write JSON report under runtime/reports.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = scan_quant_data(
        base_dir=args.base_dir,
        date=args.date,
        report_dir=args.report_dir,
        write_report=args.write_report,
    )
    print_summary(report)
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
