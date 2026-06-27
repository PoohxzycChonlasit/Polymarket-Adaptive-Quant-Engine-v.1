"""
FLAOS Memory OS v2 — Core Library.

Provides append/load/tail/index operations over typed JSONL memory files.
Standard library only. No polymarket imports.

Memory base: docs/operations/memory/
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
MEMORY_BASE = ROOT / "docs" / "operations" / "memory"
INDEX_PATH = MEMORY_BASE / "MEMORY_INDEX_001.json"

MEMORY_TYPE_DIRS: dict[str, Path] = {
    "loop":        MEMORY_BASE / "loop",
    "safety":      MEMORY_BASE / "safety",
    "decision":    MEMORY_BASE / "decision",
    "failure":     MEMORY_BASE / "failure",
    "repair":      MEMORY_BASE / "repair",
    "execution":   MEMORY_BASE / "execution",
    "runtime":     MEMORY_BASE / "runtime",
    "repository":  MEMORY_BASE / "repository",
    "research":    MEMORY_BASE / "research",
    "quant":       MEMORY_BASE / "quant",
    "tool":        MEMORY_BASE / "tool",
    "skill":       MEMORY_BASE / "skill",
    "agent":       MEMORY_BASE / "agent",
    "planning":    MEMORY_BASE / "planning",
    "permanent":   MEMORY_BASE / "permanent",
    "session":     MEMORY_BASE / "session",
}

PERMANENT_TYPES = {"safety", "permanent", "repository"}

REQUIRED_FIELDS = {
    "memory_id", "memory_type", "created_at", "source",
    "confidence", "evidence_level", "summary",
}


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------

def generate_memory_id(memory_type: str, source_task: str, suffix: str = "") -> str:
    """Generate a stable, unique memory ID.

    Format: {TYPE_PREFIX}-{YYYYMMDD}-{HASH6}
    """
    prefix_map = {
        "decision": "DEC", "failure": "FAIL", "repair": "REP",
        "runtime": "RT", "repository": "REPO", "safety": "QS",
        "loop": "LOOP", "planning": "PLAN", "tool": "TOOL",
        "skill": "SKILL", "agent": "AGENT", "session": "SES",
        "execution": "EXEC", "research": "RES", "quant": "QK",
        "permanent": "PERM",
    }
    prefix = prefix_map.get(memory_type, memory_type.upper()[:4])
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    raw = f"{memory_type}|{source_task}|{suffix}|{date_str}"
    hash6 = hashlib.sha1(raw.encode()).hexdigest()[:6]
    return f"{prefix}-{date_str}-{hash6}"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_record(record: dict[str, Any]) -> tuple[bool, str]:
    """Validate a memory record against required schema.

    Returns (is_valid, error_message).
    """
    missing = REQUIRED_FIELDS - set(record.keys())
    if missing:
        return False, f"Missing required fields: {sorted(missing)}"

    mtype = record.get("memory_type", "")
    valid_types = set(MEMORY_TYPE_DIRS.keys())
    if mtype not in valid_types:
        return False, f"Invalid memory_type '{mtype}'. Must be one of: {sorted(valid_types)}"

    conf = record.get("confidence")
    if not isinstance(conf, (int, float)) or not (0.0 <= float(conf) <= 1.0):
        return False, f"confidence must be float 0.0-1.0, got {conf!r}"

    ev = record.get("evidence_level", "")
    if ev not in ("A", "B", "C", "D", "E"):
        return False, f"evidence_level must be A/B/C/D/E, got {ev!r}"

    if mtype in PERMANENT_TYPES:
        if record.get("expires") is not None:
            return False, f"memory_type '{mtype}' must have expires=null (permanent)"

    return True, ""


# ---------------------------------------------------------------------------
# Default memory file path per type
# ---------------------------------------------------------------------------

def _default_file(memory_type: str) -> Path:
    base = MEMORY_TYPE_DIRS.get(memory_type, MEMORY_BASE / memory_type)
    base.mkdir(parents=True, exist_ok=True)
    if memory_type == "loop":
        today = datetime.now(timezone.utc)
        dated = base / str(today.year) / f"{today.month:02d}"
        dated.mkdir(parents=True, exist_ok=True)
        return dated / f"{today.strftime('%Y-%m-%d')}.jsonl"
    elif memory_type == "safety":
        return base / "SAFETY_MEMORY.jsonl"
    else:
        return base / f"{memory_type.upper()}_MEMORY.jsonl"


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------

def append_memory(memory_type: str, record: dict[str, Any],
                  file_path: Path | None = None) -> tuple[Path, int]:
    """Append a memory record to the appropriate JSONL file.

    Returns (file_path, byte_offset_of_record).
    Validates the record before writing.
    """
    ok, err = validate_record(record)
    if not ok:
        raise ValueError(f"Invalid memory record: {err}")

    if "created_at" not in record or not record["created_at"]:
        record["created_at"] = datetime.now(timezone.utc).isoformat()
    if "updated_at" not in record:
        record["updated_at"] = record["created_at"]
    if "version" not in record:
        record["version"] = 1

    target = file_path or _default_file(memory_type)
    target.parent.mkdir(parents=True, exist_ok=True)

    # Get byte offset before appending
    offset = target.stat().st_size if target.exists() else 0
    line = json.dumps(record, ensure_ascii=False) + "\n"
    with target.open("a", encoding="utf-8") as f:
        f.write(line)

    return target, offset


def load_memory(memory_type: str, memory_id: str,
                file_path: Path | None = None) -> dict[str, Any] | None:
    """Load a specific memory record by memory_id.

    Scans the JSONL file sequentially. Use index for byte_offset lookup for O(1) access.
    """
    target = file_path or _default_file(memory_type)
    if not target.exists():
        return None
    with target.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if rec.get("memory_id") == memory_id:
                    return rec
            except json.JSONDecodeError:
                continue
    return None


def load_memory_at_offset(file_path: Path, byte_offset: int) -> dict[str, Any] | None:
    """Load a memory record using a known byte offset (O(1) from index)."""
    if not file_path.exists():
        return None
    with file_path.open("rb") as f:
        f.seek(byte_offset)
        line = f.readline().decode("utf-8").strip()
        if not line:
            return None
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return None


def tail_memory(memory_type: str, limit: int = 10,
                file_path: Path | None = None) -> list[dict[str, Any]]:
    """Return the latest N records from a memory file."""
    target = file_path or _default_file(memory_type)
    if not target.exists():
        return []
    records: list[dict[str, Any]] = []
    with target.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records[-limit:]


# ---------------------------------------------------------------------------
# Index management
# ---------------------------------------------------------------------------

def _load_index() -> dict[str, Any]:
    if INDEX_PATH.exists():
        try:
            return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "$schema": "memory_index_v2",
        "last_updated": "",
        "entry_count": 0,
        "entries": {},
    }


def _save_index(index: dict[str, Any]) -> None:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    index["last_updated"] = datetime.now(timezone.utc).isoformat()
    INDEX_PATH.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")


def update_index(record: dict[str, Any], file_path: Path, byte_offset: int) -> None:
    """Add or update an entry in the Memory Index."""
    index = _load_index()
    memory_id = record.get("memory_id", "")
    if not memory_id:
        return
    index["entries"][memory_id] = {
        "memory_id": memory_id,
        "memory_type": record.get("memory_type", ""),
        "task_id": record.get("task_id", record.get("loop_id", "")),
        "summary": record.get("summary", "")[:120],
        "tags": record.get("tags", []),
        "importance": record.get("importance", 0.5),
        "confidence": record.get("confidence", 0.5),
        "evidence_level": record.get("evidence_level", "D"),
        "created_at": record.get("created_at", ""),
        "expires": record.get("expires"),
        "file": str(file_path.relative_to(ROOT)) if file_path.is_relative_to(ROOT) else str(file_path),
        "byte_offset": byte_offset,
    }
    index["entry_count"] = len(index["entries"])
    _save_index(index)


def append_and_index(memory_type: str, record: dict[str, Any],
                     file_path: Path | None = None) -> str:
    """Append a record and update the index. Returns memory_id."""
    if "memory_id" not in record:
        source = record.get("task_id", record.get("loop_id", record.get("source", "unknown")))
        record["memory_id"] = generate_memory_id(memory_type, source)
    fpath, offset = append_memory(memory_type, record, file_path)
    update_index(record, fpath, offset)
    return record["memory_id"]
