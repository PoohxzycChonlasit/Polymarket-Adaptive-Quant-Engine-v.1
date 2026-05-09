from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_SCAN_LOG_ROOT = Path("runtime/realtime_logs")


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _sort_key(indexed_row: tuple[int, dict[str, Any]]) -> tuple[int, str, int]:
    index, row = indexed_row
    timestamp = _parse_timestamp(str(row.get("timestamp_utc", "")))
    if timestamp is not None:
        return (0, timestamp.isoformat(), index)

    date_th = str(row.get("date_th", "")).strip()
    time_th = str(row.get("time_th", "")).strip()
    fallback = f"{date_th} {time_th}".strip()
    if fallback:
        return (1, fallback, index)
    return (2, "", index)


def scan_log_paths(date_str: str, root: str | Path = DEFAULT_SCAN_LOG_ROOT) -> list[Path]:
    """Return old and per-run scan CSV files for a realtime log date."""
    day_dir = Path(root) / date_str
    if not day_dir.exists():
        return []
    return sorted(path for path in day_dir.glob("scan_log*.csv") if path.is_file())


def load_scan_rows(date_str: str, root: str | Path = DEFAULT_SCAN_LOG_ROOT) -> list[dict[str, Any]]:
    """Load and combine scan logs written by old and per-run realtime loggers."""
    rows: list[dict[str, Any]] = []
    for path in scan_log_paths(date_str, root=root):
        with path.open(newline="", encoding="utf-8") as handle:
            rows.extend(dict(row) for row in csv.DictReader(handle))
    return [row for _, row in sorted(enumerate(rows), key=_sort_key)]
