from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pytest

from utils.runtime_ownership import DuplicateRuntimeError, RuntimeOwnerManager, _utc_now


def _owner_payload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def mock_cmdline(monkeypatch):
    # By default, mock _get_process_cmdline to return a valid command line
    # for the test process IDs to keep baseline tests working.
    def _mock(pid):
        if pid in (1111, 1234, 2222, 3333):
            return "python main.py polymarket-adaptive-quant-engine"
        return None
    monkeypatch.setattr("utils.runtime_ownership._get_process_cmdline", _mock)


def test_paper_owner_acquire_writes_owner_and_heartbeat(tmp_path: Path) -> None:
    manager = RuntimeOwnerManager(owner_dir=tmp_path, pid=1234, run_id="run-a")

    owner = manager.acquire(mode="paper", override=False)

    payload = _owner_payload(tmp_path / "paper_runtime_owner.json")
    assert owner.acquired is True
    assert payload["pid"] == 1234
    assert payload["run_id"] == "run-a"
    assert payload["mode"] == "paper"
    assert payload["status"] == "active"
    assert payload["override"] is False
    assert payload["heartbeat_count"] == 0
    assert payload["owner_schema_version"] == "1.0"

    owner.heartbeat()
    payload = _owner_payload(tmp_path / "paper_runtime_owner.json")
    assert payload["heartbeat_count"] == 1
    assert payload["status"] == "active"


def test_paper_owner_blocks_duplicate_alive_owner(tmp_path: Path) -> None:
    first = RuntimeOwnerManager(owner_dir=tmp_path, pid=1111, run_id="run-a")
    first.acquire(mode="paper")
    second = RuntimeOwnerManager(
        owner_dir=tmp_path,
        pid=2222,
        run_id="run-b",
        process_checker=lambda pid: pid == 1111,
    )

    with pytest.raises(DuplicateRuntimeError) as excinfo:
        second.acquire(mode="paper")

    assert excinfo.value.existing_owner["pid"] == 1111
    assert excinfo.value.existing_owner["run_id"] == "run-a"
    assert _owner_payload(tmp_path / "paper_runtime_owner.json")["run_id"] == "run-a"


def test_paper_owner_override_allows_duplicate_and_marks_owner(tmp_path: Path) -> None:
    RuntimeOwnerManager(owner_dir=tmp_path, pid=1111, run_id="run-a").acquire(mode="paper")
    second = RuntimeOwnerManager(
        owner_dir=tmp_path,
        pid=2222,
        run_id="run-b",
        process_checker=lambda pid: pid == 1111,
    )

    owner = second.acquire(mode="paper", override=True)

    payload = _owner_payload(tmp_path / "paper_runtime_owner.json")
    assert owner.acquired is True
    assert payload["pid"] == 2222
    assert payload["run_id"] == "run-b"
    assert payload["override"] is True
    assert payload["previous_owner"]["pid"] == 1111
    assert payload["contamination_risk"] == "operator_override_duplicate_allowed"


def test_paper_owner_recovers_stale_dead_owner(tmp_path: Path) -> None:
    RuntimeOwnerManager(owner_dir=tmp_path, pid=1111, run_id="old-run").acquire(mode="paper")
    manager = RuntimeOwnerManager(
        owner_dir=tmp_path,
        pid=2222,
        run_id="new-run",
        process_checker=lambda pid: False,
    )

    owner = manager.acquire(mode="paper")

    payload = _owner_payload(tmp_path / "paper_runtime_owner.json")
    assert owner.acquired is True
    assert payload["pid"] == 2222
    assert payload["run_id"] == "new-run"
    assert payload["stale_owner_recovered"] is True
    assert payload["previous_owner"]["run_id"] == "old-run"


def test_paper_owner_release_only_matching_owner(tmp_path: Path) -> None:
    first = RuntimeOwnerManager(owner_dir=tmp_path, pid=1111, run_id="run-a")
    owner = first.acquire(mode="paper")
    RuntimeOwnerManager(owner_dir=tmp_path, pid=2222, run_id="run-b").acquire(mode="paper", override=True)

    assert owner.release() is False
    payload = _owner_payload(tmp_path / "paper_runtime_owner.json")
    assert payload["run_id"] == "run-b"

    current = RuntimeOwnerManager(owner_dir=tmp_path, pid=2222, run_id="run-b")
    current_owner = current.acquire(mode="paper", override=True)
    assert current_owner.release() is True
    assert not (tmp_path / "paper_runtime_owner.json").exists()


