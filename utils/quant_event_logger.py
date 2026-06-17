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
        "trade_path_checkpoint": "path_truth",
        "orderbook_lineage_probe": "orderbook_lineage",
        "risk_event": "risk_log",
        "system_health": "system_health",
        "research_snapshot": "research_log",
        "stop_loss_shadow": "stop_loss_shadow",
        "signal_filter_shadow": "signal_filter_shadow",
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
        self.research_enabled = bool(getattr(settings, "research_data_enabled", True))
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

    def log_trade_path_checkpoint(self, payload: dict[str, Any] | None = None) -> bool:
        return self._write_event("trade_path_checkpoint", payload)

    def log_orderbook_lineage_probe(self, payload: dict[str, Any] | None = None) -> bool:
        return self._write_event("orderbook_lineage_probe", payload)

    def log_risk_event(self, payload: dict[str, Any] | None = None) -> bool:
        return self._write_event("risk_event", payload)

    def log_system_health(self, payload: dict[str, Any] | None = None) -> bool:
        return self._write_event("system_health", payload)

    def log_research_snapshot(self, payload: dict[str, Any] | None = None) -> bool:
        if not self.research_enabled:
            return False
        return self._write_event("research_snapshot", payload)

    def log_stop_loss_shadow(self, payload: dict[str, Any] | None = None) -> bool:
        return self._write_event("stop_loss_shadow", payload)

    def log_signal_filter_shadow(self, payload: dict[str, Any] | None = None) -> bool:
        return self._write_event("signal_filter_shadow", payload)

    def _write_event(self, event_type: str, payload: dict[str, Any] | None) -> bool:
        category = self._CATEGORY_BY_METHOD[event_type]
        if not self.enabled or category in self._disabled_categories:
            return False

        timestamp = self._timestamp()
        enriched_payload = self._with_candidate_trace_identity(payload or {}, timestamp, event_type=event_type)
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

    def _with_candidate_trace_identity(
        self,
        payload: dict[str, Any],
        timestamp_utc: str,
        *,
        event_type: str | None = None,
    ) -> dict[str, Any]:
        enriched = dict(payload)
        for key, value in self._normalized_identity_companion_fields(enriched).items():
            if value and not enriched.get(key):
                enriched[key] = value
        identity = self._candidate_trace_identity_fields(enriched, timestamp_utc)
        for key, value in identity.items():
            if value and not enriched.get(key):
                enriched[key] = value
        # --- Additive canonical lineage fields (observability-only, backward-compatible) ---
        enriched.setdefault("packet_schema_version", self.schema_version)
        candidate_trace_id = str(enriched.get("candidate_trace_id") or "")
        if candidate_trace_id:
            # replay_chain_id: stable per candidate+run, diagnosable across producers
            run_fragment = self.run_id[:8] if self.run_id else "norund"
            enriched.setdefault("replay_chain_id", f"rc_{run_fragment}_{candidate_trace_id[3:]}")
            # lifecycle_instance_id: groups events in the same market window
            market_key = str(enriched.get("market_key") or enriched.get("condition_id") or enriched.get("market_slug") or "")
            time_bucket = str(enriched.get("time_bucket") or self._trace_time_bucket(enriched, timestamp_utc))
            li_input = f"{market_key}|{time_bucket}"
            li_digest = hashlib.sha1(li_input.encode("utf-8")).hexdigest()[:12] if li_input.strip("|") else "nokey"
            enriched.setdefault("lifecycle_instance_id", f"li_{li_digest}")
            # inventory_context_id: ties execution/trade_journal events to a bounded context
            enriched.setdefault("inventory_context_id", f"inv_{run_fragment}_{li_digest}")
            # producer-specific trace IDs — only emitted at the relevant producer stage
            producer_stage = self._lineage_propagation_stage(enriched)
            if not enriched.get("identity_propagation_stage") or str(enriched.get("identity_propagation_stage")).lower() == "unknown":
                enriched["identity_propagation_stage"] = producer_stage
            if producer_stage == "risk":
                enriched.setdefault("risk_trace_id", f"rt_{candidate_trace_id[3:]}")
            elif producer_stage == "execution":
                enriched.setdefault("execution_trace_id", f"et_{candidate_trace_id[3:]}")
            # identity_source and lineage_confidence
            enriched.setdefault("identity_source", str(enriched.get("trace_link_reason") or "passive_deterministic_existing_fields"))
            enriched.setdefault("lineage_confidence", self._lineage_confidence(enriched))
            enriched.setdefault("lineage_drop_reason", "none")
        else:
            # Identity not derivable — emit explicit missing reasons
            has_identity_source = any(self._first_text(enriched, (field,)) for field in TRACE_ID_SOURCE_FIELDS)
            if not has_identity_source:
                missing_reason = "no_identity_source_fields"
            else:
                missing_reason = "empty_digest_input_after_alias_resolution"
            enriched.setdefault("candidate_trace_id_missing_reason", missing_reason)
            enriched.setdefault("replay_chain_id_missing_reason", "candidate_trace_id_not_derivable")
            producer_stage = self._lineage_propagation_stage(enriched)
            if not enriched.get("identity_propagation_stage") or str(enriched.get("identity_propagation_stage")).lower() == "unknown":
                enriched["identity_propagation_stage"] = producer_stage
            if producer_stage == "risk":
                enriched.setdefault("risk_trace_id_missing_reason", missing_reason)
            elif producer_stage == "execution":
                enriched.setdefault("execution_trace_id_missing_reason", missing_reason)
            enriched.setdefault("lineage_drop_reason", missing_reason)
            enriched.setdefault("lineage_confidence", "UNKNOWN")
            enriched.setdefault("identity_source", "not_derivable")
        # paper_trade_replay_key: stable cross-producer join key independent of trace ID generation
        if not enriched.get("paper_trade_replay_key"):
            replay_key = self._compute_paper_trade_replay_key(enriched)
            if replay_key:
                enriched["paper_trade_replay_key"] = replay_key
        # market_observation_key: coarse MS/DL market-window bridge only.
        # Not candidate identity, trade identity, replay grouping, or policy input.
        if event_type in {"market_snapshot", "decision"} and not enriched.get("market_observation_key"):
            observation_key, observation_source = self._compute_market_observation_key(enriched)
            if observation_key:
                enriched["market_observation_key"] = observation_key
                enriched.setdefault("market_observation_key_source", observation_source)
            else:
                enriched.setdefault("market_observation_key_missing_reason", observation_source)
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
        parent = cls._first_text(payload, ("parent_candidate_trace_id", "candidate_id", "signal_id", "decision_id"))
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
        # candidate_seen_ts: forward-compatible replay envelope field
        for ts_key in TRACE_TIME_FIELDS:
            ts_val = cls._first_text(payload, (ts_key,))
            if ts_val and "candidate_seen_ts" not in identity:
                identity["candidate_seen_ts"] = ts_val
                break
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

    @classmethod
    def _lineage_propagation_stage(cls, payload: dict[str, Any]) -> str:
        """Derive the producer lifecycle stage from serialized producer labels."""
        producer = str(
            payload.get("producer_event_type")
            or payload.get("producer")
            or ""
        ).strip().lower()
        if producer in {"risk_log", "risk_event", "risk"}:
            return "risk"
        if producer in {"execution_log", "execution", "trade_open", "trade_close", "trade_journal"}:
            return "execution"
        if producer in {"decision_log", "decision"}:
            return "decision"
        if producer in {"market_snapshots", "market_snapshot"}:
            return "pre_decision"
        if producer in {"system_health"}:
            return "system"
        return "unknown"

    @classmethod
    def _lineage_confidence(cls, payload: dict[str, Any]) -> str:
        """Classify lineage confidence from available canonical fields."""
        has_trace = bool(str(payload.get("candidate_trace_id") or "").strip())
        has_parent = bool(str(payload.get("parent_candidate_trace_id") or "").strip())
        has_market = bool(
            str(payload.get("market_key") or payload.get("condition_id") or payload.get("market_slug") or "").strip()
        )
        has_token = bool(str(payload.get("token_id") or "").strip())
        has_side = bool(str(payload.get("side") or "").strip())
        has_phase = bool(str(payload.get("lifecycle_phase") or "").strip())
        if has_trace and has_parent and has_market and has_token and has_side and has_phase:
            return "DIRECT"
        if has_trace and has_market and has_token and has_side and has_phase:
            return "STRONG"
        if has_trace and has_market:
            return "WEAK"
        if has_trace:
            return "PROXY"
        return "UNKNOWN"

    @classmethod
    def _compute_paper_trade_replay_key(cls, payload: dict[str, Any]) -> str:
        """Deterministic cross-producer join key: condition_id|epoch_start_ts|asset|side|token_id."""
        condition_id = cls._first_text(payload, ("condition_id", "conditionId"))
        epoch_start_ts = cls._first_text(
            payload,
            ("epoch_start_ts", "epoch_start", "market_epoch_start_ts", "market_epoch_start", "event_start_ts"),
        )
        asset = cls._first_text(payload, ("asset", "ticker"))
        side = cls._first_text(payload, TRACE_FIELD_ALIASES["side"])
        token_id = cls._first_text(payload, TRACE_FIELD_ALIASES["token_id"])
        if condition_id and epoch_start_ts and side and token_id:
            return f"{condition_id}|{epoch_start_ts}|{asset or ''}|{side}|{token_id}"
        return ""

    @classmethod
    def _compute_market_observation_key(cls, payload: dict[str, Any]) -> tuple[str, str]:
        """Coarse market-window bridge: condition_id|alias-resolved epoch.

        Evidence-only. Do not use for candidate identity, trade attribution,
        replay grouping, risk sizing, or runtime decisions.
        """
        condition_id = cls._first_text(payload, ("condition_id", "conditionId"))
        epoch_start = cls._first_text(
            payload,
            ("epoch_start_ts", "epoch_start", "market_epoch_start_ts", "market_epoch_start", "event_start_ts"),
        )
        if condition_id and epoch_start:
            return f"{condition_id}|{epoch_start}", "resolved"
        if not condition_id:
            return "", "condition_id_absent"
        return "", "epoch_unresolvable"

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
