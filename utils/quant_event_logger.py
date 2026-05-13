from __future__ import annotations

import json
import logging
import os
import uuid
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


LOGGER = logging.getLogger(__name__)


TRACE_IDENTITY_FIELDS = (
    "market_key",
    "market_slug",
    "condition_id",
    "token_id",
    "side",
    "lifecycle_phase",
)
TRACE_FIELD_ALIASES = {
    "condition_id": ("condition_id", "conditionId"),
    "token_id": ("token_id", "tokenId", "clob_token_id", "clobTokenId", "yes_token_id", "no_token_id"),
    "side": ("side", "asset_side", "outcome", "best_side", "token_side"),
    "market_key": ("market_key", "marketKey", "market_id", "source_market_id"),
    "market_slug": ("market_slug", "marketSlug", "slug"),
}
TRACE_ID_SOURCE_FIELDS = (
    "market_key",
    "marketKey",
    "market_id",
    "source_market_id",
    "market_slug",
    "marketSlug",
    "slug",
    "condition_id",
    "conditionId",
    "token_id",
    "tokenId",
    "clob_token_id",
    "clobTokenId",
    "yes_token_id",
    "no_token_id",
)
TRACE_TIME_FIELDS = (
    "candidate_seen_ts",
    "market_epoch_start",
    "epoch_start",
    "epoch_start_ts",
    "market_epoch_start_ts",
    "event_start_ts",
    "timestamp_utc",
)


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
        enriched_payload = self._with_candidate_trace_identity(payload or {}, timestamp)
        event = {
            "timestamp_utc": timestamp,
            "event_type": event_type,
            "mode": self.mode,
            "run_id": self.run_id,
            "source_module": str(enriched_payload.get("source_module", self.source_module)),
            "schema_version": self.schema_version,
            "payload": enriched_payload,
        }
        path = self.base_dir / category / f"{timestamp[:10]}.jsonl"
        return self._append_jsonl(category, path, event)

    def _with_candidate_trace_identity(self, payload: dict[str, Any], timestamp_utc: str) -> dict[str, Any]:
        enriched = dict(payload)
        for key, value in self._normalized_identity_companion_fields(enriched).items():
            if value and not enriched.get(key):
                enriched[key] = value
        identity = self._candidate_trace_identity_fields(enriched, timestamp_utc)
        for key, value in identity.items():
            if value and not enriched.get(key):
                enriched[key] = value
        return enriched

    @classmethod
    def _candidate_trace_identity_fields(cls, payload: dict[str, Any], timestamp_utc: str = "") -> dict[str, str]:
        market_key = cls._first_text(
            payload,
            TRACE_FIELD_ALIASES["market_key"] + TRACE_FIELD_ALIASES["market_slug"] + TRACE_FIELD_ALIASES["condition_id"],
        )
        market_slug = cls._first_text(payload, TRACE_FIELD_ALIASES["market_slug"])
        condition_id = cls._first_text(payload, TRACE_FIELD_ALIASES["condition_id"])
        token_id = cls._first_text(payload, TRACE_FIELD_ALIASES["token_id"])
        side = cls._first_text(payload, TRACE_FIELD_ALIASES["side"])
        lifecycle_phase = cls._first_text(payload, ("lifecycle_phase",))
        time_bucket = cls._trace_time_bucket(payload, timestamp_utc)

        has_identity_source = any(cls._first_text(payload, (field,)) for field in TRACE_ID_SOURCE_FIELDS)
        if not has_identity_source:
            return {}

        trace_parts = {
            "market_key": market_key,
            "market_slug": market_slug,
            "condition_id": condition_id,
            "token_id": token_id,
            "side": side,
            "lifecycle_phase": lifecycle_phase,
            "time_bucket": time_bucket,
        }
        digest_input = "|".join(f"{key}={str(value).strip().lower()}" for key, value in sorted(trace_parts.items()) if value)
        if not digest_input:
            return {}

        digest = hashlib.sha1(digest_input.encode("utf-8")).hexdigest()[:16]
        identity: dict[str, str] = {
            "candidate_trace_id": f"ct_{digest}",
            "trace_link_reason": "passive_deterministic_existing_fields",
        }
        parent = cls._first_text(payload, ("parent_candidate_trace_id", "candidate_id", "signal_id"))
        if parent:
            identity["parent_candidate_trace_id"] = parent
        for key, value in (
            ("market_key", market_key),
            ("market_slug", market_slug),
            ("condition_id", condition_id),
            ("token_id", token_id),
            ("side", side),
            ("lifecycle_phase", lifecycle_phase),
        ):
            if value:
                identity[key] = value
        return identity

    @classmethod
    def _normalized_identity_companion_fields(cls, payload: dict[str, Any]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for canonical, aliases in TRACE_FIELD_ALIASES.items():
            value = cls._first_text(payload, aliases)
            if value:
                normalized[canonical] = value
        return normalized

    @staticmethod
    def _first_text(payload: dict[str, Any], keys: tuple[str, ...]) -> str:
        for key in keys:
            value = payload.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return ""

    @classmethod
    def _trace_time_bucket(cls, payload: dict[str, Any], timestamp_utc: str) -> str:
        raw = cls._first_text(payload, TRACE_TIME_FIELDS) or timestamp_utc
        if not raw:
            return ""
        try:
            numeric = int(float(raw))
            return str(numeric - (numeric % 300))
        except (TypeError, ValueError):
            pass
        return raw[:16]

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
