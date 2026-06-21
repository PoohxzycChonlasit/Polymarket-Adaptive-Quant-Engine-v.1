from __future__ import annotations

import argparse
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "decision_log_slim_index.v1"
SQLITE_FILENAME = "decision_log_slim.sqlite"
MANIFEST_FILENAME = "decision_log_slim_manifest.json"
PROGRESS_FILENAME = "decision_log_slim_progress.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def is_safe_scratch_output(path: str | Path) -> bool:
    resolved_parts = {part.lower() for part in Path(path).resolve().parts}
    return "scratch" in resolved_parts and "runtime" not in resolved_parts


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")
    os.replace(tmp_path, path)


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    payload = row.get("payload")
    return payload if isinstance(payload, dict) else {}


def _first_non_null(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _project_row(row: dict[str, Any], source_file: Path, source_line: int) -> tuple[Any, ...]:
    payload = _payload(row)
    return (
        _first_non_null(row.get("timestamp_utc"), payload.get("timestamp_utc"), row.get("timestamp")),
        _first_non_null(row.get("run_id"), payload.get("run_id")),
        _first_non_null(row.get("signal_id"), payload.get("signal_id")),
        _first_non_null(row.get("candidate_id"), payload.get("candidate_id")),
        _first_non_null(row.get("condition_id"), payload.get("condition_id")),
        _as_float(_first_non_null(row.get("edge"), payload.get("edge"))),
        _as_float(_first_non_null(row.get("ev"), payload.get("ev"))),
        _as_float(_first_non_null(row.get("ev_after_spread"), payload.get("ev_after_spread"))),
        _as_float(_first_non_null(row.get("true_probability"), payload.get("true_probability"))),
        _first_non_null(row.get("volatility_regime"), payload.get("volatility_regime")),
        _first_non_null(row.get("trend_regime"), payload.get("trend_regime")),
        str(source_file),
        source_line,
    )


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE decisions (
          id INTEGER PRIMARY KEY,
          timestamp_utc TEXT,
          run_id TEXT,
          signal_id TEXT,
          candidate_id TEXT,
          condition_id TEXT,
          edge REAL,
          ev REAL,
          ev_after_spread REAL,
          true_probability REAL,
          volatility_regime TEXT,
          trend_regime TEXT,
          source_file TEXT,
          source_line INTEGER
        );

        CREATE INDEX idx_run_signal
        ON decisions(run_id, signal_id);

        CREATE INDEX idx_run_candidate
        ON decisions(run_id, candidate_id);

        CREATE INDEX idx_run_condition_time
        ON decisions(run_id, condition_id, timestamp_utc);
        """
    )


def _source_file_entry(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "filename": str(path),
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def _progress_payload(
    *,
    phase: str,
    files_processed: int,
    current_file: str | None,
    rows_seen: int,
    rows_inserted: int,
    malformed_rows: int,
) -> dict[str, Any]:
    return {
        "phase": phase,
        "files_processed": files_processed,
        "current_file": current_file,
        "rows_seen": rows_seen,
        "rows_inserted": rows_inserted,
        "malformed_rows": malformed_rows,
        "last_updated_utc": _utc_now_iso(),
    }


def build_decision_log_slim_index(
    decision_log_root: str | Path,
    output_dir: str | Path,
    *,
    progress_every_files: int = 5,
    max_files: int | None = None,
    max_rows: int | None = None,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    if not is_safe_scratch_output(output_path):
        raise ValueError(f"output directory outside scratch: {output_dir}")

    decision_root = Path(decision_log_root)
    output_path.mkdir(parents=True, exist_ok=True)
    sqlite_path = output_path / SQLITE_FILENAME
    manifest_path = output_path / MANIFEST_FILENAME
    progress_path = output_path / PROGRESS_FILENAME

    if sqlite_path.exists():
        sqlite_path.unlink()

    decision_files = sorted(decision_root.glob("*.jsonl"))
    if max_files is not None and max_files > 0:
        decision_files = decision_files[:max_files]

    rows_seen = 0
    rows_inserted = 0
    malformed_rows = 0
    files_processed = 0
    source_files: list[dict[str, Any]] = []

    _write_json_atomic(
        progress_path,
        _progress_payload(
            phase="started",
            files_processed=0,
            current_file=None,
            rows_seen=rows_seen,
            rows_inserted=rows_inserted,
            malformed_rows=malformed_rows,
        ),
    )

    with sqlite3.connect(str(sqlite_path)) as conn:
        _create_schema(conn)
        insert_sql = """
            INSERT INTO decisions (
                timestamp_utc,
                run_id,
                signal_id,
                candidate_id,
                condition_id,
                edge,
                ev,
                ev_after_spread,
                true_probability,
                volatility_regime,
                trend_regime,
                source_file,
                source_line
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        stop_requested = False
        for file_index, path in enumerate(decision_files, start=1):
            files_processed = file_index
            source_files.append(_source_file_entry(path))
            with path.open("r", encoding="utf-8") as handle:
                for line_no, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    if max_rows is not None and max_rows > 0 and rows_seen >= max_rows:
                        stop_requested = True
                        break
                    rows_seen += 1
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        malformed_rows += 1
                        continue
                    if not isinstance(row, dict):
                        malformed_rows += 1
                        continue
                    conn.execute(insert_sql, _project_row(row, path, line_no))
                    rows_inserted += 1

            if progress_every_files and file_index % progress_every_files == 0:
                _write_json_atomic(
                    progress_path,
                    _progress_payload(
                        phase="indexing",
                        files_processed=files_processed,
                        current_file=str(path),
                        rows_seen=rows_seen,
                        rows_inserted=rows_inserted,
                        malformed_rows=malformed_rows,
                    ),
                )
            if stop_requested:
                break
        conn.commit()

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": _utc_now_iso(),
        "decision_log_root": str(decision_root),
        "files_indexed": len(source_files),
        "rows_seen": rows_seen,
        "rows_inserted": rows_inserted,
        "malformed_rows": malformed_rows,
        "sqlite_path": SQLITE_FILENAME,
        "source_files": source_files,
    }
    _write_json_atomic(manifest_path, manifest)
    _write_json_atomic(
        progress_path,
        _progress_payload(
            phase="complete",
            files_processed=len(source_files),
            current_file=None,
            rows_seen=rows_seen,
            rows_inserted=rows_inserted,
            malformed_rows=malformed_rows,
        ),
    )
    return manifest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a scratch-only SQLite slim index for decision_log JSONL files.")
    parser.add_argument("--decision-log-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--progress-every-files", type=int, default=5)
    parser.add_argument("--max-files", type=int, default=None)
    parser.add_argument("--max-rows", type=int, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = build_decision_log_slim_index(
        args.decision_log_root,
        args.output_dir,
        progress_every_files=args.progress_every_files,
        max_files=args.max_files,
        max_rows=args.max_rows,
    )
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
