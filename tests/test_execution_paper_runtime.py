from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.execution_paper_runtime import (
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_SOURCE_ROOT,
    SCHEMA_VERSION,
    CheckpointError,
    DuplicateConflictError,
    DedupeIndex,
    PathIsolationError,
    ReconciliationError,
    SchemaValidationError,
    append_jsonl_event,
    read_checkpoint,
    reconcile_events,
    stream_source_journal,
    validate_checkpoint_source_hash,
    validate_event,
    write_checkpoint,
    main,
)


def _base_event(event_type: str = "execution_paper_open", **payload: object) -> dict:
    event = {
        "schema_version": SCHEMA_VERSION,
        "event_type": event_type,
        "timestamp_utc": "2026-06-20T00:00:00Z",
        "execution_run_id": "execution_run_1",
        "source_runtime_mode": "SIGNAL_MODE",
        "source_run_id": "signal_run_1",
        "source_event_type": "trade_open",
        "source_file": "trade_journal/2026-06-20.jsonl",
        "source_line": 1,
        "source_event_sha256": "a" * 64,
        "source_replay_key": "condition|epoch|ETH|YES|token",
        "condition_id": "0xabc",
        "epoch_start_ts": 123,
        "market_slug": "eth-updown-5m-123",
        "asset": "ETH",
        "side": "YES",
        "lifecycle_phase": "OPENING_SCAN",
        "execution_track": "5_share",
        "execution_bankroll_start": 250.0,
        "execution_entry_price": 0.52,
        "execution_shares": 5.0,
        "execution_notional": 2.6,
        "entry_bid_size": 20.0,
        "entry_ask_size": 20.0,
        "entry_spread": 0.02,
        "entry_quote_age_ms": 100,
        "execution_liquidity_pass": True,
        "execution_position_id": "ep_1",
        "signal_entry_price": 0.52,
        "signal_pnl_reference": 0.01,
    }
    event.update(payload)
    return event


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def test_schema_validation_passes_for_open_event() -> None:
    assert validate_event(_base_event()) is True


def test_schema_validation_fails_closed_when_required_field_missing() -> None:
    event = _base_event()
    del event["execution_run_id"]

    with pytest.raises(SchemaValidationError, match="execution_run_id"):
        validate_event(event)


def test_schema_validation_allows_unknown_optional_field() -> None:
    event = _base_event(extra_future_field="allowed")

    assert validate_event(event) is True


def test_writer_rejects_path_outside_execution_paper_root(tmp_path: Path) -> None:
    outside = tmp_path / "other"

    with pytest.raises(PathIsolationError):
        append_jsonl_event(outside, "trade", _base_event())


def test_writer_appends_without_overwriting(tmp_path: Path) -> None:
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT
    event = _base_event()

    path = append_jsonl_event(output_root, "trade", event)
    append_jsonl_event(output_root, "trade", {**event, "execution_position_id": "ep_2"})

    rows = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(rows) == 2
    assert json.loads(rows[0])["execution_position_id"] == "ep_1"
    assert json.loads(rows[1])["execution_position_id"] == "ep_2"


def test_checkpoint_write_and_read_round_trip(tmp_path: Path) -> None:
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT
    checkpoint = {
        "execution_run_id": "execution_run_1",
        "last_processed_trade": "trade_1",
        "last_processed_timestamp": "2026-06-20T00:00:00Z",
        "last_processed_source_file": "source.jsonl",
        "last_processed_source_line": 7,
        "last_processed_source_sha256": "b" * 64,
    }

    path = write_checkpoint(output_root, "execution_run_1", checkpoint)

    assert read_checkpoint(path)["last_processed_trade"] == "trade_1"
    assert path.read_text(encoding="utf-8").endswith("\n")


