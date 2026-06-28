from __future__ import annotations

import hashlib
import json
import ast
import shutil
import sqlite3
from pathlib import Path

import pytest

from tools.shadow import shadow_filter_evaluator
from tools.joined_records_builder import build_joined_records, extract_json_string_field, is_safe_scratch_path, main


def _write_jsonl(path: Path, rows: list[dict]) -> list[str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    hashes: list[str] = []
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            line = json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
            handle.write(line)
            hashes.append(hashlib.sha256(line.encode("utf-8")).hexdigest())
    return hashes


def _trade_row(event_type: str, *, run_id: str = "run_1", timestamp: str = "2026-06-21T00:00:00Z", **payload: object) -> dict:
    return {
        "event_type": event_type,
        "mode": "paper",
        "run_id": run_id,
        "timestamp_utc": timestamp,
        "payload": {
            "asset": "ETH",
            "outcome": "YES",
            "side": "YES",
            "condition_id": "cond_1",
            "epoch_start_ts": 1780000000,
            "market_slug": "eth-updown-5m-1780000000",
            "position_id": "pos_1",
            "signal_id": "signal_1",
            "candidate_id": "candidate_1",
            "entry_price": 0.52,
            "exit_price": 0.58,
            "pnl": 0.30,
            **payload,
        },
    }


def _decision_row(*, run_id: str = "run_1", timestamp: str = "2026-06-21T00:00:05Z", **payload: object) -> dict:
    return {
        "event_type": "decision",
        "mode": "paper",
        "run_id": run_id,
        "timestamp_utc": timestamp,
        "payload": {
            "asset": "ETH",
            "outcome": "YES",
            "condition_id": "cond_1",
            "market_slug": "eth-updown-5m-1780000000",
            "signal_id": "signal_1",
            "candidate_id": "candidate_1",
            "edge": 0.07,
            "ev": 0.06,
            "ev_after_spread": 0.05,
            "true_probability": 0.59,
            "volatility_regime": "NORMAL_VOL",
            "trend_regime": "SIDEWAY",
            **payload,
        },
    }


def _execution_close(source_file: Path, source_hash: str, *, source_line: int = 2, **payload: object) -> dict:
    return {
        "schema_version": "execution_paper.v1",
        "event_type": "execution_paper_close",
        "timestamp_utc": "2026-06-21T00:00:30Z",
        "execution_run_id": "execution_run_1",
        "source_file": str(source_file),
        "source_line": source_line,
        "source_event_sha256": source_hash,
        "source_run_id": "run_1",
        "source_event_type": "trade_close",
        "asset": "ETH",
        "side": "YES",
        "condition_id": "cond_1",
        "historical_position_uid": "hist_1",
        "execution_position_id": "ep_pos_1",
        "execution_entry_price": 0.52,
        "execution_exit_price": 0.58,
        "execution_shares": 5.0,
        "execution_pnl": 0.30,
        **payload,
    }


def _fixture_roots(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    execution_root = tmp_path / "execution_root"
    trade_root = tmp_path / "trade_journal"
    decision_root = tmp_path / "decision_log"
    output_dir = tmp_path / "scratch" / "joined_records_builder" / "output"
    return execution_root, trade_root, decision_root, output_dir


def _write_basic_fixture(tmp_path: Path, *, decision: dict | None = None, open_payload: dict | None = None, close_payload: dict | None = None) -> tuple[Path, Path, Path, Path]:
    execution_root, trade_root, decision_root, output_dir = _fixture_roots(tmp_path)
    trade_file = trade_root / "2026-06-21.jsonl"
    trade_hashes = _write_jsonl(
        trade_file,
        [
            _trade_row("trade_open", timestamp="2026-06-21T00:00:00Z", **(open_payload or {})),
            _trade_row("trade_close", timestamp="2026-06-21T00:00:30Z", **(close_payload or {})),
        ],
    )
    _write_jsonl(execution_root / "journals" / "trade" / "2026-06-21.jsonl", [_execution_close(trade_file, trade_hashes[1])])
    _write_jsonl(decision_root / "2026-06-21.jsonl", [decision if decision is not None else _decision_row()])
    return execution_root, trade_root, decision_root, output_dir


def _read_output(output_dir: Path) -> tuple[list[dict], dict]:
    rows = [json.loads(line) for line in (output_dir / "joined_records.jsonl").read_text(encoding="utf-8").splitlines()]
    report = json.loads((output_dir / "joined_records_report.json").read_text(encoding="utf-8"))
    return rows, report


def _write_slim_index(index_root: Path, decision_root: Path, rows: list[dict]) -> Path:
    index_root.mkdir(parents=True, exist_ok=True)
    sqlite_path = index_root / "decision_log_slim.sqlite"
    conn = sqlite3.connect(sqlite_path)
    try:
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
            CREATE INDEX idx_run_signal ON decisions(run_id, signal_id);
            CREATE INDEX idx_run_candidate ON decisions(run_id, candidate_id);
            CREATE INDEX idx_run_condition_time ON decisions(run_id, condition_id, timestamp_utc);
            """
        )
        for row in rows:
            payload = row.get("payload", {})
            conn.execute(
                """
                INSERT INTO decisions (
                    timestamp_utc, run_id, signal_id, candidate_id, condition_id,
                    edge, ev, ev_after_spread, true_probability, volatility_regime,
                    trend_regime, source_file, source_line
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.get("timestamp_utc"),
                    row.get("run_id"),
                    payload.get("signal_id") if "signal_id" in payload else row.get("signal_id"),
                    payload.get("candidate_id") if "candidate_id" in payload else row.get("candidate_id"),
                    payload.get("condition_id") if "condition_id" in payload else row.get("condition_id"),
                    payload.get("edge") if "edge" in payload else row.get("edge"),
                    payload.get("ev") if "ev" in payload else row.get("ev"),
                    payload.get("ev_after_spread") if "ev_after_spread" in payload else row.get("ev_after_spread"),
                    payload.get("true_probability") if "true_probability" in payload else row.get("true_probability"),
                    payload.get("volatility_regime") if "volatility_regime" in payload else row.get("volatility_regime"),
                    payload.get("trend_regime") if "trend_regime" in payload else row.get("trend_regime"),
                    str(decision_root / "2026-06-21.jsonl"),
                    1,
                ),
            )
        conn.commit()
    finally:
        conn.close()
    source_files = []
    for path in sorted(decision_root.glob("*.jsonl")):
        stat = path.stat()
        source_files.append({"filename": str(path), "size_bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    (index_root / "decision_log_slim_manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "decision_log_slim_index.v1",
                "created_at_utc": "2026-06-21T00:00:00Z",
                "decision_log_root": str(decision_root),
                "files_indexed": len(source_files),
                "rows_seen": len(rows),
                "rows_inserted": len(rows),
                "malformed_rows": 0,
                "sqlite_path": "decision_log_slim.sqlite",
                "source_files": source_files,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return index_root


def test_join_by_signal_id(tmp_path: Path) -> None:
    execution_root, trade_root, decision_root, output_dir = _write_basic_fixture(tmp_path)

    report = build_joined_records(execution_root, trade_root, decision_root, output_dir, max_join_seconds=120)

    rows, disk_report = _read_output(output_dir)
    assert report == disk_report
    assert len(rows) == 1
    assert rows[0]["join_status"] == "JOINED_SIGNAL_ID"
    assert rows[0]["edge"] == 0.07
    assert rows[0]["execution_pnl_5_share_model"] == 0.30
    assert disk_report["joined_closes"] == 1


def test_raw_field_extractor_extracts_run_id_from_compact_json() -> None:
    line = '{"run_id":"run_1","payload":{"signal_id":"signal_1"}}'

    assert extract_json_string_field(line, "run_id") == "run_1"


def test_raw_field_extractor_extracts_run_id_from_spaced_json() -> None:
    line = '{ "event_type": "decision", "run_id" : "run spaced" , "payload": {} }'

    assert extract_json_string_field(line, "run_id") == "run spaced"


def test_raw_field_extractor_returns_none_for_missing_field() -> None:
    assert extract_json_string_field('{"payload":{"signal_id":"signal_1"}}', "run_id") is None


def test_join_by_candidate_id_when_signal_missing(tmp_path: Path) -> None:
    decision = _decision_row(signal_id=None, candidate_id="candidate_1")
    execution_root, trade_root, decision_root, output_dir = _write_basic_fixture(
        tmp_path,
        decision=decision,
        open_payload={"signal_id": None},
        close_payload={"signal_id": None},
    )

    build_joined_records(execution_root, trade_root, decision_root, output_dir, max_join_seconds=120)

    rows, _ = _read_output(output_dir)
    assert rows[0]["join_status"] == "JOINED_CANDIDATE_ID"


def test_fallback_nearest_timestamp_join(tmp_path: Path) -> None:
    decision = _decision_row(signal_id=None, candidate_id=None, timestamp="2026-06-21T00:01:00Z")
    execution_root, trade_root, decision_root, output_dir = _write_basic_fixture(
        tmp_path,
        decision=decision,
        open_payload={"signal_id": None, "candidate_id": None},
        close_payload={"signal_id": None, "candidate_id": None},
    )

    build_joined_records(execution_root, trade_root, decision_root, output_dir, max_join_seconds=120)

    rows, _ = _read_output(output_dir)
    assert rows[0]["join_status"] == "JOINED_NEAREST_CONDITION"
    assert rows[0]["join_offset_seconds"] == 60.0


def test_nearest_timestamp_outside_window_unjoined(tmp_path: Path) -> None:
    decision = _decision_row(signal_id=None, candidate_id=None, timestamp="2026-06-21T00:05:00Z")
    execution_root, trade_root, decision_root, output_dir = _write_basic_fixture(
        tmp_path,
        decision=decision,
        open_payload={"signal_id": None, "candidate_id": None},
        close_payload={"signal_id": None, "candidate_id": None},
    )

    build_joined_records(execution_root, trade_root, decision_root, output_dir, max_join_seconds=120)

    rows, report = _read_output(output_dir)
    assert rows[0]["join_status"] == "JOINED_TRADE_OPEN_ONLY"
    assert report["missing_edge_count"] == 1


def test_ambiguous_nearest_timestamp_join(tmp_path: Path) -> None:
    execution_root, trade_root, decision_root, output_dir = _fixture_roots(tmp_path)
    trade_file = trade_root / "2026-06-21.jsonl"
    hashes = _write_jsonl(
        trade_file,
        [
            _trade_row("trade_open", timestamp="2026-06-21T00:00:00Z", signal_id=None, candidate_id=None),
            _trade_row("trade_close", timestamp="2026-06-21T00:00:30Z", signal_id=None, candidate_id=None),
        ],
    )
    _write_jsonl(execution_root / "journals" / "trade" / "2026-06-21.jsonl", [_execution_close(trade_file, hashes[1])])
    _write_jsonl(
        decision_root / "2026-06-21.jsonl",
        [
            _decision_row(signal_id=None, candidate_id=None, timestamp="2026-06-20T23:59:30Z"),
            _decision_row(signal_id=None, candidate_id=None, timestamp="2026-06-21T00:00:30Z"),
        ],
    )

    build_joined_records(execution_root, trade_root, decision_root, output_dir, max_join_seconds=120)

    rows, report = _read_output(output_dir)
    assert rows[0]["join_status"] == "AMBIGUOUS_DECISION_JOIN"
    assert report["ambiguous_join_count"] == 1


def test_unjoined_close_when_source_close_missing(tmp_path: Path) -> None:
    execution_root, trade_root, decision_root, output_dir = _fixture_roots(tmp_path)
    missing_source = trade_root / "missing.jsonl"
    _write_jsonl(execution_root / "journals" / "trade" / "2026-06-21.jsonl", [_execution_close(missing_source, "0" * 64)])
    _write_jsonl(decision_root / "2026-06-21.jsonl", [_decision_row()])

    build_joined_records(execution_root, trade_root, decision_root, output_dir)

    rows, report = _read_output(output_dir)
    assert rows[0]["join_status"] == "UNJOINED_SOURCE_CLOSE_MISSING"
    assert report["unjoined_closes"] == 1


def test_unjoined_close_when_source_open_missing(tmp_path: Path) -> None:
    execution_root, trade_root, decision_root, output_dir = _fixture_roots(tmp_path)
    trade_file = trade_root / "2026-06-21.jsonl"
    hashes = _write_jsonl(trade_file, [_trade_row("trade_close")])
    _write_jsonl(execution_root / "journals" / "trade" / "2026-06-21.jsonl", [_execution_close(trade_file, hashes[0], source_line=1)])
    _write_jsonl(decision_root / "2026-06-21.jsonl", [_decision_row()])

    build_joined_records(execution_root, trade_root, decision_root, output_dir)

    rows, _ = _read_output(output_dir)
    assert rows[0]["join_status"] == "UNJOINED_SOURCE_OPEN_MISSING"


def test_missing_metadata_counts(tmp_path: Path) -> None:
    decision = _decision_row(edge=None, ev=None, volatility_regime=None, trend_regime=None, true_probability=None)
    execution_root, trade_root, decision_root, output_dir = _write_basic_fixture(tmp_path, decision=decision)

    build_joined_records(execution_root, trade_root, decision_root, output_dir)

    _, report = _read_output(output_dir)
    assert report["missing_edge_count"] == 1
    assert report["missing_ev_count"] == 1
    assert report["missing_volatility_count"] == 1
    assert report["missing_trend_count"] == 1
    assert report["missing_true_probability_count"] == 1


def test_scratch_only_output_guard(tmp_path: Path) -> None:
    execution_root, trade_root, decision_root, _ = _write_basic_fixture(tmp_path)
    unsafe_output = tmp_path / "runtime" / "joined_records"

    with pytest.raises(ValueError, match="outside scratch"):
        build_joined_records(execution_root, trade_root, decision_root, unsafe_output)

    assert not unsafe_output.exists()
    assert is_safe_scratch_path(tmp_path / "scratch" / "ok")


def test_jsonl_output_schema(tmp_path: Path) -> None:
    execution_root, trade_root, decision_root, output_dir = _write_basic_fixture(tmp_path)

    build_joined_records(execution_root, trade_root, decision_root, output_dir)

    rows, _ = _read_output(output_dir)
    required = {
        "timestamp_utc",
        "run_id",
        "source_file",
        "source_line",
        "asset",
        "market_slug",
        "side",
        "outcome",
        "edge",
        "ev",
        "ev_after_spread",
        "true_probability",
        "volatility_regime",
        "trend_regime",
        "execution_pnl_5_share_model",
        "execution_entry_price",
        "execution_exit_price",
        "execution_shares",
        "historical_position_uid",
        "execution_position_id",
        "signal_id",
        "join_status",
        "join_offset_seconds",
    }
    assert required.issubset(rows[0])


def test_source_hash_mismatch_reported(tmp_path: Path) -> None:
    execution_root, trade_root, decision_root, output_dir = _fixture_roots(tmp_path)
    trade_file = trade_root / "2026-06-21.jsonl"
    _write_jsonl(trade_file, [_trade_row("trade_open"), _trade_row("trade_close")])
    _write_jsonl(execution_root / "journals" / "trade" / "2026-06-21.jsonl", [_execution_close(trade_file, "1" * 64)])
    _write_jsonl(decision_root / "2026-06-21.jsonl", [_decision_row()])

    build_joined_records(execution_root, trade_root, decision_root, output_dir)
    rows, report = _read_output(output_dir)

    assert rows[0]["join_status"] == "SOURCE_HASH_MISMATCH"
    assert report["source_hash_mismatch_count"] == 1

    with pytest.raises(ValueError, match="source hash mismatch"):
        build_joined_records(execution_root, trade_root, decision_root, tmp_path / "scratch" / "strict", fail_on_source_hash_mismatch=True)


def test_no_nested_close_decision_loop_behavior(tmp_path: Path) -> None:
    execution_root, trade_root, decision_root, output_dir = _write_basic_fixture(tmp_path)
    noise = [
        _decision_row(run_id=f"noise_{i}", signal_id=f"noise_signal_{i}", condition_id=f"noise_cond_{i}")
        for i in range(500)
    ]
    _write_jsonl(decision_root / "noise.jsonl", noise)

    build_joined_records(execution_root, trade_root, decision_root, output_dir)

    rows, report = _read_output(output_dir)
    assert rows[0]["join_status"] == "JOINED_SIGNAL_ID"
    assert report["total_closes"] == 1
    assert report["decision_rows_retained"] == 1
    assert report["decision_rows_skipped_run_id"] == 500
    assert report["required_run_id_count"] == 1


def test_irrelevant_decision_rows_are_not_retained(tmp_path: Path) -> None:
    execution_root, trade_root, decision_root, output_dir = _write_basic_fixture(tmp_path)
    _write_jsonl(
        decision_root / "irrelevant_same_run.jsonl",
        [
            _decision_row(signal_id="other_signal", candidate_id="other_candidate", condition_id="other_cond"),
            _decision_row(signal_id=None, candidate_id=None, condition_id="other_cond"),
        ],
    )

    build_joined_records(execution_root, trade_root, decision_root, output_dir)

    rows, report = _read_output(output_dir)
    assert rows[0]["join_status"] == "JOINED_SIGNAL_ID"
    assert report["decision_rows_retained"] == 1
    assert report["decision_rows_skipped_key"] == 2


def test_unmatched_run_id_lines_are_not_parsed(tmp_path: Path) -> None:
    execution_root, trade_root, decision_root, output_dir = _write_basic_fixture(tmp_path)
    with (decision_root / "unmatched_run_invalid.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        handle.write('{"run_id":"noise_run","payload":{"condition_id":"cond_1"}\n')

    build_joined_records(execution_root, trade_root, decision_root, output_dir)

    _, report = _read_output(output_dir)
    assert report["decision_rows_parsed"] == 1
    assert report["decision_rows_retained"] == 1


def test_progress_sidecar_is_written_under_scratch_output(tmp_path: Path) -> None:
    execution_root, trade_root, decision_root, output_dir = _write_basic_fixture(tmp_path)

    build_joined_records(
        execution_root,
        trade_root,
        decision_root,
        output_dir,
        progress_every_rows=1,
    )

    progress_path = output_dir / "joined_records_progress.json"
    progress = json.loads(progress_path.read_text(encoding="utf-8"))
    assert progress_path.exists()
    assert output_dir in progress_path.parents
    assert progress["phase"] == "decision_scan_complete"
    assert progress["files_processed"] == 1
    assert progress["decision_rows_seen"] == 1
    assert progress["decision_rows_retained"] == 1


def test_decision_index_matches_required_condition_when_signal_and_candidate_missing(tmp_path: Path) -> None:
    decision = _decision_row(signal_id=None, candidate_id=None, timestamp="2026-06-21T00:01:00Z")
    execution_root, trade_root, decision_root, output_dir = _write_basic_fixture(
        tmp_path,
        decision=decision,
        open_payload={"signal_id": None, "candidate_id": None},
        close_payload={"signal_id": None, "candidate_id": None},
    )
    _write_jsonl(
        decision_root / "same_run_noise.jsonl",
        [_decision_row(signal_id=None, candidate_id=None, condition_id="other_cond")],
    )

    build_joined_records(execution_root, trade_root, decision_root, output_dir)

    rows, report = _read_output(output_dir)
    assert rows[0]["join_status"] == "JOINED_NEAREST_CONDITION"
    assert report["decision_rows_retained"] == 1
    assert report["required_condition_id_count"] == 1


def test_max_decision_rows_loaded_guard_triggers(tmp_path: Path) -> None:
    execution_root, trade_root, decision_root, output_dir = _write_basic_fixture(tmp_path)

    with pytest.raises(ValueError, match="max_decision_rows_loaded exceeded"):
        build_joined_records(
            execution_root,
            trade_root,
            decision_root,
            output_dir,
            max_decision_rows_loaded=0,
        )

    assert not (output_dir / "joined_records.jsonl").exists()


def test_large_irrelevant_decision_fixture_remains_low_retention(tmp_path: Path) -> None:
    execution_root, trade_root, decision_root, output_dir = _write_basic_fixture(tmp_path)
    _write_jsonl(
        decision_root / "large_irrelevant.jsonl",
        [
            _decision_row(run_id=f"noise_{idx}", signal_id=f"noise_signal_{idx}", condition_id=f"noise_cond_{idx}")
            for idx in range(1000)
        ],
    )

    build_joined_records(execution_root, trade_root, decision_root, output_dir)

    _, report = _read_output(output_dir)
    assert report["decision_rows_seen"] == 1001
    assert report["decision_rows_parsed"] == 1
    assert report["decision_rows_retained"] == 1
    assert report["decision_retention_rate"] == pytest.approx(1.0)


def test_empty_decision_requirements_do_not_parse_decision_log(tmp_path: Path) -> None:
    execution_root, trade_root, decision_root, output_dir = _fixture_roots(tmp_path)
    missing_source = trade_root / "missing.jsonl"
    _write_jsonl(execution_root / "journals" / "trade" / "2026-06-21.jsonl", [_execution_close(missing_source, "0" * 64)])
    _write_jsonl(decision_root / "2026-06-21.jsonl", [_decision_row(), _decision_row(run_id="noise_run")])

    build_joined_records(execution_root, trade_root, decision_root, output_dir)

    _, report = _read_output(output_dir)
    assert report["decision_rows_seen"] == 2
    assert report["decision_rows_parsed"] == 0
    assert report["decision_rows_retained"] == 0


def test_shadow_filter_evaluator_compatibility(tmp_path: Path) -> None:
    execution_root, trade_root, decision_root, output_dir = _write_basic_fixture(tmp_path)
    shadow_output = Path("scratch") / f"test_shadow_filter_evaluator_{tmp_path.name}"
    if shadow_output.exists():
        shutil.rmtree(shadow_output)

    build_joined_records(execution_root, trade_root, decision_root, output_dir)
    try:
        shadow_filter_evaluator.process_file(str(output_dir / "joined_records.jsonl"), str(shadow_output), "block_edge_lt_005_shadow")

        summary = json.loads((shadow_output / "shadow_filter_summary.json").read_text(encoding="utf-8"))
        assert summary["block_edge_lt_005_shadow"]["candidates_evaluated"] == 1
        assert summary["block_edge_lt_005_shadow"]["candidates_passed"] == 1
    finally:
        if shadow_output.exists():
            shutil.rmtree(shadow_output)


def test_cli_writes_expected_outputs(tmp_path: Path) -> None:
    execution_root, trade_root, decision_root, output_dir = _write_basic_fixture(tmp_path)

    result = main(
        [
            "--execution-journal-root",
            str(execution_root),
            "--trade-journal-root",
            str(trade_root),
            "--decision-log-root",
            str(decision_root),
            "--output-dir",
            str(output_dir),
            "--max-join-seconds",
            "120",
        ]
    )

    assert result == 0
    assert (output_dir / "joined_records.jsonl").exists()
    assert (output_dir / "joined_records_report.json").exists()
    assert not (output_dir / "joined_records.jsonl.tmp").exists()
    assert not (output_dir / "joined_records_report.json.tmp").exists()


def test_slim_index_lookup_by_signal_id(tmp_path: Path) -> None:
    execution_root, trade_root, decision_root, output_dir = _write_basic_fixture(tmp_path)
    index_root = _write_slim_index(tmp_path / "scratch" / "decision_slim" / "output", decision_root, [_decision_row()])

    build_joined_records(execution_root, trade_root, decision_root, output_dir, decision_slim_index_root=index_root)

    rows, report = _read_output(output_dir)
    assert rows[0]["join_status"] == "JOINED_SIGNAL_ID"
    assert rows[0]["edge"] == 0.07
    assert report["decision_source_mode"] == "SLIM_INDEX"
    assert report["decision_rows_retained"] == 1


def test_slim_index_lookup_by_candidate_id(tmp_path: Path) -> None:
    decision = _decision_row(signal_id=None, candidate_id="candidate_1")
    execution_root, trade_root, decision_root, output_dir = _write_basic_fixture(
        tmp_path,
        decision=decision,
        open_payload={"signal_id": None},
        close_payload={"signal_id": None},
    )
    index_root = _write_slim_index(tmp_path / "scratch" / "decision_slim" / "output", decision_root, [decision])

    build_joined_records(execution_root, trade_root, decision_root, output_dir, decision_slim_index_root=index_root)

    rows, report = _read_output(output_dir)
    assert rows[0]["join_status"] == "JOINED_CANDIDATE_ID"
    assert report["decision_source_mode"] == "SLIM_INDEX"


def test_slim_index_lookup_by_condition_id_nearest_timestamp(tmp_path: Path) -> None:
    decision = _decision_row(signal_id=None, candidate_id=None, timestamp="2026-06-21T00:01:00Z")
    execution_root, trade_root, decision_root, output_dir = _write_basic_fixture(
        tmp_path,
        decision=decision,
        open_payload={"signal_id": None, "candidate_id": None},
        close_payload={"signal_id": None, "candidate_id": None},
    )
    index_root = _write_slim_index(tmp_path / "scratch" / "decision_slim" / "output", decision_root, [decision])

    build_joined_records(execution_root, trade_root, decision_root, output_dir, decision_slim_index_root=index_root)

    rows, report = _read_output(output_dir)
    assert rows[0]["join_status"] == "JOINED_NEAREST_CONDITION"
    assert rows[0]["join_offset_seconds"] == 60.0
    assert report["decision_source_mode"] == "SLIM_INDEX"


def test_slim_index_missing_sqlite_fails_closed(tmp_path: Path) -> None:
    execution_root, trade_root, decision_root, output_dir = _write_basic_fixture(tmp_path)
    index_root = _write_slim_index(tmp_path / "scratch" / "decision_slim" / "output", decision_root, [_decision_row()])
    (index_root / "decision_log_slim.sqlite").unlink()

    with pytest.raises(ValueError, match="decision_log_slim.sqlite"):
        build_joined_records(execution_root, trade_root, decision_root, output_dir, decision_slim_index_root=index_root)


def test_slim_index_missing_manifest_fails_closed(tmp_path: Path) -> None:
    execution_root, trade_root, decision_root, output_dir = _write_basic_fixture(tmp_path)
    index_root = _write_slim_index(tmp_path / "scratch" / "decision_slim" / "output", decision_root, [_decision_row()])
    (index_root / "decision_log_slim_manifest.json").unlink()

    with pytest.raises(ValueError, match="decision_log_slim_manifest.json"):
        build_joined_records(execution_root, trade_root, decision_root, output_dir, decision_slim_index_root=index_root)


def test_slim_index_manifest_schema_mismatch_fails_closed(tmp_path: Path) -> None:
    execution_root, trade_root, decision_root, output_dir = _write_basic_fixture(tmp_path)
    index_root = _write_slim_index(tmp_path / "scratch" / "decision_slim" / "output", decision_root, [_decision_row()])
    manifest_path = index_root / "decision_log_slim_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schema_version"] = "wrong"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="schema_version"):
        build_joined_records(execution_root, trade_root, decision_root, output_dir, decision_slim_index_root=index_root)


def test_slim_index_output_matches_jsonl_mode_for_identical_fixture(tmp_path: Path) -> None:
    execution_root, trade_root, decision_root, raw_output = _write_basic_fixture(tmp_path)
    slim_output = tmp_path / "scratch" / "joined_records_builder" / "slim_output"
    index_root = _write_slim_index(tmp_path / "scratch" / "decision_slim" / "output", decision_root, [_decision_row()])

    build_joined_records(execution_root, trade_root, decision_root, raw_output, max_join_seconds=120)
    build_joined_records(execution_root, trade_root, decision_root, slim_output, max_join_seconds=120, decision_slim_index_root=index_root)

    raw_rows, raw_report = _read_output(raw_output)
    slim_rows, slim_report = _read_output(slim_output)
    assert slim_rows == raw_rows
    assert slim_report["join_status_counts"] == raw_report["join_status_counts"]
    assert slim_report["joined_closes"] == raw_report["joined_closes"]
    assert slim_report["missing_edge_count"] == raw_report["missing_edge_count"]
    assert slim_report["decision_source_mode"] == "SLIM_INDEX"


def test_no_forbidden_imports() -> None:
    import tools.joined_records_builder as target_module
    source = Path(target_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")

    forbidden = (
        "polymarket.trader",
        "polymarket.order_manager",
        "utils.risk_manager",
        "polymarket.position_sizing",
        "main",
        "wallet",
        "client",
        "risk_manager",
        "order_manager",
    )
    assert all(item not in imported for item in forbidden)
