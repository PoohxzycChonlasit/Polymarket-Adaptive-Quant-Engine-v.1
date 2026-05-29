from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from utils.runtime_ownership import DuplicateRuntimeError, RuntimeOwnerManager


def _owner_payload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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


def test_corrupt_owner_file_fails_closed_without_override(tmp_path: Path) -> None:
    owner_path = tmp_path / "paper_runtime_owner.json"
    owner_path.parent.mkdir(parents=True, exist_ok=True)
    owner_path.write_text("{not-json", encoding="utf-8")
    manager = RuntimeOwnerManager(owner_dir=tmp_path, pid=3333, run_id="run-c")

    with pytest.raises(DuplicateRuntimeError) as excinfo:
        manager.acquire(mode="paper")

    assert excinfo.value.reason == "owner_file_unreadable"

    owner = manager.acquire(mode="paper", override=True)
    assert owner.acquired is True
    assert _owner_payload(owner_path)["run_id"] == "run-c"
