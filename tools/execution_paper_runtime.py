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
        "execution_equity_before",
        "execution_equity_after",
        "cumulative_execution_pnl",
        "execution_drawdown",
        "execution_max_drawdown",
        "execution_max_drawdown_pct",
        "execution_result_class",
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
        "cumulative_execution_pnl",
        "execution_dd",
        "execution_max_dd",
        "execution_max_dd_pct",
        "risk_of_ruin",
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


def reconcile_events(events: Iterable[dict[str, Any]], allow_partial_open: bool = True) -> dict[str, Any]:
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
        if not allow_partial_open:
            raise ReconciliationError("open_without_close")
        status = "PARTIAL_OPEN_ALLOWED"
    else:
        status = "PASS"
    return {
        "status": status,
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


def run_dry_run(*, source_root: Path, output_root: Path, max_events: int, compat_mode: str = "strict") -> dict[str, Any]:
    return run_replay(
        source_root=source_root,
        output_root=output_root,
        max_events=max_events,
        track="5_share",
        starting_bankroll=250.0,
        dry_run=True,
        compat_mode=compat_mode,
    )


def run_replay(
    *,
    source_root: Path,
    output_root: Path,
    max_events: int,
    track: str = "5_share",
    starting_bankroll: float = 250.0,
    dry_run: bool = False,
    compat_mode: str = "strict",
) -> dict[str, Any]:
    root = _ensure_output_root(output_root)

    # Discover checkpoints to resume
    checkpoint_dir = root / "checkpoints"
    checkpoints = []
    if checkpoint_dir.exists():
        for p in checkpoint_dir.rglob("*.json"):
            try:
                checkpoints.append(read_checkpoint(p))
            except Exception:
                pass

    latest_checkpoint = None
    if checkpoints:
        checkpoints.sort(key=lambda c: c.get("checkpointed_at", ""))
        latest_checkpoint = checkpoints[-1]

    if latest_checkpoint:
        validate_checkpoint_source_hash(latest_checkpoint)
        execution_run_id = latest_checkpoint["execution_run_id"]
        processed_event_count = latest_checkpoint.get("processed_event_count", 0)
        emitted_event_count = latest_checkpoint.get("emitted_event_count", 0)
        rejected_event_count = latest_checkpoint.get("rejected_event_count", 0)
        skipped_duplicate_count = latest_checkpoint.get("skipped_duplicate_count", 0)
        malformed_source_count = latest_checkpoint.get("malformed_source_count", 0)
        open_positions = latest_checkpoint.get("open_positions", {})
        closed_positions = latest_checkpoint.get("closed_positions", [])

        dedupe_index = DedupeIndex()
        seen_keys_list = latest_checkpoint.get("seen_keys", [])
        for k_list, digest in seen_keys_list:
            dedupe_index._seen[tuple(k_list)] = digest

        last_processed_file = latest_checkpoint.get("last_processed_source_file")
        last_processed_line = latest_checkpoint.get("last_processed_source_line", 0)
        last_line_hash = latest_checkpoint.get("last_processed_source_sha256", "")

        execution_equity = latest_checkpoint.get("execution_equity", starting_bankroll)
        cumulative_pnl = latest_checkpoint.get("cumulative_pnl", 0.0)
        peak_equity = latest_checkpoint.get("peak_equity", starting_bankroll)
        current_dd = latest_checkpoint.get("current_dd", 0.0)
        max_dd = latest_checkpoint.get("max_dd", 0.0)
        max_dd_pct = latest_checkpoint.get("max_dd_pct", 0.0)
        risk_of_ruin = latest_checkpoint.get("risk_of_ruin", False)
        win_count = latest_checkpoint.get("win_count", 0)
        loss_count = latest_checkpoint.get("loss_count", 0)
        flat_count = latest_checkpoint.get("flat_count", 0)
        gross_profit = latest_checkpoint.get("gross_profit", 0.0)
        gross_loss = latest_checkpoint.get("gross_loss", 0.0)
    else:
        execution_run_id = new_execution_run_id()
        processed_event_count = 0
        emitted_event_count = 0
        rejected_event_count = 0
        skipped_duplicate_count = 0
        malformed_source_count = 0
        open_positions = {}
        closed_positions = []
        dedupe_index = DedupeIndex()
        last_processed_file = None
        last_processed_line = 0
        last_line_hash = ""

        execution_equity = starting_bankroll
        cumulative_pnl = 0.0
        peak_equity = starting_bankroll
        current_dd = 0.0
        max_dd = 0.0
        max_dd_pct = 0.0
        risk_of_ruin = False
        win_count = 0
        loss_count = 0
        flat_count = 0
        gross_profit = 0.0
        gross_loss = 0.0

        started = _runtime_event(
            "execution_paper_runtime_started",
            execution_run_id,
            source_root=str(source_root),
            output_root=str(root),
            dry_run=dry_run,
            max_events=max_events,
        )
        append_jsonl_event(root, "runtime", started)
        emitted_event_count += 1

    # Initialize historical mode index queues
    historical_order_queue = {}
    historical_fifo_queue = {}

    if compat_mode == "historical" and open_positions:
        # Reconstruct queues from loaded open_positions in chronological order
        sorted_opens = sorted(
            open_positions.items(),
            key=lambda x: x[1].get("timestamp_utc") or x[1].get("payload", {}).get("timestamp_utc") or ""
        )
        for uid, op in sorted_opens:
            op_payload = op.get("payload") or {}
            op_run_id = op.get("source_run_id") or op_payload.get("run_id") or ""

            op_pid_val = op_payload.get("position_id")
            op_epid_val = op_payload.get("execution_position_id")
            op_receipt_oid = op_payload.get("receipt", {}).get("order_id") if isinstance(op_payload.get("receipt"), dict) else None
            op_oid_val = op_payload.get("order_id")
            op_resolved_pid = op_pid_val or op_epid_val or op_receipt_oid or op_oid_val

            resolved_order_id = None
            if isinstance(op_payload.get("receipt"), dict):
                resolved_order_id = op_payload["receipt"].get("order_id")
            if not resolved_order_id:
                resolved_order_id = op_payload.get("order_id")
            if not resolved_order_id:
                resolved_order_id = op_resolved_pid

            op_condition_id = op.get("condition_id") or op_payload.get("condition_id")
            op_asset = op.get("asset") or op_payload.get("asset") or op_payload.get("ticker")
            op_outcome = op.get("side") or op_payload.get("outcome")

            if resolved_order_id:
                key = (op_run_id, str(resolved_order_id))
                if key not in historical_order_queue:
                    historical_order_queue[key] = []
                historical_order_queue[key].append(uid)
            if op_condition_id and op_asset and op_outcome:
                fifo_key = (op_run_id, op_condition_id, op_asset, op_outcome)
                if fifo_key not in historical_fifo_queue:
                    historical_fifo_queue[fifo_key] = []
                historical_fifo_queue[fifo_key].append(uid)

    journal_dir = source_root / "trade_journal"
    source_files = []
    if journal_dir.exists() and journal_dir.is_dir():
        source_files = sorted(list(journal_dir.glob("*.jsonl")), key=lambda p: p.name)

    last_processed_file_abs = Path(last_processed_file).resolve() if last_processed_file else None
    checkpoint_path = None

    def save_checkpoint(src_file: Path | None, line_no: int, line_h: str, last_trade_id: str | None = None):
        nonlocal checkpoint_path
        checkpoint_path = write_checkpoint(
            root,
            execution_run_id,
            {
                "last_processed_trade": last_trade_id,
                "last_processed_timestamp": utc_now(),
                "last_processed_source_file": str(src_file) if src_file else None,
                "last_processed_source_line": line_no,
                "last_processed_source_sha256": line_h,
                "processed_event_count": processed_event_count,
                "emitted_event_count": emitted_event_count,
                "rejected_event_count": rejected_event_count,
                "skipped_duplicate_count": skipped_duplicate_count,
                "malformed_source_count": malformed_source_count,
                "execution_track": track,
                "execution_bankroll_start": starting_bankroll,
                "open_positions": open_positions,
                "closed_positions": closed_positions,
                "seen_keys": [[list(k), v] for k, v in dedupe_index._seen.items()],
                "execution_equity": execution_equity,
                "cumulative_pnl": cumulative_pnl,
                "peak_equity": peak_equity,
                "current_dd": current_dd,
                "max_dd": max_dd,
                "max_dd_pct": max_dd_pct,
                "risk_of_ruin": risk_of_ruin,
                "win_count": win_count,
                "loss_count": loss_count,
                "flat_count": flat_count,
                "gross_profit": gross_profit,
                "gross_loss": gross_loss,
            }
        )

    for source_file in source_files:
        source_file_abs = source_file.resolve()

        if last_processed_file_abs:
            if source_file_abs.name < last_processed_file_abs.name:
                continue

        try:
            with source_file.open("r", encoding="utf-8") as handle:
                for line_idx, line in enumerate(handle, start=1):
                    if last_processed_file_abs and source_file_abs.name == last_processed_file_abs.name:
                        if line_idx <= last_processed_line:
                            continue

                    if processed_event_count >= max_events:
                        break

                    line_hash = _sha256_line(line)
                    last_processed_file = source_file
                    last_processed_line = line_idx
                    last_line_hash = line_hash

                    try:
                        parsed = json.loads(line)
                        if not isinstance(parsed, dict):
                            raise ValueError("Not a dictionary")
                    except (json.JSONDecodeError, ValueError):
                        malformed_source_count += 1
                        processed_event_count += 1
                        save_checkpoint(source_file, line_idx, line_hash)
                        continue

                    processed_event_count += 1

                    event_type = parsed.get("event_type")
                    is_open = event_type in ("trade_open", "open", "paper_trade_open")
                    is_close = event_type in ("trade_close", "close", "paper_trade_close")

                    if not (is_open or is_close):
                        save_checkpoint(source_file, line_idx, line_hash)
                        continue

                    payload = parsed.get("payload")
                    if not isinstance(payload, dict):
                        rejected_event_count += 1
                        reject_event = {
                            "schema_version": SCHEMA_VERSION,
                            "event_type": "execution_paper_reject",
                            "timestamp_utc": utc_now(),
                            "execution_run_id": execution_run_id,
                            "source_runtime_mode": parsed.get("mode") or parsed.get("source_runtime_mode") or "SIGNAL_MODE",
                            "source_run_id": parsed.get("run_id") or parsed.get("source_run_id") or "",
                            "source_event_type": event_type,
                            "source_file": str(source_file),
                            "source_line": line_idx,
                            "source_event_sha256": line_hash,
                            "execution_track": track,
                            "reject_stage": "validation",
                            "reject_reason": "payload_is_not_dict",
                            "required_shares": 5.0,
                            "execution_equity": starting_bankroll,
                            "execution_risk_mode": "NORMAL",
                            "inventory_state": json.dumps(open_positions),
                        }
                        append_jsonl_event(root, "trade", reject_event)
                        emitted_event_count += 1
                        save_checkpoint(source_file, line_idx, line_hash)
                        continue

                    condition_id = payload.get("condition_id")
                    asset = payload.get("asset") or payload.get("ticker")

                    # Position ID Resolver
                    if compat_mode == "historical":
                        pid_val = payload.get("position_id")
                        epid_val = payload.get("execution_position_id")
                        receipt_oid = payload.get("receipt", {}).get("order_id") if isinstance(payload.get("receipt"), dict) else None
                        oid_val = payload.get("order_id")

                        resolved_pid = pid_val or epid_val or receipt_oid or oid_val

                        resolved_order_id = None
                        if isinstance(payload.get("receipt"), dict):
                            resolved_order_id = payload["receipt"].get("order_id")
                        if not resolved_order_id:
                            resolved_order_id = payload.get("order_id")
                        if not resolved_order_id:
                            resolved_order_id = resolved_pid
                    else:
                        resolved_pid = payload.get("position_id") or payload.get("execution_position_id")
                        resolved_order_id = None

                    execution_position_id = None
                    if resolved_pid is not None:
                        pos_id_str = str(resolved_pid)
                        execution_position_id = pos_id_str if pos_id_str.startswith("ep_") else f"ep_{pos_id_str}"

                    matched_key = None

                    def trigger_reject(reason: str, stage: str = "validation"):
                        nonlocal emitted_event_count, rejected_event_count
                        rejected_event_count += 1
                        req_shares = 5.0
                        if track != "5_share":
                            try:
                                req_shares = float(payload.get("shares") or payload.get("size") or 5.0)
                            except (TypeError, ValueError):
                                pass
                        reject_event = {
                            "schema_version": SCHEMA_VERSION,
                            "event_type": "execution_paper_reject",
                            "timestamp_utc": utc_now(),
                            "execution_run_id": execution_run_id,
                            "source_runtime_mode": parsed.get("mode") or parsed.get("source_runtime_mode") or "SIGNAL_MODE",
                            "source_run_id": parsed.get("run_id") or parsed.get("source_run_id") or "",
                            "source_event_type": event_type,
                            "source_file": str(source_file),
                            "source_line": line_idx,
                            "source_event_sha256": line_hash,
                            "execution_track": track,
                            "reject_stage": stage,
                            "reject_reason": reason,
                            "required_shares": req_shares,
                            "execution_equity": execution_equity,
                            "execution_risk_mode": "NORMAL",
                            "inventory_state": json.dumps(open_positions),
                        }
                        append_jsonl_event(root, "trade", reject_event)
                        emitted_event_count += 1
                        save_checkpoint(source_file, line_idx, line_hash, matched_key)

                    if is_open:
                        entry_price = payload.get("entry_price")
                        if entry_price is None:
                            entry_price = payload.get("price")
                        if entry_price is None:
                            entry_price = payload.get("receipt", {}).get("price") if isinstance(payload.get("receipt"), dict) else None

                        if compat_mode == "historical":
                            pid_val = payload.get("position_id")
                            epid_val = payload.get("execution_position_id")
                            receipt_oid = payload.get("receipt", {}).get("order_id") if isinstance(payload.get("receipt"), dict) else None
                            oid_val = payload.get("order_id")

                            if not (pid_val or epid_val) and not (receipt_oid or oid_val):
                                trigger_reject("missing_order_id_for_legacy_open")
                                continue
                            if not resolved_pid:
                                trigger_reject("position_id_unresolvable")
                                continue
                        else:
                            if not resolved_pid:
                                trigger_reject("missing_position_id")
                                continue

                        if not condition_id:
                            trigger_reject("missing_condition_id")
                            continue

                        # Side Resolver
                        if compat_mode == "historical":
                            outcome_val = payload.get("outcome")
                            side_val = payload.get("side")
                            if outcome_val in ("YES", "NO"):
                                resolved_side = outcome_val
                            elif side_val in ("YES", "NO"):
                                resolved_side = side_val
                            else:
                                trigger_reject("side_unresolvable")
                                continue
                        else:
                            resolved_side = payload.get("side") or payload.get("outcome")
                            if not resolved_side or resolved_side not in ("YES", "NO"):
                                trigger_reject("side_unresolvable")
                                continue

                        if entry_price is None:
                            trigger_reject("missing_entry_price")
                            continue
                        try:
                            entry_price = float(entry_price)
                        except (TypeError, ValueError):
                            trigger_reject("invalid_entry_price")
                            continue

                        historical_position_uid = None
                        if compat_mode == "historical":
                            run_id_val = parsed.get("run_id") or parsed.get("source_run_id") or ""
                            resolved_order_id_str = str(resolved_order_id or "")
                            condition_id_str = str(condition_id or "")
                            asset_str = str(asset or "")
                            outcome_str = str(resolved_side or "")
                            open_timestamp_utc = parsed.get("timestamp_utc") or parsed.get("timestamp") or ""

                            uid_input = f"{run_id_val}{resolved_order_id_str}{condition_id_str}{asset_str}{outcome_str}{open_timestamp_utc}"
                            historical_position_uid = hashlib.sha256(uid_input.encode("utf-8")).hexdigest()

                        if compat_mode == "historical":
                            if historical_position_uid in open_positions or historical_position_uid in closed_positions:
                                raise ReconciliationError("duplicate_open")
                            if resolved_order_id:
                                run_id_val = parsed.get("run_id") or parsed.get("source_run_id") or ""
                                key = (run_id_val, str(resolved_order_id))
                                if key in historical_order_queue and len(historical_order_queue[key]) > 0:
                                    raise ReconciliationError("duplicate_open")
                            matched_key = historical_position_uid
                        else:
                            if execution_position_id in open_positions or execution_position_id in closed_positions:
                                raise ReconciliationError("duplicate_open")
                            matched_key = execution_position_id

                        source_replay_key = _sha256_text(f"{Path(source_file).as_posix()}|{line_idx}|{line_hash}")
                        execution_shares = 5.0 if track == "5_share" else float(payload.get("shares") or payload.get("size") or 5.0)
                        execution_notional = entry_price * execution_shares

                        emitted_event = {
                            "schema_version": SCHEMA_VERSION,
                            "event_type": "execution_paper_open",
                            "timestamp_utc": utc_now(),
                            "execution_run_id": execution_run_id,
                            "source_runtime_mode": parsed.get("mode") or parsed.get("source_runtime_mode") or "SIGNAL_MODE",
                            "source_run_id": parsed.get("run_id") or parsed.get("source_run_id") or "",
                            "source_event_type": event_type,
                            "source_file": str(source_file),
                            "source_line": line_idx,
                            "source_event_sha256": line_hash,
                            "source_replay_key": source_replay_key,
                            "condition_id": condition_id,
                            "asset": asset,
                            "side": resolved_side,
                            "execution_track": track,
                            "execution_bankroll_start": starting_bankroll,
                            "execution_entry_price": entry_price,
                            "execution_shares": execution_shares,
                            "execution_notional": execution_notional,
                            "execution_liquidity_pass": True,
                            "execution_position_id": execution_position_id if compat_mode == "historical" else matched_key,
                        }
                        if compat_mode == "historical":
                            emitted_event["historical_position_uid"] = historical_position_uid
                            emitted_event["identity_source"] = "historical_run_order_uid"
                        else:
                            emitted_event["identity_source"] = "canonical_position_id"

                    elif is_close:
                        exit_price = payload.get("exit_price")
                        if exit_price is None:
                            exit_price = payload.get("price")
                        if exit_price is None:
                            exit_price = payload.get("receipt", {}).get("price") if isinstance(payload.get("receipt"), dict) else None

                        exit_reason = payload.get("exit_reason")
                        if exit_reason is None:
                            exit_reason = payload.get("reason")

                        # Resolve side (needed for FIFO matching)
                        if compat_mode == "historical":
                            outcome_val = payload.get("outcome")
                            side_val = payload.get("side")
                            if outcome_val in ("YES", "NO"):
                                resolved_side = outcome_val
                            elif side_val in ("YES", "NO"):
                                resolved_side = side_val
                            else:
                                resolved_side = None
                        else:
                            resolved_side = payload.get("side") or payload.get("outcome")

                        if compat_mode == "historical":
                            if not resolved_pid:
                                # FIFO matching needs resolved_side, condition_id, asset
                                if not (condition_id and asset and resolved_side):
                                    trigger_reject("position_id_unresolvable")
                                    continue
                        else:
                            if not resolved_pid:
                                trigger_reject("missing_position_id")
                                continue
                            if execution_position_id in closed_positions:
                                raise ReconciliationError("duplicate_close")

                        # Open/Close Linking
                        open_pos = None
                        matched_key = None

                        if compat_mode == "historical":
                            close_receipt_oid = payload.get("receipt", {}).get("order_id") if isinstance(payload.get("receipt"), dict) else None
                            close_oid_val = payload.get("order_id")
                            close_resolved_order_id = close_receipt_oid or close_oid_val or resolved_pid

                            close_run_id = parsed.get("run_id") or parsed.get("source_run_id") or ""

                            matched_uid = None

                            # 1. Try order ID matching
                            if close_resolved_order_id:
                                key = (close_run_id, str(close_resolved_order_id))
                                candidates = historical_order_queue.get(key, [])
                                active_candidates = [uid for uid in candidates if uid in open_positions]
                                closed_candidates = [uid for uid in candidates if uid in closed_positions]

                                if len(active_candidates) == 1:
                                    matched_uid = active_candidates[0]
                                elif len(active_candidates) > 1:
                                    raise ReconciliationError("ambiguous_position_match")
                                elif len(closed_candidates) > 0:
                                    trigger_reject("historical_link_collision")
                                    continue

                            # 2. Try FIFO matching
                            if not matched_uid:
                                close_cond_id = condition_id
                                close_asset = asset or payload.get("ticker")
                                if close_cond_id and close_asset and resolved_side:
                                    fifo_key = (close_run_id, close_cond_id, close_asset, resolved_side)
                                    candidates = historical_fifo_queue.get(fifo_key, [])
                                    active_candidates = [uid for uid in candidates if uid in open_positions]
                                    closed_candidates = [uid for uid in candidates if uid in closed_positions]

                                    if len(active_candidates) == 1:
                                        matched_uid = active_candidates[0]
                                    elif len(active_candidates) > 1:
                                        raise ReconciliationError("ambiguous_position_match")
                                    elif len(closed_candidates) > 0:
                                        trigger_reject("historical_link_collision")
                                        continue

                            if matched_uid:
                                open_pos = open_positions.get(matched_uid)
                                matched_key = matched_uid
                        else:
                            if execution_position_id not in open_positions:
                                raise ReconciliationError("orphan_close")
                            open_pos = open_positions[execution_position_id]
                            matched_key = execution_position_id

                        if not open_pos:
                            raise ReconciliationError("orphan_close")

                        # Now resolve condition_id
                        curr_condition_id = condition_id or open_pos.get("condition_id")
                        if not curr_condition_id:
                            trigger_reject("missing_condition_id")
                            continue

                        # Resolve side fallback if still None
                        if resolved_side is None:
                            resolved_side = open_pos.get("side")
                        if not resolved_side or resolved_side not in ("YES", "NO"):
                            trigger_reject("side_unresolvable")
                            continue

                        execution_entry_price = open_pos.get("execution_entry_price")
                        if execution_entry_price is None:
                            trigger_reject("missing_entry_price")
                            continue
                        try:
                            execution_entry_price = float(execution_entry_price)
                        except (TypeError, ValueError):
                            trigger_reject("invalid_entry_price")
                            continue

                        if exit_price is None:
                            trigger_reject("missing_exit_price")
                            continue
                        try:
                            exit_price = float(exit_price)
                        except (TypeError, ValueError):
                            trigger_reject("invalid_exit_price")
                            continue

                        exit_reason = exit_reason or "unknown"
                        source_replay_key = _sha256_text(f"{Path(source_file).as_posix()}|{line_idx}|{line_hash}")
                        execution_shares = open_pos["execution_shares"]

                        # Phase C core equity and drawdown calculations
                        execution_pnl = (exit_price - execution_entry_price) * execution_shares

                        execution_equity_before = execution_equity
                        execution_equity_after = execution_equity_before + execution_pnl

                        execution_equity = execution_equity_after
                        cumulative_pnl += execution_pnl

                        if execution_equity_after > peak_equity:
                            peak_equity = execution_equity_after

                        execution_drawdown = peak_equity - execution_equity_after
                        current_dd = execution_drawdown
                        if execution_drawdown > max_dd:
                            max_dd = execution_drawdown

                        if peak_equity > 0:
                            max_dd_pct = (max_dd / peak_equity) * 100.0
                        else:
                            max_dd_pct = 0.0

                        if execution_equity_after <= starting_bankroll * 0.10:
                            risk_of_ruin = True

                        if execution_pnl > 0:
                            execution_result_class = "win"
                            win_count += 1
                            gross_profit += execution_pnl
                        elif execution_pnl < 0:
                            execution_result_class = "loss"
                            loss_count += 1
                            gross_loss += abs(execution_pnl)
                        else:
                            execution_result_class = "flat"
                            flat_count += 1

                        curr_exec_position_id = execution_position_id or open_pos.get("execution_position_id")
                        emitted_event = {
                            "schema_version": SCHEMA_VERSION,
                            "event_type": "execution_paper_close",
                            "timestamp_utc": utc_now(),
                            "execution_run_id": execution_run_id,
                            "source_runtime_mode": parsed.get("mode") or parsed.get("source_runtime_mode") or "SIGNAL_MODE",
                            "source_run_id": parsed.get("run_id") or parsed.get("source_run_id") or "",
                            "source_event_type": event_type,
                            "source_file": str(source_file),
                            "source_line": line_idx,
                            "source_event_sha256": line_hash,
                            "execution_position_id": curr_exec_position_id if compat_mode == "historical" else matched_key,
                            "source_replay_key": source_replay_key,
                            "condition_id": curr_condition_id,
                            "asset": asset or open_pos.get("asset"),
                            "side": resolved_side,
                            "execution_track": track,
                            "execution_entry_price": execution_entry_price,
                            "execution_exit_price": exit_price,
                            "execution_shares": execution_shares,
                            "execution_pnl": execution_pnl,
                            "execution_exit_reason": exit_reason,
                            "execution_equity_before": execution_equity_before,
                            "execution_equity_after": execution_equity_after,
                            "cumulative_execution_pnl": cumulative_pnl,
                            "execution_drawdown": execution_drawdown,
                            "execution_max_drawdown": max_dd,
                            "execution_max_drawdown_pct": max_dd_pct,
                            "execution_result_class": execution_result_class,
                        }
                        if compat_mode == "historical":
                            emitted_event["historical_position_uid"] = open_pos.get("historical_position_uid")
                            emitted_event["identity_source"] = "historical_run_order_uid"
                        else:
                            emitted_event["identity_source"] = "canonical_position_id"

                    try:
                        dedupe_status = dedupe_index.register(emitted_event)
                    except DuplicateConflictError:
                        raise

                    if dedupe_status == "duplicate":
                        skipped_duplicate_count += 1
                        save_checkpoint(source_file, line_idx, line_hash, matched_key)
                        continue

                    append_jsonl_event(root, "trade", emitted_event)
                    emitted_event_count += 1

                    if is_open:
                        open_positions[matched_key] = emitted_event
                        if compat_mode == "historical":
                            run_id_val = parsed.get("run_id") or parsed.get("source_run_id") or ""
                            if resolved_order_id:
                                key = (run_id_val, str(resolved_order_id))
                                if key not in historical_order_queue:
                                    historical_order_queue[key] = []
                                historical_order_queue[key].append(historical_position_uid)
                            if condition_id and asset and resolved_side:
                                fifo_key = (run_id_val, condition_id, asset, resolved_side)
                                if fifo_key not in historical_fifo_queue:
                                    historical_fifo_queue[fifo_key] = []
                                historical_fifo_queue[fifo_key].append(historical_position_uid)
                    elif is_close:
                        closed_positions.append(matched_key)
                        del open_positions[matched_key]

                        # Emit execution_paper_equity_snapshot
                        snapshot_event = {
                            "schema_version": SCHEMA_VERSION,
                            "event_type": "execution_paper_equity_snapshot",
                            "timestamp_utc": utc_now(),
                            "execution_run_id": execution_run_id,
                            "execution_track": track,
                            "execution_bankroll_start": starting_bankroll,
                            "execution_equity": execution_equity,
                            "cumulative_execution_pnl": cumulative_pnl,
                            "execution_dd": execution_drawdown,
                            "execution_max_dd": max_dd,
                            "execution_max_dd_pct": max_dd_pct,
                            "risk_of_ruin": risk_of_ruin,
                        }
                        append_jsonl_event(root, "trade", snapshot_event)
                        emitted_event_count += 1

                    save_checkpoint(source_file, line_idx, line_hash, matched_key)

        except (IOError, OSError):
            raise

    if open_positions:
        reconciliation_status = "PARTIAL_OPEN_ALLOWED"
    else:
        reconciliation_status = "PASS"

    # 8. Reconciliation: Add equity replay consistency check
    if abs(execution_equity - (starting_bankroll + cumulative_pnl)) > 1e-6:
        raise ReconciliationError("equity replay consistency check failed: final_equity != starting_bankroll + cumulative_pnl")

    last_trade_id = None
    if open_positions:
        last_trade_id = next(iter(open_positions.keys()))
    elif closed_positions:
        last_trade_id = closed_positions[-1]

    save_checkpoint(
        Path(last_processed_file) if last_processed_file else None,
        last_processed_line,
        last_line_hash,
        last_trade_id
    )

    stopped = _runtime_event(
        "execution_paper_runtime_stopped",
        execution_run_id,
        status="COMPLETE",
        processed_event_count=processed_event_count,
        emitted_event_count=emitted_event_count + 1,
    )
    append_jsonl_event(root, "runtime", stopped)
    emitted_event_count += 1

    # Calculate metrics
    execution_net_pnl = cumulative_pnl
    execution_closed_trade_count = len(closed_positions)

    # WR calculations (excluding flats)
    denom = win_count + loss_count
    execution_wr = (win_count / denom) if denom > 0 else 0.0

    # PF calculations (gross profit / gross loss, undefined if gross loss is 0)
    if gross_loss == 0:
        execution_pf = None  # serializes to null in JSON
    else:
        execution_pf = gross_profit / gross_loss

    report = {
        "schema_version": "execution_paper.validation.v1",
        "generated_at": utc_now(),
        "execution_run_id": execution_run_id,
        "status": "PASS" if reconciliation_status in ("PASS", "PARTIAL_OPEN_ALLOWED") else "FAIL",
        "processed_source_events": processed_event_count,
        "emitted_events": emitted_event_count,
        "rejected_events": rejected_event_count,
        "skipped_duplicates": skipped_duplicate_count,
        "malformed_source_rows": malformed_source_count,
        "reconciliation_status": reconciliation_status,
        "execution_track": track,
        "execution_bankroll_start": starting_bankroll,
        "execution_net_pnl": execution_net_pnl,
        "execution_gross_profit": gross_profit,
        "execution_gross_loss": gross_loss,
        "execution_pf": execution_pf,
        "execution_wr": execution_wr,
        "execution_win_count": win_count,
        "execution_loss_count": loss_count,
        "execution_flat_count": flat_count,
        "execution_closed_trade_count": execution_closed_trade_count,
        "execution_max_dd": max_dd,
        "execution_max_dd_pct": max_dd_pct,
        "risk_of_ruin": risk_of_ruin,
        "pnl_label": "execution_pnl_5_share_model",
        "checkpoint_path": str(checkpoint_path) if checkpoint_path else "",
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
    parser.add_argument("--track", type=str, default="5_share")
    parser.add_argument("--starting-bankroll", type=float, default=250.0)
    parser.add_argument("--compat-mode", type=str, choices=["strict", "historical"], default="strict")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    output_root = args.output_root
    if args.dry_run and output_root == DEFAULT_OUTPUT_ROOT:
        import tempfile
        output_root = Path(tempfile.gettempdir()) / DEFAULT_OUTPUT_ROOT
    run_replay(
        source_root=args.source_root,
        output_root=output_root,
        max_events=args.max_events,
        track=args.track,
        starting_bankroll=args.starting_bankroll,
        dry_run=args.dry_run,
        compat_mode=args.compat_mode,
    )
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
