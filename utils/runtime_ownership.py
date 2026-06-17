from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Any


OWNER_SCHEMA_VERSION = "1.0"


class DuplicateRuntimeError(RuntimeError):
    """Raised when an active runtime owner already exists."""

    def __init__(
        self,
        message: str,
        *,
        reason: str,
        existing_owner: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.existing_owner = existing_owner or {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _default_process_checker(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if os.name == "nt":
        try:
            import ctypes

            process_query_limited_information = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(
                process_query_limited_information,
                False,
                int(pid),
            )
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:
            return True
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return True


def _get_process_cmdline(pid: int) -> str | None:
    try:
        import psutil
        proc = psutil.Process(pid)
        return " ".join(proc.cmdline())
    except Exception:
        # Fallback for Windows
        if os.name == "nt":
            try:
                out = subprocess.check_output(
                    ["wmic", "process", "where", f"ProcessId={pid}", "get", "CommandLine"],
                    stderr=subprocess.DEVNULL,
                    text=True
                )
                lines = [l.strip() for l in out.splitlines() if l.strip()]
                if len(lines) > 1:
                    return lines[1]
            except Exception:
                pass
        # Fallback for Linux /proc
        else:
            try:
                cmdline_file = Path(f"/proc/{pid}/cmdline")
                if cmdline_file.exists():
                    return cmdline_file.read_text(encoding="utf-8").replace("\x00", " ")
            except Exception:
                pass
    return None


def _atomic_json_replace(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass


@dataclass
class RuntimeOwner:
    manager: "RuntimeOwnerManager"
    pid: int
    run_id: str
    mode: str
    acquired: bool = True

    def heartbeat(self) -> bool:
        return self.manager.heartbeat(pid=self.pid, run_id=self.run_id, mode=self.mode)

    def mark_stopping(self) -> bool:
        return self.manager.mark_stopping(pid=self.pid, run_id=self.run_id, mode=self.mode)

    def release(self) -> bool:
        return self.manager.release(pid=self.pid, run_id=self.run_id, mode=self.mode)


class RuntimeOwnerManager:
    """Paper runtime ownership guard.

    This helper owns process-level evidence integrity only. It does not alter
    strategy, risk, execution, replay, or lineage behavior.
    """

    def __init__(
        self,
        *,
        owner_dir: str | Path = "runtime/ownership",
        pid: int | None = None,
        run_id: str = "",
        repo_root: str | Path | None = None,
        process_checker: Callable[[int], bool] | None = None,
        telemetry_emit: Callable[[str, dict[str, Any]], Any] | None = None,
    ) -> None:
        self.owner_dir = Path(owner_dir)
        self.pid = int(pid if pid is not None else os.getpid())
        self.run_id = str(run_id or "")
        self.repo_root = str(Path(repo_root or Path.cwd()).resolve())
        self.process_checker = process_checker or _default_process_checker
        self.telemetry_emit = telemetry_emit

    def owner_path(self, mode: str) -> Path:
        if str(mode).lower() == "paper":
            return self.owner_dir / "paper_runtime_owner.json"
        return self.owner_dir / f"{str(mode).lower()}_runtime_owner.json"

    def _lock_path(self, mode: str) -> Path:
        return self.owner_path(mode).with_suffix(".startup.lock")

    def _recover_stale_lock(self, lock_path: Path) -> None:
        if not lock_path.exists():
            return
        try:
            content = lock_path.read_text(encoding="utf-8").strip().split("\n")
            if len(content) >= 3:
                lock_pid = int(content[0])
                lock_run_id = content[1]
                lock_time_str = content[2]
                
                try:
                    lock_time = datetime.fromisoformat(lock_time_str.replace("Z", "+00:00"))
                    age = (datetime.now(timezone.utc) - lock_time).total_seconds()
                except Exception:
                    age = 9999.0
                
                pid_alive = self.process_checker(lock_pid)
                cmdline_valid = True
                if pid_alive:
                    cmdline = _get_process_cmdline(lock_pid)
                    if cmdline:
                        is_python = "python" in cmdline.lower() or "py" in cmdline.lower()
                        is_main = "main.py" in cmdline.lower()
                        is_same_dir = str(self.repo_root).lower() in cmdline.lower() or "polymarket-adaptive-quant-engine" in cmdline.lower()
                        if not (is_python and is_main and is_same_dir):
                            cmdline_valid = False
                    else:
                        cmdline_valid = False
                
                is_stale = not pid_alive or not cmdline_valid or age > 10.0
                if is_stale:
                    lock_path.unlink(missing_ok=True)
                    if self.telemetry_emit:
                        try:
                            self.telemetry_emit("log_system_health", {
                                "event_type": "startup_lock_recovered",
                                "pid": lock_pid,
                                "lock_run_id": lock_run_id,
                                "lock_age": age,
                            })
                        except Exception:
                            pass
        except Exception:
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:
                pass

    def _archive_stale_owner(self, mode: str) -> None:
        path = self.owner_path(mode)
        if not path.exists():
            return
        archive_dir = self.owner_dir / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        dest = archive_dir / f"{mode}_runtime_owner_{ts}_backup.json"
        try:
            shutil.copy2(path, dest)
        except Exception:
            pass

    def acquire(self, *, mode: str = "paper", override: bool = False) -> RuntimeOwner:
        normalized_mode = str(mode or "paper").lower()
        lock_path = self._lock_path(normalized_mode)
        self.owner_dir.mkdir(parents=True, exist_ok=True)
        
        # Recover stale lock if present
        self._recover_stale_lock(lock_path)
        
        lock_fd: int | None = None
        try:
            lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.write(lock_fd, f"{self.pid}\n{self.run_id}\n{_utc_now()}\n".encode("utf-8"))
        except FileExistsError as exc:
            raise DuplicateRuntimeError(
                "Runtime ownership startup lock is active.",
                reason="startup_lock_active",
            ) from exc

        try:
            existing = self._read_owner(normalized_mode)
            previous_owner: dict[str, Any] | None = None
            recovered = False
            recovery_reason = ""
            
            if existing is None:
                pass
            elif existing.get("_unreadable"):
                self._archive_stale_owner(normalized_mode)
                try:
                    self.owner_path(normalized_mode).unlink(missing_ok=True)
                except OSError:
                    pass
                recovered = True
                recovery_reason = "owner_file_unreadable"
            else:
                existing_pid = self._int_or_zero(existing.get("pid"))
                status = str(existing.get("status") or "").strip().lower()
                heartbeat_utc_str = existing.get("heartbeat_utc")
                repo_root = existing.get("repo_root")
                
                same_repo = str(repo_root) == str(self.repo_root)
                
                heartbeat_stale = False
                if heartbeat_utc_str:
                    try:
                        hb_time = datetime.fromisoformat(heartbeat_utc_str.replace("Z", "+00:00"))
                        age = (datetime.now(timezone.utc) - hb_time).total_seconds()
                        if age > 60.0:
                            heartbeat_stale = True
                    except Exception:
                        heartbeat_stale = True
                else:
                    heartbeat_stale = True
                
                pid_alive = self.process_checker(existing_pid)
                cmdline_valid = True
                if pid_alive:
                    cmdline = _get_process_cmdline(existing_pid)
                    if cmdline:
                        is_python = "python" in cmdline.lower() or "py" in cmdline.lower()
                        is_main = "main.py" in cmdline.lower()
                        is_same_dir = str(self.repo_root).lower() in cmdline.lower() or "polymarket-adaptive-quant-engine" in cmdline.lower()
                        if not (is_python and is_main and is_same_dir):
                            cmdline_valid = False
                    else:
                        cmdline_valid = False
                
                should_recover = False
                if not same_repo:
                    pass
                elif not pid_alive:
                    should_recover = True
                    recovery_reason = "dead_pid"
                elif not cmdline_valid:
                    should_recover = True
                    recovery_reason = "pid_reused_or_non_runtime"
                elif heartbeat_stale and status == "active":
                    should_recover = True
                    recovery_reason = "stale_heartbeat"
                elif status == "stopping":
                    if not pid_alive:
                        should_recover = True
                        recovery_reason = "stopping_process_dead"
                    else:
                        # Wait up to 5s grace period
                        for _ in range(5):
                            time.sleep(1.0)
                            if not self.process_checker(existing_pid):
                                pid_alive = False
                                break
                        
                        if not pid_alive:
                            should_recover = True
                            recovery_reason = "stopping_process_exited"
                        else:
                            if heartbeat_stale or not cmdline_valid:
                                should_recover = True
                                recovery_reason = "stopping_process_hung_stale_heartbeat"
                
                if should_recover:
                    if self.telemetry_emit:
                        try:
                            self.telemetry_emit("log_system_health", {
                                "event_type": "stale_owner_detected",
                                "existing_pid": existing_pid,
                                "existing_run_id": existing.get("run_id"),
                                "recovery_reason": recovery_reason,
                            })
                        except Exception:
                            pass
                    
                    self._archive_stale_owner(normalized_mode)
                    try:
                        self.owner_path(normalized_mode).unlink(missing_ok=True)
                    except OSError:
                        pass
                    
                    previous_owner = existing
                    recovered = True
                    
                    if self.telemetry_emit:
                        try:
                            self.telemetry_emit("log_system_health", {
                                "event_type": "stale_owner_recovered",
                                "existing_pid": existing_pid,
                                "existing_run_id": existing.get("run_id"),
                                "recovery_reason": recovery_reason,
                            })
                        except Exception:
                            pass
                else:
                    same_owner = existing_pid == self.pid and str(existing.get("run_id") or "") == self.run_id
                    if same_owner:
                        previous_owner = existing
                    elif pid_alive:
                        if not override:
                            raise DuplicateRuntimeError(
                                "Active paper paper runtime owner already exists." if normalized_mode == "paper" else f"Active {normalized_mode} runtime owner already exists.",
                                reason="active_owner",
                                existing_owner=existing,
                            )
                        previous_owner = existing

            payload = self._owner_payload(
                mode=normalized_mode,
                override=override,
                heartbeat_count=0,
                status="active",
                previous_owner=previous_owner,
                stale_owner_recovered=recovered,
            )
            _atomic_json_replace(self.owner_path(normalized_mode), payload)
            return RuntimeOwner(manager=self, pid=self.pid, run_id=self.run_id, mode=normalized_mode)
        finally:
            if lock_fd is not None:
                try:
                    os.close(lock_fd)
                except OSError:
                    pass
            try:
                lock_path.unlink()
            except OSError:
                pass

    def heartbeat(self, *, pid: int, run_id: str, mode: str = "paper") -> bool:
        normalized_mode = str(mode or "paper").lower()
        existing = self._read_owner(normalized_mode)
        if not self._is_matching_owner(existing, pid=pid, run_id=run_id):
            return False
        heartbeat_count = self._int_or_zero(existing.get("heartbeat_count")) + 1
        payload = dict(existing)
        payload.update(
            {
                "heartbeat_count": heartbeat_count,
                "heartbeat_utc": _utc_now(),
                "status": "active",
            }
        )
        _atomic_json_replace(self.owner_path(normalized_mode), payload)
        return True

    def mark_stopping(self, *, pid: int, run_id: str, mode: str = "paper") -> bool:
        normalized_mode = str(mode or "paper").lower()
        existing = self._read_owner(normalized_mode)
        if not self._is_matching_owner(existing, pid=pid, run_id=run_id):
            return False
        payload = dict(existing)
        payload.update({"status": "stopping", "stopping_utc": _utc_now()})
        _atomic_json_replace(self.owner_path(normalized_mode), payload)
        return True

    def release(self, *, pid: int, run_id: str, mode: str = "paper") -> bool:
        normalized_mode = str(mode or "paper").lower()
        existing = self._read_owner(normalized_mode)
        if not self._is_matching_owner(existing, pid=pid, run_id=run_id):
            return False
        try:
            self.owner_path(normalized_mode).unlink()
            return True
        except FileNotFoundError:
            return True
        except OSError:
            return False

    def _read_owner(self, mode: str) -> dict[str, Any] | None:
        path = self.owner_path(mode)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
            return {"_unreadable": True, "reason": "owner_payload_not_object"}
        except Exception as exc:
            return {"_unreadable": True, "reason": type(exc).__name__}

    def _owner_payload(
        self,
        *,
        mode: str,
        override: bool,
        heartbeat_count: int,
        status: str,
        previous_owner: dict[str, Any] | None,
        stale_owner_recovered: bool,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "owner_schema_version": OWNER_SCHEMA_VERSION,
            "mode": mode,
            "pid": self.pid,
            "run_id": self.run_id,
            "repo_root": self.repo_root,
            "status": status,
            "override": bool(override),
            "started_utc": _utc_now(),
            "heartbeat_utc": _utc_now(),
            "heartbeat_count": int(heartbeat_count),
            "stale_owner_recovered": bool(stale_owner_recovered),
            "runtime_behavior_changed": "ownership_guard_only",
            "strategy_risk_execution_changed": False,
            "replay_lineage_semantics_changed": False,
        }
        if previous_owner is not None:
            payload["previous_owner"] = previous_owner
        if override:
            payload["contamination_risk"] = "operator_override_duplicate_allowed"
        return payload

    @staticmethod
    def _int_or_zero(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _is_matching_owner(existing: dict[str, Any] | None, *, pid: int, run_id: str) -> bool:
        if not existing or existing.get("_unreadable"):
            return False
        return int(existing.get("pid") or 0) == int(pid) and str(existing.get("run_id") or "") == str(run_id)
