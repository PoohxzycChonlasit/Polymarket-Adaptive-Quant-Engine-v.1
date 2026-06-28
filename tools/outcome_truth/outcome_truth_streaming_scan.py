"""Bounded offline JSONL scanner for outcome-truth readiness evidence.

The scanner processes one file at a time, maintains only aggregate counters,
and writes resumable checkpoints outside source JSONL directories. It has no
runtime trading imports and no authority over strategy, risk, or execution.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


CHECKPOINT_SCHEMA_VERSION = "outcome_truth_streaming_checkpoint_v1"
REPORT_SCHEMA_VERSION = "outcome_truth_streaming_report_v1"
MAX_CHECKPOINT_BYTES = 4 * 1024 * 1024
SCAN_TYPES = ("decision_log", "market_snapshots", "trade_journal")
EPOCH_ALIASES = (
    "epoch_start_ts",
    "epoch_start",
    "market_epoch_start_ts",
    "market_epoch_start",
    "event_start_ts",
)
OFFICIAL_RESOLUTION_FIELDS = (
    "settlement_outcome",
    "resolution_outcome",
    "resolved_outcome",
    "official_outcome",
    "resolution",
    "winner",
    "payout_numerator",
    "payout_denominator",
)


class SourceMutationError(RuntimeError):
    """Raised when a checkpoint no longer matches its source file."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Atomically replace a JSON document without exposing a partial file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def checkpoint_path_for(checkpoint_dir: Path, scan_type: str, source_file: Path) -> Path:
    safe_name = "".join(character if character.isalnum() or character in "._-" else "_" for character in source_file.name)
    return Path(checkpoint_dir) / f"{scan_type}__{safe_name}.checkpoint.json"


def _is_within(child: Path, parent: Path) -> bool:
    child = child.resolve()
    parent = parent.resolve()
    return child == parent or parent in child.parents


def _validate_output_locations(source_dir: Path, checkpoint_dir: Path, report_path: Path) -> None:
    if _is_within(checkpoint_dir, source_dir) or _is_within(report_path, source_dir):
        raise ValueError("checkpoint and report paths must be outside source directory")


def _payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload")
    return payload if isinstance(payload, dict) else event


def _has_join_key(payload: dict[str, Any]) -> bool:
    if payload.get("condition_id") in (None, ""):
        return False
    return any(payload.get(alias) not in (None, "") for alias in EPOCH_ALIASES)


def _has_model_output(payload: dict[str, Any]) -> bool:
    envelope = payload.get("entry_model_truth_envelope_v1")
    envelope = envelope if isinstance(envelope, dict) else {}
    return payload.get("model_output_ready") is True or any(
        value not in (None, "")
        for value in (
            payload.get("model_probability_yes"),
            payload.get("model_p_yes"),
            payload.get("p_yes"),
            envelope.get("model_probability_yes"),
        )
    )


def _has_timestamp(event: dict[str, Any], payload: dict[str, Any]) -> bool:
    return any(
        value not in (None, "")
        for value in (
            event.get("timestamp_utc"),
            payload.get("decision_timestamp"),
            payload.get("timestamp"),
        )
    )


def _increment_common(counts: Counter[str], payload: dict[str, Any]) -> None:
    counts["valid_rows"] += 1
    if _has_join_key(payload):
        counts["join_key_rows"] += 1


def _aggregate_decision(counts: Counter[str], event: dict[str, Any], payload: dict[str, Any]) -> None:
    _increment_common(counts, payload)
    if _has_model_output(payload):
        counts["model_ready_rows"] += 1
    if _has_timestamp(event, payload):
        counts["timestamp_rows"] += 1


def _aggregate_snapshot(counts: Counter[str], _event: dict[str, Any], payload: dict[str, Any]) -> None:
    _increment_common(counts, payload)
    try:
        seconds_remaining = float(payload.get("seconds_remaining"))
        yes_bid = float(payload.get("yes_bid"))
    except (TypeError, ValueError):
        return
    if seconds_remaining >= 120:
        return
    counts["near_close_proxy_rows"] += 1
    if yes_bid >= 0.70 or yes_bid <= 0.30:
        counts["provisional_resolved_rows"] += 1
    else:
        counts["provisional_ambiguous_rows"] += 1


