from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


LOGGER = logging.getLogger(__name__)


class QuantEventLogger:
    """Fail-soft JSONL writer for quant observability events."""

    _CATEGORY_BY_METHOD = {
        "market_snapshot": "market_snapshots",
        "decision": "decision_log",
        "execution": "execution_log",
        "trade_open": "trade_journal",
        "trade_close": "trade_journal",
        "risk_event": "risk_log",
        "system_health": "system_health",
    }

    def __init__(
        self,
        *,
        base_dir: str | Path | None = None,
        enabled: bool | None = None,
        mode: str = "paper",
        run_id: str | None = None,
        source_module: str = "utils.quant_event_logger",
        schema_version: str | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        settings = None
        try:
            from config.settings import get_settings

            settings = get_settings()
        except Exception:
            settings = None

        self.enabled = bool(getattr(settings, "quant_data_enabled", True) if enabled is None else enabled)
        self.base_dir = Path(base_dir or getattr(settings, "quant_data_dir", "runtime/quant_data"))
        self.mode = mode
        self.run_id = run_id or f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}_{os.getpid()}_{uuid.uuid4().hex[:8]}"
        self.source_module = source_module
        self.schema_version = schema_version or getattr(settings, "quant_event_schema_version", "1.0")
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._disabled_categories: set[str] = set()

    @property
    def disabled_categories(self) -> set[str]:
        return set(self._disabled_categories)

    def log_market_snapshot(self, payload: dict[str, Any] | None = None) -> bool:
        return self._write_event("market_snapshot", payload)

    def log_decision(self, payload: dict[str, Any] | None = None) -> bool:
        return self._write_event("decision", payload)

    def log_execution(self, payload: dict[str, Any] | None = None) -> bool:
        return self._write_event("execution", payload)

    def log_trade_open(self, payload: dict[str, Any] | None = None) -> bool:
        return self._write_event("trade_open", payload)

    def log_trade_close(self, payload: dict[str, Any] | None = None) -> bool:
        return self._write_event("trade_close", payload)

    def log_risk_event(self, payload: dict[str, Any] | None = None) -> bool:
        return self._write_event("risk_event", payload)

    def log_system_health(self, payload: dict[str, Any] | None = None) -> bool:
        return self._write_event("system_health", payload)

    def _write_event(self, event_type: str, payload: dict[str, Any] | None) -> bool:
        category = self._CATEGORY_BY_METHOD[event_type]
        if not self.enabled or category in self._disabled_categories:
            return False

        timestamp = self._timestamp()
        event = {
            "timestamp_utc": timestamp,
            "event_type": event_type,
            "mode": self.mode,
            "run_id": self.run_id,
            "source_module": str((payload or {}).get("source_module", self.source_module)),
            "schema_version": self.schema_version,
            "payload": payload or {},
        }
        path = self.base_dir / category / f"{timestamp[:10]}.jsonl"
        return self._append_jsonl(category, path, event)

    def _timestamp(self) -> str:
        now = self._now()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    def _append_jsonl(self, category: str, path: Path, event: dict[str, Any]) -> bool:
        handle = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            handle = open(path, "a", encoding="utf-8", newline="")
            handle.write(json.dumps(event, sort_keys=True, default=str) + "\n")
            handle.flush()
            return True
        except PermissionError as exc:
            self._disable_category(category, path, exc)
            return False
        except OSError as exc:
            if getattr(exc, "errno", None) == 13:
                self._disable_category(category, path, exc)
                return False
            raise
        finally:
            if handle is not None:
                try:
                    handle.close()
                except PermissionError as exc:
                    self._disable_category(category, path, exc)
                except OSError as exc:
                    if getattr(exc, "errno", None) == 13:
                        self._disable_category(category, path, exc)
                    else:
                        raise

    def _disable_category(self, category: str, path: Path, exc: BaseException) -> None:
        if category in self._disabled_categories:
            return
        self._disabled_categories.add(category)
        LOGGER.warning(
            "quant event writer disabled for %s after PermissionError/OSError on %s: %s",
            category,
            path,
            exc,
        )
