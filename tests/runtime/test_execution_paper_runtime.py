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
    assert rows[0]["execution_notional"] == 2.6
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
    # Set dummy source pnl = 99.99 to verify it is NOT used.
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
            "pnl": 99.99,
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

    # open, close, equity snapshot = 3 rows
    assert len(rows) == 3
    assert rows[0]["event_type"] == "execution_paper_open"
    assert rows[1]["event_type"] == "execution_paper_close"
    assert rows[2]["event_type"] == "execution_paper_equity_snapshot"
    assert rows[1]["execution_position_id"] == "ep_pos_1"
    assert abs(rows[1]["execution_pnl"] - 0.40) < 1e-6
    assert rows[1]["execution_equity_before"] == 250.0
    assert abs(rows[1]["execution_equity_after"] - 250.40) < 1e-6
    assert abs(rows[1]["cumulative_execution_pnl"] - 0.40) < 1e-6


def test_missing_required_field_emits_reject(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    # condition_id missing -> reject
    open_event = {
        "event_type": "trade_open",
        "mode": "paper",
        "payload": {
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

    assert report["processed_source_events"] == 1
    assert report["rejected_events"] == 1

    journal_files = list((output_root / "journals").rglob("*.jsonl"))
    trade_journal = next(f for f in journal_files if f.parent.name != "runtime")
    rows = [json.loads(line) for line in trade_journal.read_text(encoding="utf-8").splitlines()]

    assert len(rows) == 1
    assert rows[0]["event_type"] == "execution_paper_reject"
    assert rows[0]["reject_reason"] == "missing_condition_id"


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

    # condition_id missing -> open rejects
    reject_event = {
        "event_type": "trade_open",
        "mode": "paper",
        "payload": {
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
    assert report["emitted_events"] == 4  # started, open, reject, stopped
    assert report["rejected_events"] == 1
    assert report["malformed_source_rows"] == 1
    assert report["skipped_duplicates"] == 0
    assert report["pnl_label"] == "execution_pnl_5_share_model"


def test_phase_c_price_rejects(tmp_path: Path) -> None:
    import shutil
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    # 1. Invalid entry price on open
    open_invalid_entry = {
        "event_type": "trade_open",
        "payload": {"condition_id": "0xabc", "ticker": "ETH", "outcome": "YES", "entry_price": "invalid", "position_id": "pos_1"},
        "timestamp_utc": "2026-06-20T00:00:00Z"
    }
    # 2. Missing entry price on open
    open_missing_entry = {
        "event_type": "trade_open",
        "payload": {"condition_id": "0xabc", "ticker": "ETH", "outcome": "YES", "position_id": "pos_2"},
        "timestamp_utc": "2026-06-20T00:01:00Z"
    }
    # 3. Valid open for close tests
    open_valid = {
        "event_type": "trade_open",
        "payload": {"condition_id": "0xabc", "ticker": "ETH", "outcome": "YES", "entry_price": 0.50, "position_id": "pos_3"},
        "timestamp_utc": "2026-06-20T00:02:00Z"
    }
    # 4. Missing exit price on close
    close_missing_exit = {
        "event_type": "trade_close",
        "payload": {"condition_id": "0xabc", "ticker": "ETH", "outcome": "YES", "position_id": "pos_3", "reason": "tp"},
        "timestamp_utc": "2026-06-20T00:03:00Z"
    }
    # 5. Invalid exit price on close
    close_invalid_exit = {
        "event_type": "trade_close",
        "payload": {"condition_id": "0xabc", "ticker": "ETH", "outcome": "YES", "exit_price": "invalid", "position_id": "pos_3", "reason": "tp"},
        "timestamp_utc": "2026-06-20T00:04:00Z"
    }

    from tools.execution_paper_runtime import run_replay

    _write_jsonl(source_root / "trade_journal" / "2026-06-20.jsonl", [open_invalid_entry])
    report = run_replay(source_root=source_root, output_root=output_root, max_events=10)
    assert report["rejected_events"] == 1
    shutil.rmtree(output_root)

    _write_jsonl(source_root / "trade_journal" / "2026-06-20.jsonl", [open_missing_entry])
    report = run_replay(source_root=source_root, output_root=output_root, max_events=10)
    assert report["rejected_events"] == 1
    shutil.rmtree(output_root)

    _write_jsonl(source_root / "trade_journal" / "2026-06-20.jsonl", [open_valid, close_missing_exit])
    report = run_replay(source_root=source_root, output_root=output_root, max_events=10)
    assert report["rejected_events"] == 1
    shutil.rmtree(output_root)

    _write_jsonl(source_root / "trade_journal" / "2026-06-20.jsonl", [open_valid, close_invalid_exit])
    report = run_replay(source_root=source_root, output_root=output_root, max_events=10)
    assert report["rejected_events"] == 1


def test_phase_c_equity_and_drawdown_tracking(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    # 3 trades:
    # Win 1: pnl = 0.50
    # Loss 2: pnl = -1.00
    # Win 3: pnl = 0.25
    events = [
        {"event_type": "trade_open", "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "entry_price": 0.50, "position_id": "p1"}, "timestamp_utc": "2026-06-20T00:00:00Z"},
        {"event_type": "trade_close", "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "exit_price": 0.60, "position_id": "p1", "reason": "tp"}, "timestamp_utc": "2026-06-20T00:01:00Z"},
        {"event_type": "trade_open", "payload": {"condition_id": "0x2", "ticker": "BTC", "outcome": "YES", "entry_price": 0.50, "position_id": "p2"}, "timestamp_utc": "2026-06-20T00:02:00Z"},
        {"event_type": "trade_close", "payload": {"condition_id": "0x2", "ticker": "BTC", "outcome": "YES", "exit_price": 0.30, "position_id": "p2", "reason": "sl"}, "timestamp_utc": "2026-06-20T00:03:00Z"},
        {"event_type": "trade_open", "payload": {"condition_id": "0x3", "ticker": "BTC", "outcome": "YES", "entry_price": 0.50, "position_id": "p3"}, "timestamp_utc": "2026-06-20T00:04:00Z"},
        {"event_type": "trade_close", "payload": {"condition_id": "0x3", "ticker": "BTC", "outcome": "YES", "exit_price": 0.55, "position_id": "p3", "reason": "tp"}, "timestamp_utc": "2026-06-20T00:05:00Z"},
    ]
    _write_jsonl(source_root / "trade_journal" / "2026-06-20.jsonl", events)

    from tools.execution_paper_runtime import run_replay
    report = run_replay(source_root=source_root, output_root=output_root, max_events=10, starting_bankroll=250.0)

    assert abs(report["execution_net_pnl"] - (-0.25)) < 1e-6
    assert abs(report["execution_gross_profit"] - 0.75) < 1e-6
    assert abs(report["execution_gross_loss"] - 1.00) < 1e-6
    assert report["execution_win_count"] == 2
    assert report["execution_loss_count"] == 1
    assert report["execution_flat_count"] == 0
    assert report["execution_closed_trade_count"] == 3
    assert abs(report["execution_wr"] - 2.0/3.0) < 1e-6
    assert abs(report["execution_pf"] - 0.75) < 1e-6
    assert abs(report["execution_max_dd"] - 1.00) < 1e-6
    assert abs(report["execution_max_dd_pct"] - (1.00 / 250.50) * 100.0) < 1e-6
    assert report["risk_of_ruin"] is False

    # Check snapshots & files
    journal_files = list((output_root / "journals").rglob("*.jsonl"))
    trade_journal = next(f for f in journal_files if f.parent.name != "runtime")
    rows = [json.loads(line) for line in trade_journal.read_text(encoding="utf-8").splitlines()]

    # 3 opens, 3 closes, 3 snapshots = 9 events
    assert len(rows) == 9

    closes = [r for r in rows if r["event_type"] == "execution_paper_close"]
    assert len(closes) == 3
    assert closes[0]["execution_equity_before"] == 250.0
    assert closes[0]["execution_equity_after"] == 250.50
    assert closes[0]["execution_drawdown"] == 0.0

    assert closes[1]["execution_equity_before"] == 250.50
    assert closes[1]["execution_equity_after"] == 249.50
    assert closes[1]["execution_drawdown"] == 1.00
    assert closes[1]["execution_max_drawdown"] == 1.00

    snaps = [r for r in rows if r["event_type"] == "execution_paper_equity_snapshot"]
    assert len(snaps) == 3
    assert snaps[1]["execution_equity"] == 249.50
    assert snaps[1]["execution_dd"] == 1.00
    assert snaps[1]["execution_max_dd"] == 1.00


def test_phase_c_risk_of_ruin_sticky(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    # bankroll = 5.0, threshold = 0.50
    # Trade 1: loses 4.75 -> ruined! (equity becomes 0.25 <= 0.50)
    # Trade 2: wins 2.00 -> stays ruined!
    events = [
        {"event_type": "trade_open", "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "entry_price": 0.95, "position_id": "p1"}, "timestamp_utc": "2026-06-20T00:00:00Z"},
        {"event_type": "trade_close", "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "exit_price": 0.0, "position_id": "p1", "reason": "sl"}, "timestamp_utc": "2026-06-20T00:01:00Z"},
        {"event_type": "trade_open", "payload": {"condition_id": "0x2", "ticker": "BTC", "outcome": "YES", "entry_price": 0.10, "position_id": "p2"}, "timestamp_utc": "2026-06-20T00:02:00Z"},
        {"event_type": "trade_close", "payload": {"condition_id": "0x2", "ticker": "BTC", "outcome": "YES", "exit_price": 0.50, "position_id": "p2", "reason": "tp"}, "timestamp_utc": "2026-06-20T00:03:00Z"},
    ]
    _write_jsonl(source_root / "trade_journal" / "2026-06-20.jsonl", events)

    from tools.execution_paper_runtime import run_replay
    report = run_replay(source_root=source_root, output_root=output_root, max_events=10, starting_bankroll=5.0)

    assert report["risk_of_ruin"] is True


def test_phase_c_pf_undefined_when_no_losses(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    # 1 win, 1 flat, 0 losses -> PF should be None
    events = [
        {"event_type": "trade_open", "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "entry_price": 0.50, "position_id": "p1"}, "timestamp_utc": "2026-06-20T00:00:00Z"},
        {"event_type": "trade_close", "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "exit_price": 0.60, "position_id": "p1", "reason": "tp"}, "timestamp_utc": "2026-06-20T00:01:00Z"},
        {"event_type": "trade_open", "payload": {"condition_id": "0x2", "ticker": "BTC", "outcome": "YES", "entry_price": 0.50, "position_id": "p2"}, "timestamp_utc": "2026-06-20T00:02:00Z"},
        {"event_type": "trade_close", "payload": {"condition_id": "0x2", "ticker": "BTC", "outcome": "YES", "exit_price": 0.50, "position_id": "p2", "reason": "flat"}, "timestamp_utc": "2026-06-20T00:03:00Z"},
    ]
    _write_jsonl(source_root / "trade_journal" / "2026-06-20.jsonl", events)

    from tools.execution_paper_runtime import run_replay
    report = run_replay(source_root=source_root, output_root=output_root, max_events=10)

    assert report["execution_pf"] is None
    assert report["execution_win_count"] == 1
    assert report["execution_flat_count"] == 1
    assert report["execution_loss_count"] == 0
    assert report["execution_wr"] == 1.0


def test_phase_c_rejects_do_not_affect_equity(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    # 1 win, 1 reject
    events = [
        {"event_type": "trade_open", "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "entry_price": 0.50, "position_id": "p1"}, "timestamp_utc": "2026-06-20T00:00:00Z"},
        {"event_type": "trade_close", "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "exit_price": 0.60, "position_id": "p1", "reason": "tp"}, "timestamp_utc": "2026-06-20T00:01:00Z"},
        # Reject on open (missing condition_id)
        {"event_type": "trade_open", "payload": {"ticker": "BTC", "outcome": "YES", "entry_price": 0.50, "position_id": "p2"}, "timestamp_utc": "2026-06-20T00:02:00Z"},
    ]
    _write_jsonl(source_root / "trade_journal" / "2026-06-20.jsonl", events)

    from tools.execution_paper_runtime import run_replay
    report = run_replay(source_root=source_root, output_root=output_root, max_events=10)

    assert report["rejected_events"] == 1
    assert abs(report["execution_net_pnl"] - 0.50) < 1e-6

    # Verify reject event contains correct running equity (250.50)
    journal_files = list((output_root / "journals").rglob("*.jsonl"))
    trade_journal = next(f for f in journal_files if f.parent.name != "runtime")
    rows = [json.loads(line) for line in trade_journal.read_text(encoding="utf-8").splitlines()]

    reject = next(r for r in rows if r["event_type"] == "execution_paper_reject")
    assert reject["execution_equity"] == 250.50


def test_phase_c_equity_consistency_check_failure(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    # 1. Create a dummy source file
    source_file = source_root / "trade_journal" / "2026-06-20.jsonl"
    _write_jsonl(source_file, [{"dummy": "row"}])

    # 2. Get hash of the first line
    for item in stream_source_journal(source_file):
        line_hash = item.source_event_sha256
        break

    # 3. Write a corrupted checkpoint
    checkpoint = {
        "execution_run_id": "corrupt_run",
        "checkpointed_at": "2026-06-20T00:00:00Z",
        "last_processed_trade": "t1",
        "last_processed_timestamp": "2026-06-20T00:00:00Z",
        "last_processed_source_file": str(source_file),
        "last_processed_source_line": 1,
        "last_processed_source_sha256": line_hash,
        "processed_event_count": 1,
        "emitted_event_count": 2,
        "rejected_event_count": 0,
        "skipped_duplicate_count": 0,
        "malformed_source_count": 0,
        "open_positions": {},
        "closed_positions": [],
        "seen_keys": [],
        "execution_equity": 100.0,  # Corrupted: should be equal to starting_bankroll (250.0)
        "cumulative_pnl": 0.0,
        "peak_equity": 250.0,
        "current_dd": 0.0,
        "max_dd": 0.0,
        "max_dd_pct": 0.0,
        "risk_of_ruin": False,
        "win_count": 0,
        "loss_count": 0,
        "flat_count": 0,
        "gross_profit": 0.0,
        "gross_loss": 0.0,
    }

    # Write checkpoint file
    write_checkpoint(output_root, "corrupt_run", checkpoint)

    from tools.execution_paper_runtime import run_replay
    with pytest.raises(ReconciliationError, match="equity replay consistency check failed"):
        run_replay(
            source_root=source_root,
            output_root=output_root,
            max_events=10,
            starting_bankroll=250.0,
        )


def test_strict_mode_unchanged_rejects_buy_sell(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    # In default (strict) mode, outcome/side as BUY/SELL should be rejected as side_unresolvable
    events = [
        {"event_type": "trade_open", "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "side": "BUY", "entry_price": 0.50, "position_id": "p1"}, "timestamp_utc": "2026-06-20T00:00:00Z"},
    ]
    _write_jsonl(source_root / "trade_journal" / "2026-06-20.jsonl", events)

    from tools.execution_paper_runtime import run_replay
    report = run_replay(source_root=source_root, output_root=output_root, max_events=10)
    assert report["rejected_events"] == 1

    trade_files = list((output_root / "journals" / "trade").glob("*.jsonl"))
    assert len(trade_files) == 1
    rejects = [json.loads(line) for line in trade_files[0].read_text(encoding="utf-8").splitlines() if json.loads(line)["event_type"] == "execution_paper_reject"]
    assert rejects[0]["reject_reason"] == "side_unresolvable"


def test_historical_mode_side_resolver(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    # In historical mode:
    # A. outcome YES/NO takes priority
    # B. side YES/NO as fallback
    # C. BUY/SELL side without YES/NO outcome is rejected as side_unresolvable
    events = [
        # Outcome is YES, side is BUY -> Should resolve to YES
        {"event_type": "trade_open", "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "side": "BUY", "entry_price": 0.50, "position_id": "p1"}, "timestamp_utc": "2026-06-20T00:00:00Z"},
        # Outcome is absent, side is NO -> Should resolve to NO
        {"event_type": "trade_open", "payload": {"condition_id": "0x2", "ticker": "BTC", "side": "NO", "entry_price": 0.50, "position_id": "p2"}, "timestamp_utc": "2026-06-20T00:01:00Z"},
        # Outcome is BUY, side is SELL -> Should be rejected as side_unresolvable
        {"event_type": "trade_open", "payload": {"condition_id": "0x3", "ticker": "BTC", "outcome": "BUY", "side": "SELL", "entry_price": 0.50, "position_id": "p3"}, "timestamp_utc": "2026-06-20T00:02:00Z"},
    ]
    _write_jsonl(source_root / "trade_journal" / "2026-06-20.jsonl", events)

    from tools.execution_paper_runtime import run_replay
    report = run_replay(source_root=source_root, output_root=output_root, max_events=10, compat_mode="historical")
    assert report["rejected_events"] == 1

    trade_files = list((output_root / "journals" / "trade").glob("*.jsonl"))
    assert len(trade_files) == 1
    rows = [json.loads(line) for line in trade_files[0].read_text(encoding="utf-8").splitlines()]
    opens = [r for r in rows if r["event_type"] == "execution_paper_open"]
    rejects = [r for r in rows if r["event_type"] == "execution_paper_reject"]

    assert len(opens) == 2
    assert opens[0]["execution_position_id"] == "ep_p1"
    assert opens[0]["side"] == "YES"
    assert opens[1]["execution_position_id"] == "ep_p2"
    assert opens[1]["side"] == "NO"

    assert len(rejects) == 1
    assert rejects[0]["reject_reason"] == "side_unresolvable"


def test_historical_mode_position_resolver_fallbacks(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    # Resolution order:
    # 1. position_id
    # 2. execution_position_id
    # 3. receipt.order_id
    # 4. order_id
    events = [
        # 1. uses position_id
        {"event_type": "trade_open", "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "entry_price": 0.50, "position_id": "pos_a", "execution_position_id": "pos_b"}, "timestamp_utc": "2026-06-20T00:00:00Z"},
        # 2. uses execution_position_id
        {"event_type": "trade_open", "payload": {"condition_id": "0x2", "ticker": "BTC", "outcome": "YES", "entry_price": 0.50, "execution_position_id": "pos_c"}, "timestamp_utc": "2026-06-20T00:01:00Z"},
        # 3. uses receipt.order_id
        {"event_type": "trade_open", "payload": {"condition_id": "0x3", "ticker": "BTC", "outcome": "YES", "entry_price": 0.50, "receipt": {"order_id": "ord_a"}, "order_id": "ord_b"}, "timestamp_utc": "2026-06-20T00:02:00Z"},
        # 4. uses order_id
        {"event_type": "trade_open", "payload": {"condition_id": "0x4", "ticker": "BTC", "outcome": "YES", "entry_price": 0.50, "order_id": "ord_c"}, "timestamp_utc": "2026-06-20T00:03:00Z"},
        # Unresolved position id -> missing_order_id_for_legacy_open
        {"event_type": "trade_open", "payload": {"condition_id": "0x5", "ticker": "BTC", "outcome": "YES", "entry_price": 0.50}, "timestamp_utc": "2026-06-20T00:04:00Z"},
    ]
    _write_jsonl(source_root / "trade_journal" / "2026-06-20.jsonl", events)

    from tools.execution_paper_runtime import run_replay
    report = run_replay(source_root=source_root, output_root=output_root, max_events=10, compat_mode="historical")
    assert report["rejected_events"] == 1

    trade_files = list((output_root / "journals" / "trade").glob("*.jsonl"))
    assert len(trade_files) == 1
    rows = [json.loads(line) for line in trade_files[0].read_text(encoding="utf-8").splitlines()]
    opens = [r for r in rows if r["event_type"] == "execution_paper_open"]
    rejects = [r for r in rows if r["event_type"] == "execution_paper_reject"]

    assert len(opens) == 4
    assert opens[0]["execution_position_id"] == "ep_pos_a"
    assert opens[1]["execution_position_id"] == "ep_pos_c"
    assert opens[2]["execution_position_id"] == "ep_ord_a"
    assert opens[3]["execution_position_id"] == "ep_ord_c"

    assert rejects[0]["reject_reason"] == "missing_order_id_for_legacy_open"


def test_historical_mode_position_id_unresolvable_on_close(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    # Close lacks position_id / execution_position_id / order_id, AND condition_id is omitted (so FIFO cannot match)
    events = [
        {"event_type": "trade_open", "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "entry_price": 0.50, "position_id": "p1"}, "timestamp_utc": "2026-06-20T00:00:00Z"},
        {"event_type": "trade_close", "payload": {"ticker": "BTC", "outcome": "YES", "exit_price": 0.60}, "timestamp_utc": "2026-06-20T00:01:00Z"},
    ]
    _write_jsonl(source_root / "trade_journal" / "2026-06-20.jsonl", events)

    from tools.execution_paper_runtime import run_replay
    report = run_replay(source_root=source_root, output_root=output_root, max_events=10, compat_mode="historical")
    assert report["rejected_events"] == 1

    trade_files = list((output_root / "journals" / "trade").glob("*.jsonl"))
    assert len(trade_files) == 1
    rejects = [json.loads(line) for line in trade_files[0].read_text(encoding="utf-8").splitlines() if json.loads(line)["event_type"] == "execution_paper_reject"]
    assert rejects[0]["reject_reason"] == "position_id_unresolvable"


def test_historical_mode_legacy_linking_and_ambiguity(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    # 1. Test single candidate (FIFO matches correctly)
    events1 = [
        {"event_type": "trade_open", "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "entry_price": 0.50, "order_id": "ord_open"}, "timestamp_utc": "2026-06-20T00:00:00Z"},
        {"event_type": "trade_close", "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "exit_price": 0.60, "order_id": "ord_close"}, "timestamp_utc": "2026-06-20T00:01:00Z"},
    ]
    _write_jsonl(source_root / "trade_journal" / "2026-06-20.jsonl", events1)

    from tools.execution_paper_runtime import run_replay
    report1 = run_replay(source_root=source_root, output_root=output_root, max_events=10, compat_mode="historical")
    assert report1["rejected_events"] == 0
    assert report1["execution_closed_trade_count"] == 1

    # 2. Test multiple candidates (ambiguous matching fails closed)
    events2 = [
        {"event_type": "trade_open", "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "entry_price": 0.50, "order_id": "ord_open_1"}, "timestamp_utc": "2026-06-21T00:00:00Z"},
        {"event_type": "trade_open", "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "entry_price": 0.40, "order_id": "ord_open_2"}, "timestamp_utc": "2026-06-21T00:01:00Z"},
        {"event_type": "trade_close", "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "exit_price": 0.60, "order_id": "ord_close"}, "timestamp_utc": "2026-06-21T00:02:00Z"},
    ]
    _write_jsonl(source_root / "trade_journal" / "2026-06-21.jsonl", events2)

    import shutil
    shutil.rmtree(output_root, ignore_errors=True)
    with pytest.raises(ReconciliationError, match="ambiguous_position_match"):
        run_replay(source_root=source_root, output_root=output_root, max_events=10, compat_mode="historical")


def test_historical_mode_link_collision(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    # If position is already closed, another close with same position ID triggers historical_link_collision
    events = [
        {"event_type": "trade_open", "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "entry_price": 0.50, "position_id": "p1"}, "timestamp_utc": "2026-06-20T00:00:00Z"},
        {"event_type": "trade_close", "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "exit_price": 0.60, "position_id": "p1"}, "timestamp_utc": "2026-06-20T00:01:00Z"},
        # Another close for "p1"
        {"event_type": "trade_close", "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "exit_price": 0.70, "position_id": "p1"}, "timestamp_utc": "2026-06-20T00:02:00Z"},
    ]
    _write_jsonl(source_root / "trade_journal" / "2026-06-20.jsonl", events)

    from tools.execution_paper_runtime import run_replay
    report = run_replay(source_root=source_root, output_root=output_root, max_events=10, compat_mode="historical")
    assert report["rejected_events"] == 1

    trade_files = list((output_root / "journals" / "trade").glob("*.jsonl"))
    assert len(trade_files) == 1
    rejects = [json.loads(line) for line in trade_files[0].read_text(encoding="utf-8").splitlines() if json.loads(line)["event_type"] == "execution_paper_reject"]
    assert rejects[0]["reject_reason"] == "historical_link_collision"


def test_two_opens_same_order_id_different_run_id_do_not_collide(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    # Historical mode: different run_ids can open same order_id concurrently
    events = [
        {
            "event_type": "trade_open",
            "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "entry_price": 0.50, "order_id": "paper-1"},
            "run_id": "run_1",
            "timestamp_utc": "2026-06-20T00:00:00Z"
        },
        {
            "event_type": "trade_open",
            "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "entry_price": 0.60, "order_id": "paper-1"},
            "run_id": "run_2",
            "timestamp_utc": "2026-06-20T00:01:00Z"
        }
    ]
    _write_jsonl(source_root / "trade_journal" / "2026-06-20.jsonl", events)

    from tools.execution_paper_runtime import run_replay
    report = run_replay(source_root=source_root, output_root=output_root, max_events=10, compat_mode="historical")
    assert report["emitted_events"] >= 3  # startup + 2 opens
    assert report["rejected_events"] == 0


def test_open_close_same_run_id_order_id_match(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    events = [
        {
            "event_type": "trade_open",
            "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "entry_price": 0.50, "order_id": "paper-1"},
            "run_id": "run_1",
            "timestamp_utc": "2026-06-20T00:00:00Z"
        },
        {
            "event_type": "trade_open",
            "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "entry_price": 0.60, "order_id": "paper-1"},
            "run_id": "run_2",
            "timestamp_utc": "2026-06-20T00:01:00Z"
        },
        # Close matches Open A by run_id
        {
            "event_type": "trade_close",
            "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "exit_price": 0.55, "order_id": "paper-1", "reason": "stop_loss"},
            "run_id": "run_1",
            "timestamp_utc": "2026-06-20T00:02:00Z"
        }
    ]
    _write_jsonl(source_root / "trade_journal" / "2026-06-20.jsonl", events)

    from tools.execution_paper_runtime import run_replay
    report = run_replay(source_root=source_root, output_root=output_root, max_events=10, compat_mode="historical")
    assert report["rejected_events"] == 0

    trade_files = list((output_root / "journals" / "trade").glob("*.jsonl"))
    assert len(trade_files) == 1
    rows = [json.loads(line) for line in trade_files[0].read_text(encoding="utf-8").splitlines()]
    opens = [r for r in rows if r["event_type"] == "execution_paper_open"]
    closes = [r for r in rows if r["event_type"] == "execution_paper_close"]

    assert len(opens) == 2
    assert len(closes) == 1

    # Verify close maps to correct open
    assert closes[0]["historical_position_uid"] == opens[0]["historical_position_uid"]
    assert closes[0]["execution_position_id"] == opens[0]["execution_position_id"]


def test_same_order_id_same_run_id_duplicate_fails(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    # Historical mode: same run_id cannot open same order_id twice concurrently
    events = [
        {
            "event_type": "trade_open",
            "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "entry_price": 0.50, "order_id": "paper-1"},
            "run_id": "run_1",
            "timestamp_utc": "2026-06-20T00:00:00Z"
        },
        {
            "event_type": "trade_open",
            "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "entry_price": 0.60, "order_id": "paper-1"},
            "run_id": "run_1",
            "timestamp_utc": "2026-06-20T00:01:00Z"
        }
    ]
    _write_jsonl(source_root / "trade_journal" / "2026-06-20.jsonl", events)

    from tools.execution_paper_runtime import run_replay
    with pytest.raises(ReconciliationError, match="duplicate_open"):
        run_replay(source_root=source_root, output_root=output_root, max_events=10, compat_mode="historical")


def test_missing_order_id_fallback_fifo_works(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    events = [
        # Open A
        {
            "event_type": "trade_open",
            "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "entry_price": 0.50, "order_id": "paper-1"},
            "run_id": "run_1",
            "timestamp_utc": "2026-06-20T00:00:00Z"
        },
        # Open B (different outcome to separate queue, same run_id)
        {
            "event_type": "trade_open",
            "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "NO", "entry_price": 0.40, "order_id": "paper-2"},
            "run_id": "run_1",
            "timestamp_utc": "2026-06-20T00:01:00Z"
        },
        # Close A has no order ID, should match Open A via FIFO (outcome YES matches YES queue)
        {
            "event_type": "trade_close",
            "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "exit_price": 0.55, "reason": "stop_loss"},
            "run_id": "run_1",
            "timestamp_utc": "2026-06-20T00:02:00Z"
        }
    ]
    _write_jsonl(source_root / "trade_journal" / "2026-06-20.jsonl", events)

    from tools.execution_paper_runtime import run_replay
    report = run_replay(source_root=source_root, output_root=output_root, max_events=10, compat_mode="historical")
    assert report["rejected_events"] == 0

    trade_files = list((output_root / "journals" / "trade").glob("*.jsonl"))
    assert len(trade_files) == 1
    rows = [json.loads(line) for line in trade_files[0].read_text(encoding="utf-8").splitlines()]
    opens = [r for r in rows if r["event_type"] == "execution_paper_open"]
    closes = [r for r in rows if r["event_type"] == "execution_paper_close"]

    assert len(opens) == 2
    assert len(closes) == 1
    # Check that close matched Open A (outcome YES)
    assert closes[0]["historical_position_uid"] == opens[0]["historical_position_uid"]


def test_ambiguity_fails_closed(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    # Two active opens, close has matching criteria that fits both (so it is ambiguous)
    events = [
        {"event_type": "trade_open", "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "entry_price": 0.50, "order_id": "ord_open_1"}, "run_id": "run_1", "timestamp_utc": "2026-06-20T00:00:00Z"},
        {"event_type": "trade_open", "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "entry_price": 0.40, "order_id": "ord_open_2"}, "run_id": "run_1", "timestamp_utc": "2026-06-20T00:01:00Z"},
        {"event_type": "trade_close", "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "exit_price": 0.60}, "run_id": "run_1", "timestamp_utc": "2026-06-20T00:02:00Z"},
    ]
    _write_jsonl(source_root / "trade_journal" / "2026-06-20.jsonl", events)

    from tools.execution_paper_runtime import run_replay
    with pytest.raises(ReconciliationError, match="ambiguous_position_match"):
        run_replay(source_root=source_root, output_root=output_root, max_events=10, compat_mode="historical")


def test_modern_position_id_path_unchanged(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    # Strict mode: duplicate position_id raises ReconciliationError
    events = [
        {
            "event_type": "trade_open",
            "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "entry_price": 0.50, "position_id": "p1"},
            "run_id": "run_1",
            "timestamp_utc": "2026-06-20T00:00:00Z"
        },
        {
            "event_type": "trade_open",
            "payload": {"condition_id": "0x1", "ticker": "BTC", "outcome": "YES", "entry_price": 0.60, "position_id": "p1"},
            "run_id": "run_2",
            "timestamp_utc": "2026-06-20T00:01:00Z"
        }
    ]
    _write_jsonl(source_root / "trade_journal" / "2026-06-20.jsonl", events)

    from tools.execution_paper_runtime import run_replay
    with pytest.raises(ReconciliationError, match="duplicate_open"):
        run_replay(source_root=source_root, output_root=output_root, max_events=10, compat_mode="strict")


def test_full_eligible_failure_fixture_replays_two_distinct_trades(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / DEFAULT_OUTPUT_ROOT

    # Exact replica of 2026-05-22 lines 1-4
    events = [
        {"event_type": "trade_open", "payload": {"condition_id": "0xe96b70608ff35b54aa6d59ae4cd3fe6661b94cf458db9dc7d04dd99df3ddf146", "ticker": "BTC", "outcome": "YES", "entry_price": 0.63, "receipt": {"order_id": "paper-71824750", "side": "BUY", "size": 0.034277, "price": 0.63, "filled_size": 0.034277}}, "run_id": "run_A", "timestamp_utc": "2026-05-22T02:35:25.555854Z"},
        {"event_type": "trade_open", "payload": {"condition_id": "0xe96b70608ff35b54aa6d59ae4cd3fe6661b94cf458db9dc7d04dd99df3ddf146", "ticker": "BTC", "outcome": "YES", "entry_price": 0.61, "receipt": {"order_id": "paper-71824750", "side": "BUY", "size": 0.052241, "price": 0.61, "filled_size": 0.052241}}, "run_id": "run_B", "timestamp_utc": "2026-05-22T02:35:28.667052Z"},
        {"event_type": "trade_close", "payload": {"condition_id": "0xe96b70608ff35b54aa6d59ae4cd3fe6661b94cf458db9dc7d04dd99df3ddf146", "ticker": "BTC", "outcome": "YES", "exit_price": 0.51, "receipt": {"order_id": "paper-71824750", "side": "SELL", "size": 0.034277, "price": 0.51, "filled_size": 0.034277}, "reason": "stop_loss"}, "run_id": "run_A", "timestamp_utc": "2026-05-22T02:35:31.962414Z"},
        {"event_type": "trade_close", "payload": {"condition_id": "0xe96b70608ff35b54aa6d59ae4cd3fe6661b94cf458db9dc7d04dd99df3ddf146", "ticker": "BTC", "outcome": "YES", "exit_price": 0.51, "receipt": {"order_id": "paper-71824750", "side": "SELL", "size": 0.052241, "price": 0.51, "filled_size": 0.052241}, "reason": "stop_loss"}, "run_id": "run_B", "timestamp_utc": "2026-05-22T02:35:34.307585Z"}
    ]
    _write_jsonl(source_root / "trade_journal" / "2026-05-22.jsonl", events)

    from tools.execution_paper_runtime import run_replay
    report = run_replay(source_root=source_root, output_root=output_root, max_events=10, compat_mode="historical")
    assert report["rejected_events"] == 0
    assert report["emitted_events"] >= 5  # startup + 2 opens + 2 closes

    trade_files = list((output_root / "journals" / "trade").glob("*.jsonl"))
    assert len(trade_files) == 1
    rows = [json.loads(line) for line in trade_files[0].read_text(encoding="utf-8").splitlines()]
    opens = [r for r in rows if r["event_type"] == "execution_paper_open"]
    closes = [r for r in rows if r["event_type"] == "execution_paper_close"]

    assert len(opens) == 2
    assert len(closes) == 2
    assert opens[0]["historical_position_uid"] != opens[1]["historical_position_uid"]
    assert closes[0]["historical_position_uid"] == opens[0]["historical_position_uid"]
    assert closes[1]["historical_position_uid"] == opens[1]["historical_position_uid"]