def _aggregate_journal(counts: Counter[str], event: dict[str, Any], payload: dict[str, Any]) -> None:
    _increment_common(counts, payload)
    if event.get("event_type") == "trade_close":
        counts["trade_close_rows"] += 1
        if payload.get("trade_result") not in (None, ""):
            counts["native_trade_result_rows"] += 1
    if any(payload.get(field) not in (None, "") for field in OFFICIAL_RESOLUTION_FIELDS):
        counts["strict_official_resolution_rows"] += 1


AGGREGATORS: dict[str, Callable[[Counter[str], dict[str, Any], dict[str, Any]], None]] = {
    "decision_log": _aggregate_decision,
    "market_snapshots": _aggregate_snapshot,
    "trade_journal": _aggregate_journal,
}


def _rss_mb_windows() -> float:
    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    process = ctypes.windll.kernel32.GetCurrentProcess()
    if not ctypes.windll.psapi.GetProcessMemoryInfo(process, ctypes.byref(counters), counters.cb):
        raise OSError("GetProcessMemoryInfo failed")
    return counters.WorkingSetSize / (1024 * 1024)


def current_rss_mb() -> float:
    if sys.platform == "win32":
        return _rss_mb_windows()
    try:
        import resource

        divisor = 1024.0 if sys.platform != "darwin" else 1024.0 * 1024.0
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / divisor
    except (ImportError, OSError):
        return 0.0


def _probe_memory(rss_reader: Callable[[], float]) -> tuple[str, float | None, str | None]:
    try:
        rss_mb = float(rss_reader())
        if rss_mb < 0:
            raise ValueError("RSS probe returned a negative value")
        return "AVAILABLE", rss_mb, None
    except Exception as exc:
        warning = f"memory_probe_unavailable: {type(exc).__name__}: {exc}"
        return "UNAVAILABLE", None, warning


def _source_identity(source_file: Path) -> tuple[int, int]:
    stat = source_file.stat()
    return stat.st_size, stat.st_mtime_ns


