"""Runtime Event Stream V1 — append-only, file-backed, async event emitter.

Decouples the trading loop from disk I/O via a bounded deque and background writer.
Failures never propagate to the trading thread.
"""
from __future__ import annotations

import atexit
import collections
import json
import logging
import os
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

LOGGER = logging.getLogger(__name__)

ENGINE_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0.0"
EVENT_VERSION_DEFAULT = "1.0.0"

# Lower numeric rank = higher priority
PRIORITY_RANK: dict[str, int] = {"CRITICAL": 0, "HIGH": 1, "NORMAL": 2, "LOW": 3}

# Low-priority drop threshold: drop LOW when remaining capacity < 15% of maxsize
_LOW_DROP_THRESHOLD = 0.15


def _resolve_git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2.0,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


class RuntimeEventStream:
    """Append-only, file-backed, asynchronous Runtime Event Stream V1.

    Thread-safe.  emit() is non-blocking on the trading hot path.
    The writer thread drains the bounded deque to disk with exponential-backoff
    retry on I/O failure.  The heartbeat thread fires every 5 s.
    """

    def __init__(
        self,
        *,
        session_id: str | None = None,
        mode: str = "paper",
        output_dir: str | Path = "runtime/event_stream",
        max_file_size_bytes: int = 256 * 1024 * 1024,
        queue_maxsize: int = 1000,
        heartbeat_interval_seconds: float = 5.0,
        now: Callable[[], datetime] | None = None,
        _start_writer: bool = True,
    ) -> None:
        self._mode = mode
        self._output_dir = Path(output_dir)
        self._max_file_size_bytes = max_file_size_bytes
        self._maxsize = queue_maxsize
        self._heartbeat_interval = heartbeat_interval_seconds
        self._now = now or (lambda: datetime.now(timezone.utc))

        if session_id:
            self._session_id = session_id
        else:
            ts = self._now().strftime("%Y%m%dT%H%M%SZ")
            self._session_id = f"{ts}_{os.getpid()}_{uuid.uuid4().hex[:8]}"

        self._git_commit = _resolve_git_commit()
        self._start_monotonic = time.monotonic()
        self._last_flush_monotonic: float = 0.0
        self._events_written: int = 0

        # Queue: deque protected by a Condition (also guards session_sequence)
        self._cond = threading.Condition(threading.Lock())
        self._queue: collections.deque[dict] = collections.deque()
        self._session_sequence: int = 0

        # Active file state (protected by _file_lock)
        self._file_lock = threading.Lock()
        self._active_file_path: Path | None = None
        self._active_date: str = ""
        self._active_idx: int = 0

        # Metrics cache (protected by _metrics_lock)
        self._metrics_lock = threading.Lock()
        self._metrics_cache: dict[str, Any] = {}

        self._shutdown_event = threading.Event()

        if _start_writer:
            self._writer_thread = threading.Thread(
                target=self._writer_worker,
                name="event-stream-writer",
                daemon=True,
            )
            self._writer_thread.start()

            self._heartbeat_thread = threading.Thread(
                target=self._heartbeat_worker,
                name="event-stream-heartbeat",
                daemon=True,
            )
            self._heartbeat_thread.start()

            atexit.register(self.shutdown)

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def emit(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        priority: str = "NORMAL",
        event_version: str = EVENT_VERSION_DEFAULT,
    ) -> bool:
        """Non-blocking enqueue.  Returns True if accepted, False if dropped."""
        if self._shutdown_event.is_set():
            return False
        try:
            return self._enqueue_with_policy(event_type, payload or {}, priority, event_version)
        except Exception:
            LOGGER.warning(
                "[EventStream] emit() failed silently for %s", event_type, exc_info=True
            )
            return False

    def update_metrics_cache(self, metrics: dict[str, Any]) -> None:
        """Thread-safe metrics update from the trading cycle."""
        try:
            with self._metrics_lock:
                self._metrics_cache.update(metrics)
        except Exception:
            LOGGER.warning("[EventStream] metrics cache update failed", exc_info=True)

    def shutdown(self, timeout: float = 30.0) -> None:
        """Signal shutdown, drain the queue, then stop threads."""
        self._shutdown_event.set()
        with self._cond:
            self._cond.notify_all()
        if hasattr(self, "_writer_thread") and self._writer_thread.is_alive():
            self._writer_thread.join(timeout=timeout)
        if hasattr(self, "_heartbeat_thread") and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=2.0)

    @property
    def queue_depth(self) -> int:
        with self._cond:
            return len(self._queue)

    @property
    def session_sequence(self) -> int:
        with self._cond:
            return self._session_sequence

    # ──────────────────────────────────────────────────────────────────────────
    # Queue management (internal — all critical sections hold self._cond)
    # ──────────────────────────────────────────────────────────────────────────

    def _next_seq_under_lock(self) -> int:
        """Increment session_sequence.  Must be called while self._cond is held."""
        self._session_sequence += 1
        return self._session_sequence

    def _enqueue_with_policy(
        self,
        event_type: str,
        payload: dict,
        priority: str,
        event_version: str,
    ) -> bool:
        rank = PRIORITY_RANK.get(priority, 2)

        with self._cond:
            size = len(self._queue)
            capacity = self._maxsize

            # LOW: drop immediately when remaining capacity < 15%
            if rank == 3:
                remaining = capacity - size
                if remaining < capacity * _LOW_DROP_THRESHOLD:
                    seq = self._next_seq_under_lock()
                    overflow = self._make_overflow_envelope(event_type, priority, size, seq)
                    if remaining > 0:
                        self._queue.append(overflow)
                        self._cond.notify()
                    return False

            # Normal path: room in queue
            if size < capacity:
                seq = self._next_seq_under_lock()
                envelope = self._build_envelope(event_type, payload, priority, event_version, seq)
                self._queue.append(envelope)
                self._cond.notify()
                return True

            # Queue is full — evict or drop based on priority
            if rank == 0:  # CRITICAL: evict any lower priority
                evicted = self._evict_first_with_rank_above(0)
            elif rank == 1:  # HIGH: evict NORMAL or LOW
                evicted = self._evict_first_with_rank_above(1)
            elif rank == 2:  # NORMAL: evict LOW only
                evicted = self._evict_first_with_rank_above(2)
            else:
                evicted = None  # LOW already handled above

            if evicted is not None:
                # Evicted one slot; emit overflow for the displaced event
                seq = self._next_seq_under_lock()
                overflow = self._make_overflow_envelope(
                    evicted["event_type"], evicted.get("priority", "NORMAL"), size, seq
                )
                self._queue.append(overflow)  # may transiently exceed maxsize by 1
                seq = self._next_seq_under_lock()
                envelope = self._build_envelope(event_type, payload, priority, event_version, seq)
                self._queue.append(envelope)
                self._cond.notify()
                return True

            if rank == 0:
                # CRITICAL with no lower-priority event to evict: allow transient overcapacity
                seq = self._next_seq_under_lock()
                envelope = self._build_envelope(event_type, payload, priority, event_version, seq)
                self._queue.append(envelope)
                self._cond.notify()
                return True

            # HIGH or NORMAL with nothing to evict: drop incoming
            seq = self._next_seq_under_lock()
            overflow = self._make_overflow_envelope(event_type, priority, size, seq)
            self._queue.append(overflow)  # transient +1, writer drains quickly
            self._cond.notify()
            return False

    def _evict_first_with_rank_above(self, min_rank: int) -> dict | None:
        """Remove and return the oldest (leftmost) event whose priority rank > min_rank.

        Must be called while self._cond is held.
        """
        for i, evt in enumerate(self._queue):
            evt_rank = PRIORITY_RANK.get(evt.get("priority", "NORMAL"), 2)
            if evt_rank > min_rank:
                del self._queue[i]
                return evt
        return None

    def _build_envelope(
        self,
        event_type: str,
        payload: dict,
        priority: str,
        event_version: str,
        seq: int,
    ) -> dict:
        return {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "event_version": event_version,
            "schema_version": SCHEMA_VERSION,
            "runtime_session_id": self._session_id,
            "session_sequence": seq,
            "timestamp_utc": self._utc_timestamp(),
            "priority": priority,
            "engine_version": ENGINE_VERSION,
            "git_commit": self._git_commit,
            "runtime_environment": self._mode,
            "payload": payload,
        }

    def _make_overflow_envelope(
        self,
        dropped_type: str,
        dropped_priority: str,
        queue_depth: int,
        seq: int,
    ) -> dict:
        return self._build_envelope(
            "event_stream_queue_overflow_v1",
            {
                "dropped_event_type": dropped_type,
                "dropped_event_priority": dropped_priority,
                "current_queue_depth": queue_depth,
            },
            "HIGH",
            EVENT_VERSION_DEFAULT,
            seq,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Background writer thread
    # ──────────────────────────────────────────────────────────────────────────

    def _writer_worker(self) -> None:
        while True:
            with self._cond:
                while not self._queue:
                    if self._shutdown_event.is_set():
                        return  # Empty queue + shutdown → exit cleanly
                    self._cond.wait(timeout=1.0)
                event = self._queue.popleft()
            self._write_to_file(event)

    def _write_to_file(self, event: dict) -> None:
        line = json.dumps(event, sort_keys=True, default=str) + "\n"
        backoff = 1.0
        while True:
            try:
                with self._file_lock:
                    path = self._get_active_file()
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with open(path, "a", encoding="utf-8", newline="") as fh:
                        fh.write(line)
                        fh.flush()
                    self._last_flush_monotonic = time.monotonic()
                    self._events_written += 1
                return
            except OSError as exc:
                LOGGER.warning(
                    "[EventStream] Write failed (backoff=%.1fs): %s", backoff, exc
                )
                if self._shutdown_event.wait(timeout=backoff):
                    return  # Interrupted by shutdown — abandon this event
                backoff = min(backoff * 2, 60.0)

    def _get_active_file(self) -> Path:
        """Return (and rotate if needed) the active JSONL file.  Must hold _file_lock."""
        now = self._now()
        date_str = now.strftime("%Y-%m-%d")

        if self._active_file_path is None:
            self._active_date = date_str
            self._active_idx = 1
            self._active_file_path = (
                self._output_dir / f"runtime_events_{date_str}_{self._active_idx:03d}.jsonl"
            )
            return self._active_file_path

        rotate = False
        if date_str != self._active_date:
            rotate = True
        elif (
            self._active_file_path.exists()
            and self._active_file_path.stat().st_size >= self._max_file_size_bytes
        ):
            rotate = True

        if rotate:
            if date_str != self._active_date:
                self._active_date = date_str
                self._active_idx = 1
            else:
                self._active_idx += 1
            self._active_file_path = (
                self._output_dir
                / f"runtime_events_{self._active_date}_{self._active_idx:03d}.jsonl"
            )

        return self._active_file_path

    # ──────────────────────────────────────────────────────────────────────────
    # Background heartbeat thread
    # ──────────────────────────────────────────────────────────────────────────

    def _heartbeat_worker(self) -> None:
        while not self._shutdown_event.wait(timeout=self._heartbeat_interval):
            try:
                payload = self._build_heartbeat_payload()
                self._enqueue_with_policy(
                    "runtime_heartbeat_v1", payload, "CRITICAL", EVENT_VERSION_DEFAULT
                )
            except Exception:
                LOGGER.warning("[EventStream] Heartbeat emission failed", exc_info=True)

    def _build_heartbeat_payload(self) -> dict:
        with self._metrics_lock:
            metrics = dict(self._metrics_cache)

        uptime = time.monotonic() - self._start_monotonic

        memory_mb: float | None = None
        cpu_percent: float | None = None
        try:
            import psutil  # optional — graceful fallback if absent

            proc = psutil.Process()
            memory_mb = round(proc.memory_info().rss / (1024 * 1024), 2)
            cpu_percent = round(proc.cpu_percent(interval=None), 2)
        except Exception:
            pass

        with self._cond:
            queue_depth = len(self._queue)

        file_size = 0
        with self._file_lock:
            if self._active_file_path and self._active_file_path.exists():
                try:
                    file_size = self._active_file_path.stat().st_size
                except OSError:
                    pass

        last_flush_age_ms = 0
        if self._last_flush_monotonic > 0:
            last_flush_age_ms = int((time.monotonic() - self._last_flush_monotonic) * 1000)

        elapsed = time.monotonic() - self._start_monotonic
        events_per_second = round(self._events_written / elapsed, 3) if elapsed > 0 else 0.0

        return {
            "runtime_alive": True,
            "uptime_seconds": round(uptime, 2),
            "paper_balance": metrics.get("paper_balance"),
            "active_positions": metrics.get("active_positions"),
            "current_bankroll_tier": metrics.get("current_bankroll_tier"),
            "risk_mode": metrics.get("risk_mode"),
            "candidate_count": metrics.get("candidate_count"),
            "events_per_second": events_per_second,
            "memory_mb": memory_mb,
            "cpu_percent": cpu_percent,
            "runtime_state": metrics.get("runtime_state", "running"),
            "loop_latency_ms": metrics.get("loop_latency_ms"),
            "decision_latency_ms": metrics.get("decision_latency_ms"),
            "queue_depth": queue_depth,
            "writer_backlog": queue_depth,
            "event_stream_file_size": file_size,
            "last_flush_age_ms": last_flush_age_ms,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _utc_timestamp(self) -> str:
        now = self._now()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
