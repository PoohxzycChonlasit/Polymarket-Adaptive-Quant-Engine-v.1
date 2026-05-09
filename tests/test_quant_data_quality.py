from __future__ import annotations

import json
from pathlib import Path

from tools.quant_data_quality import scan_quant_data, write_quality_report


DATE = "2026-05-08"


def _event(event_type: str = "market_snapshot", payload: dict | None = None, **overrides) -> dict:
    event = {
        "timestamp_utc": f"{DATE}T12:00:00Z",
        "event_type": event_type,
        "mode": "paper",
        "run_id": "run-test",
        "source_module": "test",
        "schema_version": "1.0",
        "payload": payload or {},
    }
    event.update(overrides)
    return event


def _write_jsonl(path: Path, lines: list[dict | str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for line in lines:
            if isinstance(line, str):
                handle.write(line + "\n")
            else:
                handle.write(json.dumps(line) + "\n")


def test_quant_data_quality_valid_files_pass_and_report_is_created(tmp_path: Path) -> None:
    base_dir = tmp_path / "runtime" / "quant_data"
    report_dir = tmp_path / "runtime" / "reports"
    _write_jsonl(base_dir / "market_snapshots" / f"{DATE}.jsonl", [
        _event(payload={"ticker": "BTC", "price": 100.0, "spread": 0.02, "liquidity": "12.5"}),
    ])
    _write_jsonl(base_dir / "decision_log" / f"{DATE}.jsonl", [
        _event("decision", payload={"confidence": 0.72, "edge": "0.04"}),
    ])

    report = scan_quant_data(base_dir=base_dir, date=DATE, report_dir=report_dir, write_report=True)

    assert report.ok
    assert report.files_scanned == 2
    assert report.lines_scanned == 2
    assert report.valid_events == 2
    assert (report_dir / f"quant_data_quality_{DATE}.json").exists()


def test_quant_data_quality_counts_malformed_missing_and_invalid_numeric_lines(tmp_path: Path) -> None:
    base_dir = tmp_path / "runtime" / "quant_data"
    _write_jsonl(base_dir / "execution_log" / f"{DATE}.jsonl", [
        "{not-json",
        _event("execution", mode="", payload={"price": "not-a-number"}),
        _event("", timestamp_utc="bad-time", payload={"size": 1.0}),
    ])

    report = scan_quant_data(base_dir=base_dir, date=DATE)

    assert not report.ok
    assert report.lines_scanned == 3
    assert report.bad_json_lines == 1
    assert report.missing_required_fields == 2
    assert report.invalid_timestamps == 1
    assert report.invalid_event_types == 1
    assert report.invalid_modes == 1
    assert report.invalid_numeric_fields == 1
    assert report.bad_lines == 3


def test_quant_data_quality_empty_dataset_is_safe(tmp_path: Path) -> None:
    report = scan_quant_data(base_dir=tmp_path / "missing", date=DATE)

    assert report.ok
    assert report.files_scanned == 0
    assert report.lines_scanned == 0
    assert report.valid_events == 0


def test_quant_data_quality_empty_file_does_not_crash(tmp_path: Path) -> None:
    base_dir = tmp_path / "runtime" / "quant_data"
    path = base_dir / "risk_log" / f"{DATE}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")

    report = scan_quant_data(base_dir=base_dir, date=DATE)

    assert report.ok
    assert report.files_scanned == 1
    assert report.empty_files == 1


def test_write_quality_report_uses_requested_directory(tmp_path: Path) -> None:
    report = scan_quant_data(base_dir=tmp_path / "missing", date=DATE)
    output = write_quality_report(report, report_dir=tmp_path / "reports")

    assert output.exists()
    assert json.loads(output.read_text(encoding="utf-8"))["date"] == DATE
