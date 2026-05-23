from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class AlertResult:
    sent: bool
    suppressed: bool = False
    reason: str = ""


class TelegramAlertLayer:
    """Cooldown and fail-soft wrapper around the project Telegram notifier."""

    def __init__(
        self,
        notifier: Any | None = None,
        *,
        cooldown_seconds: int | None = None,
        summary_interval_minutes: int | None = None,
        now: Callable[[], float] | None = None,
        telemetry_emit: Callable[[dict[str, Any]], Any] | None = None,
        run_id: str | None = None,
    ) -> None:
        if cooldown_seconds is None or summary_interval_minutes is None:
            try:
                from config.settings import get_settings

                settings = get_settings()
                if cooldown_seconds is None:
                    cooldown_seconds = int(getattr(settings, "telegram_alert_cooldown_seconds", 300))
                if summary_interval_minutes is None:
                    summary_interval_minutes = int(getattr(settings, "telegram_summary_interval_minutes", 60))
            except Exception:
                cooldown_seconds = 300 if cooldown_seconds is None else cooldown_seconds
                summary_interval_minutes = 60 if summary_interval_minutes is None else summary_interval_minutes

        self.notifier = notifier
        self.cooldown_seconds = int(cooldown_seconds)
        self.summary_interval_seconds = int(summary_interval_minutes) * 60
        self._now = now or time.monotonic
        self._last_sent: dict[str, float] = {}
        self._telemetry_emit = telemetry_emit
        self.run_id = run_id

    def notify_startup(self, message: str = "", **context: Any) -> AlertResult:
        return self._send("startup", self._format_message("STARTUP", message, context), context)

    def notify_entry(self, message: str = "", **context: Any) -> AlertResult:
        return self._send("entry", self._format_message("ENTRY", message, context), context)

    def notify_exit(self, message: str = "", **context: Any) -> AlertResult:
        return self._send("exit", self._format_message("EXIT", message, context), context)

    def notify_risk(self, message: str = "", **context: Any) -> AlertResult:
        key = self._dedup_key("risk", message, context)
        return self._send_with_cooldown("risk", key, self._format_message("RISK", message, context), context, self.cooldown_seconds)

    def notify_critical(self, message: str = "", **context: Any) -> AlertResult:
        key = self._dedup_key("critical", message, context)
        return self._send_with_cooldown("critical", key, self._format_message("CRITICAL", message, context), context, self.cooldown_seconds)

    def notify_summary(self, message: str = "", **context: Any) -> AlertResult:
        key = self._dedup_key("summary", message, context)
        return self._send_with_cooldown(
            "summary",
            key,
            self._format_message("SUMMARY", message, context),
            context,
            self.summary_interval_seconds,
        )

    def notify_incident(self, message: str = "", **context: Any) -> AlertResult:
        key = self._dedup_key("incident", message, context)
        return self._send_with_cooldown("incident", key, self._format_message("INCIDENT", message, context), context, self.cooldown_seconds)

    def _send_with_cooldown(
        self,
        route: str,
        key: str,
        message: str,
        context: dict[str, Any],
        cooldown_seconds: int,
    ) -> AlertResult:
        now = self._now()
        source_event_id = _safe_optional_text(context.get("source_event_id"))
        self._emit_telemetry(
            "telegram_route_attempt",
            route=route,
            source_event_id=source_event_id,
            cooldown_key=key,
        )
        last_sent = self._last_sent.get(key)
        if last_sent is not None and now - last_sent < cooldown_seconds:
            seconds_remaining = max(0, int(cooldown_seconds - (now - last_sent)))
            self._emit_telemetry(
                "telegram_suppressed_cooldown",
                route=route,
                source_event_id=source_event_id,
                cooldown_key=key,
                suppression_reason="cooldown",
                cooldown_seconds=int(cooldown_seconds),
                seconds_remaining=seconds_remaining,
            )
            return AlertResult(sent=False, suppressed=True, reason="cooldown")

        result = self._send(route, message, context, cooldown_key=key, emit_attempt=False)
        if result.sent:
            self._last_sent[key] = now
        return result

    def _send(
        self,
        route: str,
        message: str,
        context: dict[str, Any],
        *,
        cooldown_key: str | None = None,
        emit_attempt: bool = True,
    ) -> AlertResult:
        source_event_id = _safe_optional_text(context.get("source_event_id"))
        if emit_attempt:
            self._emit_telemetry(
                "telegram_route_attempt",
                route=route,
                source_event_id=source_event_id,
                cooldown_key=cooldown_key,
            )
        notifier = self.notifier or _get_project_notifier()
        if notifier is None:
            self._emit_telemetry(
                "telegram_send_failure",
                route=route,
                source_event_id=source_event_id,
                cooldown_key=cooldown_key,
                exception_class="NotifierUnavailable",
                failure_stage="submit",
            )
            return AlertResult(sent=False, reason="notifier_unavailable")
        try:
            try:
                notifier.send_message(
                    message,
                    route=route,
                    source_event_id=source_event_id,
                    cooldown_key=cooldown_key,
                    run_id=self.run_id,
                    telemetry_emit=self._emit_telemetry,
                )
            except TypeError:
                notifier.send_message(message)
            if not getattr(notifier, "supports_async_telegram_telemetry", False):
                self._emit_telemetry(
                    "telegram_send_success",
                    route=route,
                    source_event_id=source_event_id,
                    cooldown_key=cooldown_key,
                )
            return AlertResult(sent=True)
        except Exception as exc:
            LOGGER.warning("telegram alert send failed: %s", exc)
            self._emit_telemetry(
                "telegram_send_failure",
                route=route,
                source_event_id=source_event_id,
                cooldown_key=cooldown_key,
                exception_class=exc.__class__.__name__,
                failure_stage="submit",
            )
            return AlertResult(sent=False, reason="send_failed")

    def _emit_telemetry(self, event_type: str | dict[str, Any], **fields: Any) -> None:
        emit = self._telemetry_emit
        if emit is None:
            return
        try:
            if isinstance(event_type, dict):
                emit(event_type)
            else:
                emit(_telegram_telemetry_event(event_type, run_id=self.run_id, **fields))
        except Exception:
            LOGGER.debug("telegram telemetry emit failed", exc_info=True)

    @staticmethod
    def _format_message(kind: str, message: str, context: dict[str, Any]) -> str:
        if message:
            return message
        parts = [f"[{kind}]"]
        for key in sorted(context):
            if key in {"dedup_key", "source_event_id"}:
                continue
            parts.append(f"{key}={context[key]}")
        return " ".join(parts)

    @staticmethod
    def _dedup_key(category: str, message: str, context: dict[str, Any]) -> str:
        explicit = context.get("dedup_key")
        if explicit:
            return f"{category}:{explicit}"
        market = context.get("market") or context.get("asset")
        reason = context.get("reason") or context.get("event_type")
        if market or reason:
            return f"{category}:{market}:{reason}"
        return f"{category}:{message}"


