"""Tests for Memory OS V2 integration in FLAOS bootstrap."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import flaos.bootstrap as bs


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_minimal_state(tmp_path: Path, task_class: int = 4,
                        tier: str = "STANDARD") -> Path:
    """Write a minimal ACTIVE_WORKFLOW_STATE_001.json."""
    f = tmp_path / "ACTIVE_WORKFLOW_STATE_001.json"
    f.write_text(json.dumps({
        "$schema": "active_workflow_state_v1",
        "next_task": "TEST_TASK_001",
        "next_workflow_tier": tier,
        "blocked": False,
        "current_phase": "test",
        "last_completed_task": "prev",
        "last_commit": "abc",
    }), encoding="utf-8")
    return f


def _seed_safety_memory(safety_dir: Path, count: int = 10) -> Path:
    safety_dir.mkdir(parents=True, exist_ok=True)
    f = safety_dir / "SAFETY_MEMORY.jsonl"
    lines = []
    for i in range(1, count + 1):
        rec = {
            "memory_id": f"QS-{i:03d}",
            "memory_type": "safety",
            "expires": None,
            "summary": f"Safety entry {i}",
        }
        lines.append(json.dumps(rec))
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f


def _seed_index(mem_base: Path, safety_file: Path) -> Path:
    idx_file = mem_base / "MEMORY_INDEX_001.json"
    idx_file.write_text(json.dumps({
        "$schema": "memory_index_v2",
        "entry_count": 10,
        "entries": {},
        "safety_memory_file": str(safety_file),
    }), encoding="utf-8")
    return idx_file


# ---------------------------------------------------------------------------
# Tests: _load_safety_memory
# ---------------------------------------------------------------------------

class TestLoadSafetyMemory:
    def test_loaded_when_safety_file_exists_with_10_entries(self, tmp_path, monkeypatch):
        sm = _seed_safety_memory(tmp_path / "safety")
        monkeypatch.setattr(bs, "SAFETY_MEMORY_PATH", sm)
        monkeypatch.setattr(bs, "MEMORY_INDEX_PATH", tmp_path / "nonexistent.json")

        idx_loaded, safety_loaded, ids, status = bs._load_safety_memory()
        assert safety_loaded is True
        assert len(ids) == 10
        assert "QS-001" in ids
        assert status == "LOADED"

    def test_index_loaded_when_present(self, tmp_path, monkeypatch):
        sm = _seed_safety_memory(tmp_path / "safety")
        idx = _seed_index(tmp_path, sm)
        monkeypatch.setattr(bs, "SAFETY_MEMORY_PATH", sm)
        monkeypatch.setattr(bs, "MEMORY_INDEX_PATH", idx)

        idx_loaded, _, _, _ = bs._load_safety_memory()
        assert idx_loaded is True

    def test_missing_or_invalid_when_safety_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(bs, "SAFETY_MEMORY_PATH", tmp_path / "missing.jsonl")
        monkeypatch.setattr(bs, "MEMORY_INDEX_PATH", tmp_path / "missing_idx.json")

        _, safety_loaded, ids, status = bs._load_safety_memory()
        assert not safety_loaded
        assert len(ids) == 0
        assert status == "MISSING_OR_INVALID"

    def test_missing_or_invalid_when_invalid_jsonl(self, tmp_path, monkeypatch):
        sm = tmp_path / "safety" / "SAFETY_MEMORY.jsonl"
        sm.parent.mkdir(parents=True)
        sm.write_text("not valid json\n", encoding="utf-8")
        monkeypatch.setattr(bs, "SAFETY_MEMORY_PATH", sm)
        monkeypatch.setattr(bs, "MEMORY_INDEX_PATH", tmp_path / "i.json")

        _, safety_loaded, ids, status = bs._load_safety_memory()
        assert not safety_loaded
        assert status == "MISSING_OR_INVALID"


# ---------------------------------------------------------------------------
# Tests: build_snapshot with safety memory
# ---------------------------------------------------------------------------

class TestBuildSnapshotSafetyMemory:
    """These tests patch the real FILES dict to avoid modifying real state."""

    def _make_flaos_files(self, tmp: Path) -> dict:
        """Return patched FILES paths pointing to real operational files (read-only use)."""
        return dict(bs.FILES)  # use real files — tests are read-only

    def test_snapshot_includes_safety_memory_count(self, capsys, monkeypatch):
        """Normal run: safety memory is loaded and count appears in snapshot."""
        # Patch to real files (they exist)
        monkeypatch.setattr(bs, "MEMORY_INDEX_PATH",
                            bs.ROOT / "docs/operations/memory/MEMORY_INDEX_001.json")
        monkeypatch.setattr(bs, "SAFETY_MEMORY_PATH",
                            bs.ROOT / "docs/operations/memory/safety/SAFETY_MEMORY.jsonl")

        rc = bs.build_snapshot(pretty=False, diagnose=False)
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out.get("safety_memory_loaded") is True
        assert out.get("safety_memory_count") == 10

    def test_snapshot_includes_safety_ids(self, capsys, monkeypatch):
        monkeypatch.setattr(bs, "MEMORY_INDEX_PATH",
                            bs.ROOT / "docs/operations/memory/MEMORY_INDEX_001.json")
        monkeypatch.setattr(bs, "SAFETY_MEMORY_PATH",
                            bs.ROOT / "docs/operations/memory/safety/SAFETY_MEMORY.jsonl")

        rc = bs.build_snapshot(pretty=False, diagnose=False)
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        ids = out.get("safety_memory_ids", [])
        assert "QS-001" in ids
        assert "QS-010" in ids

    def test_diagnose_includes_memory_os_v2_fields(self, capsys, monkeypatch):
        monkeypatch.setattr(bs, "MEMORY_INDEX_PATH",
                            bs.ROOT / "docs/operations/memory/MEMORY_INDEX_001.json")
        monkeypatch.setattr(bs, "SAFETY_MEMORY_PATH",
                            bs.ROOT / "docs/operations/memory/safety/SAFETY_MEMORY.jsonl")

        rc = bs.build_snapshot(pretty=False, diagnose=True)
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        mem = out["diagnose"]["memory_os_v2"]
        assert mem["safety_memory_loaded"] is True
        assert mem["safety_memory_count"] == 10
        assert mem["safety_memory_status"] == "LOADED"
        assert "memory_index_loaded" in mem
        assert "safety_memory_required" in mem

    def test_tooling_task_stops_if_safety_missing(self, tmp_path, capsys, monkeypatch):
        """Class 4 (tooling) task must stop if safety memory is missing."""
        from unittest.mock import patch

        monkeypatch.setattr(bs, "SAFETY_MEMORY_PATH", tmp_path / "missing.jsonl")
        monkeypatch.setattr(bs, "MEMORY_INDEX_PATH", tmp_path / "i.json")
        monkeypatch.setattr(bs, "SAFETY_MEMORY_REQUIRED_TASK_CLASSES", {4, 6, 7, 8})
        monkeypatch.setattr(bs, "SAFETY_MEMORY_REQUIRED_TIERS", {"GATE", "STANDARD"})

        # The current next_task is class 4 STANDARD → safety required and missing → STOP
        with pytest.raises(SystemExit) as exc:
            bs.build_snapshot(pretty=False, diagnose=False)
        assert exc.value.code == 1
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["status"] == "STOP_AND_ESCALATE"
        assert "SAFETY_MEMORY" in data["error_type"]

    def test_docs_task_degrades_if_safety_missing(self, tmp_path, capsys, monkeypatch):
        """Class 3 (docs) LOOP task degrades (not stops) if safety missing."""
        monkeypatch.setattr(bs, "SAFETY_MEMORY_PATH", tmp_path / "missing.jsonl")
        monkeypatch.setattr(bs, "MEMORY_INDEX_PATH", tmp_path / "i.json")
        monkeypatch.setattr(bs, "SAFETY_MEMORY_REQUIRED_TASK_CLASSES", {4, 6, 7, 8})
        monkeypatch.setattr(bs, "SAFETY_MEMORY_REQUIRED_TIERS", {"GATE", "STANDARD"})

        # Patch current next_task to be Class 3 LOOP (docs only)
        # We do this by patching what _next_task_entry returns
        original_next = bs._next_task_entry

        def patched_next(queue_data, task_id):
            entry = original_next(queue_data, task_id)
            if entry:
                entry = dict(entry)
                entry["task_class"] = 3
                entry["workflow_tier"] = "LOOP"
            return entry

        # Also patch state to have a LOOP tier
        original_state_load = bs._load_file_or_fail

        def patched_load(key):
            d = original_state_load(key)
            if key == "state":
                d = dict(d)
                d["next_workflow_tier"] = "LOOP"
            return d

        monkeypatch.setattr(bs, "_next_task_entry", patched_next)
        monkeypatch.setattr(bs, "_load_file_or_fail", patched_load)

        # Should NOT raise SystemExit 1 — safety not required for class 3 LOOP
        rc = bs.build_snapshot(pretty=False, diagnose=False)
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["safety_memory_status"] == "DEGRADED"

    def test_memory_os_v2_enabled_in_snapshot(self, capsys, monkeypatch):
        monkeypatch.setattr(bs, "MEMORY_INDEX_PATH",
                            bs.ROOT / "docs/operations/memory/MEMORY_INDEX_001.json")
        monkeypatch.setattr(bs, "SAFETY_MEMORY_PATH",
                            bs.ROOT / "docs/operations/memory/safety/SAFETY_MEMORY.jsonl")

        rc = bs.build_snapshot(pretty=False, diagnose=False)
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out.get("memory_os_v2_enabled") is True
