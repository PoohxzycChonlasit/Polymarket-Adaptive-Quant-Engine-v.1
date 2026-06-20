from __future__ import annotations

import hashlib
import json
import ast
import shutil
from pathlib import Path

import pytest

from tools import shadow_filter_evaluator
from tools.joined_records_builder import build_joined_records, is_safe_scratch_path, main


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


def test_no_forbidden_imports() -> None:
    source = Path("tools/joined_records_builder.py").read_text(encoding="utf-8")
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
