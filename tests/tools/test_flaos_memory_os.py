"""Tests for FLAOS Memory OS v2 library and migration tool."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from flaos.memory_os import (
    append_memory,
    append_and_index,
    generate_memory_id,
    load_memory,
    load_memory_at_offset,
    tail_memory,
    update_index,
    validate_record,
    REQUIRED_FIELDS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_mem(tmp_path):
    """Temp directory mimicking docs/operations/memory/"""
    return tmp_path / "memory"


def _valid_record(overrides: dict | None = None) -> dict:
    rec = {
        "memory_id": "TEST-20260627-abc123",
        "memory_type": "decision",
        "created_at": "2026-06-27T00:00:00Z",
        "updated_at": "2026-06-27T00:00:00Z",
        "source": "test_task",
        "agent": "29_ARCHITECTURE_GOVERNANCE_AGENT",
        "tool": None,
        "confidence": 0.9,
        "importance": 0.8,
        "tags": ["test"],
        "expires": "2026-12-27",
        "evidence_level": "B",
        "version": 1,
        "summary": "Test memory record",
        "payload": {},
        "related_tasks": [],
        "related_files": [],
        "related_decisions": [],
    }
    if overrides:
        rec.update(overrides)
    return rec


# ---------------------------------------------------------------------------
# Tests: generate_memory_id
# ---------------------------------------------------------------------------

class TestGenerateMemoryId:
    def test_stable_prefix_for_safety(self):
        mid = generate_memory_id("safety", "some_task")
        assert mid.startswith("QS-")

    def test_stable_prefix_for_decision(self):
        mid = generate_memory_id("decision", "BATCH_3C_GATE_CHECK_001")
        assert mid.startswith("DEC-")

    def test_contains_date_portion(self):
        mid = generate_memory_id("loop", "test_loop")
        parts = mid.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 8  # YYYYMMDD
        assert parts[1].isdigit()

    def test_different_tasks_produce_different_ids(self):
        a = generate_memory_id("decision", "TASK_A")
        b = generate_memory_id("decision", "TASK_B")
        assert a != b


# ---------------------------------------------------------------------------
# Tests: validate_record
# ---------------------------------------------------------------------------

class TestValidateRecord:
    def test_valid_record_passes(self):
        ok, err = validate_record(_valid_record())
        assert ok, err

    def test_missing_required_field_fails(self):
        rec = _valid_record()
        del rec["memory_id"]
        ok, err = validate_record(rec)
        assert not ok
        assert "memory_id" in err

    def test_invalid_memory_type_fails(self):
        rec = _valid_record({"memory_type": "foobar"})
        ok, err = validate_record(rec)
        assert not ok

    def test_confidence_out_of_range_fails(self):
        rec = _valid_record({"confidence": 1.5})
        ok, err = validate_record(rec)
        assert not ok

    def test_invalid_evidence_level_fails(self):
        rec = _valid_record({"evidence_level": "Z"})
        ok, err = validate_record(rec)
        assert not ok

    def test_safety_with_expires_set_fails(self):
        rec = _valid_record({"memory_type": "safety", "expires": "2026-12-27"})
        ok, err = validate_record(rec)
        assert not ok

    def test_safety_with_null_expires_passes(self):
        rec = _valid_record({"memory_type": "safety", "expires": None})
        ok, err = validate_record(rec)
        assert ok, err


# ---------------------------------------------------------------------------
# Tests: append/load/tail
# ---------------------------------------------------------------------------

class TestAppendLoadTail:
    def test_append_creates_file(self, tmp_path):
        target = tmp_path / "test.jsonl"
        rec = _valid_record()
        fpath, offset = append_memory("decision", rec, file_path=target)
        assert target.exists()
        assert offset == 0

    def test_append_second_record_has_nonzero_offset(self, tmp_path):
        target = tmp_path / "test.jsonl"
        rec1 = _valid_record({"memory_id": "AAA-001"})
        rec2 = _valid_record({"memory_id": "BBB-002"})
        _, off1 = append_memory("decision", rec1, file_path=target)
        _, off2 = append_memory("decision", rec2, file_path=target)
        assert off1 == 0
        assert off2 > 0

    def test_load_by_id(self, tmp_path):
        target = tmp_path / "test.jsonl"
        rec = _valid_record({"memory_id": "FIND-ME"})
        append_memory("decision", rec, file_path=target)
        loaded = load_memory("decision", "FIND-ME", file_path=target)
        assert loaded is not None
        assert loaded["memory_id"] == "FIND-ME"

    def test_load_at_offset(self, tmp_path):
        target = tmp_path / "test.jsonl"
        append_memory("decision", _valid_record({"memory_id": "A"}), file_path=target)
        _, offset = append_memory("decision", _valid_record({"memory_id": "B"}), file_path=target)
        loaded = load_memory_at_offset(target, offset)
        assert loaded is not None
        assert loaded["memory_id"] == "B"

    def test_tail_returns_last_n(self, tmp_path):
        target = tmp_path / "test.jsonl"
        for i in range(5):
            append_memory("decision", _valid_record({"memory_id": f"REC-{i:03d}", "summary": f"record {i}"}), file_path=target)
        results = tail_memory("decision", limit=3, file_path=target)
        assert len(results) == 3
        assert results[-1]["memory_id"] == "REC-004"

    def test_invalid_record_rejected_on_append(self, tmp_path):
        target = tmp_path / "test.jsonl"
        bad_rec = _valid_record()
        del bad_rec["confidence"]
        with pytest.raises(ValueError, match="confidence"):
            append_memory("decision", bad_rec, file_path=target)


# ---------------------------------------------------------------------------
# Tests: index
# ---------------------------------------------------------------------------

class TestIndex:
    def test_append_and_index_returns_memory_id(self, tmp_path, monkeypatch):
        import flaos.memory_os as mos
        index_file = tmp_path / "MEMORY_INDEX.json"
        target = tmp_path / "test.jsonl"
        monkeypatch.setattr(mos, "INDEX_PATH", index_file)
        rec = _valid_record()
        mid = append_and_index("decision", rec, file_path=target)
        assert mid == rec["memory_id"]
        assert index_file.exists()

    def test_index_contains_byte_offset(self, tmp_path, monkeypatch):
        import flaos.memory_os as mos
        index_file = tmp_path / "MEMORY_INDEX.json"
        target = tmp_path / "test.jsonl"
        monkeypatch.setattr(mos, "INDEX_PATH", index_file)
        rec1 = _valid_record({"memory_id": "IDX-001"})
        rec2 = _valid_record({"memory_id": "IDX-002"})
        append_and_index("decision", rec1, file_path=target)
        append_and_index("decision", rec2, file_path=target)
        idx = json.loads(index_file.read_text(encoding="utf-8"))
        assert "IDX-001" in idx["entries"]
        assert "IDX-002" in idx["entries"]
        assert idx["entries"]["IDX-002"]["byte_offset"] > 0


# ---------------------------------------------------------------------------
# Tests: migration
# ---------------------------------------------------------------------------

class TestMigration:
    def test_dry_run_does_not_create_files(self, tmp_path, monkeypatch):
        import flaos.memory_migrate as mm
        import flaos.memory_os as mos

        # Create a minimal v1 source
        v1 = tmp_path / "LOOP_MEMORY_v1.json"
        entries = [
            {"loop_id": "TEST_LOOP_001", "task_class": 3, "result": "PASS",
             "repairs": 0, "evidence_grade": "B", "date": "2026-06-27",
             "commits": ["abc1234"], "next_recommendation": "next task"},
        ]
        v1.write_text(json.dumps(entries), encoding="utf-8")

        target = tmp_path / "loop.jsonl"
        safety = tmp_path / "safety.jsonl"
        idx = tmp_path / "index.json"

        monkeypatch.setattr(mm, "V1_SOURCE", v1)
        monkeypatch.setattr(mm, "LOOP_TARGET", target)
        monkeypatch.setattr(mm, "SAFETY_TARGET", safety)
        monkeypatch.setattr(mos, "INDEX_PATH", idx)

        result = mm.migrate(dry_run=True)
        assert result["mode"] == "DRY_RUN"
        assert not target.exists()
        assert not safety.exists()
        assert result["v1_file_deleted"] is False

    def test_execute_migrates_all_entries(self, tmp_path, monkeypatch):
        import flaos.memory_migrate as mm
        import flaos.memory_os as mos

        v1 = tmp_path / "LOOP_MEMORY_v1.json"
        n_entries = 5
        entries = [
            {"loop_id": f"LOOP_{i:03d}", "task_class": 3, "result": "PASS",
             "repairs": 0, "evidence_grade": "B", "date": "2026-06-27",
             "commits": [], "next_recommendation": ""}
            for i in range(n_entries)
        ]
        v1.write_text(json.dumps(entries), encoding="utf-8")

        target = tmp_path / "loop" / "2026" / "06" / "2026-06-27.jsonl"
        safety = tmp_path / "safety" / "SAFETY_MEMORY.jsonl"
        idx = tmp_path / "MEMORY_INDEX.json"

        monkeypatch.setattr(mm, "V1_SOURCE", v1)
        monkeypatch.setattr(mm, "LOOP_TARGET", target)
        monkeypatch.setattr(mm, "SAFETY_TARGET", safety)
        monkeypatch.setattr(mos, "INDEX_PATH", idx)

        result = mm.migrate(dry_run=False)
        assert result["entries_migrated"] == n_entries
        assert target.exists()
        records = [json.loads(l) for l in target.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(records) == n_entries

    def test_migration_does_not_delete_v1_file(self, tmp_path, monkeypatch):
        import flaos.memory_migrate as mm
        import flaos.memory_os as mos

        v1 = tmp_path / "v1.json"
        v1.write_text(json.dumps([
            {"loop_id": "X", "task_class": 3, "result": "PASS", "repairs": 0,
             "evidence_grade": "D", "date": "2026-06-27", "commits": [], "next_recommendation": ""}
        ]), encoding="utf-8")

        monkeypatch.setattr(mm, "V1_SOURCE", v1)
        monkeypatch.setattr(mm, "LOOP_TARGET", tmp_path / "l.jsonl")
        monkeypatch.setattr(mm, "SAFETY_TARGET", tmp_path / "s.jsonl")
        monkeypatch.setattr(mos, "INDEX_PATH", tmp_path / "idx.json")

        mm.migrate(dry_run=False)
        assert v1.exists()  # NOT deleted

    def test_safety_memory_seeded_with_qs001_to_010(self, tmp_path, monkeypatch):
        import flaos.memory_migrate as mm
        import flaos.memory_os as mos

        v1 = tmp_path / "v1.json"
        v1.write_text("[]", encoding="utf-8")

        safety = tmp_path / "safety.jsonl"
        monkeypatch.setattr(mm, "V1_SOURCE", v1)
        monkeypatch.setattr(mm, "LOOP_TARGET", tmp_path / "l.jsonl")
        monkeypatch.setattr(mm, "SAFETY_TARGET", safety)
        monkeypatch.setattr(mos, "INDEX_PATH", tmp_path / "idx.json")

        result = mm.migrate(dry_run=False)
        assert result["safety_entries_seeded"] == 10

        records = [json.loads(l) for l in safety.read_text(encoding="utf-8").splitlines() if l.strip()]
        ids = {r["memory_id"] for r in records}
        for i in range(1, 11):
            assert f"QS-{i:03d}" in ids
