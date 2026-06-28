"""Tests for RuntimeEventStream V1 and the runtime_event_replay tool."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from utils.runtime_event_stream import (
    ENGINE_VERSION,
    PRIORITY_RANK,
    SCHEMA_VERSION,
    RuntimeEventStream,
)


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

FIXED_NOW = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)
FIXED_DATE = "2026-06-25"


def _fixed_clock() -> datetime:
    return FIXED_NOW


def _make_stream(tmp_path: Path, **kwargs) -> RuntimeEventStream:
    """Build a no-thread stream for unit tests."""
    return RuntimeEventStream(
        output_dir=tmp_path / "event_stream",
        mode="paper",
        now=_fixed_clock,
        _start_writer=False,
        **kwargs,
    )


def _drain(stream: RuntimeEventStream) -> list[dict]:
    """Drain the internal queue without the writer thread."""
    with stream._cond:
        events = list(stream._queue)
        stream._queue.clear()
    return events


# ──────────────────────────────────────────────────────────────────────────────
# 1. Schema validity
# ──────────────────────────────────────────────────────────────────────────────

REQUIRED_ENVELOPE_FIELDS = {
    "event_id",
    "event_type",
    "event_version",
    "schema_version",
    "runtime_session_id",
    "session_sequence",
    "timestamp_utc",
    "priority",
    "engine_version",
    "git_commit",
    "runtime_environment",
    "payload",
}


def test_schema_validity(tmp_path):
    stream = _make_stream(tmp_path)
    stream.emit("runtime_started_v1", {"test": True}, priority="CRITICAL")
    events = _drain(stream)
    assert len(events) == 1
    env = events[0]
    missing = REQUIRED_ENVELOPE_FIELDS - env.keys()
    assert not missing, f"Missing envelope fields: {missing}"
    assert env["event_type"] == "runtime_started_v1"
    assert env["engine_version"] == ENGINE_VERSION
    assert env["schema_version"] == SCHEMA_VERSION
    assert env["runtime_environment"] == "paper"
    assert env["priority"] == "CRITICAL"
    assert env["timestamp_utc"].endswith("Z")
    assert env["payload"] == {"test": True}


def test_schema_event_id_is_uuid(tmp_path):
    stream = _make_stream(tmp_path)
    stream.emit("test_event_v1", {})
    stream.emit("test_event_v1", {})
    events = _drain(stream)
    ids = [e["event_id"] for e in events]
    assert ids[0] != ids[1], "event_id must be unique per event"
    # Basic UUID4 format check
    for eid in ids:
        parts = eid.split("-")
        assert len(parts) == 5


# ──────────────────────────────────────────────────────────────────────────────
# 2. session_sequence monotonically increments
# ──────────────────────────────────────────────────────────────────────────────

def test_sequence_increments(tmp_path):
    stream = _make_stream(tmp_path)
    for _ in range(5):
        stream.emit("test_v1", {})
    events = _drain(stream)
    seqs = [e["session_sequence"] for e in events]
    assert seqs == list(range(1, 6)), f"Expected [1..5], got {seqs}"


def test_sequence_is_cross_priority(tmp_path):
    stream = _make_stream(tmp_path)
    stream.emit("a", {}, priority="LOW")
    stream.emit("b", {}, priority="CRITICAL")
    stream.emit("c", {}, priority="NORMAL")
    events = _drain(stream)
    seqs = [e["session_sequence"] for e in events]
    assert seqs == [1, 2, 3]


# ──────────────────────────────────────────────────────────────────────────────
# 3. Append-only JSONL (written file has multiple lines, not overwritten)
# ──────────────────────────────────────────────────────────────────────────────

def test_append_only_jsonl(tmp_path):
    stream = RuntimeEventStream(
        output_dir=tmp_path / "event_stream",
        mode="paper",
        now=_fixed_clock,
        _start_writer=True,
    )
    stream.emit("ev_a", {"n": 1})
    stream.emit("ev_b", {"n": 2})
    stream.emit("ev_c", {"n": 3})
    stream.shutdown(timeout=10.0)

    files = list((tmp_path / "event_stream").glob("*.jsonl"))
    assert len(files) == 1
    lines = [l for l in files[0].read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 3
    for line in lines:
        obj = json.loads(line)
        assert "event_type" in obj


# ──────────────────────────────────────────────────────────────────────────────
# 4. File rotation by size
# ──────────────────────────────────────────────────────────────────────────────

def test_rotation_by_file_size(tmp_path):
    # tiny max_file_size_bytes → rotates after first event
    stream = RuntimeEventStream(
        output_dir=tmp_path / "event_stream",
        mode="paper",
        now=_fixed_clock,
        max_file_size_bytes=1,  # 1 byte: forces rotate after every write
        _start_writer=True,
    )
    for i in range(3):
        stream.emit("test_v1", {"i": i})
    stream.shutdown(timeout=10.0)

    files = sorted((tmp_path / "event_stream").glob("*.jsonl"))
    assert len(files) >= 2, "Expected at least 2 rotated files"
    # Files must be named with sequential suffix
    names = [f.name for f in files]
    assert any("_001.jsonl" in n for n in names)
    assert any("_002.jsonl" in n for n in names)


def test_file_naming_pattern(tmp_path):
    stream = RuntimeEventStream(
        output_dir=tmp_path / "event_stream",
        mode="paper",
        now=_fixed_clock,
        _start_writer=True,
    )
    stream.emit("test_v1", {})
    stream.shutdown(timeout=10.0)

    files = list((tmp_path / "event_stream").glob("*.jsonl"))
    assert len(files) == 1
    assert files[0].name == f"runtime_events_{FIXED_DATE}_001.jsonl"


# ──────────────────────────────────────────────────────────────────────────────
# 5. LOW drop behaviour
# ──────────────────────────────────────────────────────────────────────────────

def test_low_drop_at_85_percent_threshold(tmp_path):
    # maxsize=10 → LOW dropped when remaining < 1.5 (i.e., size >= 9)
    stream = _make_stream(tmp_path, queue_maxsize=10)

    # Emit 9 LOW events — all should succeed (size goes 0→9, remaining at emit time ≥ 2)
    results = [stream.emit(f"low_{i}", {}, priority="LOW") for i in range(9)]
    assert all(results), "First 9 LOWs should be accepted"

    # 10th LOW: size=9, remaining=1 < 1.5 → should be dropped
    result = stream.emit("low_dropped", {}, priority="LOW")
    assert result is False

    events = _drain(stream)
    # 9 LOW events + 1 overflow notification
    assert len(events) == 10
    overflow = events[-1]
    assert overflow["event_type"] == "event_stream_queue_overflow_v1"
    assert overflow["payload"]["dropped_event_type"] == "low_dropped"
    assert overflow["priority"] == "HIGH"


def test_low_not_dropped_below_threshold(tmp_path):
    stream = _make_stream(tmp_path, queue_maxsize=100)
    # With 100 slots, LOW is only dropped when remaining < 15 (size >= 86)
    result = stream.emit("low_event", {}, priority="LOW")
    assert result is True
    assert stream.queue_depth == 1


# ──────────────────────────────────────────────────────────────────────────────
# 6. CRITICAL not dropped
# ──────────────────────────────────────────────────────────────────────────────

def test_critical_never_dropped_evicts_lower(tmp_path):
    # Fill queue with NORMAL events, then emit CRITICAL
    stream = _make_stream(tmp_path, queue_maxsize=5)

    for i in range(5):
        result = stream.emit(f"normal_{i}", {}, priority="NORMAL")
        assert result is True

    # Queue full with 5 NORMALs
    assert stream.queue_depth == 5

    # CRITICAL should evict the oldest NORMAL
    result = stream.emit("runtime_started_v1", {}, priority="CRITICAL")
    assert result is True

    events = _drain(stream)
    event_types = [e["event_type"] for e in events]

    # The CRITICAL event must be present
    assert "runtime_started_v1" in event_types
    # An overflow notification for the evicted NORMAL must be present
    overflows = [e for e in events if e["event_type"] == "event_stream_queue_overflow_v1"]
    assert len(overflows) == 1
    assert overflows[0]["payload"]["dropped_event_type"] == "normal_0"


def test_critical_all_critical_queue_allows_overcapacity(tmp_path):
    stream = _make_stream(tmp_path, queue_maxsize=3)
    for i in range(3):
        stream.emit(f"fill_{i}", {}, priority="CRITICAL")
    # Queue full, all CRITICAL. Emitting another CRITICAL must not drop it.
    result = stream.emit("extra_critical", {}, priority="CRITICAL")
    assert result is True
    events = _drain(stream)
    types = [e["event_type"] for e in events]
    assert "extra_critical" in types


# ──────────────────────────────────────────────────────────────────────────────
# 7. Heartbeat shape
# ──────────────────────────────────────────────────────────────────────────────

REQUIRED_HEARTBEAT_FIELDS = {
    "runtime_alive",
    "uptime_seconds",
    "paper_balance",
    "active_positions",
    "current_bankroll_tier",
    "risk_mode",
    "candidate_count",
    "events_per_second",
    "memory_mb",
    "cpu_percent",
    "runtime_state",
    "loop_latency_ms",
    "decision_latency_ms",
    "queue_depth",
    "writer_backlog",
    "event_stream_file_size",
    "last_flush_age_ms",
}


def test_heartbeat_payload_shape(tmp_path):
    stream = _make_stream(tmp_path)
    stream.update_metrics_cache({
        "paper_balance": 500.0,
        "active_positions": 2,
        "current_bankroll_tier": "T1_SEED",
        "risk_mode": "NORMAL",
        "candidate_count": 7,
        "loop_latency_ms": 120,
        "decision_latency_ms": 45,
    })
    payload = stream._build_heartbeat_payload()
    missing = REQUIRED_HEARTBEAT_FIELDS - payload.keys()
    assert not missing, f"Missing heartbeat fields: {missing}"
    assert payload["runtime_alive"] is True
    assert payload["uptime_seconds"] >= 0
    assert payload["paper_balance"] == 500.0
    assert payload["active_positions"] == 2
    assert payload["current_bankroll_tier"] == "T1_SEED"
    assert payload["risk_mode"] == "NORMAL"
    assert payload["candidate_count"] == 7
    assert payload["runtime_state"] == "running"


def test_heartbeat_priority_is_critical(tmp_path):
    stream = _make_stream(tmp_path)
    payload = stream._build_heartbeat_payload()
    # Simulate heartbeat emission
    stream.emit("runtime_heartbeat_v1", payload, priority="CRITICAL")
    events = _drain(stream)
    hb = next(e for e in events if e["event_type"] == "runtime_heartbeat_v1")
    assert hb["priority"] == "CRITICAL"


# ──────────────────────────────────────────────────────────────────────────────
# 8. Graceful shutdown flush
# ──────────────────────────────────────────────────────────────────────────────

def test_graceful_shutdown_flushes_queue(tmp_path):
    stream = RuntimeEventStream(
        output_dir=tmp_path / "event_stream",
        mode="paper",
        now=_fixed_clock,
        _start_writer=True,
    )
    n = 20
    for i in range(n):
        stream.emit(f"flush_test_{i}", {"i": i})
    stream.shutdown(timeout=15.0)

    outdir = tmp_path / "event_stream"
    all_lines = []
    for f in sorted(outdir.glob("*.jsonl")):
        all_lines.extend(f.read_text(encoding="utf-8").splitlines())

    parsed = [json.loads(ln) for ln in all_lines if ln.strip()]
    assert len(parsed) == n, f"Expected {n} events flushed, got {len(parsed)}"


# ──────────────────────────────────────────────────────────────────────────────
# 9. Writer failure non-propagation
# ──────────────────────────────────────────────────────────────────────────────

def test_emit_never_raises_on_bad_output_dir(tmp_path):
    # Point output_dir to a file (not a directory) to force mkdir/write failure
    bad_path = tmp_path / "not_a_dir"
    bad_path.write_text("I am a file")

    stream = RuntimeEventStream(
        output_dir=bad_path,
        mode="paper",
        now=_fixed_clock,
        _start_writer=False,  # no background thread so we control writes
    )
    # emit() must not raise regardless of later write failures
    for _ in range(5):
        try:
            stream.emit("test_event", {"x": 1})
        except Exception as exc:
            pytest.fail(f"emit() raised unexpectedly: {exc}")


def test_emit_returns_false_after_shutdown(tmp_path):
    stream = _make_stream(tmp_path)
    stream.shutdown(timeout=1.0)
    result = stream.emit("test_event", {})
    assert result is False


# ──────────────────────────────────────────────────────────────────────────────
# 10. update_metrics_cache thread safety
# ──────────────────────────────────────────────────────────────────────────────

def test_update_metrics_cache(tmp_path):
    stream = _make_stream(tmp_path)
    stream.update_metrics_cache({"paper_balance": 250.0, "risk_mode": "REDUCED"})
    with stream._metrics_lock:
        assert stream._metrics_cache["paper_balance"] == 250.0
        assert stream._metrics_cache["risk_mode"] == "REDUCED"

    # Subsequent update merges (does not replace)
    stream.update_metrics_cache({"candidate_count": 5})
    with stream._metrics_lock:
        assert stream._metrics_cache["paper_balance"] == 250.0
        assert stream._metrics_cache["candidate_count"] == 5


# ──────────────────────────────────────────────────────────────────────────────
# 11. Replay tool — filtering
# ──────────────────────────────────────────────────────────────────────────────

def _write_test_events(outdir: Path, events: list[dict]) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / "runtime_events_2026-06-25_001.jsonl"
    with open(path, "w", encoding="utf-8") as fh:
        for e in events:
            fh.write(json.dumps(e) + "\n")
    return path


def _build_event(seq: int, event_type: str, session_id: str = "sess_001") -> dict:
    return {
        "event_id": f"id-{seq}",
        "event_type": event_type,
        "event_version": "1.0.0",
        "schema_version": "1.0.0",
        "runtime_session_id": session_id,
        "session_sequence": seq,
        "timestamp_utc": "2026-06-25T12:00:00Z",
        "priority": "NORMAL",
        "engine_version": "1.0.0",
        "git_commit": "abc1234",
        "runtime_environment": "paper",
        "payload": {"seq": seq},
    }


def test_replay_filter_by_event_type(tmp_path):
    from tools.replay.runtime_event_replay import _find_files, _read_events

    outdir = tmp_path / "event_stream"
    evts = [_build_event(i, "candidate_generated_v1" if i % 2 == 0 else "go_no_go_decision_v1") for i in range(1, 7)]
    _write_test_events(outdir, evts)

    files = _find_files("2026-06-25", outdir)
    result = _read_events(files, None, "candidate_generated_v1", None, None, False)
    assert all(e["event_type"] == "candidate_generated_v1" for e in result)
    assert len(result) == 3


def test_replay_filter_by_session_id(tmp_path):
    from tools.replay.runtime_event_replay import _find_files, _read_events

    outdir = tmp_path / "event_stream"
    evts = [
        _build_event(1, "ev", "session_A"),
        _build_event(2, "ev", "session_B"),
        _build_event(3, "ev", "session_A"),
    ]
    _write_test_events(outdir, evts)

    files = _find_files("2026-06-25", outdir)
    result = _read_events(files, "session_A", None, None, None, False)
    assert len(result) == 2
    assert all(e["runtime_session_id"] == "session_A" for e in result)


def test_replay_from_sequence(tmp_path):
    from tools.replay.runtime_event_replay import _find_files, _read_events

    outdir = tmp_path / "event_stream"
    evts = [_build_event(i, "test_v1") for i in range(1, 11)]
    _write_test_events(outdir, evts)

    files = _find_files("2026-06-25", outdir)
    result = _read_events(files, None, None, seq=5, limit=None, follow=False)
    seqs = [e["session_sequence"] for e in result]
    assert min(seqs) >= 5
    assert len(result) == 6  # events 5-10


def test_replay_limit(tmp_path):
    from tools.replay.runtime_event_replay import _find_files, _read_events

    outdir = tmp_path / "event_stream"
    evts = [_build_event(i, "test_v1") for i in range(1, 11)]
    _write_test_events(outdir, evts)

    files = _find_files("2026-06-25", outdir)
    result = _read_events(files, None, None, None, limit=3, follow=False)
    assert len(result) == 3


def test_replay_summary(tmp_path, capsys):
    from tools.replay.runtime_event_replay import _print_summary

    evts = [
        _build_event(1, "alpha_v1"),
        _build_event(2, "alpha_v1"),
        _build_event(3, "beta_v1"),
    ]
    _print_summary(evts)
    out = capsys.readouterr().out
    assert "alpha_v1" in out
    assert "2" in out
    assert "beta_v1" in out
    assert "TOTAL" in out


def test_replay_find_files_empty_dir(tmp_path):
    from tools.replay.runtime_event_replay import _find_files

    outdir = tmp_path / "empty"
    outdir.mkdir()
    files = _find_files("2026-06-25", outdir)
    assert files == []


# ──────────────────────────────────────────────────────────────────────────────
# 12. HIGH drop when nothing to evict
# ──────────────────────────────────────────────────────────────────────────────

def test_high_dropped_when_queue_full_of_criticals(tmp_path):
    stream = _make_stream(tmp_path, queue_maxsize=3)
    for _ in range(3):
        stream.emit("critical_fill", {}, priority="CRITICAL")

    # HIGH has nothing to evict (only CRITICAL in queue)
    result = stream.emit("high_event", {}, priority="HIGH")
    assert result is False

    events = _drain(stream)
    overflow = next((e for e in events if e["event_type"] == "event_stream_queue_overflow_v1"), None)
    assert overflow is not None
    assert overflow["payload"]["dropped_event_type"] == "high_event"


# ──────────────────────────────────────────────────────────────────────────────
# 13. Eviction direction: oldest first
# ──────────────────────────────────────────────────────────────────────────────

def test_eviction_removes_oldest_low_first(tmp_path):
    stream = _make_stream(tmp_path, queue_maxsize=3)
    stream.emit("first_low", {}, priority="LOW")
    stream.emit("second_low", {}, priority="LOW")
    stream.emit("third_low", {}, priority="LOW")
    # Queue full with [first_low, second_low, third_low]

    # Emit NORMAL: should evict oldest LOW (first_low)
    result = stream.emit("normal_event", {}, priority="NORMAL")
    assert result is True

    events = _drain(stream)
    overflow = next((e for e in events if e["event_type"] == "event_stream_queue_overflow_v1"), None)
    assert overflow is not None
    assert overflow["payload"]["dropped_event_type"] == "first_low"


# ──────────────────────────────────────────────────────────────────────────────
# 14. session_id in envelope
# ──────────────────────────────────────────────────────────────────────────────

def test_session_id_in_all_events(tmp_path):
    stream = _make_stream(tmp_path, session_id="test-session-001")
    for _ in range(3):
        stream.emit("test_v1", {})
    events = _drain(stream)
    for e in events:
        assert e["runtime_session_id"] == "test-session-001"