def test_corrupt_owner_file_recovers_in_24_7_mode(tmp_path: Path) -> None:
    # Under the new 24/7 reliability recovery patch, a corrupt/unreadable JSON file
    # is unlinked and archived rather than blocking the startup.
    owner_path = tmp_path / "paper_runtime_owner.json"
    owner_path.parent.mkdir(parents=True, exist_ok=True)
    owner_path.write_text("{not-json", encoding="utf-8")
    manager = RuntimeOwnerManager(owner_dir=tmp_path, pid=3333, run_id="run-c")

    owner = manager.acquire(mode="paper")
    assert owner.acquired is True
    payload = _owner_payload(owner_path)
    assert payload["run_id"] == "run-c"
    assert payload["stale_owner_recovered"] is True
    assert (tmp_path / "archive").exists()


# ── New Recovery Tests (PATCH_RUNTIME_001) ───────────────────────────────────

def test_stale_heartbeat_recovers(tmp_path: Path) -> None:
    manager_old = RuntimeOwnerManager(owner_dir=tmp_path, pid=1111, run_id="old-run")
    manager_old.acquire(mode="paper")
    
    # Overwrite the heartbeat time to be stale (older than 60s)
    owner_path = tmp_path / "paper_runtime_owner.json"
    payload = json.loads(owner_path.read_text(encoding="utf-8"))
    stale_time = (datetime.now(timezone.utc) - timedelta(seconds=70)).isoformat().replace("+00:00", "Z")
    payload["heartbeat_utc"] = stale_time
    owner_path.write_text(json.dumps(payload), encoding="utf-8")
    
    manager_new = RuntimeOwnerManager(
        owner_dir=tmp_path,
        pid=2222,
        run_id="new-run",
        process_checker=lambda pid: pid == 1111,
    )
    
    owner = manager_new.acquire(mode="paper")
    assert owner.acquired is True
    new_payload = _owner_payload(owner_path)
    assert new_payload["pid"] == 2222
    assert new_payload["stale_owner_recovered"] is True
    assert new_payload["previous_owner"]["pid"] == 1111


def test_pid_reused_by_non_runtime_process_recovers(tmp_path: Path, monkeypatch) -> None:
    manager_old = RuntimeOwnerManager(owner_dir=tmp_path, pid=1111, run_id="old-run")
    manager_old.acquire(mode="paper")
    
    # Mock cmdline for 1111 to be a non-runtime process (like chrome)
    monkeypatch.setattr("utils.runtime_ownership._get_process_cmdline", lambda pid: "chrome.exe --some-flags")
    
    manager_new = RuntimeOwnerManager(
        owner_dir=tmp_path,
        pid=2222,
        run_id="new-run",
        process_checker=lambda pid: pid == 1111,
    )
    
    owner = manager_new.acquire(mode="paper")
    assert owner.acquired is True
    new_payload = _owner_payload(tmp_path / "paper_runtime_owner.json")
    assert new_payload["pid"] == 2222
    assert new_payload["stale_owner_recovered"] is True


def test_stopping_owner_with_dead_pid_recovers_immediately(tmp_path: Path) -> None:
    manager_old = RuntimeOwnerManager(owner_dir=tmp_path, pid=1111, run_id="old-run")
    owner_old = manager_old.acquire(mode="paper")
    owner_old.mark_stopping()
    
    manager_new = RuntimeOwnerManager(
        owner_dir=tmp_path,
        pid=2222,
        run_id="new-run",
        process_checker=lambda pid: False,
    )
    
    owner = manager_new.acquire(mode="paper")
    assert owner.acquired is True
    new_payload = _owner_payload(tmp_path / "paper_runtime_owner.json")
    assert new_payload["pid"] == 2222
    assert new_payload["stale_owner_recovered"] is True


def test_stopping_owner_alive_fresh_blocks_startup(tmp_path: Path) -> None:
    manager_old = RuntimeOwnerManager(owner_dir=tmp_path, pid=1111, run_id="old-run")
    owner_old = manager_old.acquire(mode="paper")
    owner_old.mark_stopping()
    
    manager_new = RuntimeOwnerManager(
        owner_dir=tmp_path,
        pid=2222,
        run_id="new-run",
        process_checker=lambda pid: pid == 1111,
    )
    
    with pytest.raises(DuplicateRuntimeError) as excinfo:
        manager_new.acquire(mode="paper")
        
    assert excinfo.value.reason == "active_owner"


