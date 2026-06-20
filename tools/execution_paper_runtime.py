"""Isolated Phase A skeleton for Execution Paper Runtime evidence.

This module is an offline tool only. It does not import trading runtime modules,
does not submit orders, and writes only to the configured execution-paper output
root.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "execution_paper.v1"
CHECKPOINT_SCHEMA_VERSION = "execution_paper.checkpoint.v1"
DEFAULT_SOURCE_ROOT = Path("runtime/quant_data")
DEFAULT_OUTPUT_ROOT = Path("runtime/quant_data/execution_paper")

EVENT_TYPES = {
    "execution_paper_open",
    "execution_paper_close",
    "execution_paper_reject",
    "execution_paper_equity_snapshot",
    "execution_paper_position_snapshot",
    "execution_paper_runtime_started",
    "execution_paper_runtime_stopped",
}

COMMON_REQUIRED = (
    "schema_version",
    "event_type",
    "timestamp_utc",
    "execution_run_id",
)

SOURCE_REQUIRED = (
    "source_runtime_mode",
    "source_run_id",
    "source_event_type",
    "source_file",
    "source_line",
    "source_event_sha256",
)

EVENT_REQUIRED: dict[str, tuple[str, ...]] = {
    "execution_paper_open": SOURCE_REQUIRED
    + (
        "source_replay_key",
        "condition_id",
        "asset",
        "side",
        "execution_track",
        "execution_bankroll_start",
        "execution_entry_price",
        "execution_shares",
        "execution_notional",
        "execution_liquidity_pass",
        "execution_position_id",
    ),
    "execution_paper_close": SOURCE_REQUIRED
    + (
        "execution_position_id",
        "source_replay_key",
        "condition_id",
        "asset",
        "side",
        "execution_track",
        "execution_entry_price",
        "execution_exit_price",
        "execution_shares",
        "execution_pnl",
        "execution_exit_reason",
    ),
    "execution_paper_reject": SOURCE_REQUIRED
    + (
        "execution_track",
        "reject_stage",
        "reject_reason",
        "required_shares",
        "execution_equity",
        "execution_risk_mode",
        "inventory_state",
    ),
    "execution_paper_equity_snapshot": (
        "execution_track",
        "execution_bankroll_start",
        "execution_equity",
        "execution_realized_pnl",
        "execution_unrealized_pnl",
        "execution_net_pnl",
        "execution_gross_profit",
        "execution_gross_loss",
        "execution_trade_count",
        "execution_win_count",
        "execution_loss_count",
        "execution_dd",
        "execution_max_dd",
        "execution_open_exposure",
        "execution_risk_mode",
    ),
    "execution_paper_position_snapshot": SOURCE_REQUIRED
    + (
        "execution_position_id",
        "source_replay_key",
        "condition_id",
        "asset",
        "side",
        "execution_track",
        "position_state",
        "shares_open",
        "avg_entry_price",
        "realized_pnl",
    ),
    "execution_paper_runtime_started": (
        "source_root",
        "output_root",
        "dry_run",
        "max_events",
    ),
    "execution_paper_runtime_stopped": (
        "status",
        "processed_event_count",
        "emitted_event_count",
    ),
}


class SchemaValidationError(ValueError):
    """Raised when an execution-paper event fails schema validation."""


class PathIsolationError(ValueError):
    """Raised when an output path escapes the execution-paper root."""


class CheckpointError(RuntimeError):
    """Raised when checkpoint/source integrity fails."""


class DuplicateConflictError(RuntimeError):
    """Raised when a dedupe key maps to conflicting payloads."""


class ReconciliationError(RuntimeError):
    """Raised when journal replay cannot reconcile inventory state."""


@dataclass(frozen=True)
class SourceEvent:
    source_file: Path
    source_line: int
    source_event_sha256: str
    parsed_json: dict[str, Any]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_execution_run_id(now: str | None = None) -> str:
    stamp = now or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"execution_{stamp}_{os.getpid()}_{uuid.uuid4().hex[:8]}"


def _event_date(event: dict[str, Any]) -> str:
    timestamp = str(event.get("timestamp_utc") or utc_now())
    return timestamp[:10]


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_line(line: str) -> str:
    return _sha256_text(line)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, default=str)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _is_execution_paper_root(path: Path) -> bool:
    parts = path.resolve().parts
    suffix = DEFAULT_OUTPUT_ROOT.parts
    return len(parts) >= len(suffix) and tuple(parts[-len(suffix) :]) == tuple(suffix)


def _ensure_output_root(output_root: Path) -> Path:
    output_root = Path(output_root)
    if not _is_execution_paper_root(output_root):
        raise PathIsolationError(f"output root must end with {DEFAULT_OUTPUT_ROOT.as_posix()}")
    return output_root


def _ensure_inside(child: Path, parent: Path) -> None:
    child_resolved = child.resolve()
    parent_resolved = parent.resolve()
    if child_resolved != parent_resolved and parent_resolved not in child_resolved.parents:
        raise PathIsolationError(f"path escapes execution-paper root: {child}")


def validate_event(event: dict[str, Any]) -> bool:
    event_type = str(event.get("event_type") or "")
    if event_type not in EVENT_TYPES:
        raise SchemaValidationError(f"unknown event_type: {event_type}")
    missing = [field for field in COMMON_REQUIRED + EVENT_REQUIRED[event_type] if field not in event]
    if missing:
        raise SchemaValidationError(f"missing required fields: {', '.join(missing)}")
    if event.get("schema_version") != SCHEMA_VERSION:
        raise SchemaValidationError(f"schema_version must be {SCHEMA_VERSION}")
    return True


def append_jsonl_event(output_root: str | Path, journal_type: str, event: dict[str, Any]) -> Path:
    validate_event(event)
    root = _ensure_output_root(Path(output_root))
    safe_journal = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in str(journal_type))
    path = root / "journals" / safe_journal / f"{_event_date(event)}.jsonl"
    _ensure_inside(path, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(_canonical_json(event) + "\n")
        handle.flush()
    return path


def write_checkpoint(output_root: str | Path, execution_run_id: str, checkpoint: dict[str, Any]) -> Path:
    root = _ensure_output_root(Path(output_root))
    payload = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "execution_run_id": execution_run_id,
        "checkpointed_at": utc_now(),
        **checkpoint,
    }
    date = str(payload.get("checkpointed_at", utc_now()))[:10]
    path = root / "checkpoints" / date / f"{execution_run_id}.json"
    _ensure_inside(path, root)
    _atomic_write_json(path, payload)
    return path


def read_checkpoint(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("schema_version") != CHECKPOINT_SCHEMA_VERSION:
        raise CheckpointError("invalid checkpoint schema_version")
    return payload


def stream_source_journal(path: str | Path) -> Iterable[SourceEvent]:
    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        for source_line, line in enumerate(handle, start=1):
            parsed = json.loads(line)
            if not isinstance(parsed, dict):
                raise ValueError(f"source event must be an object: {source}:{source_line}")
            yield SourceEvent(
                source_file=source.resolve(),
                source_line=source_line,
                source_event_sha256=_sha256_line(line),
                parsed_json=parsed,
            )


def validate_checkpoint_source_hash(checkpoint: dict[str, Any]) -> bool:
    source_file = Path(str(checkpoint.get("last_processed_source_file") or ""))
    source_line = int(checkpoint.get("last_processed_source_line") or 0)
    expected_hash = str(checkpoint.get("last_processed_source_sha256") or "")
    if not source_file.exists() or source_line <= 0 or not expected_hash:
        raise CheckpointError("checkpoint source reference incomplete")
    for event in stream_source_journal(source_file):
        if event.source_line == source_line:
            if event.source_event_sha256 != expected_hash:
                raise CheckpointError("checkpoint source hash mismatch")
            return True
    raise CheckpointError("checkpoint source line missing")


def _dedupe_key(event: dict[str, Any]) -> tuple[str, str, str, str]:
    replay_key = str(event.get("source_replay_key") or event.get("source_event_sha256") or "")
    return (
        str(event.get("execution_run_id") or ""),
        replay_key,
        str(event.get("event_type") or ""),
        str(event.get("execution_track") or ""),
    )


class DedupeIndex:
    def __init__(self) -> None:
        self._seen: dict[tuple[str, str, str, str], str] = {}

    def register(self, event: dict[str, Any]) -> str:
        key = _dedupe_key(event)
        digest = _sha256_text(_canonical_json(event))
        previous = self._seen.get(key)
        if previous is None:
            self._seen[key] = digest
            return "new"
        if previous == digest:
            return "duplicate"
        raise DuplicateConflictError(f"conflicting duplicate for key={key}")


def reconcile_events(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    open_positions: dict[str, dict[str, Any]] = {}
    closed_positions: set[str] = set()
    rejected = 0
    opens = 0
    closes = 0
    for event in events:
        event_type = event.get("event_type")
        position_id = str(event.get("execution_position_id") or "")
        if event_type == "execution_paper_reject":
            rejected += 1
            continue
        if event_type == "execution_paper_open":
            if not position_id:
                raise ReconciliationError("missing_position_id")
            if position_id in open_positions or position_id in closed_positions:
                raise ReconciliationError("duplicate_open")
            open_positions[position_id] = event
            opens += 1
        elif event_type == "execution_paper_close":
            if position_id in closed_positions:
                raise ReconciliationError("duplicate_close")
            if position_id not in open_positions:
                raise ReconciliationError("orphan_close")
            closed_positions.add(position_id)
            del open_positions[position_id]
            closes += 1
    if open_positions:
        raise ReconciliationError("open_without_close")
    return {
        "status": "PASS",
        "open_count": opens,
        "close_count": closes,
        "reject_count": rejected,
        "closed_position_count": len(closed_positions),
    }


def _runtime_event(event_type: str, execution_run_id: str, **fields: Any) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "event_type": event_type,
        "timestamp_utc": utc_now(),
        "execution_run_id": execution_run_id,
        **fields,
    }


def run_dry_run(*, source_root: Path, output_root: Path, max_events: int) -> dict[str, Any]:
    root = _ensure_output_root(output_root)
    execution_run_id = new_execution_run_id()
    emitted = 0
    started = _runtime_event(
        "execution_paper_runtime_started",
        execution_run_id,
        source_root=str(source_root),
        output_root=str(root),
        dry_run=True,
        max_events=max_events,
    )
    append_jsonl_event(root, "runtime", started)
    emitted += 1
    stopped = _runtime_event(
        "execution_paper_runtime_stopped",
        execution_run_id,
        status="DRY_RUN_COMPLETE",
        processed_event_count=0,
        emitted_event_count=emitted + 1,
    )
    append_jsonl_event(root, "runtime", stopped)
    emitted += 1
    checkpoint_path = write_checkpoint(
        root,
        execution_run_id,
        {
            "last_processed_trade": None,
            "last_processed_timestamp": None,
            "last_processed_source_file": None,
            "last_processed_source_line": None,
            "last_processed_source_sha256": None,
            "processed_event_count": 0,
            "emitted_event_count": emitted,
            "status": "DRY_RUN_COMPLETE",
        },
    )
    report = {
        "schema_version": "execution_paper.validation.v1",
        "generated_at": utc_now(),
        "execution_run_id": execution_run_id,
        "status": "PASS",
        "dry_run": True,
        "processed_event_count": 0,
        "emitted_event_count": emitted,
        "checkpoint_path": str(checkpoint_path),
        "guardrails": {
            "signal_runtime_modified": False,
            "runtime_behavior_changed": False,
            "strategy_risk_execution_changed": False,
        },
    }
    report_path = root / "reports" / utc_now()[:10] / f"{execution_run_id}_validation.json"
    _ensure_inside(report_path, root)
    _atomic_write_json(report_path, report)
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-events", type=int, default=10)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.dry_run:
        raise SystemExit("--dry-run is required in Phase A skeleton")
    run_dry_run(
        source_root=args.source_root,
        output_root=args.output_root,
        max_events=args.max_events,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

