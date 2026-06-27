"""Tests for FLAOS Phase A log governance tool.

Uses temp directories — never touches real runtime/logs/ data.
"""
from __future__ import annotations

import gzip
import json
import os
import time
import tempfile
from pathlib import Path

import pytest

# Add tools/ to path for direct import
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from flaos.log_governance import (
    _collect_log_backups,
    _collect_zero_byte_session_logs,
    _collect_compressible_jsonl,
    _session_guard,
    cmd_inspect,
    cmd_plan,
    cmd_dry_run,
    cmd_execute,
    cmd_report,
    LOG_BACKUP_KEEP,
    LOG_BACKUP_MIN_AGE_DAYS,
    JSONL_COMPRESS_AGE_DAYS,
    MAX_ACTIONS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_root(tmp_path: Path) -> Path:
    """Create minimal directory tree for testing."""
    (tmp_path / "logs").mkdir()
    (tmp_path / "runtime" / "event_stream").mkdir(parents=True)
    (tmp_path / "runtime" / "validation").mkdir(parents=True)
    (tmp_path / "runtime" / "sessions").mkdir(parents=True)
    return tmp_path


def _aged(path: Path, days: float) -> None:
    """Set file mtime to `days` days ago."""
    ts = time.time() - days * 86400
    os.utime(path, (ts, ts))


def _write(path: Path, content: bytes = b"x" * 100) -> Path:
    path.write_bytes(content)
    return path


# ---------------------------------------------------------------------------
# Tests: inspect
# ---------------------------------------------------------------------------

class TestInspect:
    def test_inspect_empty_root(self, tmp_path, capsys):
        root = _make_root(tmp_path)
        rc = cmd_inspect(root, pretty=False)
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert "domains" in out
        assert out["active_session_guard"] == "PASS"

    def test_inspect_counts_backup_candidates(self, tmp_path, capsys):
        root = _make_root(tmp_path)
        logs = root / "logs"
        # Create backups: N=1..5 (kept) and N=6..9 (candidates if aged)
        for n in range(1, 10):
            f = _write(logs / f"polytrade_bot_20260627.log.{n}")
            if n > LOG_BACKUP_KEEP:
                _aged(f, LOG_BACKUP_MIN_AGE_DAYS + 1)
        rc = cmd_inspect(root, pretty=False)
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["domains"]["logs_rotated_backups"]["delete_candidates"] == 4  # N=6,7,8,9


# ---------------------------------------------------------------------------
# Tests: plan
# ---------------------------------------------------------------------------

class TestPlan:
    def test_plan_marks_old_backups_as_delete(self, tmp_path, capsys):
        root = _make_root(tmp_path)
        logs = root / "logs"
        for n in range(6, 10):
            f = _write(logs / f"polytrade.log.{n}")
            _aged(f, LOG_BACKUP_MIN_AGE_DAYS + 1)

        rc = cmd_plan(root, pretty=False)
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        delete_actions = [a for a in out["actions"] if a["action"] == "DELETE"]
        assert len(delete_actions) == 4

    def test_plan_marks_old_jsonl_as_compress_not_delete(self, tmp_path, capsys):
        root = _make_root(tmp_path)
        stream = root / "runtime" / "event_stream"
        f = _write(stream / "runtime_events_2026-06-01_001.jsonl", b"x" * 1000)
        _aged(f, JSONL_COMPRESS_AGE_DAYS + 1)

        rc = cmd_plan(root, pretty=False)
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        jsonl_actions = [a for a in out["actions"] if "jsonl" in a["file"].lower()]
        assert all(a["action"] == "COMPRESS" for a in jsonl_actions)
        assert not any(a["action"] == "DELETE" for a in jsonl_actions)

    def test_plan_keeps_recent_backups(self, tmp_path, capsys):
        root = _make_root(tmp_path)
        logs = root / "logs"
        # N=6 but less than 1 day old — should NOT be a candidate
        f = _write(logs / "polytrade.log.6")
        _aged(f, 0.1)  # very recent
        rc = cmd_plan(root, pretty=False)
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["total_actions"] == 0

    def test_plan_keeps_n_le_5(self, tmp_path, capsys):
        root = _make_root(tmp_path)
        logs = root / "logs"
        for n in range(1, 6):
            f = _write(logs / f"polytrade.log.{n}")
            _aged(f, 10)  # old but N <= 5 = keep
        rc = cmd_plan(root, pretty=False)
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["total_actions"] == 0


# ---------------------------------------------------------------------------
# Tests: dry-run
# ---------------------------------------------------------------------------

class TestDryRun:
    def test_dry_run_does_not_mutate_files(self, tmp_path, capsys):
        root = _make_root(tmp_path)
        logs = root / "logs"
        for n in range(6, 9):
            f = _write(logs / f"polytrade.log.{n}")
            _aged(f, 2)

        before = set(logs.iterdir())
        rc = cmd_dry_run(root, pretty=False)
        assert rc == 0
        after = set(logs.iterdir())
        assert before == after  # no files changed

    def test_dry_run_returns_dry_run_status(self, tmp_path, capsys):
        root = _make_root(tmp_path)
        logs = root / "logs"
        f = _write(logs / "polytrade.log.6")
        _aged(f, 2)
        rc = cmd_dry_run(root, pretty=False)
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["mode"] == "DRY_RUN"
        assert any(a["status"] == "DRY_RUN" for a in out["actions"])


# ---------------------------------------------------------------------------
# Tests: execute
# ---------------------------------------------------------------------------

class TestExecute:
    def test_execute_without_confirm_refuses(self, tmp_path, capsys):
        root = _make_root(tmp_path)
        rc = cmd_execute(root, confirm=False, pretty=False)
        assert rc == 0  # downgrade to dry-run, exits 0
        out = json.loads(capsys.readouterr().out)
        assert "DRY_RUN" in out.get("status", out.get("mode", ""))

    def test_execute_with_confirm_deletes_excess_backups(self, tmp_path, capsys):
        root = _make_root(tmp_path)
        logs = root / "logs"
        kept = []
        deleted = []
        for n in range(1, 10):
            f = _write(logs / f"polytrade.log.{n}", b"x" * 200)
            _aged(f, 2)
            if n <= LOG_BACKUP_KEEP:
                kept.append(f)
            else:
                deleted.append(f)

        rc = cmd_execute(root, confirm=True, pretty=False)
        assert rc == 0

        for f in kept:
            assert f.exists(), f"Should keep {f.name}"
        for f in deleted:
            assert not f.exists(), f"Should delete {f.name}"

    def test_execute_compresses_old_jsonl(self, tmp_path, capsys):
        root = _make_root(tmp_path)
        stream = root / "runtime" / "event_stream"
        f = _write(stream / "runtime_events_2026-06-01_001.jsonl", b"event data\n" * 100)
        _aged(f, JSONL_COMPRESS_AGE_DAYS + 1)

        rc = cmd_execute(root, confirm=True, pretty=False)
        assert rc == 0
        assert (stream / "runtime_events_2026-06-01_001.jsonl.gz").exists()
        assert f.exists()  # original NOT deleted in Phase A

    def test_execute_never_deletes_jsonl(self, tmp_path, capsys):
        root = _make_root(tmp_path)
        stream = root / "runtime" / "event_stream"
        f = _write(stream / "runtime_events_old.jsonl", b"data" * 100)
        _aged(f, 100)
        rc = cmd_execute(root, confirm=True, pretty=False)
        assert rc == 0
        assert f.exists()  # JSONL always kept in Phase A

    def test_execute_blocked_by_active_session(self, tmp_path, capsys, monkeypatch):
        root = _make_root(tmp_path)
        # Patch _session_guard to simulate active session
        import flaos.log_governance as lg_mod
        monkeypatch.setattr(lg_mod, "_session_guard", lambda r: (False, ["99999"]))
        rc = cmd_execute(root, confirm=True, pretty=False)
        assert rc == 1
        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "STOP_AND_ESCALATE"
        assert "ACTIVE_SESSION_BLOCKED" in out["error_type"]

    def test_execute_hard_cap_respected(self, tmp_path, capsys):
        root = _make_root(tmp_path)
        logs = root / "logs"
        # Create more than MAX_ACTIONS backup files
        for n in range(LOG_BACKUP_KEEP + 1, LOG_BACKUP_KEEP + MAX_ACTIONS + 50):
            f = _write(logs / f"polytrade.log.{n}", b"x")
            _aged(f, 2)

        rc = cmd_execute(root, confirm=True, pretty=False)
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["total_actions"] <= MAX_ACTIONS


# ---------------------------------------------------------------------------
# Tests: session guard
# ---------------------------------------------------------------------------

class TestSessionGuard:
    def test_guard_passes_with_no_sessions(self, tmp_path):
        root = _make_root(tmp_path)
        ok, pids = _session_guard(root)
        assert ok
        assert pids == []

    def test_guard_passes_with_completed_session(self, tmp_path):
        root = _make_root(tmp_path)
        sessions_dir = root / "runtime" / "sessions"
        (sessions_dir / "session_001.json").write_text(
            json.dumps({"pid": 99999, "status": "COMPLETED"}), encoding="utf-8"
        )
        ok, pids = _session_guard(root)
        assert ok

    def test_guard_blocks_on_claimed_active_pid(self, tmp_path):
        root = _make_root(tmp_path)
        sessions_dir = root / "runtime" / "sessions"
        # Use current process PID which definitely exists
        (sessions_dir / "session_002.json").write_text(
            json.dumps({"pid": os.getpid(), "status": "ACTIVE"}), encoding="utf-8"
        )
        ok, pids = _session_guard(root)
        assert not ok
        assert str(os.getpid()) in pids


# ---------------------------------------------------------------------------
# Tests: report
# ---------------------------------------------------------------------------

class TestReport:
    def test_report_returns_current_sizes(self, tmp_path, capsys):
        root = _make_root(tmp_path)
        rc = cmd_report(root, pretty=False)
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert "current_sizes" in out
        assert "logs_mb" in out["current_sizes"]
