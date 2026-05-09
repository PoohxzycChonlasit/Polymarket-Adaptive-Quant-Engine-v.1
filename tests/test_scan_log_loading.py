from __future__ import annotations

import csv
from pathlib import Path

import daily_report
from utils.scan_log_loader import load_scan_rows, scan_log_paths
from utils.telegram_reporter import _load_scan_csv


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["timestamp_utc", "asset", "signal"])
        writer.writeheader()
        writer.writerows(rows)


def test_load_scan_rows_combines_old_and_per_run_scan_logs(tmp_path: Path) -> None:
    root = tmp_path / "runtime" / "realtime_logs"
    date = "2026-05-08"
    day_dir = root / date
    _write_csv(day_dir / "scan_log.csv", [
        {"timestamp_utc": "2026-05-08T00:03:00Z", "asset": "BTC", "signal": "SKIP"},
    ])
    _write_csv(day_dir / "scan_log_20260508_000100_1234.csv", [
        {"timestamp_utc": "2026-05-08T00:01:00Z", "asset": "ETH", "signal": "WAIT"},
    ])
    _write_csv(day_dir / "scan_log_20260508_000200_1234.csv", [
        {"timestamp_utc": "2026-05-08T00:02:00Z", "asset": "BTC", "signal": "BUY"},
    ])

    rows = load_scan_rows(date, root=root)

    assert [row["timestamp_utc"] for row in rows] == [
        "2026-05-08T00:01:00Z",
        "2026-05-08T00:02:00Z",
        "2026-05-08T00:03:00Z",
    ]
    assert len(scan_log_paths(date, root=root)) == 3


def test_daily_report_and_telegram_reporter_use_combined_scan_logs(tmp_path: Path) -> None:
    root = tmp_path / "logs"
    date = "2026-05-08"
    _write_csv(root / date / "scan_log_20260508_010000_999.csv", [
        {"timestamp_utc": "2026-05-08T01:00:00Z", "asset": "BTC", "signal": "SKIP"},
    ])
    _write_csv(root / date / "scan_log.csv", [
        {"timestamp_utc": "2026-05-08T00:59:00Z", "asset": "ETH", "signal": "BUY"},
    ])

    daily_rows = daily_report.load_scan_csv(date, root=root)
    telegram_rows = _load_scan_csv(date, root=root)

    assert [row["asset"] for row in daily_rows] == ["ETH", "BTC"]
    assert [row["asset"] for row in telegram_rows] == ["ETH", "BTC"]


def test_missing_scan_log_directory_returns_empty_rows(tmp_path: Path) -> None:
    assert load_scan_rows("2026-05-08", root=tmp_path) == []
