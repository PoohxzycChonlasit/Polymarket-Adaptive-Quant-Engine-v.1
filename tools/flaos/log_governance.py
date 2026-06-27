"""
FLAOS Phase A Log Governance Tool.

Offline-only maintenance script for inspecting, planning, dry-running, and
executing log cleanup. Never touches active runtime processes or JSONL files
(JSONL: compress only, never delete).

Usage:
    python tools/flaos/log_governance.py inspect [--root ROOT]
    python tools/flaos/log_governance.py plan [--root ROOT]
    python tools/flaos/log_governance.py dry-run [--root ROOT]
    python tools/flaos/log_governance.py execute --confirm [--root ROOT]
    python tools/flaos/log_governance.py report [--root ROOT]

Standard library only. No polymarket imports.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass, asdict, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROOT_DEFAULT = Path(__file__).resolve().parents[2]
MAX_ACTIONS = 800  # hard cap on file actions per execute run
JSONL_COMPRESS_AGE_DAYS = 3
LOG_BACKUP_KEEP = 5         # keep .log.1 through .log.5
LOG_BACKUP_MIN_AGE_DAYS = 1 # only delete backups older than this
VALIDATION_LOG_ZERO_AGE_DAYS = 7  # delete 0-byte session logs older than this
VALIDATION_RUN_ALERT_MB = 50  # alert if validation_run_output.log exceeds this
SESSION_LOG_RETENTION_DAYS = 7  # delete old session log groups (PID not running + age > this)

# Pattern: polytrade_bot_YYYYMMDD_HHMMSS_PID.log[.N]
_SESSION_LOG_RE = re.compile(
    r"^polytrade_bot_(\d{8})_(\d{6})_(\d+)\.log(?:\.(\d+))?$"
)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class FileAction:
    action: str          # DELETE | COMPRESS | ALERT | SKIP
    file: str
    bytes_before: int
    reason: str
    status: str = "PENDING"   # PENDING | SUCCESS | SKIPPED | FAILED | DRY_RUN | BLOCKED
    error: str | None = None
    bytes_after: int = 0


@dataclass
class ScanDomain:
    name: str
    file_count: int
    total_bytes: int
    candidates: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class InspectResult:
    timestamp: str
    root: str
    domains: dict[str, dict[str, Any]]
    active_session_guard: str
    health_status: str
    recommended_action: str


@dataclass
class Plan:
    plan_id: str
    root: str
    actions: list[FileAction]
    estimated_total_reclaim_mb: float
    warnings: list[str]
    dry_run_ready: bool


# ---------------------------------------------------------------------------
# Session guard
# ---------------------------------------------------------------------------

def _session_guard(root: Path) -> tuple[bool, list[str]]:
    """Return (safe_to_proceed, list_of_active_pids).
    Reads runtime/sessions/*.json; checks each session PID against OS process list.
    """
    sessions_dir = root / "runtime" / "sessions"
    active_pids: list[str] = []
    if not sessions_dir.exists():
        return True, []

    for f in sessions_dir.glob("session_*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            pid = data.get("pid")
            status = str(data.get("status", "")).upper()
            if pid and status not in ("COMPLETED", "TERMINATED", "UNKNOWN", "FAILED"):
                try:
                    os.kill(int(pid), 0)
                    active_pids.append(str(pid))
                except (ProcessLookupError, PermissionError, OSError):
                    pass  # PID not found = not running
        except (json.JSONDecodeError, IOError):
            pass

    return len(active_pids) == 0, active_pids


# ---------------------------------------------------------------------------
# File collection helpers
# ---------------------------------------------------------------------------

def _collect_log_backups(logs_dir: Path) -> list[Path]:
    """Find rotated log backups (.log.N where N > LOG_BACKUP_KEEP and age > LOG_BACKUP_MIN_AGE_DAYS)."""
    candidates: list[Path] = []
    if not logs_dir.exists():
        return candidates
    cutoff = time.time() - LOG_BACKUP_MIN_AGE_DAYS * 86400
    for f in logs_dir.iterdir():
        if not f.is_file():
            continue
        name = f.name
        # Match *.log.N pattern
        parts = name.rsplit(".", 2)
        if len(parts) == 3 and parts[2].isdigit() and parts[1] == "log":
            n = int(parts[2])
            if n > LOG_BACKUP_KEEP and f.stat().st_mtime < cutoff:
                candidates.append(f)
    return candidates


def _collect_zero_byte_session_logs(validation_dir: Path) -> list[Path]:
    """Find 0-byte session logs older than VALIDATION_LOG_ZERO_AGE_DAYS."""
    candidates: list[Path] = []
    if not validation_dir.exists():
        return candidates
    cutoff = time.time() - VALIDATION_LOG_ZERO_AGE_DAYS * 86400
    for f in validation_dir.glob("session_*"):
        if f.is_file() and f.stat().st_size == 0 and f.stat().st_mtime < cutoff:
            candidates.append(f)
    return candidates


def _collect_compressible_jsonl(event_stream_dir: Path) -> list[Path]:
    """Find .jsonl files older than JSONL_COMPRESS_AGE_DAYS (never current day)."""
    candidates: list[Path] = []
    if not event_stream_dir.exists():
        return candidates
    cutoff = time.time() - JSONL_COMPRESS_AGE_DAYS * 86400
    for f in event_stream_dir.glob("*.jsonl"):
        if f.stat().st_mtime < cutoff:
            candidates.append(f)
    return candidates


# ---------------------------------------------------------------------------
# Session log group helpers
# ---------------------------------------------------------------------------

def _parse_session_log_name(name: str) -> dict[str, Any] | None:
    """Parse polytrade_bot_YYYYMMDD_HHMMSS_PID.log[.N] → metadata dict or None."""
    m = _SESSION_LOG_RE.match(name)
    if not m:
        return None
    date_str, time_str, pid_str, rot_str = m.groups()
    try:
        session_date = datetime.strptime(date_str, "%Y%m%d").date()
    except ValueError:
        return None
    return {
        "session_key": f"{date_str}_{time_str}_{pid_str}",
        "session_date": date_str,
        "session_time": time_str,
        "pid": pid_str,
        "rotation_index": int(rot_str) if rot_str else 0,
    }


def _get_running_pids() -> set[str]:
    """Return set of string PIDs for currently running processes."""
    pids: set[str] = set()
    try:
        import psutil
        pids = {str(p.pid) for p in psutil.process_iter()}
    except ImportError:
        # psutil not available — use os.kill(pid, 0) probe approach via /proc or fallback
        # Check common PID range; safe fallback: only exclude current process
        pids.add(str(os.getpid()))
        # Try to enumerate PIDs from /proc if on Linux, otherwise probe a range
        try:
            if os.path.isdir("/proc"):
                pids = {e for e in os.listdir("/proc") if e.isdigit()}
            else:
                # Windows: use a safe but limited probe
                for pid in range(1, 65536):
                    try:
                        os.kill(pid, 0)
                        pids.add(str(pid))
                    except (ProcessLookupError, PermissionError):
                        pass
                    except OSError:
                        pids.add(str(pid))  # exists but no permission = running
        except (OSError, PermissionError):
            pass
    return pids


def collect_old_session_log_groups(
    logs_dir: Path,
    running_pids: set[str] | None = None,
    retention_days: int = SESSION_LOG_RETENTION_DAYS,
    now_utc: date | None = None,
) -> list[dict[str, Any]]:
    """Find log file groups for sessions older than retention_days whose PID is not running.

    Returns a list of action dicts (with session metadata) ready for plan/execute.
    Safety: never marks JSONL as DELETE. Only targets polytrade_bot_*.log[.N] files.
    """
    if not logs_dir.exists():
        return []
    if now_utc is None:
        now_utc = datetime.now(timezone.utc).date()
    if running_pids is None:
        running_pids = _get_running_pids()

    # Group files by session_key
    groups: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
    for f in logs_dir.iterdir():
        if not f.is_file():
            continue
        meta = _parse_session_log_name(f.name)
        if meta is None:
            continue
        key = meta["session_key"]
        groups.setdefault(key, []).append((f, meta))

    actions: list[dict[str, Any]] = []
    for key, file_list in groups.items():
        # All files in group share same session_date and pid
        meta0 = file_list[0][1]
        pid = meta0["pid"]
        session_date_str = meta0["session_date"]
        try:
            session_date = datetime.strptime(session_date_str, "%Y%m%d").date()
        except ValueError:
            continue
        age_days = (now_utc - session_date).days

        # Keep if recent or PID still running
        if age_days <= retention_days:
            continue
        if pid in running_pids:
            continue

        for f, meta in file_list:
            sz = f.stat().st_size
            actions.append({
                "action": "DELETE",
                "file": str(f),
                "bytes_before": sz,
                "bytes_after": 0,
                "status": "PENDING",
                "reason": "old_session_group",
                "session_key": key,
                "session_date": session_date_str,
                "pid": pid,
                "age_days": age_days,
            })

    return actions


# ---------------------------------------------------------------------------
# Subcommand: inspect
# ---------------------------------------------------------------------------

def cmd_inspect(root: Path, pretty: bool) -> int:
    logs_dir = root / "logs"
    validation_dir = root / "runtime" / "validation"
    event_stream_dir = root / "runtime" / "event_stream"
    sessions_dir = root / "runtime" / "sessions"
    vrun_log = root / "runtime" / "validation_run_output.log"

    guard_ok, active_pids = _session_guard(root)

    def _measure(d: Path) -> dict[str, Any]:
        if not d.exists():
            return {"file_count": 0, "total_bytes": 0}
        files = [f for f in d.iterdir() if f.is_file()]
        return {"file_count": len(files), "total_bytes": sum(f.stat().st_size for f in files)}

    backup_candidates = _collect_log_backups(logs_dir)
    zero_logs = _collect_zero_byte_session_logs(validation_dir)
    compressible = _collect_compressible_jsonl(event_stream_dir)
    session_actions = collect_old_session_log_groups(logs_dir)

    logs_stats = _measure(logs_dir)
    event_stats = _measure(event_stream_dir)
    valid_stats = _measure(validation_dir)
    session_stats = _measure(sessions_dir)

    vrun_bytes = vrun_log.stat().st_size if vrun_log.exists() else 0

    health = "HEALTHY"
    if logs_stats["total_bytes"] > 3_000_000_000:
        health = "CRITICAL"
    elif logs_stats["total_bytes"] > 1_000_000_000:
        health = "WARNING"
    elif event_stats["total_bytes"] > 500_000_000:
        health = "WARNING"

    result = {
        "timestamp": _iso_now(),
        "root": str(root),
        "domains": {
            "logs_rotated_backups": {
                "delete_candidates": len(backup_candidates),
                "candidate_bytes": sum(f.stat().st_size for f in backup_candidates),
            },
            "logs_old_session_groups": {
                "delete_candidates": len(session_actions),
                "candidate_bytes": sum(a["bytes_before"] for a in session_actions),
                "unique_session_keys": len({a["session_key"] for a in session_actions}),
            },
            "logs_all": logs_stats,
            "runtime_validation_logs": {
                **valid_stats,
                "zero_byte_delete_candidates": len(zero_logs),
            },
            "runtime_event_stream": {
                **event_stats,
                "compressible_jsonl_files": len(compressible),
                "compressible_bytes": sum(f.stat().st_size for f in compressible),
            },
            "runtime_sessions": session_stats,
            "validation_run_output": {
                "bytes": vrun_bytes,
                "mb": round(vrun_bytes / 1_000_000, 1),
                "alert_needed": vrun_bytes > VALIDATION_RUN_ALERT_MB * 1_000_000,
            },
        },
        "active_session_guard": "PASS" if guard_ok else f"BLOCKED — active PIDs: {active_pids}",
        "health_status": health,
        "recommended_action": "run plan" if (backup_candidates or compressible or session_actions) else "no action needed",
    }
    _print_json(result, pretty)
    return 0


# ---------------------------------------------------------------------------
# Subcommand: plan
# ---------------------------------------------------------------------------

def cmd_plan(root: Path, pretty: bool) -> int:
    logs_dir = root / "logs"
    validation_dir = root / "runtime" / "validation"
    event_stream_dir = root / "runtime" / "event_stream"
    vrun_log = root / "runtime" / "validation_run_output.log"

    actions: list[dict[str, Any]] = []
    warnings: list[str] = []
    total_reclaim = 0

    for f in _collect_log_backups(logs_dir):
        sz = f.stat().st_size
        actions.append({
            "action": "DELETE",
            "file": str(f),
            "bytes_before": sz,
            "reason": f"rotated backup (N>{LOG_BACKUP_KEEP}) older than {LOG_BACKUP_MIN_AGE_DAYS}d",
            "status": "PENDING",
        })
        total_reclaim += sz

    for f in _collect_zero_byte_session_logs(validation_dir):
        actions.append({
            "action": "DELETE",
            "file": str(f),
            "bytes_before": 0,
            "reason": f"0-byte session log older than {VALIDATION_LOG_ZERO_AGE_DAYS}d",
            "status": "PENDING",
        })

    for f in _collect_compressible_jsonl(event_stream_dir):
        sz = f.stat().st_size
        actions.append({
            "action": "COMPRESS",
            "file": str(f),
            "bytes_before": sz,
            "reason": f"JSONL older than {JSONL_COMPRESS_AGE_DAYS}d — compress only, never delete",
            "status": "PENDING",
        })
        total_reclaim += int(sz * 0.85)  # estimate 85% compression

    # Session-age-based cleanup
    session_group_actions = collect_old_session_log_groups(logs_dir)
    for sa in session_group_actions:
        actions.append(sa)
        total_reclaim += sa["bytes_before"]

    if vrun_log.exists() and vrun_log.stat().st_size > VALIDATION_RUN_ALERT_MB * 1_000_000:
        actions.append({
            "action": "ALERT",
            "file": str(vrun_log),
            "bytes_before": vrun_log.stat().st_size,
            "reason": f"exceeds {VALIDATION_RUN_ALERT_MB}MB alert threshold — manual rotation recommended",
            "status": "PENDING",
        })

    if len(actions) > MAX_ACTIONS:
        warnings.append(f"Plan contains {len(actions)} actions which exceeds hard cap {MAX_ACTIONS}. Execute will be truncated.")

    result = {
        "plan_id": f"PLAN-{_datestamp()}-001",
        "root": str(root),
        "actions": actions[:MAX_ACTIONS],
        "total_actions": len(actions),
        "capped": len(actions) > MAX_ACTIONS,
        "estimated_reclaim_mb": round(total_reclaim / 1_000_000, 1),
        "warnings": warnings,
        "dry_run_ready": True,
    }
    _print_json(result, pretty)
    return 0


# ---------------------------------------------------------------------------
# Subcommand: dry-run
# ---------------------------------------------------------------------------

def cmd_dry_run(root: Path, pretty: bool) -> int:
    guard_ok, active_pids = _session_guard(root)

    logs_dir = root / "logs"
    validation_dir = root / "runtime" / "validation"
    event_stream_dir = root / "runtime" / "event_stream"
    vrun_log = root / "runtime" / "validation_run_output.log"

    actions: list[dict[str, Any]] = []

    for f in _collect_log_backups(logs_dir):
        status = "DRY_RUN" if guard_ok else "BLOCKED"
        actions.append({"action": "DELETE", "file": str(f), "bytes_before": f.stat().st_size,
                         "status": status, "reason": "rotated backup"})

    for f in _collect_zero_byte_session_logs(validation_dir):
        status = "DRY_RUN" if guard_ok else "BLOCKED"
        actions.append({"action": "DELETE", "file": str(f), "bytes_before": 0,
                         "status": status, "reason": "0-byte session log"})

    for f in _collect_compressible_jsonl(event_stream_dir):
        actions.append({"action": "COMPRESS", "file": str(f), "bytes_before": f.stat().st_size,
                         "status": "DRY_RUN", "reason": "old JSONL — compress only"})

    for sa in collect_old_session_log_groups(logs_dir):
        status = "DRY_RUN" if guard_ok else "BLOCKED"
        sa["status"] = status
        actions.append(sa)

    if vrun_log.exists() and vrun_log.stat().st_size > VALIDATION_RUN_ALERT_MB * 1_000_000:
        actions.append({"action": "ALERT", "file": str(vrun_log),
                         "bytes_before": vrun_log.stat().st_size, "status": "DRY_RUN", "reason": "alert threshold"})

    actions = actions[:MAX_ACTIONS]
    result = {
        "mode": "DRY_RUN",
        "session_guard": "PASS" if guard_ok else f"BLOCKED — {active_pids}",
        "total_actions": len(actions),
        "actions": actions,
        "note": "No files were modified. Re-run with execute --confirm to apply.",
    }
    _print_json(result, pretty)
    return 0


# ---------------------------------------------------------------------------
# Subcommand: execute
# ---------------------------------------------------------------------------

def cmd_execute(root: Path, confirm: bool, pretty: bool) -> int:
    if not confirm:
        # Without --confirm, run in dry-run mode only. mode field signals this.
        return cmd_dry_run(root, pretty)

    guard_ok, active_pids = _session_guard(root)
    if not guard_ok:
        _print_json({
            "status": "STOP_AND_ESCALATE",
            "error_type": "ACTIVE_SESSION_BLOCKED",
            "message": f"Active runtime session detected (PIDs: {active_pids}). Aborting execute.",
            "safe_to_continue": False,
            "recommended_action": "Wait for sessions to complete, then re-run.",
        }, pretty)
        return 1

    logs_dir = root / "logs"
    validation_dir = root / "runtime" / "validation"
    event_stream_dir = root / "runtime" / "event_stream"
    vrun_log = root / "runtime" / "validation_run_output.log"

    executed: list[dict[str, Any]] = []
    action_count = 0

    # DELETE rotated log backups
    for f in sorted(_collect_log_backups(logs_dir)):
        if action_count >= MAX_ACTIONS:
            break
        sz = f.stat().st_size
        try:
            f.unlink()
            executed.append({"action": "DELETE", "file": str(f), "bytes_before": sz,
                              "bytes_after": 0, "status": "SUCCESS", "error": None})
        except OSError as e:
            executed.append({"action": "DELETE", "file": str(f), "bytes_before": sz,
                              "bytes_after": sz, "status": "FAILED", "error": str(e)})
        action_count += 1

    # DELETE zero-byte session logs
    for f in _collect_zero_byte_session_logs(validation_dir):
        if action_count >= MAX_ACTIONS:
            break
        try:
            f.unlink()
            executed.append({"action": "DELETE", "file": str(f), "bytes_before": 0,
                              "bytes_after": 0, "status": "SUCCESS", "error": None})
        except OSError as e:
            executed.append({"action": "DELETE", "file": str(f), "bytes_before": 0,
                              "bytes_after": 0, "status": "FAILED", "error": str(e)})
        action_count += 1

    # COMPRESS JSONL files
    for f in _collect_compressible_jsonl(event_stream_dir):
        if action_count >= MAX_ACTIONS:
            break
        sz = f.stat().st_size
        gz_path = f.with_suffix(".jsonl.gz")
        try:
            with f.open("rb") as src, gzip.open(gz_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
            executed.append({"action": "COMPRESS", "file": str(f), "bytes_before": sz,
                              "bytes_after": gz_path.stat().st_size, "status": "SUCCESS", "error": None,
                              "output": str(gz_path)})
        except OSError as e:
            if gz_path.exists():
                gz_path.unlink(missing_ok=True)
            executed.append({"action": "COMPRESS", "file": str(f), "bytes_before": sz,
                              "bytes_after": sz, "status": "FAILED", "error": str(e)})
        action_count += 1

    # DELETE old session log groups
    for sa in collect_old_session_log_groups(logs_dir, running_pids=set(_session_guard(root)[1]) or None):
        if action_count >= MAX_ACTIONS:
            break
        f = Path(sa["file"])
        if not f.exists():
            continue
        sz = f.stat().st_size
        try:
            f.unlink()
            sa_result = dict(sa)
            sa_result.update({"bytes_after": 0, "status": "SUCCESS", "error": None})
            executed.append(sa_result)
        except OSError as e:
            sa_result = dict(sa)
            sa_result.update({"bytes_after": sz, "status": "FAILED", "error": str(e)})
            executed.append(sa_result)
        action_count += 1

    # ALERT for validation_run_output.log
    if vrun_log.exists() and vrun_log.stat().st_size > VALIDATION_RUN_ALERT_MB * 1_000_000:
        executed.append({"action": "ALERT", "file": str(vrun_log),
                          "bytes_before": vrun_log.stat().st_size, "status": "SUCCESS",
                          "error": None, "message": "Exceeds alert threshold. Manual rotation recommended."})

    bytes_reclaimed = sum(e["bytes_before"] - e.get("bytes_after", 0)
                          for e in executed if e["status"] == "SUCCESS" and e["action"] == "DELETE")
    bytes_compressed = sum(e["bytes_before"] for e in executed
                           if e["status"] == "SUCCESS" and e["action"] == "COMPRESS")

    result = {
        "mode": "EXECUTE",
        "session_guard": "PASS",
        "total_actions": len(executed),
        "summary": {
            "deleted": sum(1 for e in executed if e["action"] == "DELETE" and e["status"] == "SUCCESS"),
            "compressed": sum(1 for e in executed if e["action"] == "COMPRESS" and e["status"] == "SUCCESS"),
            "failed": sum(1 for e in executed if e["status"] == "FAILED"),
            "bytes_reclaimed": bytes_reclaimed,
            "bytes_compressed": bytes_compressed,
            "mb_reclaimed": round(bytes_reclaimed / 1_000_000, 1),
        },
        "actions": executed,
    }
    _print_json(result, pretty)
    return 0


# ---------------------------------------------------------------------------
# Subcommand: report
# ---------------------------------------------------------------------------

def cmd_report(root: Path, pretty: bool) -> int:
    logs_dir = root / "logs"
    event_stream_dir = root / "runtime" / "event_stream"

    def _size_mb(d: Path) -> float:
        if not d.exists():
            return 0.0
        return round(sum(f.stat().st_size for f in d.rglob("*") if f.is_file()) / 1_000_000, 1)

    result = {
        "timestamp": _iso_now(),
        "root": str(root),
        "current_sizes": {
            "logs_mb": _size_mb(logs_dir),
            "runtime_event_stream_mb": _size_mb(event_stream_dir),
        },
        "log_backup_remaining": len(_collect_log_backups(logs_dir)),
        "compressible_jsonl_remaining": len(_collect_compressible_jsonl(event_stream_dir)),
        "recommendation": "run inspect to assess current state",
    }
    _print_json(result, pretty)
    return 0


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _iso_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _datestamp() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _print_json(data: Any, pretty: bool) -> None:
    print(json.dumps(data, indent=2 if pretty else None, default=str))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="log_governance.py",
        description="FLAOS Phase A Log Governance — offline, read-only by default.",
    )
    parser.add_argument("--root", type=Path, default=None,
                        help="Override project root (for testing with temp dirs)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")

    sub = parser.add_subparsers(dest="subcommand", required=True)

    sub.add_parser("inspect", help="Scan target dirs and report sizes/candidates (read-only)")
    sub.add_parser("plan", help="Build action plan from retention policies (read-only)")
    sub.add_parser("dry-run", help="Show actions that would run without executing (read-only)")

    exec_p = sub.add_parser("execute", help="Execute plan (requires --confirm)")
    exec_p.add_argument("--confirm", action="store_true",
                        help="Required flag to actually execute. Without it, runs dry-run only.")

    sub.add_parser("report", help="Show current state after execution (read-only)")

    args = parser.parse_args()
    root = args.root if args.root else ROOT_DEFAULT
    pretty = args.pretty

    if args.subcommand == "inspect":
        sys.exit(cmd_inspect(root, pretty))
    elif args.subcommand == "plan":
        sys.exit(cmd_plan(root, pretty))
    elif args.subcommand == "dry-run":
        sys.exit(cmd_dry_run(root, pretty))
    elif args.subcommand == "execute":
        sys.exit(cmd_execute(root, confirm=args.confirm, pretty=pretty))
    elif args.subcommand == "report":
        sys.exit(cmd_report(root, pretty))


if __name__ == "__main__":
    main()