def _load_checkpoint(path: Path, source_file: Path, scan_type: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        content = handle.read(MAX_CHECKPOINT_BYTES + 1)
    if len(content.encode("utf-8")) > MAX_CHECKPOINT_BYTES:
        raise SourceMutationError(f"checkpoint exceeds bounded size: {path}")
    checkpoint = json.loads(content)
    size, mtime = _source_identity(source_file)
    if (
        checkpoint.get("schema_version") != CHECKPOINT_SCHEMA_VERSION
        or checkpoint.get("scan_type") != scan_type
        or checkpoint.get("source_file") != str(source_file.resolve())
        or checkpoint.get("file_size") != size
        or checkpoint.get("file_mtime") != mtime
    ):
        raise SourceMutationError(f"checkpoint invalidated by source mutation: {source_file}")
    return checkpoint


def _checkpoint_payload(
    *,
    scan_type: str,
    source_file: Path,
    started_at: str,
    last_completed_line: int,
    lines_seen: int,
    malformed_lines: int,
    aggregate_counts: Counter[str],
    status: str,
    memory_probe_status: str,
    warnings: list[str],
) -> dict[str, Any]:
    size, mtime = _source_identity(source_file)
    return {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "scan_type": scan_type,
        "source_file": str(source_file.resolve()),
        "file_size": size,
        "file_mtime": mtime,
        "last_completed_line": last_completed_line,
        "lines_seen": lines_seen,
        "malformed_lines": malformed_lines,
        "aggregate_counts": dict(aggregate_counts),
        "started_at": started_at,
        "checkpointed_at": utc_now(),
        "status": status,
        "memory_probe_status": memory_probe_status,
        "warnings": warnings,
    }


def _scan_one_file(
    *,
    scan_type: str,
    source_file: Path,
    checkpoint_dir: Path,
    max_additional_lines: int | None,
    memory_limit_mb: float,
    rss_reader: Callable[[], float],
    require_memory_probe: bool,
    progress_every: int,
) -> dict[str, Any]:
    checkpoint_path = checkpoint_path_for(checkpoint_dir, scan_type, source_file)
    checkpoint = _load_checkpoint(checkpoint_path, source_file, scan_type)
    started_at = checkpoint["started_at"] if checkpoint else utc_now()
    last_completed_line = int(checkpoint.get("last_completed_line", 0)) if checkpoint else 0
    lines_seen = int(checkpoint.get("lines_seen", 0)) if checkpoint else 0
    malformed_lines = int(checkpoint.get("malformed_lines", 0)) if checkpoint else 0
    counts: Counter[str] = Counter(checkpoint.get("aggregate_counts", {})) if checkpoint else Counter()
    added_lines = 0
    status = "COMPLETE"
    memory_probe_status = str(checkpoint.get("memory_probe_status", "AVAILABLE")) if checkpoint else "AVAILABLE"
    warnings = list(checkpoint.get("warnings", [])) if checkpoint else []
    probe_status, last_rss_mb, warning = _probe_memory(rss_reader)
    if probe_status == "UNAVAILABLE":
        memory_probe_status = "UNAVAILABLE"
        if warning and warning not in warnings:
            warnings.append(warning)
        if require_memory_probe:
            status = "MEMORY_PROBE_REQUIRED_UNAVAILABLE"
    elif last_rss_mb is not None and last_rss_mb > memory_limit_mb:
        status = "MEMORY_LIMIT_REACHED"

    if status == "COMPLETE":
        with source_file.open("r", encoding="utf-8", errors="strict") as handle:
            for line_number, line in enumerate(handle, start=1):
                if line_number <= last_completed_line:
                    continue
                if max_additional_lines is not None and added_lines >= max_additional_lines:
                    status = "MAX_LINES_REACHED"
                    break
                probe_status, last_rss_mb, warning = _probe_memory(rss_reader)
                if probe_status == "UNAVAILABLE":
                    memory_probe_status = "UNAVAILABLE"
                    if warning and warning not in warnings:
                        warnings.append(warning)
                    if require_memory_probe:
                        status = "MEMORY_PROBE_REQUIRED_UNAVAILABLE"
                        break
                elif last_rss_mb is not None and last_rss_mb > memory_limit_mb:
                    status = "MEMORY_LIMIT_REACHED"
                    break
                lines_seen += 1
                added_lines += 1
                try:
                    event = json.loads(line)
                    if not isinstance(event, dict):
                        raise json.JSONDecodeError("event must be an object", line, 0)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    malformed_lines += 1
                    status = "MALFORMED_JSON"
                    break
                AGGREGATORS[scan_type](counts, event, _payload(event))
                last_completed_line = line_number
                if progress_every > 0 and lines_seen % progress_every == 0:
                    progress = _checkpoint_payload(
                        scan_type=scan_type,
                        source_file=source_file,
                        started_at=started_at,
                        last_completed_line=last_completed_line,
                        lines_seen=lines_seen,
                        malformed_lines=malformed_lines,
                        aggregate_counts=counts,
                        status="IN_PROGRESS",
                        memory_probe_status=memory_probe_status,
                        warnings=warnings,
                    )
                    atomic_write_json(checkpoint_path, progress)
                    rss_display = f"{last_rss_mb:.1f}" if last_rss_mb is not None else "unavailable"
                    print(
                        f"[outcome-truth-scan] type={scan_type} file={source_file.name} "
                        f"lines={lines_seen} rss_mb={rss_display}",
                        flush=True,
                    )

    final = _checkpoint_payload(
        scan_type=scan_type,
        source_file=source_file,
        started_at=started_at,
        last_completed_line=last_completed_line,
        lines_seen=lines_seen,
        malformed_lines=malformed_lines,
        aggregate_counts=counts,
        status=status,
        memory_probe_status=memory_probe_status,
        warnings=warnings,
    )
    atomic_write_json(checkpoint_path, final)
    return final


def scan_files(
    *,
    scan_type: str,
    source_dir: str | Path,
    checkpoint_dir: str | Path,
    report_path: str | Path,
    max_files: int | None = None,
    max_lines: int | None = None,
    memory_limit_mb: float = 450.0,
    rss_reader: Callable[[], float] = current_rss_mb,
    require_memory_probe: bool = False,
    progress_every: int = 100_000,
) -> dict[str, Any]:
    """Scan bounded JSONL files sequentially and persist a summary report."""
    if scan_type not in SCAN_TYPES:
        raise ValueError(f"scan_type must be one of {SCAN_TYPES}")
    if memory_limit_mb <= 0:
        raise ValueError("memory_limit_mb must be positive")
    source_dir = Path(source_dir)
    checkpoint_dir = Path(checkpoint_dir)
    report_path = Path(report_path)
    _validate_output_locations(source_dir, checkpoint_dir, report_path)

    files = sorted(path for path in source_dir.glob("*.jsonl") if path.is_file())
    if max_files is not None:
        files = files[: max(0, max_files)]
    remaining_lines = max_lines
    aggregate_counts: Counter[str] = Counter()
    file_results: list[dict[str, Any]] = []
    status = "COMPLETE"

    for source_file in files:
        result = _scan_one_file(
            scan_type=scan_type,
            source_file=source_file,
            checkpoint_dir=checkpoint_dir,
            max_additional_lines=remaining_lines,
            memory_limit_mb=memory_limit_mb,
            rss_reader=rss_reader,
            require_memory_probe=require_memory_probe,
            progress_every=progress_every,
        )
        file_results.append(result)
        aggregate_counts.update(result["aggregate_counts"])
        if max_lines is not None:
            remaining_lines = max(0, max_lines - sum(item["lines_seen"] for item in file_results))
        if result["status"] != "COMPLETE":
            status = result["status"]
            break
        if remaining_lines == 0 and max_lines is not None:
            status = "MAX_LINES_REACHED"
            break

    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "scan_type": scan_type,
        "source_dir": str(source_dir.resolve()),
        "checkpoint_dir": str(checkpoint_dir.resolve()),
        "generated_at": utc_now(),
        "status": status,
        "ready": status == "COMPLETE" and all(item["malformed_lines"] == 0 for item in file_results),
        "files_available": len(sorted(source_dir.glob("*.jsonl"))),
        "files_processed": len(file_results),
        "lines_seen": sum(item["lines_seen"] for item in file_results),
        "malformed_lines": sum(item["malformed_lines"] for item in file_results),
        "aggregate_counts": dict(aggregate_counts),
        "file_results": file_results,
        "memory_limit_mb": memory_limit_mb,
        "require_memory_probe": require_memory_probe,
        "memory_probe_status": (
            "UNAVAILABLE"
            if any(item["memory_probe_status"] == "UNAVAILABLE" for item in file_results)
            else "AVAILABLE"
        ),
        "warnings": list(
            dict.fromkeys(warning for item in file_results for warning in item.get("warnings", []))
        ),
        "guardrails": {
            "offline_only": True,
            "source_files_modified": False,
            "runtime_authority": False,
            "strategy_risk_execution_changed": False,
        },
    }
    atomic_write_json(report_path, report)
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scan-type", required=True, choices=SCAN_TYPES)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--checkpoint-dir", required=True, type=Path)
    parser.add_argument("--report-path", required=True, type=Path)
    parser.add_argument("--max-files", type=int)
    parser.add_argument("--max-lines", type=int)
    parser.add_argument("--memory-limit-mb", type=float, default=450.0)
    parser.add_argument("--require-memory-probe", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        report = scan_files(
            scan_type=args.scan_type,
            source_dir=args.source_dir,
            checkpoint_dir=args.checkpoint_dir,
            report_path=args.report_path,
            max_files=args.max_files,
            max_lines=args.max_lines,
            memory_limit_mb=args.memory_limit_mb,
            require_memory_probe=args.require_memory_probe,
        )
    except SourceMutationError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps({"status": report["status"], "ready": report["ready"], "report": str(args.report_path)}))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