def test_checkpoint_hash_mismatch_fails(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    _write_jsonl(source, [{"a": 1}])
    row = next(stream_source_journal(source))
    checkpoint = {
        "last_processed_source_file": str(source),
        "last_processed_source_line": row.source_line,
        "last_processed_source_sha256": "c" * 64,
    }

    with pytest.raises(CheckpointError, match="hash mismatch"):
        validate_checkpoint_source_hash(checkpoint)


def test_streaming_reader_yields_line_hashes(tmp_path: Path) -> None:
    source = tmp_path / "trade_journal" / "2026-06-20.jsonl"
    rows = [{"event_type": "trade_open", "payload": {"paper_trade_replay_key": "k1"}}]
    _write_jsonl(source, rows)

    result = list(stream_source_journal(source))

    assert len(result) == 1
    assert result[0].source_file == source.resolve()
    assert result[0].source_line == 1
    assert len(result[0].source_event_sha256) == 64
    assert result[0].parsed_json == rows[0]


def test_dedupe_identical_duplicate_skips_but_conflict_fails() -> None:
    index = DedupeIndex()
    event = _base_event()

    assert index.register(event) == "new"
    assert index.register(dict(event)) == "duplicate"
    with pytest.raises(DuplicateConflictError):
        index.register({**event, "execution_notional": 3.0})


def test_reconciliation_orphan_close_fails() -> None:
    close = {
        **_base_event(event_type="execution_paper_close"),
        "execution_exit_price": 0.6,
        "execution_pnl": 0.4,
        "execution_exit_reason": "take_profit",
    }

    with pytest.raises(ReconciliationError, match="orphan_close"):
        reconcile_events([close])


def test_dry_run_writes_only_under_tmp_output_root(tmp_path: Path) -> None:
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT
    source_root = tmp_path / DEFAULT_SOURCE_ROOT
    signal_categories = ("trade_journal", "decision_log", "execution_log", "path_truth")
    before_signal_files = {
        category: set((source_root / category).rglob("*")) if (source_root / category).exists() else set()
        for category in signal_categories
    }

    result = main(
        [
            "--dry-run",
            "--max-events",
            "10",
            "--source-root",
            str(source_root),
            "--output-root",
            str(output_root),
        ]
    )

    assert result == 0
    assert output_root.exists()
    assert list((output_root / "journals").rglob("*.jsonl"))
    assert list((output_root / "checkpoints").rglob("*.json"))
    assert list((output_root / "reports").rglob("*validation.json"))
    after_signal_files = {
        category: set((source_root / category).rglob("*")) if (source_root / category).exists() else set()
        for category in signal_categories
    }
    assert before_signal_files == after_signal_files
    assert all(path.resolve().is_relative_to(output_root.resolve()) for path in output_root.rglob("*"))


def test_no_forbidden_imports() -> None:
    source = Path("tools/execution_paper_runtime.py").read_text(encoding="utf-8")

    forbidden = (
        "polymarket.trader",
        "polymarket.order_manager",
        "utils.risk_manager",
        "polymarket.position_sizing",
    )
    assert all(item not in source for item in forbidden)


def test_trade_open_emits_execution_paper_open(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    open_event = {
        "event_type": "trade_open",
        "mode": "paper",
        "payload": {
            "condition_id": "0xabc",
            "ticker": "ETH",
            "outcome": "YES",
            "entry_price": 0.52,
            "position_id": "pos_1",
        },
        "run_id": "run_1",
        "timestamp_utc": "2026-06-20T00:00:00Z"
    }
    _write_jsonl(source_root / "trade_journal" / "2026-06-20.jsonl", [open_event])

    from tools.execution_paper_runtime import run_replay
    report = run_replay(
        source_root=source_root,
        output_root=output_root,
        max_events=10,
        track="5_share",
        starting_bankroll=250.0,
    )

    assert report["status"] == "PASS"
    assert report["processed_source_events"] == 1
    assert report["rejected_events"] == 0

    journal_files = list((output_root / "journals").rglob("*.jsonl"))
    assert len(journal_files) >= 1

    trade_journal = next(f for f in journal_files if f.parent.name != "runtime")
    rows = [json.loads(line) for line in trade_journal.read_text(encoding="utf-8").splitlines()]

    assert len(rows) == 1
    assert rows[0]["event_type"] == "execution_paper_open"
    assert rows[0]["execution_position_id"] == "ep_pos_1"
    assert rows[0]["execution_shares"] == 5.0
    assert rows[0]["execution_bankroll_start"] == 250.0


def test_trade_close_emits_execution_paper_close(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    open_event = {
        "event_type": "trade_open",
        "mode": "paper",
        "payload": {
            "condition_id": "0xabc",
            "ticker": "ETH",
            "outcome": "YES",
            "entry_price": 0.52,
            "position_id": "pos_1",
        },
        "run_id": "run_1",
        "timestamp_utc": "2026-06-20T00:00:00Z"
    }
    close_event = {
        "event_type": "trade_close",
        "mode": "paper",
        "payload": {
            "condition_id": "0xabc",
            "ticker": "ETH",
            "outcome": "YES",
            "exit_price": 0.60,
            "position_id": "pos_1",
            "reason": "take_profit",
            "pnl": 0.40,
        },
        "run_id": "run_1",
        "timestamp_utc": "2026-06-20T00:05:00Z"
    }
    _write_jsonl(source_root / "trade_journal" / "2026-06-20.jsonl", [open_event, close_event])

    from tools.execution_paper_runtime import run_replay
    report = run_replay(
        source_root=source_root,
        output_root=output_root,
        max_events=10,
    )

    assert report["status"] == "PASS"
    assert report["processed_source_events"] == 2

    journal_files = list((output_root / "journals").rglob("*.jsonl"))
    trade_journal = next(f for f in journal_files if f.parent.name != "runtime")
    rows = [json.loads(line) for line in trade_journal.read_text(encoding="utf-8").splitlines()]

    assert len(rows) == 2
    assert rows[0]["event_type"] == "execution_paper_open"
    assert rows[1]["event_type"] == "execution_paper_close"
    assert rows[1]["execution_position_id"] == "ep_pos_1"
    assert rows[1]["execution_pnl"] == 0.40


def test_missing_required_field_emits_reject(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    open_event = {
        "event_type": "trade_open",
        "mode": "paper",
        "payload": {
            "condition_id": "0xabc",
            "outcome": "YES",
            "entry_price": 0.52,
            "position_id": "pos_1",
        },
        "run_id": "run_1",
        "timestamp_utc": "2026-06-20T00:00:00Z"
    }
    _write_jsonl(source_root / "trade_journal" / "2026-06-20.jsonl", [open_event])

    from tools.execution_paper_runtime import run_replay
    report = run_replay(
        source_root=source_root,
        output_root=output_root,
        max_events=10,
    )

    assert report["processed_source_events"] == 1
    assert report["rejected_events"] == 1

    journal_files = list((output_root / "journals").rglob("*.jsonl"))
    trade_journal = next(f for f in journal_files if f.parent.name != "runtime")
    rows = [json.loads(line) for line in trade_journal.read_text(encoding="utf-8").splitlines()]

    assert len(rows) == 1
    assert rows[0]["event_type"] == "execution_paper_reject"


def test_checkpoint_after_source_processing(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    open_event = {
        "event_type": "trade_open",
        "mode": "paper",
        "payload": {
            "condition_id": "0xabc",
            "ticker": "ETH",
            "outcome": "YES",
            "entry_price": 0.52,
            "position_id": "pos_1",
        },
        "run_id": "run_1",
        "timestamp_utc": "2026-06-20T00:00:00Z"
    }
    _write_jsonl(source_root / "trade_journal" / "2026-06-20.jsonl", [open_event])

    from tools.execution_paper_runtime import run_replay
    report = run_replay(
        source_root=source_root,
        output_root=output_root,
        max_events=10,
    )

    checkpoint_path = Path(report["checkpoint_path"])
    assert checkpoint_path.exists()

    checkpoint = read_checkpoint(checkpoint_path)
    assert checkpoint["processed_event_count"] == 1
    assert checkpoint["last_processed_source_line"] == 1


def test_resume_skips_already_processed_event(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    event1 = {
        "event_type": "trade_open",
        "mode": "paper",
        "payload": {
            "condition_id": "0xabc",
            "ticker": "ETH",
            "outcome": "YES",
            "entry_price": 0.52,
            "position_id": "pos_1",
        },
        "run_id": "run_1",
        "timestamp_utc": "2026-06-20T00:00:00Z"
    }
    event2 = {
        "event_type": "trade_open",
        "mode": "paper",
        "payload": {
            "condition_id": "0xdef",
            "ticker": "BTC",
            "outcome": "NO",
            "entry_price": 0.60,
            "position_id": "pos_2",
        },
        "run_id": "run_1",
        "timestamp_utc": "2026-06-20T00:05:00Z"
    }
    source_file = source_root / "trade_journal" / "2026-06-20.jsonl"
    _write_jsonl(source_file, [event1, event2])

    from tools.execution_paper_runtime import run_replay
    report1 = run_replay(
        source_root=source_root,
        output_root=output_root,
        max_events=1,
    )
    assert report1["processed_source_events"] == 1

    journal_files = list((output_root / "journals").rglob("*.jsonl"))
    trade_journal = next(f for f in journal_files if f.parent.name != "runtime")
    rows = [json.loads(line) for line in trade_journal.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["execution_position_id"] == "ep_pos_1"

    report2 = run_replay(
        source_root=source_root,
        output_root=output_root,
        max_events=10,
    )
    assert report2["processed_source_events"] == 2

    rows_after = [json.loads(line) for line in trade_journal.read_text(encoding="utf-8").splitlines()]
    assert len(rows_after) == 2
    assert rows_after[0]["execution_position_id"] == "ep_pos_1"
    assert rows_after[1]["execution_position_id"] == "ep_pos_2"


def test_reject_does_not_create_position(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    reject_event = {
        "event_type": "trade_open",
        "mode": "paper",
        "payload": {
            "condition_id": "0xabc",
            "outcome": "YES",
            "entry_price": 0.52,
            "position_id": "pos_1",
        },
        "run_id": "run_1",
        "timestamp_utc": "2026-06-20T00:00:00Z"
    }
    close_event = {
        "event_type": "trade_close",
        "mode": "paper",
        "payload": {
            "condition_id": "0xabc",
            "ticker": "ETH",
            "outcome": "YES",
            "exit_price": 0.60,
            "position_id": "pos_1",
            "reason": "take_profit",
            "pnl": 0.40,
        },
        "run_id": "run_1",
        "timestamp_utc": "2026-06-20T00:05:00Z"
    }
    _write_jsonl(source_root / "trade_journal" / "2026-06-20.jsonl", [reject_event, close_event])

    from tools.execution_paper_runtime import run_replay
    with pytest.raises(ReconciliationError, match="orphan_close"):
        run_replay(
            source_root=source_root,
            output_root=output_root,
            max_events=10,
        )


def test_cli_defaults_track_and_bankroll() -> None:
    from tools.execution_paper_runtime import _build_parser
    parser = _build_parser()
    args = parser.parse_args([])
    assert args.track == "5_share"
    assert args.starting_bankroll == 250.0


def test_validation_report_counts(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    open_event = {
        "event_type": "trade_open",
        "mode": "paper",
        "payload": {
            "condition_id": "0xabc",
            "ticker": "ETH",
            "outcome": "YES",
            "entry_price": 0.52,
            "position_id": "pos_1",
        },
        "run_id": "run_1",
        "timestamp_utc": "2026-06-20T00:00:00Z"
    }
    reject_event = {
        "event_type": "trade_open",
        "mode": "paper",
        "payload": {
            "ticker": "ETH",
            "outcome": "YES",
            "entry_price": 0.52,
            "position_id": "pos_2",
        },
        "run_id": "run_1",
        "timestamp_utc": "2026-06-20T00:05:00Z"
    }
    source_file = source_root / "trade_journal" / "2026-06-20.jsonl"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    with source_file.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(open_event) + "\n")
        handle.write("invalid_json_row\n")
        handle.write(json.dumps(reject_event) + "\n")

    from tools.execution_paper_runtime import run_replay
    report = run_replay(
        source_root=source_root,
        output_root=output_root,
        max_events=10,
    )

    assert report["processed_source_events"] == 3
    assert report["emitted_events"] == 4  # 1 started, 1 open, 1 reject, 1 stopped
    assert report["rejected_events"] == 1
    assert report["malformed_source_rows"] == 1
    assert report["skipped_duplicates"] == 0
    assert report["pnl_label"] == "signal_pnl_placeholder"