def test_stopping_owner_alive_stale_heartbeat_recovers(tmp_path: Path) -> None:
    manager_old = RuntimeOwnerManager(owner_dir=tmp_path, pid=1111, run_id="old-run")
    owner_old = manager_old.acquire(mode="paper")
    owner_old.mark_stopping()
    
    # Make heartbeat stale
    owner_path = tmp_path / "paper_runtime_owner.json"
    payload = json.loads(owner_path.read_text(encoding="utf-8"))
    stale_time = (datetime.now(timezone.utc) - timedelta(seconds=70)).isoformat().replace("+00:00", "Z")
    payload["heartbeat_utc"] = stale_time
    owner_path.write_text(json.dumps(payload), encoding="utf-8")
    
    manager_new = RuntimeOwnerManager(
        owner_dir=tmp_path,
        pid=2222,
        run_id="new-run",
        process_checker=lambda pid: pid == 1111,
    )
    
    owner = manager_new.acquire(mode="paper")
    assert owner.acquired is True
    new_payload = _owner_payload(owner_path)
    assert new_payload["pid"] == 2222
    assert new_payload["stale_owner_recovered"] is True


def test_stale_startup_lock_recovers(tmp_path: Path) -> None:
    lock_path = tmp_path / "paper_runtime_owner.startup.lock"
    # Write lock file with a dead PID (1111) and old timestamp
    old_time = (datetime.now(timezone.utc) - timedelta(seconds=20)).isoformat().replace("+00:00", "Z")
    lock_path.write_text(f"1111\nold-run\n{old_time}\n", encoding="utf-8")
    
    manager = RuntimeOwnerManager(
        owner_dir=tmp_path,
        pid=2222,
        run_id="new-run",
        process_checker=lambda pid: False,
    )
    
    owner = manager.acquire(mode="paper")
    assert owner.acquired is True
    assert not lock_path.exists()
    
    new_payload = _owner_payload(tmp_path / "paper_runtime_owner.json")
    assert new_payload["pid"] == 2222


def test_stale_owner_archived_before_removal(tmp_path: Path) -> None:
    manager_old = RuntimeOwnerManager(owner_dir=tmp_path, pid=1111, run_id="old-run")
    manager_old.acquire(mode="paper")
    
    manager_new = RuntimeOwnerManager(
        owner_dir=tmp_path,
        pid=2222,
        run_id="new-run",
        process_checker=lambda pid: False,
    )
    
    manager_new.acquire(mode="paper")
    
    # Assert archive exists with a backup file
    archive_dir = tmp_path / "archive"
    assert archive_dir.exists()
    backups = list(archive_dir.glob("*.json"))
    assert len(backups) == 1
    
    backup_payload = json.loads(backups[0].read_text(encoding="utf-8"))
    assert backup_payload["pid"] == 1111
    assert backup_payload["run_id"] == "old-run"


def test_telemetry_emitted_during_recovery(tmp_path: Path) -> None:
    emitted_events = []
    
    def mock_telemetry(category, payload):
        emitted_events.append((category, payload))
        
    manager_old = RuntimeOwnerManager(owner_dir=tmp_path, pid=1111, run_id="old-run")
    manager_old.acquire(mode="paper")
    
    manager_new = RuntimeOwnerManager(
        owner_dir=tmp_path,
        pid=2222,
        run_id="new-run",
        process_checker=lambda pid: False,
        telemetry_emit=mock_telemetry,
    )
    
    manager_new.acquire(mode="paper")
    
    # Telemetry should capture both detected and recovered events
    event_types = [payload.get("event_type") for _, payload in emitted_events]
    assert "stale_owner_detected" in event_types
    assert "stale_owner_recovered" in event_types
    
    detected_event = [p for _, p in emitted_events if p.get("event_type") == "stale_owner_detected"][0]
    assert detected_event["existing_pid"] == 1111
    assert detected_event["existing_run_id"] == "old-run"
    assert detected_event["recovery_reason"] == "dead_pid"
