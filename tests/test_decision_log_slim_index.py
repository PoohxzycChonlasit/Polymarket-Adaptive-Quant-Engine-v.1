from __future__ import annotations

import ast
import json
import sqlite3
from pathlib import Path

import pytest

from tools.unknown.decision_log_slim_index import build_decision_log_slim_index, is_safe_scratch_output


def _write_jsonl(path: Path, rows: list[dict | str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            if isinstance(row, str):
                handle.write(row.rstrip("\n") + "\n")
            else:
                handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def _decision_row(
    *,
    timestamp: str = "2026-06-21T00:00:00Z",
    run_id: str = "run_1",
    signal_id: str = "signal_1",
    candidate_id: str = "candidate_1",
    condition_id: str = "cond_1",
    edge: float = 0.07,
) -> dict:
    return {
        "event_type": "decision",
        "timestamp_utc": timestamp,
        "run_id": run_id,
        "payload": {
            "signal_id": signal_id,
            "candidate_id": candidate_id,
            "condition_id": condition_id,
            "edge": edge,
            "ev": 0.06,
            "ev_after_spread": 0.05,
            "true_probability": 0.59,
            "volatility_regime": "NORMAL_VOL",
            "trend_regime": "SIDEWAY",
            "large_unused_payload": {"must": "not be stored"},
        },
    }


def _connect(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(str(db_path))


def test_scratch_only_output_guard(tmp_path: Path) -> None:
    assert is_safe_scratch_output(tmp_path / "scratch" / "decision_log_slim_index" / "output")
    assert not is_safe_scratch_output(tmp_path / "runtime" / "decision_log_slim_index")
    assert not is_safe_scratch_output(tmp_path / "other" / "output")


def test_sqlite_and_manifest_are_created(tmp_path: Path) -> None:
    decision_root = tmp_path / "input" / "decision_log"
    output_dir = tmp_path / "scratch" / "decision_log_slim_index" / "output"
    _write_jsonl(decision_root / "2026-06-21.jsonl", [_decision_row()])

    report = build_decision_log_slim_index(decision_root, output_dir)

    assert report["rows_seen"] == 1
    assert report["rows_inserted"] == 1
    assert (output_dir / "decision_log_slim.sqlite").exists()
    manifest_path = output_dir / "decision_log_slim_manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["files_indexed"] == 1
    assert manifest["sqlite_path"] == "decision_log_slim.sqlite"
    assert len(manifest["source_files"]) == 1
    assert {"filename", "size_bytes", "mtime_ns"} <= set(manifest["source_files"][0])


def test_malformed_rows_are_counted(tmp_path: Path) -> None:
    decision_root = tmp_path / "input" / "decision_log"
    output_dir = tmp_path / "scratch" / "decision_log_slim_index" / "output"
    _write_jsonl(decision_root / "2026-06-21.jsonl", [_decision_row(), '{"broken":'])

    report = build_decision_log_slim_index(decision_root, output_dir)

    assert report["rows_seen"] == 2
    assert report["rows_inserted"] == 1
    assert report["malformed_rows"] == 1


def test_projected_fields_are_inserted_without_payload_blob(tmp_path: Path) -> None:
    decision_root = tmp_path / "input" / "decision_log"
    output_dir = tmp_path / "scratch" / "decision_log_slim_index" / "output"
    _write_jsonl(decision_root / "2026-06-21.jsonl", [_decision_row(edge=0.11)])

    build_decision_log_slim_index(decision_root, output_dir)

    with _connect(output_dir / "decision_log_slim.sqlite") as conn:
        row = conn.execute(
            "SELECT timestamp_utc, run_id, signal_id, candidate_id, condition_id, edge, ev, ev_after_spread, true_probability, volatility_regime, trend_regime, source_file, source_line FROM decisions"
        ).fetchone()
        columns = [item[1] for item in conn.execute("PRAGMA table_info(decisions)").fetchall()]

    assert row[:11] == (
        "2026-06-21T00:00:00Z",
        "run_1",
        "signal_1",
        "candidate_1",
        "cond_1",
        0.11,
        0.06,
        0.05,
        0.59,
        "NORMAL_VOL",
        "SIDEWAY",
    )
    assert row[12] == 1
    assert "payload" not in columns
    assert "large_unused_payload" not in columns


def test_indexes_support_run_signal_candidate_and_condition_queries(tmp_path: Path) -> None:
    decision_root = tmp_path / "input" / "decision_log"
    output_dir = tmp_path / "scratch" / "decision_log_slim_index" / "output"
    _write_jsonl(
        decision_root / "2026-06-21.jsonl",
        [
            _decision_row(timestamp="2026-06-21T00:00:00Z", signal_id="signal_a", candidate_id="candidate_a", condition_id="cond_a"),
            _decision_row(timestamp="2026-06-21T00:00:30Z", signal_id="signal_b", candidate_id="candidate_b", condition_id="cond_b"),
        ],
    )

    build_decision_log_slim_index(decision_root, output_dir)

    with _connect(output_dir / "decision_log_slim.sqlite") as conn:
        signal = conn.execute("SELECT condition_id FROM decisions WHERE run_id=? AND signal_id=?", ("run_1", "signal_a")).fetchone()
        candidate = conn.execute("SELECT signal_id FROM decisions WHERE run_id=? AND candidate_id=?", ("run_1", "candidate_b")).fetchone()
        condition_rows = conn.execute(
            "SELECT signal_id FROM decisions WHERE run_id=? AND condition_id=? ORDER BY timestamp_utc",
            ("run_1", "cond_b"),
        ).fetchall()
        index_names = {row[1] for row in conn.execute("PRAGMA index_list(decisions)").fetchall()}

    assert signal == ("cond_a",)
    assert candidate == ("signal_b",)
    assert condition_rows == [("signal_b",)]
    assert {"idx_run_signal", "idx_run_candidate", "idx_run_condition_time"} <= index_names


def test_progress_sidecar_exists(tmp_path: Path) -> None:
    decision_root = tmp_path / "input" / "decision_log"
    output_dir = tmp_path / "scratch" / "decision_log_slim_index" / "output"
    _write_jsonl(decision_root / "2026-06-21.jsonl", [_decision_row()])

    build_decision_log_slim_index(decision_root, output_dir, progress_every_files=1)

    progress = json.loads((output_dir / "decision_log_slim_progress.json").read_text(encoding="utf-8"))
    assert progress["phase"] == "complete"
    assert progress["files_processed"] == 1
    assert progress["rows_seen"] == 1
    assert progress["rows_inserted"] == 1


def test_max_files_and_max_rows_limits_work(tmp_path: Path) -> None:
    decision_root = tmp_path / "input" / "decision_log"
    output_dir = tmp_path / "scratch" / "decision_log_slim_index" / "output"
    _write_jsonl(decision_root / "2026-06-20.jsonl", [_decision_row(signal_id="signal_1"), _decision_row(signal_id="signal_2")])
    _write_jsonl(decision_root / "2026-06-21.jsonl", [_decision_row(signal_id="signal_3")])

    report = build_decision_log_slim_index(decision_root, output_dir, max_files=1, max_rows=1)

    assert report["files_indexed"] == 1
    assert report["rows_seen"] == 1
    assert report["rows_inserted"] == 1
    with _connect(output_dir / "decision_log_slim.sqlite") as conn:
        count = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
    assert count == 1


def test_output_outside_scratch_fails_closed(tmp_path: Path) -> None:
    decision_root = tmp_path / "input" / "decision_log"
    _write_jsonl(decision_root / "2026-06-21.jsonl", [_decision_row()])

    with pytest.raises(ValueError, match="outside scratch"):
        build_decision_log_slim_index(decision_root, tmp_path / "not_scratch" / "output")


def test_no_forbidden_imports() -> None:
    import tools.unknown.decision_log_slim_index as target_module
    tree = ast.parse(Path(target_module.__file__).read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    forbidden = {
        "main",
        "polymarket",
        "polymarket.trader",
        "polymarket.order_manager",
        "polymarket.position_sizing",
        "utils.risk_manager",
    }
    assert imports.isdisjoint(forbidden)