_DEFAULT_ALERT_LAYER: TelegramAlertLayer | None = None


def _get_project_notifier() -> Any | None:
    try:
        from utils.logger import get_telegram_notifier

        return get_telegram_notifier()
    except Exception:
        return None


def _safe_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _telegram_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _telegram_telemetry_event(event_type: str, *, run_id: str | None = None, **fields: Any) -> dict[str, Any]:
    event: dict[str, Any] = {
        "timestamp": _telegram_timestamp(),
        "event_type": event_type,
        "route": _safe_optional_text(fields.pop("route", None)) or "unknown",
        "run_id": run_id,
        "source_event_id": _safe_optional_text(fields.pop("source_event_id", None)),
    }
    for key, value in fields.items():
        if value is not None:
            event[key] = value
    return event


def _telegram_enabled_value(settings: Any) -> bool:
    return str(getattr(settings, "telegram_enabled", "true") or "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
        "enabled",
    }


def _secret_present(value: Any) -> bool:
    try:
        if hasattr(value, "get_secret_value"):
            value = value.get_secret_value()
    except Exception:
        return False
    return bool(str(value or "").strip())


def emit_startup_config_telemetry(
    settings: Any,
    *,
    telemetry_emit: Callable[[dict[str, Any]], Any] | None,
    run_id: str | None = None,
) -> None:
    if telemetry_emit is None:
        return
    try:
        enabled = _telegram_enabled_value(settings)
        has_token = _secret_present(getattr(settings, "telegram_bot_token", ""))
        has_chat_id = _secret_present(getattr(settings, "telegram_chat_id", ""))
        if not enabled:
            telemetry_emit(
                _telegram_telemetry_event(
                    "telegram_disabled",
                    run_id=run_id,
                    route="startup",
                    source_event_id=None,
                    suppression_reason="disabled",
                )
            )
        elif not has_token or not has_chat_id:
            telemetry_emit(
                _telegram_telemetry_event(
                    "telegram_missing_config",
                    run_id=run_id,
                    route="startup",
                    source_event_id=None,
                    suppression_reason="missing_config",
                    has_token=has_token,
                    has_chat_id=has_chat_id,
                )
            )
    except Exception:
        LOGGER.debug("telegram startup config telemetry failed", exc_info=True)


def get_telegram_alert_layer() -> TelegramAlertLayer:
    global _DEFAULT_ALERT_LAYER
    if _DEFAULT_ALERT_LAYER is None:
        _DEFAULT_ALERT_LAYER = TelegramAlertLayer()
    return _DEFAULT_ALERT_LAYER


def notify_startup(message: str = "", **context: Any) -> AlertResult:
    return get_telegram_alert_layer().notify_startup(message, **context)


def notify_entry(message: str = "", **context: Any) -> AlertResult:
    return get_telegram_alert_layer().notify_entry(message, **context)


def notify_exit(message: str = "", **context: Any) -> AlertResult:
    return get_telegram_alert_layer().notify_exit(message, **context)


def notify_risk(message: str = "", **context: Any) -> AlertResult:
    return get_telegram_alert_layer().notify_risk(message, **context)


def notify_critical(message: str = "", **context: Any) -> AlertResult:
    return get_telegram_alert_layer().notify_critical(message, **context)


def notify_summary(message: str = "", **context: Any) -> AlertResult:
    return get_telegram_alert_layer().notify_summary(message, **context)


def notify_incident(message: str = "", **context: Any) -> AlertResult:
    return get_telegram_alert_layer().notify_incident(message, **context)
