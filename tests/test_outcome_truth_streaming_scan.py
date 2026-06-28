from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from tools.outcome_truth_streaming_scan import (
    CHECKPOINT_SCHEMA_VERSION,
    SourceMutationError,
    atomic_write_json,
    checkpoint_path_for,
    scan_files,
)


def _event(event_type: str, payload: dict) -> dict:
    return {
        "timestamp_utc": "2026-06-14T00:00:00Z",
        "event_type": event_type,
        "mode": "paper",
        "run_id": "run-test",
        "schema_version": "1.0",
        "source_module": "test",
        "payload": payload,
    }


def _write_jsonl(path: Path, events: list[dict | str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write((event if isinstance(event, str) else json.dumps(event)) + "\n")


def _scan(
    tmp_path: Path,
    scan_type: str,
    *,
    max_lines: int | None = None,
    memory_limit_mb: float = 450.0,
    rss_reader=lambda: 10.0,
    require_memory_probe: bool = False,
) -> dict:
    source_dir = tmp_path / "source" / scan_type
    checkpoint_dir = tmp_path / "checkpoints"
    report_path = tmp_path / "reports" / f"{scan_type}.json"
    return scan_files(
        scan_type=scan_type,
        source_dir=source_dir,
        checkpoint_dir=checkpoint_dir,
        report_path=report_path,
        max_lines=max_lines,
        memory_limit_mb=memory_limit_mb,
        rss_reader=rss_reader,
        require_memory_probe=require_memory_probe,
        progress_every=2,
    )


def test_source_uses_line_iteration_without_whole_file_loading() -> None:
    import tools.outcome_truth_streaming_scan as target_module
    source = Path(target_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = [
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    assert "readlines" not in calls
    assert "read_text" not in calls
    assert "read_bytes" not in calls
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "json"
        and node.func.attr == "load"
        for node in ast.walk(tree)
    )
    assert "list(file" not in source


def test_checkpoint_is_created_with_required_contract(tmp_path: Path) -> None:
    path = tmp_path / "source" / "decision_log" / "one.jsonl"
    _write_jsonl(path, [_event("decision", {"condition_id": "c1", "epoch_start": 1})])

    result = _scan(tmp_path, "decision_log")
    checkpoint = json.loads(
        checkpoint_path_for(tmp_path / "checkpoints", "decision_log", path).read_text(encoding="utf-8")
    )

    assert result["status"] == "COMPLETE"
    assert checkpoint["schema_version"] == CHECKPOINT_SCHEMA_VERSION
    for field in (
        "scan_type",
        "source_file",
        "file_size",
        "file_mtime",
        "last_completed_line",
        "lines_seen",
        "malformed_lines",
        "aggregate_counts",
        "started_at",
        "checkpointed_at",
    ):
        assert field in checkpoint


def test_resume_continues_from_checkpoint_without_double_counting(tmp_path: Path) -> None:
    path = tmp_path / "source" / "decision_log" / "one.jsonl"
    _write_jsonl(
        path,
        [
            _event("decision", {"condition_id": f"c{i}", "epoch_start": i, "model_output_ready": True})
            for i in range(4)
        ],
    )

    first = _scan(tmp_path, "decision_log", max_lines=2)
    second = _scan(tmp_path, "decision_log")

    assert first["status"] == "MAX_LINES_REACHED"
    assert first["aggregate_counts"]["valid_rows"] == 2
    assert second["status"] == "COMPLETE"
    assert second["aggregate_counts"]["valid_rows"] == 4
    assert second["aggregate_counts"]["model_ready_rows"] == 4


def test_source_mutation_invalidates_checkpoint(tmp_path: Path) -> None:
    path = tmp_path / "source" / "decision_log" / "one.jsonl"
    _write_jsonl(path, [_event("decision", {"condition_id": "c1", "epoch_start": 1})])
    _scan(tmp_path, "decision_log", max_lines=1)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_event("decision", {"condition_id": "c2", "epoch_start": 2})) + "\n")

    with pytest.raises(SourceMutationError):
        _scan(tmp_path, "decision_log")


def test_malformed_json_fails_closed_and_checkpoints(tmp_path: Path) -> None:
    path = tmp_path / "source" / "decision_log" / "one.jsonl"
    _write_jsonl(path, [_event("decision", {"condition_id": "c1", "epoch_start": 1}), "{broken"])

    result = _scan(tmp_path, "decision_log")

    assert result["status"] == "MALFORMED_JSON"
    assert result["ready"] is False
    assert result["malformed_lines"] == 1
    assert result["aggregate_counts"]["valid_rows"] == 1


def test_atomic_write_replaces_destination_without_leaving_temp_file(tmp_path: Path) -> None:
    destination = tmp_path / "reports" / "report.json"
    destination.parent.mkdir(parents=True)
    destination.write_text('{"old": true}\n', encoding="utf-8")

    atomic_write_json(destination, {"new": True})

    assert json.loads(destination.read_text(encoding="utf-8")) == {"new": True}
    assert list(destination.parent.glob(f".{destination.name}.*.tmp")) == []


def test_max_lines_stops_cleanly(tmp_path: Path) -> None:
    path = tmp_path / "source" / "decision_log" / "one.jsonl"
    _write_jsonl(
        path,
        [_event("decision", {"condition_id": f"c{i}", "epoch_start": i}) for i in range(5)],
    )

    result = _scan(tmp_path, "decision_log", max_lines=3)

    assert result["status"] == "MAX_LINES_REACHED"
    assert result["lines_seen"] == 3
    assert result["aggregate_counts"]["valid_rows"] == 3


def test_memory_limit_stop_can_be_simulated(tmp_path: Path) -> None:
    path = tmp_path / "source" / "decision_log" / "one.jsonl"
    _write_jsonl(path, [_event("decision", {"condition_id": "c1", "epoch_start": 1})])

    result = _scan(tmp_path, "decision_log", memory_limit_mb=450, rss_reader=lambda: 451.0)

    assert result["status"] == "MEMORY_LIMIT_REACHED"
    assert result["ready"] is False
    assert result["lines_seen"] == 0


def test_memory_probe_failure_continues_by_default(tmp_path: Path) -> None:
    path = tmp_path / "source" / "decision_log" / "one.jsonl"
    _write_jsonl(path, [_event("decision", {"condition_id": "c1", "epoch_start": 1})])

    def unavailable_probe() -> float:
        raise OSError("simulated probe failure")

    result = _scan(tmp_path, "decision_log", rss_reader=unavailable_probe)
    checkpoint = json.loads(
        checkpoint_path_for(tmp_path / "checkpoints", "decision_log", path).read_text(encoding="utf-8")
    )

    assert result["status"] == "COMPLETE"
    assert result["ready"] is True
    assert result["lines_seen"] == 1
    assert result["memory_probe_status"] == "UNAVAILABLE"
    assert any("memory_probe_unavailable" in warning for warning in result["warnings"])
    assert checkpoint["memory_probe_status"] == "UNAVAILABLE"
    assert any("memory_probe_unavailable" in warning for warning in checkpoint["warnings"])


def test_memory_probe_failure_fails_closed_when_required(tmp_path: Path) -> None:
    path = tmp_path / "source" / "decision_log" / "one.jsonl"
    _write_jsonl(path, [_event("decision", {"condition_id": "c1", "epoch_start": 1})])

    def unavailable_probe() -> float:
        raise OSError("simulated probe failure")

    result = _scan(
        tmp_path,
        "decision_log",
        rss_reader=unavailable_probe,
        require_memory_probe=True,
    )

    assert result["status"] == "MEMORY_PROBE_REQUIRED_UNAVAILABLE"
    assert result["ready"] is False
    assert result["lines_seen"] == 0
    assert result["memory_probe_status"] == "UNAVAILABLE"
    assert any("memory_probe_unavailable" in warning for warning in result["warnings"])


def test_decision_log_mode_aggregates_expected_counts(tmp_path: Path) -> None:
    path = tmp_path / "source" / "decision_log" / "one.jsonl"
    _write_jsonl(
        path,
        [
            _event(
                "decision",
                {
                    "condition_id": "c1",
                    "epoch_start": 1,
                    "model_output_ready": True,
                    "decision_timestamp": "2026-06-14T00:00:00Z",
                },
            ),
            _event("decision", {"condition_id": "c2", "epoch_start": 2}),
        ],
    )

    counts = _scan(tmp_path, "decision_log")["aggregate_counts"]

    assert counts["valid_rows"] == 2
    assert counts["join_key_rows"] == 2
    assert counts["model_ready_rows"] == 1
    assert counts["timestamp_rows"] == 2


def test_market_snapshot_mode_aggregates_expected_counts(tmp_path: Path) -> None:
    path = tmp_path / "source" / "market_snapshots" / "one.jsonl"
    _write_jsonl(
        path,
        [
            _event("market_snapshot", {"condition_id": "c1", "epoch_start_ts": 1, "seconds_remaining": 60, "yes_bid": 0.8}),
            _event("market_snapshot", {"condition_id": "c2", "epoch_start_ts": 2, "seconds_remaining": 60, "yes_bid": 0.5}),
            _event("market_snapshot", {"condition_id": "c3", "epoch_start_ts": 3, "seconds_remaining": 150, "yes_bid": 0.2}),
        ],
    )

    counts = _scan(tmp_path, "market_snapshots")["aggregate_counts"]

    assert counts["valid_rows"] == 3
    assert counts["near_close_proxy_rows"] == 2
    assert counts["provisional_resolved_rows"] == 1
    assert counts["provisional_ambiguous_rows"] == 1


def test_trade_journal_mode_aggregates_expected_counts(tmp_path: Path) -> None:
    path = tmp_path / "source" / "trade_journal" / "one.jsonl"
    _write_jsonl(
        path,
        [
            _event("trade_open", {"condition_id": "c1", "epoch_start_ts": 1}),
            _event("trade_close", {"condition_id": "c1", "epoch_start_ts": 1, "trade_result": "TP"}),
            _event("trade_close", {"condition_id": "c2", "epoch_start_ts": 2, "official_outcome": "YES"}),
        ],
    )

    counts = _scan(tmp_path, "trade_journal")["aggregate_counts"]

    assert counts["valid_rows"] == 3
    assert counts["trade_close_rows"] == 2
    assert counts["native_trade_result_rows"] == 1
    assert counts["strict_official_resolution_rows"] == 1


def test_outputs_must_not_be_inside_source_directory(tmp_path: Path) -> None:
    source_dir = tmp_path / "source" / "decision_log"
    _write_jsonl(source_dir / "one.jsonl", [_event("decision", {})])

    with pytest.raises(ValueError, match="outside source"):
        scan_files(
            scan_type="decision_log",
            source_dir=source_dir,
            checkpoint_dir=source_dir / "checkpoints",
            report_path=tmp_path / "report.json",
            rss_reader=lambda: 10.0,
        )
