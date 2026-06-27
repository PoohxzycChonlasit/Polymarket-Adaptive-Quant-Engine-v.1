"""
FLAOS Memory OS v2 — Migration Tool.

Reads old LOOP_MEMORY_20260627_001.json (v1 JSON array) and:
  1. Writes each entry as a JSONL line to memory/loop/2026/06/2026-06-27.jsonl
  2. Builds MEMORY_INDEX_001.json
  3. Seeds SAFETY_MEMORY.jsonl with QS-001..QS-010

NON-DESTRUCTIVE: old memory files are never deleted or modified.

Usage:
    python tools/flaos/memory_migrate.py --dry-run
    python tools/flaos/memory_migrate.py --execute
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from flaos.memory_os import (
    ROOT as MEM_ROOT,
    MEMORY_BASE,
    INDEX_PATH,
    append_and_index,
    append_memory,
    update_index,
    validate_record,
    _default_file,
    _load_index,
    _save_index,
)

# ---------------------------------------------------------------------------
# Source v1 file
# ---------------------------------------------------------------------------

V1_SOURCE = ROOT / "docs" / "operations" / "loop_memory" / "LOOP_MEMORY_20260627_001.json"
LOOP_TARGET = MEMORY_BASE / "loop" / "2026" / "06" / "2026-06-27.jsonl"
SAFETY_TARGET = MEMORY_BASE / "safety" / "SAFETY_MEMORY.jsonl"

# ---------------------------------------------------------------------------
# Safety memory seed — QS-001..QS-010
# ---------------------------------------------------------------------------

SAFETY_ENTRIES = [
    {
        "memory_id": "QS-001",
        "memory_type": "safety",
        "created_at": "2026-06-27T00:00:00Z",
        "updated_at": "2026-06-27T00:00:00Z",
        "source": "BATCH_3B_DESIGN_REVIEW_001",
        "agent": "29_ARCHITECTURE_GOVERNANCE_AGENT",
        "tool": None,
        "confidence": 1.0,
        "importance": 1.0,
        "tags": ["permanent", "execution_path", "never_extract"],
        "expires": None,
        "evidence_level": "B",
        "version": 1,
        "summary": "_phase4_build_quote_lineage is PERMANENT — called from live order submission path",
        "payload": {
            "forbidden_method": "_phase4_build_quote_lineage",
            "reason": "Called from live order submission path (lines 4338, 11583, 11689). Extraction creates execution-path coupling.",
            "severity": "CRITICAL",
            "file": "polymarket/trader.py",
        },
        "related_tasks": ["BATCH_3B_DESIGN_REVIEW_001"],
        "related_files": ["polymarket/trader.py"],
        "related_decisions": [],
    },
    {
        "memory_id": "QS-002",
        "memory_type": "safety",
        "created_at": "2026-06-27T00:00:00Z",
        "updated_at": "2026-06-27T00:00:00Z",
        "source": "BATCH_3B_DESIGN_REVIEW_001",
        "agent": "29_ARCHITECTURE_GOVERNANCE_AGENT",
        "tool": None,
        "confidence": 1.0,
        "importance": 1.0,
        "tags": ["permanent", "execution_path", "never_extract"],
        "expires": None,
        "evidence_level": "B",
        "version": 1,
        "summary": "_phase4_quote_lineage_carry is PERMANENT — execution path",
        "payload": {
            "forbidden_method": "_phase4_quote_lineage_carry",
            "reason": "Called from execution path. Same rationale as QS-001.",
            "severity": "CRITICAL",
            "file": "polymarket/trader.py",
        },
        "related_tasks": ["BATCH_3B_DESIGN_REVIEW_001"],
        "related_files": ["polymarket/trader.py"],
        "related_decisions": [],
    },
    {
        "memory_id": "QS-003",
        "memory_type": "safety",
        "created_at": "2026-06-27T00:00:00Z",
        "updated_at": "2026-06-27T00:00:00Z",
        "source": "BATCH_3B_DESIGN_REVIEW_001",
        "agent": "29_ARCHITECTURE_GOVERNANCE_AGENT",
        "tool": None,
        "confidence": 1.0,
        "importance": 1.0,
        "tags": ["permanent", "execution_path", "never_extract"],
        "expires": None,
        "evidence_level": "B",
        "version": 1,
        "summary": "_last_quote_lineage_context is PERMANENT — written from execution path",
        "payload": {
            "forbidden_field": "_last_quote_lineage_context",
            "reason": "Written inside _phase4_build_quote_lineage — execution path write.",
            "severity": "CRITICAL",
            "file": "polymarket/trader.py",
        },
        "related_tasks": [],
        "related_files": ["polymarket/trader.py"],
        "related_decisions": [],
    },
    {
        "memory_id": "QS-004",
        "memory_type": "safety",
        "created_at": "2026-06-27T00:00:00Z",
        "updated_at": "2026-06-27T00:00:00Z",
        "source": "PROJECT_WIDE_REFACTOR_AUDIT_001",
        "agent": "29_ARCHITECTURE_GOVERNANCE_AGENT",
        "tool": None,
        "confidence": 1.0,
        "importance": 1.0,
        "tags": ["permanent", "risk_coupled", "never_extract"],
        "expires": None,
        "evidence_level": "B",
        "version": 1,
        "summary": "_risk_plan_zero_diagnostics is PERMANENT — risk-coupled, cyclical back-coupling if moved",
        "payload": {
            "forbidden_method": "_risk_plan_zero_diagnostics",
            "reason": "Reads bankroll tiers, risk modes, sizing rules directly.",
            "severity": "CRITICAL",
            "file": "polymarket/trader.py",
        },
        "related_tasks": [],
        "related_files": ["polymarket/trader.py"],
        "related_decisions": [],
    },
    {
        "memory_id": "QS-005",
        "memory_type": "safety",
        "created_at": "2026-06-27T00:00:00Z",
        "updated_at": "2026-06-27T00:00:00Z",
        "source": "PROJECT_WIDE_REFACTOR_AUDIT_001",
        "agent": "29_ARCHITECTURE_GOVERNANCE_AGENT",
        "tool": None,
        "confidence": 1.0,
        "importance": 1.0,
        "tags": ["permanent", "blast_radius", "never_extract"],
        "expires": None,
        "evidence_level": "B",
        "version": 1,
        "summary": "_diagnostic_float is PERMANENT — 99+ core math paths, maximum blast radius",
        "payload": {
            "forbidden_method": "_diagnostic_float",
            "reason": "Used in 99+ core math paths. Moving has maximum blast radius.",
            "severity": "CRITICAL",
            "file": "polymarket/trader.py",
        },
        "related_tasks": [],
        "related_files": ["polymarket/trader.py"],
        "related_decisions": [],
    },
    {
        "memory_id": "QS-006",
        "memory_type": "safety",
        "created_at": "2026-06-27T00:00:00Z",
        "updated_at": "2026-06-27T00:00:00Z",
        "source": "PROJECT_WIDE_REFACTOR_AUDIT_001",
        "agent": "29_ARCHITECTURE_GOVERNANCE_AGENT",
        "tool": None,
        "confidence": 1.0,
        "importance": 1.0,
        "tags": ["permanent", "blast_radius", "never_extract"],
        "expires": None,
        "evidence_level": "B",
        "version": 1,
        "summary": "_diagnostic_int is PERMANENT — same as QS-005",
        "payload": {
            "forbidden_method": "_diagnostic_int",
            "reason": "Same as QS-005.",
            "severity": "CRITICAL",
            "file": "polymarket/trader.py",
        },
        "related_tasks": [],
        "related_files": ["polymarket/trader.py"],
        "related_decisions": [],
    },
    {
        "memory_id": "QS-007",
        "memory_type": "safety",
        "created_at": "2026-06-27T00:00:00Z",
        "updated_at": "2026-06-27T00:00:00Z",
        "source": "AGENTS.md",
        "agent": "29_ARCHITECTURE_GOVERNANCE_AGENT",
        "tool": None,
        "confidence": 1.0,
        "importance": 1.0,
        "tags": ["live_trading", "never_automate", "requires_explicit_auth"],
        "expires": None,
        "evidence_level": "B",
        "version": 1,
        "summary": "Live trading commands require explicit user authorization — never automate",
        "payload": {
            "forbidden_action": "live_trading",
            "reason": "--mode live requires explicit operator authorization. Never run from automated loop.",
            "severity": "CRITICAL",
            "file": "polymarket/client.py",
        },
        "related_tasks": [],
        "related_files": ["polymarket/client.py", "main.py"],
        "related_decisions": [],
    },
    {
        "memory_id": "QS-008",
        "memory_type": "safety",
        "created_at": "2026-06-27T00:00:00Z",
        "updated_at": "2026-06-27T00:00:00Z",
        "source": "AGENTS.md",
        "agent": "29_ARCHITECTURE_GOVERNANCE_AGENT",
        "tool": None,
        "confidence": 1.0,
        "importance": 1.0,
        "tags": ["env_flag", "live_risk", "never_change"],
        "expires": None,
        "evidence_level": "B",
        "version": 1,
        "summary": ".env live flags — treat as live-risk if PAPER_TRADING=false or DRY_RUN=false",
        "payload": {
            "forbidden_action": "env_live_flag_change",
            "reason": "Any change to .env live trading flags requires explicit user sign-off.",
            "severity": "CRITICAL",
            "file": ".env",
        },
        "related_tasks": [],
        "related_files": [".env", "config/settings.py"],
        "related_decisions": [],
    },
    {
        "memory_id": "QS-009",
        "memory_type": "safety",
        "created_at": "2026-06-27T00:00:00Z",
        "updated_at": "2026-06-27T00:00:00Z",
        "source": "PROJECT_RULES.md",
        "agent": "29_ARCHITECTURE_GOVERNANCE_AGENT",
        "tool": None,
        "confidence": 1.0,
        "importance": 1.0,
        "tags": ["runtime_data", "never_delete_auto"],
        "expires": None,
        "evidence_level": "B",
        "version": 1,
        "summary": "Runtime data deletion requires explicit authorization — never from automated loops",
        "payload": {
            "forbidden_action": "runtime_data_deletion",
            "reason": "Deleting runtime/ data can destroy trading history, session state, JSONL evidence. Requires explicit user authorization (Class 8 gate).",
            "severity": "CRITICAL",
            "file": "runtime/",
        },
        "related_tasks": [],
        "related_files": ["runtime/"],
        "related_decisions": [],
    },
    {
        "memory_id": "QS-010",
        "memory_type": "safety",
        "created_at": "2026-06-27T00:00:00Z",
        "updated_at": "2026-06-27T00:00:00Z",
        "source": "AGENTS.md",
        "agent": "29_ARCHITECTURE_GOVERNANCE_AGENT",
        "tool": None,
        "confidence": 1.0,
        "importance": 1.0,
        "tags": ["execution", "risk", "sizing", "reconciliation", "never_automate"],
        "expires": None,
        "evidence_level": "B",
        "version": 1,
        "summary": "Execution/risk/sizing/reconciliation/wallet changes require Class 7-8 gate and explicit authorization",
        "payload": {
            "forbidden_domains": ["execution", "risk", "sizing", "reconciliation", "wallet", "bankroll"],
            "reason": "arb_auto_execute must remain false. No automated changes to execution logic, risk gates, position sizing, or wallet operations.",
            "severity": "CRITICAL",
            "affected_files": ["polymarket/order_intent.py", "utils/risk_manager.py", "polymarket/position_sizing.py"],
        },
        "related_tasks": [],
        "related_files": ["polymarket/order_intent.py", "utils/risk_manager.py"],
        "related_decisions": [],
    },
]


# ---------------------------------------------------------------------------
# Migration logic
# ---------------------------------------------------------------------------

def _load_v1_entries() -> list[dict]:
    if not V1_SOURCE.exists():
        print(f"ERROR: v1 source not found: {V1_SOURCE}", file=sys.stderr)
        sys.exit(1)
    data = json.loads(V1_SOURCE.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        print("ERROR: v1 source is not a JSON array", file=sys.stderr)
        sys.exit(1)
    return data


def _adapt_v1_to_v2(entry: dict) -> dict:
    """Convert v1 loop memory entry to v2 memory record schema."""
    loop_id = entry.get("loop_id", "unknown")
    return {
        "memory_id": entry.get("memory_id", f"LOOP-{loop_id}"),
        "memory_type": "loop",
        "created_at": entry.get("date", "2026-06-27") + "T00:00:00Z",
        "updated_at": entry.get("date", "2026-06-27") + "T00:00:00Z",
        "source": loop_id,
        "agent": "auto_migrated_from_v1",
        "tool": None,
        "confidence": 0.9,
        "importance": 0.7,
        "tags": ["migrated_from_v1"],
        "expires": None if entry.get("result") == "PASS" else "2027-06-27",
        "evidence_level": entry.get("evidence_grade", "D"),
        "version": 1,
        "summary": f"{loop_id}: {entry.get('result', 'UNKNOWN')} (repairs={entry.get('repairs', 0)})",
        "payload": entry,
        "related_tasks": [loop_id],
        "related_files": entry.get("scope", []),
        "related_decisions": [],
        "loop_id": loop_id,
        "task_class": entry.get("task_class", 3),
        "result": entry.get("result", "UNKNOWN"),
        "repairs": entry.get("repairs", 0),
        "commits": entry.get("commits", []),
        "next_recommendation": entry.get("next_recommendation", ""),
    }


def migrate(dry_run: bool = True) -> dict:
    """Run the migration. Returns a summary dict."""
    entries = _load_v1_entries()
    mode_prefix = "[DRY-RUN] " if dry_run else ""
    print(f"{mode_prefix}Migrating {len(entries)} loop memory entries from v1 to v2 JSONL")
    print(f"  Source: {V1_SOURCE}")
    print(f"  Target: {LOOP_TARGET}")

    migrated = 0
    index_updates = 0

    if not dry_run:
        LOOP_TARGET.parent.mkdir(parents=True, exist_ok=True)
        # Clear target file if it exists (idempotent migration)
        LOOP_TARGET.write_text("", encoding="utf-8")

    for entry in entries:
        v2 = _adapt_v1_to_v2(entry)
        if dry_run:
            print(f"  [DRY] Would write: {v2['memory_id']} ({v2['summary'][:60]})")
        else:
            _, offset = append_memory("loop", v2, LOOP_TARGET)
            update_index(v2, LOOP_TARGET, offset)
            index_updates += 1
        migrated += 1

    # Seed safety memory
    safety_seeded = 0
    if not dry_run:
        SAFETY_TARGET.parent.mkdir(parents=True, exist_ok=True)
        SAFETY_TARGET.write_text("", encoding="utf-8")

    for qs in SAFETY_ENTRIES:
        if dry_run:
            print(f"  [DRY] Would seed safety: {qs['memory_id']} — {qs['summary'][:60]}")
        else:
            _, offset = append_memory("safety", qs, SAFETY_TARGET)
            update_index(qs, SAFETY_TARGET, offset)
        safety_seeded += 1

    # Finalize index
    if not dry_run:
        idx = _load_index()
        def _rel(p: Path) -> str:
            try:
                return str(p.relative_to(ROOT))
            except ValueError:
                return str(p)
        idx["latest_loop_file"] = _rel(LOOP_TARGET)
        idx["latest_loop_count"] = migrated
        idx["safety_memory_file"] = _rel(SAFETY_TARGET)
        idx["open_quant_questions"] = ["LOW_PRICE_TRUTH_RESOLUTION_001"]
        _save_index(idx)

    result = {
        "mode": "DRY_RUN" if dry_run else "EXECUTE",
        "source": str(V1_SOURCE),
        "target": str(LOOP_TARGET),
        "entries_migrated": migrated,
        "safety_entries_seeded": safety_seeded,
        "index_updated": not dry_run,
        "v1_file_deleted": False,
        "non_destructive": True,
    }
    print(f"\n{'DRY-RUN ' if dry_run else ''}Summary: {migrated} loop entries, {safety_seeded} safety entries")
    if not dry_run:
        print(f"  Index: {INDEX_PATH}")
        print(f"  Loop JSONL: {LOOP_TARGET} ({LOOP_TARGET.stat().st_size} bytes)")
        print(f"  Safety JSONL: {SAFETY_TARGET} ({SAFETY_TARGET.stat().st_size} bytes)")
        print("  v1 source: NOT modified (non-destructive)")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="FLAOS Memory OS v2 Migration Tool")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Simulate migration without writing files")
    group.add_argument("--execute", action="store_true", help="Execute migration (non-destructive)")
    args = parser.parse_args()
    result = migrate(dry_run=args.dry_run)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
